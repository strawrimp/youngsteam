"""MemoryService: Shared memory management for all agents."""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class MemoryService:
    """Manages shared memory accessible to all agents."""

    def __init__(self, db_session=None):
        """Initialize memory service.

        Args:
            db_session: SQLAlchemy database session
        """
        self.db = db_session
        self.in_memory_cache: Dict[str, List[Dict]] = {}

    async def save_memory(
        self,
        category: str,
        content: str,
        created_by: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """Save a memory entry.

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

        # In-memory storage for Phase 2
        if category not in self.in_memory_cache:
            self.in_memory_cache[category] = []

        self.in_memory_cache[category].append(memory_entry)
        logger.info(f"Saved memory: {category} (by {created_by})")

        return memory_entry

    async def get_memory(
        self,
        category: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """Retrieve memory entries.

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
        """Search memory entries by content.

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

        logger.info(f"Memory search found {len(results)} results for: {query}")
        return results

    async def update_memory(
        self,
        category: str,
        content: str,
        created_by: Optional[str] = None,
    ) -> Dict:
        """Update memory (in Phase 2, adds new entry; in Phase 3+, uses versioning).

        Args:
            category: Memory category
            content: Updated content
            created_by: Agent ID updating

        Returns:
            Updated memory entry
        """
        return await self.save_memory(category, content, created_by)

    async def clear_memory(self, category: Optional[str] = None):
        """Clear memory entries.

        Args:
            category: Category to clear (None = all)
        """
        if category:
            self.in_memory_cache[category] = []
            logger.info(f"Cleared memory: {category}")
        else:
            self.in_memory_cache.clear()
            logger.info("Cleared all memory")

    def get_context_for_agent(self) -> str:
        """Get formatted context string for agents.

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

        return context if context != "## 공유 메모리 (Shared Memory)\n\n" else "No shared memory yet."
