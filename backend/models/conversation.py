from sqlalchemy import Column, String, Boolean, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
import uuid
from database import Base


class Conversation(Base):
    """Conversation session between user and agents."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(255), nullable=True)
    is_voting = Column(Boolean, default=False)
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Conversation(id={self.id}, title={self.title})>"
