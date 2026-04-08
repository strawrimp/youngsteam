"""MemoryService: Individual and shared memory management for agents."""

import logging
import json
import asyncio
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)


class MemoryService:
    """Manages both individual agent memory and shared project memory."""

    def __init__(self, db_session=None, workspace_base: str = None):
        """Initialize memory service.

        Args:
            db_session: SQLAlchemy database session
            workspace_base: Base path for agent workspaces (default: backend/agents/workspaces)
        """
        self.db = db_session
        self.in_memory_cache: Dict[str, List[Dict]] = {}
        self._file_locks: Dict[str, asyncio.Lock] = {}

        # Set workspace base path
        if workspace_base:
            self.workspace_base = Path(workspace_base)
        else:
            # Default: backend/agents/workspaces
            current_dir = Path(__file__).parent.parent  # backend/
            self.workspace_base = current_dir / "agents" / "workspaces"

    # ==================== 기존 공유 메모리 메서드 ====================

    async def save_memory(
        self,
        category: str,
        content: str,
        created_by: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Save a shared memory entry.

        Args:
            category: Memory category (strategy, goal, project, decision)
            content: Memory content
            created_by: Agent ID of creator
            metadata: Additional metadata (JSON-serializable dict)

        Returns:
            Saved memory entry
        """
        memory_entry = {
            "category": category,
            "content": content,
            "created_by": created_by,
            "metadata": metadata or {},
            "created_at": datetime.now().isoformat(),
        }

        # In-memory storage
        if category not in self.in_memory_cache:
            self.in_memory_cache[category] = []

        self.in_memory_cache[category].append(memory_entry)
        logger.info(f"Saved shared memory: {category} (by {created_by})")

        return memory_entry

    async def get_memory(
        self,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Retrieve shared memory entries.

        Args:
            category: Filter by category (None = all)
            limit: Max entries to retrieve

        Returns:
            List of memory entries
        """
        if category:
            entries = self.in_memory_cache.get(category, [])
        else:
            # Get from all categories
            entries = []
            for cat_entries in self.in_memory_cache.values():
                entries.extend(cat_entries)

        # Return most recent entries (sorted by created_at)
        entries.sort(key=lambda x: x["created_at"], reverse=True)
        return entries[:limit]

    async def search_memory(self, query: str) -> List[Dict]:
        """Search shared memory entries by content.

        Args:
            query: Search query

        Returns:
            List of matching entries
        """
        results = []
        for entries in self.in_memory_cache.values():
            for entry in entries:
                if query.lower() in entry["content"].lower():
                    results.append(entry)

        logger.info(f"Shared memory search found {len(results)} results for: {query}")
        return results

    async def update_memory(
        self,
        category: str,
        content: str,
        created_by: Optional[str] = None,
    ) -> Dict:
        """Update shared memory (adds new entry).

        Args:
            category: Memory category
            content: Updated content
            created_by: Agent ID updating

        Returns:
            Updated memory entry
        """
        return await self.save_memory(category, content, created_by)

    async def clear_memory(self, category: Optional[str] = None):
        """Clear shared memory entries.

        Args:
            category: Category to clear (None = all)
        """
        if category:
            self.in_memory_cache[category] = []
            logger.info(f"Cleared shared memory: {category}")
        else:
            self.in_memory_cache.clear()
            logger.info("Cleared all shared memory")

    def get_context_for_agent(self) -> str:
        """Get formatted shared memory context string for agents.

        Returns:
            Formatted memory context
        """
        context = "## 공유 메모리 (Shared Memory)\n\n"

        for category, entries in self.in_memory_cache.items():
            if entries:
                context += f"### {category.upper()}\n"
                for entry in entries[-3:]:  # Last 3 entries per category
                    context += f"- {entry['content']}\n"
                context += "\n"

        return (
            context
            if context != "## 공유 메모리 (Shared Memory)\n\n"
            else "No shared memory yet."
        )

    # ==================== 개별 에이전트 메모리 메서드 (NEW) ====================

    async def _get_file_lock(self, agent_name: str) -> asyncio.Lock:
        """Get or create file lock for agent.

        Args:
            agent_name: Agent name

        Returns:
            asyncio.Lock instance
        """
        if agent_name not in self._file_locks:
            self._file_locks[agent_name] = asyncio.Lock()
        return self._file_locks[agent_name]

    def _get_memory_path(self, agent_name: str) -> Path:
        """Get memory file path for agent.

        Args:
            agent_name: Agent name

        Returns:
            Path to memory.json
        """
        return self.workspace_base / agent_name / "memory.json"

    def _ensure_workspace_exists(self, agent_name: str):
        """Ensure workspace directory exists for agent.

        Args:
            agent_name: Agent name
        """
        workspace_path = self.workspace_base / agent_name
        workspace_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Ensured workspace exists: {workspace_path}")

    def _create_default_memory(self, agent_name: str, project_id: int = None) -> Dict:
        """Create default memory template.

        Args:
            agent_name: Agent name
            project_id: Project ID (optional)

        Returns:
            Default memory dict
        """
        return {
            "agent_name": agent_name,
            "project_id": project_id,
            "conversations": [],
            "context": {
                "current_task": None,
                "last_updated": datetime.now().isoformat(),
                "project_context": None,
            },
            "settings": {"max_conversations": 100, "retention_days": 30},
        }

    async def load_agent_memory(self, agent_name: str, project_id: int = None) -> Dict:
        """Load individual agent memory from file.

        Args:
            agent_name: Agent name
            project_id: Project ID (optional, for filtering)

        Returns:
            Memory dict
        """
        lock = await self._get_file_lock(agent_name)

        async with lock:
            memory_path = self._get_memory_path(agent_name)

            if not memory_path.exists():
                # Create default memory
                self._ensure_workspace_exists(agent_name)
                default_memory = self._create_default_memory(agent_name, project_id)

                # Save default memory
                with open(memory_path, "w", encoding="utf-8") as f:
                    json.dump(default_memory, f, ensure_ascii=False, indent=2)

                logger.info(f"Created default memory for {agent_name}")
                return default_memory

            try:
                with open(memory_path, "r", encoding="utf-8") as f:
                    memory = json.load(f)

                logger.debug(
                    f"Loaded memory for {agent_name}: {len(memory.get('conversations', []))} conversations"
                )
                return memory

            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse memory file for {agent_name}: {e}")
                # Return default memory on parse error
                return self._create_default_memory(agent_name, project_id)

    async def save_agent_memory(self, agent_name: str, memory: Dict):
        """Save individual agent memory to file.

        Args:
            agent_name: Agent name
            memory: Memory dict to save
        """
        lock = await self._get_file_lock(agent_name)

        async with lock:
            self._ensure_workspace_exists(agent_name)
            memory_path = self._get_memory_path(agent_name)

            # Update last_updated timestamp
            if "context" in memory:
                memory["context"]["last_updated"] = datetime.now().isoformat()

            try:
                with open(memory_path, "w", encoding="utf-8") as f:
                    json.dump(memory, f, ensure_ascii=False, indent=2)

                logger.debug(f"Saved memory for {agent_name}")

            except Exception as e:
                logger.error(f"Failed to save memory for {agent_name}: {e}")
                raise

    async def add_conversation(
        self,
        agent_name: str,
        role: str,
        content: str,
        project_id: int = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Add a conversation entry to agent memory.

        Args:
            agent_name: Agent name
            role: 'user' or 'agent'
            content: Message content
            project_id: Project ID (optional)
            metadata: Additional metadata (model, tokens, etc.)

        Returns:
            Created conversation entry
        """
        # Load current memory
        memory = await self.load_agent_memory(agent_name, project_id)

        # Create conversation entry
        conversation_entry = {
            "id": f"conv_{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "metadata": metadata or {},
        }

        # Add to conversations
        if "conversations" not in memory:
            memory["conversations"] = []

        memory["conversations"].append(conversation_entry)

        # Check max conversations limit
        max_convs = memory.get("settings", {}).get("max_conversations", 100)
        if len(memory["conversations"]) > max_convs:
            # Remove oldest conversations
            memory["conversations"] = memory["conversations"][-max_convs:]
            logger.info(f"Trimmed conversations for {agent_name} to {max_convs}")

        # Save memory
        await self.save_agent_memory(agent_name, memory)

        logger.info(f"Added conversation for {agent_name}: {role}")
        return conversation_entry

    async def get_merged_context(
        self,
        agent_name: str,
        project_id: int = None,
        include_shared: bool = True,
        max_conversations: int = 10,
    ) -> str:
        """Get merged context (individual + shared memory) for LLM prompt.

        Args:
            agent_name: Agent name
            project_id: Project ID (optional)
            include_shared: Whether to include shared memory
            max_conversations: Max recent conversations to include

        Returns:
            Formatted context string
        """
        context_parts = []

        # 1. Individual agent memory
        memory = await self.load_agent_memory(agent_name, project_id)

        # Agent context
        agent_context = memory.get("context", {})
        if agent_context.get("current_task") or agent_context.get("project_context"):
            context_parts.append("## 현재 컨텍스트\n")
            if agent_context.get("project_context"):
                context_parts.append(f"프로젝트: {agent_context['project_context']}\n")
            if agent_context.get("current_task"):
                context_parts.append(f"현재 작업: {agent_context['current_task']}\n")
            context_parts.append("\n")

        # Recent conversations
        conversations = memory.get("conversations", [])
        if conversations:
            context_parts.append("## 최근 대화 기록\n\n")
            recent_convs = conversations[-max_conversations:]
            for conv in recent_convs:
                role_label = "사용자" if conv["role"] == "user" else agent_name
                context_parts.append(f"{role_label}: {conv['content']}\n")
            context_parts.append("\n")

        # 2. Shared memory (optional)
        if include_shared:
            shared_context = self.get_context_for_agent()
            if shared_context != "No shared memory yet.":
                context_parts.append(shared_context)

        return "".join(context_parts) if context_parts else "No context available."

    async def update_agent_context(
        self,
        agent_name: str,
        current_task: Optional[str] = None,
        project_context: Optional[str] = None,
        project_id: int = None,
    ):
        """Update agent context fields.

        Args:
            agent_name: Agent name
            current_task: Current task description
            project_context: Project context description
            project_id: Project ID (optional)
        """
        memory = await self.load_agent_memory(agent_name, project_id)

        if "context" not in memory:
            memory["context"] = {}

        if current_task is not None:
            memory["context"]["current_task"] = current_task

        if project_context is not None:
            memory["context"]["project_context"] = project_context

        if project_id is not None:
            memory["project_id"] = project_id

        await self.save_agent_memory(agent_name, memory)
        logger.info(f"Updated context for {agent_name}")

    async def cleanup_old_conversations(
        self, agent_name: str, project_id: int = None, days: int = None
    ) -> int:
        """Remove conversations older than retention period.

        Args:
            agent_name: Agent name
            project_id: Project ID (optional)
            days: Retention days (default: use settings or 30)

        Returns:
            Number of conversations removed
        """
        memory = await self.load_agent_memory(agent_name, project_id)

        # Get retention days from settings or use default
        if days is None:
            days = memory.get("settings", {}).get("retention_days", 30)

        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_str = cutoff_date.isoformat()

        # Filter conversations
        original_count = len(memory.get("conversations", []))
        memory["conversations"] = [
            conv
            for conv in memory.get("conversations", [])
            if conv.get("timestamp", "") >= cutoff_str
        ]
        new_count = len(memory["conversations"])

        removed_count = original_count - new_count

        if removed_count > 0:
            await self.save_agent_memory(agent_name, memory)
            logger.info(
                f"Cleaned up {removed_count} old conversations for {agent_name}"
            )

        return removed_count

    async def clear_agent_memory(self, agent_name: str, project_id: int = None):
        """Clear all conversations for agent (reset memory).

        Args:
            agent_name: Agent name
            project_id: Project ID (optional)
        """
        default_memory = self._create_default_memory(agent_name, project_id)
        await self.save_agent_memory(agent_name, default_memory)
        logger.info(f"Cleared memory for {agent_name}")

    async def get_conversation_count(
        self, agent_name: str, project_id: int = None
    ) -> int:
        """Get total conversation count for agent.

        Args:
            agent_name: Agent name
            project_id: Project ID (optional)

        Returns:
            Number of conversations
        """
        memory = await self.load_agent_memory(agent_name, project_id)
        return len(memory.get("conversations", []))
