from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.agent import Agent
from models.project_agent import ProjectAgent
from schemas.agent import (
    AgentResponse,
    AgentInviteRequest,
    InviteSuggestionRequest,
    InviteSuggestionResponse,
    AcceptInviteRequest,
    RejectInviteRequest,
    MentionRequest,
    MentionResponse,
)
from services.invite_service import InviteService
from engines.invite_engine import InviteEngine
from websocket.events import EventType, create_event

router = APIRouter(prefix="/api/agents", tags=["agents"])

# WebSocket manager (main.py에서 주입)
ws_manager = None


def set_ws_manager(manager):
    """WebSocket manager 주입"""
    global ws_manager
    ws_manager = manager


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """특정 에이전트 조회"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/invite")
def invite_agent(invite: AgentInviteRequest, db: Session = Depends(get_db)):
    """에이전트를 프로젝트에 초대 (기존 수동 초대)"""
    # 에이전트 존재 확인
    agent = db.query(Agent).filter(Agent.id == invite.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 중복 바인딩 확인
    existing = (
        db.query(ProjectAgent)
        .filter(
            ProjectAgent.project_id == invite.project_id,
            ProjectAgent.agent_id == invite.agent_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=400, detail="Agent already invited to this project"
        )

    # 바인딩 생성
    binding = ProjectAgent(
        project_id=invite.project_id, agent_id=invite.agent_id, is_lead=invite.is_lead
    )
    db.add(binding)
    db.commit()
    db.refresh(binding)

    # WebSocket 이벤트 발행
    if ws_manager:
        import asyncio

        event = create_event(
            EventType.AGENT_INVITED,
            {
                "id": binding.id,
                "project_id": binding.project_id,
                "agent_id": binding.agent_id,
                "is_lead": binding.is_lead,
                "agent_name": agent.name,
            },
        )
        asyncio.create_task(ws_manager.broadcast_to_project(invite.project_id, event))

    return {
        "id": binding.id,
        "project_id": binding.project_id,
        "agent_id": binding.agent_id,
        "is_lead": binding.is_lead,
        "message": f"Agent {agent.name} invited to project",
    }


# ============================================================
# Phase 3A: 하이브리드 초대 시스템 엔드포인트
# ============================================================


@router.post("/suggest-invite", response_model=List[InviteSuggestionResponse])
async def suggest_invite(
    request: InviteSuggestionRequest, db: Session = Depends(get_db)
):
    """메시지 분석하여 초대 제안 생성

    - 선임에이전트가 보낸 메시지에서 키워드 감지
    - 모든 메시지에서 @멘션 감지
    """
    # 현재 프로젝트에 참여 중인 에이전트 조회
    project_agents = InviteService.get_project_agents_set(db, request.project_id)

    # 메시지 분석
    suggestions = InviteEngine.analyze_message_for_invites(
        message=request.message,
        project_agents=project_agents,
        sender_role=request.sender_role,
    )

    # 응답 변환
    response = []
    for suggestion in suggestions:
        # 에이전트 정보 조회
        agent = (
            db.query(Agent)
            .filter(Agent.role == suggestion.suggested_agent_role)
            .first()
        )

        if agent:
            response.append(
                InviteSuggestionResponse(
                    agent_id=agent.id,
                    agent_name=agent.name,
                    agent_role=agent.role,
                    agent_display_name=agent.display_name,
                    agent_emoji=agent.emoji,
                    reason=suggestion.reason,
                    triggered_by=suggestion.triggered_by,
                    confidence=suggestion.confidence,
                )
            )

    return response


@router.post("/accept-invite")
async def accept_invite(request: AcceptInviteRequest, db: Session = Depends(get_db)):
    """초대 승인 - 에이전트를 프로젝트에 바인딩"""
    success = await InviteService.accept_invite(
        db=db,
        project_id=request.project_id,
        agent_id=request.agent_id,
        ws_manager=ws_manager,
    )

    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to accept invite (agent may already be bound)",
        )

    return {
        "success": True,
        "project_id": request.project_id,
        "agent_id": request.agent_id,
        "message": "Agent successfully joined the project",
    }


@router.post("/reject-invite")
async def reject_invite(request: RejectInviteRequest, db: Session = Depends(get_db)):
    """초대 거부"""
    success = await InviteService.reject_invite(
        db=db,
        project_id=request.project_id,
        agent_id=request.agent_id,
        ws_manager=ws_manager,
    )

    if not success:
        raise HTTPException(status_code=400, detail="Failed to reject invite")

    return {
        "success": True,
        "project_id": request.project_id,
        "agent_id": request.agent_id,
        "message": "Invite rejected",
    }


@router.post("/mention", response_model=MentionResponse)
async def handle_mention(request: MentionRequest, db: Session = Depends(get_db)):
    """@멘션 처리 - 즉시 에이전트 초대

    메시지에서 @developer, @designer 등을 파싱하여
    해당 에이전트를 즉시 프로젝트에 초대
    """
    # @멘션 파싱
    mentioned_roles = InviteEngine.parse_mentions(request.message)

    if not mentioned_roles:
        return MentionResponse(
            mentioned_agents=[], invited_count=0, message="No valid mentions found"
        )

    # 각 멘션된 에이전트 초대
    invited_count = 0
    invited_agents = []

    for role in mentioned_roles:
        agent = db.query(Agent).filter(Agent.role == role).first()
        if agent:
            success = await InviteService.handle_mention(
                db=db,
                project_id=request.project_id,
                agent_id=agent.id,
                ws_manager=ws_manager,
            )
            if success:
                invited_count += 1
                invited_agents.append(agent.name)

    return MentionResponse(
        mentioned_agents=invited_agents,
        invited_count=invited_count,
        message=f"Successfully invited {invited_count} agent(s)",
    )


@router.delete("/{agent_id}/projects/{project_id}")
def remove_agent_from_project(
    agent_id: str, project_id: str, db: Session = Depends(get_db)
):
    """프로젝트에서 에이전트 제거"""
    binding = (
        db.query(ProjectAgent)
        .filter(
            ProjectAgent.agent_id == agent_id, ProjectAgent.project_id == project_id
        )
        .first()
    )

    if not binding:
        raise HTTPException(status_code=404, detail="Binding not found")

    db.delete(binding)
    db.commit()

    # WebSocket 이벤트 발행
    if ws_manager:
        import asyncio

        event = create_event(
            EventType.AGENT_REMOVED, {"project_id": project_id, "agent_id": agent_id}
        )
        asyncio.create_task(ws_manager.broadcast_to_project(project_id, event))

    return {"message": "Agent removed from project"}
