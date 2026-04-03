"""Agent Message Broker - Agent-to-agent messaging (Inbox/Outbox concept)."""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    """Represents a message between agents."""
    message_id: str
    from_agent_id: str
    to_agent_id: str
    content: str
    context: Dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    read: bool = False


@dataclass  
class DebateContext:
    """Shared context for a debate session."""
    debate_id: str
    topic: str
    round_num: int
    previous_messages: List[Dict] = field(default_factory=list)


class AgentMessageBroker:
    """Manages agent-to-agent messaging using Inbox/Outbox pattern."""

    def __init__(self):
        """Initialize the message broker."""
        self.inboxes: Dict[str, List[AgentMessage]] = {}
        self.outboxes: Dict[str, List[AgentMessage]] = {}
        self.debate_contexts: Dict[str, DebateContext] = {}

    async def send_to_agent(
        self,
        from_id: str,
        to_id: str,
        content: str,
        context: Optional[Dict] = None,
    ) -> str:
        """Send a message to a specific agent.

        Args:
            from_id: Sender agent ID
            to_id: Recipient agent ID
            content: Message content
            context: Optional context metadata

        Returns:
            Message ID
        """
        message_id = str(uuid.uuid4())
        message = AgentMessage(
            message_id=message_id,
            from_agent_id=from_id,
            to_agent_id=to_id,
            content=content,
            context=context or {},
        )

        if to_id not in self.inboxes:
            self.inboxes[to_id] = []
        self.inboxes[to_id].append(message)

        if from_id not in self.outboxes:
            self.outboxes[from_id] = []
        self.outboxes[from_id].append(message)

        logger.info(f"Message {message_id}: {from_id} -> {to_id}")
        return message_id

    async def broadcast(
        self,
        from_id: str,
        content: str,
        context: Optional[Dict] = None,
        exclude: Optional[List[str]] = None,
    ) -> List[str]:
        """Broadcast a message to all agents.

        Args:
            from_id: Sender agent ID
            content: Message content
            context: Optional context metadata
            exclude: Agent IDs to exclude from broadcast

        Returns:
            List of message IDs
        """
        exclude_set = set(exclude or [])
        message_ids = []

        for to_id in self.inboxes.keys():
            if to_id == from_id or to_id in exclude_set:
                continue

            msg_id = await self.send_to_agent(from_id, to_id, content, context)
            message_ids.append(msg_id)

        logger.info(f"Broadcast from {from_id}: {len(message_ids)} recipients")
        return message_ids

    def get_inbox(self, agent_id: str, unread_only: bool = False) -> List[AgentMessage]:
        """Get messages from an agent's inbox.

        Args:
            agent_id: Agent ID to get inbox for
            unread_only: If True, return only unread messages

        Returns:
            List of AgentMessage
        """
        messages = self.inboxes.get(agent_id, [])
        
        if unread_only:
            messages = [m for m in messages if not m.read]
        
        return messages

    def get_outbox(self, agent_id: str) -> List[AgentMessage]:
        """Get messages from an agent's outbox.

        Args:
            agent_id: Agent ID to get outbox for

        Returns:
            List of AgentMessage
        """
        return self.outboxes.get(agent_id, [])

    def mark_read(self, agent_id: str, message_id: str):
        """Mark a message as read.

        Args:
            agent_id: Agent ID
            message_id: Message ID to mark as read
        """
        messages = self.inboxes.get(agent_id, [])
        for msg in messages:
            if msg.message_id == message_id:
                msg.read = True
                break

    def get_debate_context(self, debate_id: str) -> Optional[DebateContext]:
        """Get debate context by ID.

        Args:
            debate_id: Debate identifier

        Returns:
            DebateContext or None
        """
        return self.debate_contexts.get(debate_id)

    def set_debate_context(self, context: DebateContext):
        """Set debate context.

        Args:
            context: DebateContext to store
        """
        self.debate_contexts[context.debate_id] = context

    def clear_inbox(self, agent_id: str):
        """Clear an agent's inbox.

        Args:
            agent_id: Agent ID
        """
        if agent_id in self.inboxes:
            self.inboxes[agent_id] = []

    def get_all_inboxes_summary(self) -> Dict[str, int]:
        """Get unread count for all agents.

        Returns:
            Dict of agent_id -> unread count
        """
        summary = {}
        for agent_id, messages in self.inboxes.items():
            unread = sum(1 for m in messages if not m.read)
            summary[agent_id] = unread
        return summary

    def __repr__(self):
        return f"<AgentMessageBroker(inboxes={len(self.inboxes)}, contexts={len(self.debate_contexts)})>"