from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime
from database import get_db
from models.discussion import Discussion, DiscussionMessage
from models.project import Project
from schemas.discussion import (
    DiscussionCreate,
    DiscussionResponse,
    DiscussionMessageCreate,
    DiscussionMessageResponse,
)

router = APIRouter(prefix="/api/discussions", tags=["discussions"])


@router.post("/", response_model=DiscussionResponse)
def create_discussion(discussion: DiscussionCreate, db: Session = Depends(get_db)):
    """새 토론 생성"""
    # 프로젝트 존재 확인
    project = db.query(Project).filter(Project.id == discussion.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_discussion = Discussion(**discussion.model_dump())
    db.add(db_discussion)
    db.commit()
    db.refresh(db_discussion)
    return db_discussion


@router.get("/{project_id}", response_model=List[DiscussionResponse])
def list_discussions(project_id: str, db: Session = Depends(get_db)):
    """프로젝트별 토론 목록 조회"""
    discussions = db.query(Discussion).filter(Discussion.project_id == project_id).all()
    return discussions


@router.get("/detail/{discussion_id}", response_model=DiscussionResponse)
def get_discussion(discussion_id: str, db: Session = Depends(get_db)):
    """특정 토론 조회"""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    return discussion


@router.post("/{discussion_id}/messages", response_model=DiscussionMessageResponse)
def create_discussion_message(
    discussion_id: str, message: DiscussionMessageCreate, db: Session = Depends(get_db)
):
    """토론에 메시지 전송"""
    # 토론 존재 및 활성 상태 확인
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    if discussion.status != "active":
        raise HTTPException(status_code=400, detail="Discussion is closed")

    db_message = DiscussionMessage(
        discussion_id=discussion_id, agent_id=message.agent_id, content=message.content
    )
    db.add(db_message)
    db.commit()
    db.refresh(db_message)
    return db_message


@router.get("/{discussion_id}/messages", response_model=List[DiscussionMessageResponse])
def list_discussion_messages(discussion_id: str, db: Session = Depends(get_db)):
    """토론 메시지 목록 조회"""
    messages = (
        db.query(DiscussionMessage)
        .filter(DiscussionMessage.discussion_id == discussion_id)
        .order_by(DiscussionMessage.created_at)
        .all()
    )
    return messages


@router.post("/{discussion_id}/close")
def close_discussion(discussion_id: str, db: Session = Depends(get_db)):
    """토론 종료"""
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")

    discussion.status = "closed"
    discussion.closed_at = datetime.utcnow()
    db.commit()

    return {"message": "Discussion closed", "id": discussion_id}
