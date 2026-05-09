"""
ConversationEngine: Core conversation management system.

Orchestrates multi-agent discussions:
1. Accepts user message
2. Routes to all agents with Tool Use (web_search, execute_python)
3. Stores conversation history
4. Manages shared memory updates
5. References past conversations for context

All agent responses now go through AgentTaskExecutor for real tool usage.
"""

import asyncio
import logging
import re
from typing import List, Dict, Optional, Callable
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
        self.semaphore = asyncio.Semaphore(
            4
        )  # Rate limit: up to 4 concurrent LLM calls (all agents)
        self.deepseek_service = None  # Injected via set_deepseek_service()
        self.live_discussion_engine = (
            None  # LiveDiscussionEngine injected via set_live_discussion_engine()
        )

    def set_conversation_service(self, service):
        """Set conversation service for archive access."""
        self.conversation_service = service
        logger.info("ConversationService attached to ConversationEngine")

    def set_deepseek_service(self, service):
        """Set DeepSeek service for tool use execution.

        Args:
            service: DeepSeekService instance
        """
        self.deepseek_service = service
        logger.info("DeepSeekService attached to ConversationEngine for Tool Use")

    def set_live_discussion_engine(self, engine):
        """Set LiveDiscussionEngine for chain-style discussions.

        Args:
            engine: LiveDiscussionEngine instance
        """
        self.live_discussion_engine = engine
        logger.info("LiveDiscussionEngine attached to ConversationEngine")

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
        step_callback: Optional[Callable] = None,
        force_discussion: bool = False,
        image_context: Optional[str] = None,
    ) -> Dict:
        """
        Process a user message through all agents with Tool Use.

        If force_discussion=True or discussion keywords detected,
        routes to LiveDiscussionEngine for chain-style discussion.

        Args:
            conversation_id: Conversation ID
            user_message: User's input message
            agent_ids: List of agent IDs to consult (defaults to all)
            step_callback: Optional callback(agent_id, agent_name, step_dict) for real-time step streaming
            force_discussion: Force chain-style discussion mode
            image_context: Optional context about attached images

        Returns:
            Dict with conversation results and agent responses.
            For discussion mode, returns {discussion_mode: True, discussion_id: str}
        """
        if not user_message.strip():
            return {"error": "Empty message"}

        # ★ 이미지 컨텍스트가 있으면 메시지에 추가
        effective_message = user_message
        if image_context:
            effective_message = f"{user_message}\n\n{image_context}"

        # Check if LiveDiscussion is active for this conversation
        if self.live_discussion_engine and self.live_discussion_engine.is_discussing(
            conversation_id
        ):
            return {
                "error": "이미 토론이 진행 중입니다. 잠시 기다려주세요.",
                "discussion_active": True,
            }

        # Check for discussion intent
        is_discussion = force_discussion or self._detect_discussion_intent(user_message)

        if is_discussion and self.live_discussion_engine:
            logger.info(f"[Discussion] Detected discussion intent: {user_message[:50]}")

            # Extract topic — remove trigger keywords
            topic = self._extract_discussion_topic(user_message)

            discussion_info = await self.live_discussion_engine.start_discussion(
                topic=topic,
                conversation_id=conversation_id,
                num_rounds=2,
                force_discussion=force_discussion,
            )

            return {
                "discussion_mode": True,
                "discussion_id": discussion_info.discussion_id,
                "topic": topic,
                "conversation_id": conversation_id,
            }

        # Normal chat flow
        # Determine which agents to consult
        if agent_ids is None:
            agent_ids = self._determine_agents(user_message)

        logger.info(f"Processing message in conversation {conversation_id}")
        logger.info(f"Consulting agents: {agent_ids}")

        # Search for past context
        past_context = self._search_past_context(user_message)
        if past_context:
            logger.info(f"Found past context for reference")

        # ★ 공유 컨텍스트 + 참조 코드 + 과거 대화 처리
        shared_context, referenced_context, past_conversation_context = (
            self._build_shared_contexts(conversation_id, user_message)
        )

        # Get agent responses concurrently with rate limiting
        agent_responses = await self._get_agent_responses(
            effective_message,
            agent_ids,
            past_context,
            step_callback,
            shared_context=shared_context,
            referenced_context=referenced_context,
            past_conversation_context=past_conversation_context,
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

    def _build_shared_contexts(self, conversation_id: str, user_message: str) -> tuple:
        """공유 컨텍스트, 참조 컨텍스트, 과거 대화 컨텍스트를 생성합니다.

        Returns:
            (shared_context, referenced_context, past_conversation_context) 튜플
        """
        from services.shared_context_builder import (
            build_live_context,
            detect_reference_codes,
            build_referenced_context,
            detect_natural_time_reference,
            build_past_context_by_date,
        )

        shared_context = ""
        referenced_context = ""
        past_conversation_context = ""

        try:
            # 1. 현재 대화 공유 컨텍스트
            shared_context = build_live_context(conversation_id, limit=20)
            if shared_context:
                logger.info(
                    f"[SharedContext] Built live context for {conversation_id} "
                    f"({len(shared_context)} chars)"
                )

            # 2. 참조 코드 감지 및 로드
            ref_codes = detect_reference_codes(user_message)
            if ref_codes:
                logger.info(f"[SharedContext] Detected reference codes: {ref_codes}")
                referenced_context = build_referenced_context(ref_codes)
                if referenced_context:
                    logger.info(
                        f"[SharedContext] Loaded referenced context ({len(referenced_context)} chars)"
                    )

            # 3. 자연어 시간 키워드 감지 → 과거 대화 검색
            time_ref = detect_natural_time_reference(user_message)
            if time_ref:
                date_from_str = time_ref["date_from"].strftime("%Y-%m-%d")
                date_to_str = time_ref["date_to"].strftime("%Y-%m-%d")
                logger.info(
                    f"[SharedContext] Detected time reference: '{time_ref['time_keyword']}' "
                    f"→ {date_from_str} ~ {date_to_str}"
                )
                raw_past_context = build_past_context_by_date(
                    date_from=time_ref["date_from"],
                    date_to=time_ref["date_to"],
                    keywords=time_ref.get("keywords"),
                )
                if raw_past_context:
                    # ★ 왜 이 대화를 가져왔는지 에이전트에게 명시
                    past_conversation_context = (
                        f"[사용자가 '{time_ref['time_keyword']}' 대화를 요청했습니다 — "
                        f"검색 기간: {date_from_str} ~ {date_to_str}]\n\n"
                        f"{raw_past_context}"
                    )
                    logger.info(
                        f"[SharedContext] Loaded past conversation context "
                        f"({len(past_conversation_context)} chars)"
                    )

        except Exception as e:
            logger.error(f"[SharedContext] Error building contexts: {e}")

        return shared_context, referenced_context, past_conversation_context

    def _determine_agents(self, user_message: str) -> List[str]:
        """
        Determine which agents should respond based on the message.

        By default, ALL agents respond. If specific agents are @mentioned
        or keyword-matched, only those agents respond.

        Args:
            user_message: User's input message

        Returns:
            List of agent IDs to consult
        """
        message_lower = user_message.lower()

        # Map keywords to agent roles (names + titles + domain keywords)
        agent_keywords = {
            "manager": [
                # 이름
                "네오",
                "neo",
                # 직함
                "비서실장",
            ],
            "developer": [
                # 이름
                "아서",
                "arthur",
                # 직함
                "개발부장",
                # 도메인 키워드
                "개발자",
                "developer",
                "dev",
                "코드",
                "code",
                "기술",
                "tech",
                "개발",
            ],
            "designer": [
                # 이름
                "소피아",
                "sophia",
                # 직함
                "디자이너",
                # 도메인 키워드
                "designer",
                "design",
                "디자인",
                "ui",
                "ux",
            ],
            "researcher": [
                # 이름
                "루나",
                "luna",
                # 직함
                "연구소장",
                # 도메인 키워드
                "리서처",
                "researcher",
                "연구",
                "research",
                "데이터",
                "data",
                "분석",
            ],
            "bot": [
                # ✨ 명시적 이름 기반 호출만 지원 (오탐 방지)
                # 이를 통해 "@클로", "클로야", "claw", "@openclaw" 등이 자동 라우팅됨
                # 일반 키워드(실행/터미널/명령/mac)는 제거 → 개발자/매니저 질문 오탐 방지
                "클로",
                "claw",
                "openclaw",
            ],
        }

        # Check for specific agent mentions via keywords
        mentioned_agents = []
        for role, keywords in agent_keywords.items():
            matched_kws = [kw for kw in keywords if kw in message_lower]
            if matched_kws:
                logger.info(f"[Routing] Keywords {matched_kws} matched role '{role}'")
                for agent_id, agent in self.agents.items():
                    if hasattr(agent, "role") and agent.role == role:
                        mentioned_agents.append(agent_id)
                        logger.info(
                            f"[Routing] → Agent {agent.name} (id={agent_id}, role={agent.role})"
                        )
                        break
                else:
                    logger.warning(
                        f"[Routing] No registered agent found for role '{role}'"
                    )

        # ★ "모든 에이전트" / "전원" / "다들" / "팀 전체" 감지 → 전원 참여
        all_agent_keywords = [
            "모든 에이전트",
            "모든 직원",
            "모두",
            "전원",
            "다들",
            "팀 전체",
            "다 같이",
            "다함께",
            "모든 팀원",
            "전체 회의",
            "전체 의견",
            "everyone",
            "all agents",
            "all team",
        ]
        if any(kw in message_lower for kw in all_agent_keywords):
            all_ids = list(self.agents.keys())
            logger.info(
                f"[Routing] 'All agents' keyword detected → all {len(all_ids)} agents responding"
            )
            return all_ids

        # If specific agents mentioned, only those respond
        if mentioned_agents:
            logger.info(f"[Routing] Targeted agents: {mentioned_agents}")
            return mentioned_agents

        # Default: 네오(manager)만 응답 — 직함/이름 언급 시에만 해당 에이전트 참여
        for agent_id, agent in self.agents.items():
            if hasattr(agent, "role") and agent.role == "manager":
                logger.info(
                    f"[Routing] No agent keywords — default to manager: {agent.name}"
                )
                return [agent_id]

        # manager가 없으면 첫 번째 에이전트
        fallback = list(self.agents.keys())
        logger.warning(f"[Routing] No manager found — fallback to: {fallback[:1]}")
        return fallback[:1]

    def _detect_discussion_intent(self, user_message: str) -> bool:
        """사용자 메시지에서 토론 의도를 감지합니다.

        키워드: "토론해줘", "토론 시작", "논의해줘", "의견 나눠", "discuss" 등

        Args:
            user_message: 사용자 메시지

        Returns:
            토론 의도 여부
        """
        message_lower = user_message.lower()
        discussion_keywords = [
            "토론해줘",
            "토론해줘요",
            "토론 시작",
            "토론시작",
            "논의해줘",
            "논의해줘요",
            "논의해 주세요",
            "의견 나눠",
            "의견 나눠줘",
            "의견을 나눠",
            "토론해 보자",
            "토론해보자",
            "함께 논의",
            "같이 논의",
            "같이 토론",
            "discuss",
            "debate",
            "brainstorm",
            "모두의 의견",
            "전체 의견",
            "팀 토론",
            "라운드 테이블",
            "회의해줘",
            "회의 해줘",
            "모두 물어봐",
            "다 물어봐",
            "전원 토론",
        ]
        return any(kw in message_lower for kw in discussion_keywords)

    async def _get_agent_responses(
        self,
        message: str,
        agent_ids: List[str],
        past_context: Optional[str] = None,
        step_callback: Optional[Callable] = None,
        shared_context: str = "",
        referenced_context: str = "",
        past_conversation_context: str = "",
    ) -> Dict[str, str]:
        """
        Get responses from multiple agents concurrently with rate limiting.

        Args:
            message: Message to send to agents
            agent_ids: List of agent IDs
            past_context: Optional past conversation context
            step_callback: Optional callback for real-time step streaming
            shared_context: Formatted live conversation context (all agents' messages)
            referenced_context: Referenced conversation context from #C- codes
            past_conversation_context: Past conversation context from natural language time references

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
            task = self._get_agent_response_with_limit(
                agent_id,
                message,
                past_context,
                step_callback,
                shared_context=shared_context,
                referenced_context=referenced_context,
                past_conversation_context=past_conversation_context,
            )
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
        step_callback: Optional[Callable] = None,
        shared_context: str = "",
        referenced_context: str = "",
        past_conversation_context: str = "",
    ) -> str:
        """
        Get a single agent response with semaphore rate limiting via AgentTaskExecutor.

        All chat responses now go through the Tool Use pipeline:
        AgentTaskExecutor → DeepSeek function calling → tools (web_search, execute_python)

        Args:
            agent_id: Agent ID
            message: Message to process
            past_context: Optional past conversation context
            step_callback: Optional callback(agent_id, agent_name, step_dict) for real-time streaming
            shared_context: Formatted live conversation context (all agents' messages)
            referenced_context: Referenced conversation context from #C- codes
            past_conversation_context: Past conversation context from natural language time references

        Returns:
            Agent's final response string
        """
        async with self.semaphore:
            agent = self.agents[agent_id]
            logger.info(
                f"[Tool Use] Getting response from {agent.name} (role: {agent.role})"
            )

            try:
                # ★ Bot agent (e.g. OpenClawAgent): bypass AgentTaskExecutor entirely
                if not agent.use_deepseek_tool_use:
                    enhanced_message = message
                    if past_context:
                        enhanced_message = f"""[과거 대화 참고]
{past_context}

[현재 요청]
{message}"""

                    response = await agent.respond(enhanced_message)

                    if past_context and len(response) > 50:
                        response = f"{response}\n\n_📌 과거 대화를 참고했습니다_"

                    agent.add_to_history("user", enhanced_message)
                    agent.add_to_history("assistant", response)

                    logger.info(
                        f"[BotAgent] {agent.name} responded (direct, no Tool Use): {response[:100]}..."
                    )
                    return response

                # --- Tool Use Path (AgentTaskExecutor) ---
                if self.deepseek_service is not None:
                    from services.agent_executor import AgentTaskExecutor, TaskStep

                    # Build enhanced message with context if available
                    enhanced_message = message
                    if past_context:
                        enhanced_message = f"""[과거 대화 참고]
{past_context}

[현재 요청]
{message}"""

                    # Get SOUL prompt for this agent
                    soul_prompt = agent.get_soul_system_prompt()

                    # Create per-agent step callback wrapper
                    def on_step(step: TaskStep):
                        if step_callback:
                            step_callback(
                                agent_id,
                                agent.name,
                                {
                                    "type": step.type,
                                    "content": step.content,
                                    "tool_name": step.tool_name,
                                    "tool_args": step.tool_args,
                                    "success": step.success,
                                },
                            )

                    executor = AgentTaskExecutor(
                        deepseek_service=self.deepseek_service,
                        on_step=on_step,
                    )

                    # Get conversation history from the agent
                    conversation_history = agent.get_history(limit=10)

                    result = await executor.execute_task(
                        task=enhanced_message,
                        agent_name=agent.name,
                        agent_role=agent.role,
                        soul_prompt=soul_prompt,
                        conversation_history=conversation_history,
                        shared_context=shared_context,
                        referenced_context=referenced_context,
                        past_conversation_context=past_conversation_context,
                    )

                    # Save to agent's conversation history
                    agent.add_to_history("user", enhanced_message)
                    agent.add_to_history("assistant", result.final_response)

                    # Add context reference indicator if past context was used
                    response = result.final_response
                    if past_context and len(response) > 50:
                        tool_count = sum(
                            1 for s in result.steps if s.type == "tool_call"
                        )
                        if tool_count > 0:
                            response = f"{response}\n\n_🔧 {tool_count}개의 도구를 활용했습니다_"
                        response = f"{response}\n\n_📌 과거 대화를 참고했습니다_"

                    logger.info(
                        f"[Tool Use] {agent.name} responded ({len(result.steps)} steps): {response[:100]}..."
                    )
                    return response

                # --- Fallback: simple respond() if no deepseek_service ---
                else:
                    logger.warning(
                        f"No DeepSeekService — falling back to agent.respond() for {agent.name}"
                    )

                    enhanced_message = message
                    if past_context:
                        enhanced_message = f"""[과거 대화 참고]
{past_context}

[현재 요청]
{message}"""

                    response = await agent.respond(enhanced_message)

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

    def _extract_discussion_topic(self, user_message: str) -> str:
        """토론 트리거 키워드를 제거하고 주제를 추출합니다.

        Args:
            user_message: 원본 사용자 메시지

        Returns:
            정제된 토론 주제
        """
        import re

        topic = user_message

        # 토론 트리거 키워드 패턴 제거
        remove_patterns = [
            r"모두에게?\s*물어봐\s*주세요\.?",
            r"모두의?\s*의견을?\s*들려주세요\.?",
            r"전원\s*토론\s*해주세요\.?",
            r"팀\s*토론\s*해주세요\.?",
            r"함께\s*논의\s*해\s*주세요\.?",
            r"같이\s*논의\s*해\s*주세요\.?",
            r"같이\s*토론\s*해\s*주세요\.?",
            r"토론\s*해\s*주세요\.?",
            r"토론\s*해\s*줘\.?",
            r"토론\s*해\s*줘요\.?",
            r"토론\s*해\s*보자\.?",
            r"토론\s*시작\s*해\s*주세요\.?",
            r"토론해\s*주세요\.?",
            r"토론해\s*줘\.?",
            r"토론해\s*줘요\.?",
            r"토론해\s*보자\.?",
            r"토론시작",
            r"논의\s*해\s*주세요\.?",
            r"논의\s*해\s*줘\.?",
            r"논의\s*해\s*줘요\.?",
            r"의견\s*나눠\s*주세요\.?",
            r"의견\s*나눠\s*줘\.?",
            r"의견을\s*나눠\s*주세요\.?",
            r"discuss\s*(please)?",
            r"debate\s*(please)?",
            r"brainstorm\s*(please)?",
            r"회의\s*해\s*주세요\.?",
            r"회의해\s*줘\.?",
        ]

        for pattern in remove_patterns:
            topic = re.sub(pattern, "", topic, flags=re.IGNORECASE).strip()

        # 남은 내용이 없으면 원본 사용
        if not topic or len(topic) < 3:
            topic = user_message

        return topic

    def __repr__(self):
        return f"<ConversationEngine(agents={len(self.agents)})>"
