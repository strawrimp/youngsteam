"""OpenClaw Gateway HTTP 클라이언트."""

import httpx
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class OpenClawService:
    """OpenClaw Gateway API 클라이언트.

    OpenClaw Gateway는 OpenAI 호환이 아닌 자체 엔드포인트 사용.
    API 타입: anthropic-messages (OpenAI chat completions 아님)
    """

    def __init__(
        self,
        base_url: str = "http://localhost:4242",
        api_key: str = "",
        timeout: float = 180.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def health_check(self) -> bool:
        """OpenClaw Gateway 도달 가능 여부 확인."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"OpenClaw health check failed: {e}")
            return False

    async def execute_instruction(
        self,
        instruction: str,
        context: Optional[Dict[str, Any]] = None,
        agent_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """OpenClaw에 작업 지시 전달.

        Args:
            instruction: 자연어 지시 (예: 'Gmail로 테스트 메일 보내기')
            context: 추가 컨텍스트
            agent_name: 호출한 에이전트 이름

        Returns:
            Dict: {"success": bool, "output": str, "actions_taken": List[str], "error": str}
        """
        # TODO: 실제 API 호출 구현 (Phase 2에서)
        pass