from enum import Enum
from pydantic import BaseModel
from typing import Optional, Any, Dict


class EventType(str, Enum):
    """WebSocket 이벤트 타입"""

    # Project events
    PROJECT_CREATED = "project_created"
    PROJECT_UPDATED = "project_updated"
    PROJECT_DELETED = "project_deleted"

    # Agent events
    AGENT_INVITED = "agent_invited"
    AGENT_REMOVED = "agent_removed"

    # Invite events (Phase 3A - 하이브리드 초대 시스템)
    INVITE_SUGGESTED = "invite_suggested"  # 선임에이전트가 초대 제안
    INVITE_ACCEPTED = "invite_accepted"  # 사용자가 초대 승인
    INVITE_REJECTED = "invite_rejected"  # 사용자가 초대 거부
    AGENT_MENTIONED = "agent_mentioned"  # @멘션으로 에이전트 호출

    # Discussion events
    DISCUSSION_STARTED = "discussion_started"
    DISCUSSION_MESSAGE = "discussion_message"
    DISCUSSION_CLOSED = "discussion_closed"

    # Vote events
    VOTE_CAST = "vote_cast"
    VOTE_COMPLETED = "vote_completed"

    # Chat events (existing)
    CHAT_MESSAGE = "chat_message"
    AGENT_RESPONSE = "agent_response"
    TYPING_INDICATOR = "typing_indicator"


class WebSocketEvent(BaseModel):
    """WebSocket 이벤트 스키마"""

    type: EventType
    data: Dict[str, Any]
    timestamp: Optional[str] = None

    class Config:
        use_enum_values = True


# 편의 함수들
def create_event(event_type: EventType, data: Dict[str, Any]) -> Dict[str, Any]:
    """이벤트 생성 헬퍼 함수"""
    from datetime import datetime

    return {
        "type": event_type.value,
        "data": data,
        "timestamp": datetime.utcnow().isoformat(),
    }
