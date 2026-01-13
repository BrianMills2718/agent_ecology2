# Gap 24: Ecosystem Health KPIs

**Status:** ✅ Complete

**Verified:** 2026-01-13T19:46:13Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-13T19:46:13Z
tests:
  unit: 1017 passed in 11.00s
  e2e_smoke: PASSED (2.05s)
  doc_coupling: passed
commit: 2ee58f3
```
**Priority:** Medium
**Blocked By:** None
**Blocks:** #25 (System Auditor Agent)

---

## Gap

**Current:** No ecosystem health metrics. Human must read raw logs or use dashboard for individual agent inspection.

**Target:** Computed KPIs that indicate overall ecosystem health, capital flow, and emergence patterns.

---

## Problem Statement

The simulation generates rich event data (actions, transfers, artifacts, mints) but lacks aggregate metrics that answer questions like:

- Is the economy healthy? (capital flowing vs stagnant)
- Are agents thriving or struggling? (activity vs frozen)
- Is emergence happening? (coordination, specialization, growth)
- What's the wealth distribution? (equal vs concentrated)

Without KPIs, we can't:
- Detect problems early (starvation cascade, inflation)
- Compare experiment runs
- Measure the impact of parameter changes
- Enable System Auditor Agent (#25) to generate reports

---

## Plan

### Phase 1: Define KPI Categories

**1. Capital Metrics**
| KPI | Formula | Meaning |
|-----|---------|---------|
| `total_scrip` | Sum of all principal scrip balances | Total economy size |
| `scrip_velocity` | Transfers / total_scrip / time | How fast money moves |
| `gini_coefficient` | Lorenz curve calculation | Wealth inequality (0=equal, 1=concentrated) |
| `median_scrip` | Median principal balance | Typical agent wealth |

**2. Activity Metrics**
| KPI | Formula | Meaning |
|-----|---------|---------|
| `active_agent_ratio` | Active agents / total agents | % of economy participating |
| `frozen_agent_count` | Agents with status=frozen | Agents blocked on resources |
| `actions_per_tick` | Actions / ticks | Activity level |
| `thinking_cost_rate` | LLM cost / time | API burn rate |

**3. Market Metrics**
| KPI | Formula | Meaning |
|-----|---------|---------|
| `escrow_volume` | Sum of escrow trade prices | Trading activity |
| `escrow_active_listings` | Count of active listings | Supply in market |
| `mint_scrip_rate` | Scrip minted / time | New money entering |
| `artifact_creation_rate` | Artifacts created / time | Production rate |

**4. Resource Metrics**
| KPI | Formula | Meaning |
|-----|---------|---------|
| `llm_budget_remaining` | Budget limit - spent | Runway left |
| `llm_budget_burn_rate` | Spent / time | Time to exhaustion |
| `rate_limit_utilization` | Used capacity / available | How constrained |

**5. Emergence Indicators**
| KPI | Formula | Meaning |
|-----|---------|---------|
| `agent_spawn_rate` | New agents / time | Growth rate |
| `coordination_events` | Multi-agent contract invokes | Cooperation |
| `artifact_diversity` | Unique artifact types | Specialization |
| `longest_artifact_chain` | Max ownership transfers | Asset churn |

### Phase 2: Implementation

#### 2.1 Add KPI Calculator Module

```python
# src/dashboard/kpis.py

@dataclass
class EcosystemKPIs:
    """Computed health metrics."""
    # Capital
    total_scrip: int
    scrip_velocity: float
    gini_coefficient: float
    median_scrip: int

    # Activity
    active_agent_ratio: float
    frozen_agent_count: int
    actions_per_tick: float
    thinking_cost_rate: float

    # Market
    escrow_volume: int
    escrow_active_listings: int
    mint_scrip_rate: float
    artifact_creation_rate: float

    # Resource
    llm_budget_remaining: float
    llm_budget_burn_rate: float

    # Emergence
    agent_spawn_rate: float
    coordination_events: int
    artifact_diversity: int

    # Trends (last 10 ticks)
    scrip_velocity_trend: list[float]
    activity_trend: list[float]

def calculate_kpis(state: SimulationState, events: list[RawEvent]) -> EcosystemKPIs:
    """Calculate all KPIs from current state and event history."""
    ...
```

#### 2.2 Add Dashboard API Endpoint

```python
# In server.py
@app.get("/api/kpis")
async def get_kpis() -> EcosystemKPIs:
    """Return computed ecosystem health KPIs."""
    state = parser.get_simulation_state()
    events = parser.get_events(limit=1000)
    return calculate_kpis(state, events)
```

#### 2.3 Add Dashboard Widget

New panel in dashboard showing:
- Key metrics at a glance (scrip velocity, active ratio, burn rate)
- Trend sparklines (last 10 ticks)
- Health status indicators (green/yellow/red)

### Phase 3: Thresholds and Alerts

Define configurable thresholds in `config.yaml`:

```yaml
health_kpis:
  thresholds:
    frozen_agent_ratio_warning: 0.3  # 30% frozen = warning
    gini_warning: 0.8                # High inequality
    scrip_velocity_low: 0.01         # Stagnant economy
    burn_rate_warning: 0.1           # >10% budget/hour
  enabled: true
```

### Implementation Steps

1. **Create `src/dashboard/kpis.py`** - KPI calculation logic
2. **Add Pydantic model** - `EcosystemKPIs` in `models.py`
3. **Add API endpoint** - `/api/kpis` in `server.py`
4. **Add dashboard widget** - New panel in `static/`
5. **Add config schema** - `health_kpis` section
6. **Add tests** - Unit tests for calculation logic

---

## Required Tests

### Unit Tests
- `tests/unit/test_kpis.py::test_gini_coefficient_equal` - All equal balances → 0
- `tests/unit/test_kpis.py::test_gini_coefficient_concentrated` - One has all → 1
- `tests/unit/test_kpis.py::test_scrip_velocity_calculation` - Transfers / total / time
- `tests/unit/test_kpis.py::test_frozen_count` - Counts frozen agents correctly

### Integration Tests
- `tests/integration/test_dashboard_kpis.py::test_kpi_endpoint` - API returns valid KPIs
- `tests/integration/test_dashboard_kpis.py::test_kpi_trends` - Trends update over ticks

---

## E2E Verification

Run a simulation and verify KPIs are computed:

```bash
python run.py --ticks 20 --agents 3 --dashboard
# Check http://localhost:8080/api/kpis returns valid data
# Verify dashboard shows KPI panel
```

---

## Out of Scope

- **Alerting/notifications** - Future feature
- **Historical KPI storage** - Just compute current
- **Cross-run comparison** - Future feature
- **Custom KPI definitions** - Fixed set for now

---

## Verification

- [ ] Tests pass
- [ ] Docs updated
- [ ] Implementation matches target

---

## Notes

This enables Gap #25 (System Auditor Agent) which will use these KPIs to generate periodic reports.

See also:
- `src/dashboard/models.py` - Existing dashboard models
- `src/dashboard/parser.py` - Event parsing
- `docs/architecture/target/` - Health observability target
