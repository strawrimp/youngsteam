from sqlalchemy import Column, String, DateTime, Boolean, func
import uuid
from database import Base


class Agent(Base):
    """Agent entity representing a role in the company."""

    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    role = Column(
        String(50), nullable=False
    )  # manager, developer, designer, researcher
    status = Column(String(20), default="active")
    system_prompt = Column(String, nullable=False)
    is_lead = Column(Boolean, default=False)  # 선임에이전트 여부 (초대 제안 권한)

    # New display columns
    display_name = Column(String(50), nullable=True)  # 비서실장, 개발부장, etc.
    emoji = Column(String(10), nullable=True)  # 👔, 💻, 🎨, 📚
    badge_text = Column(String(20), nullable=True)  # 책임, 기술, 디자인, 연구
    icon = Column(String(50), nullable=True)  # Material Symbols name
    color = Column(String(20), nullable=True)  # Hex color code

    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Agent(id={self.id}, name={self.name}, role={self.role}, is_lead={self.is_lead})>"
