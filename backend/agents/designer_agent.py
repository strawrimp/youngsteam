"""Designer Agent - Design and UX role"""

from .base_agent import BaseAgent
from services.deepseek_service import DeepSeekService
import logging

logger = logging.getLogger(__name__)


class DesignerAgent(BaseAgent):
    """Design and UX specialist agent."""

    def __init__(
        self,
        agent_id: str,
        name: str = "Sophia",
        deepseek_service: DeepSeekService = None,
    ):
        """Initialize Designer agent.

        Args:
            agent_id: Unique agent ID
            name: Agent name (default: Designer)
            deepseek_service: DeepSeek service instance for API calls
        """
        system_prompt = """당신은 AI 회사의 디자인 리드입니다. 전문:
- UI/UX 설계 및 사용자 경험
- 시각적 일관성 및 브랜드 가이드
- 접근성 및 인터페이스 설계

디자인 관점에서 통찰력 있는 의견을 제시하세요."""

        super().__init__(agent_id, name, "designer", system_prompt)
        self.deepseek = deepseek_service or DeepSeekService()

        # Load SOUL personality
        self._soul_system_prompt = self.get_soul_system_prompt(
            debate_style="diplomatic"
        )

    async def think(self, context: str) -> str:
        """Process context and generate design insights.

        Args:
            context: Conversation context

        Returns:
            Design analysis
        """
        prompt = f"""다음 대화 상황을 디자인/UX 관점에서 분석하고 인사이트를 제공하세요:

{context}

사용자 경험, 인터페이스 설계, 시각적 일관성을 고려하여 분석하세요."""

        response = await self.deepseek.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
            task_type="insight",
            complexity=0.6,
        )

        self.add_to_history("assistant", response)
        return response

    async def respond(
        self,
        message: str,
        task_type: str = "default",
        complexity: float = 0.0,
    ) -> str:
        """Respond to a user message from Designer perspective.

        Args:
            message: User message
            task_type: Type of task (used for model selection)
            complexity: Task complexity score

        Returns:
            Designer's response
        """
        prompt = f"""사용자의 다음 메시지에 디자인/UX 관점에서 응답하세요:

"{message}"

사용자 경험, 인터페이스 설계, 시각적 미학을 고려한 제안을 제시하세요. (2-3문장)"""

        response = await self.deepseek.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
            task_type=task_type or "default",
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

디자인/UX 관점에서 사용자 경험이 가장 좋은 선택을 고르고, 이유를 간단히 설명하세요.
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
            Designer's debate response
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

디자인/UX 관점에서 위 의견들을 종합하여 다음과 같이 응답하세요:
{debate_mode_instruction.get(mode, debate_mode_instruction["debate"])}

사용자 경험, 인터페이스 설계, 시각적 미학을 고려하여 2-3문장으로 응답하세요."""

        response = await self.deepseek.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
            task_type="debate",
            complexity=0.8,
        )

        self.add_to_history("assistant", response)
        return response
