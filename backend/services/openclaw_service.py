"""OpenClaw Gateway Service - High-level API for OpenClaw integration.

This module provides the high-level service interface for delegating
real-world tasks to OpenClaw Gateway on Mac Mini.

Architecture:
- OpenClawService: Public API for tools and other services
- Uses GatewayWsClient internally for WebSocket communication
- Handles connection lifecycle, session management, and error handling

Reference: OpenClaw Gateway Protocol Documentation
"""

import asyncio
import json
import logging
from typing import Any, Dict, Optional

from config import settings
from models.openclaw_protocol import ExecutionResult
from repositories.openclaw_device_store import OpenClawDeviceStore
from services.openclaw_ws_client import GatewayWsClient

logger = logging.getLogger(__name__)

# Singleton instances
_openclaw_service: Optional["OpenClawService"] = None
_ws_client: Optional[GatewayWsClient] = None


class OpenClawService:
    """High-level service for OpenClaw Gateway integration.

    Provides:
    - health_check(): Verify gateway connectivity and auth
    - execute_instruction(): Execute natural language instruction
    - is_available(): Quick availability check

    This service is a facade that:
    - Manages WebSocket client lifecycle
    - Handles reconnection and token refresh
    - Provides simple instruction-based API
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[float] = None,
        ws_enabled: Optional[bool] = None,
    ):
        """Initialize OpenClaw service.

        Args:
            base_url: Gateway URL (default from settings)
            api_key: Gateway token (default from settings)
            timeout: Request timeout (default from settings)
            ws_enabled: Force WebSocket usage (default from settings)
        """
        self.base_url = base_url or settings.openclaw_base_url
        self.api_key = api_key or settings.openclaw_api_key
        self.timeout = timeout or settings.openclaw_timeout
        self.ws_enabled = ws_enabled if ws_enabled is not None else getattr(settings, 'openclaw_ws_enabled', True)
        # Backward-compatible aliases used by existing callers/tests.
        self.BASE_URL = self.base_url
        self.API_KEY = self.api_key
        self.TIMEOUT = self.timeout

        # Device store for identity and token management
        state_path = getattr(settings, 'openclaw_device_state_path', 'backend/state/openclaw_device.json')
        self.device_store = OpenClawDeviceStore(
            state_path=state_path,
            gateway_url=self.base_url,
        )

        # Requested scopes
        requested_scopes_str = getattr(settings, 'openclaw_requested_scopes', 'operator.admin,operator.read,operator.write,operator.approvals,operator.pairing')
        self.requested_scopes = [s.strip() for s in requested_scopes_str.split(',')]

        logger.info(
            f"[OpenClawService] Initialized: url={self.base_url} "
            f"ws_enabled={self.ws_enabled} "
            f"scopes={self.requested_scopes}"
        )

    def _get_headers(self) -> Dict[str, str]:
        """Build auth headers for diagnostics and backward compatibility."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def _get_ws_client(self) -> GatewayWsClient:
        """Get or create WebSocket client instance."""
        global _ws_client

        if _ws_client is None:
            ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
            _ws_client = GatewayWsClient(
                gateway_url=ws_url,
                device_store=self.device_store,
                gateway_token=self.api_key,
                requested_scopes=self.requested_scopes,
                timeout=self.timeout,
            )
            logger.info("[OpenClawService] Created new WS client")

        return _ws_client

    async def health_check(self) -> bool:
        """Check if OpenClaw Gateway is reachable and authenticated.

        Tries multiple methods:
        1. WebSocket connection (full auth)
        2. HTTP health endpoint (basic connectivity)

        Returns:
            True if gateway is accessible (authenticated via WS or reachable via HTTP)
        """
        if not self.base_url:
            logger.warning("[OpenClawService] BASE_URL not configured")
            return False

        # Try WebSocket first if enabled
        if self.ws_enabled:
            try:
                client = self._get_ws_client()

                # Already connected and authenticated?
                if client.is_authenticated:
                    logger.info("[OpenClawService] ✅ WebSocket authenticated")
                    return True

                # Try to connect
                await client.connect()
                if client.is_authenticated:
                    logger.info("[OpenClawService] ✅ WebSocket authenticated")
                    return True

            except Exception as e:
                logger.debug(
                    f"[OpenClawService] WebSocket health check failed: {e}, "
                    f"trying HTTP fallback"
                )

        # Try HTTP health endpoints as fallback
        import httpx

        for endpoint in [f"{self.base_url.rstrip('/')}/health",
                        f"{self.base_url.rstrip('/')}/v1/models"]:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(endpoint)
                    if response.status_code in (200, 404):  # 404 ok, means gateway exists
                        logger.info(f"[OpenClawService] ✅ HTTP reachable: {endpoint}")
                        return True
            except Exception:
                pass

        logger.error(f"[OpenClawService] ❌ Gateway unreachable at {self.base_url}")
        return False

    async def is_available(self) -> bool:
        """Quick availability check without full handshake.

        Tries WebSocket first, then HTTP.

        Returns:
            True if gateway is reachable (may not be authenticated)
        """
        if not self.base_url:
            return False

        # Try WebSocket first
        if self.ws_enabled:
            try:
                client = self._get_ws_client()
                if client.is_connected:
                    return True

                # Quick connect attempt with short timeout
                ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
                import websockets
                async with websockets.connect(ws_url, open_timeout=5.0) as ws:
                    logger.debug("[OpenClawService] WebSocket available")
                    return True
            except Exception as e:
                logger.debug(f"[OpenClawService] WebSocket not available: {e}")

        # Try HTTP as fallback
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.base_url.rstrip('/')}/")
                logger.debug(f"[OpenClawService] HTTP available (status {response.status_code})")
                return True
        except Exception:
            logger.debug("[OpenClawService] HTTP not available")
            return False

    def _build_payload(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
        agent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build LLM payload for instruction execution.

        Args:
            instruction: Natural language instruction
            context: Optional execution context
            agent_name: Optional delegating agent name

        Returns:
            Dict ready for LLM API (HTTP or WebSocket)
        """
        system_prompt = f"""You are an intelligent agent tasked with executing instructions.
Your role is to:
1. Understand the given instruction
2. Determine what actions need to be taken
3. Execute those actions
4. Report the results

You have access to various tools and capabilities.
Always be clear about what you're doing and the outcomes.
"""

        if context:
            system_prompt += f"\n\nExecution context:\n{json.dumps(context, indent=2)}"

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": instruction},
        ]

        payload = {
            "model": "gpt-4",  # OpenClaw understands this
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 2000,
        }

        if agent_name:
            payload["metadata"] = {"agent": agent_name}

        return payload

    async def _execute_via_ws(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute instruction via WebSocket.

        Args:
            payload: LLM payload prepared by _build_payload()

        Returns:
            Dict with success, output, actions_taken, error
        """
        try:
            client = self._get_ws_client()

            # Ensure we're connected and authenticated
            if not client.is_authenticated:
                await client.connect()

            # Extract instruction from payload for the client
            messages = payload.get("messages", [])
            instruction = ""
            for msg in messages:
                if msg.get("role") == "user":
                    instruction = msg.get("content", "")
                    break

            # Execute via WebSocket
            result = await client.execute_instruction(instruction, None)
            return result.to_dict()

        except Exception as e:
            logger.warning(f"[OpenClawService] WebSocket execution failed: {e}")
            raise

    async def _execute_via_http(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute instruction via HTTP REST API (fallback).

        Args:
            payload: LLM payload prepared by _build_payload()

        Returns:
            Dict with success, output, actions_taken, error
        """
        import httpx

        try:
            # Determine endpoint (prefer /v1/chat/completions)
            endpoint = f"{self.base_url.rstrip('/')}/v1/chat/completions"

            headers = self._get_headers()
            headers["Content-Type"] = "application/json"

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"[OpenClawService] HTTP POST {endpoint}")
                response = await client.post(endpoint, json=payload, headers=headers)

                if response.status_code == 200:
                    data = response.json()
                    # Parse OpenAI-format response
                    if "choices" in data and data["choices"]:
                        choice = data["choices"][0]
                        if "message" in choice:
                            output = choice["message"].get("content", "")
                            return {
                                "success": True,
                                "output": output,
                                "actions_taken": [],
                                "error": None,
                            }

                    return {
                        "success": True,
                        "output": str(data),
                        "actions_taken": [],
                        "error": None,
                    }

                elif response.status_code == 401:
                    raise PermissionError(
                        f"HTTP 401: Unauthorized. Check OPENCLAW_API_KEY. "
                        f"(Known issue: operator.write scope may be missing from external networks)"
                    )

                elif response.status_code == 403:
                    raise PermissionError(
                        f"HTTP 403: Forbidden. Insufficient scopes. "
                        f"Expected: operator.read, operator.write"
                    )

                else:
                    error_text = response.text[:500]
                    logger.error(
                        f"[OpenClawService] HTTP {response.status_code}: {error_text}"
                    )
                    raise RuntimeError(
                        f"HTTP {response.status_code}: {error_text}"
                    )

        except httpx.ConnectError as e:
            logger.warning(f"[OpenClawService] HTTP connection failed: {e}")
            raise

        except Exception as e:
            logger.error(f"[OpenClawService] HTTP execution failed: {e}")
            raise

    async def execute_instruction(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
        agent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a natural language instruction via OpenClaw.

        This is the main entry point for delegating tasks to OpenClaw.

        Strategy:
        1. Try WebSocket first (cleaner protocol, avoids OAuth scope issues)
        2. If WebSocket fails, fall back to HTTP REST API
        3. If both fail, return error with diagnostics

        Args:
            instruction: Natural language instruction (e.g., "Send email to Bob")
            context: Optional context (e.g., {"expected_outcome": "Email sent successfully"})
            agent_name: Optional name of delegating agent

        Returns:
            Dict with:
            - success: bool
            - output: str (agent's response)
            - actions_taken: List[str] (actions performed)
            - error: str (error message if failed)
        """
        if not self.base_url:
            return {
                "success": False,
                "output": "",
                "actions_taken": [],
                "error": "OpenClaw BASE_URL not configured. Set OPENCLAW_BASE_URL in .env",
            }

        payload = self._build_payload(instruction, context, agent_name)

        # Try WebSocket first (if enabled)
        if self.ws_enabled:
            try:
                logger.info("[OpenClawService] Attempting WebSocket execution")
                return await self._execute_via_ws(payload)

            except asyncio.TimeoutError:
                logger.warning(
                    "[OpenClawService] WebSocket timeout, falling back to HTTP"
                )

            except Exception as e:
                logger.warning(
                    f"[OpenClawService] WebSocket failed ({e}), falling back to HTTP"
                )

        # Fall back to HTTP
        try:
            logger.info("[OpenClawService] Attempting HTTP execution")
            return await self._execute_via_http(payload)

        except PermissionError as e:
            return {
                "success": False,
                "output": "",
                "actions_taken": [],
                "error": str(e),
            }

        except ConnectionError as e:
            return {
                "success": False,
                "output": "",
                "actions_taken": [],
                "error": f"Cannot connect to OpenClaw Gateway at {self.base_url}. "
                         f"Verify OPENCLAW_BASE_URL and gateway is running.",
            }

        except Exception as e:
            logger.error(f"[OpenClawService] All execution methods failed: {e}")
            return {
                "success": False,
                "output": "",
                "actions_taken": [],
                "error": f"OpenClaw execution failed: {str(e)}",
            }

    async def check_gateway_capabilities(self) -> Dict[str, Any]:
        """Check what capabilities the gateway supports.

        Returns:
            Dict with capability information
        """
        try:
            client = self._get_ws_client()

            if not client.is_authenticated:
                await client.connect()

            return {
                "connected": client.is_connected,
                "authenticated": client.is_authenticated,
                "approved_scopes": client._approved_scopes,
                "protocol_version": client._protocol_version,
                "tick_interval_ms": client._tick_interval_ms,
            }
        except Exception as e:
            return {
                "connected": False,
                "authenticated": False,
                "error": str(e),
            }

    def explain_last_error(self) -> str:
        """Get explanation of the last error.

        Returns human-readable explanation of what went wrong.
        """
        if _ws_client is None:
            return "No WebSocket client initialized"

        # Add specific error explanations here based on error patterns
        return "See logs for details"

    async def close(self) -> None:
        """Close connection and cleanup."""
        global _ws_client
        if _ws_client:
            await _ws_client.disconnect()
            _ws_client = None
            logger.info("[OpenClawService] Connection closed")

    def __repr__(self) -> str:
        return (
            f"[OpenClawService] url={self.base_url} "
            f"ws_enabled={self.ws_enabled}"
        )


def get_openclaw_service() -> Optional[OpenClawService]:
    """Get or create global OpenClawService instance.

    Returns:
        OpenClawService if enabled in settings, None otherwise
    """
    global _openclaw_service

    if not getattr(settings, 'openclaw_enabled', False):
        logger.debug("[OpenClawService] Not enabled (OPENCLAW_ENABLED=false)")
        return None

    if _openclaw_service is None:
        _openclaw_service = OpenClawService()

    return _openclaw_service


async def check_openclaw_status() -> Dict[str, Any]:
    """Check OpenClaw status and return a status report.

    Returns:
        Dict with:
        - reachable: bool
        - base_url: str
        - enabled: bool
        - message: str
    """
    enabled = getattr(settings, 'openclaw_enabled', False)
    base_url = getattr(settings, 'openclaw_base_url', '')

    if not enabled:
        return {
            "reachable": False,
            "base_url": base_url,
            "enabled": False,
            "message": "OpenClaw integration is disabled (OPENCLAW_ENABLED=false)",
        }

    service = OpenClawService()
    reachable = await service.is_available()

    return {
        "reachable": reachable,
        "base_url": base_url,
        "enabled": True,
        "message": (
            f"✅ OpenClaw Gateway reachable at {base_url}"
            if reachable
            else f"❌ OpenClaw Gateway unreachable at {base_url}"
        ),
    }
