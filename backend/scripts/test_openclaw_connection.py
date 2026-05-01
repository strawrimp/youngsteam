#!/usr/bin/env python3
"""Test OpenClaw Gateway connection."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import settings
from services.openclaw_service import OpenClawService


async def main():
    print("Testing OpenClaw Gateway connection...")
    print(f"Base URL: {settings.openclaw_base_url}")
    print(f"Enabled: {settings.openclaw_enabled}")

    if not settings.openclaw_enabled:
        print("❌ OPENCLAW_ENABLED=false — skipping test")
        return

    service = OpenClawService(
        base_url=settings.openclaw_base_url,
        api_key=settings.openclaw_api_key,
        timeout=settings.openclaw_timeout,
    )

    # Try health check
    print("\n[1] Running health check...")
    try:
        result = await service.health_check()
        if result:
            print("✅ OpenClaw Gateway is reachable!")
        else:
            print("❌ OpenClaw Gateway health check failed")
            print("   Possible causes:")
            print("   - OpenClaw not running on Mac Mini")
            print("   - Network connectivity issue")
            print("   - Wrong OPENCLAW_BASE_URL")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Try fallback host if configured
    if settings.openclaw_fallback_host:
        print(f"\n[2] Trying fallback host: {settings.openclaw_fallback_host}")
        # TODO: Implement fallback

if __name__ == "__main__":
    asyncio.run(main())
