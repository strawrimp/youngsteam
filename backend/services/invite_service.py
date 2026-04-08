"""에이전트 초대 서비스 - 승인/거부 처리 및 알림

Phase 3A: 하이브리드 초대 시스템
- 초대 제안 발행
- 승인/거부 처리
- @멘션 즉시 초대
"""

import logging
from typing import Optional, Set
from sqlalchemy.orm import Session

from models.agent import Agent
from models.project import Project
from engines.invite_engine import InviteEngine, InviteSuggestion
from services.binding_service import BindingService
from websocket.events import EventType, create_event

logger = logging.getLogger(__name__)


class InviteService:
    """에이전트 초대 관리 서비스"""

    @staticmethod
    async def suggest_invite(
        db: Session, project_id: str, suggestion: InviteSuggestion, ws_manager=None
    ) -> bool:
        """초대 제안 발행

        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            suggestion: 초대 제안 데이터
            ws_manager: WebSocket 관리자

        Returns:
            발행 성공 여부
        """
        try:
            # 에이전트 정보 조회
            agent = (
                db.query(Agent)
                .filter(Agent.role == suggestion.suggested_agent_role)
                .first()
            )

            if not agent:
                logger.warning(f"Agent not found: {suggestion.suggested_agent_role}")
                return False

            # WebSocket 이벤트 발행
            if ws_manager:
                event = create_event(
                    EventType.INVITE_SUGGESTED,
                    {
                        "project_id": project_id,
                        "agent_id": agent.id,
                        "agent_name": agent.name,
                        "agent_role": agent.role,
                        "agent_display_name": agent.display_name,
                        "agent_emoji": agent.emoji,
                        "reason": suggestion.reason,
                        "triggered_by": suggestion.triggered_by,
                        "confidence": suggestion.confidence,
                    },
                )
                await ws_manager.broadcast_to_project(project_id, event)

            logger.info(
                f"Invite suggested: {agent.name} to project {project_id} "
                f"(trigger: {suggestion.triggered_by})"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to suggest invite: {e}")
            return False

    @staticmethod
    async def accept_invite(
        db: Session, project_id: str, agent_id: str, ws_manager=None
    ) -> bool:
        """초대 승인 및 에이전트 바인딩

        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            agent_id: 에이전트 ID
            ws_manager: WebSocket 관리자

        Returns:
            승인 성공 여부
        """
        try:
            # 바인딩 생성 (BindingService 사용)
            binding = BindingService.bind_agent_with_validation(
                db=db,
                project_id=project_id,
                agent_id=agent_id,
                is_lead=False,  # 초대된 에이전트는 기본적으로 일반 멤버
                ws_manager=ws_manager,
            )

            if not binding:
                logger.warning(
                    f"Failed to bind agent {agent_id} to project {project_id}"
                )
                return False

            # 승인 이벤트 발행
            if ws_manager:
                agent = db.query(Agent).filter(Agent.id == agent_id).first()
                event = create_event(
                    EventType.INVITE_ACCEPTED,
                    {
                        "project_id": project_id,
                        "agent_id": agent_id,
                        "agent_name": agent.name if agent else "Unknown",
                        "binding_id": binding.id,
                    },
                )
                await ws_manager.broadcast_to_project(project_id, event)

            logger.info(
                f"Invite accepted: agent {agent_id} joined project {project_id}"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to accept invite: {e}")
            return False

    @staticmethod
    async def reject_invite(
        db: Session, project_id: str, agent_id: str, ws_manager=None
    ) -> bool:
        """초대 거부

        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            agent_id: 에이전트 ID
            ws_manager: WebSocket 관리자

        Returns:
            거부 처리 성공 여부
        """
        try:
            # 거부 이벤트 발행
            if ws_manager:
                agent = db.query(Agent).filter(Agent.id == agent_id).first()
                event = create_event(
                    EventType.INVITE_REJECTED,
                    {
                        "project_id": project_id,
                        "agent_id": agent_id,
                        "agent_name": agent.name if agent else "Unknown",
                    },
                )
                await ws_manager.broadcast_to_project(project_id, event)

            logger.info(f"Invite rejected: agent {agent_id} for project {project_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to reject invite: {e}")
            return False

    @staticmethod
    async def handle_mention(
        db: Session, project_id: str, agent_id: str, ws_manager=None
    ) -> bool:
        """@멘션 즉시 초대 처리

        @멘션은 사용자 의도가 명확하므로 바로 바인딩

        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            agent_id: 에이전트 ID
            ws_manager: WebSocket 관리자

        Returns:
            초대 성공 여부
        """
        try:
            # 에이전트 조회
            agent = db.query(Agent).filter(Agent.id == agent_id).first()
            if not agent:
                logger.warning(f"Agent not found: {agent_id}")
                return False

            # 멘션 알림 이벤트 발행
            if ws_manager:
                event = create_event(
                    EventType.AGENT_MENTIONED,
                    {
                        "project_id": project_id,
                        "agent_id": agent_id,
                        "agent_name": agent.name,
                        "agent_display_name": agent.display_name,
                    },
                )
                await ws_manager.broadcast_to_project(project_id, event)

            # 즉시 바인딩 (승인 절차 없음)
            binding = BindingService.bind_agent_with_validation(
                db=db,
                project_id=project_id,
                agent_id=agent_id,
                is_lead=False,
                ws_manager=ws_manager,
            )

            if binding:
                logger.info(
                    f"Agent {agent_id} mentioned and bound to project {project_id}"
                )
                return True
            else:
                # 이미 바인딩된 경우도 성공으로 처리
                logger.info(f"Agent {agent_id} already bound to project {project_id}")
                return True

        except Exception as e:
            logger.error(f"Failed to handle mention: {e}")
            return False

    @staticmethod
    def get_project_agents_set(db: Session, project_id: str) -> Set[str]:
        """프로젝트에 참여 중인 에이전트 ID 집합 반환

        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID

        Returns:
            에이전트 ID 집합
        """
        bindings = BindingService.get_project_bindings_with_agents(db, project_id)
        return {b["agent_id"] for b in bindings}

    @staticmethod
    async def process_message_for_invites(
        db: Session,
        project_id: str,
        message: str,
        sender_role: Optional[str] = None,
        ws_manager=None,
    ) -> int:
        """메시지 분석하여 자동 초대 제안/처리

        Args:
            db: 데이터베이스 세션
            project_id: 프로젝트 ID
            message: 분석할 메시지
            sender_role: 발신자 역할
            ws_manager: WebSocket 관리자

        Returns:
            처리된 초대 수
        """
        # 현재 참여 중인 에이전트 조회
        project_agents = InviteService.get_project_agents_set(db, project_id)

        # 메시지 분석
        suggestions = InviteEngine.analyze_message_for_invites(
            message=message, project_agents=project_agents, sender_role=sender_role
        )

        processed_count = 0

        for suggestion in suggestions:
            if suggestion.triggered_by == "mention":
                # @멘션은 즉시 초대
                # 에이전트 ID로 변환 (role → id)
                agent = (
                    db.query(Agent)
                    .filter(Agent.role == suggestion.suggested_agent_role)
                    .first()
                )

                if agent:
                    success = await InviteService.handle_mention(
                        db=db,
                        project_id=project_id,
                        agent_id=agent.id,
                        ws_manager=ws_manager,
                    )
                    if success:
                        processed_count += 1

            else:
                # 키워드 기반은 제안만 발행
                success = await InviteService.suggest_invite(
                    db=db,
                    project_id=project_id,
                    suggestion=suggestion,
                    ws_manager=ws_manager,
                )
                if success:
                    processed_count += 1

        return processed_count
