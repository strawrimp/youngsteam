"""
ConversationEngine: Core conversation management system.

Orchestrates multi-agent discussions:
1. Accepts user message
2. Routes to all agents for synchronous opinions
3. Stores conversation history
4. Manages shared memory updates
"""

import asyncio
import logging
from typing import List, Dict, Optional
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class ConversationEngine:
    """Manages conversations and agent interactions."""

    def __init__(self, db_session=None):
        """Initialize conversation engine.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.agents: Dict[str, 'BaseAgent'] = {}
        self.semaphore = asyncio.Semaphore(2)  # Rate limit to 2 concurrent GLM calls

    def register_agent(self, agent_id: str, agent):
        """Register an agent with the engine.

        Args:
            agent_id: Unique agent identifier
            agent: Agent instance
        """
        self.agents[agent_id] = agent
        logger.info(f"Registered agent: {agent_id} ({agent.name})")

    async def process_message(
        self,
        conversation_id: str,
        user_message: str,
        agent_ids: Optional[List[str]] = None,
    ) -> Dict:
        """
        Process a user message through all agents.

        Args:
            conversation_id: Conversation ID
            user_message: User's input message
            agent_ids: List of agent IDs to consult (defaults to all)

        Returns:
            Dict with conversation results and agent responses
        """
        if not user_message.strip():
            return {"error": "Empty message"}

        # Determine which agents to consult
        if agent_ids is None:
            agent_ids = self._determine_agents(user_message)

        logger.info(f"Processing message in conversation {conversation_id}")
        logger.info(f"Consulting agents: {agent_ids}")

        # Get agent responses concurrently with rate limiting
        agent_responses = await self._get_agent_responses(user_message, agent_ids)

        result = {
            "conversation_id": conversation_id,
            "user_message": user_message,
            "timestamp": datetime.now().isoformat(),
            "agent_responses": agent_responses,
            "consulted_agents": agent_ids,
        }

        return result

    def _determine_agents(self, user_message: str) -> List[str]:
        """
        Determine which agents should respond based on the message.
        
        If no specific agent is mentioned, only Manager responds.
        
        Args:
            user_message: User's input message
            
        Returns:
            List of agent IDs to consult
        """
        message_lower = user_message.lower()
        
        # Map keywords to agent roles
        agent_keywords = {
            "developer": ["개발자", "developer", "dev", "코드", "code", "기술", "tech"],
            "designer": ["디자이너", "designer", "design", "디자인", "ui", "ux"],
            "researcher": ["리서처", "researcher", "연구", "research", "데이터", "data", "분석"],
        }
        
        # Check if Manager is explicitly mentioned
        manager_keywords = ["매니저", "manager", "ceo", "ceo", "관리자", "리더", "leader"]
        manager_mentioned = any(kw in message_lower for kw in manager_keywords)
        
        # Check for other specific agent mentions
        mentioned_agents = []
        for role, keywords in agent_keywords.items():
            if any(kw in message_lower for kw in keywords):
                # Find agent ID by role
                for agent_id, agent in self.agents.items():
                    if agent.role == role:
                        mentioned_agents.append(agent_id)
                        break
        
        # If no specific agent mentioned, use only Manager
        if not mentioned_agents:
            for agent_id, agent in self.agents.items():
                if agent.role == "manager":
                    return [agent_id]
        
        return mentioned_agents if mentioned_agents else list(self.agents.keys())

    async def _get_agent_responses(
        self,
        message: str,
        agent_ids: List[str],
    ) -> Dict[str, str]:
        """
        Get responses from multiple agents concurrently with rate limiting.

        Args:
            message: Message to send to agents
            agent_ids: List of agent IDs

        Returns:
            Dict mapping agent IDs to their responses
        """
        logger.info(f"_get_agent_responses called with {len(agent_ids)} agents")
        
        tasks = []
        for agent_id in agent_ids:
            if agent_id not in self.agents:
                logger.warning(f"Agent not found: {agent_id}")
                continue

            logger.info(f"Creating task for agent {agent_id}")
            task = self._get_agent_response_with_limit(agent_id, message)
            tasks.append(task)

        logger.info(f"Starting asyncio.gather for {len(tasks)} tasks")
        
        # Run all tasks concurrently
        responses_list = await asyncio.gather(*tasks, return_exceptions=True)

        logger.info(f"asyncio.gather completed")

        # Map responses back to agent IDs
        responses = {}
        for agent_id, response in zip(agent_ids, responses_list):
            if isinstance(response, Exception):
                logger.error(f"Agent {agent_id} error: {response}")
                responses[agent_id] = f"[Error] {str(response)}"
            else:
                responses[agent_id] = response

        logger.info(f"Returning {len(responses)} responses")
        return responses

    async def _get_agent_response_with_limit(self, agent_id: str, message: str) -> str:
        """
        Get a single agent response with semaphore rate limiting.

        Args:
            agent_id: Agent ID
            message: Message to process

        Returns:
            Agent's response string
        """
        async with self.semaphore:
            agent = self.agents[agent_id]
            logger.info(f"Getting response from {agent.name}")

            try:
                response = await agent.respond(message)
                logger.info(f"{agent.name} responded: {response[:100]}...")
                return response
            except Exception as e:
                logger.error(f"Error from {agent.name}: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return f"[Error] {str(e)}"

    async def start_voting(
        self,
        conversation_id: str,
        topic: str,
        candidates: List[str],
        agent_ids: Optional[List[str]] = None,
    ) -> Dict:
        """
        Start a voting process for a topic.

        Args:
            conversation_id: Conversation ID
            topic: Topic to vote on
            candidates: List of candidate choices
            agent_ids: Agents to vote (defaults to all)

        Returns:
            Dict with voting results
        """
        if agent_ids is None:
            agent_ids = list(self.agents.keys())

        logger.info(f"Starting voting on topic: {topic}")
        logger.info(f"Candidates: {candidates}")

        votes = {}
        for agent_id in agent_ids:
            if agent_id not in self.agents:
                continue

            agent = self.agents[agent_id]
            try:
                vote = await agent.vote(topic, candidates)
                votes[agent_id] = vote
                logger.info(f"{agent.name} voted: {vote.get('choice', 'unknown')}")
            except Exception as e:
                logger.error(f"Voting error for {agent.name}: {e}")
                votes[agent_id] = {"choice": "abstain", "reasoning": str(e)}

        return {
            "conversation_id": conversation_id,
            "topic": topic,
            "candidates": candidates,
            "votes": votes,
            "timestamp": datetime.now().isoformat(),
        }

    def get_conversation_context(self, conversation_id: str, limit: int = 20) -> List[Dict]:
        """
        Get recent conversation context (sliding window).

        Args:
            conversation_id: Conversation ID
            limit: Max messages to retrieve

        Returns:
            List of recent messages
        """
        # This will be integrated with database in Phase 3
        # For now, returns empty list
        return []

    def __repr__(self):
        return f"<ConversationEngine(agents={len(self.agents)})>"
