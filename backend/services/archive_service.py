"""
ArchiveService: 대화 보관 및 자동 분류 서비스.

대화가 종료되면 Manager 에이전트가 자동으로 분류하고,
제목, 태그, 요약, 카테고리를 생성합니다.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from database import SessionLocal
from models import Conversation, Message, Agent

logger = logging.getLogger(__name__)


class ArchiveService:
    """대화 보관 및 자동 분류 서비스."""

    def __init__(self, manager_agent=None, deepseek_service=None):
        """
        Args:
            manager_agent: ManagerAgent instance for classification
            deepseek_service: DeepSeekService for LLM calls
        """
        self.manager_agent = manager_agent
        self.deepseek_service = deepseek_service

    def set_manager_agent(self, agent):
        """Manager 에이전트 설정."""
        self.manager_agent = agent
        logger.info("ArchiveService: ManagerAgent set")

    async def archive_conversation(self, conversation_id: str) -> Optional[Dict]:
        """대화를 보관하고 자동 분류합니다.

        Args:
            conversation_id: 대화 ID

        Returns:
            분류 결과 또는 None
        """
        db = SessionLocal()
        try:
            conversation = (
                db.query(Conversation)
                .filter(Conversation.id == conversation_id)
                .first()
            )
            if not conversation:
                logger.warning(f"Conversation not found: {conversation_id}")
                return None

            # 대화 메시지 조회
            messages = (
                db.query(Message)
                .filter(Message.conversation_id == conversation_id)
                .order_by(Message.created_at)
                .all()
            )

            if not messages:
                logger.info(f"No messages in conversation: {conversation_id}")
                return None

            # Manager 에이전트로 자동 분류
            msg_dicts = []
            for msg in messages:
                agent = (
                    db.query(Agent).filter(Agent.id == msg.agent_id).first()
                    if msg.agent_id
                    else None
                )
                msg_dicts.append(
                    {
                        "sender_type": msg.sender_type or "unknown",
                        "content": msg.content or "",
                        "agent_name": agent.display_name if agent else None,
                    }
                )

            classification = {
                "title": "대화",
                "tags": ["일반"],
                "summary": "",
                "category": "일반",
            }

            if self.manager_agent:
                try:
                    classification = await self.manager_agent.classify_conversation(
                        msg_dicts
                    )
                    logger.info(
                        f"[Archive] Classified: {classification.get('title', 'N/A')} "
                        f"[{classification.get('category', 'N/A')}]"
                    )
                except Exception as e:
                    logger.error(f"Classification error: {e}")

            # 대화 업데이트 — title + tags + category + summary + reference_code 모두 DB에 반영
            conversation.title = classification.get("title", "제목 없는 대화")
            conversation.category = classification.get("category", "일반")
            conversation.summary = classification.get("summary", "")
            # tags는 리스트 → JSON 문자열로 직렬화하여 저장
            tags_list = classification.get("tags", ["일반"])
            conversation.tags = json.dumps(tags_list, ensure_ascii=False)
            conversation.ended_at = datetime.now()

            # ★ 참조 코드 자동 부여 (없는 경우)
            if not conversation.reference_code:
                from services.shared_context_builder import generate_reference_code

                conversation.reference_code = generate_reference_code()
                logger.info(
                    f"[Archive] Assigned reference code: {conversation.reference_code}"
                )

            db.commit()

            logger.info(
                f"[Archive] Saved: title='{conversation.title}' "
                f"category='{conversation.category}' tags={tags_list}"
            )

            return {
                "conversation_id": conversation_id,
                "title": conversation.title,
                "tags": tags_list,
                "summary": conversation.summary,
                "category": conversation.category,
                "message_count": len(messages),
            }

        except Exception as e:
            logger.error(f"Archive error: {e}")
            db.rollback()
            return None
        finally:
            db.close()

    def get_recent_archives(self, limit: int = 50, offset: int = 0) -> Dict:
        """최근 보관된 대화 목록을 반환합니다.

        Args:
            limit: 반환할 대화 수
            offset: 오프셋

        Returns:
            {conversations: list, total: int}
        """
        db = SessionLocal()
        try:
            total = db.query(Conversation).count()
            conversations = (
                db.query(Conversation)
                .order_by(Conversation.started_at.desc())
                .limit(limit)
                .offset(offset)
                .all()
            )

            result = []
            for conv in conversations:
                msg_count = (
                    db.query(Message).filter(Message.conversation_id == conv.id).count()
                )
                result.append(
                    {
                        "id": str(conv.id),
                        "title": conv.title or "제목 없는 대화",
                        "started_at": conv.started_at.isoformat()
                        if conv.started_at
                        else None,
                        "ended_at": conv.ended_at.isoformat()
                        if conv.ended_at
                        else None,
                        "message_count": msg_count,
                    }
                )

            return {"conversations": result, "total": total}
        finally:
            db.close()

    def search_archives(self, query: str, limit: int = 20) -> List[Dict]:
        """대화 내용으로 검색합니다.

        Args:
            query: 검색어
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        db = SessionLocal()
        try:
            if len(query) < 2:
                return []

            search_term = f"%{query}%"
            messages = (
                db.query(Message)
                .filter(Message.content.ilike(search_term))
                .limit(limit * 5)
                .all()
            )

            conv_ids = list(set(m.conversation_id for m in messages))
            results = []
            for conv_id in conv_ids[:limit]:
                conv = db.query(Conversation).filter(Conversation.id == conv_id).first()
                if conv:
                    msg_count = (
                        db.query(Message)
                        .filter(Message.conversation_id == conv.id)
                        .count()
                    )
                    results.append(
                        {
                            "id": str(conv.id),
                            "title": conv.title or "제목 없는 대화",
                            "started_at": conv.started_at.isoformat()
                            if conv.started_at
                            else None,
                            "ended_at": conv.ended_at.isoformat()
                            if conv.ended_at
                            else None,
                            "message_count": msg_count,
                        }
                    )

            return results
        finally:
            db.close()
