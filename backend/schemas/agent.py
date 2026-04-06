from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


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
