from sqlalchemy import Column, String, DateTime, func
import uuid
from database import Base


class TeamSettings(Base):
    """Team settings for the company."""

    __tablename__ = "team_settings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    team_name = Column(String(100), nullable=False, default="Young's Team")
    team_subtitle = Column(String(100), nullable=False, default="AI Agents Online")
    team_icon = Column(String(50), nullable=False, default="terminal")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<TeamSettings(team_name={self.team_name})>"
