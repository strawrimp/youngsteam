"""Manager Agent - CEO role"""

from .base_agent import BaseAgent
from services.glm_service import GLMService
import logging

logger = logging.getLogger(__name__)


class ManagerAgent(BaseAgent):
    """CEO/Manager agent for strategic decisions."""

    def __init__(self, agent_id: str, name: str = "Manager", glm_service: GLMService = None):
        """Initialize Manager agent.

        Args:
            agent_id: Unique agent ID
            name: Agent name (default: Manager)
            glm_service: GLM service instance for API calls
        """
        system_prompt = """당신은 AI 회사의 CEO입니다. 역할:
- 전략 수립 및 우선순위 결정
- 팀원들의 의견을 종합하여 최종 판단
- 목표 수립 및 진행 상황 추적

다른 팀원들의 의견을 고려하여 현명한 결정을 내리세요."""

        super().__init__(agent_id, name, "manager", system_prompt)
        self.glm = glm_service or GLMService()

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

        response = await self.glm.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
        )

        self.add_to_history("assistant", response)
        return response

    async def respond(self, message: str) -> str:
        """Respond to a user message from CEO perspective.

        Args:
            message: User message

        Returns:
            CEO's response
        """
        prompt = f"""사용자의 다음 메시지에 CEO 관점에서 응답하세요:

"{message}"

전략, 비전, 우선순위 측면에서 현명한 조언을 제시하세요. (2-3문장)"""

        response = await self.glm.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
        )

        self.add_to_history("user", message)
        self.add_to_history("assistant", response)
        return response

    async def vote(self, topic: str, candidates: list) -> dict:
        """Cast a vote on a topic.

        Args:
            topic: Topic to vote on
            candidates: List of candidate choices

        Returns:
            Dict with choice and reasoning
        """
        candidates_str = "\n".join([f"{i+1}. {c}" for i, c in enumerate(candidates)])

        prompt = f"""주제: {topic}

선택지:
{candidates_str}

CEO 관점에서 가장 전략적인 선택을 고르고, 이유를 간단히 설명하세요.
형식: "선택: [선택 번호]"로 시작하세요."""

        response = await self.glm.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(5),
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
