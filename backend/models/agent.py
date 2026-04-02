from sqlalchemy import Column, String, DateTime, func
import uuid
from database import Base


class Agent(Base):
    """Agent entity representing a role in the company."""

    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    role = Column(String(50), nullable=False)  # manager, developer, designer, researcher
    status = Column(String(20), default="active")
    system_prompt = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Agent(id={self.id}, name={self.name}, role={self.role})>"
