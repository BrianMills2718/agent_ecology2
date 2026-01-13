# Gap 25: System Auditor Agent

**Status:** ✅ Complete

**Verified:** 2026-01-13T20:11:20Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-13T20:11:20Z
tests:
  unit: 1096 passed, 1 skipped in 15.59s
  e2e_smoke: PASSED (2.33s)
  doc_coupling: passed
commit: a5c1232
```
**Priority:** Low
**Blocked By:** None (was #24, now complete)
**Blocks:** None

---

## Gap

**Current:** Human must read raw logs or use dashboard for individual agent inspection.

**Target:** Read-only observer generating periodic health reports based on KPIs.

---

## Problem Statement

Gap #24 implemented computed KPIs (Gini coefficient, scrip velocity, frozen agents, etc.) but these are raw numbers. A human still needs to interpret them:

- Is Gini 0.6 good or bad?
- Is 30% frozen agents concerning?
- Is the burn rate sustainable?

The System Auditor provides:
1. **Threshold-based assessment** - Automatic classification (healthy/warning/critical)
2. **Trend analysis** - Are things getting better or worse?
3. **Actionable concerns** - Specific issues to investigate
4. **Periodic reports** - Logged to event stream for observability

---

## Plan

### Phase 1: Health Assessment Module

**1.1 HealthReport dataclass**

```python
# src/dashboard/auditor.py

@dataclass
class HealthConcern:
    """A specific health issue detected."""
    metric: str           # Which KPI
    value: float          # Current value
    threshold: float      # Violated threshold
    severity: str         # "warning" or "critical"
    message: str          # Human-readable description

@dataclass
class HealthReport:
    """Overall ecosystem health assessment."""
    timestamp: str
    overall_status: str   # "healthy", "warning", "critical"
    health_score: float   # 0.0-1.0 composite score
    concerns: list[HealthConcern]
    kpis: EcosystemKPIs   # Raw KPIs for reference
    trend: str            # "improving", "stable", "declining"
```

**1.2 Threshold Configuration**

Add to `config/schema.yaml`:

```yaml
auditor:
  enabled: bool = False
  report_interval_ticks: int = 10  # How often to generate reports
  thresholds:
    gini_warning: float = 0.7
    gini_critical: float = 0.9
    frozen_ratio_warning: float = 0.2
    frozen_ratio_critical: float = 0.5
    active_ratio_warning: float = 0.3
    active_ratio_critical: float = 0.1
    burn_rate_warning: float = 0.1  # % budget per hour
    burn_rate_critical: float = 0.25
    scrip_velocity_low_warning: float = 0.001
```

**1.3 Assessment Logic**

```python
def assess_health(
    kpis: EcosystemKPIs,
    prev_kpis: EcosystemKPIs | None,
    thresholds: AuditorThresholds
) -> HealthReport:
    """Assess ecosystem health from KPIs."""
    concerns = []

    # Check Gini coefficient (wealth inequality)
    if kpis.gini_coefficient >= thresholds.gini_critical:
        concerns.append(HealthConcern(
            metric="gini_coefficient",
            value=kpis.gini_coefficient,
            threshold=thresholds.gini_critical,
            severity="critical",
            message=f"Extreme wealth inequality: {kpis.gini_coefficient:.2f}"
        ))
    elif kpis.gini_coefficient >= thresholds.gini_warning:
        # ... warning level

    # Check frozen agent ratio
    # Check active agent ratio
    # Check burn rate sustainability
    # Check scrip velocity (economic stagnation)

    # Compute overall status
    # Compute health score (weighted average)
    # Compute trend from prev_kpis

    return HealthReport(...)
```

### Phase 2: Integration

**2.1 Dashboard Endpoint**

Add `/api/health` endpoint in `server.py`:

```python
@app.get("/api/health")
async def get_health() -> dict[str, Any]:
    """Get ecosystem health report."""
    kpis = calculate_kpis(dashboard.parser.state)
    report = assess_health(kpis, dashboard.prev_kpis, thresholds)
    dashboard.prev_kpis = kpis
    return asdict(report)
```

**2.2 Event Logging**

Health reports should be logged to the event stream:

```python
# In auditor.py
def log_health_report(report: HealthReport, logger: logging.Logger) -> None:
    """Log health report as structured event."""
    logger.info(
        "health_report",
        extra={
            "event_type": "health_report",
            "overall_status": report.overall_status,
            "health_score": report.health_score,
            "concern_count": len(report.concerns),
            "trend": report.trend,
        }
    )
```

**2.3 SimulationRunner Integration (Optional)**

If `auditor.enabled`, generate reports every N ticks:

```python
# In runner.py tick loop
if config.get("auditor.enabled") and tick % report_interval == 0:
    kpis = calculate_kpis(state)
    report = assess_health(kpis, prev_kpis, thresholds)
    log_health_report(report, logger)
    prev_kpis = kpis
```

### Implementation Steps

1. **Create `src/dashboard/auditor.py`** - HealthReport, HealthConcern, assess_health()
2. **Add config schema** - `auditor` section in `config/schema.yaml`
3. **Add `/api/health` endpoint** - In `server.py`
4. **Add event logging** - log_health_report() function
5. **Add runner integration** - Periodic reports during simulation
6. **Add tests** - Unit tests for threshold logic
7. **Update docs** - `current/supporting_systems.md`

---

## Required Tests

### Unit Tests
- `tests/unit/test_auditor.py::test_healthy_ecosystem` - All KPIs within thresholds → "healthy"
- `tests/unit/test_auditor.py::test_warning_gini` - High Gini → warning concern
- `tests/unit/test_auditor.py::test_critical_frozen` - Many frozen agents → critical concern
- `tests/unit/test_auditor.py::test_multiple_concerns` - Multiple issues detected
- `tests/unit/test_auditor.py::test_health_score_calculation` - Score reflects severity
- `tests/unit/test_auditor.py::test_trend_improving` - Score increasing → "improving"
- `tests/unit/test_auditor.py::test_trend_declining` - Score decreasing → "declining"

### Integration Tests
- `tests/integration/test_dashboard_health.py::test_health_endpoint` - API returns valid report
- `tests/integration/test_dashboard_health.py::test_health_with_simulation` - Reports reflect simulation state

---

## E2E Verification

Run simulation and verify health assessment:

```bash
python run.py --ticks 20 --agents 3 --dashboard
# Check http://localhost:8080/api/health returns valid report
# Verify overall_status is one of: healthy, warning, critical
# Verify health_score is between 0.0 and 1.0
```

---

## Out of Scope

- **Alerts/notifications** - Just assessment, no push notifications
- **Historical report storage** - Reports logged to events, not persisted separately
- **Custom threshold editing via UI** - Config file only
- **Remediation suggestions** - Assessment only, not prescriptive

---

## Verification

- [ ] Tests pass
- [ ] Docs updated
- [ ] Implementation matches target

---

## Notes

This builds directly on Gap #24's EcosystemKPIs. The auditor interprets those KPIs through configurable thresholds to produce actionable health assessments.

Key design decisions:
- **Read-only** - Auditor observes but never modifies state
- **Configurable thresholds** - No hardcoded magic numbers
- **Event logging** - Reports appear in run.jsonl for observability
- **Optional integration** - Can be enabled/disabled via config

See also:
- `src/dashboard/kpis.py` - KPI calculations (Gap #24)
- `docs/architecture/target/` - Health observability target
