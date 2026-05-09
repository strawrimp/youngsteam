"""Agent task executor - runs agents with tools using DeepSeek function calling."""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from services.deepseek_service import DeepSeekService
from tools import get_all_tools
from tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 8  # Max tool call iterations to prevent infinite loops


@dataclass
class TaskStep:
    """A single step in task execution."""

    type: str  # 'thinking', 'tool_call', 'tool_result', 'response'
    content: str
    tool_name: str = ""
    tool_args: Dict = field(default_factory=dict)
    success: bool = True


@dataclass
class TaskExecutionResult:
    """Final result of executing a task."""

    success: bool
    final_response: str
    steps: List[TaskStep]
    agent_name: str
    agent_role: str
    task: str
    tokens_used: int = 0

    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "final_response": self.final_response,
            "steps": [
                {
                    "type": s.type,
                    "content": s.content,
                    "tool_name": s.tool_name,
                    "tool_args": s.tool_args,
                    "success": s.success,
                }
                for s in self.steps
            ],
            "agent_name": self.agent_name,
            "agent_role": self.agent_role,
            "task": self.task,
        }


class AgentTaskExecutor:
    """Executes tasks using an agent's SOUL prompt + DeepSeek function calling.

    This is the core "real work" engine:
    1. Loads the agent's SOUL system prompt
    2. Gives the agent access to tools (web search, code execution)
    3. Runs a tool-calling loop until the agent completes the task
    4. Returns all steps taken + final response
    """

    def __init__(
        self,
        deepseek_service: DeepSeekService,
        tools: Optional[List[BaseTool]] = None,
        on_step: Optional[Callable[[TaskStep], None]] = None,
    ):
        """
        Args:
            deepseek_service: DeepSeek service instance
            tools: List of tools to give the agent (default: all tools)
            on_step: Optional callback called after each step (for real-time streaming)
        """
        self.deepseek = deepseek_service
        self.tools = tools or get_all_tools()
        self.on_step = on_step

        # Build tool registry for fast lookup
        self.tool_registry: Dict[str, BaseTool] = {
            tool.name: tool for tool in self.tools
        }

        # Build function schemas for DeepSeek
        self.tool_schemas = [tool.to_function_schema() for tool in self.tools]

    async def execute_task(
        self,
        task: str,
        agent_name: str,
        agent_role: str,
        soul_prompt: str,
        conversation_history: Optional[List[Dict]] = None,
        shared_context: str = "",
        referenced_context: str = "",
        past_conversation_context: str = "",
    ) -> TaskExecutionResult:
        """Execute a task for an agent with tool use.

        Args:
            task: The task description/instruction
            agent_name: Agent's name (for display)
            agent_role: Agent's role (manager, developer, designer, researcher)
            soul_prompt: Agent's SOUL system prompt
            conversation_history: Previous conversation context
            shared_context: Formatted live conversation context (all agents' messages)
            referenced_context: Referenced conversation context from #C- codes
            past_conversation_context: Past conversation context from natural language time references

        Returns:
            TaskExecutionResult with all steps and final response
        """
        steps: List[TaskStep] = []
        messages: List[Dict] = list(conversation_history or [])

        # Build system prompt combining SOUL + context + tool instructions
        system_prompt = self._build_system_prompt(
            soul_prompt,
            agent_role,
            shared_context=shared_context,
            referenced_context=referenced_context,
            past_conversation_context=past_conversation_context,
        )

        # Direct task message — identity is now in system prompt,
        # so no need to block self-intro here (user can ask names directly)
        task_message = task

        logger.info(f"[{agent_name}] Starting task: {task[:80]!r}")

        # Tool calling loop
        for round_num in range(MAX_TOOL_ROUNDS):
            # Build API call parameters
            # Round 0: pass conversation_history + user_message separately
            # Round 1+: pass full messages (including tool results) as conversation_history,
            #           with empty user_message (tool results are already in messages)
            if round_num == 0:
                api_history = messages
                api_user_msg = task_message
            else:
                # messages already contains: user, assistant(+tool_calls), tool results
                # Send as conversation_history so call_model_with_tools builds full context
                api_history = messages
                api_user_msg = ""

            result = await self.deepseek.call_model_with_tools(
                system_prompt=system_prompt,
                user_message=api_user_msg,
                tools=self.tool_schemas,
                conversation_history=api_history,
                task_type="default",
            )

            # After first round, we pass messages differently
            # Add assistant's response to message history
            if round_num == 0:
                messages.append({"role": "user", "content": task_message})

            content = result.get("content", "")
            tool_calls = result.get("tool_calls", [])

            # Record assistant thinking/response
            if content:
                step = TaskStep(
                    type="thinking" if tool_calls else "response",
                    content=content,
                )
                steps.append(step)
                if self.on_step:
                    self.on_step(step)

            # Add assistant message to history
            messages.append(
                {
                    "role": "assistant",
                    "content": content or "",
                    **(
                        {
                            "tool_calls": result.get("raw_message", {}).get(
                                "tool_calls", []
                            )
                        }
                        if tool_calls
                        else {}
                    ),
                }
            )

            # If no tool calls, we're done
            if not tool_calls:
                logger.info(
                    f"[{agent_name}] Task complete after {round_num + 1} rounds"
                )
                return TaskExecutionResult(
                    success=True,
                    final_response=content,
                    steps=steps,
                    agent_name=agent_name,
                    agent_role=agent_role,
                    task=task,
                )

            # Execute each tool call
            tool_results_for_message = []
            for tc in tool_calls:
                tool_name = tc["name"]
                tool_args = tc["arguments"]
                tool_id = tc["id"]

                # Record tool call step
                call_step = TaskStep(
                    type="tool_call",
                    content=f"{tool_name} 호출 중...",
                    tool_name=tool_name,
                    tool_args=tool_args,
                )
                steps.append(call_step)
                if self.on_step:
                    self.on_step(call_step)

                # Execute the tool
                tool = self.tool_registry.get(tool_name)
                if not tool:
                    tool_result = ToolResult(
                        success=False,
                        output="",
                        error=f"Unknown tool: {tool_name}",
                    )
                else:
                    try:
                        logger.info(
                            f"[{agent_name}] Calling tool: {tool_name}({tool_args})"
                        )
                        tool_result = await tool.execute(**tool_args)
                    except Exception as e:
                        logger.error(f"Tool execution error: {e}")
                        tool_result = ToolResult(
                            success=False,
                            output="",
                            error=f"Tool error: {str(e)}",
                        )

                # Record tool result step
                result_step = TaskStep(
                    type="tool_result",
                    content=tool_result.to_string(),
                    tool_name=tool_name,
                    tool_args=tool_args,
                    success=tool_result.success,
                )
                steps.append(result_step)
                if self.on_step:
                    self.on_step(result_step)

                tool_results_for_message.append(
                    {
                        "tool_call_id": tool_id,
                        "role": "tool",
                        "name": tool_name,
                        "content": tool_result.to_string(),
                    }
                )

            # Add tool results to message history
            messages.extend(tool_results_for_message)

            # Continue to next loop iteration — the next call_model_with_tools
            # at the top of the loop will process tool results naturally
            task_message = ""

            logger.info(f"[{agent_name}] Tools executed, continuing to next round")

        # Max rounds reached
        logger.warning(f"[{agent_name}] Max tool rounds ({MAX_TOOL_ROUNDS}) reached")
        last_content = steps[-1].content if steps else "업무를 완료하지 못했습니다."
        return TaskExecutionResult(
            success=True,
            final_response=last_content,
            steps=steps,
            agent_name=agent_name,
            agent_role=agent_role,
            task=task,
        )

    def _build_system_prompt(
        self,
        soul_prompt: str,
        role: str,
        shared_context: str = "",
        referenced_context: str = "",
        past_conversation_context: str = "",
    ) -> str:
        """Build system prompt combining SOUL + role context + tool instructions.

        2026-04-27 업데이트 — 모든 에이전트가 일목요연한 결과물을 출력하도록 지침 강화.
        
        3대 원칙 (3C):
        1️⃣ Clear — 구조화된 포맷으로 명확하게 전달할 것  
        2️⃣ Concise — 불필요한 서론/자기소개 없이 핵심부터 말할 것  
        3️⃣ Complete — 표/리스트/코드블록으로 빠짐없이 정리할 것  

        4단계 출력 포맷 (적용 가능한 경우):
        ① 헤더/제목 — 주제를 명확히 표시  
        ② 본문 — 표·리스트·코드블록으로 구조화  
        ③ 비교/분석 — 수치·근거 포함  
        ④ 결론/추천 — 최종 의견과 액션 아이템 제시  
        
        2026-04-27 업데이트 끝.
        
        3대 원칙 (3C):
        1️⃣ Clear — 구조화된 포맷으로 명확하게 전달할 것  
        2️⃣ Concise — 불필요한 서론/자기소개 없이 핵심부터 말할 것  
        3️⃣ Complete — 표/리스트/코드블록으로 빠짐없이 정리할 것  

## 도구 사용 가이드
다음 도구들을 활용하여 업무를 수행하세요:
- **web_search**: 최신 정보, 뉴스, 사실 확인이 필요할 때 사용
- **execute_python**: 계산, 데이터 분석, 알고리즘 구현이 필요할 때 사용
- **youtube_transcript**: YouTube 영상의 자막을 추출하고 분석해야 할 때 사용. YouTube URL이 포함된 요청이나 영상 내용 분석 요청 시 활용하세요.
- **delegate_to_openclaw**: 외부 시스템에 변경을 가하는 작업(이메일 발송, GitHub 조작, 파일 작성 등)이 필요할 때 사용. 단순 정보 조회는 web_search를 사용하세요.

        
        

Key design:

The system prompt must prioritize RESPONDING to the user's

actual message over personality expression. SOUL prompt is used as a

personality/tone guide, NOT as the entire system prompt.

"""
        role_identities = {
            "manager": {"name": "네오(Neo)", "title": "비서실장"},
            "developer": {"name": "아서(Arthur)", "title": "개발부장"},
            "designer": {"name": "소피아(Sophia)", "title": "디자이너"},
            "researcher": {"name": "루나(Luna)", "title": "연구소장"},
        }
        identity = role_identities.get(role, {"name": "AI", "title": "어시스턴트"})

        # Team members roster — all known agents in the company
        team_members = {
            "manager": {"name": "네오(Neo)", "role": "비서실장", "desc": "전략 기획, 의사결정, 팀 조율"},
            "developer": {"name": "아서(Arthur)", "role": "개발부장", "desc": "소프트웨어 개발, 코드 리뷰, 기술 설계"},
            "designer": {"name": "소피아(Sophia)", "role": "디자이너", "desc": "UI/UX 디자인, 시각적 구성, 사용자 경험"},
            "researcher": {"name": "루나(Luna)", "role": "연구소장", "desc": "데이터 분석, 리서치, 정보 수집"},
            "openclaw": {"name": "클로(Clo)", "role": "Mac Mini 게이트웨이", "desc": "실세계 작업 위임 (이메일, GitHub, 파일 조작, 브라우저 등)"},
        }

        now = datetime.now()
        today_str = now.strftime("%Y년 %m월 %d일 (%A)")
        time_str = now.strftime("%H:%M")

        identity_section = f"""# 당신의 정체성

당신은 AI 회사의 {identity["title"]} '{identity["name"]}'입니다.

- 기본적으로 본인({identity["name"]}, {identity["title"]})만 소개하세요.
- 불필요하게 팀 전체를 나열하지는 마세요. 당신은 {identity["name"]} 한 명입니다.
- 단, 사용자가 특정 팀원을 언급하거나 "팀원 소개"를 요청하면 아래 팀 정보를 활용해 안내할 수 있습니다.
- 실세계 작업(이메일, GitHub, 파일 저장 등) 문의 시 "클로(Clo)"에게 요청하도록 안내하세요.

# 현재 시각

오늘: {today_str}
현재 시간: {time_str}

이 정보를 바탕으로 "어제", "지난주", "최근" 등의 시간 표현을 정확히 파악하세요."""

        # Core behavior instruction - ALWAYS respond to the actual message
        core_instruction = """# 지시사항

사용자의 질문이나 요청에 직접적으로 답변하세요.

규칙:

1. 사용자가 무엇을 물어보면 그것에 대해 바로 답변하세요
2. 대화 시작 시 불필요한 자기소개나 "어떤 도움이 필요하신가요" 금지
3. 단, 사용자가 직접 이름이나 직책을 물어보면 답변하세요
4. 일상적인 질문(날씨, 안부 등)에는 일상적으로 답변하세요
5. "안녕"에는 "안녕하세요! 😊" 정도로 답하세요
6. 전략/프로젝트 관련 질문에는 전략적 관점에서 답변하세요
7. 다른 팀원이 한 발언을 인용하거나 동의/반박할 수 있습니다
8. ⭐ 모든 답변은 반드시 **일목요연하게 정리된 결과물**로 출력하세요!
   - 표(markdown table), 리스트(bullet/numbered), 코드블록을 적극 활용할 것
   - 서론 없이 핵심부터 말하고, 구조화된 형태로 전달할 것
   - 비교가 필요한 항목은 반드시 표로 정리할 것
   - 결론에는 최종 추천과 액션 아이템을 포함할 것
9. ⭐ 출력 포맷 원칙 (3C):
   - **Clear** (명확하게) — 구조화된 포맷으로 한눈에 이해되게
   - **Concise** (간결하게) — 불필요한 설명 생략하고 핵심 먼저
   - **Complete** (완전하게) — 빠진 정보 없이 표/리스트로 총망라
        10. ⭐ 4단계 출력 템플릿 (적용 가능한 주제):
     ① 헤더/제목 섹션 — 지금 다루는 주제를 명확히 표시
     ② 본문 정보 — 표·리스트·코드블록으로 구조화하여 제시
     ③ 비교/분석 섹션 — 수치와 근거를 포함한 객관적 분석
     ④ 결론 및 추천 — 최종 의견과 구체적인 액션 아이템 제시

# 🦾 실세계 작업 위임 (OpenClaw)

외부 시스템에 변경을 가하는 작업이 필요하면 `delegate_to_openclaw` 툴을 사용하라:

- 이메일 발송, 캘린더 일정 관리 → `delegate_to_openclaw`
- GitHub 이슈/PR 생성, 코드 제출 → `delegate_to_openclaw`
- 브라우저 자동화, 웹사이트 조작 → `delegate_to_openclaw`
- 파일 시스템 조작 (로컬 서버 외) → `delegate_to_openclaw`
- 스마트홈 제어 → `delegate_to_openclaw`

    단, **단순 정보 조회**는 `web_search`를 사용하라 ( OpenClaw는 사용하지 말 것).
파괴적 작업(삭제, 발송 등)은 실행 전 사용자에게 확인하라.
"""

        # Build the full system prompt
        tool_usage_section = """
# 툴 사용 가이드

사용 가능한 툴:
- web_search: 인터넷 검색 (단순 정보 조회 시 사용)
- web_scrape: 웹페이지 내용 추출
- code_executor: Python 코드 실행
- youtube_transcript: YouTube 자막 가져오기
- file_operations: 파일 읽기/쓰기/검색
- delegate_to_openclaw: 실세계 작업 위임 (이메일, GitHub, 캘린더, 브라우저 등)

툴 호출 방법:
1. 작업을 수행하려면 툴을 선택하고 필요한 매개변수를 제공하세요
2. 툴 실행 결과를 바탕으로 다음 행동을 결정하세요
3. 더 이상 툴 호출이 필요 없으면 최종 응답을 반환하세요
"""

        # Build the team roster section
        team_lines = ["# 🏢 팀 구성원", "", "우리 AI 회사는 5명의 팀원이 함께 일하고 있습니다:", ""]
        team_lines.append("| 호출명 | 이름 | 역할 | 설명 |")
        team_lines.append("|--------|------|------|------|")
        for key, member in team_members.items():
            mention = f"@{key}" if key == "openclaw" else key
            team_lines.append(f"| `{mention}` | {member['name']} | {member['role']} | {member['desc']} |")
        team_lines.append("")
        team_lines.append("참고:")
        team_lines.append("- 사용자가 Mac Mini 작업, 외부 시스템 조작(이메일, GitHub, 파일 저장 등)을 요청하면 `@클로`를 사용하도록 안내하세요.")
        team_lines.append("- `delegate_to_openclaw` 툴로 직접 클로에게 작업을 위임할 수도 있습니다.")
        team_lines.append("- 사용자가 \"팀원을 소개해달라\"고 하면 위 표를 참고하여 간략히 소개해주세요.")
        team_section = "\n".join(team_lines)

        return f"{identity_section}\n\n{core_instruction}\n{tool_usage_section}\n\n{team_section}"
