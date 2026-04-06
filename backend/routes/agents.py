from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.agent import Agent
from models.project_agent import ProjectAgent
from schemas.agent import AgentResponse, AgentInviteRequest

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/", response_model=List[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    """에이전트 목록 조회"""
    agents = db.query(Agent).all()
    return agents


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """특정 에이전트 조회"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.post("/invite")
def invite_agent(invite: AgentInviteRequest, db: Session = Depends(get_db)):
    """에이전트를 프로젝트에 초대"""
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

    return {
        "id": binding.id,
        "project_id": binding.project_id,
        "agent_id": binding.agent_id,
        "is_lead": binding.is_lead,
        "message": f"Agent {agent.name} invited to project",
    }


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

    return {"message": "Agent removed from project"}
