"""Agent task executor - runs agents with tools using DeepSeek function calling."""

import asyncio
import json
import logging
from dataclasses import dataclass, field
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
    ) -> TaskExecutionResult:
        """Execute a task for an agent with tool use.

        Args:
            task: The task description/instruction
            agent_name: Agent's name (for display)
            agent_role: Agent's role (manager, developer, designer, researcher)
            soul_prompt: Agent's SOUL system prompt
            conversation_history: Previous conversation context

        Returns:
            TaskExecutionResult with all steps and final response
        """
        steps: List[TaskStep] = []
        messages: List[Dict] = list(conversation_history or [])

        # Build system prompt combining SOUL + tool instructions
        system_prompt = self._build_system_prompt(soul_prompt, agent_role)

        # Initial task message
        task_message = f"""다음 업무를 수행해주세요:

{task}

필요하다면 도구(웹 검색, 코드 실행)를 사용하세요. 업무를 완료한 후 결과를 명확하게 정리해 보고해주세요."""

        logger.info(f"[{agent_name}] Starting task: {task[:80]!r}")

        # Tool calling loop
        for round_num in range(MAX_TOOL_ROUNDS):
            # Call DeepSeek with tools
            result = await self.deepseek.call_model_with_tools(
                system_prompt=system_prompt,
                user_message=task_message if round_num == 0 else "",
                tools=self.tool_schemas,
                conversation_history=messages if round_num == 0 else None,
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

            # Continue loop - the next call will process tool results
            # Use empty task_message since we're continuing conversation
            task_message = ""

            # Re-call with updated messages (tool results)
            continue_result = await self.deepseek.call_model_with_tools(
                system_prompt=system_prompt,
                user_message="",
                tools=self.tool_schemas,
                conversation_history=messages,
                task_type="default",
            )

            content = continue_result.get("content", "")
            next_tool_calls = continue_result.get("tool_calls", [])

            if content:
                step = TaskStep(
                    type="thinking" if next_tool_calls else "response",
                    content=content,
                )
                steps.append(step)
                if self.on_step:
                    self.on_step(step)

            messages.append(
                {
                    "role": "assistant",
                    "content": content or "",
                }
            )

            if not next_tool_calls:
                logger.info(f"[{agent_name}] Task complete with tools")
                return TaskExecutionResult(
                    success=True,
                    final_response=content,
                    steps=steps,
                    agent_name=agent_name,
                    agent_role=agent_role,
                    task=task,
                )

            # Update tool_calls for next iteration
            result["tool_calls"] = next_tool_calls
            result["content"] = content

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

    def _build_system_prompt(self, soul_prompt: str, role: str) -> str:
        """Build system prompt combining SOUL + role context + tool instructions."""
        role_context = {
            "manager": "당신은 팀의 관리자(CEO)입니다. 전략적 판단과 팀 조율이 전문입니다.",
            "developer": "당신은 시니어 개발자입니다. 코딩, 아키텍처 설계, 기술 문제 해결이 전문입니다.",
            "designer": "당신은 UI/UX 디자이너입니다. 사용자 경험과 시각적 디자인이 전문입니다.",
            "researcher": "당신은 리서처입니다. 시장 조사, 데이터 분석, 정보 수집이 전문입니다.",
        }.get(role, "당신은 AI 에이전트입니다.")

        base = soul_prompt if soul_prompt else role_context

        tool_instructions = """

## 도구 사용 가이드
다음 도구들을 활용하여 업무를 수행하세요:
- **web_search**: 최신 정보, 뉴스, 사실 확인이 필요할 때 사용
- **execute_python**: 계산, 데이터 분석, 알고리즘 구현이 필요할 때 사용
- **youtube_transcript**: YouTube 영상의 자막을 추출하고 분석해야 할 때 사용. YouTube URL이 포함된 요청이나 영상 내용 분석 요청 시 활용하세요.

업무 완료 후 결과를 명확하고 구조적으로 정리하여 보고하세요.
한국어로 응답하세요."""

        return base + tool_instructions
