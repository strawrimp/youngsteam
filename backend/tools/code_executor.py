"""Safe Python code execution tool with timeout and output capture."""

import asyncio
import io
import logging
import sys
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Any, Dict

from tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Forbidden modules and keywords for basic safety
FORBIDDEN_MODULES = {
    "os",
    "subprocess",
    "sys",
    "shutil",
    "pathlib",
    "socket",
    "urllib",
    "requests",
    "httpx",
    "aiohttp",
    "__import__",
    "importlib",
    "ctypes",
    "multiprocessing",
}

FORBIDDEN_KEYWORDS = {
    "__import__",
    "exec(",
    "eval(",
    "compile(",
    "open(",
    "file(",
    "input(",
    "raw_input(",
    "globals()",
    "locals()",
    "vars(",
}


def _is_safe_code(code: str) -> tuple[bool, str]:
    """Basic safety check for code."""
    code_lower = code.lower()

    for keyword in FORBIDDEN_KEYWORDS:
        if keyword in code_lower:
            return False, f"금지된 함수 사용: {keyword}"

    # Check for dangerous imports
    import re

    imports = re.findall(r"import\s+(\w+)", code)
    for mod in imports:
        if mod in FORBIDDEN_MODULES:
            return False, f"금지된 모듈: {mod}"

    return True, ""


async def _run_code_with_timeout(code: str, timeout: float = 10.0) -> tuple[str, str]:
    """Run code in executor with timeout."""
    loop = asyncio.get_event_loop()

    def _execute():
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        local_vars = {}

        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(
                    code,
                    {
                        # Allow safe built-ins only
                        "__builtins__": {
                            "print": print,
                            "len": len,
                            "range": range,
                            "enumerate": enumerate,
                            "zip": zip,
                            "map": map,
                            "filter": filter,
                            "sorted": sorted,
                            "reversed": reversed,
                            "sum": sum,
                            "min": min,
                            "max": max,
                            "abs": abs,
                            "round": round,
                            "int": int,
                            "float": float,
                            "str": str,
                            "bool": bool,
                            "list": list,
                            "dict": dict,
                            "set": set,
                            "tuple": tuple,
                            "type": type,
                            "isinstance": isinstance,
                            "repr": repr,
                            "format": format,
                            # Exception types for try/except
                            "Exception": Exception,
                            "ValueError": ValueError,
                            "TypeError": TypeError,
                            "KeyError": KeyError,
                            "IndexError": IndexError,
                            "AttributeError": AttributeError,
                            "RuntimeError": RuntimeError,
                            "NotImplementedError": NotImplementedError,
                            "ZeroDivisionError": ZeroDivisionError,
                            "StopIteration": StopIteration,
                            "__name__": "__main__",
                        },
                        # Allow math and json
                        "math": __import__("math"),
                        "json": __import__("json"),
                        "re": __import__("re"),
                        "datetime": __import__("datetime"),
                        "random": __import__("random"),
                        "collections": __import__("collections"),
                        "itertools": __import__("itertools"),
                    },
                    local_vars,
                )
        except Exception as e:
            return (
                stdout_capture.getvalue(),
                f"실행 오류: {type(e).__name__}: {e}\n{traceback.format_exc()}",
            )

        return stdout_capture.getvalue(), stderr_capture.getvalue()

    try:
        stdout, stderr = await asyncio.wait_for(
            loop.run_in_executor(None, _execute),
            timeout=timeout,
        )
        return stdout, stderr
    except asyncio.TimeoutError:
        return "", f"타임아웃: 코드 실행이 {timeout}초를 초과했습니다."


class CodeExecutorTool(BaseTool):
    """Execute Python code safely in a sandboxed environment."""

    @property
    def name(self) -> str:
        return "execute_python"

    @property
    def description(self) -> str:
        return (
            "Execute Python code to perform calculations, data analysis, algorithm design, "
            "string manipulation, and problem solving. "
            "Available: math, json, re, datetime, random, collections, itertools. "
            "No file I/O, network, or system access. Max execution: 10 seconds."
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string",
                    "description": "Python code to execute. Use print() to show output.",
                },
                "description": {
                    "type": "string",
                    "description": "Brief description of what this code does",
                },
            },
            "required": ["code"],
        }

    async def execute(self, code: str, description: str = "") -> ToolResult:
        """Execute Python code safely."""
        # Safety check
        is_safe, reason = _is_safe_code(code)
        if not is_safe:
            return ToolResult(
                success=False,
                output="",
                error=f"보안 위반: {reason}",
            )

        logger.info(f"Executing code: {description or code[:50]!r}")

        stdout, stderr = await _run_code_with_timeout(code, timeout=10.0)

        if stderr and "실행 오류" in stderr:
            return ToolResult(
                success=False,
                output=stdout,
                error=stderr,
            )

        output = ""
        if description:
            output += f"**{description}**\n\n"
        output += f"```python\n{code}\n```\n\n"
        if stdout:
            output += f"**실행 결과:**\n```\n{stdout}\n```"
        else:
            output += "*(출력 없음)*"

        if stderr:
            output += f"\n\n**경고:**\n```\n{stderr}\n```"

        return ToolResult(
            success=True,
            output=output,
            metadata={"stdout": stdout, "stderr": stderr},
        )
