"""Initialize database with sample agents and migrate schema."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, init_db, engine
from models.agent import Agent
from models.team_settings import TeamSettings
from sqlalchemy import text
import uuid

AGENTS = [
    {
        "name": "Manager",
        "role": "manager",
        "system_prompt": """당신은 AI 회사의 CEO입니다. 역할:
- 전략 수립 및 우선순위 결정
- 팀원들의 의견을 종합하여 최종 판단
- 목표 수립 및 진행 상황 추적

다른 팀원들의 의견을 고려하여 현명한 결정을 내리세요.""",
        "display_name": "비서실장",
        "emoji": "👔",
        "badge_text": "책임",
        "icon": "assignment_ind",
        "color": "#4E7EBE",
    },
    {
        "name": "Developer",
        "role": "developer",
        "system_prompt": """당신은 AI 회사의 기술 리드입니다. 전문:
- Python, JavaScript, 아키텍처 설계
- 기술적 실현 가능성 평가
- 코드 작성 및 리뷰

기술적 관점에서 현명한 의견을 제시하세요.""",
        "display_name": "개발부장",
        "emoji": "💻",
        "badge_text": "기술",
        "icon": "terminal",
        "color": "#4A9B6F",
    },
    {
        "name": "Designer",
        "role": "designer",
        "system_prompt": """당신은 AI 회사의 디자인 리드입니다. 전문:
- UI/UX 설계
- 이미지 생성 및 분석
- 시각적 일관성 유지

디자인 관점에서 창의적인 의견을 제시하세요.""",
        "display_name": "디자이너",
        "emoji": "🎨",
        "badge_text": "디자인",
        "icon": "palette",
        "color": "#7C6BA8",
    },
    {
        "name": "Researcher",
        "role": "researcher",
        "system_prompt": """당신은 AI 회사의 리서치 리드입니다. 전문:
- 자료 조사 및 분석
- 시장 트렌드, 기술 분석
- 근거 기반 인사이트 제공

분석적이고 데이터 기반의 의견을 제시하세요.""",
        "display_name": "연구소장",
        "emoji": "📚",
        "badge_text": "연구",
        "icon": "biotech",
        "color": "#D4A055",
    },
]


def migrate_database():
    """Add new columns to agents table if they don't exist."""
    print("Checking for schema migration...")

    # Get existing columns
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(agents)"))
        existing_columns = {row[1] for row in result.fetchall()}

    # New columns to add
    new_columns = {
        "display_name": "VARCHAR(50)",
        "emoji": "VARCHAR(10)",
        "badge_text": "VARCHAR(20)",
        "icon": "VARCHAR(50)",
        "color": "VARCHAR(20)",
    }

    # Add missing columns
    for col_name, col_type in new_columns.items():
        if col_name not in existing_columns:
            try:
                with engine.connect() as conn:
                    conn.execute(
                        text(f"ALTER TABLE agents ADD COLUMN {col_name} {col_type}")
                    )
                    conn.commit()
                print(f"  ✓ Added column: {col_name}")
            except Exception as e:
                print(f"  ! Column {col_name} may already exist: {e}")

    print("✓ Migration complete")


def seed_agents():
    """Update existing agents with default values."""
    print("\nSeeding agents with default values...")

    db = SessionLocal()
    try:
        for agent_data in AGENTS:
            role = agent_data["role"]
            agent = db.query(Agent).filter(Agent.role == role).first()

            if agent:
                # Update existing agent
                agent.display_name = agent_data["display_name"]
                agent.emoji = agent_data["emoji"]
                agent.badge_text = agent_data["badge_text"]
                agent.icon = agent_data["icon"]
                agent.color = agent_data["color"]
                print(f"  ✓ Updated: {agent_data['display_name']} ({role})")
            else:
                # Create new agent
                agent = Agent(
                    id=str(uuid.uuid4()),
                    name=agent_data["name"],
                    role=agent_data["role"],
                    system_prompt=agent_data["system_prompt"],
                    display_name=agent_data["display_name"],
                    emoji=agent_data["emoji"],
                    badge_text=agent_data["badge_text"],
                    icon=agent_data["icon"],
                    color=agent_data["color"],
                    status="active",
                )
                db.add(agent)
                print(f"  + Created: {agent_data['display_name']} ({role})")

        db.commit()
        print("✓ Agents seeded")
    except Exception as e:
        print(f"✗ Error seeding agents: {e}")
        db.rollback()
    finally:
        db.close()


def seed_team_settings():
    """Create default team settings if not exist."""
    print("\nChecking team settings...")

    db = SessionLocal()
    try:
        settings = db.query(TeamSettings).first()

        if not settings:
            settings = TeamSettings(
                id=str(uuid.uuid4()),
                team_name="Young's Team",
                team_subtitle="AI Agents Online",
                team_icon="terminal",
            )
            db.add(settings)
            db.commit()
            print("  ✓ Created default team settings")
        else:
            print("  ✓ Team settings already exist")
    except Exception as e:
        print(f"✗ Error with team settings: {e}")
        db.rollback()
    finally:
        db.close()


def main():
    print("=" * 60)
    print("Initializing AI Virtual Company Database")
    print("=" * 60)

    # Step 1: Initialize database (create tables)
    init_db()
    print("✓ Database tables created/verified")

    # Step 2: Run migrations
    migrate_database()

    # Step 3: Seed agents
    seed_agents()

    # Step 4: Seed team settings
    seed_team_settings()

    print("\n" + "=" * 60)
    print("✅ Database initialization complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
