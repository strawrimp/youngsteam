"""에이전트 초대 시스템 테스트

Phase 3A: 하이브리드 초대 시스템
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from engines.invite_engine import InviteEngine, AgentRole, InviteSuggestion
from services.invite_service import InviteService
from models.agent import Agent
from models.project import Project
from models.project_agent import ProjectAgent


from websocket.events import EventType


@pytest.fixture
def mock_db():
    """Mock 데이터베이스 세션"""
    return MagicMock()


@pytest.fixture
def mock_ws_manager():
    """Mock WebSocket 관리자"""
    return AsyncMock()


class TestInviteEngine:
    """InviteEngine 테스트"""

    def test_detect_keywords_developer(self):
        """개발자 키워드 감지 테스트"""
        message = "API 개발이 필요해요. 백엔드 코드를 작성해주세요."
        suggestions = InviteEngine.detect_keywords(message)

        assert len(suggestions) == 1
        assert suggestions[0].suggested_agent_role == AgentRole.DEVELOPER
        assert "api" in suggestions[0].keywords_matched
        assert suggestions[0].triggered_by == "keyword"

        assert suggestions[0].confidence > 0

    def test_detect_keywords_designer(self):
        """디자이너 키워드 감지 테스트"""
        message = "UI/UX 디자인을 개선하고 싶어"
        suggestions = InviteEngine.detect_keywords(message)

        assert len(suggestions) == 1
        assert suggestions[0].suggested_agent_role == AgentRole.DESIGNER
        assert "디자인" in suggestions[0].keywords_matched

        assert "ui" in suggestions[0].keywords_matched
        assert "ux" in suggestions[0].keywords_matched

        assert suggestions[0].confidence > 0

        assert suggestions[0].triggered_by == "keyword"

    def test_detect_keywords_researcher(self):
        """리서처 키워드 감지 테스트"""
        message = "시장 조사와 데이터 분석이 필요합니다."
        suggestions = InviteEngine.detect_keywords(message)

        assert len(suggestions) == 1
        assert suggestions[0].suggested_agent_role == AgentRole.RESEARCHER
        assert "조사" in suggestions[0].keywords_matched
        assert "분석" in suggestions[0].keywords_matched
        assert suggestions[0].confidence > 0

        assert suggestions[0].triggered_by == "keyword"

    def test_detect_keywords_exclude_agents(self):
        """이미 참여 중인 에이전트 제외 테스트"""
        message = "API 개발이 필요해요."
        exclude = {AgentRole.DEVELOPER}
        suggestions = InviteEngine.detect_keywords(message, exclude)

        # Developer는 이미 참여 중이므로 제안에서 제외
        assert AgentRole.DEVELOPER not in [s.suggested_agent_role for s in suggestions]

    def test_detect_keywords_no_match(self):
        """매칭되는 키워드 없음 테스트"""
        message = "안녕하세요! 오늘 날씨가 좋네요."
        suggestions = InviteEngine.detect_keywords(message)

        assert len(suggestions) == 0

    def test_parse_mentions_single(self):
        """단일 @멘션 파싱 테스트"""
        message = "@developer API를 수정해주세요."
        mentions = InviteEngine.parse_mentions(message)

        assert len(mentions) == 1
        assert mentions[0] == "developer"

    def test_parse_mentions_multiple(self):
        """다중 @멘션 파싱 테스트"""
        message = "@developer @designer 협업이 필요해요."
        mentions = InviteEngine.parse_mentions(message)

        assert len(mentions) == 2
        assert "developer" in mentions
        assert "designer" in mentions

    def test_parse_mentions_invalid(self):
        """유효하지 않은 멘션은 무시"""
        message = "@unknown @invalid_mention 테스트"
        mentions = InviteEngine.parse_mentions(message)

        assert len(mentions) == 0

    def test_can_suggest_invite_lead_only(self):
        """선임에이전트만 제안 권한 있음"""
        assert InviteEngine.can_suggest_invite("manager") is True
        assert InviteEngine.can_suggest_invite("developer") is False
        assert InviteEngine.can_suggest_invite("designer") is False

        assert InviteEngine.can_suggest_invite("researcher") is False

    def test_create_mention_suggestions(self):
        """@멘션 기반 제안 생성 테스트"""
        mentioned = ["developer", "designer"]
        suggestions = InviteEngine.create_mention_suggestions(mentioned)

        assert len(suggestions) == 2
        assert suggestions[0].suggested_agent_role == "developer"
        assert suggestions[0].triggered_by == "mention"
        assert suggestions[0].confidence == 1.0

        assert suggestions[1].suggested_agent_role == "designer"
        assert suggestions[1].triggered_by == "mention"
        assert suggestions[1].confidence == 1.0

        assert suggestions[0].reason == "@developer 멘션으로 호출됨"
        assert suggestions[1].reason == "@designer 멘션으로 호출됨"

    def test_create_mention_suggestions_exclude(self):
        """이미 참여 중인 에이전트 제외 테스트"""
        mentioned = ["developer", "designer"]
        exclude = {"developer"}
        suggestions = InviteEngine.create_mention_suggestions(mentioned, exclude)

        assert len(suggestions) == 1
        assert suggestions[0].suggested_agent_role == "designer"

        assert AgentRole.DEVELOPER not in [s.suggested_agent_role for s in suggestions]

    def test_analyze_message_for_invites_keywords_only(self):
        """키워드 기반 분석 테스트"""
        message = "API 개발이 필요해요. 코드를 작성해주세요."
        project_agents = set()
        suggestions = InviteEngine.analyze_message_for_invites(
            message=message, project_agents=project_agents, sender_role="manager"
        )

        # Manager는 선임에이전트이므로 키워드 기반 제안 포함
        assert len(suggestions) == 1
        assert suggestions[0].suggested_agent_role == AgentRole.DEVELOPER
        assert suggestions[0].triggered_by == "keyword"

    def test_analyze_message_for_invites_mention(self):
        """@멘션 기반 분석 테스트"""
        message = "@developer @designer 도와해주세요."
        project_agents = set()
        suggestions = InviteEngine.analyze_message_for_invites(
            message=message, project_agents=project_agents, sender_role="manager"
        )

        # @멘션은 선임에이전트 권한 없이 작동
        assert len(suggestions) == 2
        mention_suggestions = [s for s in suggestions if s.triggered_by == "mention"]
        assert len(mention_suggestions) == 2
        assert mention_suggestions[0].suggested_agent_role == "developer"
        assert mention_suggestions[1].suggested_agent_role == "designer"
        assert all(s.confidence == 1.0 for s in mention_suggestions)

    def test_analyze_message_for_invites_no_permission(self):
        """선임에이전트가 아닌 경우 키워드 제안 없음"""
        message = "API 개발이 필요해요."
        project_agents = set()
        suggestions = InviteEngine.analyze_message_for_invites(
            message=message,
            project_agents=project_agents,
            sender_role="developer",  # Developer는 선임에이전트가 아님
        )

        # 키워드 기반 제안이 없어야 함
        assert len(suggestions) == 0

    def test_analyze_message_for_invites_exclude_existing(self):
        """이미 참여 중인 에이전트 제외 테스트"""
        message = "API 개발이 필요해요. @designer도 필요해요."
        project_agents = {AgentRole.DEVELOPER}
        suggestions = InviteEngine.analyze_message_for_invites(
            message=message, project_agents=project_agents, sender_role="manager"
        )

        # Developer는 이미 참여 중이므로 제안에서 제외
        assert AgentRole.DEVELOPER not in [s.suggested_agent_role for s in suggestions]
        # Designer는 제안에 포함됨
        assert any(s.suggested_agent_role == AgentRole.DESIGNER for s in suggestions)

        designer_suggestion = next(
            s for s in suggestions if s.suggested_agent_role == AgentRole.DESIGNER
        )
        # @designer는 mention이므로 mention이 맞음
        assert designer_suggestion.triggered_by == "mention"

    def test_get_agent_display_name(self):
        """에이전트 표시명 반환 테스트"""
        assert InviteEngine._get_agent_display_name("manager") == "Manager"
        assert InviteEngine._get_agent_display_name("developer") == "Developer"
        assert InviteEngine._get_agent_display_name("designer") == "Designer"
        assert InviteEngine._get_agent_display_name("researcher") == "Researcher"
        assert InviteEngine._get_agent_display_name("unknown") == "Unknown"

    def test_generate_reason_developer(self):
        """개발자 초대 사유 생성 테스트"""
        reason = InviteEngine._generate_reason(
            AgentRole.DEVELOPER, ["api", "코드", "개발"]
        )

        assert "개발 관련 키워드 감지" in reason
        assert "api" in reason
        assert "코드" in reason

        assert "개발" in reason


class TestInviteService:
    """InviteService 테스트"""

    @pytest.mark.asyncio
    async def test_suggest_invite_success(self, mock_db, mock_ws_manager):
        """초대 제안 발행 성공 테스트"""
        # Mock 에이전트
        mock_agent = MagicMock()
        mock_agent.id = "test-agent-id"
        mock_agent.name = "Test Agent"
        mock_agent.role = "developer"
        mock_agent.display_name = "Developer"
        mock_agent.emoji = "👨‍💻"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_agent

        # Mock WebSocket 이벤트
        mock_ws_manager.broadcast_to_project = AsyncMock()

        suggestion = InviteSuggestion(
            suggested_agent_id="test-agent-id",
            suggested_agent_name="Developer",
            suggested_agent_role="developer",
            reason="개발 관련 키워드 감지: api, 코드",
            triggered_by="keyword",
            keywords_matched=["api", "코드"],
            confidence=0.8,
        )

        success = await InviteService.suggest_invite(
            db=mock_db,
            project_id="test-project-id",
            suggestion=suggestion,
            ws_manager=mock_ws_manager,
        )

        assert success is True
        mock_ws_manager.broadcast_to_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_accept_invite_success(self, mock_db, mock_ws_manager):
        """초대 승인 성공 테스트"""
        # Mock BindingService
        with patch("services.invite_service.BindingService") as mock_binding_service:
            mock_binding = MagicMock()
            mock_binding.id = "test-binding-id"
            mock_binding_service.bind_agent_with_validation = MagicMock(
                return_value=mock_binding
            )

            success = await InviteService.accept_invite(
                db=mock_db,
                project_id="test-project-id",
                agent_id="test-agent-id",
                ws_manager=mock_ws_manager,
            )

            assert success is True
            mock_binding_service.bind_agent_with_validation.assert_called_once()

            # WebSocket 이벤트 발행 확인
            mock_ws_manager.broadcast_to_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_invite_success(self, mock_db, mock_ws_manager):
        """초대 거부 성공 테스트"""
        mock_ws_manager.broadcast_to_project = AsyncMock()

        success = await InviteService.reject_invite(
            db=mock_db,
            project_id="test-project-id",
            agent_id="test-agent-id",
            ws_manager=mock_ws_manager,
        )

        assert success is True
        mock_ws_manager.broadcast_to_project.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_mention_success(self, mock_db, mock_ws_manager):
        """@멘션 처리 성공 테스트"""
        # Mock 에이전트
        mock_agent = MagicMock()
        mock_agent.id = "test-agent-id"
        mock_agent.name = "Developer"
        mock_agent.role = "developer"
        mock_agent.display_name = "Developer"

        mock_db.query.return_value.filter.return_value.first.return_value = mock_agent

        # Mock BindingService
        with patch("services.invite_service.BindingService") as mock_binding_service:
            mock_binding = MagicMock()
            mock_binding.id = "test-binding-id"
            mock_binding_service.bind_agent_with_validation = MagicMock(
                return_value=mock_binding
            )
            mock_binding_service.get_project_bindings_with_agents = MagicMock(
                return_value=[]
            )

            success = await InviteService.handle_mention(
                db=mock_db,
                project_id="test-project-id",
                agent_id="test-agent-id",
                ws_manager=mock_ws_manager,
            )

            assert success is True

    def test_get_project_agents_set(self, mock_db):
        """프로젝트 참여 에이전트 집합 조회 테스트"""
        with patch("services.invite_service.BindingService") as mock_binding_service:
            mock_binding_service.get_project_bindings_with_agents = MagicMock(
                return_value=[
                    {"agent_id": "agent-1"},
                    {"agent_id": "agent-2"},
                ]
            )

            result = InviteService.get_project_agents_set(mock_db, "test-project-id")

            assert result == {"agent-1", "agent-2"}

    @pytest.mark.asyncio
    async def test_process_message_for_invites(self, mock_db, mock_ws_manager):
        """메시지 분석 및 초대 처리 테스트"""
        # Mock 설정
        with patch("services.invite_service.InviteService") as mock_service:
            mock_service.get_project_agents_set = MagicMock(return_value=set())
            mock_service.suggest_invite = AsyncMock(return_value=True)
            mock_service.handle_mention = AsyncMock(return_value=True)

            count = await InviteService.process_message_for_invites(
                db=mock_db,
                project_id="test-project-id",
                message="@developer API 개발이 필요해요.",
                sender_role="manager",
                ws_manager=mock_ws_manager,
            )

            assert count == 1  # @멘션 1개


if __name__ == "__main__":
    pytest.main()
