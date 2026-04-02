"""Initialize database with sample agents."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import SessionLocal, init_db
from models.agent import Agent
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
    },
    {
        "name": "Developer",
        "role": "developer",
        "system_prompt": """당신은 AI 회사의 기술 리드입니다. 전문:
- Python, JavaScript, 아키텍처 설계
- 기술적 실현 가능성 평가
- 코드 작성 및 리뷰

기술적 관점에서 현명한 의견을 제시하세요.""",
    },
    {
        "name": "Designer",
        "role": "designer",
        "system_prompt": """당신은 AI 회사의 디자인 리드입니다. 전문:
- UI/UX 설계
- 이미지 생성 및 분석
- 시각적 일관성 유지

디자인 관점에서 창의적인 의견을 제시하세요.""",
    },
    {
        "name": "Researcher",
        "role": "researcher",
        "system_prompt": """당신은 AI 회사의 리서치 리드입니다. 전문:
- 자료 조사 및 분석
- 시장 트렌드, 기술 분석
- 근거 기반 인사이트 제공

분석적이고 데이터 기반의 의견을 제시하세요.""",
    },
]


def main():
    """Initialize database with agents."""
    try:
        init_db()
        print("✓ Database tables created")

        db = SessionLocal()

        # Check if agents already exist
        existing_agents = db.query(Agent).count()
        if existing_agents > 0:
            print(f"✓ Agents already initialized ({existing_agents} agents found)")
            db.close()
            return

        # Create agents
        for agent_data in AGENTS:
            agent = Agent(
                id=uuid.uuid4(),
                **agent_data,
            )
            db.add(agent)
            print(f"+ Added agent: {agent.name} ({agent.role})")

        db.commit()
        print(f"✓ Successfully initialized {len(AGENTS)} agents")
        db.close()

    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
