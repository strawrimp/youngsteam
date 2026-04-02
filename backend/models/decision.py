from sqlalchemy import Column, String, DateTime, ForeignKey, func, Text
import uuid
from database import Base


class Decision(Base):
    """Final decision made after voting."""

    __tablename__ = "decisions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=True)
    topic = Column(Text, nullable=False)
    final_decision = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Decision(id={self.id}, topic={self.topic})>"
