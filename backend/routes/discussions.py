"""Discussions API Router

Phase 3C: 사이드 토론 패널 (백엔드)
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from models.discussion import Discussion, DiscussionMessage
from schemas.discussion import (
    DiscussionCreate,
    DiscussionResponse,
    DiscussionMessageCreate,
    DiscussionMessageResponse,
)
from services.discussion_service import DiscussionService
from services.llm_provider_service import LLMProviderService
from database import get_db

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/discussions", tags=["discussions"])


def get_discussion_service(db: Session = Depends(get_db)):
    """DiscussionService 의존성 주입"""
    llm_service = LLMProviderService()  # 기본 LLM 서비스
    return DiscussionService(db, llm_service)


@router.get("/", response_model=List[DiscussionResponse])
async def list_active_discussions(
    project_id: Optional[str] = None, db: Session = Depends(get_db)
):
    """
    활성 토론 목록 조회

    Args:
        project_id: 프로젝트 ID (선택사항)

    Returns:
        활성 토론 목록
    """
    query = db.query(Discussion).filter(Discussion.status == "active")

    if project_id:
        query = query.filter(Discussion.project_id == project_id)

    discussions = query.order_by(Discussion.created_at.desc()).all()

    logger.info(f"Retrieved {len(discussions)} active discussions")

    return discussions


@router.post("/", response_model=DiscussionResponse, status_code=201)
async def create_discussion(
    discussion_data: DiscussionCreate,
    agent_ids: List[str],
    initial_message: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """
    새 토론 생성

    Args:
        discussion_data: 토론 생성 데이터
        agent_ids: 참여 에이전트 ID 목록
        initial_message: 초기 메시지 (선택사항)

    Returns:
        생성된 토론
    """
    # 토론 생성
    discussion = Discussion(
        topic=discussion_data.topic,
        project_id=discussion_data.project_id,
        status="active",
        agent_ids=agent_ids,
        created_at=datetime.utcnow(),
    )

    db.add(discussion)
    db.commit()
    db.refresh(discussion)

    # 초기 메시지가 있으면 추가
    if initial_message:
        message = DiscussionMessage(
            discussion_id=discussion.id, agent_id="system", content=initial_message
        )
        db.add(message)
        db.commit()

    logger.info(f"Discussion {discussion.id} created")

    return discussion


@router.get("/{discussion_id}", response_model=DiscussionResponse)
async def get_discussion(discussion_id: str, db: Session = Depends(get_db)):
    """
    특정 토론 조회

    Args:
        discussion_id: 토론 ID

    Returns:
        토론 정보
    """
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()

    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")

    return discussion


@router.post("/{discussion_id}/close", response_model=DiscussionResponse)
async def close_discussion(
    discussion_id: str,
    discussion_service: DiscussionService = Depends(get_discussion_service),
    db: Session = Depends(get_db),
):
    """
    토론 종료

    Args:
        discussion_id: 토론 ID

    Returns:
        종료된 토론
    """
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()

    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")

    # 토론 종료
    discussion.status = "closed"
    discussion.closed_at = datetime.utcnow()

    db.commit()
    db.refresh(discussion)

    # 토론 요약 생성
    summary = await discussion_service.summarize_discussion(discussion_id)

    if summary:
        logger.info(f"Discussion {discussion_id} closed with summary")
    else:
        logger.warning(f"Discussion {discussion_id} closed but summary failed")

    return discussion


@router.get("/{discussion_id}/messages", response_model=List[DiscussionMessageResponse])
async def get_discussion_messages(
    discussion_id: str,
    limit: int = 50,
    discussion_service: DiscussionService = Depends(get_discussion_service),
):
    """
    토론 메시지 목록 조회

    Args:
        discussion_id: 토론 ID
        limit: 조회할 메시지 수 (기본 50)

    Returns:
        메시지 목록
    """
    messages = await discussion_service.get_messages(discussion_id, limit)

    return messages


@router.post(
    "/{discussion_id}/messages",
    response_model=DiscussionMessageResponse,
    status_code=201,
)
async def add_discussion_message(
    discussion_id: str,
    message_data: DiscussionMessageCreate,
    discussion_service: DiscussionService = Depends(get_discussion_service),
    db: Session = Depends(get_db),
):
    """
    토론에 메시지 추가

    Args:
        discussion_id: 토론 ID
        message_data: 메시지 데이터

    Returns:
        추가된 메시지
    """
    # 토론 존재 확인
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()

    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")

    # 메시지 저장
    message = await discussion_service.save_message(
        discussion_id=discussion_id,
        agent_id=message_data.agent_id,
        content=message_data.content,
    )

    return message


@router.get("/{discussion_id}/summary")
async def get_discussion_summary(
    discussion_id: str,
    discussion_service: DiscussionService = Depends(get_discussion_service),
    db: Session = Depends(get_db),
):
    """
    토론 요약 조회

    Args:
        discussion_id: 토론 ID

    Returns:
        토론 요약
    """
    # 토론 존재 확인
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()

    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")

    # 요약 생성
    summary = await discussion_service.summarize_discussion(discussion_id)

    if not summary:
        raise HTTPException(status_code=500, detail="Failed to generate summary")

    return {"discussion_id": discussion_id, "summary": summary}


@router.delete("/{discussion_id}")
async def delete_discussion(discussion_id: str, db: Session = Depends(get_db)):
    """
    토론 삭제

    Args:
        discussion_id: 토론 ID

    Returns:
        삭제 결과
    """
    discussion = db.query(Discussion).filter(Discussion.id == discussion_id).first()

    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")

    # 관련 메시지도 삭제 (CASCADE 설정이 없는 경우)
    db.query(DiscussionMessage).filter(
        DiscussionMessage.discussion_id == discussion_id
    ).delete()

    db.delete(discussion)
    db.commit()

    logger.info(f"Discussion {discussion_id} deleted")

    return {"status": "ok", "message": "Discussion deleted"}
