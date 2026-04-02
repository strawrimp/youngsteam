"""Base agent class for all specialized agents."""

import uuid
from abc import ABC
from typing import Dict, List, Optional


class BaseAgent(ABC):
    """Abstract base class for all agents."""

    def __init__(self, agent_id: str, name: str, role: str, system_prompt: str):
        """
        Initialize an agent.

        Args:
            agent_id: Unique identifier for the agent
            name: Human-readable name
            role: Agent role (manager, developer, designer, researcher)
            system_prompt: System prompt defining agent behavior
        """
        self.id = agent_id
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.conversation_history: List[Dict] = []

    async def think(self, context: str) -> str:
        """
        Process context and generate a response.

        Args:
            context: Conversation context

        Returns:
            Agent's response
        """
        raise NotImplementedError

    async def respond(self, message: str) -> str:
        """
        Respond to a user message.

        Args:
            message: User message

        Returns:
            Agent's response
        """
        raise NotImplementedError

    async def vote(self, topic: str, candidates: List[str]) -> Dict:
        """
        Cast a vote on a topic.

        Args:
            topic: Topic for voting
            candidates: Available choices

        Returns:
            Dict with 'choice' and 'reasoning'
        """
        raise NotImplementedError

    def add_to_history(self, role: str, content: str):
        """Add a message to conversation history."""
        self.conversation_history.append({"role": role, "content": content})

    def get_history(self, limit: int = 20) -> List[Dict]:
        """Get conversation history (sliding window)."""
        return self.conversation_history[-limit:]

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id}, name={self.name}, role={self.role})>"
