# Plan #76: Simulation Metrics

**Status:** ✅ Complete

**Verified:** 2026-01-19T04:52:00Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-19T04:52:00Z
tests:
  unit: 1717 passed, 9 skipped, 3 warnings in 57.08s
  e2e_smoke: PASSED (10.70s)
  e2e_real: PASSED (26.81s)
  doc_coupling: passed
commit: f4c320b
```
**Priority:** Medium
**Blocks:** -

---

## Gap

**Current:** Metrics are primarily aggregates (total scrip, actions per tick, overall health). Per-agent breakdowns exist in raw logs but aren't surfaced in KPIs or dashboard.

**Target:** Per-agent metrics tracked and exposed - action success rates, dormancy detection, specialization patterns, individual resource burn.

**Why:** Understanding individual agent behavior enables:
- Early detection of struggling agents
- Identification of specialization/role emergence
- Better debugging of agent failures
- Richer observability for researchers

---

## Design

### Scope (Minimal Valuable Increment)

Focus on **per-agent action metrics** - the simplest extension with highest value:

1. **Per-agent action counts** - How many actions has each agent taken?
2. **Per-agent success rate** - What % of actions succeed vs fail?
3. **Per-agent dormancy** - How long since last action?
4. **Per-agent resource state** - Budget remaining, frozen status

### Implementation Approach

Extend existing infrastructure rather than building new:

| Component | Change |
|-----------|--------|
| `TickSummaryCollector` | Add `per_agent_actions: dict[str, AgentTickStats]` |
| `kpis.py` | Add `per_agent_metrics()` returning per-agent KPIs |
| `server.py` | Add `/api/agents/{id}/metrics` endpoint |
| Dashboard | Agent detail page shows metrics (optional, low priority) |

### Data Model

```python
@dataclass
class AgentTickStats:
    """Per-agent stats for a single tick."""
    actions: int = 0
    successes: int = 0
    failures: int = 0
    tokens_consumed: int = 0
    scrip_spent: Decimal = Decimal(0)

@dataclass
class AgentMetrics:
    """Aggregate metrics for an agent across simulation."""
    total_actions: int
    success_rate: float  # 0.0-1.0
    last_action_tick: int | None
    ticks_since_action: int  # Dormancy indicator
    is_frozen: bool
    llm_budget_remaining: Decimal
    scrip_balance: Decimal
```

### Changes Required

| File | Change |
|------|--------|
| `src/world/logger.py` | Extend `TickSummaryCollector` with per-agent tracking |
| `src/dashboard/kpis.py` | Add `compute_agent_metrics()` function |
| `src/dashboard/server.py` | Add `/api/agents/{id}/metrics` endpoint |
| `src/dashboard/parser.py` | Track per-agent action history during parsing |

## Files Affected

- src/world/logger.py (modify)
- src/dashboard/kpis.py (modify)
- src/dashboard/server.py (modify)
- src/dashboard/parser.py (modify)
- tests/unit/test_logger.py (modify)
- tests/unit/test_kpis.py (modify)
- tests/integration/test_dashboard_api.py (create)
- docs/architecture/current/supporting_systems.md (modify)

---

## Required Tests

| Test | Description |
|------|-------------|
| `tests/unit/test_logger.py::TestTickSummaryCollector::test_per_agent_action_tracking` | Per-agent stats accumulated correctly |
| `tests/unit/test_logger.py::TestTickSummaryCollector::test_per_agent_success_failure` | Success/failure counted per agent |
| `tests/unit/test_kpis.py::TestAgentMetrics::test_compute_agent_metrics` | KPI calculation for agents |
| `tests/unit/test_kpis.py::TestAgentMetrics::test_dormancy_calculation` | Ticks since last action |
| `tests/integration/test_dashboard_api.py::test_agent_metrics_endpoint` | API returns per-agent metrics |

---

## Dependencies

- None (extends existing infrastructure)

---

## Notes

This is a minimal first step. Future enhancements could include:
- Per-agent token efficiency (output quality vs tokens spent)
- Agent cooperation patterns (who invokes whose artifacts)
- Specialization detection (artifact creation patterns)
- Trust network visualization

These are out of scope for this plan but could be separate plans.
