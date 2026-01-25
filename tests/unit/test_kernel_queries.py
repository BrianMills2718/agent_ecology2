"""Tests for Plan #184: Query Kernel Action.

Tests that agents can query kernel state directly via query_kernel action.
"""

import pytest
from typing import Any

from src.world.kernel_queries import KernelQueryHandler, QUERY_SCHEMA
from src.world.artifacts import ArtifactStore


class TestQuerySchema:
    """Test query schema validation."""

    def test_all_query_types_have_schema(self) -> None:
        """Every query type must have schema defined."""
        expected_types = [
            "artifacts", "artifact", "principals", "principal",
            "balances", "resources", "quotas", "mint", "events",
            "invocations", "frozen", "libraries", "dependencies",
        ]
        for qt in expected_types:
            assert qt in QUERY_SCHEMA, f"Missing schema for query type: {qt}"

    def test_schema_has_required_fields(self) -> None:
        """Each schema must have params and required lists."""
        for qt, schema in QUERY_SCHEMA.items():
            assert "params" in schema, f"{qt} schema missing 'params'"
            assert "required" in schema, f"{qt} schema missing 'required'"
            assert isinstance(schema["params"], list)
            assert isinstance(schema["required"], list)


class TestKernelQueryHandler:
    """Test KernelQueryHandler directly."""

    @pytest.fixture
    def mock_world(self) -> Any:
        """Create a minimal mock world for testing."""
        class MockLedger:
            scrip = {"alice": 100, "bob": 50}
            def get_scrip(self, pid: str) -> int:
                return self.scrip.get(pid, 0)

        class MockLogger:
            def read_recent(self, n: int) -> list[dict[str, Any]]:
                return [{"event_type": "test", "data": i} for i in range(min(n, 3))]

        class MockWorld:
            def __init__(self) -> None:
                self.artifacts = ArtifactStore()
                self.ledger = MockLedger()
                self.logger = MockLogger()
                self.rights_registry = None
                self.resource_manager = None
                self.invocation_registry = None
                self.mint_auction = None
                self._frozen_agents: set[str] = set()
                self._installed_libraries: dict[str, list[tuple[str, str | None]]] = {}

            def is_agent_frozen(self, agent_id: str) -> bool:
                return agent_id in self._frozen_agents

            def get_frozen_agents(self) -> list[str]:
                return list(self._frozen_agents)

            def get_installed_libraries(self, pid: str) -> list[tuple[str, str | None]]:
                return self._installed_libraries.get(pid, [])

        return MockWorld()

    @pytest.fixture
    def handler(self, mock_world: Any) -> KernelQueryHandler:
        """Create handler with mock world."""
        return KernelQueryHandler(mock_world)

    def test_unknown_query_type(self, handler: KernelQueryHandler) -> None:
        """Unknown query types return error."""
        result = handler.execute("invalid_query", {})
        assert result["success"] is False
        assert "Unknown query_type" in result["error"]
        assert "valid types" in result["error"].lower()

    def test_unknown_param(self, handler: KernelQueryHandler) -> None:
        """Unknown params return error."""
        result = handler.execute("artifacts", {"invalid_param": "value"})
        assert result["success"] is False
        assert "Unknown param" in result["error"]

    def test_missing_required_param(self, handler: KernelQueryHandler) -> None:
        """Missing required params return error."""
        result = handler.execute("artifact", {})  # artifact_id required
        assert result["success"] is False
        assert "requires" in result["error"]
        assert "artifact_id" in result["error"]


class TestArtifactsQuery:
    """Test artifacts query type."""

    @pytest.fixture
    def mock_world(self) -> Any:
        """Create mock world with artifacts."""
        class MockLedger:
            scrip = {"alice": 100}
            def get_scrip(self, pid: str) -> int:
                return self.scrip.get(pid, 0)

        class MockWorld:
            def __init__(self) -> None:
                self.artifacts = ArtifactStore()
                self.ledger = MockLedger()
                # Add some artifacts
                self.artifacts.write(
                    artifact_id="tool_1",
                    type="executable",
                    content="A tool",
                    created_by="alice",
                    executable=True,
                )
                self.artifacts.write(
                    artifact_id="data_1",
                    type="data",
                    content="Some data",
                    created_by="bob",
                )
                self.artifacts.write(
                    artifact_id="tool_2",
                    type="executable",
                    content="Another tool",
                    created_by="alice",
                    executable=True,
                )

        return MockWorld()

    @pytest.fixture
    def handler(self, mock_world: Any) -> KernelQueryHandler:
        return KernelQueryHandler(mock_world)

    def test_query_all_artifacts(self, handler: KernelQueryHandler) -> None:
        """Can query all artifacts."""
        result = handler.execute("artifacts", {})
        assert result["success"] is True
        assert result["total"] == 3
        assert result["returned"] == 3

    def test_filter_by_owner(self, handler: KernelQueryHandler) -> None:
        """Can filter artifacts by owner."""
        result = handler.execute("artifacts", {"owner": "alice"})
        assert result["success"] is True
        assert result["total"] == 2
        assert all(a["created_by"] == "alice" for a in result["results"])

    def test_filter_by_type(self, handler: KernelQueryHandler) -> None:
        """Can filter artifacts by type."""
        result = handler.execute("artifacts", {"type": "executable"})
        assert result["success"] is True
        assert result["total"] == 2
        assert all(a["type"] == "executable" for a in result["results"])

    def test_filter_by_executable(self, handler: KernelQueryHandler) -> None:
        """Can filter artifacts by executable flag."""
        result = handler.execute("artifacts", {"executable": True})
        assert result["success"] is True
        assert result["total"] == 2
        assert all(a["executable"] is True for a in result["results"])

    def test_filter_by_name_pattern(self, handler: KernelQueryHandler) -> None:
        """Can filter artifacts by name pattern regex."""
        result = handler.execute("artifacts", {"name_pattern": "^tool"})
        assert result["success"] is True
        assert result["total"] == 2
        assert all(a["id"].startswith("tool") for a in result["results"])

    def test_pagination_limit(self, handler: KernelQueryHandler) -> None:
        """Limit param restricts results."""
        result = handler.execute("artifacts", {"limit": 1})
        assert result["success"] is True
        assert result["total"] == 3
        assert result["returned"] == 1

    def test_pagination_offset(self, handler: KernelQueryHandler) -> None:
        """Offset param skips results."""
        result = handler.execute("artifacts", {"offset": 2})
        assert result["success"] is True
        assert result["total"] == 3
        assert result["returned"] == 1


class TestBalancesQuery:
    """Test balances query type."""

    @pytest.fixture
    def mock_world(self) -> Any:
        class MockLedger:
            scrip = {"alice": 100, "bob": 50, "charlie": 25}
            def get_scrip(self, pid: str) -> int:
                return self.scrip.get(pid, 0)

        class MockWorld:
            def __init__(self) -> None:
                self.ledger = MockLedger()
                self.artifacts = ArtifactStore()

        return MockWorld()

    @pytest.fixture
    def handler(self, mock_world: Any) -> KernelQueryHandler:
        return KernelQueryHandler(mock_world)

    def test_query_all_balances(self, handler: KernelQueryHandler) -> None:
        """Can query all balances."""
        result = handler.execute("balances", {})
        assert result["success"] is True
        assert "balances" in result
        assert result["balances"]["alice"] == 100
        assert result["balances"]["bob"] == 50

    def test_query_single_balance(self, handler: KernelQueryHandler) -> None:
        """Can query single principal's balance."""
        result = handler.execute("balances", {"principal_id": "alice"})
        assert result["success"] is True
        assert result["scrip"] == 100

    def test_query_nonexistent_balance(self, handler: KernelQueryHandler) -> None:
        """Querying nonexistent principal returns error."""
        result = handler.execute("balances", {"principal_id": "nobody"})
        assert result["success"] is False
        assert "not found" in result["error"].lower()


class TestPrincipalsQuery:
    """Test principals query type."""

    @pytest.fixture
    def mock_world(self) -> Any:
        class MockLedger:
            scrip = {"alice": 100, "bob": 50}
            def get_scrip(self, pid: str) -> int:
                return self.scrip.get(pid, 0)

        class MockWorld:
            def __init__(self) -> None:
                self.ledger = MockLedger()
                self.artifacts = ArtifactStore()

        return MockWorld()

    @pytest.fixture
    def handler(self, mock_world: Any) -> KernelQueryHandler:
        return KernelQueryHandler(mock_world)

    def test_query_principals(self, handler: KernelQueryHandler) -> None:
        """Can list all principals."""
        result = handler.execute("principals", {})
        assert result["success"] is True
        assert result["total"] == 2
        assert "alice" in result["results"]
        assert "bob" in result["results"]

    def test_query_principal_exists(self, handler: KernelQueryHandler) -> None:
        """Can check if principal exists."""
        result = handler.execute("principal", {"principal_id": "alice"})
        assert result["success"] is True
        assert result["exists"] is True
        assert result["scrip"] == 100

    def test_query_principal_not_exists(self, handler: KernelQueryHandler) -> None:
        """Can check if principal doesn't exist."""
        result = handler.execute("principal", {"principal_id": "nobody"})
        assert result["success"] is True
        assert result["exists"] is False


class TestEventsQuery:
    """Test events query type."""

    @pytest.fixture
    def mock_world(self) -> Any:
        class MockLogger:
            def read_recent(self, n: int) -> list[dict[str, Any]]:
                return [{"event_type": "test", "i": i} for i in range(min(n, 5))]

        class MockWorld:
            def __init__(self) -> None:
                self.logger = MockLogger()
                self.artifacts = ArtifactStore()
                self.ledger = type("MockLedger", (), {"scrip": {}})()

        return MockWorld()

    @pytest.fixture
    def handler(self, mock_world: Any) -> KernelQueryHandler:
        return KernelQueryHandler(mock_world)

    def test_query_events(self, handler: KernelQueryHandler) -> None:
        """Can query recent events."""
        result = handler.execute("events", {"limit": 3})
        assert result["success"] is True
        assert result["returned"] == 3
        assert len(result["events"]) == 3


class TestFrozenQuery:
    """Test frozen query type."""

    @pytest.fixture
    def mock_world(self) -> Any:
        class MockWorld:
            def __init__(self) -> None:
                self._frozen = {"alice"}
                self.artifacts = ArtifactStore()
                self.ledger = type("MockLedger", (), {"scrip": {}})()

            def is_agent_frozen(self, agent_id: str) -> bool:
                return agent_id in self._frozen

            def get_frozen_agents(self) -> list[str]:
                return list(self._frozen)

        return MockWorld()

    @pytest.fixture
    def handler(self, mock_world: Any) -> KernelQueryHandler:
        return KernelQueryHandler(mock_world)

    def test_query_all_frozen(self, handler: KernelQueryHandler) -> None:
        """Can query all frozen agents."""
        result = handler.execute("frozen", {})
        assert result["success"] is True
        assert "alice" in result["frozen_agents"]

    def test_query_single_frozen(self, handler: KernelQueryHandler) -> None:
        """Can check if specific agent is frozen."""
        result = handler.execute("frozen", {"agent_id": "alice"})
        assert result["success"] is True
        assert result["frozen"] is True

        result = handler.execute("frozen", {"agent_id": "bob"})
        assert result["success"] is True
        assert result["frozen"] is False
