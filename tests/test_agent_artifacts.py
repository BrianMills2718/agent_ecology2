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
            owner_id="owner_1",
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
            owner_id="owner_1",
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
            owner_id="owner_1",
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
            owner_id="dao_1",
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
            owner_id="agent_1",
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
            owner_id="agent_1",
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
            owner_id="owner_1",
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
            owner_id="dao_1",
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
            owner_id="dao_1",
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
            owner_id="agent_1",
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
            owner_id="owner_1",
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
            owner_id="dao_1",
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
            owner_id="owner_1",
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
            owner_id="agent_1",
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
            owner_id="agent_001",
            agent_config={"model": "test"},
        )
        assert agent.type == "agent"

    def test_creates_artifact_with_correct_id(self) -> None:
        """Verify factory uses provided agent_id."""
        agent = create_agent_artifact(
            agent_id="my_agent",
            owner_id="owner",
            agent_config={},
        )
        assert agent.id == "my_agent"

    def test_creates_artifact_with_correct_owner(self) -> None:
        """Verify factory uses provided owner_id."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="different_owner",
            agent_config={},
        )
        assert agent.owner_id == "different_owner"

    def test_creates_self_owned_agent(self) -> None:
        """Verify can create self-owned agent (owner == id)."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config={},
        )
        assert agent.owner_id == agent.id

    def test_has_standing_is_true(self) -> None:
        """Verify factory sets has_standing=True."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config={},
        )
        assert agent.has_standing is True

    def test_can_execute_is_true(self) -> None:
        """Verify factory sets can_execute=True."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config={},
        )
        assert agent.can_execute is True

    def test_is_agent_is_true(self) -> None:
        """Verify created artifact reports is_agent=True."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config={},
        )
        assert agent.is_agent is True

    def test_is_principal_is_true(self) -> None:
        """Verify created artifact reports is_principal=True."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config={},
        )
        assert agent.is_principal is True

    def test_stores_config_as_content(self) -> None:
        """Verify agent_config is stored as JSON content."""
        config = {"model": "gpt-4", "system_prompt": "You are helpful."}
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config=config,
        )
        stored_config = json.loads(agent.content)
        assert stored_config == config

    def test_memory_artifact_id_default_none(self) -> None:
        """Verify memory_artifact_id defaults to None."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config={},
        )
        assert agent.memory_artifact_id is None

    def test_memory_artifact_id_can_be_set(self) -> None:
        """Verify memory_artifact_id can be provided."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config={},
            memory_artifact_id="agent_001_memory",
        )
        assert agent.memory_artifact_id == "agent_001_memory"

    def test_default_access_contract_is_self_owned(self) -> None:
        """Verify default access is self-owned (restrictive)."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config={},
        )
        # Self-owned means empty allow lists (owner always implicitly allowed)
        assert agent.policy["allow_read"] == []
        assert agent.policy["allow_write"] == []

    def test_freeware_access_contract(self) -> None:
        """Verify freeware access opens read access."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config={},
            access_contract_id="genesis_contract_freeware",
        )
        # Freeware uses default policy (open read)
        assert "*" in agent.policy["allow_read"]

    def test_public_access_contract(self) -> None:
        """Verify public access opens all access."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
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
            owner_id="agent_001",
            agent_config={},
        )
        assert agent.created_at is not None
        assert agent.updated_at is not None
        assert len(agent.created_at) > 0

    def test_executable_is_false(self) -> None:
        """Verify agents don't use executable code path."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config={},
        )
        assert agent.executable is False

    def test_code_is_empty(self) -> None:
        """Verify agents don't have inline code."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config={},
        )
        assert agent.code == ""


class TestCreateMemoryArtifact:
    """Tests for the create_memory_artifact() factory function."""

    def test_creates_artifact_with_correct_type(self) -> None:
        """Verify factory creates artifact with type='memory'."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            owner_id="agent_001",
        )
        assert memory.type == "memory"

    def test_creates_artifact_with_correct_id(self) -> None:
        """Verify factory uses provided memory_id."""
        memory = create_memory_artifact(
            memory_id="my_memory",
            owner_id="agent_001",
        )
        assert memory.id == "my_memory"

    def test_creates_artifact_with_correct_owner(self) -> None:
        """Verify factory uses provided owner_id."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            owner_id="agent_001",
        )
        assert memory.owner_id == "agent_001"

    def test_has_standing_is_false(self) -> None:
        """Verify memory cannot own things."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            owner_id="agent_001",
        )
        assert memory.has_standing is False

    def test_can_execute_is_false(self) -> None:
        """Verify memory cannot execute."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            owner_id="agent_001",
        )
        assert memory.can_execute is False

    def test_is_agent_is_false(self) -> None:
        """Verify memory is not an agent."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            owner_id="agent_001",
        )
        assert memory.is_agent is False

    def test_is_principal_is_false(self) -> None:
        """Verify memory is not a principal."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            owner_id="agent_001",
        )
        assert memory.is_principal is False

    def test_default_content_structure(self) -> None:
        """Verify default content has history and knowledge."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            owner_id="agent_001",
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
            owner_id="agent_001",
            initial_content=initial,
        )
        content = json.loads(memory.content)
        assert content == initial

    def test_self_owned_access(self) -> None:
        """Verify memory uses self-owned (private) access."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            owner_id="agent_001",
        )
        # Private access: empty allow lists
        assert memory.policy["allow_read"] == []
        assert memory.policy["allow_write"] == []

    def test_memory_artifact_id_is_none(self) -> None:
        """Verify memory doesn't have its own memory."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            owner_id="agent_001",
        )
        assert memory.memory_artifact_id is None

    def test_sets_timestamps(self) -> None:
        """Verify factory sets timestamps."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            owner_id="agent_001",
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
            owner_id="agent_001",
        )

        # Create agent with link to memory
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
            agent_config={"model": "test"},
            memory_artifact_id="agent_001_memory",
        )

        # Verify relationships
        assert agent.memory_artifact_id == memory.id
        assert memory.owner_id == agent.id

    def test_agent_is_principal_memory_is_not(self) -> None:
        """Verify only agent is principal, not memory."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            owner_id="agent_001",
        )
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
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
            owner_id="owner_1",
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
            owner_id="agent_1",
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
            owner_id="owner_1",
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
            owner_id="agent_1",
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
            owner_id="owner_1",
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
            owner_id="agent_1",
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
            owner_id="agent_001",
            agent_config={"model": "test"},
            memory_artifact_id="agent_001_memory",
        )
        d = agent.to_dict()

        assert d["id"] == "agent_001"
        assert d["type"] == "agent"
        assert d["owner_id"] == "agent_001"
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
            owner_id="agent_001",
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
            owner_id="agent_001",
        )
        store.artifacts[memory.id] = memory

        retrieved = store.get("agent_001_memory")
        assert retrieved is not None
        assert retrieved.type == "memory"

    def test_store_agent_and_memory_together(self, store: ArtifactStore) -> None:
        """Verify agent and memory can be stored together."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            owner_id="agent_001",
        )
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
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
        assert retrieved_memory.owner_id == "agent_001"

    def test_list_by_owner_includes_agent_artifacts(
        self, store: ArtifactStore
    ) -> None:
        """Verify list_by_owner includes agent and memory artifacts."""
        memory = create_memory_artifact(
            memory_id="agent_001_memory",
            owner_id="agent_001",
        )
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
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
            owner_id="owner_1",
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
            owner_id="owner_1",
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
            owner_id="agent_001",
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
        assert transferred.owner_id == "new_owner"
        # Still an agent after transfer
        assert transferred.is_agent is True

    def test_transfer_agent_keeps_capabilities(self, store: ArtifactStore) -> None:
        """Verify transferred agent retains its capabilities."""
        agent = create_agent_artifact(
            agent_id="agent_001",
            owner_id="agent_001",
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
