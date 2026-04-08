from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional, List


class AgentBase(BaseModel):
    name: str
    role: str
    system_prompt: str
    is_lead: bool = False
    display_name: Optional[str] = None
    emoji: Optional[str] = None
    badge_text: Optional[str] = None
    icon: Optional[str] = None
    color: Optional[str] = None


class AgentResponse(AgentBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    created_at: datetime
    updated_at: datetime


class AgentInviteRequest(BaseModel):
    project_id: str
    agent_id: str
    is_lead: bool = False


# Phase 3A: 초대 시스템 스키마
class InviteSuggestionRequest(BaseModel):
    """초대 제안 요청"""

    project_id: str
    message: str  # 분석할 메시지
    sender_role: Optional[str] = None  # 발신자 역할 (선임에이전트 확인용)


class InviteSuggestionResponse(BaseModel):
    """초대 제안 응답"""

    agent_id: str
    agent_name: str
    agent_role: str
    agent_display_name: Optional[str] = None
    agent_emoji: Optional[str] = None
    reason: str
    triggered_by: str  # 'keyword' | 'mention'
    confidence: float


class AcceptInviteRequest(BaseModel):
    """초대 승인 요청"""

    project_id: str
    agent_id: str


class RejectInviteRequest(BaseModel):
    """초대 거부 요청"""

    project_id: str
    agent_id: str


class MentionRequest(BaseModel):
    """@멘션 요청"""

    project_id: str
    message: str  # @멘션이 포함된 메시지


class MentionResponse(BaseModel):
    """@멘션 응답"""

    mentioned_agents: List[str]
    invited_count: int
    message: str
