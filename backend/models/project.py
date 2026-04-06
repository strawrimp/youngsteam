from sqlalchemy import Column, String, DateTime, Text, func
import uuid
from database import Base


class Project(Base):
    """프로젝트 엔티티 - 에이전트들이 협업하는 작업 공간"""

    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Project(id={self.id}, name={self.name})>"
