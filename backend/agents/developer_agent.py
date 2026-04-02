"""Developer Agent - Technical role"""

from .base_agent import BaseAgent
from services.glm_service import GLMService
import logging

logger = logging.getLogger(__name__)


class DeveloperAgent(BaseAgent):
    """Technical lead agent for development decisions."""

    def __init__(self, agent_id: str, name: str = "Developer", glm_service: GLMService = None):
        """Initialize Developer agent.

        Args:
            agent_id: Unique agent ID
            name: Agent name (default: Developer)
            glm_service: GLM service instance for API calls
        """
        system_prompt = """당신은 AI 회사의 기술 리드입니다. 전문:
- Python, JavaScript, 아키텍처 설계
- 기술적 실현 가능성 평가
- 코드 작성 및 리뷰

기술적 관점에서 현명한 의견을 제시하세요."""

        super().__init__(agent_id, name, "developer", system_prompt)
        self.glm = glm_service or GLMService()

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

        response = await self.glm.call_model(
            system_prompt=self.system_prompt,
            user_message=prompt,
            conversation_history=self.get_history(10),
        )

        self.add_to_history("assistant", response)
        return response

    async def respond(self, message: str) -> str:
        """Respond to a user message from Developer perspective.

        Args:
            message: User message

        Returns:
            Developer's response
        """
        prompt = f"""사용자의 다음 메시지에 개발자 관점에서 응답하세요:

"{message}"

기술적 실현 가능성, 구현 난이도, 아키텍처 영향을 고려한 조언을 제시하세요. (2-3문장)"""

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

개발자 관점에서 기술적으로 가장 타당한 선택을 고르고, 이유를 간단히 설명하세요.
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
