# OpenClaw 연동 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** OpenClaw Gateway를 Mac Mini에서 my-ai-company 에이전트의 실세계 작업 수행 백엔드로 연결

**Architecture:**
- `delegate_to_openclaw` 툴을 에이전트의 툴 레지스트리에 추가
- OpenClaw Gateway에 자연어 지시 전달 → 50+ 실세계 툴으로 실행
- Phase 1: 연결 검증 → Phase 2: 위임 실행 → Phase 3: 프론트엔드 → Phase 4: 안정화

**Tech Stack:** Python (httpx async), FastAPI, 기존 푣 패턴 재사용

---

## 파일 구조

```
backend/
├── config.py                    # OpenClaw 환경변수 추가
├── services/
│   ├── openclaw_service.py      # Gateway HTTP 클라이언트 (신규)
│   └── deepseek_service.py       # 참고: httpx 패턴
├── tools/
│   ├── __init__.py              # OpenClawTool 등록
│   ├── base_tool.py              # BaseTool 추상 클래스
│   ├── openclaw_tool.py          # delegate_to_openclaw 툴 (신규)
│   └── web_search.py             # 참고: 외부 API 호출 예시
├── services/agent_executor.py   # 툴 주입 + 시스템 프롬프트 수정
├── main.py                       # OpenClaw 상태 추적 (살짝)
└── scripts/
    └── test_openclaw_connection.py  # 연결 테스트 (신규)
```

---

## Task 1: config.py에 OpenClaw 환경변수 추가

**Files:**
- Modify: `backend/config.py:44-50` (Settings 클래스 내, environment 필드 뒤)

- [ ] **Step 1: config.py 수정하여 OpenClaw 설정 추가**

```python
# 환경변수 섹션 뒤에 추가 (line 46 이후)
# OpenClaw Integration (Mac Mini)
openclaw_enabled: bool = False
openclaw_base_url: str = "http://localhost:4242"
openclaw_api_key: str = ""
openclaw_timeout: float = 180.0
openclaw_fallback_host: str = ""
```

---

## Task 2: openclaw_service.py 작성

**Files:**
- Create: `backend/services/openclaw_service.py`

- [ ] **Step 1: 기본 클래스 구조 작성**

```python
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
```

- [ ] **Step 2: 커밋**

```bash
git add backend/services/openclaw_service.py
git commit -m "feat(openclaw): initial OpenClawService class with health_check"
```

---

## Task 3: test_openclaw_connection.py 작성

**Files:**
- Create: `backend/scripts/test_openclaw_connection.py`

- [ ] **Step 1: 연결 테스트 스크립트 작성**

```python
#!/usr/bin/env python3
"""Test OpenClaw Gateway connection."""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from config import settings
from services.openclaw_service import OpenClawService


async def main():
    print("Testing OpenClaw Gateway connection...")
    print(f"Base URL: {settings.openclaw_base_url}")
    print(f"Enabled: {settings.openclaw_enabled}")

    if not settings.openclaw_enabled:
        print("❌ OPENCLAW_ENABLED=false — skipping test")
        return

    service = OpenClawService(
        base_url=settings.openclaw_base_url,
        api_key=settings.openclaw_api_key,
        timeout=settings.openclaw_timeout,
    )

    # Try health check
    print("\n[1] Running health check...")
    try:
        result = await service.health_check()
        if result:
            print("✅ OpenClaw Gateway is reachable!")
        else:
            print("❌ OpenClaw Gateway health check failed")
            print("   Possible causes:")
            print("   - OpenClaw not running on Mac Mini")
            print("   - Network connectivity issue")
            print("   - Wrong OPENCLAW_BASE_URL")
    except Exception as e:
        print(f"❌ Error: {e}")

    # Try fallback host if configured
    if settings.openclaw_fallback_host:
        print(f"\n[2] Trying fallback host: {settings.openclaw_fallback_host}")
        # TODO: Implement fallback

if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 2: 실행 권한 부여 및 테스트**

```bash
chmod +x backend/scripts/test_openclaw_connection.py
python backend/scripts/test_openclaw_connection.py
```

- [ ] **Step 3: 커밋**

```bash
git add backend/scripts/test_openclaw_connection.py
git commit -m "feat(openclaw): add connection test script"
```

---

## Task 4: openclaw_tool.py 작성

**Files:**
- Create: `backend/tools/openclaw_tool.py`

- [ ] **Step 1: OpenClawTool 클래스 작성**

```python
"""delegate_to_openclaw tool - executes real-world tasks via Mac Mini OpenClaw."""

import logging
from typing import Any, Dict
from tools.base_tool import BaseTool, ToolResult

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
        from config import settings
        from services.openclaw_service import OpenClawService

        if not settings.openclaw_enabled:
            return ToolResult(
                success=False,
                output="",
                error="OpenClaw integration is disabled (OPENCLAW_ENABLED=false)",
            )

        try:
            service = OpenClawService(
                base_url=settings.openclaw_base_url,
                api_key=settings.openclaw_api_key,
                timeout=settings.openclaw_timeout,
            )

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
```

- [ ] **Step 2: 커밋**

```bash
git add backend/tools/openclaw_tool.py
git commit -m "feat(openclaw): add OpenClawTool for real-world task delegation"
```

---

## Task 5: tools/__init__.py 수정

**Files:**
- Modify: `backend/tools/__init__.py`

- [ ] **Step 1: OpenClawTool import 및 등록 추가**

```python
# 기존 imports에 추가
from tools.openclaw_tool import OpenClawTool

# __all__에 추가
__all__ = [
    # ... existing tools ...
    "OpenClawTool",
    "get_all_tools",
]

# get_all_tools() 함수 수정 - OpenClawTool 조건부 추가
def get_all_tools() -> list["BaseTool"]:
    """Return all available tools."""
    from config import settings

    tools = [
        WebSearchTool(),
        WebScrapeTool(),
        CodeExecutorTool(),
        YouTubeTranscriptTool(),
        FileOperationsTool(),
    ]

    # OpenClawTool 조건부 등록
    if getattr(settings, "openclaw_enabled", False):
        tools.append(OpenClawTool())

    return tools
```

- [ ] **Step 2: 커밋**

```bash
git add backend/tools/__init__.py
git commit -m "feat(openclaw): register OpenClawTool in get_all_tools()"
```

---

## Task 6: agent_executor.py 수정

**Files:**
- Modify: `backend/services/agent_executor.py:84-94` (tool_registry 빌드 부분)

- [ ] **Step 1: 시스템 프롬프트에 OpenClaw 사용 가이드 추가**

이 파일의 `_build_system_prompt` 메서드 찾기 (약 line 150-200 구간 예상)

```python
# _build_system_prompt 메서드 내, 툴 목록 설명 뒤에 추가:
# (이미 tools 설명 부분이 있음)
TOOL_GUIDE = """
## OpenClaw Tool (실세계 작업 위임)
외부 시스템에 변경을 가하는 작업(메일 발송, GitHub 조작, 파일 작성 등)이 필요하면 `delegate_to_openclaw` 툴을 사용하라.
단순 정보 조회는 web_search를 사용하라.
"""
```

- [ ] **Step 2: 커밋**

```bash
git add backend/services/agent_executor.py
git commit -m "feat(openclaw): add OpenClaw usage guide to system prompt"
```

---

## Task 7: main.py에 OpenClaw 상태 추적 추가

**Files:**
- Modify: `backend/main.py` (startup 로그 부분)

- [ ] **Step 1: 시작 시 OpenClaw 헬스체크 추가 (line 92 근처)**

```python
# DeepSeekService 초기화 후 추가
if settings.openclaw_enabled:
    from services.openclaw_service import OpenClawService

    openclaw_service = OpenClawService(
        base_url=settings.openclaw_base_url,
        api_key=settings.openclaw_api_key,
        timeout=settings.openclaw_timeout,
    )

    # Health check async
    try:
        oc_healthy = await openclaw_service.health_check()
        if oc_healthy:
            logger.info(f"✅ OpenClaw Gateway reachable at {settings.openclaw_base_url}")
        else:
            logger.warning(f"⚠️ OpenClaw Gateway not reachable at {settings.openclaw_base_url}")
    except Exception as e:
        logger.warning(f"⚠️ OpenClaw health check failed: {e}")
else:
    logger.info("   OpenClaw: DISABLED")
```

- [ ] **Step 2: 커밋**

```bash
git add backend/main.py
git commit -m "feat(openclaw): add OpenClaw health check on startup"
```

---

## Task 8: .env.example에 OpenClaw 설정 추가

**Files:**
- Modify: `.env.example` (기존 설정 뒤에)

- [ ] **Step 1: OpenClaw 설정 추가**

```bash
# OpenClaw Integration (Mac Mini)
OPENCLAW_ENABLED=false
OPENCLAW_BASE_URL=http://localhost:4242
OPENCLAW_API_KEY=
OPENCLAW_TIMEOUT=180
OPENCLAW_FALLBACK_HOST=
```

- [ ] **Step 2: 커밋**

```bash
git add .env.example
git commit -m "feat(openclaw): add OpenClaw config to .env.example"
```

---

## Task 9: execute_instruction 구현 (Phase 2 핵심)

**Files:**
- Modify: `backend/services/openclaw_service.py`

- [ ] **Step 1: 실제 API 호출 구현**

```python
async def execute_instruction(
    self,
    instruction: str,
    context: Optional[Dict[str, Any]] = None,
    agent_name: Optional[str] = None,
) -> Dict[str, Any]:
    """OpenClaw에 작업 지시 전달."""
    headers = {}
    if self.api_key:
        headers["Authorization"] = f"Bearer {self.api_key}"

    # OpenClaw Gateway는 anthropic-messages 형식 사용
    # (OpenAI /v1/chat/completions 아님)
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
            # OpenClaw Gateway의 실제 엔드포인트 확인 필요
            # 아래는 임시 경로 - openclaw gateway status 확인 후 수정
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

        # 응답 파싱 (OpenClaw 실제 응답 형식에 맞게 조정 필요)
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
    # 간단한 파싱 - 실제 구현 시 개선 필요
    actions = []
    for line in content.split("\n"):
        if line.strip().startswith("-"):
            actions.append(line.strip().lstrip("- ").strip())
    return actions
```

- [ ] **Step 2: 커밋**

```bash
git add backend/services/openclaw_service.py
git commit -m "feat(openclaw): implement execute_instruction with proper API call"
```

---

## 검증을 위한 E2E 시나리오

모든 태스크 완료 후:

1. **백엔드 실행:**
   ```bash
   cd backend && python -m uvicorn main:app --reload --port 7521
   ```

2. **프론트엔드 실행:**
   ```bash   cd frontend && npm run dev
   ```

3. **브라우저에서 테스트:**
   - "내 Gmail 임시함에 테스트 메일 만들어줘" 요청
   - TaskPanel에서 `delegate_to_openclaw` 단계 확인

4. **연결 테스트 스크립트 실행:**
   ```bash
   python backend/scripts/test_openclaw_connection.py
   ```

---

**Plan 완료 및 저장:** `docs/superpowers/plans/2026-05-01-openclaw-integration-plan.md`

---

**실행 옵션:**

**1. Subagent-Driven (권장)** - 태스크별 fresh subagent + 2단계 리뷰

**2. Inline Execution** - executing-plans로 체크포인트 리뷰しながら 실행

어떤 방식으로 진행하시겠습니까?

---

**작업 담당자: @Sisyphus 👑**