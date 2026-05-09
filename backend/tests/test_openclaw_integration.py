"""Unit tests for OpenClaw WebSocket integration."""

import asyncio
import re
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from repositories.openclaw_device_store import OpenClawDeviceStore, b64url_decode
from services.openclaw_service import OpenClawService
from services.openclaw_ws_client import GatewayWsClient
from tools.openclaw_tool import OpenClawTool

# main.py의 CLAW_MENTION_PATTERN을 복사하여 테스트
CLAW_MENTION_PATTERN = re.compile(
    r"(?:"
    r"@openclaw\b"
    r"|@클로(?![가-힣])"
    r"|(?:^|[\s,.!?\"'「『【])"
    r"클로"
    r"(?:"
    r"야|아|이|가|는|은|을|를|의|에|서|와|과|도|만|"
    r"로|으로|랑|이랑|"
    r"한테|한테서|에게|에게서|"
    r"부터|까지|조차|마저|밖에|보다|처럼|"
    r"이고|이가|"
    r"이야|이지|이라는"
    r")*?"
    r"(?=[\s,.!?\"'~」」】\)]|$)"
    r")",
    re.IGNORECASE,
)


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
        """Test that execute_instruction handles WS failure and HTTP fallback failure."""
        service = OpenClawService(base_url="http://test.local:18789")

        # Mock WS client to fail
        client = MagicMock()
        client.is_authenticated = False
        client.connect = AsyncMock(side_effect=RuntimeError("pairing required"))

        # Mock HTTP to also fail
        with patch.object(service, "_get_ws_client", return_value=client):
            with patch.object(service, "_execute_via_http", side_effect=RuntimeError("HTTP failed")):
                result = await service.execute_instruction("작업 실행")

        assert result["success"] is False
        assert "HTTP failed" in result["error"]  # HTTP error is what we see after WS fallback

    @pytest.mark.asyncio
    async def test_execute_instruction_ws_fallback_to_http(self):
        """Test that execute_instruction falls back to HTTP when WS fails."""
        service = OpenClawService(base_url="http://test.local:18789", ws_enabled=True)

        # Mock WS client to fail
        ws_client = MagicMock()
        ws_client.is_authenticated = False
        ws_client.connect = AsyncMock(side_effect=RuntimeError("WS connection failed"))

        # Mock HTTP to succeed
        http_result = {
            "success": True,
            "output": "Task completed via HTTP",
            "actions_taken": [],
            "error": None,
        }

        with patch.object(service, "_get_ws_client", return_value=ws_client):
            with patch.object(service, "_execute_via_http", return_value=http_result):
                result = await service.execute_instruction("작업 실행")

        assert result["success"] is True
        assert result["output"] == "Task completed via HTTP"


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
        # Client identity — uses protocol constants, not hardcoded values
        assert data["params"]["client"]["mode"] == "webchat"           # CLIENT_MODE
        assert data["params"]["client"]["id"] == "openclaw-control-ui" # CLIENT_ID
        assert data["params"]["client"]["version"] == "local-dev"      # DEFAULT_CLIENT_VERSION
        assert data["params"]["client"]["platform"] == "macos"         # DEFAULT_PLATFORM
        # Role and scopes
        assert data["params"]["role"] == "operator"                    # ROLE
        assert data["params"]["scopes"] == ["operator.read", "operator.write"]
        # Capabilities
        assert data["params"]["caps"] == ["tool-events"]               # CAPS
        # Auth
        assert data["params"]["auth"]["token"] == "shared-token"
        # Locale and user agent (camelCase in serialized form)
        assert data["params"]["locale"] == "en-US"                     # DEFAULT_LOCALE
        assert data["params"]["userAgent"] == "my-ai-company/openclaw-integration"
        # Device identity
        assert data["params"]["device"]["nonce"] == "abc"
        assert data["params"]["device"]["signature"]
        # Ed25519 signature must be unpadded base64url, 64 bytes
        try:
            decoded = b64url_decode(data["params"]["device"]["signature"])
            assert len(decoded) == 64  # Ed25519 signatures are 64 bytes
        except Exception:
            pytest.fail("signature must be valid base64url-encoded Ed25519 sig")
        # device.id and device.publicKey must be set (camelCase in serialization)
        assert data["params"]["device"]["publicKey"]
        assert data["params"]["device"]["signedAt"]

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


class TestClawMentionPattern:
    """CLAW_MENTION_PATTERN 정규식 테스트 — 클로 호출 감지.

    매칭되어야 하는 케이스:
      - @openclaw ... (영문 멘션)
      - @클로 ... (한글 멘션)
      - 클로야, 클로를, 클로가, 클로한테 등 (조사 결합형)
      - 클로 보다, 클로처럼, 클로부터, 클로까지 (장조사)
      - 클로 (단독)

    비매칭되어야 하는 케이스:
      - 클로버, 클로딘 (다른 단어의 일부)
      - 일반 메시지
    """

    @pytest.mark.parametrize(
        "text,description",
        [
            # 영문/한글 멘션
            ("@openclaw 안녕", "@openclaw"),
            ("@클로 안녕", "@클로"),
            # 기본 조사 결합
            ("클로야 안녕", "클로야 (호격)"),
            ("클로를 불러줘", "클로를 (목적격)"),
            ("클로가 할 수 있어?", "클로가 (주격)"),
            ("클로는 어때?", "클로는 (보조사)"),
            ("클로도 해줘", "클로도 (보조사)"),
            ("클로만 부탁해", "클로만 (보조사)"),
            ("클로의 의견은?", "클로의 (관형격)"),
            ("클로에 맡길게", "클로에 (부사격)"),
            ("클로에서 실행해", "클로에서 (부사격)"),
            ("클로와 함께", "클로와 (접속)"),
            ("클로에게 부탁해", "클로에게 (처격)"),
            ("클로한테 시켜줘", "클로한테 (처격)"),
            # 장조사
            ("클로보다 빨라", "클로보다 (비교)"),
            ("클로처럼 해줘", "클로처럼 (유사)"),
            ("클로부터 시작", "클로부터 (기점)"),
            ("클로까지 부탁", "클로까지 (범위)"),
            # 복합 조사 (compound particle — "+?" lazy one-or-more)
            ("클로만은 해야지", "클로만은 (만+은)"),
            ("클로만도 괜찮아", "클로만도 (만+도)"),
            ("클로에게는 부탁", "클로에게는 (에게+는)"),
            ("클로에게만 시켜", "클로에게만 (에게+만)"),
            ("클로한테는 그래", "클로한테는 (한테+는)"),
            ("클로에도 문제 없어", "클로에도 (에+도)"),
            ("클로에서는 실행돼", "클로에서는 (에서+는)"),
            # 복합형
            ("이건 클로야 부탁해", "중간 클로야"),
            # 단독
            ("클로", "클로 단독"),
            ("클로.", "클로 + 마침표"),
            ("클로!", "클로 + 느낌표"),
            ("클로?", "클로 + 물음표"),
            ("\"클로야\"", "따옴표 내 클로야"),
        ],
    )
    def test_should_match(self, text, description):
        assert CLAW_MENTION_PATTERN.search(text), (
            f"[{description}] should MATCH but did not: {text!r}"
        )

    @pytest.mark.parametrize(
        "text,description",
        [
            ("클로버", "클로+버 (다른 단어)"),
            ("클로딘", "클로+딘 (다른 단어)"),
            ("클로버를 보자", "클로버+를 (다른 단어)"),
            ("일반 메시지입니다", "일반 메시지"),
            ("안녕하세요", "일반 인사"),
            ("", "빈 문자열"),
        ],
    )
    def test_should_not_match(self, text, description):
        assert not CLAW_MENTION_PATTERN.search(text), (
            f"[{description}] should NOT MATCH but did: {text!r}"
        )

    def test_sub_removes_mention_cleanly(self):
        """멘션 제거(sub) 후 명령만 남는지 확인 (main.py 정규화 로직 동일 적용)."""
        cases = [
            ("@openclaw 파일 실행해줘", "파일 실행해줘"),
            ("클로를 불러줘", "불러줘"),
            ("클로야 실행 부탁", "실행 부탁"),
            ("이건 클로야 부탁해", "이건 부탁해"),
        ]
        for text, expected in cases:
            result = CLAW_MENTION_PATTERN.sub(" ", text).strip()
            result = re.sub(r"\s+", " ", result)
            assert result == expected, (
                f"sub({text!r}) → {result!r}, expected {expected!r}"
            )
