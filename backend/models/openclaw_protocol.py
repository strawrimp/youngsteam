"""OpenClaw Gateway Protocol models.

Defines the WebSocket frame types, request/response structures,
and protocol constants for OpenClaw Gateway communication.

Reference: OpenClaw Gateway Protocol Documentation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class FrameType(str, Enum):
    """OpenClaw WS frame types."""

    EVENT = "event"
    REQ = "req"
    RES = "res"


class EventType(str, Enum):
    """OpenClaw event types."""

    CONNECT_CHALLENGE = "connect.challenge"
    HELLO_OK = "hello-ok"
    HELLO_ERROR = "hello-error"
    SESSION_END = "session.end"
    AGENT_OUTPUT = "agent.output"
    AGENT_TOOL_CALL = "agent.tool-call"
    AGENT_TOOL_RESULT = "agent.tool-result"
    PAIRING_REQUIRED = "pairing-required"
    ERROR = "error"


class Method(str, Enum):
    """OpenClaw RPC methods."""

    CONNECT = "connect"
    SESSIONS_CREATE = "sessions.create"
    SESSIONS_SEND = "sessions.send"
    SESSIONS_RESOLVE = "sessions.resolve"
    CHAT_SEND = "chat.send"
    AGENT_WAIT = "agent.wait"
    CHAT_HISTORY = "chat.history"


# ─── Ed25519 Protocol Constants (from JS index-DWX0XMYb.js) ──────────────

# Client identity (MUST match JS constants)
CLIENT_ID = "openclaw-control-ui"  # JS M.CONTROL_UI
CLIENT_MODE = "webchat"            # JS N.WEBCHAT
ROLE = "operator"

# Protocol version (JS: minProtocol=3, maxProtocol=3)
MIN_PROTOCOL = 3
MAX_PROTOCOL = 3
PROTOCOL_VERSION = 3

# Capabilities (JS: caps = ["tool-events"])
CAPS = ["tool-events"]

# Platform / locale constants
DEFAULT_PLATFORM = "macos"
DEFAULT_LOCALE = "en-US"
DEFAULT_USER_AGENT = "my-ai-company/openclaw-integration"
DEFAULT_CLIENT_VERSION = "local-dev"

# Scope constants (matching JS defaults)
SCOPE_ADMIN = "operator.admin"
SCOPE_READ = "operator.read"
SCOPE_WRITE = "operator.write"
SCOPE_APPROVALS = "operator.approvals"
SCOPE_PAIRING = "operator.pairing"
DEFAULT_SCOPES: List[str] = [
    SCOPE_ADMIN,
    SCOPE_READ,
    SCOPE_WRITE,
    SCOPE_APPROVALS,
    SCOPE_PAIRING,
]

# Sign string prefix (JS oe() uses "v2")
SIGN_STRING_PREFIX = "v2"


def build_sign_string(
    device_id: str,
    client_id: str,
    client_mode: str,
    role: str,
    scopes: List[str],
    signed_at_ms: int,
    token: Optional[str],
    nonce: str,
) -> str:
    """
    Build the string to sign, matching JS oe() function.

    JS oe():
        function oe(e) {
            let t = e.scopes.join(",");
            let n = e.token ?? "";
            return [
                "v2",
                e.deviceId, e.clientId, e.clientMode,
                e.role, t,
                String(e.signedAtMs), n, e.nonce
            ].join("|");
        }

    Sign string: v2|deviceId|clientId|clientMode|role|scope1,scope2|signedAtMs|token|nonce
    """
    scopes_str = ",".join(scopes)
    token_str = token if token else ""
    nonce_str = nonce if nonce else ""
    return f"{SIGN_STRING_PREFIX}|{device_id}|{client_id}|{client_mode}|{role}|{scopes_str}|{signed_at_ms}|{token_str}|{nonce_str}"


@dataclass
class DeviceIdentity:
    """Device identity for Ed25519 challenge-response authentication.

    Matches JS device identity block format:
    {
        "id": deviceId,
        "publicKey": base64url(publicKeyBytes),
        "signature": base64url(ed25519_signature),
        "signedAt": unix_timestamp_ms,
        "nonce": challenge_nonce,
    }
    """

    id: str
    public_key: str
    signature: str
    signed_at: int
    nonce: str


@dataclass
class ConnectParams:
    """Parameters for connect request (matching JS buildConnectParams())."""

    min_protocol: int = MIN_PROTOCOL
    max_protocol: int = MAX_PROTOCOL
    client: Dict[str, str] = field(default_factory=lambda: {
        "id": CLIENT_ID,
        "version": DEFAULT_CLIENT_VERSION,
        "platform": DEFAULT_PLATFORM,
        "mode": CLIENT_MODE,
    })
    role: str = ROLE
    scopes: List[str] = field(default_factory=lambda: list(DEFAULT_SCOPES))
    caps: List[str] = field(default_factory=lambda: list(CAPS))
    commands: List[str] = field(default_factory=list)
    permissions: Dict[str, bool] = field(default_factory=dict)
    auth: Dict[str, str] = field(default_factory=dict)
    locale: str = DEFAULT_LOCALE
    user_agent: str = DEFAULT_USER_AGENT
    device: Optional[DeviceIdentity] = None


@dataclass
class ConnectRequest:
    """Connect request frame."""

    id: str = ""
    type: str = FrameType.REQ.value
    method: str = Method.CONNECT.value
    params: ConnectParams = field(default_factory=ConnectParams)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "type": self.type,
            "id": self.id,
            "method": self.method,
            "params": {
                "minProtocol": self.params.min_protocol,
                "maxProtocol": self.params.max_protocol,
                "client": self.params.client,
                "role": self.params.role,
                "scopes": self.params.scopes,
                "caps": self.params.caps,
                "commands": self.params.commands,
                "permissions": self.params.permissions,
                "auth": self.params.auth,
                "locale": self.params.locale,
                "userAgent": self.params.user_agent,
            },
        }
        if self.params.device:
            device = self.params.device
            if isinstance(device, DeviceIdentity):
                result["params"]["device"] = {
                    "id": device.id,
                    "publicKey": device.public_key,
                    "signature": device.signature,
                    "signedAt": device.signed_at,
                    "nonce": device.nonce,
                }
            else:
                # Already a dict
                result["params"]["device"] = device
        return result


@dataclass
class ChallengeEvent:
    """connect.challenge event from server."""

    type: str = FrameType.EVENT.value
    event: str = EventType.CONNECT_CHALLENGE.value
    payload: Dict[str, Any] = field(default_factory=dict)

    @property
    def nonce(self) -> Optional[str]:
        """Extract nonce from payload."""
        return self.payload.get("nonce")

    @property
    def timestamp(self) -> Optional[int]:
        """Extract timestamp from payload."""
        return self.payload.get("ts")


@dataclass
class HelloOkPayload:
    """Payload from hello-ok response."""

    type: str = "hello-ok"
    protocol: int = PROTOCOL_VERSION
    policy: Dict[str, Any] = field(default_factory=dict)
    auth: Dict[str, Any] = field(default_factory=dict)

    @property
    def device_token(self) -> Optional[str]:
        """Extract device token."""
        return self.auth.get("deviceToken")

    @property
    def approved_scopes(self) -> List[str]:
        """Extract approved scopes."""
        return self.auth.get("scopes", [])

    @property
    def tick_interval_ms(self) -> Optional[int]:
        """Extract tick interval from policy."""
        return self.policy.get("tickIntervalMs")


@dataclass
class HelloOkResponse:
    """hello-ok response frame."""

    id: str = ""
    type: str = FrameType.RES.value
    ok: bool = True
    payload: HelloOkPayload = field(default_factory=HelloOkPayload)


@dataclass
class SessionCreateParams:
    """Parameters for sessions.create request."""

    model: str = "minimax/MiniMax-M2.7"
    system_prompt: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


@dataclass
class SessionSendParams:
    """Parameters for sessions.send request."""

    content: str = ""
    session_key: str = ""
    stream: bool = False


@dataclass
class AgentWaitParams:
    """Parameters for agent.wait request."""

    run_id: str = ""
    session_key: str = ""
    timeout_ms: int = 30000


@dataclass
class SessionResponse:
    """Response from session operations."""

    run_id: Optional[str] = None
    session_key: str = ""
    messages: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "pending"


@dataclass
class AgentMessage:
    """Agent output message."""

    role: str = "assistant"
    content: str = ""
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentMessage":
        """Create from dictionary."""
        return cls(
            role=data.get("role", "assistant"),
            content=data.get("content", ""),
            tool_calls=data.get("tool_calls", []),
        )


@dataclass
class ExecutionResult:
    """Result of OpenClaw instruction execution."""

    success: bool
    output: str = ""
    actions_taken: List[str] = field(default_factory=list)
    error: str = ""
    session_key: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "output": self.output,
            "actions_taken": self.actions_taken,
            "error": self.error,
            "session_key": self.session_key,
            "details": self.details,
        }


class ErrorCode(str, Enum):
    """OpenClaw error codes."""

    DEVICE_AUTH_NONCE_REQUIRED = "DEVICE_AUTH_NONCE_REQUIRED"
    DEVICE_AUTH_SIGNATURE_INVALID = "DEVICE_AUTH_SIGNATURE_INVALID"
    AUTH_TOKEN_MISMATCH = "AUTH_TOKEN_MISMATCH"
    PAIRING_REQUIRED = "pairing-required"
    UNKNOWN_METHOD = "UNKNOWN_METHOD"
    INVALID_PARAMS = "INVALID_PARAMS"
    SCOPE_DENIED = "SCOPE_DENIED"
    SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
    RUN_TIMEOUT = "RUN_TIMEOUT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass
class ProtocolError:
    """OpenClaw protocol error."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProtocolError":
        """Create from error response dictionary."""
        return cls(
            code=data.get("code", "UNKNOWN"),
            message=data.get("message", str(data)),
            details=data.get("details"),
        )

    def is_auth_error(self) -> bool:
        """Check if this is an authentication error."""
        return self.code in (
            ErrorCode.DEVICE_AUTH_NONCE_REQUIRED.value,
            ErrorCode.DEVICE_AUTH_SIGNATURE_INVALID.value,
            ErrorCode.AUTH_TOKEN_MISMATCH.value,
            ErrorCode.PAIRING_REQUIRED.value,
        )

    def is_scope_error(self) -> bool:
        """Check if this is a scope error."""
        return self.code == ErrorCode.SCOPE_DENIED.value
