"""delegate_to_openclaw tool - executes real-world tasks via Mac Mini OpenClaw."""

import logging
from typing import Any, Dict
from tools.base_tool import BaseTool, ToolResult
from services.openclaw_service import get_openclaw_service

logger = logging.getLogger(__name__)


class OpenClawTool(BaseTool):
    """Tool to delegate real-world tasks to OpenClaw on Mac Mini."""

    @property
    def name(self) -> str:
        return "delegate_to_openclaw"

    @property
    def description(self) -> str:
        return (
            "실세계 작업(이메일 발송, GitHub 조작, 캘린더 일정, 파일 시스템 조작, "
            "브라우저 자동화, 스마트홈 제어 등)을 Mac Mini의 OpenClaw에 위임한다. "
            "단순 정보 조회는 다른 툴을 사용하고, 외부 시스템에 변경을 가하는 작업에만 사용할 것."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "instruction": {
                    "type": "string",
                    "description": "OpenClaw에 전달할 자연어 지시 (예: 'GitHub에 버그 이슈 생성: 제목: ..., 본문: ...')",
                },
                "expected_outcome": {
                    "type": "string",
                    "description": "기대하는 결과의 한 줄 요약 (성공 검증용)",
                },
            },
            "required": ["instruction"],
        }

    async def execute(self, instruction: str, expected_outcome: str = "") -> ToolResult:
        """Execute by delegating to OpenClaw.

        Args:
            instruction: OpenClaw에 전달할 자연어 지시
            expected_outcome: 기대 결과 (선택)

        Returns:
            ToolResult with success status and output
        """
        service = get_openclaw_service()
        if service is None:
            return ToolResult(
                success=False,
                output="",
                error="OpenClaw 서비스를 사용할 수 없습니다 (OPENCLAW_ENABLED=false)",
            )

        if not await service.is_available():
            return ToolResult(
                success=False,
                output="",
                error=f"OpenClaw Gateway({service.BASE_URL})에 연결할 수 없습니다",
            )

        try:
            result = await service.execute_instruction(
                instruction=instruction,
                context={"expected_outcome": expected_outcome} if expected_outcome else None,
            )

            if result.get("success"):
                return ToolResult(
                    success=True,
                    output=result.get("output", "Completed"),
                    metadata={"actions_taken": result.get("actions_taken", [])},
                )
            else:
                return ToolResult(
                    success=False,
                    output="",
                    error=result.get("error", "Unknown error"),
                )

        except Exception as e:
            logger.error(f"OpenClaw delegation error: {e}")
            return ToolResult(
                success=False,
                output="",
                error=f"OpenClaw delegation failed: {str(e)}",
            )