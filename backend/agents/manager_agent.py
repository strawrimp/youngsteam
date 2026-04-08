"""Manager Agent - CEO role"""

from .base_agent import BaseAgent
from services.deepseek_service import DeepSeekService
import logging

logger = logging.getLogger(__name__)


class ManagerAgent(BaseAgent):
    """CEO/Manager agent for strategic decisions."""

    def __init__(
        self,
        agent_id: str,
        name: str = "Manager",
        deepseek_service: DeepSeekService = None,
    ):
        """Initialize Manager agent.

        Args:
            agent_id: Unique agent ID
            name: Agent name (default: Manager)
            deepseek_service: DeepSeek service instance for API calls
        """
        # Use SOUL-based system prompt
        system_prompt = """당신은 AI 회사의 CEO입니다. 너무 격식적이지 말고 자연스럽게 대화하세요.

역할:
- 팀원들과 함께 고민하고 해결책을 찾는 리더
- 다양한 의견을 듣고 가장 좋은 방향을 제안
- 프로젝트 진행 상황을 챙 챙 확인
- 회사가 더 나아질 수 있도록 고민

대화 스타일:
- 친근하고 이해하기 쉬운 말투
- "우리", "함께" 같은 표현 사용
- 어려운 용어는 피하고 쉬운 말로 설명
- 걱정되는 점이나 고민을 솔직하게 공유

전문 분야:
- 어떤 기능을 먼저 만들지 고민
- 팀원들과 어떻게 협업하면 좋을지 생각
- 프로젝트 일정이나 우선순위 정하기
- 회사 방향성에 대해 팀원들과 소통

다른 팀원들의 의견을 존중하고, 함께 최선의 결정을 내려봐요."""

        super().__init__(agent_id, name, "manager", system_prompt)
        self.deepseek = deepseek_service or DeepSeekService()

        # Load SOUL personality
        self._soul_system_prompt = self.get_soul_system_prompt(debate_style="assertive")

    async def think(self, context: str) -> str:
        """Process context and generate strategic insights.

        Args:
            context: Conversation context

        Returns:
            Strategic analysis
        """
        prompt = f"""다음 대화 상황을 분석하고 전략적 관점에서 인사이트를 제공하세요:

{context}

당신의 전략적 분석을 간결하게 제시하세요."""

        response = await self.deepseek.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
            task_type="strategy",
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
        """Respond to a user message from CEO perspective.


        매개변수:
                    message: 사용자 메시지
                    task_type: 작업 유형 (모델 선택에 사용)
                    complexity: 작업 복잡도 점수

        반환값:
                    CEO의 응답
        """
        prompt = f"""사용자가 이렇게 물어봤어요: "{message}"

리더로서 자연스럽고 친근하게 응답해주세요. 
- 무슨 고민이 있는지 물어보거나
- 팀원들과 어떻게 해결하면 좋을지 제안하거나
- 우선순위나 일정에 대해 이야기해주세요.
너무 격식적인 표현은 피하고, 대화하듯 말해주세요."""

        response = await self.deepseek.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
            task_type="debate",
            complexity=0.8,
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

CEO 관점에서 가장 전략적인 선택을 고르고, 이유를 간단히 설명하세요.
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
            Manager's debate response
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

CEO 관점에서 위 의견들을 종합하여 다음과 같이 응답하세요:
{debate_mode_instruction.get(mode, debate_mode_instruction["debate"])}

전략적 판단을 바탕으로 2-3문장으로 응답하세요."""

        response = await self.deepseek.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
            task_type="debate",
            complexity=0.8,
        )

        self.add_to_history("assistant", response)
        return response
