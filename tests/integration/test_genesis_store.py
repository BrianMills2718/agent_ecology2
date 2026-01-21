"""Unit tests for genesis_store artifact discovery.

Tests the GenesisStore class that provides programmatic artifact discovery
for agents via invoke. This is Gap #16 implementation.

Test plan from docs/plans/16_artifact_discovery.md:
- test_list_returns_all_artifacts: Basic list works
- test_list_with_type_filter: Filter by type
- test_list_with_owner_filter: Filter by owner
- test_get_returns_artifact: Get single artifact
- test_get_missing_returns_error: Error on missing
- test_search_by_content: Search finds matches
- test_list_agents: Returns only agent artifacts
- test_list_principals: Returns artifacts with standing
- test_count_all: Count total artifacts
- test_count_filtered: Count with filter
- test_registered_in_genesis_artifacts: genesis_store exists
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import pytest

from src.world.artifacts import Artifact, ArtifactStore
from src.world.genesis import (
    GenesisStore,
    create_genesis_artifacts,
)
from src.world.ledger import Ledger
from src.config_schema import GenesisConfig, StoreConfig


def make_artifact(
    artifact_id: str,
    artifact_type: str,
    created_by: str,
    content: Any,
    has_standing: bool = False,
    can_execute: bool = False,
) -> Artifact:
    """Helper to create test artifacts with required fields."""
    now = datetime.utcnow().isoformat()
    return Artifact(
        id=artifact_id,
        type=artifact_type,
        created_by=created_by,
        content=content,
        created_at=now,
        updated_at=now,
        has_standing=has_standing,
        can_execute=can_execute,
    )


class TestGenesisStoreBasics:
    """Basic GenesisStore tests."""

    @pytest.fixture
    def artifact_store(self) -> ArtifactStore:
        """Create an ArtifactStore with some test artifacts."""
        store = ArtifactStore()

        # Add various test artifacts
        store.artifacts["agent_alice"] = make_artifact(
            artifact_id="agent_alice",
            artifact_type="agent",
            created_by="agent_alice",
            content={"name": "Alice"},
            has_standing=True,
            can_execute=True,
        )
        store.artifacts["agent_bob"] = make_artifact(
            artifact_id="agent_bob",
            artifact_type="agent",
            created_by="agent_bob",
            content={"name": "Bob"},
            has_standing=True,
            can_execute=True,
        )
        store.artifacts["data_weather"] = make_artifact(
            artifact_id="data_weather",
            artifact_type="data",
            created_by="agent_alice",
            content={"weather": "sunny", "temperature": 72},
            has_standing=False,
            can_execute=False,
        )
        store.artifacts["tool_calculator"] = make_artifact(
            artifact_id="tool_calculator",
            artifact_type="executable",
            created_by="agent_bob",
            content="def calculate(a, b): return a + b",
            has_standing=False,
            can_execute=True,
        )
        store.artifacts["contract_escrow_helper"] = make_artifact(
            artifact_id="contract_escrow_helper",
            artifact_type="contract",
            created_by="system",
            content={"type": "contract"},
            has_standing=True,  # Contract with standing (a principal)
            can_execute=False,
        )
        return store

    @pytest.fixture
    def genesis_store(self, artifact_store: ArtifactStore) -> GenesisStore:
        """Create a GenesisStore instance."""
        return GenesisStore(artifact_store=artifact_store)


class TestListReturnsAllArtifacts(TestGenesisStoreBasics):
    """Test that list returns all artifacts."""

    def test_list_returns_all_artifacts(
        self, genesis_store: GenesisStore, artifact_store: ArtifactStore
    ) -> None:
        """Verify list returns all artifacts in the store."""
        result = genesis_store._list([], "any_invoker")

        assert result["success"] is True
        assert "artifacts" in result
        artifacts = result["artifacts"]

        # Should have all 5 test artifacts
        assert len(artifacts) == 5

        # Check artifact IDs are present
        artifact_ids = [a["id"] for a in artifacts]
        assert "agent_alice" in artifact_ids
        assert "agent_bob" in artifact_ids
        assert "data_weather" in artifact_ids
        assert "tool_calculator" in artifact_ids
        assert "contract_escrow_helper" in artifact_ids


class TestListWithTypeFilter(TestGenesisStoreBasics):
    """Test filtering artifacts by type."""

    def test_list_with_type_filter(self, genesis_store: GenesisStore) -> None:
        """Verify list can filter by artifact type."""
        # Filter for agents only
        result = genesis_store._list([{"type": "agent"}], "invoker")

        assert result["success"] is True
        artifacts = result["artifacts"]

        # Should only have the 2 agent artifacts
        assert len(artifacts) == 2
        for artifact in artifacts:
            assert artifact["type"] == "agent"

    def test_list_by_type_method(self, genesis_store: GenesisStore) -> None:
        """Verify list_by_type method works."""
        result = genesis_store._list_by_type(["executable"], "invoker")

        assert result["success"] is True
        artifacts = result["artifacts"]

        # Should have 1 executable
        assert len(artifacts) == 1
        assert artifacts[0]["id"] == "tool_calculator"


class TestListWithOwnerFilter(TestGenesisStoreBasics):
    """Test filtering artifacts by owner."""

    def test_list_with_owner_filter(self, genesis_store: GenesisStore) -> None:
        """Verify list can filter by owner."""
        # Filter for Alice's artifacts
        result = genesis_store._list([{"owner": "agent_alice"}], "invoker")

        assert result["success"] is True
        artifacts = result["artifacts"]

        # Alice owns: agent_alice, data_weather
        assert len(artifacts) == 2
        for artifact in artifacts:
            assert artifact["created_by"] == "agent_alice"

    def test_list_by_owner_method(self, genesis_store: GenesisStore) -> None:
        """Verify list_by_owner method works."""
        result = genesis_store._list_by_owner(["agent_bob"], "invoker")

        assert result["success"] is True
        artifacts = result["artifacts"]

        # Bob owns: agent_bob, tool_calculator
        assert len(artifacts) == 2
        artifact_ids = [a["id"] for a in artifacts]
        assert "agent_bob" in artifact_ids
        assert "tool_calculator" in artifact_ids


class TestGetReturnsArtifact(TestGenesisStoreBasics):
    """Test getting a single artifact."""

    def test_get_returns_artifact(self, genesis_store: GenesisStore) -> None:
        """Verify get returns artifact details."""
        result = genesis_store._get(["agent_alice"], "invoker")

        assert result["success"] is True
        assert "artifact" in result
        artifact = result["artifact"]

        assert artifact["id"] == "agent_alice"
        assert artifact["type"] == "agent"
        assert artifact["created_by"] == "agent_alice"
        assert artifact["has_standing"] is True
        assert artifact["can_execute"] is True

    def test_get_returns_content(self, genesis_store: GenesisStore) -> None:
        """Verify get includes artifact content."""
        result = genesis_store._get(["data_weather"], "invoker")

        assert result["success"] is True
        artifact = result["artifact"]
        assert artifact["content"] == {"weather": "sunny", "temperature": 72}


class TestGetMissingReturnsError(TestGenesisStoreBasics):
    """Test error handling for missing artifacts."""

    def test_get_missing_returns_error(self, genesis_store: GenesisStore) -> None:
        """Verify get returns error for non-existent artifact."""
        result = genesis_store._get(["nonexistent_artifact"], "invoker")

        assert result["success"] is False
        assert "error" in result
        assert "not found" in result["error"].lower()

    def test_get_empty_args_returns_error(self, genesis_store: GenesisStore) -> None:
        """Verify get returns error when no artifact_id provided."""
        result = genesis_store._get([], "invoker")

        assert result["success"] is False
        assert "error" in result


class TestSearchByContent(TestGenesisStoreBasics):
    """Test searching artifacts by content."""

    def test_search_by_content(self, genesis_store: GenesisStore) -> None:
        """Verify search finds artifacts by content match."""
        # Search for "calculator" in content
        result = genesis_store._search(["calculate"], "invoker")

        assert result["success"] is True
        artifacts = result["artifacts"]

        # Should find the calculator tool
        assert len(artifacts) >= 1
        artifact_ids = [a["id"] for a in artifacts]
        assert "tool_calculator" in artifact_ids

    def test_search_returns_empty_on_no_match(self, genesis_store: GenesisStore) -> None:
        """Verify search returns empty list when no matches."""
        result = genesis_store._search(["nonexistent_content_xyz"], "invoker")

        assert result["success"] is True
        assert result["artifacts"] == []

    def test_search_with_limit(self, genesis_store: GenesisStore) -> None:
        """Verify search respects limit parameter."""
        # Search with limit=1
        result = genesis_store._search(["a", None, 1], "invoker")

        assert result["success"] is True
        assert len(result["artifacts"]) <= 1


class TestListAgents(TestGenesisStoreBasics):
    """Test listing agent artifacts specifically."""

    def test_list_agents(self, genesis_store: GenesisStore) -> None:
        """Verify list_agents returns only agent artifacts."""
        result = genesis_store._list_agents([], "invoker")

        assert result["success"] is True
        artifacts = result["artifacts"]

        # Should only have agents (has_standing=True AND can_execute=True)
        assert len(artifacts) == 2
        for artifact in artifacts:
            assert artifact["has_standing"] is True
            assert artifact["can_execute"] is True


class TestListPrincipals(TestGenesisStoreBasics):
    """Test listing principal artifacts (artifacts with standing)."""

    def test_list_principals(self, genesis_store: GenesisStore) -> None:
        """Verify list_principals returns artifacts with has_standing=True."""
        result = genesis_store._list_principals([], "invoker")

        assert result["success"] is True
        artifacts = result["artifacts"]

        # Should have agents + contracts with standing
        # agent_alice, agent_bob, contract_escrow_helper
        assert len(artifacts) == 3
        for artifact in artifacts:
            assert artifact["has_standing"] is True


class TestCountAll(TestGenesisStoreBasics):
    """Test counting all artifacts."""

    def test_count_all(self, genesis_store: GenesisStore) -> None:
        """Verify count returns total artifact count."""
        result = genesis_store._count([], "invoker")

        assert result["success"] is True
        assert result["count"] == 5


class TestCountFiltered(TestGenesisStoreBasics):
    """Test counting with filters."""

    def test_count_filtered(self, genesis_store: GenesisStore) -> None:
        """Verify count respects filters."""
        # Count only agents
        result = genesis_store._count([{"type": "agent"}], "invoker")

        assert result["success"] is True
        assert result["count"] == 2

    def test_count_by_owner(self, genesis_store: GenesisStore) -> None:
        """Verify count can filter by owner."""
        result = genesis_store._count([{"owner": "agent_alice"}], "invoker")

        assert result["success"] is True
        assert result["count"] == 2  # agent_alice, data_weather


class TestRegisteredInGenesisArtifacts:
    """Test that genesis_store is properly registered."""

    def test_registered_in_genesis_artifacts(self) -> None:
        """Verify genesis_store is created by create_genesis_artifacts."""
        from src.world.artifacts import ArtifactStore
        from src.world.ledger import Ledger
        from src.world.logger import EventLogger

        ledger = Ledger()
        artifact_store = ArtifactStore()
        logger = EventLogger()

        def mint_callback(agent_id: str, amount: int) -> None:
            ledger.credit_scrip(agent_id, amount)

        artifacts = create_genesis_artifacts(
            ledger=ledger,
            mint_callback=mint_callback,
            artifact_store=artifact_store,
            logger=logger,
            rights_config={"default_quotas": {"llm_tokens": 100.0, "disk": 10000.0}}
        )

        # genesis_store should be in the created artifacts
        assert "genesis_store" in artifacts

        # Verify it's a GenesisStore
        genesis_store = artifacts["genesis_store"]
        assert isinstance(genesis_store, GenesisStore)

    def test_store_disabled_when_config_false(self) -> None:
        """Verify genesis_store not created when disabled in config."""
        from src.world.artifacts import ArtifactStore
        from src.world.ledger import Ledger
        from src.world.logger import EventLogger
        from src.config_schema import (
            GenesisConfig,
            GenesisArtifactsEnabled,
            ArtifactEnabledConfig
        )

        ledger = Ledger()
        artifact_store = ArtifactStore()
        logger = EventLogger()

        def mint_callback(agent_id: str, amount: int) -> None:
            pass

        # Create config with store disabled
        disabled_store = ArtifactEnabledConfig(enabled=False)
        artifacts_enabled = GenesisArtifactsEnabled(store=disabled_store)
        config = GenesisConfig(artifacts=artifacts_enabled)

        artifacts = create_genesis_artifacts(
            ledger=ledger,
            mint_callback=mint_callback,
            artifact_store=artifact_store,
            logger=logger,
            rights_config={"default_quotas": {"llm_tokens": 100.0, "disk": 10000.0}},
            genesis_config=config
        )

        # genesis_store should NOT be in the created artifacts
        assert "genesis_store" not in artifacts


class TestMethodCosts:
    """Test that all methods have zero cost (discovery is free)."""

    @pytest.fixture
    def genesis_store(self) -> GenesisStore:
        """Create a GenesisStore instance."""
        return GenesisStore(artifact_store=ArtifactStore())

    def test_all_methods_cost_zero(self, genesis_store: GenesisStore) -> None:
        """Verify all discovery methods have zero cost."""
        methods = genesis_store.list_methods()

        for method in methods:
            assert method["cost"] == 0, f"Method {method['name']} should cost 0"


class TestMethodRegistration:
    """Test method registration follows genesis artifact pattern."""

    @pytest.fixture
    def genesis_store(self) -> GenesisStore:
        """Create a GenesisStore instance."""
        return GenesisStore(artifact_store=ArtifactStore())

    def test_has_required_methods(self, genesis_store: GenesisStore) -> None:
        """Verify all required methods are registered."""
        methods = genesis_store.list_methods()
        method_names = [m["name"] for m in methods]

        required = [
            "list",
            "get",
            "search",
            "list_by_type",
            "list_by_owner",
            "list_agents",
            "list_principals",
            "count",
        ]

        for name in required:
            assert name in method_names, f"Method {name} should be registered"

    def test_artifact_id(self, genesis_store: GenesisStore) -> None:
        """Verify genesis_store has correct ID."""
        assert genesis_store.id == "genesis_store"

    def test_artifact_type(self, genesis_store: GenesisStore) -> None:
        """Verify genesis_store has genesis type."""
        assert genesis_store.type == "genesis"

    def test_owner_is_system(self, genesis_store: GenesisStore) -> None:
        """Verify genesis_store is owned by system."""
        assert genesis_store.created_by == "system"


class TestPaginationSupport:
    """Test pagination with limit/offset."""

    @pytest.fixture
    def large_store(self) -> ArtifactStore:
        """Create a store with many artifacts."""
        store = ArtifactStore()
        for i in range(20):
            store.artifacts[f"data_{i:02d}"] = make_artifact(
                artifact_id=f"data_{i:02d}",
                artifact_type="data",
                created_by="owner",
                content=f"data {i}",
            )
        return store

    @pytest.fixture
    def genesis_store(self, large_store: ArtifactStore) -> GenesisStore:
        """Create a GenesisStore instance."""
        return GenesisStore(artifact_store=large_store)

    def test_list_with_limit(self, genesis_store: GenesisStore) -> None:
        """Verify list respects limit parameter."""
        result = genesis_store._list([{"limit": 5}], "invoker")

        assert result["success"] is True
        assert len(result["artifacts"]) == 5

    def test_list_with_offset(self, genesis_store: GenesisStore) -> None:
        """Verify list respects offset parameter."""
        # Get first 5
        result1 = genesis_store._list([{"limit": 5, "offset": 0}], "invoker")
        # Get next 5
        result2 = genesis_store._list([{"limit": 5, "offset": 5}], "invoker")

        assert result1["success"] is True
        assert result2["success"] is True

        # Should be different sets
        ids1 = {a["id"] for a in result1["artifacts"]}
        ids2 = {a["id"] for a in result2["artifacts"]}
        assert ids1.isdisjoint(ids2)
