"""Unit tests for agent artifacts (GAP-AGENT-001 Unified Ontology).

Tests the extensions to Artifact that enable agents as artifacts:
- has_standing field: Can own things, enter contracts
- can_execute field: Can execute code autonomously
- memory_artifact_id field: Link to separate memory artifact
- is_principal property: True if has_standing
- is_agent property: True if has_standing AND can_execute
- create_agent_artifact() factory function
- create_memory_artifact() factory function

Test cases based on GAP-AGENT-001 implementation plan:
- test_agent_is_artifact: Agent stored as artifact with is_agent == True
- test_has_standing: Agent has standing
- test_can_execute: Agent can execute
- test_memory_artifact: Memory stored separately
- test_agent_owns_memory: Agent owns its memory
- test_non_agent_artifact: Regular artifact flags default to False
- test_factory_function: Factory creates correct artifact
"""

from __future__ import annotations

import json

import pytest

from src.world.artifacts import (
    Artifact,
    ArtifactStore,
    create_agent_artifact,
    create_memory_artifact,
    default_policy,
)


class TestArtifactPrincipalFields:
    """Tests for the new principal capability fields on Artifact."""

    def test_has_standing_default_false(self) -> None:
        """Verify has_standing defaults to False for regular artifacts."""
        artifact = Artifact(
            id="test_artifact",
            type="data",
            content="test content",
            created_by="owner_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert artifact.has_standing is False

    def test_can_execute_default_false(self) -> None:
        """Verify can_execute defaults to False for regular artifacts."""
        artifact = Artifact(
            id="test_artifact",
            type="data",
            content="test content",
            created_by="owner_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert artifact.can_execute is False

    def test_memory_artifact_id_default_none(self) -> None:
        """Verify memory_artifact_id defaults to None."""
        artifact = Artifact(
            id="test_artifact",
            type="data",
            content="test content",
            created_by="owner_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert artifact.memory_artifact_id is None

    def test_has_standing_can_be_set_true(self) -> None:
        """Verify has_standing can be set to True."""
        artifact = Artifact(
            id="dao_1",
            type="dao",
            content="{}",
            created_by="dao_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            has_standing=True,
        )
        assert artifact.has_standing is True

    def test_can_execute_can_be_set_true(self) -> None:
        """Verify can_execute can be set to True."""
        artifact = Artifact(
            id="agent_1",
            type="agent",
            content="{}",
            created_by="agent_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            can_execute=True,
        )
        assert artifact.can_execute is True

    def test_memory_artifact_id_can_be_set(self) -> None:
        """Verify memory_artifact_id can be set to a string."""
        artifact = Artifact(
            id="agent_1",
            type="agent",
            content="{}",
            created_by="agent_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            memory_artifact_id="agent_1_memory",
        )
        assert artifact.memory_artifact_id == "agent_1_memory"


class TestIsPrincipalProperty:
    """Tests for the is_principal property."""

    def test_is_principal_false_when_no_standing(self) -> None:
        """Verify is_principal is False when has_standing is False."""
        artifact = Artifact(
            id="data_1",
            type="data",
            content="test",
            created_by="owner_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            has_standing=False,
        )
        assert artifact.is_principal is False

    def test_is_principal_true_when_has_standing(self) -> None:
        """Verify is_principal is True when has_standing is True."""
        artifact = Artifact(
            id="dao_1",
            type="dao",
            content="{}",
            created_by="dao_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            has_standing=True,
        )
        assert artifact.is_principal is True

    def test_is_principal_independent_of_can_execute(self) -> None:
        """Verify is_principal only depends on has_standing, not can_execute."""
        # Principal without execution capability (e.g., a DAO)
        dao = Artifact(
            id="dao_1",
            type="dao",
            content="{}",
            created_by="dao_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            has_standing=True,
            can_execute=False,
        )
        assert dao.is_principal is True

        # Agent with both capabilities
        agent = Artifact(
            id="agent_1",
            type="agent",
            content="{}",
            created_by="agent_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            has_standing=True,
            can_execute=True,
        )
        assert agent.is_principal is True


class TestIsAgentProperty:
    """Tests for the is_agent property."""

    def test_is_agent_false_for_regular_artifact(self) -> None:
        """Verify is_agent is False for regular artifacts."""
        artifact = Artifact(
            id="data_1",
            type="data",
            content="test",
            created_by="owner_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert artifact.is_agent is False

    def test_is_agent_false_with_only_standing(self) -> None:
        """Verify is_agent is False with only has_standing (e.g., DAO)."""
        dao = Artifact(
            id="dao_1",
            type="dao",
            content="{}",
            created_by="dao_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            has_standing=True,
            can_execute=False,
        )
        assert dao.is_agent is False

    def test_is_agent_false_with_only_execute(self) -> None:
        """Verify is_agent is False with only can_execute (invalid state)."""
        # This is a degenerate case - can_execute without has_standing
        # should not occur in practice but we test the logic
        artifact = Artifact(
            id="code_1",
            type="code",
            content="{}",
            created_by="owner_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            has_standing=False,
            can_execute=True,
        )
        assert artifact.is_agent is False

    def test_is_agent_true_with_both_capabilities(self) -> None:
        """Verify is_agent is True when has_standing AND can_execute."""
        agent = Artifact(
            id="agent_1",
            type="agent",
            content="{}",
            created_by="agent_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            has_standing=True,
            can_execute=True,
        )
        assert agent.is_agent is True


class TestCreateAgentArtifact:
    """Tests for the create_agent_artifact() factory function."""

    def test_creates_artifact_with_correct_type(self) -> None:
        """Verify factory creates artifact with type='agent'."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={"model": "test"},
        )
        assert agent.type == "agent"

    def test_creates_artifact_with_correct_id(self) -> None:
        """Verify factory uses provided agent_id."""
        agent = create_agent_artifact(
            agent_id="my_agent",
            created_by="owner",
            agent_config={},
        )
        assert agent.id == "my_agent"

    def test_creates_artifact_with_correct_owner(self) -> None:
        """Verify factory uses provided created_by."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="different_owner",
            agent_config={},
        )
        assert agent.created_by == "different_owner"

    def test_creates_self_owned_agent(self) -> None:
        """Verify can create self-owned agent (owner == id)."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
        )
        assert agent.created_by == agent.id

    def test_has_standing_is_true(self) -> None:
        """Verify factory sets has_standing=True."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
        )
        assert agent.has_standing is True

    def test_can_execute_is_true(self) -> None:
        """Verify factory sets can_execute=True."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
        )
        assert agent.can_execute is True

    def test_is_agent_is_true(self) -> None:
        """Verify created artifact reports is_agent=True."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
        )
        assert agent.is_agent is True

    def test_is_principal_is_true(self) -> None:
        """Verify created artifact reports is_principal=True."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
        )
        assert agent.is_principal is True

    def test_stores_config_as_content(self) -> None:
        """Verify agent_config is stored as JSON content."""
        config = {"model": "gpt-4", "system_prompt": "You are helpful."}
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config=config,
        )
        stored_config = json.loads(agent.content)
        assert stored_config == config

    def test_memory_artifact_id_default_none(self) -> None:
        """Verify memory_artifact_id defaults to None."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
        )
        assert agent.memory_artifact_id is None

    def test_memory_artifact_id_can_be_set(self) -> None:
        """Verify memory_artifact_id can be provided."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
            memory_artifact_id="agent_001_memory",
        )
        assert agent.memory_artifact_id == "agent_001_memory"

    def test_default_access_contract_is_self_owned(self) -> None:
        """Verify default access is self-owned (restrictive)."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
        )
        # Self-owned means empty allow lists (owner always implicitly allowed)
        assert agent.policy["allow_read"] == []
        assert agent.policy["allow_write"] == []

    def test_freeware_access_contract(self) -> None:
        """Verify freeware access opens read access."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
            access_contract_id="genesis_contract_freeware",
        )
        # Freeware uses default policy (open read)
        assert "*" in agent.policy["allow_read"]

    def test_public_access_contract(self) -> None:
        """Verify public access opens all access."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
            access_contract_id="genesis_contract_public",
        )
        assert "*" in agent.policy["allow_read"]
        assert "*" in agent.policy["allow_write"]
        assert "*" in agent.policy["allow_invoke"]

    def test_sets_timestamps(self) -> None:
        """Verify factory sets created_at and updated_at."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
        )
        assert agent.created_at is not None
        assert agent.updated_at is not None
        assert len(agent.created_at) > 0

    def test_executable_is_false(self) -> None:
        """Verify agents don't use executable code path."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
        )
        assert agent.executable is False

    def test_code_is_empty(self) -> None:
        """Verify agents don't have inline code."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
        )
        assert agent.code == ""


class TestCreateMemoryArtifact:
    """Tests for the create_memory_artifact() factory function."""

    def test_creates_artifact_with_correct_type(self) -> None:
        """Verify factory creates artifact with type='memory'."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        assert memory.type == "memory"

    def test_creates_artifact_with_correct_id(self) -> None:
        """Verify factory uses provided memory_id."""
        memory = create_memory_artifact(
            memory_id="my_memory",
            created_by="agent_001",
        )
        assert memory.id == "my_memory"

    def test_creates_artifact_with_correct_owner(self) -> None:
        """Verify factory uses provided created_by."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        assert memory.created_by == "agent_001"

    def test_has_standing_is_false(self) -> None:
        """Verify memory cannot own things."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        assert memory.has_standing is False

    def test_can_execute_is_false(self) -> None:
        """Verify memory cannot execute."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        assert memory.can_execute is False

    def test_is_agent_is_false(self) -> None:
        """Verify memory is not an agent."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        assert memory.is_agent is False

    def test_is_principal_is_false(self) -> None:
        """Verify memory is not a principal."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        assert memory.is_principal is False

    def test_default_content_structure(self) -> None:
        """Verify default content has history and knowledge."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        content = json.loads(memory.content)
        assert "history" in content
        assert "knowledge" in content
        assert content["history"] == []
        assert content["knowledge"] == {}

    def test_custom_initial_content(self) -> None:
        """Verify custom initial content is stored."""
        initial = {
            "history": [{"action": "think", "result": "hello"}],
            "knowledge": {"fact1": "value1"},
        }
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
            initial_content=initial,
        )
        content = json.loads(memory.content)
        assert content == initial

    def test_self_owned_access(self) -> None:
        """Verify memory uses self-owned (private) access."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        # Private access: empty allow lists
        assert memory.policy["allow_read"] == []
        assert memory.policy["allow_write"] == []

    def test_memory_artifact_id_is_none(self) -> None:
        """Verify memory doesn't have its own memory."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        assert memory.memory_artifact_id is None

    def test_sets_timestamps(self) -> None:
        """Verify factory sets timestamps."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        assert memory.created_at is not None
        assert memory.updated_at is not None


class TestAgentOwnsMemory:
    """Tests for the pattern where an agent owns its memory artifact."""

    def test_agent_memory_ownership(self) -> None:
        """Verify agent can own a memory artifact."""
        # Create memory first
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )

        # Create agent with link to memory
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={"model": "test"},
            memory_artifact_id="agent_001_memory",
        )

        # Verify relationships
        assert agent.memory_artifact_id == memory.id
        assert memory.created_by == agent.id

    def test_agent_is_principal_memory_is_not(self) -> None:
        """Verify only agent is principal, not memory."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
            memory_artifact_id="agent_001_memory",
        )

        assert agent.is_principal is True
        assert memory.is_principal is False


class TestToDictWithNewFields:
    """Tests for to_dict() serialization of new fields."""

    def test_to_dict_excludes_false_has_standing(self) -> None:
        """Verify to_dict omits has_standing when False (default)."""
        artifact = Artifact(
            id="data_1",
            type="data",
            content="test",
            created_by="owner_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        d = artifact.to_dict()
        assert "has_standing" not in d

    def test_to_dict_includes_true_has_standing(self) -> None:
        """Verify to_dict includes has_standing when True."""
        artifact = Artifact(
            id="agent_1",
            type="agent",
            content="{}",
            created_by="agent_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            has_standing=True,
        )
        d = artifact.to_dict()
        assert d["has_standing"] is True

    def test_to_dict_excludes_false_can_execute(self) -> None:
        """Verify to_dict omits can_execute when False (default)."""
        artifact = Artifact(
            id="data_1",
            type="data",
            content="test",
            created_by="owner_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        d = artifact.to_dict()
        assert "can_execute" not in d

    def test_to_dict_includes_true_can_execute(self) -> None:
        """Verify to_dict includes can_execute when True."""
        artifact = Artifact(
            id="agent_1",
            type="agent",
            content="{}",
            created_by="agent_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            can_execute=True,
        )
        d = artifact.to_dict()
        assert d["can_execute"] is True

    def test_to_dict_excludes_none_memory_artifact_id(self) -> None:
        """Verify to_dict omits memory_artifact_id when None."""
        artifact = Artifact(
            id="data_1",
            type="data",
            content="test",
            created_by="owner_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        d = artifact.to_dict()
        assert "memory_artifact_id" not in d

    def test_to_dict_includes_memory_artifact_id_when_set(self) -> None:
        """Verify to_dict includes memory_artifact_id when set."""
        artifact = Artifact(
            id="agent_1",
            type="agent",
            content="{}",
            created_by="agent_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            memory_artifact_id="agent_1_memory",
        )
        d = artifact.to_dict()
        assert d["memory_artifact_id"] == "agent_1_memory"

    def test_agent_artifact_to_dict_complete(self) -> None:
        """Verify agent artifact to_dict includes all relevant fields."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={"model": "test"},
            memory_artifact_id="agent_001_memory",
        )
        d = agent.to_dict()

        assert d["id"] == "agent_001"
        assert d["type"] == "agent"
        assert d["created_by"] == "agent_001"
        assert d["has_standing"] is True
        assert d["can_execute"] is True
        assert d["memory_artifact_id"] == "agent_001_memory"


class TestArtifactStoreWithAgents:
    """Tests for storing agent artifacts in ArtifactStore."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    def test_store_agent_artifact(self, store: ArtifactStore) -> None:
        """Verify agent artifact can be stored."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={"model": "test"},
        )
        store.artifacts[agent.id] = agent

        retrieved = store.get("agent_001")
        assert retrieved is not None
        assert retrieved.is_agent is True

    def test_store_memory_artifact(self, store: ArtifactStore) -> None:
        """Verify memory artifact can be stored."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        store.artifacts[memory.id] = memory

        retrieved = store.get("agent_001_memory")
        assert retrieved is not None
        assert retrieved.type == "memory"

    def test_store_agent_and_memory_together(self, store: ArtifactStore) -> None:
        """Verify agent and memory can be stored together."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
            memory_artifact_id="agent_001_memory",
        )

        store.artifacts[memory.id] = memory
        store.artifacts[agent.id] = agent

        # Verify both exist
        assert store.exists("agent_001")
        assert store.exists("agent_001_memory")

        # Verify agent links to memory
        retrieved_agent = store.get("agent_001")
        assert retrieved_agent is not None
        assert retrieved_agent.memory_artifact_id == "agent_001_memory"

        # Verify memory is owned by agent
        retrieved_memory = store.get("agent_001_memory")
        assert retrieved_memory is not None
        assert retrieved_memory.created_by == "agent_001"

    def test_list_by_owner_includes_agent_artifacts(
        self, store: ArtifactStore
    ) -> None:
        """Verify list_by_owner includes agent and memory artifacts."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            created_by="agent_001",
        )
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
            memory_artifact_id="agent_001_memory",
        )

        store.artifacts[memory.id] = memory
        store.artifacts[agent.id] = agent

        owned = store.list_by_owner("agent_001")
        assert len(owned) == 2
        ids = {a["id"] for a in owned}
        assert "agent_001" in ids
        assert "agent_001_memory" in ids


class TestNonAgentArtifact:
    """Tests verifying regular artifacts don't have agent capabilities."""

    def test_executable_artifact_not_agent(self) -> None:
        """Verify executable artifacts are not agents by default."""
        executable = Artifact(
            id="contract_1",
            type="contract",
            content="def run(): pass",
            created_by="owner_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
            executable=True,
            code="def run(): pass",
        )
        assert executable.is_agent is False
        assert executable.is_principal is False

    def test_data_artifact_not_principal(self) -> None:
        """Verify data artifacts are not principals."""
        data = Artifact(
            id="data_1",
            type="data",
            content="some data",
            created_by="owner_1",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        assert data.is_principal is False
        assert data.is_agent is False


class TestAgentTransfer:
    """Tests for agent ownership transfer capability."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    def test_agent_ownership_transferable(self, store: ArtifactStore) -> None:
        """Verify agent ownership can be transferred via standard mechanism."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={},
        )
        store.artifacts[agent.id] = agent

        # Transfer ownership using standard artifact transfer
        success = store.transfer_ownership(
            artifact_id="agent_001",
            from_id="agent_001",
            to_id="new_owner",
        )

        assert success is True
        transferred = store.get("agent_001")
        assert transferred is not None
        assert transferred.created_by == "new_owner"
        # Still an agent after transfer
        assert transferred.is_agent is True

    def test_transfer_agent_keeps_capabilities(self, store: ArtifactStore) -> None:
        """Verify transferred agent retains its capabilities."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            created_by="agent_001",
            agent_config={"model": "gpt-4"},
            memory_artifact_id="agent_001_memory",
        )
        store.artifacts[agent.id] = agent

        store.transfer_ownership("agent_001", "agent_001", "buyer")

        transferred = store.get("agent_001")
        assert transferred is not None
        assert transferred.has_standing is True
        assert transferred.can_execute is True
        assert transferred.memory_artifact_id == "agent_001_memory"
        # Config preserved
        config = json.loads(transferred.content)
        assert config["model"] == "gpt-4"


# =============================================================================
# INT-004: Agent Runtime from Artifact Tests
# =============================================================================


class TestAgentFromArtifact:
    """Tests for Agent.from_artifact() and artifact-backed agents."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    def test_from_artifact_creates_agent(self, store: ArtifactStore) -> None:
        """Verify Agent.from_artifact() creates an agent from artifact."""
        from src.agents.agent import Agent

        # Create agent artifact
        artifact = create_agent_artifact(
            agent_id="test_agent",
            created_by="test_agent",
            agent_config={"llm_model": "test-model", "system_prompt": "Test prompt"},
        )
        store.artifacts[artifact.id] = artifact

        # Create agent from artifact
        agent = Agent.from_artifact(artifact, store=store)

        assert agent.agent_id == "test_agent"
        assert agent.is_artifact_backed is True
        assert agent.artifact is artifact

    def test_from_artifact_loads_config(self, store: ArtifactStore) -> None:
        """Verify Agent.from_artifact() loads config from artifact content."""
        from src.agents.agent import Agent

        config = {
            "llm_model": "custom-model",
            "system_prompt": "Custom prompt",
            "action_schema": "Custom schema",
            "rag": {"enabled": False, "limit": 10},
        }
        artifact = create_agent_artifact(
            agent_id="config_agent",
            created_by="config_agent",
            agent_config=config,
        )
        store.artifacts[artifact.id] = artifact

        agent = Agent.from_artifact(artifact, store=store)

        assert agent.llm_model == "custom-model"
        assert agent.system_prompt == "Custom prompt"
        assert agent.action_schema == "Custom schema"

    def test_from_artifact_rejects_non_agent(self, store: ArtifactStore) -> None:
        """Verify Agent.from_artifact() rejects non-agent artifacts."""
        from src.agents.agent import Agent

        # Create regular artifact (not an agent)
        artifact = Artifact(
            id="data_artifact",
            type="data",
            content="some data",
            created_by="owner",
            created_at="2024-01-01T00:00:00",
            updated_at="2024-01-01T00:00:00",
        )
        store.artifacts[artifact.id] = artifact

        with pytest.raises(ValueError, match="Cannot create Agent from non-agent artifact"):
            Agent.from_artifact(artifact, store=store)

    def test_from_artifact_memory_link(self, store: ArtifactStore) -> None:
        """Verify Agent.from_artifact() preserves memory link."""
        from src.agents.agent import Agent

        # Create memory artifact
        memory = create_memory_artifact(
            memory_id="agent_memory",
            created_by="linked_agent",
        )
        store.artifacts[memory.id] = memory

        # Create agent with memory link
        artifact = create_agent_artifact(
            agent_id="linked_agent",
            created_by="linked_agent",
            agent_config={},
            memory_artifact_id="agent_memory",
        )
        store.artifacts[artifact.id] = artifact

        agent = Agent.from_artifact(artifact, store=store)

        assert agent.memory_artifact_id == "agent_memory"
        assert agent.artifact_store is store


class TestAgentToArtifact:
    """Tests for Agent.to_artifact() serialization."""

    def test_to_artifact_basic(self) -> None:
        """Verify to_artifact() creates valid agent artifact."""
        from src.agents.agent import Agent

        agent = Agent(
            agent_id="serialize_agent",
            llm_model="test-model",
            system_prompt="Test prompt",
        )

        artifact = agent.to_artifact()

        assert artifact.id == "serialize_agent"
        assert artifact.is_agent is True
        assert artifact.type == "agent"
        assert artifact.created_by == "serialize_agent"  # Self-owned by default

    def test_to_artifact_preserves_config(self) -> None:
        """Verify to_artifact() preserves agent config."""
        from src.agents.agent import Agent

        agent = Agent(
            agent_id="config_serialize",
            llm_model="custom-model",
            system_prompt="Custom system prompt",
            action_schema="Custom action schema",
        )

        artifact = agent.to_artifact()
        config = json.loads(artifact.content)

        assert config["llm_model"] == "custom-model"
        assert config["system_prompt"] == "Custom system prompt"
        assert config["action_schema"] == "Custom action schema"

    def test_to_artifact_roundtrip(self) -> None:
        """Verify agent can be serialized and restored."""
        from src.agents.agent import Agent

        original = Agent(
            agent_id="roundtrip_agent",
            llm_model="roundtrip-model",
            system_prompt="Roundtrip prompt",
        )

        artifact = original.to_artifact()
        restored = Agent.from_artifact(artifact)

        assert restored.agent_id == original.agent_id
        assert restored.llm_model == original.llm_model
        assert restored.system_prompt == original.system_prompt


class TestAgentBackwardCompatibility:
    """Tests ensuring backward compatibility without artifact backing."""

    def test_agent_without_artifact(self) -> None:
        """Verify agents work without artifact backing."""
        from src.agents.agent import Agent

        agent = Agent(
            agent_id="no_artifact_agent",
            llm_model="test-model",
        )

        assert agent.agent_id == "no_artifact_agent"
        assert agent.is_artifact_backed is False
        assert agent.artifact is None
        assert agent.memory_artifact_id is None

    def test_agent_properties_without_artifact(self) -> None:
        """Verify agent properties work without artifact."""
        from src.agents.agent import Agent

        agent = Agent(
            agent_id="props_agent",
            llm_model="props-model",
            system_prompt="Props prompt",
            action_schema="Props schema",
        )

        assert agent.llm_model == "props-model"
        assert agent.system_prompt == "Props prompt"
        assert agent.action_schema == "Props schema"

    def test_agent_property_setters(self) -> None:
        """Verify agent property setters work."""
        from src.agents.agent import Agent

        agent = Agent(
            agent_id="setter_agent",
            system_prompt="Original prompt",
        )

        agent.system_prompt = "Modified prompt"
        agent.action_schema = "Modified schema"

        assert agent.system_prompt == "Modified prompt"
        assert agent.action_schema == "Modified schema"


class TestAgentLoaderArtifacts:
    """Tests for AgentLoader artifact creation functions."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    def test_create_agent_artifacts(self, store: ArtifactStore) -> None:
        """Verify create_agent_artifacts creates artifacts in store."""
        from src.agents.loader import create_agent_artifacts, AgentConfig

        configs: list[AgentConfig] = [
            {
                "id": "loader_agent_1",
                "llm_model": "model1",
                "starting_scrip": 100,
                "system_prompt": "Prompt 1",
                "action_schema": "",
            },
            {
                "id": "loader_agent_2",
                "llm_model": "model2",
                "starting_scrip": 200,
                "system_prompt": "Prompt 2",
                "action_schema": "",
            },
        ]

        artifacts = create_agent_artifacts(store, configs)

        assert len(artifacts) == 2
        assert store.exists("loader_agent_1")
        assert store.exists("loader_agent_2")
        assert store.get("loader_agent_1").is_agent  # type: ignore[union-attr]
        assert store.get("loader_agent_2").is_agent  # type: ignore[union-attr]

    def test_create_agent_artifacts_with_memory(self, store: ArtifactStore) -> None:
        """Verify create_agent_artifacts creates memory artifacts."""
        from src.agents.loader import create_agent_artifacts, AgentConfig

        configs: list[AgentConfig] = [
            {
                "id": "memory_loader_agent",
                "llm_model": None,
                "starting_scrip": 100,
                "system_prompt": "",
                "action_schema": "",
            },
        ]

        create_agent_artifacts(store, configs, create_memory=True)

        # Agent artifact exists
        assert store.exists("memory_loader_agent")
        # Memory artifact exists
        assert store.exists("memory_loader_agent_memory")
        # Agent links to memory
        agent = store.get("memory_loader_agent")
        assert agent is not None
        assert agent.memory_artifact_id == "memory_loader_agent_memory"

    def test_create_agent_artifacts_without_memory(self, store: ArtifactStore) -> None:
        """Verify create_agent_artifacts can skip memory creation."""
        from src.agents.loader import create_agent_artifacts, AgentConfig

        configs: list[AgentConfig] = [
            {
                "id": "no_memory_agent",
                "llm_model": None,
                "starting_scrip": 100,
                "system_prompt": "",
                "action_schema": "",
            },
        ]

        create_agent_artifacts(store, configs, create_memory=False)

        assert store.exists("no_memory_agent")
        assert not store.exists("no_memory_agent_memory")
        agent = store.get("no_memory_agent")
        assert agent is not None
        assert agent.memory_artifact_id is None

    def test_load_agents_from_store(self, store: ArtifactStore) -> None:
        """Verify load_agents_from_store creates Agent instances."""
        from src.agents.loader import create_agent_artifacts, load_agents_from_store, AgentConfig

        configs: list[AgentConfig] = [
            {
                "id": "store_agent_1",
                "llm_model": "store-model",
                "starting_scrip": 100,
                "system_prompt": "Store prompt",
                "action_schema": "",
            },
        ]

        create_agent_artifacts(store, configs)
        agents = load_agents_from_store(store)

        assert len(agents) == 1
        assert agents[0].agent_id == "store_agent_1"
        assert agents[0].is_artifact_backed is True
        assert agents[0].system_prompt == "Store prompt"

    def test_load_agents_from_store_ignores_non_agents(self, store: ArtifactStore) -> None:
        """Verify load_agents_from_store ignores non-agent artifacts."""
        from src.agents.loader import create_agent_artifacts, load_agents_from_store, AgentConfig

        # Create one agent
        configs: list[AgentConfig] = [
            {
                "id": "only_agent",
                "llm_model": None,
                "starting_scrip": 100,
                "system_prompt": "",
                "action_schema": "",
            },
        ]
        create_agent_artifacts(store, configs)

        # Add non-agent artifact
        store.write(
            artifact_id="data_item",
            type="data",
            content="some data",
            created_by="someone",
        )

        agents = load_agents_from_store(store)

        assert len(agents) == 1
        assert agents[0].agent_id == "only_agent"


class TestAgentArtifactIntegration:
    """Integration tests for artifact-backed agents."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    def test_full_lifecycle(self, store: ArtifactStore) -> None:
        """Test full agent lifecycle: create, serialize, restore."""
        from src.agents.agent import Agent

        # Create agent without artifact
        original = Agent(
            agent_id="lifecycle_agent",
            llm_model="lifecycle-model",
            system_prompt="Lifecycle prompt",
        )

        # Serialize to artifact
        artifact = original.to_artifact()
        store.artifacts[artifact.id] = artifact

        # Restore from artifact
        restored = Agent.from_artifact(artifact, store=store)

        # Verify restoration
        assert restored.agent_id == original.agent_id
        assert restored.llm_model == original.llm_model
        assert restored.system_prompt == original.system_prompt
        assert restored.is_artifact_backed is True

    def test_agent_with_transferred_artifact(self, store: ArtifactStore) -> None:
        """Test agent behavior after artifact ownership transfer."""
        from src.agents.agent import Agent

        # Create agent artifact
        artifact = create_agent_artifact(
            agent_id="transfer_agent",
            created_by="original_owner",
            agent_config={"llm_model": "transfer-model"},
        )
        store.artifacts[artifact.id] = artifact

        # Transfer ownership
        store.transfer_ownership("transfer_agent", "original_owner", "new_owner")

        # Create agent from transferred artifact
        agent = Agent.from_artifact(store.get("transfer_agent"), store=store)  # type: ignore[arg-type]

        # Agent ID should be artifact ID, not owner
        assert agent.agent_id == "transfer_agent"
        assert agent.artifact.created_by == "new_owner"  # type: ignore[union-attr]
