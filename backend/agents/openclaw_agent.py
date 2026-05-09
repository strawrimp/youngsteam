"""OpenClaw Agent - Gateway bot for delegating real-world tasks to Mac Mini.

This agent is NOT LLM-driven. Instead of calling DeepSeek for responses,
it forwards instructions to the OpenClaw Gateway (WebSocket/HTTP) and
returns the execution results directly.

Architecture:
- Extends BaseAgent with role="bot"
- Injects OpenClawService via closure (callable or instance)
- respond() → execute_instruction() → return output
- think(), vote(), respond_to_debate() return canned responses
"""

from typing import Callable, Optional, Union

from .base_agent import BaseAgent
from services.openclaw_service import OpenClawService
import logging

logger = logging.getLogger(__name__)


class OpenClawAgent(BaseAgent):
    """Bot agent that delegates real-world tasks to OpenClaw Gateway on Mac Mini.

    Unlike LLM-driven agents (Manager/Developer/etc.), OpenClawAgent does not
    call DeepSeek for responses. It forwards instructions to the OpenClaw
    Gateway and returns results directly.
    """

    def __init__(
        self,
        agent_id: str,
        name: str = "Claw",
        openclaw_service: Optional[
            Union[OpenClawService, Callable[[], OpenClawService]]
        ] = None,
    ):
        """Initialize OpenClaw bot agent.

        Dependency injection supports both direct instances and closures
        (lambdas) for lazy resolution and circular-import safety.

        Args:
            agent_id: Unique agent ID (typically "openclaw-bot")
            name: Agent name (default: Claw)
            openclaw_service: OpenClawService instance or callable returning one
        """
        system_prompt = (
            "당신은 Mac Mini 게이트웨이 '클로(Claw)'입니다. 역할:\n"
            "- OpenClaw Gateway를 통한 실제 기기 작업 위임\n"
            "- WebSocket 연결 관리 및 명령 실행\n"
            "- 실세계 태스크 실행 결과 보고\n\n"
            "실제 기기 작업이 필요할 때 현실적인 판단과 정확한 실행이 중요합니다."
        )

        super().__init__(agent_id, name, "bot", system_prompt)
        self.use_deepseek_tool_use = False  # Bot agent: bypass AgentTaskExecutor
        self._openclaw_service = openclaw_service

    def _get_service(self) -> Optional[OpenClawService]:
        """Resolve OpenClawService from injection (instance or callable).

        Returns:
            OpenClawService if available, None if not configured.
        """
        if self._openclaw_service is None:
            return None
        if callable(self._openclaw_service):
            return self._openclaw_service()
        return self._openclaw_service

    async def respond(
        self,
        message: str,
        task_type: str = "default",
        complexity: float = 0.0,
    ) -> str:
        """Execute instruction via OpenClaw Gateway and return result.

        This is the primary entry point. The message is forwarded to the
        OpenClaw Gateway as a natural-language instruction, and the
        execution result (success/failure + output) is returned as text.

        Args:
            message: Natural language instruction for the gateway
            task_type: Unused (bot agent ignores model selection)
            complexity: Unused (bot agent ignores complexity scoring)

        Returns:
            Gateway response text, or error message if execution fails.
        """
        service = self._get_service()
        if service is None:
            return (
                "❌ OpenClaw Gateway가 설정되지 않았습니다. "
                "OPENCLAW_ENABLED 환경변수를 확인하세요."
            )

        # 먼저 연결 가능 여부를 빠르게 확인 (5s timeout each for WS/HTTP)
        # Mac Mini Gateway가 오프라인일 때 긴 시간(최대 180s) 기다리지 않도록 함
        try:
            available = await service.is_available()
            if not available:
                return (
                    "🔌 **클로(Claw)가 연결할 Mac Mini를 찾을 수 없습니다.**\n\n"
                    "현재 OpenClaw Gateway에 접속할 수 없습니다. 다음을 확인해주세요:\n\n"
                    f"• Mac Mini의 전원이 켜져 있는지 확인해주세요\n"
                    f"• Mac Mini와 같은 네트워크에 연결되어 있는지 확인해주세요\n"
                    f"• 게이트웨이 주소({service.base_url})가 올바른지 확인해주세요\n\n"
                    "네트워크 연결을 확인한 후 다시 시도해주세요 😊"
                )
        except Exception as e:
            # is_available() 자체가 실패해도 execute_instruction() 시도는 허용
            logger.warning(f"[OpenClawAgent] availability check failed: {e}")

        try:
            result = await service.execute_instruction(
                instruction=message,
                agent_name=self.name,
            )

            if result.get("success"):
                output = result.get("output", "")
                actions = result.get("actions_taken", [])
                if actions:
                    action_lines = "\n".join(f"  • {a}" for a in actions)
                    return f"{output}\n\n실행된 작업:\n{action_lines}"
                return output or "✅ 명령이 실행되었습니다."
            else:
                error = result.get("error", "알 수 없는 오류")
                return (
                    f"❌ OpenClaw 실행 실패: {error}\n\n"
                    "Mac Mini의 전원과 네트워크 연결을 확인한 후 다시 시도해주세요."
                )

        except Exception as e:
            logger.error(f"[OpenClawAgent] respond() error: {e}")
            return (
                f"❌ OpenClaw 게이트웨이 연결 중 오류가 발생했습니다.\n\n"
                f"• 상세: {str(e)}\n"
                f"• Mac Mini의 전원과 네트워크 연결을 확인해주세요\n"
                f"• 게이트웨이 주소({service.base_url})가 올바른지 확인해주세요\n\n"
                "문제가 지속되면 시스템 관리자에게 문의해주세요."
            )

    async def think(self, context: str) -> str:
        """OpenClawAgent does not perform internal reasoning.

        Returns:
            Canned message indicating the bot cannot think independently.
        """
        return (
            "🔧 클로는 명령 실행 전용 봇입니다. "
            "독립적인 사고가 필요하면 @매니저를 호출해주세요."
        )

    async def vote(
        self,
        topic: str,
        candidates: list,
        task_type: str = "voting",
    ) -> dict:
        """OpenClawAgent does not participate in voting.

        Args:
            topic: Unused
            candidates: Unused
            task_type: Unused

        Returns:
            Dict with choice=None and explanation that bot cannot vote.
        """
        return {
            "choice": None,
            "reasoning": "🔧 클로는 봇 에이전트로 투표에 참여할 수 없습니다.",
        }

    async def respond_to_debate(
        self,
        topic: str,
        previous_messages: list,
        round_num: int,
        mode: str = "debate",
    ) -> str:
        """OpenClawAgent does not participate in debates.

        Args:
            topic: Unused
            previous_messages: Unused
            round_num: Unused
            mode: Unused

        Returns:
            Canned message indicating the bot cannot debate.
        """
        return (
            "🔧 클로는 토론에 참여할 수 없는 봇 에이전트입니다. "
            "필요한 경우 실제 기기 명령을 요청해주세요."
        )
