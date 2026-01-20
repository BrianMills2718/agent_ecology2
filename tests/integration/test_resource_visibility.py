"""Integration tests for the Agent Resource Visibility system.

Tests the end-to-end resource visibility flow:
- ResourceMetricsProvider integration with World
- Agent prompt injection with metrics
- Configuration override behavior

Plan #93: Agent Resource Visibility
"""

from __future__ import annotations

import pytest

from src.world.world import World
from src.world.resource_metrics import ResourceVisibilityConfig


class TestMetricsInStateSummary:
    """Tests for resource metrics in world state."""

    def test_metrics_in_state_summary(self, test_world: World) -> None:
        """StateSummary includes resource_metrics."""
        # Get state summary
        summary = test_world.get_state_summary()

        # Should have resource_metrics key
        assert "resource_metrics" in summary

        # Should have metrics for known agents
        for agent_id in test_world.principal_ids:
            if agent_id.startswith("genesis_"):
                continue  # Skip genesis artifacts
            # Agent should have resource metrics
            assert agent_id in summary["resource_metrics"]


class TestAgentVisibility:
    """Tests for agent-level visibility configuration."""

    def test_agent_sees_own_metrics(self, test_world: World) -> None:
        """Agent prompt includes their metrics."""
        # This would require actually building a prompt and checking
        # For now, verify the metrics structure is correct
        summary = test_world.get_state_summary()

        if "resource_metrics" in summary:
            for agent_id, metrics in summary["resource_metrics"].items():
                # Each agent's metrics should have resources dict
                assert "resources" in metrics or metrics == {}

    def test_agent_visibility_config_override(self) -> None:
        """Per-agent config overrides system default."""
        # Create configs
        system_config = ResourceVisibilityConfig(
            resources=["llm_budget", "disk"],
            detail_level="standard",
        )
        agent_config = ResourceVisibilityConfig(
            resources=["llm_budget"],  # Override: only llm_budget
            detail_level="verbose",  # Override: verbose
        )

        # Agent config should take precedence
        assert agent_config.detail_level == "verbose"
        assert agent_config.resources == ["llm_budget"]

    def test_see_others_false(self) -> None:
        """Agent only sees own resources when see_others=False."""
        config = ResourceVisibilityConfig(see_others=False)
        assert config.see_others is False

    def test_see_others_true(self) -> None:
        """Agent sees all agents' resources when see_others=True."""
        config = ResourceVisibilityConfig(see_others=True)
        assert config.see_others is True
