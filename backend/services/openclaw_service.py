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
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        payload = {
            "model": "openclaw-default",
            "messages": [
                {
                    "role": "user",
                    "content": f"""You are an action agent. Execute the requested task using available tools.

Task: {instruction}
{f'Context: {context}' if context else ''}
{f'Agent: {agent_name}' if agent_name else ''}

Report what you did in this format:
- actions_taken: list of actions performed
- success: true/false
- output: what happened""",
                }
            ],
            "stream": False,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/v1/chat/completions",
                    json=payload,
                    headers=headers,
                )

            if response.status_code != 200:
                return {
                    "success": False,
                    "output": "",
                    "actions_taken": [],
                    "error": f"OpenClaw API error {response.status_code}: {response.text}",
                }

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            return {
                "success": True,
                "output": content,
                "actions_taken": self._parse_actions(content),
                "error": "",
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "output": "",
                "actions_taken": [],
                "error": "OpenClaw request timed out",
            }
        except Exception as e:
            logger.error(f"OpenClaw execute_instruction error: {e}")
            return {
                "success": False,
                "output": "",
                "actions_taken": [],
                "error": str(e),
            }

    def _parse_actions(self, content: str) -> list:
        """응답에서 수행한 액션 목록 파싱."""
        actions = []
        for line in content.split("\n"):
            if line.strip().startswith("-"):
                actions.append(line.strip().lstrip("- ").strip())
        return actions

    def _parse_actions(self, content: str) -> list:
        """응답에서 수행한 액션 목록 파싱."""
        actions = []
        for line in content.split("\n"):
            if line.strip().startswith("-"):
                actions.append(line.strip().lstrip("- ").strip())
        return actions