"""OpenClaw Gateway Service - High-level API for OpenClaw integration.

This module provides the high-level service interface for delegating
real-world tasks to OpenClaw Gateway on Mac Mini.

Architecture:
- OpenClawService: Public API for tools and other services
- Uses GatewayWsClient internally for WebSocket communication
- Handles connection lifecycle, session management, and error handling

Reference: OpenClaw Gateway Protocol Documentation
"""

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
        requested_scopes_str = getattr(settings, 'openclaw_requested_scopes', 'operator.read,operator.write')
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

        Performs a full connection check:
        1. TCP/WS connection
        2. connect.challenge received
        3. connect request sent
        4. hello-ok received

        Returns:
            True if gateway is fully accessible and authenticated
        """
        if not self.base_url:
            logger.warning("[OpenClawService] BASE_URL not configured")
            return False

        try:
            client = self._get_ws_client()

            # Already connected and authenticated?
            if client.is_authenticated:
                logger.info("[OpenClawService] ✅ Already authenticated")
                return True

            # Try to connect
            await client.connect()
            return client.is_authenticated

        except Exception as e:
            logger.error(f"[OpenClawService] ❌ Health check failed: {e}")
            return False

    async def is_available(self) -> bool:
        """Quick availability check without full handshake.

        Returns:
            True if we can establish a connection (auth may still fail)
        """
        if not self.base_url:
            return False

        try:
            client = self._get_ws_client()
            if client.is_connected:
                return True

            # Quick connect attempt with short timeout
            ws_url = self.base_url.replace("http://", "ws://").replace("https://", "wss://")
            import websockets
            async with websockets.connect(ws_url, open_timeout=5.0) as ws:
                return True
        except Exception:
            return False

    async def execute_instruction(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
        agent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Execute a natural language instruction via OpenClaw.

        This is the main entry point for delegating tasks to OpenClaw.

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

        if not self.ws_enabled:
            return {
                "success": False,
                "output": "",
                "actions_taken": [],
                "error": "OpenClaw WebSocket is disabled (OPENCLAW_WS_ENABLED=false)",
            }

        try:
            client = self._get_ws_client()

            # Ensure we're connected
            if not client.is_authenticated:
                await client.connect()

            # Execute via WebSocket
            result = await client.execute_instruction(instruction, context)

            return result.to_dict()

        except Exception as e:
            logger.error(f"[OpenClawService] Execute failed: {e}")
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
