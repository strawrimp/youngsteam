from sqlalchemy import Column, String, DateTime, ForeignKey, func, Text
import uuid
from database import Base


class SharedMemory(Base):
    """Shared memory accessible to all agents."""

    __tablename__ = "shared_memory"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    category = Column(String(50), nullable=False)  # strategy, goal, project, decision
    content = Column(Text, nullable=False)
    created_by = Column(
        String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True
    )
    memory_metadata = Column(
        Text, nullable=True
    )  # JSON string for SQLite compatibility (renamed from 'metadata')
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SharedMemory(id={self.id}, category={self.category})>"
