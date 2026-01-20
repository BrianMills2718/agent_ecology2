"""Tests for Plan #113: Contractable Model Access.

Tests for GenesisModelRegistry - manages model access as tradeable resource.

Tests cover:
- Model configuration
- Quota allocation
- Quota consumption tracking
- Quota exhaustion behavior
- Quota transfer (including caller verification)
- Fallback model selection
"""

from __future__ import annotations

import pytest

from src.world.genesis.model_registry import GenesisModelRegistry


class TestModelConfiguration:
    """Tests for model setup and configuration."""

    def test_configure_model_basic(self) -> None:
        """Models can be configured with properties."""
        registry = GenesisModelRegistry()
        registry.configure_model(
            model_id="gemini-2.5-flash",
            global_limit=50000,
            cost_per_1k_input=0.002,
            cost_per_1k_output=0.006,
            properties=["fast", "cheap"]
        )

        result = registry._list_models([], "alice")
        assert result["success"] is True
        assert len(result["models"]) == 1
        model = result["models"][0]
        assert model["model_id"] == "gemini-2.5-flash"
        assert model["global_limit"] == 50000
        assert model["properties"] == ["fast", "cheap"]

    def test_configure_multiple_models(self) -> None:
        """Multiple models can be configured."""
        registry = GenesisModelRegistry()
        registry.configure_model("gemini-2.5-flash", global_limit=50000)
        registry.configure_model("gemini-3-flash", global_limit=10000)
        registry.configure_model("claude-haiku", global_limit=100000)

        result = registry._list_models([], "alice")
        assert result["count"] == 3

    def test_list_models_shows_availability(self) -> None:
        """list_models shows global availability after allocations."""
        registry = GenesisModelRegistry()
        registry.configure_model("gemini-2.5-flash", global_limit=50000)
        registry.allocate_initial_quota("alice", "gemini-2.5-flash", 10000)

        result = registry._list_models([], "bob")
        model = result["models"][0]
        assert model["allocated"] == 10000
        assert model["available"] == 40000


class TestQuotaAllocation:
    """Tests for initial quota allocation."""

    @pytest.fixture
    def registry(self) -> GenesisModelRegistry:
        """Create registry with sample models."""
        reg = GenesisModelRegistry()
        reg.configure_model(
            model_id="gemini/gemini-2.5-flash",
            global_limit=50000,
            cost_per_1k_input=0.002,
            cost_per_1k_output=0.006,
            properties=["fast", "cheap"],
        )
        reg.configure_model(
            model_id="gemini/gemini-3-flash",
            global_limit=10000,
            cost_per_1k_input=0.001,
            cost_per_1k_output=0.003,
            properties=["experimental"],
        )
        return reg

    def test_quota_allocation(self, registry: GenesisModelRegistry) -> None:
        """Agents receive initial quotas via allocate_initial_quota."""
        # Allocate 20% of global limits
        registry.allocate_initial_quota("agent_001", "gemini/gemini-2.5-flash", 10000)
        registry.allocate_initial_quota("agent_001", "gemini/gemini-3-flash", 2000)

        result1 = registry._get_quota(["agent_001", "gemini/gemini-2.5-flash"], "agent_001")
        result2 = registry._get_quota(["agent_001", "gemini/gemini-3-flash"], "agent_001")

        assert result1["quota"] == 10000
        assert result2["quota"] == 2000

    def test_allocate_quota_unknown_model_fails(self, registry: GenesisModelRegistry) -> None:
        """Allocating quota for unknown model fails."""
        success = registry.allocate_initial_quota("alice", "unknown-model", 10000)
        assert success is False

    def test_request_access_allocates_from_global_pool(self, registry: GenesisModelRegistry) -> None:
        """Agents can request additional quota from global pool."""
        result = registry._request_access(
            ["alice", "gemini/gemini-2.5-flash", 5000],
            "alice"
        )
        assert result["success"] is True
        assert result["allocated"] == 5000

    def test_request_access_checks_invoker(self, registry: GenesisModelRegistry) -> None:
        """Cannot request quota for another agent."""
        result = registry._request_access(
            ["bob", "gemini/gemini-2.5-flash", 5000],
            "alice"  # Alice trying to request for Bob
        )
        assert result["success"] is False
        assert result.get("code") == "not_authorized"

    def test_request_access_respects_global_limit(self, registry: GenesisModelRegistry) -> None:
        """Cannot request more than available global quota."""
        registry.allocate_initial_quota("bob", "gemini/gemini-2.5-flash", 40000)

        # Alice tries to request more than remaining 10000
        result = registry._request_access(
            ["alice", "gemini/gemini-2.5-flash", 15000],
            "alice"
        )
        assert result["success"] is False
        assert result["details"]["available"] == 10000


class TestQuotaConsumption:
    """Tests for consuming quota."""

    @pytest.fixture
    def registry(self) -> GenesisModelRegistry:
        """Create registry with allocated quota."""
        reg = GenesisModelRegistry()
        reg.configure_model("gemini/gemini-2.5-flash", global_limit=50000)
        reg.allocate_initial_quota("agent_001", "gemini/gemini-2.5-flash", 10000)
        return reg

    def test_quota_consumption(self, registry: GenesisModelRegistry) -> None:
        """Usage is deducted from agent's quota."""
        # Consume some quota
        result = registry._consume(
            ["agent_001", "gemini/gemini-2.5-flash", 1000],
            "system"
        )

        assert result["success"] is True
        assert result["remaining"] == 9000

        # Verify via get_quota
        quota_result = registry._get_quota(
            ["agent_001", "gemini/gemini-2.5-flash"],
            "agent_001"
        )
        assert quota_result["used"] == 1000
        assert quota_result["available"] == 9000

    def test_consume_tracks_usage_cumulatively(self, registry: GenesisModelRegistry) -> None:
        """Multiple consumptions track cumulative usage."""
        registry._consume(["agent_001", "gemini/gemini-2.5-flash", 1000], "system")
        registry._consume(["agent_001", "gemini/gemini-2.5-flash", 500], "system")

        result = registry._get_quota(["agent_001", "gemini/gemini-2.5-flash"], "agent_001")
        assert result["used"] == 1500
        assert result["available"] == 8500


class TestQuotaExhaustion:
    """Tests for quota exhaustion behavior."""

    @pytest.fixture
    def registry(self) -> GenesisModelRegistry:
        """Create registry with limited quota."""
        reg = GenesisModelRegistry()
        reg.configure_model("gemini/gemini-2.5-flash", global_limit=50000)
        reg.allocate_initial_quota("agent_001", "gemini/gemini-2.5-flash", 1000)
        return reg

    def test_quota_exhaustion(self, registry: GenesisModelRegistry) -> None:
        """Error when trying to consume more than available."""
        # Exhaust the quota
        registry._consume(["agent_001", "gemini/gemini-2.5-flash", 1000], "system")

        # Now has_capacity should return False
        assert not registry.has_capacity("agent_001", "gemini/gemini-2.5-flash", 1)

        # And consume should fail
        result = registry._consume(
            ["agent_001", "gemini/gemini-2.5-flash", 1],
            "system"
        )
        assert result["success"] is False
        assert result.get("code") == "insufficient_funds"

    def test_has_capacity_checks_remaining(self, registry: GenesisModelRegistry) -> None:
        """has_capacity correctly checks remaining quota."""
        assert registry.has_capacity("agent_001", "gemini/gemini-2.5-flash", 500) is True
        assert registry.has_capacity("agent_001", "gemini/gemini-2.5-flash", 1000) is True
        assert registry.has_capacity("agent_001", "gemini/gemini-2.5-flash", 1001) is False


class TestQuotaTransfer:
    """Tests for quota transfers between agents."""

    @pytest.fixture
    def registry(self) -> GenesisModelRegistry:
        """Create registry with two agents having quota."""
        reg = GenesisModelRegistry()
        reg.configure_model("gemini/gemini-2.5-flash", global_limit=50000)
        reg.allocate_initial_quota("agent_001", "gemini/gemini-2.5-flash", 10000)
        reg.allocate_initial_quota("agent_002", "gemini/gemini-2.5-flash", 10000)
        return reg

    def test_quota_transfer(self, registry: GenesisModelRegistry) -> None:
        """Agents can transfer quota to each other."""
        # Transfer 5000 from agent_001 to agent_002
        result = registry._transfer_quota(
            ["agent_002", "gemini/gemini-2.5-flash", 5000],
            "agent_001"  # agent_001 is invoker (sender)
        )

        assert result["success"] is True
        assert result["from_quota_after"] == 5000
        assert result["to_quota_after"] == 15000

    def test_transfer_creates_recipient_quota(self, registry: GenesisModelRegistry) -> None:
        """Transfer creates quota entry for recipient if none exists."""
        # Transfer to new agent
        result = registry._transfer_quota(
            ["agent_003", "gemini/gemini-2.5-flash", 3000],
            "agent_001"
        )
        assert result["success"] is True

        quota = registry._get_quota(["agent_003", "gemini/gemini-2.5-flash"], "agent_003")
        assert quota["quota"] == 3000

    def test_cannot_transfer_used_quota(self, registry: GenesisModelRegistry) -> None:
        """Cannot transfer quota that has been consumed."""
        # Consume 8000, leaving only 2000 transferable
        registry._consume(["agent_001", "gemini/gemini-2.5-flash", 8000], "system")

        # Try to transfer more than available
        result = registry._transfer_quota(
            ["agent_002", "gemini/gemini-2.5-flash", 5000],
            "agent_001"
        )
        assert result["success"] is False
        assert result["details"]["available_to_transfer"] == 2000

    def test_release_quota_returns_to_pool(self, registry: GenesisModelRegistry) -> None:
        """Releasing quota makes it available in global pool again."""
        result = registry._release_quota(
            ["agent_001", "gemini/gemini-2.5-flash", 5000],
            "agent_001"
        )
        assert result["success"] is True
        assert result["new_quota"] == 5000

        # Check global availability increased
        list_result = registry._list_models([], "bob")
        model = list_result["models"][0]
        # 50000 - 5000 (agent_001) - 10000 (agent_002) = 35000 available
        assert model["available"] == 35000


class TestFallbackModelSelection:
    """Tests for fallback model selection."""

    @pytest.fixture
    def registry(self) -> GenesisModelRegistry:
        """Create registry with multiple models."""
        reg = GenesisModelRegistry()
        reg.configure_model("gemini/gemini-2.5-flash", global_limit=50000)
        reg.configure_model("gemini/gemini-3-flash", global_limit=10000)
        reg.allocate_initial_quota("agent_001", "gemini/gemini-2.5-flash", 1000)
        reg.allocate_initial_quota("agent_001", "gemini/gemini-3-flash", 2000)
        return reg

    def test_fallback_model(self, registry: GenesisModelRegistry) -> None:
        """Falls back to next available model when primary exhausted."""
        # Exhaust primary model
        registry._consume(["agent_001", "gemini/gemini-2.5-flash", 1000], "system")

        # Get available models - should return fallback only
        result = registry._get_available_models(["agent_001"], "agent_001")

        model_ids = [m["model_id"] for m in result["models"]]
        assert "gemini/gemini-2.5-flash" not in model_ids
        assert "gemini/gemini-3-flash" in model_ids

    def test_get_available_models_returns_capacity_ordered(self) -> None:
        """get_available_models returns models ordered by remaining capacity."""
        registry = GenesisModelRegistry()
        registry.configure_model("model-a", global_limit=50000)
        registry.configure_model("model-b", global_limit=50000)
        registry.configure_model("model-c", global_limit=50000)

        registry.allocate_initial_quota("alice", "model-a", 1000)
        registry.allocate_initial_quota("alice", "model-b", 5000)
        registry.allocate_initial_quota("alice", "model-c", 2000)

        result = registry._get_available_models(["alice"], "alice")
        assert result["count"] == 3

        # Should be ordered: model-b (5000), model-c (2000), model-a (1000)
        models = result["models"]
        assert models[0]["model_id"] == "model-b"
        assert models[1]["model_id"] == "model-c"
        assert models[2]["model_id"] == "model-a"


class TestValidation:
    """Tests for input validation."""

    def test_get_quota_unknown_model(self) -> None:
        """get_quota fails for unknown model."""
        registry = GenesisModelRegistry()

        result = registry._get_quota(["alice", "unknown-model"], "alice")
        assert result["success"] is False
        assert result.get("code") == "not_found"

    def test_get_quota_missing_args(self) -> None:
        """get_quota requires agent_id and model_id."""
        registry = GenesisModelRegistry()

        result = registry._get_quota(["alice"], "alice")
        assert result["success"] is False
        assert result.get("code") == "missing_argument"

    def test_consume_negative_amount_fails(self) -> None:
        """Cannot consume negative amounts."""
        registry = GenesisModelRegistry()
        registry.configure_model("gemini-2.5-flash", global_limit=50000)
        registry.allocate_initial_quota("alice", "gemini-2.5-flash", 10000)

        result = registry._consume(
            ["alice", "gemini-2.5-flash", -100],
            "system"
        )
        assert result["success"] is False


class TestInterface:
    """Tests for interface schema."""

    def test_get_interface_returns_tools(self) -> None:
        """get_interface returns tool descriptions."""
        registry = GenesisModelRegistry()

        interface = registry.get_interface()
        assert "tools" in interface
        assert len(interface["tools"]) > 0

        # Check expected methods are present
        tool_names = [t["name"] for t in interface["tools"]]
        assert "list_models" in tool_names
        assert "get_quota" in tool_names
        assert "transfer_quota" in tool_names
        assert "consume" in tool_names
