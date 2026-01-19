"""Unit tests for System Auditor health assessment."""

import pytest
from dataclasses import dataclass

from src.dashboard.auditor import (
    HealthConcern,
    HealthReport,
    AuditorThresholds,
    assess_health,
    calculate_health_score,
    determine_trend,
)
from src.dashboard.kpis import EcosystemKPIs


@pytest.fixture
def default_thresholds() -> AuditorThresholds:
    """Default threshold configuration."""
    return AuditorThresholds(
        gini_warning=0.7,
        gini_critical=0.9,
        frozen_ratio_warning=0.2,
        frozen_ratio_critical=0.5,
        active_ratio_warning=0.3,
        active_ratio_critical=0.1,
        burn_rate_warning=0.1,
        burn_rate_critical=0.25,
        scrip_velocity_low_warning=0.001,
    )


@pytest.fixture
def healthy_kpis() -> EcosystemKPIs:
    """KPIs representing a healthy ecosystem."""
    return EcosystemKPIs(
        total_scrip=10000,
        scrip_velocity=0.05,
        gini_coefficient=0.3,  # Low inequality
        median_scrip=500,
        active_agent_ratio=0.8,  # High activity
        frozen_agent_count=1,
        actions_per_second=5.0,  # Time-based metric (Plan #102)
        thinking_cost_rate=0.01,
        escrow_volume=1000,
        escrow_active_listings=5,
        mint_scrip_rate=10.0,
        artifact_creation_rate=2.0,
        llm_budget_remaining=90.0,
        llm_budget_burn_rate=0.01,
        agent_spawn_rate=0.1,
        coordination_events=10,
        artifact_diversity=5,
    )


class TestHealthyEcosystem:
    """Test assessment of healthy ecosystem."""

    def test_healthy_ecosystem(
        self, healthy_kpis: EcosystemKPIs, default_thresholds: AuditorThresholds
    ) -> None:
        """All KPIs within thresholds should return healthy status."""
        report = assess_health(healthy_kpis, None, default_thresholds, total_agents=10)

        assert report.overall_status == "healthy"
        assert len(report.concerns) == 0
        assert report.health_score >= 0.8

    def test_healthy_no_concerns(
        self, healthy_kpis: EcosystemKPIs, default_thresholds: AuditorThresholds
    ) -> None:
        """Healthy ecosystem should have no concerns."""
        report = assess_health(healthy_kpis, None, default_thresholds, total_agents=10)
        assert report.concerns == []


class TestWarningConditions:
    """Test detection of warning-level issues."""

    def test_warning_gini(
        self, healthy_kpis: EcosystemKPIs, default_thresholds: AuditorThresholds
    ) -> None:
        """High Gini coefficient should trigger warning."""
        kpis = EcosystemKPIs(
            gini_coefficient=0.75,  # Above warning threshold
            active_agent_ratio=0.8,
            frozen_agent_count=1,
            llm_budget_burn_rate=0.01,
            scrip_velocity=0.05,
        )
        report = assess_health(kpis, None, default_thresholds, total_agents=10)

        assert report.overall_status == "warning"
        assert len(report.concerns) >= 1
        gini_concern = next(
            (c for c in report.concerns if c.metric == "gini_coefficient"), None
        )
        assert gini_concern is not None
        assert gini_concern.severity == "warning"

    def test_warning_active_ratio(
        self, default_thresholds: AuditorThresholds
    ) -> None:
        """Low active agent ratio should trigger warning."""
        kpis = EcosystemKPIs(
            gini_coefficient=0.3,
            active_agent_ratio=0.25,  # Below warning threshold
            frozen_agent_count=1,
            llm_budget_burn_rate=0.01,
            scrip_velocity=0.05,
        )
        report = assess_health(kpis, None, default_thresholds, total_agents=10)

        assert report.overall_status == "warning"
        activity_concern = next(
            (c for c in report.concerns if c.metric == "active_agent_ratio"), None
        )
        assert activity_concern is not None
        assert activity_concern.severity == "warning"


class TestCriticalConditions:
    """Test detection of critical-level issues."""

    def test_critical_frozen(
        self, default_thresholds: AuditorThresholds
    ) -> None:
        """Many frozen agents should trigger critical."""
        kpis = EcosystemKPIs(
            gini_coefficient=0.3,
            active_agent_ratio=0.8,
            frozen_agent_count=6,  # 60% frozen with 10 total agents
            llm_budget_burn_rate=0.01,
            scrip_velocity=0.05,
        )
        report = assess_health(kpis, None, default_thresholds, total_agents=10)

        assert report.overall_status == "critical"
        frozen_concern = next(
            (c for c in report.concerns if c.metric == "frozen_agent_ratio"), None
        )
        assert frozen_concern is not None
        assert frozen_concern.severity == "critical"

    def test_critical_gini(
        self, default_thresholds: AuditorThresholds
    ) -> None:
        """Extreme Gini coefficient should trigger critical."""
        kpis = EcosystemKPIs(
            gini_coefficient=0.95,  # Above critical threshold
            active_agent_ratio=0.8,
            frozen_agent_count=1,
            llm_budget_burn_rate=0.01,
            scrip_velocity=0.05,
        )
        report = assess_health(kpis, None, default_thresholds, total_agents=10)

        assert report.overall_status == "critical"
        gini_concern = next(
            (c for c in report.concerns if c.metric == "gini_coefficient"), None
        )
        assert gini_concern is not None
        assert gini_concern.severity == "critical"

    def test_critical_burn_rate(
        self, default_thresholds: AuditorThresholds
    ) -> None:
        """High budget burn rate should trigger critical."""
        kpis = EcosystemKPIs(
            gini_coefficient=0.3,
            active_agent_ratio=0.8,
            frozen_agent_count=1,
            llm_budget_burn_rate=0.3,  # Above critical threshold
            scrip_velocity=0.05,
        )
        report = assess_health(kpis, None, default_thresholds, total_agents=10)

        assert report.overall_status == "critical"
        burn_concern = next(
            (c for c in report.concerns if c.metric == "llm_budget_burn_rate"), None
        )
        assert burn_concern is not None
        assert burn_concern.severity == "critical"


class TestMultipleConcerns:
    """Test handling of multiple concurrent issues."""

    def test_multiple_concerns(
        self, default_thresholds: AuditorThresholds
    ) -> None:
        """Multiple issues should all be reported."""
        kpis = EcosystemKPIs(
            gini_coefficient=0.75,  # Warning
            active_agent_ratio=0.25,  # Warning
            frozen_agent_count=3,  # 30% = Warning
            llm_budget_burn_rate=0.15,  # Warning
            scrip_velocity=0.0005,  # Warning (low velocity)
        )
        report = assess_health(kpis, None, default_thresholds, total_agents=10)

        # Should have multiple concerns
        assert len(report.concerns) >= 3

    def test_worst_severity_wins(
        self, default_thresholds: AuditorThresholds
    ) -> None:
        """Overall status should reflect worst concern."""
        kpis = EcosystemKPIs(
            gini_coefficient=0.95,  # Critical
            active_agent_ratio=0.25,  # Warning
            frozen_agent_count=1,
            llm_budget_burn_rate=0.01,
            scrip_velocity=0.05,
        )
        report = assess_health(kpis, None, default_thresholds, total_agents=10)

        # One critical means overall is critical
        assert report.overall_status == "critical"


class TestHealthScore:
    """Test health score calculation."""

    def test_health_score_calculation(
        self, healthy_kpis: EcosystemKPIs, default_thresholds: AuditorThresholds
    ) -> None:
        """Health score should reflect overall health."""
        # Healthy ecosystem should have high score
        healthy_report = assess_health(healthy_kpis, None, default_thresholds, total_agents=10)
        assert 0.8 <= healthy_report.health_score <= 1.0

        # Unhealthy ecosystem should have low score
        unhealthy_kpis = EcosystemKPIs(
            gini_coefficient=0.95,
            active_agent_ratio=0.05,
            frozen_agent_count=8,
            llm_budget_burn_rate=0.3,
            scrip_velocity=0.0001,
        )
        unhealthy_report = assess_health(unhealthy_kpis, None, default_thresholds, total_agents=10)
        assert unhealthy_report.health_score < 0.5

    def test_health_score_bounds(
        self, default_thresholds: AuditorThresholds
    ) -> None:
        """Health score should always be between 0 and 1."""
        # Test with extreme values
        extreme_kpis = EcosystemKPIs(
            gini_coefficient=1.0,
            active_agent_ratio=0.0,
            frozen_agent_count=100,
            llm_budget_burn_rate=1.0,
            scrip_velocity=0.0,
        )
        report = assess_health(extreme_kpis, None, default_thresholds, total_agents=100)
        assert 0.0 <= report.health_score <= 1.0


class TestTrend:
    """Test trend detection."""

    def test_trend_improving(
        self, default_thresholds: AuditorThresholds
    ) -> None:
        """Score increasing should show improving trend."""
        prev_kpis = EcosystemKPIs(
            gini_coefficient=0.8,  # Warning
            active_agent_ratio=0.25,  # Warning
            frozen_agent_count=3,
            llm_budget_burn_rate=0.15,
            scrip_velocity=0.001,
        )
        current_kpis = EcosystemKPIs(
            gini_coefficient=0.5,  # Now healthy
            active_agent_ratio=0.6,  # Now healthy
            frozen_agent_count=1,
            llm_budget_burn_rate=0.05,
            scrip_velocity=0.05,
        )
        report = assess_health(current_kpis, prev_kpis, default_thresholds, total_agents=10)
        assert report.trend == "improving"

    def test_trend_declining(
        self, default_thresholds: AuditorThresholds
    ) -> None:
        """Score decreasing should show declining trend."""
        prev_kpis = EcosystemKPIs(
            gini_coefficient=0.3,
            active_agent_ratio=0.8,
            frozen_agent_count=1,
            llm_budget_burn_rate=0.01,
            scrip_velocity=0.05,
        )
        current_kpis = EcosystemKPIs(
            gini_coefficient=0.85,  # Now warning
            active_agent_ratio=0.2,  # Now warning
            frozen_agent_count=5,
            llm_budget_burn_rate=0.2,
            scrip_velocity=0.0005,
        )
        report = assess_health(current_kpis, prev_kpis, default_thresholds, total_agents=10)
        assert report.trend == "declining"

    def test_trend_stable(
        self, healthy_kpis: EcosystemKPIs, default_thresholds: AuditorThresholds
    ) -> None:
        """Similar scores should show stable trend."""
        report = assess_health(healthy_kpis, healthy_kpis, default_thresholds, total_agents=10)
        assert report.trend == "stable"

    def test_trend_unknown_no_previous(
        self, healthy_kpis: EcosystemKPIs, default_thresholds: AuditorThresholds
    ) -> None:
        """No previous KPIs should show unknown trend."""
        report = assess_health(healthy_kpis, None, default_thresholds, total_agents=10)
        assert report.trend == "unknown"
