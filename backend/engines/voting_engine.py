"""
VotingEngine: Manages voting and consensus for multi-agent decisions.

Handles:
1. Vote collection from agents
2. Consensus calculation (simple majority)
3. Tiebreaker resolution (Manager agent decides)
4. Decision persistence
"""

import logging
from typing import Dict, List, Optional, Tuple
from collections import Counter
from datetime import datetime

logger = logging.getLogger(__name__)


class VotingEngine:
    """Manages voting and consensus decision-making."""

    def __init__(self, db_session=None):
        """Initialize voting engine.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session

    def calculate_consensus(self, votes: Dict[str, str]) -> Tuple[Optional[str], Dict]:
        """
        Calculate consensus from votes.

        Simple majority rule:
        - Most voted choice wins
        - If tie, returns None (needs tiebreaker)

        Args:
            votes: Dict mapping agent_id to chosen candidate (string)

        Returns:
            Tuple of (winning_choice, vote_breakdown)
            - winning_choice: Most voted choice, or None if tied
            - vote_breakdown: Dict with vote counts and breakdown
        """
        if not votes:
            return None, {}

        # Count votes
        vote_counts = Counter(votes.values())

        # Get the most common vote
        most_common = vote_counts.most_common()

        if not most_common:
            return None, {}

        # Check for tie
        if len(most_common) > 1 and most_common[0][1] == most_common[1][1]:
            logger.info(f"Vote tie detected: {most_common}")
            return None, {
                "votes": votes,
                "counts": dict(vote_counts),
                "status": "tied",
                "top_choices": [choice for choice, _ in most_common[:2]]
            }

        # Winner found
        winner = most_common[0][0]
        logger.info(f"Consensus reached: {winner}")

        return winner, {
            "votes": votes,
            "counts": dict(vote_counts),
            "status": "consensus",
            "winner": winner
        }

    def resolve_tie(
        self,
        topic: str,
        tied_choices: List[str],
        manager_vote: str
    ) -> Tuple[str, Dict]:
        """
        Resolve a tied vote using manager agent's tiebreaker vote.

        Args:
            topic: The voting topic
            tied_choices: List of candidates tied for first
            manager_vote: Manager agent's choice

        Returns:
            Tuple of (final_decision, resolution_info)
        """
        if manager_vote not in tied_choices:
            # Manager chose a different option, use it
            manager_vote = tied_choices[0] if tied_choices else None

        logger.info(f"Tiebreaker decision: {manager_vote}")

        return manager_vote, {
            "type": "tiebreaker",
            "topic": topic,
            "tied_choices": tied_choices,
            "manager_decision": manager_vote,
            "timestamp": datetime.now().isoformat()
        }

    def format_voting_result(
        self,
        topic: str,
        candidates: List[str],
        votes: Dict[str, Dict],  # agent_id -> {choice, reasoning}
        final_decision: str,
        is_tie: bool = False
    ) -> Dict:
        """
        Format voting results for storage and display.

        Args:
            topic: Voting topic
            candidates: All candidate choices
            votes: Dict with all agent votes and reasoning
            final_decision: Final decided choice
            is_tie: Whether this was resolved via tiebreaker

        Returns:
            Formatted voting result dict
        """
        return {
            "topic": topic,
            "candidates": candidates,
            "votes": votes,  # Dict with choice and reasoning
            "final_decision": final_decision,
            "is_tiebreaker": is_tie,
            "timestamp": datetime.now().isoformat(),
            "vote_count": len(votes),
            "breakdown": self._get_vote_breakdown(votes, candidates)
        }

    def _get_vote_breakdown(self, votes: Dict[str, Dict], candidates: List[str]) -> Dict:
        """
        Get vote breakdown by candidate.

        Args:
            votes: Dict with agent votes
            candidates: List of candidates

        Returns:
            Dict mapping candidate to vote count
        """
        breakdown = {candidate: 0 for candidate in candidates}
        for vote_data in votes.values():
            choice = vote_data.get("choice", "")
            if choice in breakdown:
                breakdown[choice] += 1

        return breakdown

    def __repr__(self):
        return f"<VotingEngine(db={self.db})>"
