"""OpenClaw Device Store - manages device identity and paired device tokens.

Handles:
- Device keypair generation
- Paired device token storage
- Approved scopes persistence
- Gateway metadata

Reference: OpenClaw Gateway Protocol - Device Authentication
"""

import json
import logging
import hashlib
import time
import uuid
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Default state file path
DEFAULT_STATE_PATH = "backend/state/openclaw_device.json"


@dataclass
class DeviceState:
    """Persisted device state."""

    device_id: str
    public_key: str
    private_key_ref: str  # Path or reference to private key
    device_token: Optional[str] = None
    approved_scopes: List[str] = field(default_factory=list)
    gateway_base_url: str = ""
    last_connected_at: Optional[float] = None
    protocol_version: int = 3

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DeviceState":
        """Create from dictionary."""
        return cls(
            device_id=data.get("device_id", ""),
            public_key=data.get("public_key", ""),
            private_key_ref=data.get("private_key_ref", ""),
            device_token=data.get("device_token"),
            approved_scopes=data.get("approved_scopes", []),
            gateway_base_url=data.get("gateway_base_url", ""),
            last_connected_at=data.get("last_connected_at"),
            protocol_version=data.get("protocol_version", 3),
        )


class OpenClawDeviceStore:
    """Manages device identity and paired tokens for OpenClaw Gateway.

    Responsibilities:
    - Generate stable device identity (keypair)
    - Store/load device state
    - Cache device token after successful handshake
    - Clear invalid tokens on auth failures
    """

    def __init__(
        self,
        state_path: Optional[str] = None,
        gateway_url: Optional[str] = None,
    ):
        """Initialize device store.

        Args:
            state_path: Path to state file (default: backend/state/openclaw_device.json)
            gateway_url: Base URL of gateway for this device
        """
        self.state_path = Path(state_path or DEFAULT_STATE_PATH)
        self.gateway_url = gateway_url or ""

        # Ensure directory exists
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

        self._state: Optional[DeviceState] = None

    @property
    def state(self) -> Optional[DeviceState]:
        """Lazy load state."""
        if self._state is None:
            self._state = self._load_state()
        return self._state

    def _generate_keypair(self) -> tuple:
        """Generate RSA keypair for device signing.

        Returns:
            Tuple of (public_key_pem, private_key_pem)

        Note: For development, uses simple key generation.
              Production should use secure key storage.
        """
        # For development: use a simple approach
        # In production, this should use proper RSA key generation
        # with secure private key storage
        device_id = str(uuid.uuid4())
        # Development-only stable pseudo keypair. This is not cryptographically
        # equivalent to the production OpenClaw clients, but it gives the client
        # a durable device identity and deterministic request signing material.
        private_key = uuid.uuid4().hex + uuid.uuid4().hex
        public_key = hashlib.sha256(private_key.encode("utf-8")).hexdigest()
        return public_key, private_key

    def load_or_create_device_identity(self) -> DeviceState:
        """Load existing device identity or create new one.

        Returns:
            DeviceState with device identity
        """
        existing = self._load_state()
        if existing and existing.device_id:
            logger.info(f"[DeviceStore] Loaded existing device: {existing.device_id}")
            return existing

        # Create new identity
        device_id = str(uuid.uuid4())
        public_key, private_key = self._generate_keypair()

        new_state = DeviceState(
            device_id=device_id,
            public_key=public_key,
            private_key_ref=private_key,
            gateway_base_url=self.gateway_url,
        )

        self._save_state(new_state)
        logger.info(f"[DeviceStore] Created new device identity: {device_id}")

        return new_state

    def _load_state(self) -> Optional[DeviceState]:
        """Load state from file.

        Returns:
            DeviceState if file exists and valid, None otherwise
        """
        if not self.state_path.exists():
            logger.debug(f"[DeviceStore] No state file at {self.state_path}")
            return None

        try:
            with open(self.state_path, "r") as f:
                data = json.load(f)
            state = DeviceState.from_dict(data)
            logger.debug(f"[DeviceStore] Loaded state from {self.state_path}")
            return state
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"[DeviceStore] Failed to load state: {e}")
            return None

    def _save_state(self, state: DeviceState) -> None:
        """Save state to file.

        Args:
            state: DeviceState to save
        """
        try:
            with open(self.state_path, "w") as f:
                json.dump(state.to_dict(), f, indent=2)
            logger.debug(f"[DeviceStore] Saved state to {self.state_path}")
            self._state = state
        except IOError as e:
            logger.error(f"[DeviceStore] Failed to save state: {e}")

    def get_device_token(self) -> Optional[str]:
        """Get cached device token.

        Returns:
            Device token if available, None otherwise
        """
        if self.state:
            return self.state.device_token
        return None

    def get_private_key_material(self) -> Optional[str]:
        """Return stored private key material for request signing."""
        if self.state:
            return self.state.private_key_ref
        return None

    def get_approved_scopes(self) -> List[str]:
        """Get approved scopes from last successful connection.

        Returns:
            List of approved scope strings
        """
        if self.state:
            return self.state.approved_scopes
        return []

    def save_handshake_result(
        self,
        device_token: str,
        approved_scopes: List[str],
        gateway_url: str,
    ) -> None:
        """Save successful handshake result.

        Args:
            device_token: Token from hello-ok response
            approved_scopes: Scopes approved by gateway
            gateway_url: URL of gateway for this connection
        """
        if not self.state:
            logger.error("[DeviceStore] No device state to update")
            return

        self.state.device_token = device_token
        self.state.approved_scopes = approved_scopes
        self.state.gateway_base_url = gateway_url
        self.state.last_connected_at = time.time()

        self._save_state(self.state)
        logger.info(
            f"[DeviceStore] Saved handshake result: token={device_token[:20]}..., "
            f"scopes={approved_scopes}"
        )

    def clear_invalid_token(self) -> None:
        """Clear stored token on auth failure.

        Called when gateway returns AUTH_TOKEN_MISMATCH or similar errors.
        """
        if not self.state:
            return

        logger.warning("[DeviceStore] Clearing invalid device token")
        self.state.device_token = None
        self.state.approved_scopes = []
        self._save_state(self.state)

    def update_last_connected(self) -> None:
        """Update last connection timestamp."""
        if self.state:
            self.state.last_connected_at = time.time()
            self._save_state(self.state)

    def is_token_valid(self, min_age_seconds: int = 0) -> bool:
        """Check if stored token exists and is recent enough.

        Args:
            min_age_seconds: Minimum age of token in seconds (0 = any valid token)

        Returns:
            True if token exists and is recent enough
        """
        if not self.state or not self.state.device_token:
            return False

        if min_age_seconds <= 0:
            return True

        if not self.state.last_connected_at:
            return False

        age = time.time() - self.state.last_connected_at
        return age <= min_age_seconds

    def get_device_identity_for_connect(self) -> Optional[Dict[str, Any]]:
        """Get device identity data for connect request.

        Returns:
            Dictionary with device.id, device.publicKey, device.signature, etc.
        """
        if not self.state:
            return None

        # In production, this would:
        # 1. Sign the nonce from challenge
        # 2. Include the signature in the request
        # For development, returns simple identity
        return {
            "id": self.state.device_id,
            "publicKey": self.state.public_key,
            "signature": f"dev-sig-{self.state.device_id}",
            "signedAt": int(time.time() * 1000),
            "nonce": "",  # Will be filled by caller with challenge nonce
        }

    def __repr__(self) -> str:
        return (
            f"[DeviceStore] path={self.state_path} "
            f"device_id={self.state.device_id if self.state else 'none'} "
            f"has_token={bool(self.state.device_token if self.state else False)}"
        )
