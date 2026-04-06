from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class DiscussionBase(BaseModel):
    project_id: str
    topic: str


class DiscussionCreate(DiscussionBase):
    pass


class DiscussionResponse(DiscussionBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    created_at: datetime
    closed_at: Optional[datetime] = None


class DiscussionMessageBase(BaseModel):
    discussion_id: str
    agent_id: Optional[str] = None
    content: str


class DiscussionMessageCreate(DiscussionMessageBase):
    pass


class DiscussionMessageResponse(DiscussionMessageBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
