from sqlalchemy import Column, String, Boolean, DateTime, Text, Index, func
import uuid
from database import Base


class Conversation(Base):
    """Conversation session between user and agents."""

    __tablename__ = "conversations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = Column(String(255), nullable=True)
    is_voting = Column(Boolean, default=False)
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)
    tags = Column(Text, nullable=True)  # JSON string of tags
    category = Column(
        String(50), nullable=True
    )  # 기획|개발|디자인|리서치|일반|토론|의사결정
    summary = Column(Text, nullable=True)  # Auto-generated summary
    reference_code = Column(String(20), unique=True, nullable=True)  # #C-YYMMDD-NNN

    __table_args__ = (Index("ix_conversations_reference_code", "reference_code"),)

    def __repr__(self):
        ref = self.reference_code or "no-ref"
        return f"<Conversation(id={self.id}, title={self.title}, ref={ref})>"
