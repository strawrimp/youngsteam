from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class VoteBase(BaseModel):
    discussion_id: str
    agent_id: str
    choice: str
    reasoning: Optional[str] = None


class VoteCreate(VoteBase):
    pass


class VoteResponse(VoteBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime
