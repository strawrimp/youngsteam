from sqlalchemy import Column, String, DateTime, ForeignKey, func
import uuid
import json
from database import Base


class Image(Base):
    """Generated or uploaded image."""

    __tablename__ = "images"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    url = Column(String(500), nullable=True)
    local_path = Column(String(255), nullable=True)
    metadata = Column(String, nullable=True)  # JSON string for SQLite compatibility
    created_by = Column(String(36), ForeignKey("agents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Image(id={self.id}, url={self.url})>"
