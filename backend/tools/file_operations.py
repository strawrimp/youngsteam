"""File operations tool for agent file system access.

Provides safe, read-write access to the project directory.
Primary use: developer agent (Arthur) writing and modifying code.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from tools.base_tool import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Project root — only files under this directory are accessible
PROJECT_ROOT = Path("/Volumes/Dock/2604/my-ai-company").resolve()

# Sensitive paths — never allow access
SENSITIVE_PATTERNS = [
    re.compile(r"\.env", re.IGNORECASE),
    re.compile(r"\.git[/\\]", re.IGNORECASE),
    re.compile(r"\.key$", re.IGNORECASE),
    re.compile(r"\.pem$", re.IGNORECASE),
    re.compile(r"credentials", re.IGNORECASE),
    re.compile(r"secret", re.IGNORECASE),
    re.compile(r"__pycache__", re.IGNORECASE),
    re.compile(r"node_modules", re.IGNORECASE),
    re.compile(r"\.venv", re.IGNORECASE),
    re.compile(r"venv[/\\]", re.IGNORECASE),
]

MAX_READ_LINES = 500
MAX_WRITE_SIZE = 100_000  # 100KB
MAX_SEARCH_RESULTS = 30


def _validate_path(path_str: str) -> tuple[bool, str, Optional[Path]]:
    """Validate and resolve a path. Returns (ok, error_msg, resolved_path)."""
    try:
        target = (PROJECT_ROOT / path_str).resolve()
    except (ValueError, OSError) as e:
        return False, f"잘못된 경로: {e}", None

    # Must be under project root
    try:
        target.relative_to(PROJECT_ROOT)
    except ValueError:
        return False, f"프로젝트 디렉토리 외부 접근 불가: {path_str}", None

    # Check sensitive patterns
    relative = str(target.relative_to(PROJECT_ROOT))
    for pattern in SENSITIVE_PATTERNS:
        if pattern.search(relative):
            return False, f"보안: 민감한 경로 접근 불가: {relative}", None

    return True, "", target


class FileOperationsTool(BaseTool):
    """Read, write, list, and search project files."""

    @property
    def name(self) -> str:
        return "file_operations"

    @property
    def description(self) -> str:
        return (
            "프로젝트 파일 시스템에 접근합니다. "
            "코드 작성, 파일 수정, 프로젝트 구조 파악에 사용하세요. "
            "Operations: "
            "'list' — 디렉토리 내용 보기, "
            "'read' — 파일 내용 읽기, "
            "'write' — 파일 생성/수정, "
            "'search' — 파일 내용에서 패턴 검색"
        )

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["list", "read", "write", "search"],
                    "description": "수행할 작업: list, read, write, search",
                },
                "path": {
                    "type": "string",
                    "description": "파일 또는 디렉토리 경로 (프로젝트 루트 기준 상대경로). 예: 'frontend/src/App.tsx'",
                },
                "content": {
                    "type": "string",
                    "description": "write 작업 시 파일에 쓸 내용",
                },
                "pattern": {
                    "type": "string",
                    "description": "search 작업 시 검색할 정규식 패턴",
                },
                "offset": {
                    "type": "integer",
                    "description": "read 작업 시 시작 줄 번호 (1-based, 기본값: 1)",
                    "default": 1,
                },
                "limit": {
                    "type": "integer",
                    "description": "read 작업 시 읽을 최대 줄 수 (기본값: 200)",
                    "default": 200,
                },
            },
            "required": ["operation", "path"],
        }

    async def execute(
        self,
        operation: str,
        path: str,
        content: str = "",
        pattern: str = "",
        offset: int = 1,
        limit: int = 200,
    ) -> ToolResult:
        """Execute a file operation."""
        try:
            if operation == "list":
                return await self._list(path)
            elif operation == "read":
                return await self._read(path, offset, limit)
            elif operation == "write":
                return await self._write(path, content)
            elif operation == "search":
                return await self._search(path, pattern)
            else:
                return ToolResult(
                    success=False, output="", error=f"알 수 없는 작업: {operation}"
                )
        except Exception as e:
            logger.error(f"File operation error ({operation}): {e}")
            return ToolResult(success=False, output="", error=str(e))

    async def _list(self, path: str) -> ToolResult:
        """List directory contents."""
        ok, err, target = _validate_path(path)
        if not ok:
            return ToolResult(success=False, output="", error=err)

        if not target.exists():
            return ToolResult(
                success=False, output="", error=f"경로가 존재하지 않음: {path}"
            )

        if target.is_file():
            # Show file info
            size = target.stat().st_size
            return ToolResult(
                success=True,
                output=f"📄 **{path}** ({size:,} bytes)",
            )

        # List directory
        entries: List[str] = []
        try:
            items = sorted(
                target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())
            )
        except PermissionError:
            return ToolResult(success=False, output="", error=f"접근 권한 없음: {path}")

        for item in items:
            # Skip sensitive dirs
            rel = str(item.relative_to(PROJECT_ROOT))
            if any(p.search(rel) for p in SENSITIVE_PATTERNS):
                continue

            name = item.name
            if item.is_dir():
                entries.append(f"📁 {name}/")
            else:
                size = item.stat().st_size
                entries.append(f"📄 {name} ({size:,} bytes)")

        if not entries:
            return ToolResult(success=True, output=f"빈 디렉토리: {path}")

        output = f"## 📂 {path}\n\n"
        output += "\n".join(entries)
        output += f"\n\n총 {len(entries)}개 항목"

        return ToolResult(success=True, output=output)

    async def _read(self, path: str, offset: int = 1, limit: int = 200) -> ToolResult:
        """Read file content."""
        ok, err, target = _validate_path(path)
        if not ok:
            return ToolResult(success=False, output="", error=err)

        if not target.exists():
            return ToolResult(
                success=False, output="", error=f"파일이 존재하지 않음: {path}"
            )

        if target.is_dir():
            return ToolResult(
                success=False, output="", error=f"디렉토리는 읽을 수 없음: {path}"
            )

        try:
            with open(target, "r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
        except PermissionError:
            return ToolResult(
                success=False, output="", error=f"파일 읽기 권한 없음: {path}"
            )

        total_lines = len(lines)
        # Clamp offset and limit
        start = max(1, offset) - 1  # 0-based
        end = min(start + min(limit, MAX_READ_LINES), total_lines)
        selected = lines[start:end]

        if not selected:
            return ToolResult(
                success=True,
                output=f"📄 **{path}** ({total_lines} 줄)\n지정된 범위에 내용이 없습니다.",
            )

        # Format with line numbers
        numbered = []
        for i, line in enumerate(selected, start=start + 1):
            numbered.append(f"{i:>4}: {line.rstrip()}")

        ext = target.suffix.lstrip(".")
        output = f"📄 **{path}** ({total_lines} 줄, {offset}-{end}줄 표시)\n\n"
        output += f"```{ext}\n" + "\n".join(numbered) + "\n```"

        return ToolResult(success=True, output=output)

    async def _write(self, path: str, content: str) -> ToolResult:
        """Write content to a file (create or overwrite)."""
        ok, err, target = _validate_path(path)
        if not ok:
            return ToolResult(success=False, output="", error=err)

        if not content:
            return ToolResult(success=False, output="", error="내용이 비어있음")

        if len(content) > MAX_WRITE_SIZE:
            return ToolResult(
                success=False,
                output="",
                error=f"파일 크기 초과: {len(content):,} > {MAX_WRITE_SIZE:,} bytes",
            )

        # Create parent directories if needed
        target.parent.mkdir(parents=True, exist_ok=True)

        is_new = not target.exists()
        try:
            with open(target, "w", encoding="utf-8") as f:
                f.write(content)
        except PermissionError:
            return ToolResult(
                success=False, output="", error=f"파일 쓰기 권한 없음: {path}"
            )

        action = "생성" if is_new else "수정"
        line_count = content.count("\n") + 1
        output = f"✅ 파일 {action} 완료: **{path}**\n"
        output += f"- 크기: {len(content):,} bytes\n"
        output += f"- 줄 수: {line_count}"

        logger.info(f"File {action}: {path} ({len(content)} bytes, {line_count} lines)")

        return ToolResult(success=True, output=output)

    async def _search(self, path: str, pattern: str) -> ToolResult:
        """Search for a regex pattern in files under a directory."""
        if not pattern:
            return ToolResult(success=False, output="", error="검색 패턴이 없음")

        ok, err, target = _validate_path(path)
        if not ok:
            return ToolResult(success=False, output="", error=err)

        if not target.exists():
            return ToolResult(
                success=False, output="", error=f"경로가 존재하지 않음: {path}"
            )

        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error as e:
            return ToolResult(success=False, output="", error=f"잘못된 정규식: {e}")

        results: List[str] = []
        search_root = target if target.is_dir() else target.parent

        for root, dirs, files in os.walk(search_root):
            # Skip sensitive dirs
            rel_root = str(Path(root).relative_to(PROJECT_ROOT))
            if any(p.search(rel_root) for p in SENSITIVE_PATTERNS):
                dirs.clear()
                continue

            # Prune sensitive subdirs
            dirs[:] = [
                d for d in dirs if not any(p.search(d) for p in SENSITIVE_PATTERNS)
            ]

            for fname in files:
                fpath = Path(root) / fname
                try:
                    with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                        for line_num, line in enumerate(f, 1):
                            if regex.search(line):
                                rel = str(fpath.relative_to(PROJECT_ROOT))
                                results.append(
                                    f"  {rel}:{line_num}: {line.strip()[:120]}"
                                )
                                if len(results) >= MAX_SEARCH_RESULTS:
                                    break
                except (PermissionError, OSError):
                    continue

                if len(results) >= MAX_SEARCH_RESULTS:
                    break

        if not results:
            return ToolResult(
                success=True,
                output=f"'{pattern}' 패턴 검색 결과 없음 (경로: {path})",
            )

        output = f"## 🔍 검색 결과: '{pattern}'\n\n"
        output += "\n".join(results)
        if len(results) >= MAX_SEARCH_RESULTS:
            output += f"\n\n... (최대 {MAX_SEARCH_RESULTS}개 결과까지만 표시)"

        return ToolResult(success=True, output=output)
