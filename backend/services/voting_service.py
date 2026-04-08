"""
VotingService: Business logic for voting session management.

Handles:
1. Creating voting sessions
2. Collecting votes from agents
3. Calculating consensus
4. Broadcasting voting results
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session

from engines.voting_engine import VotingEngine
from models.vote import Vote
from models.discussion import Discussion
from models.agent import Agent
from websocket.events import EventType, create_event

logger = logging.getLogger(__name__)


class VotingService:
    """Service for managing voting sessions."""

    def __init__(self, db_session: Session, ws_manager=None):
        """
        Initialize voting service.

        Args:
            db_session: SQLAlchemy database session
            ws_manager: WebSocket manager for broadcasting events
        """
        self.db = db_session
        self.ws_manager = ws_manager
        self.voting_engine = VotingEngine(db_session)

    async def start_voting_session(
        self,
        project_id: str,
        discussion_id: str,
        topic: str,
        candidates: List[str],
        agent_ids: List[str],
    ) -> Dict[str, Any]:
        """
        Start a new voting session.

        Args:
            project_id: Project ID for broadcasting
            discussion_id: Discussion ID this vote belongs to
            topic: What is being voted on
            candidates: List of choices to vote for
            agent_ids: List of agent IDs eligible to vote

        Returns:
            Dict with voting session info
        """
        # Verify discussion exists and is active
        discussion = (
            self.db.query(Discussion).filter(Discussion.id == discussion_id).first()
        )

        if not discussion:
            raise ValueError(f"Discussion {discussion_id} not found")

        if discussion.status != "active":
            raise ValueError(f"Discussion {discussion_id} is not active")

        # Verify all agents exist
        agents = self.db.query(Agent).filter(Agent.id.in_(agent_ids)).all()
        if len(agents) != len(agent_ids):
            raise ValueError("Some agents not found")

        # Create voting session info
        voting_session = {
            "discussion_id": discussion_id,
            "project_id": project_id,
            "topic": topic,
            "candidates": candidates,
            "eligible_voters": agent_ids,
            "votes": {},  # agent_id -> {choice, reasoning}
            "status": "active",
            "started_at": datetime.utcnow().isoformat(),
        }

        # Broadcast VOTE_STARTED event
        if self.ws_manager:
            event = create_event(
                EventType.VOTE_STARTED,
                {
                    "discussion_id": discussion_id,
                    "topic": topic,
                    "candidates": candidates,
                    "eligible_voters": agent_ids,
                },
            )
            await self.ws_manager.broadcast_to_project(project_id, event)

        logger.info(f"Voting session started: {topic} for discussion {discussion_id}")
        return voting_session

    async def cast_vote(
        self,
        project_id: str,
        discussion_id: str,
        agent_id: str,
        choice: str,
        reasoning: Optional[str] = None,
    ) -> Vote:
        """
        Cast a vote from an agent.

        Args:
            project_id: Project ID for broadcasting
            discussion_id: Discussion ID
            agent_id: Agent casting the vote
            choice: The chosen option
            reasoning: Optional reasoning for the vote

        Returns:
            Created Vote object
        """
        # Check if agent already voted
        existing_vote = (
            self.db.query(Vote)
            .filter(Vote.discussion_id == discussion_id, Vote.agent_id == agent_id)
            .first()
        )

        if existing_vote:
            raise ValueError(f"Agent {agent_id} has already voted")

        # Create vote
        vote = Vote(
            discussion_id=discussion_id,
            agent_id=agent_id,
            choice=choice,
            reasoning=reasoning,
        )
        self.db.add(vote)
        self.db.commit()
        self.db.refresh(vote)

        # Broadcast VOTE_CAST event
        if self.ws_manager:
            event = create_event(
                EventType.VOTE_CAST,
                {
                    "id": vote.id,
                    "discussion_id": discussion_id,
                    "agent_id": agent_id,
                    "choice": choice,
                    "reasoning": reasoning,
                },
            )
            await self.ws_manager.broadcast_to_project(project_id, event)

        logger.info(f"Vote cast by {agent_id}: {choice}")
        return vote

    async def complete_voting_session(
        self,
        project_id: str,
        discussion_id: str,
        manager_agent_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Complete a voting session and calculate results.

        Args:
            project_id: Project ID for broadcasting
            discussion_id: Discussion ID
            manager_agent_id: Manager agent ID for tiebreaker (optional)

        Returns:
            Dict with voting results
        """
        # Get all votes for this discussion
        votes = self.db.query(Vote).filter(Vote.discussion_id == discussion_id).all()

        if not votes:
            return {
                "discussion_id": discussion_id,
                "status": "no_votes",
                "message": "No votes cast",
            }

        # Prepare votes dict for consensus calculation
        votes_dict = {vote.agent_id: vote.choice for vote in votes}
        votes_with_reasoning = {
            vote.agent_id: {"choice": vote.choice, "reasoning": vote.reasoning}
            for vote in votes
        }

        # Get candidates from discussion or infer from votes
        candidates = list(set(vote.choice for vote in votes))

        # Calculate consensus
        winner, breakdown = self.voting_engine.calculate_consensus(votes_dict)

        # If tied and manager provided, resolve tie
        is_tie = breakdown.get("status") == "tied"
        if is_tie and manager_agent_id:
            tied_choices = breakdown.get("top_choices", [])
            manager_vote = votes_dict.get(manager_agent_id)

            if manager_vote:
                winner, tiebreaker_info = self.voting_engine.resolve_tie(
                    breakdown.get("topic", ""), tied_choices, manager_vote
                )
                breakdown["tiebreaker"] = tiebreaker_info

        # Format final result
        topic = f"Vote for discussion {discussion_id}"
        result = self.voting_engine.format_voting_result(
            topic, candidates, votes_with_reasoning, winner or "no_consensus", is_tie
        )

        # Broadcast VOTE_COMPLETED event
        if self.ws_manager:
            event = create_event(
                EventType.VOTE_COMPLETED,
                {
                    "discussion_id": discussion_id,
                    "winner": winner,
                    "is_tiebreaker": is_tie,
                    "breakdown": breakdown,
                    "total_votes": len(votes),
                },
            )
            await self.ws_manager.broadcast_to_project(project_id, event)

        logger.info(f"Voting session completed: {discussion_id}, winner: {winner}")
        return result

    def get_voting_status(self, discussion_id: str) -> Dict[str, Any]:
        """
        Get current voting status for a discussion.

        Args:
            discussion_id: Discussion ID

        Returns:
            Dict with voting status info
        """
        votes = self.db.query(Vote).filter(Vote.discussion_id == discussion_id).all()

        # Get discussion info
        discussion = (
            self.db.query(Discussion).filter(Discussion.id == discussion_id).first()
        )

        if not discussion:
            return {
                "discussion_id": discussion_id,
                "status": "not_found",
            }

        # Count votes by choice
        vote_counts = {}
        for vote in votes:
            if vote.choice not in vote_counts:
                vote_counts[vote.choice] = 0
            vote_counts[vote.choice] += 1

        return {
            "discussion_id": discussion_id,
            "status": "active" if discussion.status == "active" else "closed",
            "total_votes": len(votes),
            "vote_breakdown": vote_counts,
        }

    def __repr__(self):
        return f"<VotingService(db={self.db})>"
