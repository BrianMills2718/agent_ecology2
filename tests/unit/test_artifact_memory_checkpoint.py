"""Tests for ArtifactMemory checkpoint persistence.

Plan #10: Memory Persistence
Verifies that artifact-backed memory persists across checkpoint save/restore.
"""

import json
import pytest
from typing import Any

from src.agents.memory import ArtifactMemory
from src.world.artifacts import ArtifactStore


def restore_artifact(store: ArtifactStore, artifact_data: dict[str, Any]) -> None:
    """Restore an artifact from checkpoint data (mirrors runner.py logic)."""
    artifact = store.write(
        artifact_id=artifact_data["id"],
        type=artifact_data.get("type", "data"),
        content=artifact_data.get("content", ""),
        created_by=artifact_data.get("created_by", "system"),
        executable=artifact_data.get("executable", False),
        price=artifact_data.get("price", 0),
        code=artifact_data.get("code", ""),
        policy=artifact_data.get("policy"),
    )
    # Restore extra fields
    if artifact_data.get("has_standing"):
        artifact.has_standing = True
    if artifact_data.get("has_loop") or artifact_data.get("can_execute"):
        artifact.has_loop = True
    if artifact_data.get("memory_artifact_id"):
        artifact.memory_artifact_id = artifact_data["memory_artifact_id"]


@pytest.mark.plans([10])
class TestArtifactMemoryCheckpointPersistence:
    """Tests that ArtifactMemory persists through checkpoint save/restore."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    @pytest.fixture
    def artifact_memory(self, store: ArtifactStore) -> ArtifactMemory:
        """Create an ArtifactMemory instance."""
        return ArtifactMemory(store)

    def test_persists_with_checkpoint(
        self, store: ArtifactStore, artifact_memory: ArtifactMemory
    ) -> None:
        """Memory persists when artifacts are saved and restored via checkpoint.

        This verifies the core Plan #10 requirement: memory should be
        consistent with simulation checkpoints.
        """
        # Add memories
        artifact_memory.add("agent_1", "First memory", tick=1)
        artifact_memory.add("agent_1", "Second memory", tick=2)
        artifact_memory.set_knowledge("agent_1", "learned_skill", "trading")

        # Simulate checkpoint save: serialize all artifacts
        checkpoint_data = [a.to_dict() for a in store.artifacts.values()]

        # Create a new store (simulating checkpoint restore)
        new_store = ArtifactStore()
        for artifact_dict in checkpoint_data:
            restore_artifact(new_store, artifact_dict)

        # Create new memory instance pointing to restored store
        restored_memory = ArtifactMemory(new_store)

        # Verify memories were restored
        memories = restored_memory.get_all_memories("agent_1")
        assert len(memories) == 2
        assert memories[0]["content"] == "First memory"
        assert memories[1]["content"] == "Second memory"

        # Verify knowledge was restored
        skill = restored_memory.get_knowledge("agent_1", "learned_skill")
        assert skill == "trading"

    def test_cleared_on_rollback(
        self, store: ArtifactStore, artifact_memory: ArtifactMemory
    ) -> None:
        """Memory reverts to checkpoint state on rollback.

        This tests that memories added after a checkpoint are lost
        when rolling back to that checkpoint state.
        """
        # Add initial memories
        artifact_memory.add("agent_1", "Before checkpoint", tick=1)

        # Save checkpoint
        checkpoint_data = [a.to_dict() for a in store.artifacts.values()]

        # Add more memories after checkpoint
        artifact_memory.add("agent_1", "After checkpoint 1", tick=5)
        artifact_memory.add("agent_1", "After checkpoint 2", tick=6)

        # Verify we have 3 memories now
        all_memories = artifact_memory.get_all_memories("agent_1")
        assert len(all_memories) == 3

        # Rollback: restore from checkpoint
        store.artifacts.clear()
        for artifact_dict in checkpoint_data:
            restore_artifact(store, artifact_dict)

        # Create fresh memory instance (simulating what happens after rollback)
        rolled_back_memory = ArtifactMemory(store)

        # Verify only checkpoint memories remain
        memories = rolled_back_memory.get_all_memories("agent_1")
        assert len(memories) == 1
        assert memories[0]["content"] == "Before checkpoint"

    def test_search_returns_relevant(
        self, store: ArtifactStore, artifact_memory: ArtifactMemory
    ) -> None:
        """Search returns most recent memories (relevance by recency).

        Note: ArtifactMemory uses recency-based search, not semantic search.
        This is acceptable for checkpoint consistency - semantic search
        can be added later without changing checkpoint behavior.
        """
        # Add memories in order
        for i in range(10):
            artifact_memory.add("agent_1", f"Memory about topic {i}", tick=i)

        # Search returns most recent
        results = artifact_memory.search("agent_1", "topic", limit=3)

        assert len(results) == 3
        # Most recent first
        assert "Memory about topic 9" in results[0]["memory"]
        assert "Memory about topic 8" in results[1]["memory"]
        assert "Memory about topic 7" in results[2]["memory"]


@pytest.mark.plans([10])
class TestArtifactMemoryCheckpointEdgeCases:
    """Edge case tests for checkpoint persistence."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    def test_empty_memory_persists(self, store: ArtifactStore) -> None:
        """Empty memory artifact structure persists correctly."""
        memory = ArtifactMemory(store)

        # Touch memory to create artifact (no actual memories added)
        _ = memory.get_all_memories("agent_1")

        # Checkpoint
        checkpoint_data = [a.to_dict() for a in store.artifacts.values()]

        # Restore
        new_store = ArtifactStore()
        for artifact_dict in checkpoint_data:
            restore_artifact(new_store, artifact_dict)

        # Verify empty structure
        restored_memory = ArtifactMemory(new_store)
        memories = restored_memory.get_all_memories("agent_1")
        assert memories == []

    def test_multiple_agents_isolated(self, store: ArtifactStore) -> None:
        """Each agent's memory is isolated through checkpoint."""
        memory = ArtifactMemory(store)

        # Add memories for different agents
        memory.add("agent_1", "Agent 1 memory")
        memory.add("agent_2", "Agent 2 memory")

        # Checkpoint
        checkpoint_data = [a.to_dict() for a in store.artifacts.values()]

        # Restore
        new_store = ArtifactStore()
        for artifact_dict in checkpoint_data:
            restore_artifact(new_store, artifact_dict)

        restored_memory = ArtifactMemory(new_store)

        # Verify isolation
        agent1_memories = restored_memory.get_all_memories("agent_1")
        agent2_memories = restored_memory.get_all_memories("agent_2")

        assert len(agent1_memories) == 1
        assert len(agent2_memories) == 1
        assert agent1_memories[0]["content"] == "Agent 1 memory"
        assert agent2_memories[0]["content"] == "Agent 2 memory"

    def test_knowledge_separate_from_history(self, store: ArtifactStore) -> None:
        """Knowledge and history persist independently."""
        memory = ArtifactMemory(store)

        memory.add("agent_1", "History entry")
        memory.set_knowledge("agent_1", "key", "value")

        # Checkpoint
        checkpoint_data = [a.to_dict() for a in store.artifacts.values()]

        # Restore
        new_store = ArtifactStore()
        for artifact_dict in checkpoint_data:
            restore_artifact(new_store, artifact_dict)

        restored_memory = ArtifactMemory(new_store)

        # Both should be restored
        assert len(restored_memory.get_all_memories("agent_1")) == 1
        assert restored_memory.get_knowledge("agent_1", "key") == "value"
