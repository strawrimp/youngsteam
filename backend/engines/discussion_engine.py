"""Discussion Engine - 에이전트 간 토론 관리

Phase 3C: 사이드 토론 패널 (백엔드)
토론 시나리오:
1. 사용자 또는 Manager가 특정 주제에 대해 토론 세션 생성 요 2. Manager가 토론에 참여할 에이전트들을4. 토론이 진행되면서 새 메시지가 추가되5. 토론 종료 시, Manager가 결과를 메인 채팅에 전달
6. 필요시 투표 시스템을 통해 투표로 최종 결정 내 내"""

from typing import List, Dict, Optional, Set
from datetime import datetime
from sqlalchemy.orm import Session

from models.discussion import Discussion, DiscussionMessage


class DiscussionEngine:
    """토론 엔진 - 에이전트 간 토론 관리"""

    def __init__(self, db: Session):
        self.db = db
        self.active_discussions: Dict[
            int, Discussion
        ] = {}  # discussion_id -> Discussion

    async def create_discussion(
        self,
        project_id: str,
        topic: str,
        participant_ids: List[str],
        max_round: Optional[int] = 3,
    ) -> Discussion:
        """
        새 토론 세션 생성

        Args:
            project_id: 프로젝트 ID
            topic: 토론 주제
            participant_ids: 참여할 에이전트 ID 목록
            max_round: 최대 라운드 수 (기본: 3)

        Returns:
            생성된 Discussion 객체
        """
        # 토론 생성
        discussion = Discussion(
            project_id=project_id,
            topic=topic,
            status="active",
            created_at=datetime.utcnow(),
        )

        self.db.add(discussion)
        self.db.commit()
        self.db.refresh()

        # 참여자 추가
        for agent_id in participant_ids:
            agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
            if agent:
                discussion.participants.append(agent)

        self.active_discussions[discussion.id] = discussion
        return discussion

    async def add_message(
        self,
        discussion_id: int,
        agent_id: str,
        content: str,
    ) -> DiscussionMessage:
        """
        토론에 메시지 추가

        Args:
            discussion_id: 토론 ID
            agent_id: 에이전트 ID
            content: 메시지 내용
        """
        # 토론 조회
        discussion = self.active_discussions.get(discussion_id)
        if not discussion:
            raise ValueError(f"Discussion {discussion_id} not found")

        # 에이전트 조회
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        # 메시지 생성
        message = DiscussionMessage(
            discussion_id=discussion_id,
            agent_id=agent_id,
            content=content,
            created_at=datetime.utcnow(),
        )

        self.db.add(message)
        self.db.commit()
        self.db.refresh()

        return message

    async def get_discussion_messages(
        self, discussion_id: int, limit: int = 50
    ) -> List[DiscussionMessage]:
        """
        토론 메시지 목록 조회

        Args:
            discussion_id: 토론 ID
            limit: 조회할 메시지 수 (기본 50)

        Returns:
            메시지 목록
        """
        messages = (
            self.db.query(DiscussionMessage)
            .filter(DiscussionMessage.discussion_id == discussion_id)
            .order_by(DiscussionMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        return messages

    async def end_discussion(
        self,
        discussion_id: int,
        result: Optional[str] = None,
    ) -> Discussion:
        """
        토론 종료

        Args:
            discussion_id: 토론 ID
            result: 토론 결과 요약 (선택사항)

        Returns:
            종료된 Discussion 객체
        """
        discussion = self.active_discussions.get(discussion_id)
        if not discussion:
            raise ValueError(f"Discussion {discussion_id} not found")

        discussion.status = "closed"
        discussion.closed_at = datetime.utcnow()

        if result:
            discussion.result = result

        self.db.commit()
        self.db.refresh()

        # 활성 토론 목록에서 제거
        del self.active_discussions[discussion_id]

        return discussion

    def get_active_discussion(self, discussion_id: int) -> Optional[Discussion]:
        """
        활성 토론 조회

        Args:
            discussion_id: 토론 ID

        Returns:
            Discussion | None
        """
        return self.active_discussions.get(discussion_id)

    def get_project_discussions(
        self, project_id: str, status: Optional[str] = None
    ) -> List[Discussion]:
        """
        프로젝트의 토론 목록 조회

        Args:
            project_id: 프로젝트 ID
            status: 상태 필터 ('active', 'closed')

        Returns:
            토론 목록
        """
        query = self.db.query(Discussion).filter(Discussion.project_id == project_id)
        if status:
            query = query.filter(Discussion.status == status)

        query = query.order_by(Discussion.created_at.desc()).all()

        return query.all()
