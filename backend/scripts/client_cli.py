#!/usr/bin/env python3
"""
OpenClaw Gateway E2E Connection Test (Standalone CLI).

Exercises the full WebSocket lifecycle against a real Mac Mini Gateway:
  1. Connect → receive challenge
  2. Ed25519 sign challenge → send connect request
  3. Receive hello-ok → persist device token
  4. (Optional) Create session → send instruction → wait for output

Usage:
  # Default: use .env config
  python backend/scripts/client_cli.py

  # Override gateway URL and token
  python backend/scripts/client_cli.py --url ws://172.30.1.18:18789/ --token my-token

  # Test with a sample instruction
  python backend/scripts/client_cli.py --say "open Safari and search for weather"

  # Verbose logging
  python backend/scripts/client_cli.py -v

Exit codes:
  0  — Full success (connect + auth)
  1  — Connection or handshake failed
  2  — Authentication failed (gateway rejected credentials)
  3  — Session creation or instruction execution failed
"""

import argparse
import asyncio
import logging
import os
import sys
import time
from typing import Optional

# Ensure backend/ is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import settings
from models.openclaw_protocol import (
    CLIENT_ID,
    CLIENT_MODE,
    ROLE,
    CAPS,
    PROTOCOL_VERSION,
    DEFAULT_USER_AGENT,
    ExecutionResult,
)
from repositories.openclaw_device_store import OpenClawDeviceStore
from services.openclaw_ws_client import GatewayWsClient


# ─── Logging helpers ──────────────────────────────────────────────────────

class ColorFormatter(logging.Formatter):
    """Simple color-coded log formatter for the terminal."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

    LEVEL_COLORS = {
        logging.DEBUG: CYAN,
        logging.INFO: GREEN,
        logging.WARNING: YELLOW,
        logging.ERROR: RED,
        logging.CRITICAL: RED + BOLD,
    }

    def format(self, record):
        color = self.LEVEL_COLORS.get(record.levelno, self.RESET)
        record.msg = f"{color}{record.msg}{self.RESET}"
        return super().format(record)


def setup_logging(verbose: bool) -> None:
    """Configure logging with optional verbosity."""
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        ColorFormatter("%(message)s") if sys.stdout.isatty()
        else logging.Formatter("%(message)s")
    )
    logging.root.setLevel(level)
    logging.root.handlers.clear()
    logging.root.addHandler(handler)

    # Suppress noisy library logging
    logging.getLogger("websockets").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


log = logging.getLogger("client_cli")


# ─── Progress display ────────────────────────────────────────────────────

def step(label: str, ok: bool, detail: str = "") -> None:
    """Print a step result with colored check/cross."""
    icon = "✅" if ok else "❌"
    msg = f"  {icon} {label}"
    if detail:
        msg += f" — {detail}"
    log.info(msg)


# ─── Core test logic ─────────────────────────────────────────────────────

async def test_connection(
    gateway_url: str,
    gateway_token: str,
    scopes: list,
    device_state_path: str,
    verbose: bool,
    instruction: Optional[str] = None,
) -> int:
    """
    Run the full E2E connection test.

    Returns exit code (0 = success).
    """
    start_time = time.time()

    # ── 1. Device store setup ──────────────────────────────────────────
    log.info(f"\n{'='*60}")
    log.info(f"🔌 OpenClaw Gateway E2E Test")
    log.info(f"{'='*60}")
    log.info(f"")
    log.info(f"  Gateway URL    : {gateway_url}")
    log.info(f"  Device State   : {device_state_path}")
    log.info(f"  Client ID      : {CLIENT_ID}")
    log.info(f"  Client Mode    : {CLIENT_MODE}")
    log.info(f"  Role           : {ROLE}")
    log.info(f"  Scopes         : {scopes}")
    log.info(f"  Caps           : {CAPS}")
    log.info(f"  Protocol       : v{PROTOCOL_VERSION}")
    log.info(f"  User Agent     : {DEFAULT_USER_AGENT}")
    log.info(f"")

    store = OpenClawDeviceStore(state_path=device_state_path)

    # Show existing device identity
    try:
        state = store.load_or_create_device_identity()
        log.info(f"  Device ID      : {state.device_id[:32]}...")
        log.info(f"  Public Key     : {state.public_key[:32]}...")
        has_token = store.get_device_token() is not None
        if has_token:
            token_preview = store.get_device_token()[:20]
            log.info(f"  Device Token   : {token_preview}... (cached)")
        else:
            log.info(f"  Device Token   : (none — will be assigned on first connect)")
        log.info(f"")
    except Exception as e:
        step("Device identity load", False, str(e))
        return 1

    # ── 2. WebSocket connect + handshake ──────────────────────────────
    client = GatewayWsClient(
        gateway_url=gateway_url,
        device_store=store,
        gateway_token=gateway_token,
        requested_scopes=scopes,
        timeout=30.0,
    )

    log.info(f"  [1/3] Connecting & authenticating...")
    try:
        ok = await client.connect()
    except RuntimeError as e:
        err_str = str(e)
        if "Authentication failed" in err_str:
            step("Authentication", False, err_str)
            return 2
        step("Connection", False, err_str)
        return 1
    except Exception as e:
        step("Connection", False, str(e))
        await client.disconnect()
        return 1

    step("WebSocket connect", True, f"authenticated={client.is_authenticated}")

    # Show device token after handshake
    device_token = store.get_device_token()
    if device_token:
        step("Device token persisted", True, f"{device_token[:24]}...")
    else:
        step("Device token persisted", False, "no token returned by gateway")

    elapsed_connect = time.time() - start_time
    log.info(f"  ⏱  Connection time: {elapsed_connect:.1f}s")
    log.info(f"")

    # ── 3. (Optional) Create session + send instruction ──────────────
    if instruction:
        log.info(f"  [2/3] Executing instruction...")
        log.info(f"  Instruction: {instruction[:80]}{'...' if len(instruction) > 80 else ''}")
        log.info(f"")

        try:
            result: ExecutionResult = await client.execute_instruction(
                instruction=instruction,
            )
        except Exception as e:
            step("Instruction execution", False, str(e))
            await client.disconnect()
            return 3

        if result.success:
            output_preview = result.output[:200] if result.output else "(empty)"
            step("Instruction executed", True, f"session={result.session_key}")
            if result.output:
                log.info(f"")
                log.info(f"  ┌─ Agent Output {'─'*40}")
                output_lines = result.output.split("\n")
                for line in output_lines[:15]:
                    log.info(f"  │ {line}")
                if len(output_lines) > 15:
                    log.info(f"  │ ... ({len(output_lines) - 15} more lines)")
                log.info(f"  └{'─'*55}")
                log.info(f"")
        else:
            step("Instruction failed", False, result.error or "no output")
            await client.disconnect()
            return 3

        elapsed_total = time.time() - start_time
        log.info(f"  ⏱  Total time: {elapsed_total:.1f}s")

    # ── 4. Summary ───────────────────────────────────────────────────
    elapsed_total = time.time() - start_time
    log.info(f"")
    log.info(f"{'='*60}")
    log.info(f"  ✅ E2E Test Complete")
    log.info(f"  Duration        : {elapsed_total:.1f}s")
    log.info(f"  Gateway         : {gateway_url}")
    log.info(f"  Device ID       : {store.load_or_create_device_identity().device_id[:32]}...")
    log.info(f"  Device Token    : {'✅ cached' if store.get_device_token() else '❌ missing'}")
    if instruction:
        log.info(f"  Instruction     : {'✅ completed' if result.success else '❌ failed'}")
    log.info(f"{'='*60}")
    log.info(f"")

    await client.disconnect()
    return 0


# ─── Entry point ─────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="OpenClaw Gateway E2E Connection Test",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  %(prog)s\n"
            "  %(prog)s --url ws://172.30.1.18:18789/ --token my-token\n"
            "  %(prog)s --say 'open calculator'\n"
            "  %(prog)s -v --say 'tell me the current time'\n"
        ),
    )

    # Connection settings
    parser.add_argument(
        "--url",
        default=None,
        help="Gateway WebSocket URL (default: from OPENCLAW_WS_ENDPOINT or OPENCLAW_BASE_URL)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="Gateway shared token (default: from OPENCLAW_API_KEY)",
    )
    parser.add_argument(
        "--scopes",
        default=None,
        help="Comma-separated scopes (default: from OPENCLAW_REQUESTED_SCOPES)",
    )
    parser.add_argument(
        "--state",
        default=None,
        help="Device state file path (default: from OPENCLAW_DEVICE_STATE_PATH)",
    )

    # Behavior
    parser.add_argument(
        "--say",
        default=None,
        metavar="INSTRUCTION",
        help="Send an instruction to the agent after connecting (e.g., 'open Safari')",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        default=False,
        help="Enable verbose (DEBUG) logging",
    )

    return parser.parse_args()


def resolve_settings(args: argparse.Namespace) -> tuple:
    """Resolve effective settings from CLI args + env + defaults."""
    # Gateway URL: CLI > WS endpoint > base URL with ws scheme
    gateway_url = args.url
    if not gateway_url:
        gateway_url = settings.openclaw_ws_endpoint
    if not gateway_url:
        base = settings.openclaw_base_url.rstrip("/")
        # Replace http with ws
        base = base.replace("http://", "ws://").replace("https://", "wss://")
        gateway_url = base + "/"

    # Token: CLI > API key
    gateway_token = args.token or settings.openclaw_api_key or ""

    # Scopes: CLI > env > default
    if args.scopes:
        scopes = [s.strip() for s in args.scopes.split(",")]
    else:
        scopes_str = settings.openclaw_requested_scopes
        scopes = [s.strip() for s in scopes_str.split(",")] if scopes_str else [
            "operator.read", "operator.write"
        ]

    # Device state path: CLI > env > default
    device_state_path = args.state or settings.openclaw_device_state_path or "backend/state/openclaw_device.json"

    # Ensure state directory exists
    state_dir = os.path.dirname(device_state_path)
    if state_dir:
        os.makedirs(state_dir, exist_ok=True)

    return gateway_url, gateway_token, scopes, device_state_path


def main() -> int:
    """CLI entry point. Returns exit code."""
    args = parse_args()
    setup_logging(args.verbose)

    try:
        gateway_url, gateway_token, scopes, device_state_path = resolve_settings(args)
    except Exception as e:
        log.error(f"Configuration error: {e}")
        return 1

    if not gateway_url:
        log.error(
            "No gateway URL configured. "
            "Set OPENCLAW_WS_ENDPOINT or OPENCLAW_BASE_URL in .env, "
            "or pass --url."
        )
        return 1

    if not gateway_token:
        log.warning(
            "⚠️  No gateway token configured. "
            "Set OPENCLAW_API_KEY in .env or pass --token."
        )
        log.warning("   The gateway may reject the connection if a token is required.")
        log.warning("")

    try:
        exit_code = asyncio.run(
            test_connection(
                gateway_url=gateway_url,
                gateway_token=gateway_token,
                scopes=scopes,
                device_state_path=device_state_path,
                verbose=args.verbose,
                instruction=args.say,
            )
        )
    except KeyboardInterrupt:
        log.info("\n⚠️  Interrupted by user")
        return 130
    except Exception as e:
        log.error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
