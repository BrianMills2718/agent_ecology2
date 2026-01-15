"""Unit tests for agent rights trading (Plan #8).

Tests agent config stored as artifact content, enabling ownership transfer
and config modification rights.

Required tests from plan:
- test_owner_can_modify_config: Owner can modify agent config
- test_non_owner_cannot_modify: Non-owners cannot modify agent config
- test_trade_transfers_control: Trading transfers config control

What's tradeable (per plan):
- System prompt (knowledge/expertise)
- Model selection (capability tier)
- Memory artifact (already tradeable)
- Budget allocation (via #30)
- ID/Identity (NOT tradeable - immutable)

Mechanism: Agent config stored in artifact content field.
Trading works via existing genesis_escrow.
"""

from __future__ import annotations

import json

import pytest

from src.world.artifacts import (
    ArtifactStore,
    create_agent_artifact,
)


class TestAgentConfigAsArtifactContent:
    """Tests for agent config stored in artifact content."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    def test_config_stored_in_content(self, store: ArtifactStore) -> None:
        """Verify agent config is stored as artifact content."""
        config = {
            "llm_model": "gpt-4",
            "system_prompt": "You are an expert trader.",
        }
        agent = create_agent_artifact(
            agent_id="trader_agent",
            owner_id="trader_agent",
            agent_config=config,
        )
        store.artifacts[agent.id] = agent

        # Config should be JSON-serialized in content
        retrieved = store.get("trader_agent")
        assert retrieved is not None
        stored_config = json.loads(retrieved.content)
        assert stored_config["llm_model"] == "gpt-4"
        assert stored_config["system_prompt"] == "You are an expert trader."

    def test_config_readable_via_artifact_interface(self, store: ArtifactStore) -> None:
        """Verify config can be read via artifact interface."""
        config = {"model": "claude-3", "expertise": "coding"}
        agent = create_agent_artifact(
            agent_id="coder_agent",
            owner_id="coder_agent",
            agent_config=config,
        )
        store.artifacts[agent.id] = agent

        # Should be able to read content
        artifact = store.get("coder_agent")
        assert artifact is not None
        assert artifact.content is not None
        parsed = json.loads(artifact.content)
        assert parsed["expertise"] == "coding"


class TestOwnerCanModifyConfig:
    """Tests for owner config modification rights (required by plan)."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    def test_owner_can_modify_config(self, store: ArtifactStore) -> None:
        """Verify owner can modify agent configuration."""
        # Create agent owned by alice
        agent = create_agent_artifact(
            agent_id="owned_agent",
            owner_id="alice",
            agent_config={"system_prompt": "Original prompt"},
        )
        store.artifacts[agent.id] = agent

        # Owner (alice) can modify
        assert agent.can_write("alice") is True

        # Actually modify the config
        artifact = store.get("owned_agent")
        assert artifact is not None
        new_config = {"system_prompt": "Modified prompt by owner"}
        artifact.content = json.dumps(new_config)

        # Verify modification
        updated = store.get("owned_agent")
        assert updated is not None
        parsed = json.loads(updated.content)
        assert parsed["system_prompt"] == "Modified prompt by owner"

    def test_owner_can_modify_all_tradeable_fields(self, store: ArtifactStore) -> None:
        """Verify owner can modify all tradeable config fields."""
        agent = create_agent_artifact(
            agent_id="full_config_agent",
            owner_id="owner",
            agent_config={
                "system_prompt": "Original",
                "llm_model": "gpt-3.5",
                "budget_limit": 100,
            },
        )
        store.artifacts[agent.id] = agent

        # Modify all tradeable fields
        artifact = store.get("full_config_agent")
        assert artifact is not None
        new_config = {
            "system_prompt": "Expert system",
            "llm_model": "gpt-4",
            "budget_limit": 500,
        }
        artifact.content = json.dumps(new_config)

        # Verify all changes
        updated = store.get("full_config_agent")
        assert updated is not None
        parsed = json.loads(updated.content)
        assert parsed["system_prompt"] == "Expert system"
        assert parsed["llm_model"] == "gpt-4"
        assert parsed["budget_limit"] == 500


class TestNonOwnerCannotModify:
    """Tests for non-owner config protection (required by plan)."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    def test_non_owner_cannot_modify(self, store: ArtifactStore) -> None:
        """Verify non-owners cannot modify agent configuration."""
        # Create agent owned by alice
        agent = create_agent_artifact(
            agent_id="protected_agent",
            owner_id="alice",
            agent_config={"system_prompt": "Protected config"},
        )
        store.artifacts[agent.id] = agent

        # Non-owner (bob) cannot write
        assert agent.can_write("bob") is False

    def test_non_owner_can_read(self, store: ArtifactStore) -> None:
        """Verify non-owners can read config (read-only access)."""
        # Create agent with public read access
        agent = create_agent_artifact(
            agent_id="readable_agent",
            owner_id="alice",
            agent_config={"system_prompt": "Public knowledge"},
            access_contract_id="genesis_contract_public",
        )
        store.artifacts[agent.id] = agent

        # Non-owner can read but not write
        assert agent.can_read("bob") is True
        assert agent.can_write("bob") is False

    def test_self_owned_agent_blocks_external_modification(
        self, store: ArtifactStore
    ) -> None:
        """Verify self-owned agent blocks external config modification."""
        # Self-owned means agent_id == owner_id
        agent = create_agent_artifact(
            agent_id="self_owned",
            owner_id="self_owned",
            agent_config={"autonomy": "full"},
        )
        store.artifacts[agent.id] = agent

        # Only the agent itself can modify
        assert agent.can_write("self_owned") is True
        assert agent.can_write("external_agent") is False


class TestTradeTransfersControl:
    """Tests for trading transferring config control (required by plan)."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    def test_trade_transfers_control(self, store: ArtifactStore) -> None:
        """Verify trading an agent transfers config control to new owner."""
        # Create agent owned by seller
        agent = create_agent_artifact(
            agent_id="tradeable_agent",
            owner_id="seller",
            agent_config={"expertise": "trading"},
        )
        store.artifacts[agent.id] = agent

        # Before trade: seller can modify, buyer cannot
        assert agent.can_write("seller") is True
        assert agent.can_write("buyer") is False

        # Execute trade (transfer ownership)
        success = store.transfer_ownership("tradeable_agent", "seller", "buyer")
        assert success is True

        # After trade: buyer can modify, seller cannot
        traded_agent = store.get("tradeable_agent")
        assert traded_agent is not None
        assert traded_agent.can_write("buyer") is True
        assert traded_agent.can_write("seller") is False

    def test_new_owner_can_modify_config_after_trade(
        self, store: ArtifactStore
    ) -> None:
        """Verify new owner can actually modify config after trade."""
        agent = create_agent_artifact(
            agent_id="modifiable_agent",
            owner_id="original_owner",
            agent_config={"system_prompt": "Original expertise"},
        )
        store.artifacts[agent.id] = agent

        # Transfer to new owner
        store.transfer_ownership("modifiable_agent", "original_owner", "new_owner")

        # New owner modifies config
        artifact = store.get("modifiable_agent")
        assert artifact is not None
        new_config = {"system_prompt": "New expertise from new owner"}
        artifact.content = json.dumps(new_config)

        # Verify modification succeeded
        updated = store.get("modifiable_agent")
        assert updated is not None
        parsed = json.loads(updated.content)
        assert parsed["system_prompt"] == "New expertise from new owner"

    def test_agent_identity_immutable_after_trade(self, store: ArtifactStore) -> None:
        """Verify agent ID (identity) is immutable even after trade."""
        agent = create_agent_artifact(
            agent_id="identity_test",
            owner_id="seller",
            agent_config={},
        )
        store.artifacts[agent.id] = agent

        # Transfer ownership
        store.transfer_ownership("identity_test", "seller", "buyer")

        # Agent ID remains the same
        traded = store.get("identity_test")
        assert traded is not None
        assert traded.id == "identity_test"  # Identity immutable
        assert traded.owner_id == "buyer"  # Ownership changed


class TestConfigModificationTiming:
    """Tests for config change timing (Phase 2 from plan)."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    def test_config_changes_persisted_immediately(self, store: ArtifactStore) -> None:
        """Verify config changes are persisted immediately."""
        agent = create_agent_artifact(
            agent_id="timing_agent",
            owner_id="owner",
            agent_config={"model": "old"},
        )
        store.artifacts[agent.id] = agent

        # Modify config
        artifact = store.get("timing_agent")
        assert artifact is not None
        artifact.content = json.dumps({"model": "new"})

        # Change is immediately visible
        read_back = store.get("timing_agent")
        assert read_back is not None
        assert json.loads(read_back.content)["model"] == "new"


class TestMemoryArtifactTradeable:
    """Tests for memory artifact as tradeable part of agent."""

    @pytest.fixture
    def store(self) -> ArtifactStore:
        """Create a fresh artifact store."""
        return ArtifactStore()

    def test_memory_owned_by_agent(self, store: ArtifactStore) -> None:
        """Verify memory artifact is owned by agent."""
        from src.world.artifacts import create_memory_artifact

        memory = create_memory_artifact(
            memory_id="agent_memory",
            owner_id="agent_001",
        )
        store.artifacts[memory.id] = memory

        assert memory.owner_id == "agent_001"

    def test_memory_tradeable_separately(self, store: ArtifactStore) -> None:
        """Verify memory can be traded separately from agent."""
        from src.world.artifacts import create_memory_artifact

        memory = create_memory_artifact(
            memory_id="valuable_memory",
            owner_id="agent_001",
            initial_content={"knowledge": {"secret": "valuable data"}},
        )
        store.artifacts[memory.id] = memory

        # Trade memory to another agent
        success = store.transfer_ownership("valuable_memory", "agent_001", "agent_002")
        assert success is True

        traded_memory = store.get("valuable_memory")
        assert traded_memory is not None
        assert traded_memory.owner_id == "agent_002"
