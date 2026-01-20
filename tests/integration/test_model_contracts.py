"""Integration tests for Plan #113: Contractable Model Access.

Tests for model access contracts and trading via genesis_model_registry.
"""

from __future__ import annotations

import pytest

from src.world.genesis.model_registry import GenesisModelRegistry


class TestModelAccessContract:
    """Tests for model access via genesis artifact."""

    @pytest.fixture
    def registry(self) -> GenesisModelRegistry:
        """Create a model registry for testing."""
        registry = GenesisModelRegistry()
        # Configure some test models
        registry.configure_model(
            model_id="gemini/gemini-2.5-flash",
            global_limit=50000,
            cost_per_1k_input=0.002,
            cost_per_1k_output=0.006,
            properties=["fast", "cheap"],
        )
        registry.configure_model(
            model_id="claude/haiku",
            global_limit=100000,
            cost_per_1k_input=0.003,
            cost_per_1k_output=0.015,
            properties=["reliable"],
        )
        return registry

    def test_model_access_contract(self, registry: GenesisModelRegistry) -> None:
        """Contract grants model access to agents."""
        # Agent requests quota
        result = registry._request_access(
            args=["agent_001", "gemini/gemini-2.5-flash", 10000],
            invoker_id="agent_001",
        )
        assert result["success"] is True
        assert result["allocated"] == 10000

        # Agent can check their quota
        quota_result = registry._get_quota(
            args=["agent_001", "gemini/gemini-2.5-flash"],
            invoker_id="agent_001",
        )
        assert quota_result["success"] is True
        assert quota_result["quota"] == 10000
        assert quota_result["available"] == 10000

        # Agent can consume quota
        consume_result = registry._consume(
            args=["agent_001", "gemini/gemini-2.5-flash", 500],
            invoker_id="agent_001",
        )
        assert consume_result["success"] is True
        assert consume_result["remaining"] == 9500

        # Verify quota is reduced
        quota_after = registry._get_quota(
            args=["agent_001", "gemini/gemini-2.5-flash"],
            invoker_id="agent_001",
        )
        assert quota_after["available"] == 9500

    def test_model_access_market(self, registry: GenesisModelRegistry) -> None:
        """Agents can trade model access quotas."""
        # Setup: Both agents get initial quota
        registry._request_access(
            args=["agent_001", "gemini/gemini-2.5-flash", 10000],
            invoker_id="agent_001",
        )
        registry._request_access(
            args=["agent_002", "gemini/gemini-2.5-flash", 5000],
            invoker_id="agent_002",
        )

        # Verify initial state
        a1_initial = registry._get_quota(
            args=["agent_001", "gemini/gemini-2.5-flash"],
            invoker_id="agent_001",
        )
        a2_initial = registry._get_quota(
            args=["agent_002", "gemini/gemini-2.5-flash"],
            invoker_id="agent_002",
        )
        assert a1_initial["quota"] == 10000
        assert a2_initial["quota"] == 5000

        # Agent 1 transfers 3000 to Agent 2
        transfer_result = registry._transfer_quota(
            args=["agent_002", "gemini/gemini-2.5-flash", 3000],
            invoker_id="agent_001",
        )
        assert transfer_result["success"] is True
        assert transfer_result["transferred"] == 3000

        # Verify new balances
        a1_after = registry._get_quota(
            args=["agent_001", "gemini/gemini-2.5-flash"],
            invoker_id="agent_001",
        )
        a2_after = registry._get_quota(
            args=["agent_002", "gemini/gemini-2.5-flash"],
            invoker_id="agent_002",
        )
        assert a1_after["quota"] == 7000  # 10000 - 3000
        assert a2_after["quota"] == 8000  # 5000 + 3000

    def test_model_list_and_availability(self, registry: GenesisModelRegistry) -> None:
        """Agents can list models and check availability."""
        # List all models
        list_result = registry._list_models(args=[], invoker_id="agent_001")
        assert list_result["success"] is True
        assert list_result["count"] == 2

        model_ids = [m["model_id"] for m in list_result["models"]]
        assert "gemini/gemini-2.5-flash" in model_ids
        assert "claude/haiku" in model_ids

        # Request quota and check available models
        registry._request_access(
            args=["agent_001", "gemini/gemini-2.5-flash", 1000],
            invoker_id="agent_001",
        )

        available = registry._get_available_models(
            args=["agent_001"],
            invoker_id="agent_001",
        )
        assert available["success"] is True
        assert available["count"] == 1
        assert available["models"][0]["model_id"] == "gemini/gemini-2.5-flash"

    def test_insufficient_quota_blocked(self, registry: GenesisModelRegistry) -> None:
        """Operations blocked when quota insufficient."""
        # Agent gets small quota
        registry._request_access(
            args=["agent_001", "gemini/gemini-2.5-flash", 100],
            invoker_id="agent_001",
        )

        # Try to consume more than available
        result = registry._consume(
            args=["agent_001", "gemini/gemini-2.5-flash", 200],
            invoker_id="agent_001",
        )
        assert result["success"] is False
        assert "Insufficient quota" in result.get("error", "")

    def test_transfer_fails_with_insufficient_quota(
        self, registry: GenesisModelRegistry
    ) -> None:
        """Transfer fails if sender doesn't have enough quota."""
        # Agent 1 gets quota
        registry._request_access(
            args=["agent_001", "gemini/gemini-2.5-flash", 1000],
            invoker_id="agent_001",
        )

        # Try to transfer more than available
        result = registry._transfer_quota(
            args=["agent_002", "gemini/gemini-2.5-flash", 2000],
            invoker_id="agent_001",
        )
        assert result["success"] is False
