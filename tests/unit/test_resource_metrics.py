"""Unit tests for the ResourceMetricsProvider class.

Tests the resource visibility system that aggregates metrics from:
- Ledger.resources (llm_budget, etc.)
- Config (initial allocations)

Plan #93: Agent Resource Visibility
"""

from __future__ import annotations

import time
from typing import Any

import pytest

from src.world.resource_metrics import (
    ResourceMetrics,
    AgentResourceMetrics,
    ResourceMetricsProvider,
    ResourceVisibilityConfig,
)


class TestResourceMetricsBasic:
    """Tests for basic ResourceMetricsProvider functionality."""

    def test_get_agent_metrics_basic(self) -> None:
        """Returns metrics for agent with llm_budget."""
        provider = ResourceMetricsProvider(
            initial_allocations={"llm_budget": 1.0, "disk": 10000},
            resource_units={"llm_budget": "dollars", "disk": "bytes"},
        )

        ledger_resources = {"agent_a": {"llm_budget": 0.75}}

        metrics = provider.get_agent_metrics(
            agent_id="agent_a",
            ledger_resources=ledger_resources,
            agents={},
            start_time=time.time() - 60,
        )

        assert metrics.agent_id == "agent_a"
        assert "llm_budget" in metrics.resources
        assert metrics.resources["llm_budget"].remaining == 0.75
        assert metrics.resources["llm_budget"].unit == "dollars"

    def test_metrics_percentage_calculation(self) -> None:
        """percentage = remaining/initial * 100"""
        provider = ResourceMetricsProvider(
            initial_allocations={"llm_budget": 1.0},
            resource_units={"llm_budget": "dollars"},
        )

        ledger_resources = {"agent_a": {"llm_budget": 0.6}}

        metrics = provider.get_agent_metrics(
            agent_id="agent_a",
            ledger_resources=ledger_resources,
            agents={},
            start_time=time.time(),
        )

        # 0.6 / 1.0 * 100 = 60%
        assert metrics.resources["llm_budget"].percentage == 60.0

    def test_metrics_spent_calculation(self) -> None:
        """spent = initial - remaining"""
        provider = ResourceMetricsProvider(
            initial_allocations={"llm_budget": 1.0},
            resource_units={"llm_budget": "dollars"},
        )

        ledger_resources = {"agent_a": {"llm_budget": 0.3}}

        metrics = provider.get_agent_metrics(
            agent_id="agent_a",
            ledger_resources=ledger_resources,
            agents={},
            start_time=time.time(),
        )

        # 1.0 - 0.3 = 0.7
        assert metrics.resources["llm_budget"].spent == 0.7

    def test_burn_rate_calculation(self) -> None:
        """burn_rate = spent / elapsed_seconds"""
        provider = ResourceMetricsProvider(
            initial_allocations={"llm_budget": 1.0},
            resource_units={"llm_budget": "dollars"},
        )

        ledger_resources = {"agent_a": {"llm_budget": 0.4}}

        # Started 100 seconds ago
        start_time = time.time() - 100

        metrics = provider.get_agent_metrics(
            agent_id="agent_a",
            ledger_resources=ledger_resources,
            agents={},
            start_time=start_time,
        )

        # spent = 0.6, elapsed = 100s, rate = 0.006/s
        assert metrics.resources["llm_budget"].burn_rate is not None
        assert abs(metrics.resources["llm_budget"].burn_rate - 0.006) < 0.001


class TestDetailLevels:
    """Tests for detail level filtering."""

    def test_detail_level_minimal(self) -> None:
        """Only includes remaining for minimal detail level."""
        provider = ResourceMetricsProvider(
            initial_allocations={"llm_budget": 1.0},
            resource_units={"llm_budget": "dollars"},
        )

        ledger_resources = {"agent_a": {"llm_budget": 0.5}}

        config = ResourceVisibilityConfig(detail_level="minimal")

        metrics = provider.get_agent_metrics(
            agent_id="agent_a",
            ledger_resources=ledger_resources,
            agents={},
            start_time=time.time(),
            visibility_config=config,
        )

        llm_metrics = metrics.resources["llm_budget"]
        # minimal: only remaining
        assert llm_metrics.remaining == 0.5
        # Other fields should be None or excluded
        assert llm_metrics.initial is None
        assert llm_metrics.spent is None
        assert llm_metrics.percentage is None

    def test_detail_level_standard(self) -> None:
        """Includes remaining, initial, spent, percentage for standard."""
        provider = ResourceMetricsProvider(
            initial_allocations={"llm_budget": 1.0},
            resource_units={"llm_budget": "dollars"},
        )

        ledger_resources = {"agent_a": {"llm_budget": 0.5}}

        config = ResourceVisibilityConfig(detail_level="standard")

        metrics = provider.get_agent_metrics(
            agent_id="agent_a",
            ledger_resources=ledger_resources,
            agents={},
            start_time=time.time(),
            visibility_config=config,
        )

        llm_metrics = metrics.resources["llm_budget"]
        # standard: remaining, initial, spent, percentage
        assert llm_metrics.remaining == 0.5
        assert llm_metrics.initial == 1.0
        assert llm_metrics.spent == 0.5
        assert llm_metrics.percentage == 50.0
        # LLM-specific should be None at standard level
        assert llm_metrics.tokens_in is None
        assert llm_metrics.burn_rate is None

    def test_detail_level_verbose(self) -> None:
        """Includes all metrics for verbose detail level."""
        provider = ResourceMetricsProvider(
            initial_allocations={"llm_budget": 1.0},
            resource_units={"llm_budget": "dollars"},
        )

        ledger_resources = {"agent_a": {"llm_budget": 0.5}}

        config = ResourceVisibilityConfig(detail_level="verbose")

        metrics = provider.get_agent_metrics(
            agent_id="agent_a",
            ledger_resources=ledger_resources,
            agents={},
            start_time=time.time() - 100,
            visibility_config=config,
        )

        llm_metrics = metrics.resources["llm_budget"]
        # verbose: all fields populated
        assert llm_metrics.remaining == 0.5
        assert llm_metrics.initial == 1.0
        assert llm_metrics.spent == 0.5
        assert llm_metrics.percentage == 50.0
        assert llm_metrics.burn_rate is not None


class TestResourceFiltering:
    """Tests for resource filtering based on config."""

    def test_resource_filtering(self) -> None:
        """Only returns configured resources."""
        provider = ResourceMetricsProvider(
            initial_allocations={"llm_budget": 1.0, "disk": 10000},
            resource_units={"llm_budget": "dollars", "disk": "bytes"},
        )

        ledger_resources = {"agent_a": {"llm_budget": 0.5, "disk": 5000}}

        # Only request llm_budget
        config = ResourceVisibilityConfig(resources=["llm_budget"])

        metrics = provider.get_agent_metrics(
            agent_id="agent_a",
            ledger_resources=ledger_resources,
            agents={},
            start_time=time.time(),
            visibility_config=config,
        )

        # Only llm_budget should be present
        assert "llm_budget" in metrics.resources
        assert "disk" not in metrics.resources

    def test_invalid_resource_name_errors(self) -> None:
        """Raises error for unknown resource at startup."""
        provider = ResourceMetricsProvider(
            initial_allocations={"llm_budget": 1.0},
            resource_units={"llm_budget": "dollars"},
        )

        # Config references non-existent resource
        config = ResourceVisibilityConfig(resources=["nonexistent_resource"])

        with pytest.raises(ValueError, match="Unknown resource"):
            provider.validate_config(config)
