from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.project import Project
from schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from websocket.events import EventType, create_event
from websocket.events import EventType, create_event

router = APIRouter(prefix="/api/projects", tags=["projects"])

# WebSocket manager (main.py에서 주입)
ws_manager = None


def set_ws_manager(manager):
    """WebSocket manager 주입"""
    global ws_manager
    ws_manager = manager


@router.post("/", response_model=ProjectResponse)
def create_project(project: ProjectCreate, db: Session = Depends(get_db)):
    """새 프로젝트 생성"""
    db_project = Project(**project.model_dump())
    db.add(db_project)
    db.commit()
    db.refresh(db_project)

    # WebSocket 이벤트 발행
    if ws_manager:
        import asyncio

        event = create_event(
            EventType.PROJECT_CREATED,
            {
                "id": db_project.id,
                "name": db_project.name,
                "description": db_project.description,
            },
        )
        asyncio.create_task(ws_manager.broadcast(event))

    return db_project


@router.get("/", response_model=List[ProjectResponse])
def list_projects(db: Session = Depends(get_db)):
    """프로젝트 목록 조회"""
    projects = db.query(Project).all()
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: str, db: Session = Depends(get_db)):
    """특정 프로젝트 조회"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.put("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: str, project_update: ProjectUpdate, db: Session = Depends(get_db)
):
    """프로젝트 수정"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)

    # WebSocket 이벤트 발행
    if ws_manager:
        import asyncio

        event = create_event(
            EventType.PROJECT_UPDATED,
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
            },
        )
        asyncio.create_task(ws_manager.broadcast(event))

    return project


@router.delete("/{project_id}")
def delete_project(project_id: str, db: Session = Depends(get_db)):
    """프로젝트 삭제"""
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db.delete(project)
    db.commit()

    # WebSocket 이벤트 발행
    if ws_manager:
        import asyncio

        event = create_event(EventType.PROJECT_DELETED, {"id": project_id})
        asyncio.create_task(ws_manager.broadcast(event))

    return {"message": "Project deleted successfully", "id": project_id}
