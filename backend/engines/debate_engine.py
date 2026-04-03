"""
DebateEngine: Multi-round debate orchestration.

Enables agent-to-agent discussions:
1. Accepts debate topic
2. Runs multiple rounds where agents respond to each other
3. Supports different modes: debate, brainstorm, consensus
"""

import asyncio
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


@dataclass
class DebateMessage:
    """Represents a single message in a debate."""
    round_num: int
    agent_id: str
    agent_name: str
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class DebateResult:
    """Results from a complete debate."""
    debate_id: str
    topic: str
    mode: str
    rounds: int
    messages: List[DebateMessage]
    final_summary: str
    timestamp: str


class DebateEngine:
    """Manages multi-round debates between agents."""

    def __init__(self, agents: Dict[str, 'BaseAgent'] = None, semaphore: asyncio.Semaphore = None):
        """
        Initialize debate engine.

        Args:
            agents: Dict of agent_id -> agent instance
            semaphore: Rate limiter for LLM calls
        """
        self.agents = agents or {}
        self.semaphore = semaphore or asyncio.Semaphore(2)
        self._ws_callback: Optional[Callable] = None

    def set_websocket_callback(self, callback: Callable):
        """Set callback for real-time updates.
        
        Args:
            callback: Async function(debate_id, round_num, agent_id, message)
        """
        self._ws_callback = callback

    async def start_debate(
        self,
        topic: str,
        agent_ids: List[str],
        num_rounds: int = 2,
        mode: str = "debate",
    ) -> DebateResult:
        """
        Start a multi-round debate.

        Args:
            topic: Debate topic/question
            agent_ids: List of agent IDs to participate
            num_rounds: Number of debate rounds
            mode: debate | brainstorm | consensus

        Returns:
            DebateResult with all messages
        """
        if not agent_ids:
            raise ValueError("No agents specified for debate")

        debate_id = str(uuid.uuid4())
        logger.info(f"Starting debate {debate_id}: {topic} (mode: {mode}, rounds: {num_rounds})")

        all_messages: List[DebateMessage] = []

        # Round 1: All agents respond to the topic
        round1_messages = await self._run_round(debate_id, 1, topic, [], agent_ids)
        all_messages.extend(round1_messages)

        # Subsequent rounds: Agents respond to previous round
        for round_num in range(2, num_rounds + 1):
            prev_round = [m for m in all_messages if m.round_num == round_num - 1]
            round_messages = await self._run_round(debate_id, round_num, topic, prev_round, agent_ids)
            all_messages.extend(round_messages)

        # Generate final summary
        summary = await self._generate_summary(topic, all_messages)

        result = DebateResult(
            debate_id=debate_id,
            topic=topic,
            mode=mode,
            rounds=num_rounds,
            messages=all_messages,
            final_summary=summary,
            timestamp=datetime.now().isoformat(),
        )

        logger.info(f"Debate {debate_id} completed with {len(all_messages)} messages")
        return result

    async def _run_round(
        self,
        debate_id: str,
        round_num: int,
        topic: str,
        previous_messages: List[DebateMessage],
        agent_ids: List[str],
    ) -> List[DebateMessage]:
        """Run a single debate round.

        Args:
            debate_id: Debate identifier
            round_num: Current round number
            topic: Original debate topic
            previous_messages: Messages from previous rounds
            agent_ids: Agent IDs participating

        Returns:
            List of DebateMessage from this round
        """
        logger.info(f"Running round {round_num} for debate {debate_id}")

        # Build context for agents
        context_parts = [f"주제: {topic}"]

        if previous_messages:
            context_parts.append("\n이전 의견들:")
            for msg in previous_messages:
                context_parts.append(f"- {msg.agent_name}: {msg.content[:150]}...")

        context = "\n".join(context_parts)

        # Get responses from all agents concurrently
        tasks = []
        for agent_id in agent_ids:
            if agent_id not in self.agents:
                logger.warning(f"Agent not found: {agent_id}")
                continue

            agent = self.agents[agent_id]
            task = self._get_agent_debate_response(
                debate_id, round_num, agent, topic, previous_messages
            )
            tasks.append((agent_id, agent.name, task))

        # Run all concurrently with rate limiting
        results = await asyncio.gather(
            *[t[2] for t in tasks],
            return_exceptions=True
        )

        round_messages = []
        for (agent_id, name, _), response in zip(tasks, results):
            if isinstance(response, Exception):
                logger.error(f"Agent {name} error: {response}")
                content = f"[Error] {str(response)}"
            else:
                content = response

            msg = DebateMessage(
                round_num=round_num,
                agent_id=agent_id,
                agent_name=name,
                content=content,
            )
            round_messages.append(msg)

            # Send real-time update if callback is set
            if self._ws_callback:
                try:
                    await self._ws_callback(debate_id, round_num, agent_id, content)
                except Exception as e:
                    logger.error(f"WebSocket callback error: {e}")

        return round_messages

    async def _get_agent_debate_response(
        self,
        debate_id: str,
        round_num: int,
        agent,
        topic: str,
        previous_messages: List[DebateMessage],
    ) -> str:
        """Get a single agent's debate response with rate limiting."""
        async with self.semaphore:
            try:
                # Check if agent has respond_to_debate method
                if hasattr(agent, 'respond_to_debate'):
                    response = await agent.respond_to_debate(
                        topic=topic,
                        previous_messages=[
                            {"agent_id": m.agent_id, "content": m.content}
                            for m in previous_messages
                        ],
                        round_num=round_num,
                    )
                else:
                    # Fallback to regular respond
                    prev_text = "\n".join([
                        f"- {m.agent_name}: {m.content[:100]}"
                        for m in previous_messages
                    ])
                    agent_name = getattr(agent, 'name', 'Agent')
                    prompt = f"""주제: {topic}

이전 의견들:
{prev_text}

{agent_name}으로서 어떻게 생각하나요? 자신의 관점을 명확히 설명하세요."""

                    if hasattr(agent, 'respond'):
                        response = await agent.respond(prompt)
                    else:
                        response = "[Error] Agent does not support respond method"

                return response
            except Exception as e:
                logger.error(f"Error getting response from {agent.name}: {e}")
                return f"[Error] {str(e)}"

    async def _generate_summary(
        self,
        topic: str,
        messages: List[DebateMessage],
    ) -> str:
        """Generate a summary of the debate."""
        if not messages:
            return "No messages in debate"

        summary_parts = [f"주제: {topic}\n"]
        summary_parts.append("토론 요약:\n")

        for msg in messages:
            summary_parts.append(f"- {msg.agent_name} (Round {msg.round_num}): {msg.content[:100]}...")

        return "\n".join(summary_parts)

    def register_agent(self, agent_id: str, agent):
        """Register an agent with the engine."""
        self.agents[agent_id] = agent
        logger.info(f"DebateEngine: Registered agent {agent_id}")

    def __repr__(self):
        return f"<DebateEngine(agents={len(self.agents)})>"