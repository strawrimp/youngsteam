"""OpenClaw Device Store - manages Ed25519 device identity and paired device tokens.

Handles:
- Ed25519 keypair generation (matching JS kt() from index-DWX0XMYb.js)
- Paired device token storage
- Approved scopes persistence
- Gateway metadata

Reference: OpenClaw Gateway Protocol - Device Authentication
           JS index-DWX0XMYb.js: kt() keygen, Et() key decode, oe() sign string
"""

import base64
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from models.openclaw_protocol import DEFAULT_SCOPES

logger = logging.getLogger(__name__)

# Default state file path
DEFAULT_STATE_PATH = "backend/state/openclaw_device.json"


# ─── Helpers: base64url (RFC 4648 §5, no padding) ───────────────────────────

def b64url(data: bytes) -> str:
    """Encode bytes to base64url without padding (matching JS btoa/atob)."""
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()


def b64url_decode(s: str) -> bytes:
    """Decode base64url string with padding restoration."""
    padding = 4 - len(s) % 4
    if padding != 4:
        s += '=' * padding
    return base64.urlsafe_b64decode(s)


# ─── Ed25519 Key Generation (matching JS kt()) ──────────────────────────────

def generate_ed25519_device_identity(seed: Optional[bytes] = None) -> Dict[str, Any]:
    """
    Generate Ed25519 device identity matching JS kt().

    JS kt() logic:
    1. Generate 32 random bytes as the Ed25519 seed
    2. Derive keypair from seed
    3. deviceId = hex(SHA-256(publicKeyBytes))
    4. publicKey = base64url(publicKeyBytes)  # 32 bytes, no padding
    5. privateKey = base64url(seed)           # 32 bytes, no padding

    Returns:
        Dict with deviceId, publicKey, privateKey (b64url), and private_key_obj
    """
    if seed is None:
        seed = os.urandom(32)

    # Create Ed25519 key from seed (JS Ed25519 uses raw 32-byte seed as private key)
    private_key = Ed25519PrivateKey.from_private_bytes(seed)
    public_key = private_key.public_key()
    public_key_bytes = public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)  # 32 bytes

    # deviceId = hex(SHA-256(publicKeyBytes))
    device_id = hashlib.sha256(public_key_bytes).hexdigest()

    return {
        "deviceId": device_id,
        "publicKey": b64url(public_key_bytes),
        "privateKey": b64url(seed),  # Store raw seed (matching JS localStorage)
        "private_key_obj": private_key,  # cryptography object for signing
        "public_key_bytes": public_key_bytes,
        "seed": seed,
    }


@dataclass
class DeviceState:
    """Persisted device state."""

    device_id: str
    public_key: str
    private_key_ref: str  # base64url-encoded 32-byte Ed25519 seed
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
    """Manages Ed25519 device identity and paired tokens for OpenClaw Gateway.

    Responsibilities:
    - Generate stable Ed25519 device identity (matching JS kt())
    - Store/load device state (seed-based persistence)
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
        # Cache cryptography objects for active signing
        self._signing_key: Optional[Ed25519PrivateKey] = None
        self._public_key_bytes: Optional[bytes] = None

    @property
    def state(self) -> Optional[DeviceState]:
        """Lazy load state."""
        if self._state is None:
            self._load_state(validate_ed25519=True)
        return self._state

    def _generate_ed25519_identity(self, seed: Optional[bytes] = None) -> DeviceState:
        """Generate new Ed25519 identity and persist it.

        Args:
            seed: Optional 32-byte seed for deterministic keygen

        Returns:
            DeviceState with Ed25519 identity
        """
        identity = generate_ed25519_device_identity(seed=seed)

        new_state = DeviceState(
            device_id=identity["deviceId"],
            public_key=identity["publicKey"],
            private_key_ref=identity["privateKey"],  # base64url seed
            gateway_base_url=self.gateway_url,
        )

        # Cache crypto objects for signing
        self._signing_key = identity["private_key_obj"]
        self._public_key_bytes = identity["public_key_bytes"]

        self._save_state(new_state)
        logger.info(f"[DeviceStore] 🆕 Created new Ed25519 device identity: {new_state.device_id[:20]}...")

        return new_state

    def load_or_create_device_identity(self) -> DeviceState:
        """Load existing Ed25519 device identity or create new one.

        Returns:
            DeviceState with device identity
        """
        existing = self._load_state(validate_ed25519=True)
        if existing and existing.device_id:
            logger.info(f"[DeviceStore] ✅ Loaded existing Ed25519 device: {existing.device_id[:20]}...")
            return existing

        # Create new Ed25519 identity
        return self._generate_ed25519_identity()

    def _load_state(self, validate_ed25519: bool = False) -> Optional[DeviceState]:
        """Load state from file and optionally validate Ed25519 key integrity.

        Args:
            validate_ed25519: If True, decode seed and regenerate keypair to verify

        Returns:
            DeviceState if file exists and is valid, None otherwise
        """
        if not self.state_path.exists():
            logger.debug(f"[DeviceStore] No state file at {self.state_path}")
            return None

        try:
            with open(self.state_path, "r") as f:
                data = json.load(f)
            state = DeviceState.from_dict(data)

            if validate_ed25519 and state.private_key_ref:
                # Decode seed and regenerate keypair to verify integrity
                try:
                    seed = b64url_decode(state.private_key_ref)
                    identity = generate_ed25519_device_identity(seed=seed)
                    if identity["deviceId"] == state.device_id:
                        # Verified OK — cache crypto objects
                        self._signing_key = identity["private_key_obj"]
                        self._public_key_bytes = identity["public_key_bytes"]
                        logger.debug(f"[DeviceStore] Ed25519 key integrity verified")
                    else:
                        logger.warning(
                            f"[DeviceStore] ⚠️  Device ID hash mismatch — "
                            f"loaded={state.device_id[:20]}..., "
                            f"computed={identity['deviceId'][:20]}..."
                        )
                        return None
                except Exception as e:
                    logger.warning(f"[DeviceStore] ⚠️  Ed25519 key validation failed: {e}")
                    return None

            logger.debug(f"[DeviceStore] Loaded state from {self.state_path}")
            self._state = state
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

    def ensure_identity(self) -> DeviceState:
        """Ensure a valid Ed25519 identity exists (load or create).

        Returns:
            DeviceState with valid identity
        """
        return self.load_or_create_device_identity()

    # ─── Ed25519 signing helpers ───────────────────────────────────────────

    def get_signing_key(self) -> Optional[Ed25519PrivateKey]:
        """Get Ed25519 private key for signing.

        Returns:
            Ed25519PrivateKey if identity loaded, None otherwise
        """
        if self._signing_key is not None:
            return self._signing_key

        # Try to load from state
        if self.state and self.state.private_key_ref:
            try:
                seed = b64url_decode(self.state.private_key_ref)
                self._signing_key = Ed25519PrivateKey.from_private_bytes(seed)
                return self._signing_key
            except Exception as e:
                logger.error(f"[DeviceStore] Failed to decode signing key: {e}")
                return None

        return None

    def get_public_key_b64(self) -> Optional[str]:
        """Get base64url-encoded public key.

        Returns:
            Public key string if available
        """
        if self.state:
            return self.state.public_key
        return None

    def get_device_id(self) -> Optional[str]:
        """Get device ID (SHA-256 of public key bytes).

        Returns:
            Hex device ID string
        """
        if self.state:
            return self.state.device_id
        return None

    def has_identity(self) -> bool:
        """Check if we have a persisted Ed25519 identity.

        Returns:
            True if identity exists and is valid
        """
        try:
            return self.state is not None and bool(self.state.device_id)
        except Exception:
            return False

    # ─── Token management ──────────────────────────────────────────────────

    def get_device_token(self) -> Optional[str]:
        """Get cached device token.

        Returns:
            Device token if available, None otherwise
        """
        if self.state:
            return self.state.device_token
        return None

    def get_private_key_material(self) -> Optional[str]:
        """Return stored private key reference (base64url seed)."""
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
            Dictionary with device.id, device.publicKey, etc.
            The caller must fill in signature, signedAt, and nonce.
        """
        if not self.state:
            return None

        return {
            "id": self.state.device_id,
            "publicKey": self.state.public_key,
            "signature": "",  # Caller must fill
            "signedAt": 0,  # Caller must fill
            "nonce": "",  # Caller must fill (challenge nonce)
        }

    def __repr__(self) -> str:
        return (
            f"[DeviceStore] path={self.state_path} "
            f"device_id={self.state.device_id[:16] + '...' if self.state else 'none'} "
            f"has_token={bool(self.state.device_token if self.state else False)}"
        )
