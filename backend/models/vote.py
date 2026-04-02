from sqlalchemy import Column, String, DateTime, ForeignKey, func, Text
import uuid
from database import Base


class Vote(Base):
    """Vote cast by an agent."""

    __tablename__ = "votes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    decision_id = Column(String(36), ForeignKey("decisions.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    choice = Column(String, nullable=False)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Vote(id={self.id}, agent_id={self.agent_id}, choice={self.choice})>"
