"""Researcher Agent - Research and analysis role"""

from .base_agent import BaseAgent
from services.deepseek_service import DeepSeekService
import logging

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent):
    """Research and data analysis specialist agent."""

    def __init__(
        self,
        agent_id: str,
        name: str = "Luna",
        deepseek_service: DeepSeekService = None,
    ):
        """Initialize Researcher agent.

        Args:
            agent_id: Unique agent ID
            name: Agent name (default: Researcher)
            deepseek_service: DeepSeek service instance for API calls
        """
        system_prompt = """당신은 AI 회사의 리서치 리드입니다. 전문:
- 자료 조사 및 데이터 분석
- 시장 트렌드 및 기술 분석
- 근거 기반 인사이트 제공

데이터와 사실에 기반하여 분석적 의견을 제시하세요."""

        super().__init__(agent_id, name, "researcher", system_prompt)
        self.deepseek = deepseek_service or DeepSeekService()

        # Load SOUL personality
        self._soul_system_prompt = self.get_soul_system_prompt(
            debate_style="analytical"
        )

    async def think(self, context: str) -> str:
        """Process context and generate research insights.

        Args:
            context: Conversation context

        Returns:
            Research analysis
        """
        prompt = f"""다음 대화 상황을 연구/분석 관점에서 분석하고 인사이트를 제공하세요:

{context}

데이터, 시장 동향, 기술 분석을 고려하여 분석하세요."""

        response = await self.deepseek.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
            task_type="analysis",
            complexity=0.8,
        )

        self.add_to_history("assistant", response)
        return response

    async def respond(
        self,
        message: str,
        task_type: str = "default",
        complexity: float = 0.0,
    ) -> str:
        """Respond to a user message from Researcher perspective.

        Args:
            message: User message
            task_type: Type of task (used for model selection)
            complexity: Task complexity score

        Returns:
            Researcher's response
        """
        prompt = f"""사용자의 다음 메시지에 리서처 관점에서 응답하세요:

"{message}"

데이터, 시장 조사, 트렌드 분석을 기반으로 인사이트를 제시하세요. (2-3문장)"""

        response = await self.deepseek.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
            task_type=task_type or "analysis",
            complexity=complexity,
        )

        self.add_to_history("user", message)
        self.add_to_history("assistant", response)
        return response

    async def vote(
        self,
        topic: str,
        candidates: list,
        task_type: str = "voting",
    ) -> dict:
        """Cast a vote on a topic.

        Args:
            topic: Topic to vote on
            candidates: List of candidate choices
            task_type: Type of task (default: 'voting' which requires R1)

        Returns:
            Dict with choice and reasoning
        """
        candidates_str = "\n".join([f"{i + 1}. {c}" for i, c in enumerate(candidates)])

        prompt = f"""주제: {topic}

선택지:
{candidates_str}

리서처 관점에서 데이터와 사실에 기반하여 가장 타당한 선택을 고르고, 이유를 간단히 설명하세요.
형식: "선택: [선택 번호]"로 시작하세요."""

        response = await self.deepseek.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(5),
            task_type=task_type,  # "voting" → uses R1
            complexity=1.0,  # Voting is always high complexity
        )

        # Extract choice from response
        choice = candidates[0]  # Default to first
        for i, candidate in enumerate(candidates, 1):
            if f"선택: {i}" in response or f"선택:{i}" in response:
                choice = candidate
                break

        return {
            "choice": choice,
            "reasoning": response,
        }

    async def respond_to_debate(
        self,
        topic: str,
        previous_messages: list,
        round_num: int,
        mode: str = "debate",
    ) -> str:
        """Respond in a debate considering other agents' views.

        Args:
            topic: Debate topic
            previous_messages: List of previous messages in this debate
            round_num: Current round number
            mode: debate | brainstorm | consensus

        Returns:
            Researcher's debate response
        """
        # Build context from previous messages
        context = f"주제: {topic}\n라운드: {round_num}\n\n이전 의견들:\n"
        for msg in previous_messages[-10:]:  # Last 10 messages for context
            context += (
                f"- {msg.get('agent_name', 'Unknown')}: {msg.get('content', '')}\n"
            )

        debate_mode_instruction = {
            "debate": "상대 의견에 대해 논리적으로 반박하거나 개선안을 제시하세요.",
            "brainstorm": "다른 의견들을 존중하면서 새로운 아이디어를 제안하세요.",
            "consensus": "공통점을 찾아 합의점을 도출하는 방향으로 응답하세요.",
        }

        prompt = f"""{context}

리서처 관점에서 위 의견들을 종합하여 다음과 같이 응답하세요:
{debate_mode_instruction.get(mode, debate_mode_instruction["debate"])}

데이터, 시장 조사, 트렌드 분석을 고려하여 2-3문장으로 응답하세요."""

        response = await self.deepseek.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
            task_type="analysis",
            complexity=0.8,
        )

        self.add_to_history("assistant", response)
        return response
