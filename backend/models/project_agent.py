from sqlalchemy import (
    Column,
    String,
    DateTime,
    Boolean,
    ForeignKey,
    func,
    UniqueConstraint,
)
import uuid
from database import Base


class ProjectAgent(Base):
    """프로젝트-에이전트 바인딩 (중간 테이블)"""

    __tablename__ = "project_agents"
    __table_args__ = (
        UniqueConstraint("project_id", "agent_id", name="uq_project_agent"),
    )

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(
        String(36), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False
    )
    agent_id = Column(
        String(36), ForeignKey("agents.id", ondelete="CASCADE"), nullable=False
    )
    is_lead = Column(Boolean, default=False)  # 이 프로젝트에서 선임 역할 여부
    invited_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<ProjectAgent(project_id={self.project_id}, agent_id={self.agent_id}, is_lead={self.is_lead})>"
