"""OpenClaw Gateway WebSocket Client.

Implements the full OpenClaw Gateway WebSocket protocol:
1. Connect to ws://host:port/
2. Receive connect.challenge event
3. Send connect request with device auth
4. Receive hello-ok response
5. Send session RPC commands
6. Handle responses and events

Reference: OpenClaw Gateway Protocol Documentation
"""

import asyncio
import hashlib
import hmac
import json
import logging
import time
import uuid
from typing import Any, Dict, List, Optional, Callable

import websockets
import websockets.exceptions

from models.openclaw_protocol import (
    FrameType,
    EventType,
    Method,
    ChallengeEvent,
    ConnectParams,
    ConnectRequest,
    ExecutionResult,
    ProtocolError,
    DeviceIdentity,
    PROTOCOL_VERSION,
)
from repositories.openclaw_device_store import OpenClawDeviceStore
from config import settings

logger = logging.getLogger(__name__)


class GatewayWsClient:
    """WebSocket client for OpenClaw Gateway protocol.

    Handles:
    - Connection establishment with challenge-response handshake
    - Device authentication and token management
    - Session lifecycle (create, send, wait)
    - Response parsing and event handling
    - Reconnection with cached device token
    """

    def __init__(
        self,
        gateway_url: str,
        device_store: OpenClawDeviceStore,
        gateway_token: str,
        requested_scopes: Optional[List[str]] = None,
        timeout: float = 180.0,
        on_event: Optional[Callable[[Dict[str, Any]], None]] = None,
    ):
        """Initialize WebSocket client.

        Args:
            gateway_url: WebSocket URL (e.g., ws://172.30.1.18:18789/)
            device_store: Device identity and token store
            gateway_token: Shared gateway token for auth
            requested_scopes: List of scopes to request (default: operator.read, operator.write)
            timeout: Request timeout in seconds
            on_event: Optional callback for received events
        """
        self.gateway_url = gateway_url.rstrip("/") + "/"
        self.device_store = device_store
        self.gateway_token = gateway_token
        self.requested_scopes = requested_scopes or ["operator.read", "operator.write"]
        self.timeout = timeout
        self.on_event = on_event

        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._connected: bool = False
        self._authenticated: bool = False
        self._device_token: Optional[str] = None
        self._approved_scopes: List[str] = []
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()

        # Protocol state
        self._protocol_version: int = PROTOCOL_VERSION
        self._tick_interval_ms: Optional[int] = None

    @property
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected and self._ws is not None

    @property
    def is_authenticated(self) -> bool:
        """Check if authenticated with gateway."""
        return self._authenticated

    async def connect(self) -> bool:
        """Establish WebSocket connection and complete handshake.

        Steps:
        1. Connect to WebSocket
        2. Receive connect.challenge event
        3. Send connect request with device auth
        4. Receive hello-ok or hello-error

        Returns:
            True if connection and handshake successful

        Raises:
            RuntimeError: If connection or handshake fails
        """
        if self.is_connected:
            logger.warning("[WSClient] Already connected")
            return True

        try:
            # Connect to WebSocket
            logger.info(f"[WSClient] Connecting to {self.gateway_url}")
            self._ws = await websockets.connect(
                self.gateway_url,
                open_timeout=10.0,
                close_timeout=5.0,
            )
            self._connected = True
            logger.info("[WSClient] ✅ WebSocket connected")

            # Receive connect.challenge from server
            challenge_event = await self._receive_challenge()
            if not challenge_event:
                raise RuntimeError("Did not receive connect.challenge event")

            nonce = challenge_event.nonce
            timestamp = challenge_event.timestamp
            logger.info(f"[WSClient] Received challenge: nonce={nonce[:20]}...")

            # Build and send connect request
            connect_request = await self._build_connect_request(nonce, timestamp)
            await self._send_request(connect_request)

            # Receive hello-ok or hello-error
            response = await self._receive_response(connect_request.id)
            if not response:
                raise RuntimeError("Did not receive connect response")

            if response.get("ok"):
                await self._handle_hello_ok(response)
                self._authenticated = True
                logger.info("[WSClient] ✅ Authentication successful")
                return True
            else:
                # Error response - error is in 'error' key, not 'payload'
                error_data = response.get("error", {})
                error = ProtocolError.from_dict(error_data)
                if error.code in {"AUTH_TOKEN_MISMATCH", "AUTH_DEVICE_TOKEN_MISMATCH"}:
                    self.device_store.clear_invalid_token()
                logger.error(f"[WSClient] ❌ Authentication failed: {error.code} - {error.message}")
                await self.disconnect()
                raise RuntimeError(f"Authentication failed: {error.code}")

        except Exception as e:
            logger.error(f"[WSClient] Connection failed: {e}")
            await self.disconnect()
            raise

    async def _receive_challenge(self) -> Optional[ChallengeEvent]:
        """Receive and parse connect.challenge event.

        Returns:
            ChallengeEvent if received successfully
        """
        try:
            raw = await asyncio.wait_for(
                self._ws.recv(),
                timeout=10.0
            )
            data = json.loads(raw)

            if data.get("type") == FrameType.EVENT.value and data.get("event") == EventType.CONNECT_CHALLENGE.value:
                return ChallengeEvent(
                    type=data.get("type"),
                    event=data.get("event"),
                    payload=data.get("payload", {}),
                )
            else:
                logger.warning(f"[WSClient] Unexpected first frame: {data.get('type')}/{data.get('event')}")
                return None

        except asyncio.TimeoutError:
            logger.error("[WSClient] Timeout waiting for challenge")
            return None
        except Exception as e:
            logger.error(f"[WSClient] Failed to receive challenge: {e}")
            return None

    async def _build_connect_request(
        self,
        nonce: str,
        timestamp: int,
    ) -> ConnectRequest:
        """Build connect request with device authentication.

        Args:
            nonce: Challenge nonce from server
            timestamp: Challenge timestamp

        Returns:
            ConnectRequest ready to send
        """
        device_state = self.device_store.load_or_create_device_identity()
        auth_token = self.device_store.get_device_token() or self.gateway_token

        private_key = self.device_store.get_private_key_material() or ""
        signature_payload = "\n".join(
            [
                device_state.device_id,
                nonce,
                str(timestamp or 0),
                "operator",
                ",".join(self.requested_scopes),
            ]
        )
        signature = hmac.new(
            private_key.encode("utf-8"),
            signature_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        auth = {"token": auth_token}
        device = DeviceIdentity(
            id=device_state.device_id,
            public_key=device_state.public_key,
            signature=signature,
            signed_at=int(time.time() * 1000),
            nonce=nonce,
        )

        params = ConnectParams(
            min_protocol=PROTOCOL_VERSION,
            max_protocol=PROTOCOL_VERSION,
            client={
                "id": getattr(settings, "openclaw_client_id", "my-ai-company"),
                "version": getattr(settings, "openclaw_client_version", "local-dev"),
                "platform": "macos",
                "mode": "operator",
            },
            role="operator",
            scopes=self.requested_scopes,
            caps=[],
            commands=[],
            permissions={},
            auth=auth,
            locale="ko-KR",
            user_agent="my-ai-company/openclaw-integration",
            device=device,
        )

        return ConnectRequest(
            id=str(uuid.uuid4()),
            method=Method.CONNECT.value,
            params=params,
        )

    async def _send_request(self, request: ConnectRequest) -> None:
        """Send JSON-RPC style request.

        Args:
            request: Request object with to_dict method
        """
        data = request.to_dict() if hasattr(request, 'to_dict') else request
        await self._ws.send(json.dumps(data))
        logger.debug(f"[WSClient] Sent: {data.get('method', 'unknown')}")

    async def _receive_response(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Receive response for specific request ID.

        Args:
            request_id: ID of request to match response

        Returns:
            Response dictionary if received
        """
        try:
            # Collect all messages until we get a matching response
            deadline = time.time() + self.timeout

            while time.time() < deadline:
                remaining = deadline - time.time()
                try:
                    raw = await asyncio.wait_for(
                        self._ws.recv(),
                        timeout=min(remaining, 10.0)
                    )
                except asyncio.TimeoutError:
                    continue

                data = json.loads(raw)

                # Handle event frames by queuing them
                if data.get("type") == FrameType.EVENT.value:
                    event_type = data.get("event")
                    logger.debug(f"[WSClient] Event: {event_type}")
                    if self.on_event:
                        self.on_event(data)
                    await self._event_queue.put(data)
                    continue

                # Handle response frames
                if data.get("type") == FrameType.RES.value:
                    resp_id = data.get("id")
                    if resp_id == request_id:
                        logger.debug(f"[WSClient] Matched response for {request_id}")
                        return data
                    else:
                        logger.warning(f"[WSClient] Response ID mismatch: {resp_id} != {request_id}")

            logger.error(f"[WSClient] Timeout waiting for response {request_id}")
            return None

        except Exception as e:
            logger.error(f"[WSClient] Failed to receive response: {e}")
            return None

    async def _handle_hello_ok(self, response: Dict[str, Any]) -> None:
        """Handle successful hello-ok response.

        Args:
            response: hello-ok response dictionary
        """
        payload = response.get("payload", {})
        auth_data = payload.get("auth", {})

        # Extract and cache device token
        self._device_token = auth_data.get("deviceToken")
        self._approved_scopes = auth_data.get("scopes", self.requested_scopes)

        # Extract protocol info
        self._protocol_version = payload.get("protocol", PROTOCOL_VERSION)
        policy = payload.get("policy", {})
        self._tick_interval_ms = policy.get("tickIntervalMs")

        # Save to device store
        if self._device_token:
            self.device_store.save_handshake_result(
                device_token=self._device_token,
                approved_scopes=self._approved_scopes,
                gateway_url=self.gateway_url,
            )

        logger.info(
            f"[WSClient] Auth OK: scopes={self._approved_scopes}, "
            f"tick_interval={self._tick_interval_ms}ms"
        )

    async def create_session(
        self,
        model: str = "minimax/MiniMax-M2.7",
        system_prompt: Optional[str] = None,
    ) -> Optional[str]:
        """Create a new session.

        Args:
            model: Model to use
            system_prompt: Optional system prompt

        Returns:
            Session key if successful
        """
        if not self.is_authenticated:
            raise RuntimeError("Not authenticated")

        request_id = str(uuid.uuid4())
        params = {
            "model": model,
        }
        if system_prompt:
            params["systemPrompt"] = system_prompt

        request = {
            "type": FrameType.REQ.value,
            "id": request_id,
            "method": Method.SESSIONS_CREATE.value,
            "params": params,
        }

        await self._send_request(request)
        response = await self._receive_response(request_id)

        if response and response.get("ok"):
            result = response.get("payload", {})
            session_key = result.get("sessionKey") or result.get("key")
            logger.info(f"[WSClient] Created session: {session_key}")
            return session_key

        logger.error(f"[WSClient] Failed to create session: {response}")
        return None

    async def send_session_message(
        self,
        session_key: str,
        content: str,
    ) -> Optional[str]:
        """Send a message to a session.

        Args:
            session_key: Session to send to
            content: Message content

        Returns:
            Run ID if successful
        """
        if not self.is_authenticated:
            raise RuntimeError("Not authenticated")

        request_id = str(uuid.uuid4())
        request = {
            "type": FrameType.REQ.value,
            "id": request_id,
            "method": Method.SESSIONS_SEND.value,
            "params": {
                "sessionKey": session_key,
                "input": {
                    "role": "user",
                    "content": content,
                },
                "stream": False,
            },
        }

        await self._send_request(request)
        response = await self._receive_response(request_id)

        if response and response.get("ok"):
            result = response.get("payload", {})
            run_id = result.get("runId") or result.get("id")
            logger.info(f"[WSClient] Sent message, run_id={run_id}")
            return run_id

        logger.error(f"[WSClient] Failed to send message: {response}")
        return None

    async def wait_for_completion(
        self,
        session_key: str,
        run_id: str,
        timeout_ms: int = 60000,
    ) -> List[str]:
        """Wait for agent run to complete and collect output.

        Args:
            session_key: Session containing the run
            run_id: Run to wait for
            timeout_ms: Timeout in milliseconds

        Returns:
            List of output messages from the agent
        """
        if not self.is_authenticated:
            raise RuntimeError("Not authenticated")

        request_id = str(uuid.uuid4())
        request = {
            "type": FrameType.REQ.value,
            "id": request_id,
            "method": Method.AGENT_WAIT.value,
            "params": {
                "sessionKey": session_key,
                "runId": run_id,
                "timeoutMs": timeout_ms,
            },
        }

        await self._send_request(request)

        outputs: List[str] = []
        deadline = time.time() + (timeout_ms / 1000)

        while time.time() < deadline:
            try:
                raw = await asyncio.wait_for(
                    self._ws.recv(),
                    timeout=min(max(deadline - time.time(), 0.1), 5.0)
                )
                data = json.loads(raw)

                # Check for agent output events
                if data.get("type") == FrameType.EVENT.value:
                    event_type = data.get("event")
                    if event_type == EventType.AGENT_OUTPUT.value:
                        payload = data.get("payload", {})
                        content = payload.get("content", "")
                        if isinstance(content, list):
                            content = "\n".join(
                                part.get("text", "")
                                for part in content
                                if isinstance(part, dict)
                            )
                        if content:
                            outputs.append(content)
                    elif event_type == EventType.SESSION_END.value:
                        logger.info("[WSClient] Session ended")
                        break
                    elif event_type == EventType.PAIRING_REQUIRED.value:
                        payload = data.get("payload", {})
                        request_id = payload.get("requestId", "unknown")
                        raise RuntimeError(
                            f"Gateway pairing approval required. Approve request {request_id} on Mac Mini with 'openclaw devices list' then 'openclaw devices approve <requestId>'."
                        )

                # Check for matching response
                if data.get("type") == FrameType.RES.value:
                    resp_id = data.get("id")
                    if resp_id == request_id:
                        logger.info(f"[WSClient] Wait complete, collected {len(outputs)} outputs")
                        return outputs

            except asyncio.TimeoutError:
                continue

        return outputs

    async def disconnect(self) -> None:
        """Close WebSocket connection."""
        if self._ws:
            try:
                await self._ws.close()
            except Exception as e:
                logger.debug(f"[WSClient] Error closing: {e}")
            self._ws = None
        self._connected = False
        self._authenticated = False
        logger.info("[WSClient] Disconnected")

    async def execute_instruction(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> ExecutionResult:
        """Execute a natural language instruction via OpenClaw.

        High-level flow:
        1. Create session
        2. Send instruction
        3. Wait for completion
        4. Return result

        Args:
            instruction: Natural language instruction
            context: Optional context dict

        Returns:
            ExecutionResult with output and metadata
        """
        if not self.is_authenticated:
            try:
                await self.connect()
            except Exception as e:
                return ExecutionResult(
                    success=False,
                    error=f"Connection failed: {e}",
                )

        try:
            # Build message content
            content = instruction
            if context:
                expected = context.get("expected_outcome", "")
                if expected:
                    content = f"{instruction}\n\n[Expected outcome] {expected}"

            # Create session
            session_key = await self.create_session()
            if not session_key:
                return ExecutionResult(
                    success=False,
                    error="Failed to create session",
                )

            # Send instruction
            run_id = await self.send_session_message(session_key, content)
            if not run_id:
                return ExecutionResult(
                    success=False,
                    error="Failed to send message",
                    session_key=session_key,
                )

            # Wait for completion
            outputs = await self.wait_for_completion(session_key, run_id)

            if outputs:
                return ExecutionResult(
                    success=True,
                    output="\n".join(outputs),
                    session_key=session_key,
                )
            else:
                return ExecutionResult(
                    success=True,
                    output="No output received",
                    session_key=session_key,
                )

        except Exception as e:
            logger.error(f"[WSClient] Execute error: {e}")
            return ExecutionResult(
                success=False,
                error=str(e),
            )

    def __repr__(self) -> str:
        return (
            f"[WSClient] url={self.gateway_url} "
            f"connected={self.is_connected} "
            f"auth={self.is_authenticated}"
        )
