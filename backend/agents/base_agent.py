"""Base agent class for all specialized agents."""

import uuid
from abc import ABC
from typing import Dict, List, Optional
from agents.soul.loader import get_soul_loader


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

    async def respond(
        self,
        message: str,
        task_type: str = "default",
        complexity: float = 0.0,
    ) -> str:
        """
        Respond to a user message.

        Args:
            message: User message
            task_type: Type of task (used for model selection in hybrid strategy)
            complexity: Task complexity score (0.0-1.0)

        Returns:
            Agent's response
        """
        raise NotImplementedError

    async def vote(
        self,
        topic: str,
        candidates: List[str],
        task_type: str = "voting",
    ) -> Dict:
        """
        Cast a vote on a topic.

        Args:
            topic: Topic for voting
            candidates: Available choices
            task_type: Type of task (default: 'voting' which requires R1)

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
        self.conversation_history = []

    def get_soul_system_prompt(self, shared_memory: str = "", debate_style: str = "diplomatic") -> str:
        """Get SOUL-based system prompt for this agent.

        Args:
            shared_memory: Shared memory content
            debate_style: Debate style (assertive, diplomatic, analytical)

        Returns:
            Personalized system prompt
        """
        soul_loader = get_soul_loader()
        return soul_loader.get_personalized_prompt(
            role=self.role,
            shared_memory=shared_memory,
            debate_style=debate_style,
        )

    async def respond_to_debate(
        self,
        topic: str,
        previous_messages: List[Dict],
        round_num: int,
        mode: str = "debate",
    ) -> str:
        raise NotImplementedError

    def __repr__(self):
        return f"<{self.__class__.__name__}(id={self.id}, name={self.name}, role={self.role})>"
