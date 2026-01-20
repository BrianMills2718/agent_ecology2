# Plan 93: Agent Resource Visibility

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None (was #95, now complete)
**Blocks:** None

---

## Gap

**Current:** Agents don't see their LLM budget consumption or detailed resource metrics. They only see:
- Scrip balance (economic currency)
- Compute quota (llm_tokens per tick)
- Disk quota/used/available

Missing: `llm_budget` (dollars), token breakdowns, cost metrics, burn rates.

**Target:** Agents see comprehensive, configurable resource metrics in their context for self-regulation:
- Remaining budget (dollars) with percentage
- Tokens consumed (in/out breakdown)
- Cost per request averages
- Burn rate (consumption velocity)
- Configurable at system and per-agent levels

**Why Medium:** Improves agent self-regulation and emergent resource-aware behavior without affecting core simulation mechanics.

---

## References Reviewed

- `src/world/resource_manager.py:1-469` - ResourceManager API (Plan #95 foundation)
- `src/world/ledger.py:200-260` - Ledger.resources tracks llm_budget
- `src/world/ledger.py:536-556` - get_all_balances() vs get_all_balances_full()
- `src/world/world.py:1306-1341` - StateSummary structure, get_state_summary()
- `src/agents/agent.py:591-720` - build_prompt() context injection
- `src/agents/agent.py:250-262` - Agent has own LLMProvider instance
- `llm_provider_standalone/llm_provider.py:158-178` - usage_stats and last_usage tracking
- `llm_provider_standalone/llm_provider.py:1144-1163` - get_usage_stats() API
- `src/config_schema.py:100-115` - ResourcesConfig schema
- `src/agents/loader.py` - Agent loading from YAML
- `config/config.yaml:11-21` - Current resource configuration
- `CLAUDE.md` - Maximum configurability, fail loud principles

---

## Files Affected

- `src/world/resource_metrics.py` (create) - ResourceMetricsProvider component
- `src/world/world.py` (modify) - Add resource_metrics to StateSummary
- `src/agents/agent.py` (modify) - Use metrics in build_prompt(), load visibility config
- `src/agents/loader.py` (modify) - Parse resource_visibility from agent.yaml
- `src/agents/models.py` (modify) - Add ResourceVisibilityConfig model
- `src/config_schema.py` (modify) - Add visibility config to ResourcesConfig
- `config/config.yaml` (modify) - Add default visibility settings
- `config/schema.yaml` (modify) - Document new config options
- `tests/unit/test_resource_metrics.py` (create) - Unit tests for ResourceMetricsProvider
- `tests/integration/test_resource_visibility.py` (create) - Integration tests
- `docs/architecture/current/resources.md` (modify) - Document visibility system

---

## Plan

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    ResourceMetricsProvider                           │
│                                                                      │
│  Responsibility: Read-only aggregation of resource metrics           │
│                  (Separate from ResourceManager for clean SoC)       │
│                                                                      │
│  Data Sources:                                                       │
│  ├─ Ledger.resources["llm_budget"] → remaining budget                │
│  ├─ Agent.llm.get_usage_stats() → tokens, cost, requests             │
│  ├─ World.get_quota() → disk quotas                                  │
│  └─ Config → initial allocations                                     │
│                                                                      │
│  Output: AgentResourceMetrics dataclass                              │
└─────────────────────────────────────────────────────────────────────┘
```

### Data Models

```python
@dataclass
class ResourceMetrics:
    """Metrics for a single resource."""
    resource_name: str
    unit: str
    remaining: float
    initial: float
    spent: float
    percentage: float  # remaining/initial * 100
    # LLM-specific (None for non-LLM resources)
    tokens_in: int | None = None
    tokens_out: int | None = None
    total_requests: int | None = None
    avg_cost_per_request: float | None = None
    burn_rate: float | None = None  # units per second

@dataclass
class AgentResourceMetrics:
    """All resource metrics for an agent."""
    agent_id: str
    resources: dict[str, ResourceMetrics]
    timestamp: float

class ResourceVisibilityConfig(BaseModel):
    """Per-agent visibility configuration."""
    resources: list[str] | None = None  # None = use system default
    detail_level: Literal["minimal", "standard", "verbose"] = "standard"
    see_others: bool = False
```

### Configuration Schema

**System level (config.yaml):**
```yaml
resources:
  visibility:
    enabled: true
    compute_metrics: [remaining, initial, spent, percentage,
                      tokens_in, tokens_out, total_requests,
                      avg_cost_per_request, burn_rate]
    defaults:
      resources: [llm_budget, disk]
      detail_level: standard
      see_others: false
```

**Agent level (agent.yaml):**
```yaml
resource_visibility:
  resources: [llm_budget]  # Override: only see LLM budget
  detail_level: verbose    # Full metrics
  see_others: false
```

### Detail Level Mapping

| Level | Metrics Included |
|-------|------------------|
| minimal | remaining |
| standard | remaining, initial, spent, percentage |
| verbose | All configured metrics |

### Changes Required

| File | Change |
|------|--------|
| `resource_metrics.py` | Create ResourceMetricsProvider class with get_agent_metrics() |
| `world.py` | Add ResourceMetricsProvider instance, include in StateSummary |
| `agent.py` | Load visibility config, filter metrics in build_prompt() |
| `loader.py` | Parse resource_visibility from agent.yaml |
| `models.py` | Add ResourceMetrics, AgentResourceMetrics, ResourceVisibilityConfig |
| `config_schema.py` | Add VisibilityConfig, VisibilityDefaults models |
| `config.yaml` | Add visibility section with defaults |
| `schema.yaml` | Document visibility configuration |

### Steps

1. **Add config schema** - VisibilityConfig in config_schema.py
2. **Create ResourceMetricsProvider** - src/world/resource_metrics.py
   - get_agent_metrics(agent_id, agents_dict, ledger, config) -> AgentResourceMetrics
   - Aggregate from Ledger.resources and Agent.llm.get_usage_stats()
   - Compute derived metrics (percentage, spent, burn_rate)
3. **Update StateSummary** - Add `resource_metrics` field alongside existing `balances`
4. **Update agent models** - ResourceVisibilityConfig in src/agents/models.py
5. **Update loader** - Parse resource_visibility from agent.yaml
6. **Update build_prompt()** - Filter and format metrics based on agent's visibility config
7. **Add system config defaults** - config.yaml visibility section
8. **Write tests** - Unit tests first (TDD), then integration
9. **Update documentation** - resources.md with visibility system

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_resource_metrics.py` | `test_get_agent_metrics_basic` | Returns metrics for agent with llm_budget |
| `tests/unit/test_resource_metrics.py` | `test_metrics_percentage_calculation` | percentage = remaining/initial * 100 |
| `tests/unit/test_resource_metrics.py` | `test_metrics_spent_calculation` | spent = initial - remaining |
| `tests/unit/test_resource_metrics.py` | `test_metrics_with_llm_stats` | Includes tokens_in, tokens_out from LLMProvider |
| `tests/unit/test_resource_metrics.py` | `test_burn_rate_calculation` | burn_rate = spent / elapsed_seconds |
| `tests/unit/test_resource_metrics.py` | `test_detail_level_minimal` | Only includes remaining |
| `tests/unit/test_resource_metrics.py` | `test_detail_level_standard` | Includes remaining, initial, spent, percentage |
| `tests/unit/test_resource_metrics.py` | `test_detail_level_verbose` | Includes all metrics |
| `tests/unit/test_resource_metrics.py` | `test_resource_filtering` | Only returns configured resources |
| `tests/unit/test_resource_metrics.py` | `test_invalid_resource_name_errors` | Raises error for unknown resource at startup |
| `tests/integration/test_resource_visibility.py` | `test_metrics_in_state_summary` | StateSummary includes resource_metrics |
| `tests/integration/test_resource_visibility.py` | `test_agent_sees_own_metrics` | Agent prompt includes their metrics |
| `tests/integration/test_resource_visibility.py` | `test_agent_visibility_config_override` | Per-agent config overrides system default |
| `tests/integration/test_resource_visibility.py` | `test_see_others_false` | Agent only sees own resources |
| `tests/integration/test_resource_visibility.py` | `test_see_others_true` | Agent sees all agents' resources |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_ledger.py` | Ledger behavior unchanged |
| `tests/unit/test_resource_manager.py` | ResourceManager unchanged |
| `tests/integration/test_resource_integration.py` | Resource system integration |
| `tests/unit/test_async_agent.py` | Agent behavior unchanged |
| `tests/e2e/test_smoke.py` | E2E smoke test |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Agent sees LLM budget | 1. Run simulation 2. Check agent prompt logs | Agent prompt shows remaining budget, percentage, token counts |
| Verbose detail level | 1. Set agent detail_level: verbose 2. Run | Agent sees burn_rate, avg_cost_per_request |
| Config override works | 1. Set system default: standard 2. Set agent: verbose 3. Run | Agent gets verbose despite system default |

```bash
# Run E2E verification
pytest tests/e2e/test_smoke.py -v
# Manual verification - check agent prompts in logs
python run.py --max-ticks 5
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 93`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] E2E verification passes: `pytest tests/e2e/test_smoke.py -v`

### Documentation
- [ ] `docs/architecture/current/resources.md` updated with visibility system
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`
- [ ] Config schema documented in `config/schema.yaml`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work
- [ ] Branch merged or PR created

---

## Notes

### Design Decisions

1. **Separate component (ResourceMetricsProvider) vs extending ResourceManager**
   - Chose separate component for clean separation of concerns
   - ResourceManager: state management (writes + state reads)
   - ResourceMetricsProvider: read-only aggregation for visibility
   - Easier to extend with new data sources (future APIs)

2. **Two-layer configuration**
   - System level: what's available, defaults
   - Agent level: per-agent overrides
   - Aligns with "maximum configurability" principle

3. **LLMProvider as data source**
   - Each agent already has own LLMProvider with get_usage_stats()
   - No new tracking needed - just expose existing data
   - Tracks: total_tokens, requests, total_cost, cache_hits, etc.

4. **Error on invalid resource names at startup**
   - Aligns with "fail loud" principle
   - Invalid config caught early, not at runtime

5. **Detail levels for progressive disclosure**
   - minimal: just remaining (low context overhead)
   - standard: core metrics for self-regulation
   - verbose: full metrics for advanced agents

### Future Extensions

- Historical burn rate (rolling window)
- Cost projections ("at current rate, budget exhausted in X seconds")
- Cross-agent resource comparison (if see_others enabled)
- Dashboard integration for visibility metrics
- Support for additional resource types as APIs are added
