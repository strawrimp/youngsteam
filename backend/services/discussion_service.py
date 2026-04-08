"""Discussion Service - 토론 메시지 저장 및 요약

Phase 3C: 사이드 토론 패널 (백엔드)
"""

from typing import List, Optional
from sqlalchemy.orm import Session
from models.discussion import Discussion, DiscussionMessage
from models.agent import Agent
from services.llm_provider_service import LLMProviderService

import logging

logger = logging.getLogger(__name__)


class DiscussionService:
    """토론 관련 비즈니스 로직"""

    def __init__(self, db: Session, llm_service: LLMProviderService):
        self.db = db
        self.llm_service = llm_service

    async def save_message(
        self, discussion_id: int, agent_id: str, content: str
    ) -> DiscussionMessage:
        """
        토론 메시지 저장

        Args:
            discussion_id: 토론 ID
            agent_id: 에이전트 ID
            content: 메시지 내용

        Returns:
            저장된 DiscussionMessage 객체
        """
        message = DiscussionMessage(
            discussion_id=discussion_id, agent_id=agent_id, content=content
        )

        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)

        logger.info(f"Message saved to discussion {discussion_id} by agent {agent_id}")

        return message

    async def get_messages(
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

        logger.info(
            f"Retrieved {len(messages)} messages for discussion {discussion_id}"
        )

        return messages

    async def summarize_discussion(
        self, discussion_id: int, requesting_agent_id: Optional[str] = None
    ) -> str:
        """
        토론 요약 생성 (LLM 기반)

        Args:
            discussion_id: 토론 ID
            requesting_agent_id: 특정 에이전트 ID 요청 (None이면 전체 요약)

        Returns:
            요약된 토론 내용
        """
        # 토론 정보 가져오기
        discussion = (
            self.db.query(Discussion).filter(Discussion.id == discussion_id).first()
        )

        if not discussion:
            logger.warning(f"Discussion {discussion_id} not found")
            return None

        # 모든 메시지 가져오기
        messages = await self.get_messages(discussion_id)

        if not messages:
            logger.warning(f"No messages found for discussion {discussion_id}")
            return None

        # 에이전트 정보 수집
        agent_info_list = []
        for msg in messages:
            if msg.agent_id and msg.agent_id != "system":
                agent_info = await self.get_agent_info(msg.agent_id)
                if agent_info:
                    agent_info_list.append(
                        f"- {agent_info['name']} ({agent_info['role']})"
                    )

        # 메시지 텍스트 생성
        messages_text = "\n\n".join(
            [f"{msg.agent_id}: {msg.content}" for msg in messages]
        )

        # 프롬프트 생성
        summary_prompt = f"""
토론 주제: {discussion.topic}
참여 에이전트:
{chr(10).join(set(agent_info_list)) if agent_info_list else "없음"}

토론 내용:
{messages_text}

위 토론에 참여한 에이전트들과 논의 내용을 요약해주세요. 
주요 논의 사항과 결론을 중요한 순서대로 정리해주세요.
"""

        # LLM으로 요약 생성
        try:
            summary = await self.llm_service.generate_response(
                summary_prompt, max_tokens=500
            )

            logger.info(f"Discussion {discussion_id} summarized by LLM")

            return summary
        except Exception as e:
            logger.error(f"Failed to summarize discussion {discussion_id}: {e}")
            # 간단한 요약 반환
            return f"토론 요약: {discussion.topic} - {len(messages)}개 메시지"

    async def get_agent_info(self, agent_id: str) -> Optional[dict]:
        """
        에이전트 정보 조회

        Args:
            agent_id: 에이전트 ID

        Returns:
            에이전트 정보 (이름, 역할 등)
        """
        agent = self.db.query(Agent).filter(Agent.id == agent_id).first()

        if not agent:
            logger.warning(f"Agent {agent_id} not found")
            return None

        return {"id": str(agent.id), "name": agent.name, "role": agent.role}
