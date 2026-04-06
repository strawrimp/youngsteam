from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.vote import Vote
from models.discussion import Discussion
from models.agent import Agent
from schemas.vote import VoteCreate, VoteResponse

router = APIRouter(prefix="/api/votes", tags=["votes"])


@router.post("/", response_model=VoteResponse)
def create_vote(vote: VoteCreate, db: Session = Depends(get_db)):
    """새 투표 생성"""
    # 토론 존재 및 활성 상태 확인
    discussion = (
        db.query(Discussion).filter(Discussion.id == vote.discussion_id).first()
    )
    if not discussion:
        raise HTTPException(status_code=404, detail="Discussion not found")
    if discussion.status != "active":
        raise HTTPException(status_code=400, detail="Discussion is closed")

    # 에이전트 존재 확인
    agent = db.query(Agent).filter(Agent.id == vote.agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # 중복 투표 확인
    existing_vote = (
        db.query(Vote)
        .filter(
            Vote.discussion_id == vote.discussion_id, Vote.agent_id == vote.agent_id
        )
        .first()
    )
    if existing_vote:
        raise HTTPException(status_code=400, detail="Agent has already voted")

    db_vote = Vote(**vote.model_dump())
    db.add(db_vote)
    db.commit()
    db.refresh(db_vote)

    return db_vote


@router.get("/{discussion_id}", response_model=List[VoteResponse])
def get_votes_by_discussion(discussion_id: str, db: Session = Depends(get_db)):
    """토론별 투표 결과 조회"""
    votes = db.query(Vote).filter(Vote.discussion_id == discussion_id).all()
    return votes


@router.get("/{discussion_id}/results")
def get_vote_results(discussion_id: str, db: Session = Depends(get_db)):
    """투표 결과 집계"""
    votes = db.query(Vote).filter(Vote.discussion_id == discussion_id).all()

    if not votes:
        return {"discussion_id": discussion_id, "total_votes": 0, "results": {}}

    # 선택별 집계
    results = {}
    for vote in votes:
        if vote.choice not in results:
            results[vote.choice] = {"count": 0, "reasoning": []}
        results[vote.choice]["count"] += 1
        if vote.reasoning:
            results[vote.choice]["reasoning"].append(vote.reasoning)

    return {
        "discussion_id": discussion_id,
        "total_votes": len(votes),
        "results": results,
    }
