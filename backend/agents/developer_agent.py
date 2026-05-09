"""Developer Agent - Technical role"""

from .base_agent import BaseAgent
from services.deepseek_service import DeepSeekService
import logging

logger = logging.getLogger(__name__)


class DeveloperAgent(BaseAgent):
    """Technical lead agent for development decisions."""

    def __init__(
        self,
        agent_id: str,
        name: str = "Arthur",
        deepseek_service: DeepSeekService = None,
    ):
        """Initialize Developer agent.

        Args:
            agent_id: Unique agent ID
            name: Agent name (default: Developer)
            deepseek_service: DeepSeek service instance for API calls
        """
        system_prompt = """당신은 AI 회사의 개발자입니다. 기술을 좋아하고, 실력 있으며, 팀원들과 함께 일하는 걸 즐깁니다.

전문:
- 웹 개발 (React, Node.js, Python)
- API 만들기와 데이터베이스 설계
- 코드가 느리지 않게 하는 방법
- 보안과 안정성 챙기기

기술적으로 어떻게 구현할지, 어려운 부분은 없는지, 현실적으로 판단해주세요."""

        super().__init__(agent_id, name, "developer", system_prompt)
        self.deepseek = deepseek_service or DeepSeekService()

        # Load SOUL personality
        self._soul_system_prompt = self.get_soul_system_prompt(
            debate_style="analytical"
        )

    async def think(self, context: str) -> str:
        """Process context and generate technical analysis.

        Args:
            context: Conversation context

        Returns:
            Technical analysis
        """
        prompt = f"""다음 대화 상황을 기술적으로 분석하고 개발 관점에서 인사이트를 제공하세요:

{context}

기술적 복잡도, 구현 가능성, 아키텍처 영향을 고려하여 분석하세요."""

        response = await self.deepseek.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
            task_type="architecture",
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
        """Respond to a user message from Developer perspective.

        Args:
            message: User message
            task_type: Type of task (used for model selection)
            complexity: Task complexity score

        Returns:
            Developer's response
        """
        prompt = f"""사용자가 이렇게 물어봤어요: "{message}"

개발자로서 자연스럽게 응답해주세요.
- 어떻게 구현할지 생각나는 대로 이야기하거나
- 기술적으로 어려울 것 같은 점이 있다면 솔직하게 말하거나
- 더 나은 방법이 떠오른다면 제안하거나
너무 기술적인 용어는 피하고, 팀원들도 이해할 수 있게 설명해주세요."""

        response = await self.deepseek.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
            task_type=task_type or "code_review",
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

개발자 관점에서 기술적으로 가장 타당한 선택을 고르고, 이유를 간단히 설명하세요.
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
            Developer's debate response
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

개발자 관점에서 위 의견들을 종합하여 다음과 같이 응답하세요:
{debate_mode_instruction.get(mode, debate_mode_instruction["debate"])}

기술적 복잡도, 구현 시간, 아키텍처 영향을 고려하여 2-3문장으로 응답하세요."""

        response = await self.deepseek.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
            task_type="debate",
            complexity=0.8,
        )

        self.add_to_history("assistant", response)
        return response
