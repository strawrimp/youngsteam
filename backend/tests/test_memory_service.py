"""Tests for MemoryService."""

import pytest
import asyncio
import json
from pathlib import Path
from datetime import datetime, timedelta

from services.memory_service import MemoryService


class TestMemoryService:
    """Test suite for MemoryService."""

    @pytest.fixture
    def memory_service(self, tmp_path):
        """Create MemoryService with temporary workspace."""
        workspace_base = tmp_path / "workspaces"
        workspace_base.mkdir(parents=True, exist_ok=True)
        return MemoryService(db_session=None, workspace_base=str(workspace_base))

    # ==================== Shared Memory Tests ====================

    @pytest.mark.asyncio
    async def test_save_shared_memory(self, memory_service):
        """Test saving shared memory."""
        entry = await memory_service.save_memory(
            category="strategy",
            content="Use microservices architecture",
            created_by="manager",
        )

        assert entry["category"] == "strategy"
        assert entry["content"] == "Use microservices architecture"
        assert entry["created_by"] == "manager"
        assert "created_at" in entry

    @pytest.mark.asyncio
    async def test_get_shared_memory(self, memory_service):
        """Test retrieving shared memory."""
        # Save multiple entries
        await memory_service.save_memory("strategy", "Strategy 1", "manager")
        await memory_service.save_memory("strategy", "Strategy 2", "developer")
        await memory_service.save_memory("goal", "Goal 1", "manager")

        # Get all strategy entries
        entries = await memory_service.get_memory(category="strategy")
        assert len(entries) == 2

        # Get all entries
        all_entries = await memory_service.get_memory()
        assert len(all_entries) == 3

    @pytest.mark.asyncio
    async def test_search_shared_memory(self, memory_service):
        """Test searching shared memory."""
        await memory_service.save_memory(
            "strategy", "Use React for frontend", "developer"
        )
        await memory_service.save_memory("goal", "Build REST API", "developer")

        results = await memory_service.search_memory("React")
        assert len(results) == 1
        assert "React" in results[0]["content"]

        results = await memory_service.search_memory("API")
        assert len(results) == 1

    # ==================== Individual Agent Memory Tests ====================

    @pytest.mark.asyncio
    async def test_load_agent_memory_creates_default(self, memory_service):
        """Test loading non-existent agent memory creates default."""
        memory = await memory_service.load_agent_memory("developer", project_id=1)

        assert memory["agent_name"] == "developer"
        assert memory["project_id"] == 1
        assert memory["conversations"] == []
        assert "context" in memory
        assert "settings" in memory
        assert memory["settings"]["max_conversations"] == 100
        assert memory["settings"]["retention_days"] == 30

    @pytest.mark.asyncio
    async def test_save_and_load_agent_memory(self, memory_service):
        """Test saving and loading agent memory."""
        # Load default memory
        memory = await memory_service.load_agent_memory("manager", project_id=1)

        # Modify and save
        memory["context"]["current_task"] = "Design API"
        await memory_service.save_agent_memory("manager", memory)

        # Load again
        loaded_memory = await memory_service.load_agent_memory("manager")

        assert loaded_memory["context"]["current_task"] == "Design API"
        assert "last_updated" in loaded_memory["context"]

    @pytest.mark.asyncio
    async def test_add_conversation(self, memory_service):
        """Test adding conversation to agent memory."""
        # Add user message
        conv1 = await memory_service.add_conversation(
            agent_name="developer",
            role="user",
            content="API 설계 부탁드립니다",
            project_id=1,
            metadata={"source": "chat"},
        )

        assert conv1["role"] == "user"
        assert conv1["content"] == "API 설계 부탁드립니다"
        assert "timestamp" in conv1

        # Add agent response
        conv2 = await memory_service.add_conversation(
            agent_name="developer",
            role="agent",
            content="네, REST API로 설계하겠습니다",
            project_id=1,
            metadata={"model": "deepseek-chat", "tokens": 150},
        )

        assert conv2["role"] == "agent"
        assert conv2["metadata"]["model"] == "deepseek-chat"

        # Verify conversations saved
        memory = await memory_service.load_agent_memory("developer")
        assert len(memory["conversations"]) == 2

    @pytest.mark.asyncio
    async def test_get_merged_context(self, memory_service):
        """Test getting merged context."""
        # Add individual agent memory
        await memory_service.add_conversation(
            agent_name="designer",
            role="user",
            content="UI 디자인 부탁드려요",
            project_id=1,
        )

        # Add shared memory
        await memory_service.save_memory("strategy", "Use minimal design", "manager")

        # Get merged context (without shared memory)
        context = await memory_service.get_merged_context(
            "designer", project_id=1, include_shared=False
        )
        assert "UI 디자인 부탁드려요" in context

        # Get merged context (with shared memory)
        context_with_shared = await memory_service.get_merged_context(
            "designer", project_id=1, include_shared=True
        )
        assert "UI 디자인 부탁드려요" in context_with_shared
        assert "Use minimal design" in context_with_shared

    @pytest.mark.asyncio
    async def test_update_agent_context(self, memory_service):
        """Test updating agent context."""
        await memory_service.update_agent_context(
            agent_name="researcher",
            current_task="Market research for AI tools",
            project_context="AI startup project",
            project_id=1,
        )

        memory = await memory_service.load_agent_memory("researcher")

        assert memory["context"]["current_task"] == "Market research for AI tools"
        assert memory["context"]["project_context"] == "AI startup project"
        assert memory["project_id"] == 1

    @pytest.mark.asyncio
    async def test_cleanup_old_conversations(self, memory_service):
        """Test cleaning up old conversations."""
        # Add conversations
        await memory_service.add_conversation(
            "manager", "user", "Message 1", project_id=1
        )
        await memory_service.add_conversation(
            "manager", "agent", "Response 1", project_id=1
        )

        # Manually add old conversation
        memory = await memory_service.load_agent_memory("manager")
        old_date = (datetime.now() - timedelta(days=60)).isoformat()
        memory["conversations"].insert(
            0,
            {
                "id": "old_conv",
                "timestamp": old_date,
                "role": "user",
                "content": "Old message",
                "metadata": {},
            },
        )
        await memory_service.save_agent_memory("manager", memory)

        # Cleanup (30 days retention)
        removed = await memory_service.cleanup_old_conversations("manager", days=30)

        assert removed == 1

        # Verify old conversation removed
        memory = await memory_service.load_agent_memory("manager")
        assert len(memory["conversations"]) == 2
        assert all(c["content"] != "Old message" for c in memory["conversations"])

    @pytest.mark.asyncio
    async def test_clear_agent_memory(self, memory_service):
        """Test clearing agent memory."""
        # Add conversations
        await memory_service.add_conversation(
            "developer", "user", "Message 1", project_id=1
        )
        await memory_service.add_conversation(
            "developer", "agent", "Response 1", project_id=1
        )

        # Verify conversations exist
        memory = await memory_service.load_agent_memory("developer")
        assert len(memory["conversations"]) == 2

        # Clear memory
        await memory_service.clear_agent_memory("developer")

        # Verify memory cleared
        memory = await memory_service.load_agent_memory("developer")
        assert memory["conversations"] == []

    @pytest.mark.asyncio
    async def test_get_conversation_count(self, memory_service):
        """Test getting conversation count."""
        # Add conversations
        await memory_service.add_conversation(
            "manager", "user", "Message 1", project_id=1
        )
        await memory_service.add_conversation(
            "manager", "agent", "Response 1", project_id=1
        )
        await memory_service.add_conversation(
            "manager", "user", "Message 2", project_id=1
        )

        count = await memory_service.get_conversation_count("manager")
        assert count == 3

    # ==================== Concurrency Tests ====================

    @pytest.mark.asyncio
    async def test_concurrent_memory_access(self, memory_service):
        """Test concurrent access to same agent memory."""

        async def add_messages(agent_name, count):
            for i in range(count):
                await memory_service.add_conversation(
                    agent_name=agent_name, role="user", content=f"Message {i}"
                )

        # Run concurrent tasks
        await asyncio.gather(
            add_messages("developer", 5),
            add_messages("developer", 5),
            add_messages("developer", 5),
        )

        # Verify all messages saved
        count = await memory_service.get_conversation_count("developer")
        assert count == 15

    # ==================== Edge Case Tests ====================

    @pytest.mark.asyncio
    async def test_max_conversations_limit(self, memory_service):
        """Test max conversations limit."""
        # Set low limit
        memory = await memory_service.load_agent_memory("researcher")
        memory["settings"]["max_conversations"] = 3
        await memory_service.save_agent_memory("researcher", memory)

        # Add more conversations than limit
        for i in range(5):
            await memory_service.add_conversation(
                agent_name="researcher", role="user", content=f"Message {i}"
            )

        # Verify only last 3 kept
        memory = await memory_service.load_agent_memory("researcher")
        assert len(memory["conversations"]) == 3

        # Verify oldest removed
        conversation_contents = [c["content"] for c in memory["conversations"]]
        assert "Message 0" not in conversation_contents
        assert "Message 1" not in conversation_contents
        assert "Message 4" in conversation_contents

    @pytest.mark.asyncio
    async def test_file_locking(self, memory_service):
        """Test file locking prevents concurrent write conflicts."""

        async def write_concurrent(agent_name, task_id):
            for i in range(10):
                await memory_service.add_conversation(
                    agent_name=agent_name,
                    role="user",
                    content=f"Task {task_id} Message {i}",
                )

        # Run 5 concurrent tasks
        tasks = [write_concurrent("manager", i) for i in range(5)]
        await asyncio.gather(*tasks)

        # Verify no data loss
        count = await memory_service.get_conversation_count("manager")
        assert count == 50


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
