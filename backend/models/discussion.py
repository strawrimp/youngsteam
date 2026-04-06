from sqlalchemy import Column, String, DateTime, ForeignKey, Text, func
import uuid
from database import Base


class Discussion(Base):
    """에이전트 간 토론 세션"""

    __tablename__ = "discussions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    topic = Column(String(200), nullable=False)
    status = Column(String(20), default="active")  # active, closed
    created_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime, nullable=True)

    def __repr__(self):
        return f"<Discussion(id={self.id}, topic={self.topic}, status={self.status})>"


class DiscussionMessage(Base):
    """토론 내 메시지"""

    __tablename__ = "discussion_messages"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    discussion_id = Column(
        String(36), ForeignKey("discussions.id", ondelete="CASCADE"), nullable=False
    )
    agent_id = Column(
        String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<DiscussionMessage(discussion_id={self.discussion_id}, agent_id={self.agent_id})>"
