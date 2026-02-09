"""System Auditor for ecosystem health assessment.

Provides threshold-based health assessment of ecosystem KPIs,
generating reports with concerns and trends.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from ..config import get_validated_config
from .kpis import EcosystemKPIs

if TYPE_CHECKING:
    import logging


def _get_default_thresholds() -> dict[str, float]:
    """Get audit thresholds from config."""
    config = get_validated_config()
    monitoring = config.monitoring
    return {
        "gini_warning": monitoring.audit_thresholds.gini.warning,
        "gini_critical": monitoring.audit_thresholds.gini.critical or 0.9,
        "frozen_ratio_warning": monitoring.audit_thresholds.frozen_ratio.warning,
        "frozen_ratio_critical": monitoring.audit_thresholds.frozen_ratio.critical or 0.5,
        "active_ratio_warning": monitoring.audit_thresholds.active_ratio.warning,
        "active_ratio_critical": monitoring.audit_thresholds.active_ratio.critical or 0.1,
        "burn_rate_warning": monitoring.audit_thresholds.burn_rate.warning,
        "burn_rate_critical": monitoring.audit_thresholds.burn_rate.critical or 0.25,
        "scrip_velocity_low_warning": monitoring.audit_thresholds.scrip_velocity_low.warning,
    }


@dataclass
class AuditorThresholds:
    """Configurable thresholds for health assessment.

    Defaults loaded from config/config.yaml monitoring.audit_thresholds.
    """

    # Gini coefficient (wealth inequality)
    gini_warning: float = 0.7
    gini_critical: float = 0.9

    # Frozen agent ratio
    frozen_ratio_warning: float = 0.2
    frozen_ratio_critical: float = 0.5

    # Active agent ratio
    active_ratio_warning: float = 0.3
    active_ratio_critical: float = 0.1

    # LLM budget burn rate (% per hour)
    burn_rate_warning: float = 0.1
    burn_rate_critical: float = 0.25

    # Scrip velocity (low = economic stagnation)
    scrip_velocity_low_warning: float = 0.001

    @classmethod
    def from_config(cls) -> "AuditorThresholds":
        """Create thresholds from config values."""
        defaults = _get_default_thresholds()
        return cls(
            gini_warning=defaults["gini_warning"],
            gini_critical=defaults["gini_critical"],
            frozen_ratio_warning=defaults["frozen_ratio_warning"],
            frozen_ratio_critical=defaults["frozen_ratio_critical"],
            active_ratio_warning=defaults["active_ratio_warning"],
            active_ratio_critical=defaults["active_ratio_critical"],
            burn_rate_warning=defaults["burn_rate_warning"],
            burn_rate_critical=defaults["burn_rate_critical"],
            scrip_velocity_low_warning=defaults["scrip_velocity_low_warning"],
        )


@dataclass
class HealthConcern:
    """A specific health issue detected."""

    metric: str  # Which KPI
    value: float  # Current value
    threshold: float  # Violated threshold
    severity: str  # "warning" or "critical"
    message: str  # Human-readable description


@dataclass
class HealthReport:
    """Overall ecosystem health assessment."""

    timestamp: str
    overall_status: str  # "healthy", "warning", "critical"
    health_score: float  # 0.0-1.0 composite score
    concerns: list[HealthConcern] = field(default_factory=list)
    kpis: EcosystemKPIs = field(default_factory=EcosystemKPIs)
    trend: str = "unknown"  # "improving", "stable", "declining", "unknown"


def calculate_health_score(concerns: list[HealthConcern]) -> float:
    """Calculate composite health score from concerns.

    Score ranges from 0.0 (very unhealthy) to 1.0 (perfectly healthy).
    Penalties from config: monitoring.health_scoring.warning_penalty/critical_penalty.
    """
    if not concerns:
        return 1.0

    config = get_validated_config()
    warning_penalty = config.monitoring.health_scoring.warning_penalty
    critical_penalty = config.monitoring.health_scoring.critical_penalty

    penalty = 0.0
    for concern in concerns:
        if concern.severity == "critical":
            penalty += critical_penalty
        elif concern.severity == "warning":
            penalty += warning_penalty

    return max(0.0, min(1.0, 1.0 - penalty))


def determine_trend(
    current_score: float, prev_score: float | None, threshold: float | None = None
) -> str:
    """Determine trend based on score comparison.

    Args:
        current_score: Current health score
        prev_score: Previous health score (None if no history)
        threshold: Minimum change to count as improving/declining.
                   Defaults to config monitoring.health_scoring.trend_threshold.

    Returns:
        "improving", "stable", "declining", or "unknown"
    """
    if prev_score is None:
        return "unknown"

    if threshold is None:
        threshold = get_validated_config().monitoring.health_scoring.trend_threshold

    diff = current_score - prev_score

    if diff > threshold:
        return "improving"
    elif diff < -threshold:
        return "declining"
    else:
        return "stable"


def assess_health(
    kpis: EcosystemKPIs,
    prev_kpis: EcosystemKPIs | None,
    thresholds: AuditorThresholds,
    total_agents: int = 1,
) -> HealthReport:
    """Assess ecosystem health from KPIs.

    Args:
        kpis: Current ecosystem KPIs
        prev_kpis: Previous KPIs for trend calculation (None if first report)
        thresholds: Threshold configuration
        total_agents: Total number of agents for ratio calculations

    Returns:
        HealthReport with status, score, concerns, and trend
    """
    concerns: list[HealthConcern] = []

    # Check Gini coefficient (wealth inequality)
    if kpis.gini_coefficient >= thresholds.gini_critical:
        concerns.append(
            HealthConcern(
                metric="gini_coefficient",
                value=kpis.gini_coefficient,
                threshold=thresholds.gini_critical,
                severity="critical",
                message=f"Extreme wealth inequality: {kpis.gini_coefficient:.2f}",
            )
        )
    elif kpis.gini_coefficient >= thresholds.gini_warning:
        concerns.append(
            HealthConcern(
                metric="gini_coefficient",
                value=kpis.gini_coefficient,
                threshold=thresholds.gini_warning,
                severity="warning",
                message=f"High wealth inequality: {kpis.gini_coefficient:.2f}",
            )
        )

    # Check frozen agent ratio
    frozen_ratio = kpis.frozen_agent_count / max(1, total_agents)
    if frozen_ratio >= thresholds.frozen_ratio_critical:
        concerns.append(
            HealthConcern(
                metric="frozen_agent_ratio",
                value=frozen_ratio,
                threshold=thresholds.frozen_ratio_critical,
                severity="critical",
                message=f"Critical: {frozen_ratio:.0%} of agents frozen",
            )
        )
    elif frozen_ratio >= thresholds.frozen_ratio_warning:
        concerns.append(
            HealthConcern(
                metric="frozen_agent_ratio",
                value=frozen_ratio,
                threshold=thresholds.frozen_ratio_warning,
                severity="warning",
                message=f"Warning: {frozen_ratio:.0%} of agents frozen",
            )
        )

    # Check active agent ratio
    if kpis.active_agent_ratio <= thresholds.active_ratio_critical:
        concerns.append(
            HealthConcern(
                metric="active_agent_ratio",
                value=kpis.active_agent_ratio,
                threshold=thresholds.active_ratio_critical,
                severity="critical",
                message=f"Critical inactivity: only {kpis.active_agent_ratio:.0%} agents active",
            )
        )
    elif kpis.active_agent_ratio <= thresholds.active_ratio_warning:
        concerns.append(
            HealthConcern(
                metric="active_agent_ratio",
                value=kpis.active_agent_ratio,
                threshold=thresholds.active_ratio_warning,
                severity="warning",
                message=f"Low activity: only {kpis.active_agent_ratio:.0%} agents active",
            )
        )

    # Check LLM budget burn rate
    if kpis.llm_budget_burn_rate >= thresholds.burn_rate_critical:
        concerns.append(
            HealthConcern(
                metric="llm_budget_burn_rate",
                value=kpis.llm_budget_burn_rate,
                threshold=thresholds.burn_rate_critical,
                severity="critical",
                message=f"Critical burn rate: {kpis.llm_budget_burn_rate:.1%}/s",
            )
        )
    elif kpis.llm_budget_burn_rate >= thresholds.burn_rate_warning:
        concerns.append(
            HealthConcern(
                metric="llm_budget_burn_rate",
                value=kpis.llm_budget_burn_rate,
                threshold=thresholds.burn_rate_warning,
                severity="warning",
                message=f"High burn rate: {kpis.llm_budget_burn_rate:.1%}/s",
            )
        )

    # Check scrip velocity (economic stagnation)
    if kpis.scrip_velocity <= thresholds.scrip_velocity_low_warning:
        concerns.append(
            HealthConcern(
                metric="scrip_velocity",
                value=kpis.scrip_velocity,
                threshold=thresholds.scrip_velocity_low_warning,
                severity="warning",
                message=f"Low economic activity: velocity {kpis.scrip_velocity:.4f}",
            )
        )

    # Determine overall status
    has_critical = any(c.severity == "critical" for c in concerns)
    has_warning = any(c.severity == "warning" for c in concerns)

    if has_critical:
        overall_status = "critical"
    elif has_warning:
        overall_status = "warning"
    else:
        overall_status = "healthy"

    # Calculate health score
    health_score = calculate_health_score(concerns)

    # Determine trend
    prev_score: float | None = None
    if prev_kpis is not None:
        # Calculate previous score for comparison
        prev_concerns = _assess_concerns_only(prev_kpis, thresholds, total_agents)
        prev_score = calculate_health_score(prev_concerns)

    trend = determine_trend(health_score, prev_score)

    return HealthReport(
        timestamp=datetime.now().isoformat(),
        overall_status=overall_status,
        health_score=health_score,
        concerns=concerns,
        kpis=kpis,
        trend=trend,
    )


def _assess_concerns_only(
    kpis: EcosystemKPIs,
    thresholds: AuditorThresholds,
    total_agents: int,
) -> list[HealthConcern]:
    """Helper to assess concerns without full report (for trend calculation)."""
    concerns: list[HealthConcern] = []

    # Gini
    if kpis.gini_coefficient >= thresholds.gini_critical:
        concerns.append(
            HealthConcern("gini_coefficient", kpis.gini_coefficient, 0, "critical", "")
        )
    elif kpis.gini_coefficient >= thresholds.gini_warning:
        concerns.append(
            HealthConcern("gini_coefficient", kpis.gini_coefficient, 0, "warning", "")
        )

    # Frozen ratio
    frozen_ratio = kpis.frozen_agent_count / max(1, total_agents)
    if frozen_ratio >= thresholds.frozen_ratio_critical:
        concerns.append(HealthConcern("frozen_ratio", frozen_ratio, 0, "critical", ""))
    elif frozen_ratio >= thresholds.frozen_ratio_warning:
        concerns.append(HealthConcern("frozen_ratio", frozen_ratio, 0, "warning", ""))

    # Active ratio
    if kpis.active_agent_ratio <= thresholds.active_ratio_critical:
        concerns.append(
            HealthConcern("active_ratio", kpis.active_agent_ratio, 0, "critical", "")
        )
    elif kpis.active_agent_ratio <= thresholds.active_ratio_warning:
        concerns.append(
            HealthConcern("active_ratio", kpis.active_agent_ratio, 0, "warning", "")
        )

    # Burn rate
    if kpis.llm_budget_burn_rate >= thresholds.burn_rate_critical:
        concerns.append(
            HealthConcern("burn_rate", kpis.llm_budget_burn_rate, 0, "critical", "")
        )
    elif kpis.llm_budget_burn_rate >= thresholds.burn_rate_warning:
        concerns.append(
            HealthConcern("burn_rate", kpis.llm_budget_burn_rate, 0, "warning", "")
        )

    # Velocity
    if kpis.scrip_velocity <= thresholds.scrip_velocity_low_warning:
        concerns.append(
            HealthConcern("velocity", kpis.scrip_velocity, 0, "warning", "")
        )

    return concerns

