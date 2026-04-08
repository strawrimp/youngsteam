"""
ConversationEngine: Core conversation management system.

Orchestrates multi-agent discussions:
1. Accepts user message
2. Routes to all agents for synchronous opinions
3. Stores conversation history
4. Manages shared memory updates
5. References past conversations for context
"""

import asyncio
import logging
import re
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
        self.conversation_service = None
        self.agents: Dict[str, "BaseAgent"] = {}
        self.semaphore = asyncio.Semaphore(2)  # Rate limit to 2 concurrent GLM calls

    def set_conversation_service(self, service):
        """Set conversation service for archive access."""
        self.conversation_service = service
        logger.info("ConversationService attached to ConversationEngine")

    def register_agent(self, agent_id: str, agent):
        """Register an agent with the engine.

        Args:
            agent_id: Unique agent identifier
            agent: Agent instance
        """
        self.agents[agent_id] = agent
        logger.info(f"✅ Registered agent: {agent_id} ({agent.name})")
        if not self.agents:
            logger.warning(f"⚠️ No agents registered in ConversationEngine")

    def _extract_keywords(self, message: str, max_keywords: int = 3) -> List[str]:
        """Extract keywords from user message for past context search.

        Args:
            message: User message
            max_keywords: Maximum number of keywords to extract

        Returns:
            List of keywords
        """
        # Remove common Korean particles and stopwords
        stopwords = {
            "은",
            "는",
            "이",
            "가",
            "을",
            "를",
            "에",
            "의",
            "와",
            "과",
            "도",
            "만",
            "까지",
            "부터",
            "까지",
            "에서",
            "으로",
            "로",
            "하세요",
            "해주세요",
            "부탁드립니다",
            "입니다",
            "있습니다",
            "the",
            "a",
            "an",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "must",
            "can",
            "to",
            "of",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "as",
            "into",
        }

        # Extract meaningful words (2+ characters, Korean or English)
        words = re.findall(r"[가-힣]{2,}|[a-zA-Z]{3,}", message.lower())

        # Filter stopwords and get unique keywords
        keywords = []
        seen = set()
        for word in words:
            if word not in stopwords and word not in seen and len(word) >= 2:
                keywords.append(word)
                seen.add(word)
                if len(keywords) >= max_keywords:
                    break

        return keywords

    def _search_past_context(self, message: str, limit: int = 3) -> Optional[str]:
        """Search past conversations for relevant context.

        Args:
            message: User message to search for
            limit: Maximum number of past contexts to include

        Returns:
            Formatted context string or None
        """
        if not self.conversation_service:
            return None

        keywords = self._extract_keywords(message)
        if not keywords:
            return None

        context_parts = []
        for keyword in keywords[:2]:  # Search top 2 keywords
            try:
                results = self.conversation_service.search_past_context(
                    keyword, limit=2
                )
                for result in results:
                    # Format: [과거 대화 - 제목] 내용...
                    snippet = result.get("content", "")[:150]
                    if snippet:
                        context_parts.append(
                            f"• {result.get('conversation_title', '제목 없음')}: {snippet}..."
                        )
            except Exception as e:
                logger.error(f"Error searching past context for '{keyword}': {e}")

        if not context_parts:
            return None

        # Deduplicate and limit
        unique_parts = list(dict.fromkeys(context_parts))[:limit]

        return "\n".join(unique_parts)

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

        # Search for past context
        past_context = self._search_past_context(user_message)
        if past_context:
            logger.info(f"Found past context for reference")

        # Get agent responses concurrently with rate limiting
        agent_responses = await self._get_agent_responses(
            user_message, agent_ids, past_context
        )

        result = {
            "conversation_id": conversation_id,
            "user_message": user_message,
            "timestamp": datetime.now().isoformat(),
            "agent_responses": agent_responses,
            "consulted_agents": agent_ids,
            "has_past_context": past_context is not None,
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
            "researcher": [
                "리서처",
                "researcher",
                "연구",
                "research",
                "데이터",
                "data",
                "분석",
            ],
        }

        # Check if Manager is explicitly mentioned
        manager_keywords = ["매니저", "manager", "ceo", "관리자", "리더", "leader"]

        # Check for other specific agent mentions
        mentioned_agents = []
        for role, keywords in agent_keywords.items():
            if any(kw in message_lower for kw in keywords):
                # Find agent ID by role
                for agent_id, agent in self.agents.items():
                    if hasattr(agent, "role") and agent.role == role:
                        mentioned_agents.append(agent_id)
                        break

        # If no specific agent mentioned, use only Manager
        if not mentioned_agents:
            for agent_id, agent in self.agents.items():
                if hasattr(agent, "role") and agent.role == "manager":
                    return [agent_id]

        return mentioned_agents if mentioned_agents else list(self.agents.keys())

    async def _get_agent_responses(
        self,
        message: str,
        agent_ids: List[str],
        past_context: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Get responses from multiple agents concurrently with rate limiting.

        Args:
            message: Message to send to agents
            agent_ids: List of agent IDs
            past_context: Optional past conversation context

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
            task = self._get_agent_response_with_limit(agent_id, message, past_context)
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

    async def _get_agent_response_with_limit(
        self,
        agent_id: str,
        message: str,
        past_context: Optional[str] = None,
    ) -> str:
        """
        Get a single agent response with semaphore rate limiting.

        Args:
            agent_id: Agent ID
            message: Message to process
            past_context: Optional past conversation context

        Returns:
            Agent's response string
        """
        async with self.semaphore:
            agent = self.agents[agent_id]
            logger.info(f"Getting response from {agent.name}")

            try:
                # Build enhanced message with context if available
                enhanced_message = message
                if past_context:
                    enhanced_message = f"""[과거 대화 참고]
{past_context}

[현재 요청]
{message}"""

                response = await agent.respond(enhanced_message)

                # Add context reference indicator if past context was used
                if past_context and len(response) > 50:
                    response = f"{response}\n\n_📌 과거 대화를 참고했습니다_"

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

    def get_conversation_context(
        self, conversation_id: str, limit: int = 20
    ) -> List[Dict]:
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
