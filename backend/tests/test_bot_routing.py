"""Tests for bot keyword routing and auto-seed logic.

P1 이슈 검증:
  1. bot 키워드 오탐 방지 — 일반 개발 질문이 bot으로 라우팅되지 않아야 함
  2. /api/agents 빈 배열 방지 — DB가 비어도 startup auto-seed가 최소 팀을 생성함
"""

import pytest
from types import SimpleNamespace
from unittest.mock import patch

# ──────────────────────────────────────────────
#  Engine 라우팅 테스트 (pure logic, no DB)
# ──────────────────────────────────────────────


class TestBotRouting:
    """_determine_agents()의 bot 키워드 매칭 정확성 검증"""

    @pytest.fixture
    def engine(self):
        """ConversationEngine 인스턴스 + mock agent 등록."""
        from engines.conversation_engine import ConversationEngine

        eng = ConversationEngine()

        # bot agent
        bot_agent = SimpleNamespace(
            id="openclaw-bot", name="Claw", role="bot"
        )
        eng.register_agent("openclaw-bot", bot_agent)

        # 다른 역할 agents (모든 agent가 등록되어 있어야 _determine_agents가 정상 동작)
        for aid, name, role in [
            ("agent-manager", "Neo", "manager"),
            ("agent-dev", "Arthur", "developer"),
            ("agent-designer", "Sophia", "designer"),
            ("agent-researcher", "Luna", "researcher"),
        ]:
            eng.register_agent(aid, SimpleNamespace(id=aid, name=name, role=role))

        return eng

    # ========== bot SHOULD match ==========

    @pytest.mark.parametrize("msg", [
        "클로야 이거 실행해줘",
        "@클로 도와줘",
        "클로를 불러줘",
        "Claw, 터미널 명령 실행해",
        "claw 상태 알려줘",
        "@openclaw gateway 연결",
        "openclaw 도커 이미지 빌드",
        "클로에게 맡길게",
    ])
    def test_bot_should_match(self, engine, msg):
        """명시적 bot 호출은 'openclaw-bot'을 반환해야 함"""
        result = engine._determine_agents(msg)
        assert "openclaw-bot" in result, (
            f"Expected bot match for: '{msg}' — got: {result}"
        )

    # ========== bot should NOT match ==========

    @pytest.mark.parametrize("msg", [
        "이 코드 실행이 안 돼요",
        "mac에서 빌드가 깨졌어",
        "터미널 에러 좀 봐줘",
        "명령어가 뭐야 npm start?",
        "command not found 에러가 나",
        "실행 권한이 없다고 나와",
        "터미널에서 git push가 안 돼",
        "맥북에서 도커 실행하는 법",
        "개발 서버 실행 스크립트",
        "쉘 명령어 추천해줘",
    ])
    def test_bot_should_not_match(self, engine, msg):
        """일반 개발/기술 질문에는 bot이 응답하지 않아야 함"""
        result = engine._determine_agents(msg)
        assert "openclaw-bot" not in result, (
            f"False bot match for: '{msg}' — got: {result}"
        )

    # ========== developer should still match ==========

    @pytest.mark.parametrize("msg", [
        "아서야 이 코드 리뷰해줘",
        "개발자 도와줘",
        "Arthur, 기술 검토 부탁",
        "코드 최적화 방법 알려줘",
    ])
    def test_developer_still_matches(self, engine, msg):
        """개발 관련 키워드는 developer agent에 정상 매칭되어야 함"""
        result = engine._determine_agents(msg)
        assert "agent-dev" in result, (
            f"Expected developer match for: '{msg}' — got: {result}"
        )


# ──────────────────────────────────────────────
#  Seed 모듈 테스트 (in-memory SQLite)
# ──────────────────────────────────────────────


@pytest.fixture
def seed_db_session():
    """In-memory SQLite로 seed 테스트용 DB 세션 생성."""
    # 먼저 모든 모델을 임포트하여 Base.metadata에 등록
    from models.agent import Agent  # noqa: F401 — register table with Base
    from models.team_settings import TeamSettings  # noqa: F401
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from database import Base

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class TestAutoSeed:
    """ensure_agents_seeded() 동작 검증"""

    def test_seed_creates_agents_when_empty(self, seed_db_session):
        """DB가 비어 있을 때 5명의 기본 agent가 생성되어야 함"""
        from seed import ensure_agents_seeded

        # seed.SessionLocal → in-memory session으로 교체
        with patch("seed.SessionLocal", return_value=seed_db_session):
            ensure_agents_seeded()

        from models.agent import Agent
        agents = seed_db_session.query(Agent).all()
        assert len(agents) == 5, f"Expected 5 agents, got {len(agents)}"

        roles = {a.role for a in agents}
        assert roles == {"manager", "developer", "designer", "researcher", "bot"}, (
            f"Roles mismatch: {roles}"
        )

        # bot agent는 고정 ID를 가져야 함
        bot = seed_db_session.query(Agent).filter(Agent.role == "bot").first()
        assert bot is not None
        assert bot.id == "openclaw-bot"
        assert bot.name == "Claw"
        assert bot.display_name == "클로"

    def test_seed_skips_when_not_empty(self, seed_db_session):
        """이미 agent가 있으면 추가 생성하지 않아야 함"""
        from seed import ensure_agents_seeded
        from models.agent import Agent

        # 하나의 agent를 미리 생성
        existing = Agent(
            id="test-only",
            name="TestOnly",
            role="manager",
            system_prompt="test",
            status="active",
        )
        seed_db_session.add(existing)
        seed_db_session.commit()

        with patch("seed.SessionLocal", return_value=seed_db_session):
            ensure_agents_seeded()

        # 여전히 1개만 존재해야 함 (추가 생성 금지)
        count = seed_db_session.query(Agent).count()
        assert count == 1, f"Expected 1 agent (no seed), got {count}"

    def test_seed_creates_bot_with_correct_role(self, seed_db_session):
        """bot agent의 role='bot'이 정확히 설정되어야 함"""
        from seed import ensure_agents_seeded

        with patch("seed.SessionLocal", return_value=seed_db_session):
            ensure_agents_seeded()

        from models.agent import Agent
        bot = seed_db_session.query(Agent).filter(Agent.role == "bot").first()
        assert bot is not None
        assert bot.role == "bot"


# ──────────────────────────────────────────────
#  TeamSettings seed 테스트
# ──────────────────────────────────────────────


class TestTeamSettingsSeed:
    """ensure_team_settings() 동작 검증"""

    def test_creates_default_settings_when_empty(self, seed_db_session):
        """TeamSettings가 없을 때 기본값이 생성되어야 함"""
        from seed import ensure_team_settings

        with patch("seed.SessionLocal", return_value=seed_db_session):
            ensure_team_settings()

        from models.team_settings import TeamSettings
        settings = seed_db_session.query(TeamSettings).first()
        assert settings is not None
        assert settings.team_name == "Young's Team"

    def test_skips_when_exists(self, seed_db_session):
        """TeamSettings가 이미 있으면 추가 생성하지 않아야 함"""
        from seed import ensure_team_settings
        from models.team_settings import TeamSettings
        import uuid

        existing = TeamSettings(
            id=str(uuid.uuid4()),
            team_name="Custom Team",
            team_subtitle="Custom",
            team_icon="custom",
        )
        seed_db_session.add(existing)
        seed_db_session.commit()

        with patch("seed.SessionLocal", return_value=seed_db_session):
            ensure_team_settings()

        count = seed_db_session.query(TeamSettings).count()
        assert count == 1, "Should not create duplicate settings"
        assert seed_db_session.query(TeamSettings).first().team_name == "Custom Team"
