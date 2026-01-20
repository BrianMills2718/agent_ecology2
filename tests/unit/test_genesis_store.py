"""Tests for GenesisStore interface discovery (Plan #114)."""

import pytest

from src.world.artifacts import Artifact, ArtifactStore
from src.world.genesis.store import GenesisStore


@pytest.fixture
def artifact_store() -> ArtifactStore:
    """Create a fresh artifact store."""
    return ArtifactStore()


@pytest.fixture
def genesis_store(artifact_store: ArtifactStore) -> GenesisStore:
    """Create genesis store with artifact store."""
    return GenesisStore(artifact_store=artifact_store)


@pytest.fixture
def artifact_with_interface(artifact_store: ArtifactStore) -> Artifact:
    """Create an artifact with a defined interface."""
    interface = {
        "description": "Calculator service",
        "dataType": "service",
        "methods": [
            {
                "name": "add",
                "description": "Add two numbers",
                "inputSchema": {"a": "number", "b": "number"},
                "outputSchema": {"type": "number"},
            }
        ],
        "examples": [{"input": {"a": 1, "b": 2}, "output": 3}],
    }
    artifact = artifact_store.write(
        artifact_id="test_calculator",
        type="executable",
        content="Calculator artifact",
        created_by="alice",
        executable=True,
        code="def run(*args): return args[0] + args[1]",
    )
    # Set interface directly on artifact (Plan #14 stores interface on Artifact dataclass)
    artifact.interface = interface
    return artifact


@pytest.fixture
def artifact_without_interface(artifact_store: ArtifactStore) -> Artifact:
    """Create an artifact without an interface."""
    artifact_store.write(
        artifact_id="test_data",
        type="data",
        content="Some data content",
        created_by="bob",
        executable=False,
    )
    return artifact_store.get("test_data")


def call_method(store: GenesisStore, method_name: str, args: list, invoker: str) -> dict:
    """Helper to call a method on genesis store."""
    method = store.get_method(method_name)
    assert method is not None, f"Method {method_name} not found"
    return method.handler(args, invoker)


class TestInterfaceInGetResponse:
    """Test that get() returns interface field (Plan #114 Phase 1)."""

    def test_get_returns_interface(
        self,
        genesis_store: GenesisStore,
        artifact_with_interface: Artifact,
    ) -> None:
        """get() includes interface field in response."""
        result = call_method(genesis_store, "get", ["test_calculator"], "alice")

        assert result["success"] is True
        assert "artifact" in result
        assert "interface" in result["artifact"]
        assert result["artifact"]["interface"] is not None
        assert result["artifact"]["interface"]["description"] == "Calculator service"
        assert result["artifact"]["interface"]["dataType"] == "service"

    def test_get_returns_null_interface_when_not_set(
        self,
        genesis_store: GenesisStore,
        artifact_without_interface: Artifact,
    ) -> None:
        """get() returns None for interface when artifact has no interface."""
        result = call_method(genesis_store, "get", ["test_data"], "bob")

        assert result["success"] is True
        assert "artifact" in result
        assert "interface" in result["artifact"]
        assert result["artifact"]["interface"] is None


class TestInterfaceInListResponse:
    """Test that list() returns interface fields (Plan #114 Phase 1)."""

    def test_list_returns_interfaces(
        self,
        genesis_store: GenesisStore,
        artifact_with_interface: Artifact,
        artifact_without_interface: Artifact,
    ) -> None:
        """list() includes interface field for all artifacts."""
        result = call_method(genesis_store, "list", [], "alice")

        assert result["success"] is True
        assert result["count"] >= 2

        # Find artifacts by ID
        artifacts_by_id = {a["id"]: a for a in result["artifacts"]}

        assert "test_calculator" in artifacts_by_id
        assert "interface" in artifacts_by_id["test_calculator"]
        assert artifacts_by_id["test_calculator"]["interface"] is not None

        assert "test_data" in artifacts_by_id
        assert "interface" in artifacts_by_id["test_data"]
        assert artifacts_by_id["test_data"]["interface"] is None


class TestGetInterfaceMethod:
    """Test dedicated get_interface() method (Plan #114 Phase 2)."""

    def test_get_interface_returns_interface(
        self,
        genesis_store: GenesisStore,
        artifact_with_interface: Artifact,
    ) -> None:
        """get_interface() returns full interface schema."""
        result = call_method(genesis_store, "get_interface", ["test_calculator"], "alice")

        assert result["success"] is True
        assert result["artifact_id"] == "test_calculator"
        assert result["executable"] is True
        assert result["interface"] is not None
        assert result["interface"]["description"] == "Calculator service"
        assert "methods" in result["interface"]
        assert len(result["interface"]["methods"]) == 1
        assert result["interface"]["methods"][0]["name"] == "add"

    def test_get_interface_null_interface(
        self,
        genesis_store: GenesisStore,
        artifact_without_interface: Artifact,
    ) -> None:
        """get_interface() works when artifact has no interface."""
        result = call_method(genesis_store, "get_interface", ["test_data"], "bob")

        assert result["success"] is True
        assert result["artifact_id"] == "test_data"
        assert result["executable"] is False
        assert result["interface"] is None

    def test_get_interface_not_found(
        self,
        genesis_store: GenesisStore,
    ) -> None:
        """get_interface() returns error for missing artifact."""
        result = call_method(genesis_store, "get_interface", ["nonexistent"], "alice")

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    def test_get_interface_no_args(
        self,
        genesis_store: GenesisStore,
    ) -> None:
        """get_interface() returns error when no artifact_id provided."""
        result = call_method(genesis_store, "get_interface", [], "alice")

        assert result["success"] is False
        assert "requires" in result["error"].lower()


class TestSearchIncludesInterface:
    """Test that search() returns interface fields."""

    def test_search_returns_interfaces(
        self,
        genesis_store: GenesisStore,
        artifact_with_interface: Artifact,
    ) -> None:
        """search() includes interface field in results."""
        result = call_method(genesis_store, "search", ["calculator"], "alice")

        assert result["success"] is True
        assert len(result["artifacts"]) >= 1

        found = result["artifacts"][0]
        assert "interface" in found
        assert found["interface"] is not None
