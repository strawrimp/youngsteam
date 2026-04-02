from sqlalchemy import Column, String, DateTime, ForeignKey, func
import uuid
from database import Base


class Message(Base):
    """Message in a conversation."""

    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    sender_type = Column(String(20), nullable=False)  # "user" or "agent"
    content = Column(String, nullable=False)
    message_type = Column(String(20), default="text")  # text, image, decision
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, sender_type={self.sender_type})>"
