from sqlalchemy import Column, String, Boolean, DateTime, func
import uuid
from database import Base


class Conversation(Base):
    """Conversation session between user and agents."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=True)
    is_voting = Column(Boolean, default=False)
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title})>"
