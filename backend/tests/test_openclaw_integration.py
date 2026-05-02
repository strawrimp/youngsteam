"""Unit tests for OpenClaw WebSocket integration."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from repositories.openclaw_device_store import OpenClawDeviceStore
from services.openclaw_service import OpenClawService
from services.openclaw_ws_client import GatewayWsClient
from tools.openclaw_tool import OpenClawTool


class TestOpenClawService:
    """Tests for the high-level OpenClaw service."""

    def test_initialization(self):
        service = OpenClawService(
            base_url="http://test.local:18789",
            api_key="test-key",
            timeout=60.0,
            ws_enabled=True,
        )
        assert service.BASE_URL == "http://test.local:18789"
        assert service.API_KEY == "test-key"
        assert service.TIMEOUT == 60.0
        assert service.ws_enabled is True

    def test_get_headers_with_api_key(self):
        service = OpenClawService(
            base_url="http://test.local:18789",
            api_key="secret",
        )
        assert service._get_headers()["Authorization"] == "Bearer secret"

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        service = OpenClawService(base_url="http://test.local:18789")
        client = MagicMock()
        client.is_authenticated = False
        client.connect = AsyncMock()
        client.is_authenticated = True

        with patch.object(service, "_get_ws_client", return_value=client):
            assert await service.health_check() is True

    @pytest.mark.asyncio
    async def test_execute_instruction_success(self):
        service = OpenClawService(base_url="http://test.local:18789")
        client = MagicMock()
        client.is_authenticated = True
        client.execute_instruction = AsyncMock(
            return_value=SimpleNamespace(
                to_dict=lambda: {
                    "success": True,
                    "output": "작업 완료",
                    "actions_taken": [],
                    "error": "",
                }
            )
        )

        with patch.object(service, "_get_ws_client", return_value=client):
            result = await service.execute_instruction("작업 실행")

        assert result["success"] is True
        assert result["output"] == "작업 완료"

    @pytest.mark.asyncio
    async def test_execute_instruction_failure(self):
        service = OpenClawService(base_url="http://test.local:18789")
        client = MagicMock()
        client.is_authenticated = False
        client.connect = AsyncMock(side_effect=RuntimeError("pairing required"))

        with patch.object(service, "_get_ws_client", return_value=client):
            result = await service.execute_instruction("작업 실행")

        assert result["success"] is False
        assert "pairing required" in result["error"]


class TestGatewayWsClient:
    """Tests for the low-level gateway WS client."""

    def test_build_connect_request_uses_operator_mode(self, tmp_path):
        store = OpenClawDeviceStore(state_path=str(tmp_path / "device.json"))
        client = GatewayWsClient(
            gateway_url="ws://gateway.local:18789/",
            device_store=store,
            gateway_token="shared-token",
            requested_scopes=["operator.read", "operator.write"],
        )

        request = asyncio.run(client._build_connect_request("abc", 123))

        data = request.to_dict()
        assert data["method"] == "connect"
        assert data["params"]["client"]["mode"] == "operator"
        assert data["params"]["client"]["id"] == "my-ai-company"
        assert data["params"]["role"] == "operator"
        assert data["params"]["scopes"] == ["operator.read", "operator.write"]
        assert data["params"]["auth"]["token"] == "shared-token"
        assert data["params"]["device"]["nonce"] == "abc"
        assert data["params"]["device"]["signature"]

    @pytest.mark.asyncio
    async def test_handle_hello_ok_persists_device_token(self, tmp_path):
        store = OpenClawDeviceStore(state_path=str(tmp_path / "device.json"))
        store.load_or_create_device_identity()
        client = GatewayWsClient(
            gateway_url="ws://gateway.local:18789/",
            device_store=store,
            gateway_token="shared-token",
        )

        await client._handle_hello_ok(
            {
                "payload": {
                    "protocol": 3,
                    "policy": {"tickIntervalMs": 15000},
                    "auth": {
                        "deviceToken": "device-token",
                        "scopes": ["operator.read", "operator.write"],
                    },
                }
            }
        )

        assert store.get_device_token() == "device-token"
        assert store.get_approved_scopes() == ["operator.read", "operator.write"]


class TestOpenClawTool:
    """Tests for the user-facing OpenClaw tool."""

    def test_tool_properties(self):
        tool = OpenClawTool()

        assert tool.name == "delegate_to_openclaw"
        assert "실세계 작업" in tool.description
        assert "instruction" in tool.parameters["properties"]

    @pytest.mark.asyncio
    async def test_execute_without_service(self):
        tool = OpenClawTool()

        with patch("tools.openclaw_tool.get_openclaw_service", return_value=None):
            result = await tool.execute(instruction="작업 실행")

        assert result.success is False
        assert "사용할 수 없습니다" in result.error

    @pytest.mark.asyncio
    async def test_execute_when_gateway_unreachable(self):
        tool = OpenClawTool()
        service = MagicMock()
        service.is_available = AsyncMock(return_value=False)
        service.BASE_URL = "http://test.local:18789"

        with patch("tools.openclaw_tool.get_openclaw_service", return_value=service):
            result = await tool.execute(instruction="작업 실행")

        assert result.success is False
        assert "연결할 수 없습니다" in result.error
