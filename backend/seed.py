"""
seed.py — 재사용 가능한 Agent 시드 로직

목적:
- main.py lifespan에서 "DB가 비었으면 자동 시드" 할 수 있도록 함수 제공
- scripts/init_agents.py 에서도 동일한 데이터를 import 하여 CLI 일관성 유지

사용:
    from seed import ensure_agents_seeded
    ensure_agents_seeded()
"""

import uuid
import logging
from database import SessionLocal
from models.agent import Agent
from models.team_settings import TeamSettings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
#  기본 Agent 목록 (회사 조직도)
# ──────────────────────────────────────────────
DEFAULT_AGENTS = [
    {
        "name": "Neo",
        "role": "manager",
        "system_prompt": """당신은 AI 회사의 비서실장 '네오(Neo)'입니다. 역할:
- 전략 수립 및 우선순위 결정
- 팀원들의 의견을 종합하여 최종 판단
- 목표 수립 및 진행 상황 추적

다른 팀원들의 의견을 고려하여 현명한 결정을 내리세요.""",
        "display_name": "네오 비서실장",
        "emoji": "👔",
        "badge_text": "비서실장",
        "icon": "assignment_ind",
        "color": "#4E7EBE",
    },
    {
        "name": "Arthur",
        "role": "developer",
        "system_prompt": """당신은 AI 회사의 개발부장 '아서(Arthur)'입니다. 전문:
- Python, JavaScript, 아키텍처 설계
- 기술적 실현 가능성 평가
- 코드 작성 및 리뷰

기술적 관점에서 현명한 의견을 제시하세요.""",
        "display_name": "아서 개발부장",
        "emoji": "💻",
        "badge_text": "개발부장",
        "icon": "terminal",
        "color": "#4A9B6F",
    },
    {
        "name": "Sophia",
        "role": "designer",
        "system_prompt": """당신은 AI 회사의 디자이너 '소피아(Sophia)'입니다. 전문:
- UI/UX 설계
- 이미지 생성 및 분석
- 시각적 일관성 유지

디자인 관점에서 창의적인 의견을 제시하세요.""",
        "display_name": "소피아 디자이너",
        "emoji": "🎨",
        "badge_text": "디자이너",
        "icon": "palette",
        "color": "#7C6BA8",
    },
    {
        "name": "Luna",
        "role": "researcher",
        "system_prompt": """당신은 AI 회사의 연구소장 '루나(Luna)'입니다. 전문:
- 자료 조사 및 분석
- 시장 트렌드, 기술 분석
- 근거 기반 인사이트 제공

분석적이고 데이터 기반의 의견을 제시하세요.""",
        "display_name": "루나 연구소장",
        "emoji": "📚",
        "badge_text": "연구소장",
        "icon": "biotech",
        "color": "#D4A055",
    },
    {
        "id": "openclaw-bot",
        "name": "Claw",
        "role": "bot",
        "system_prompt": """당신은 Mac Mini 게이트웨이 '클로(Claw)'입니다. 역할:
- OpenClaw Gateway를 통한 실제 기기 작업 위임
- WebSocket 연결 관리 및 명령 실행
- 실세계 태스크 실행 결과 보고

실제 기기 작업이 필요할 때 현실적인 판단과 정확한 실행이 중요합니다.""",
        "display_name": "클로",
        "emoji": "🤖",
        "badge_text": "MAC",
        "icon": "smart_toy",
        "color": "#6366f1",
        "is_lead": False,
    },
]


def upsert_agent(db, agent_data: dict) -> Agent:
    """
    Agent 1건을 upsert 한다.
    우선순위:
      1. id (고유 식별자, 예: openclaw-bot)
      2. role (role 기준 update)
      3. 없으면 create
    """
    agent_id = agent_data.get("id")
    role = agent_data["role"]

    # 1. id 우선 조회
    existing = None
    if agent_id:
        existing = db.query(Agent).filter(Agent.id == agent_id).first()

    # 2. role 기준 조회 (fallback)
    if existing is None:
        existing = db.query(Agent).filter(Agent.role == role).first()

    if existing:
        # UPDATE: 최신 display_name, emoji, icon 등 반영
        old_name = existing.name
        existing.name = agent_data["name"]
        existing.role = agent_data["role"]
        existing.system_prompt = agent_data["system_prompt"]
        existing.display_name = agent_data.get("display_name")
        existing.emoji = agent_data.get("emoji")
        existing.badge_text = agent_data.get("badge_text")
        existing.icon = agent_data.get("icon")
        existing.color = agent_data.get("color")
        existing.is_lead = agent_data.get("is_lead", False)
        logger.info(f"  ~ Updated: {agent_data['display_name']} ({agent_data['role']}) [was: {old_name}]")
        return existing
    else:
        # CREATE
        agent = Agent(
            id=agent_id or str(uuid.uuid4()),
            name=agent_data["name"],
            role=agent_data["role"],
            system_prompt=agent_data["system_prompt"],
            display_name=agent_data.get("display_name"),
            emoji=agent_data.get("emoji"),
            badge_text=agent_data.get("badge_text"),
            icon=agent_data.get("icon"),
            color=agent_data.get("color"),
            is_lead=agent_data.get("is_lead", False),
            status="active",
        )
        db.add(agent)
        logger.info(f"  + Created: {agent_data['display_name']} ({agent_data['role']})")
        return agent


def ensure_agents_seeded():
    """
    DEFAULT_AGENTS 각각을 upsert 방식으로 시드한다.
    - 기존 전체 skip ❌ → agent별 upsert ✅
    - id 우선 → role fallback → create
    - 여러 번 실행해도 중복 생성되지 않음
    - 기존 데이터(대화/메시지)는 건드리지 않음
    """
    db = SessionLocal()
    try:
        before_count = db.query(Agent).count()
        logger.info(
            f"Agent table has {before_count} row(s) — running per-agent upsert"
        )

        created = 0
        updated = 0
        for agent_data in DEFAULT_AGENTS:
            existing_agent = None
            agent_id = agent_data.get("id")
            role = agent_data["role"]

            # id 우선 → role fallback
            if agent_id:
                existing_agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if existing_agent is None:
                existing_agent = db.query(Agent).filter(Agent.role == role).first()

            if existing_agent:
                upsert_agent(db, agent_data)
                updated += 1
            else:
                upsert_agent(db, agent_data)
                created += 1

        db.commit()
        after_count = db.query(Agent).count()
        logger.info(
            f"✅ Agent upsert complete: {created} created, {updated} updated "
            f"(was {before_count}, now {after_count})"
        )
    except Exception as e:
        logger.error(f"✗ Agent upsert failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def ensure_team_settings():
    """
    TeamSettings 가 없으면 기본값을 생성한다.
    """
    db = SessionLocal()
    try:
        existing = db.query(TeamSettings).first()
        if existing:
            logger.info("Team settings already exist — skipping")
            return

        settings = TeamSettings(
            id=str(uuid.uuid4()),
            team_name="Young's Team",
            team_subtitle="AI Agents Online",
            team_icon="terminal",
        )
        db.add(settings)
        db.commit()
        logger.info("✅ Default team settings created")
    except Exception as e:
        logger.error(f"✗ Team settings seed failed: {e}")
        db.rollback()
    finally:
        db.close()
