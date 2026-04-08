"""에이전트 바인딩 서비스 - 비즈니스 로직 및 검증"""

from sqlalchemy.orm import Session
from models.project_agent import ProjectAgent
from models.agent import Agent
from models.project import Project
from websocket.events import EventType, create_event
from typing import List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BindingService:
    """에이전트 바인딩 비즈니스 로직"""

    @staticmethod
    def validate_binding(
        db: Session, project_id: str, agent_id: str
    ) -> Tuple[bool, Optional[str]]:
        """바인딩 유효성 검사

        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            agent_id: 에이전트 ID

        Returns:
            (유효 여부, 에러 메시지)
        """
        # 프로젝트 존재 확인
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            return False, "Project not found"

        # 에이전트 존재 확인
        agent = db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            return False, "Agent not found"

        # 중복 바인딩 확인
        existing = (
            db.query(ProjectAgent)
            .filter(
                ProjectAgent.project_id == project_id, ProjectAgent.agent_id == agent_id
            )
            .first()
        )

        if existing:
            return False, "Agent already bound to this project"

        return True, None

    @staticmethod
    def bind_agent_with_validation(
        db: Session,
        project_id: str,
        agent_id: str,
        is_lead: bool = False,
        ws_manager=None,
    ) -> Optional[ProjectAgent]:
        """검증 후 에이전트 바인딩

        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            agent_id: 에이전트 ID
            is_lead: 선임 에이전트 여부
            ws_manager: WebSocket 관리자 (이벤트 발행용)

        Returns:
            생성된 바인딩 (실패 시 None)
        """
        # 검증
        is_valid, error_msg = BindingService.validate_binding(db, project_id, agent_id)
        if not is_valid:
            logger.warning(f"Binding validation failed: {error_msg}")
            return None

        # 바인딩 생성
        from engines.binding_engine import BindingEngine

        binding = BindingEngine.bind_agent_to_project(
            db=db, project_id=project_id, agent_id=agent_id, is_lead=is_lead
        )

        # WebSocket 이벤트 발행
        if ws_manager:
            import asyncio

            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            event = create_event(
                EventType.AGENT_INVITED,
                {
                    "id": binding.id,
                    "project_id": project_id,
                    "agent_id": agent_id,
                    "is_lead": is_lead,
                    "agent_name": agent.name if agent else "Unknown",
                },
            )
            asyncio.create_task(ws_manager.broadcast_to_project(project_id, event))

        return binding

    @staticmethod
    def get_project_bindings_with_agents(db: Session, project_id: str) -> List[dict]:
        """프로젝트의 모든 바인딩과 에이전트 정보 조회

        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID

        Returns:
            바인딩 + 에이전트 정보 딕셔너리 목록
        """
        from sqlalchemy.orm import joinedload

        bindings = (
            db.query(ProjectAgent)
            .options(joinedload(ProjectAgent.agent))
            .filter(ProjectAgent.project_id == project_id)
            .all()
        )

        result = []
        for binding in bindings:
            result.append(
                {
                    "binding_id": binding.id,
                    "project_id": binding.project_id,
                    "agent_id": binding.agent_id,
                    "is_lead": binding.is_lead,
                    "invited_at": binding.invited_at.isoformat()
                    if binding.invited_at
                    else None,
                    "agent": {
                        "name": binding.agent.name if binding.agent else None,
                        "role": binding.agent.role if binding.agent else None,
                        "display_name": binding.agent.display_name
                        if binding.agent
                        else None,
                        "emoji": binding.agent.emoji if binding.agent else None,
                    },
                }
            )

        return result
