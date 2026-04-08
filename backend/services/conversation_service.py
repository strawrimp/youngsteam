"""Conversation persistence service for archiving and searching conversations."""

from typing import List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_

from models.conversation import Conversation
from models.message import Message


class ConversationService:
    """Service for managing conversation persistence and retrieval."""

    def __init__(self, db: Session):
        self.db = db

    def create_conversation(
        self, conversation_id: str, title: Optional[str] = None
    ) -> Conversation:
        """Create a new conversation record."""
        conversation = Conversation(
            id=conversation_id,
            title=title,
            is_voting=False,
        )
        self.db.add(conversation)
        self.db.commit()
        self.db.refresh(conversation)
        return conversation

    def save_message(
        self,
        conversation_id: str,
        content: str,
        sender_type: str,
        agent_id: Optional[str] = None,
        message_type: str = "text",
    ) -> Message:
        """Save a message to a conversation."""
        message = Message(
            conversation_id=conversation_id,
            agent_id=agent_id,
            sender_type=sender_type,
            content=content,
            message_type=message_type,
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def update_title(self, conversation_id: str, title: str) -> Optional[Conversation]:
        """Update conversation title."""
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )
        if conversation:
            conversation.title = title[:255]  # Truncate to max length
            self.db.commit()
            self.db.refresh(conversation)
        return conversation

    def end_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """Mark conversation as ended."""
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )
        if conversation:
            conversation.ended_at = datetime.utcnow()
            self.db.commit()
            self.db.refresh(conversation)
        return conversation

    def list_conversations(
        self,
        limit: int = 50,
        offset: int = 0,
        include_ended: bool = True,
    ) -> List[Conversation]:
        """List all conversations, ordered by most recent."""
        query = self.db.query(Conversation).order_by(desc(Conversation.started_at))
        if not include_ended:
            query = query.filter(Conversation.ended_at.is_(None))
        return query.offset(offset).limit(limit).all()

    def get_conversation_detail(self, conversation_id: str) -> Optional[dict]:
        """Get a conversation with all its messages."""
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )
        if not conversation:
            return None

        messages = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
            .all()
        )

        return {
            "id": conversation.id,
            "title": conversation.title,
            "is_voting": conversation.is_voting,
            "started_at": conversation.started_at.isoformat()
            if conversation.started_at
            else None,
            "ended_at": conversation.ended_at.isoformat()
            if conversation.ended_at
            else None,
            "messages": [
                {
                    "id": msg.id,
                    "sender_type": msg.sender_type,
                    "agent_id": msg.agent_id,
                    "content": msg.content,
                    "message_type": msg.message_type,
                    "created_at": msg.created_at.isoformat()
                    if msg.created_at
                    else None,
                }
                for msg in messages
            ],
        }

    def search_messages(self, query: str, limit: int = 20) -> List[dict]:
        """Search messages by content keyword."""
        messages = (
            self.db.query(Message)
            .filter(Message.content.ilike(f"%{query}%"))
            .order_by(desc(Message.created_at))
            .limit(limit)
            .all()
        )

        return [
            {
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "sender_type": msg.sender_type,
                "content": msg.content[:200] + "..."
                if len(msg.content) > 200
                else msg.content,
                "created_at": msg.created_at.isoformat() if msg.created_at else None,
            }
            for msg in messages
        ]

    def delete_conversation(self, conversation_id: str) -> bool:
        """Delete a conversation and all its messages."""
        conversation = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .first()
        )
        if conversation:
            # Messages will be cascade deleted due to FK constraint
            self.db.delete(conversation)
            self.db.commit()
            return True
        return False

    def search_past_context(self, query: str, limit: int = 5) -> List[dict]:
        """Search past conversations for agent reference.

        Returns relevant past messages that can be used as context for agents.
        """
        # Search in messages for relevant content
        messages = (
            self.db.query(Message)
            .filter(Message.content.ilike(f"%{query}%"))
            .order_by(desc(Message.created_at))
            .limit(limit)
            .all()
        )

        results = []
        for msg in messages:
            # Get conversation title for context
            conv = (
                self.db.query(Conversation)
                .filter(Conversation.id == msg.conversation_id)
                .first()
            )
            results.append(
                {
                    "conversation_id": msg.conversation_id,
                    "conversation_title": conv.title if conv else "제목 없음",
                    "content": msg.content,
                    "sender_type": msg.sender_type,
                    "created_at": msg.created_at.isoformat()
                    if msg.created_at
                    else None,
                }
            )

        return results

    def search_conversations(self, query: str, limit: int = 20) -> List[dict]:
        """Search conversations by title or message content.

        Args:
            query: Search query string
            limit: Maximum number of results

        Returns:
            List of matching conversations with message snippets
        """
        # Search in conversation titles
        title_matches = (
            self.db.query(Conversation)
            .filter(Conversation.title.ilike(f"%{query}%"))
            .all()
        )

        # Search in message content
        message_matches = (
            self.db.query(Message)
            .filter(Message.content.ilike(f"%{query}%"))
            .order_by(desc(Message.created_at))
            .limit(limit * 2)
            .all()
        )

        # Collect unique conversation IDs
        seen_ids = set()
        results = []

        # Add title matches first
        for conv in title_matches:
            if conv.id not in seen_ids and len(results) < limit:
                message_count = (
                    self.db.query(Message)
                    .filter(Message.conversation_id == conv.id)
                    .count()
                )

                results.append(
                    {
                        "id": conv.id,
                        "title": conv.title or "제목 없음",
                        "started_at": conv.started_at.isoformat()
                        if conv.started_at
                        else None,
                        "ended_at": conv.ended_at.isoformat()
                        if conv.ended_at
                        else None,
                        "message_count": message_count,
                        "match_type": "title",
                    }
                )
                seen_ids.add(conv.id)

        # Add message content matches
        for msg in message_matches:
            if msg.conversation_id not in seen_ids and len(results) < limit:
                conv = (
                    self.db.query(Conversation)
                    .filter(Conversation.id == msg.conversation_id)
                    .first()
                )

                if conv:
                    message_count = (
                        self.db.query(Message)
                        .filter(Message.conversation_id == conv.id)
                        .count()
                    )

                    # Create snippet from matching message
                    snippet = msg.content[:100] + (
                        "..." if len(msg.content) > 100 else ""
                    )

                    results.append(
                        {
                            "id": conv.id,
                            "title": conv.title or "제목 없음",
                            "started_at": conv.started_at.isoformat()
                            if conv.started_at
                            else None,
                            "ended_at": conv.ended_at.isoformat()
                            if conv.ended_at
                            else None,
                            "message_count": message_count,
                            "match_type": "content",
                            "snippet": snippet,
                        }
                    )
                    seen_ids.add(msg.conversation_id)

        return results
