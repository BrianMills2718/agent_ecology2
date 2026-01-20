# Gap 113: Contractable Model Access

**Status:** ✅ Complete

**Verified:** 2026-01-20T03:39:05Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-20T03:39:05Z
tests:
  unit: 1862 passed, 9 skipped, 3 warnings in 72.46s (0:01:12)
  e2e_smoke: PASSED (12.62s)
  e2e_real: skipped (--skip-real-e2e)
  doc_coupling: passed
commit: 663c386
```
**Priority:** **High**
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** All agents use a single globally-configured LLM model. When rate limits are hit, agents simply wait or fail. There's no scarcity-driven behavior around model access, and agents cannot differentiate by model capability or trade access rights.

**Target:** LLM model access becomes a scarce, tradeable resource. Each model has its own rate limits (reflecting real API constraints). Agents receive initial quotas and can trade/contract for model access. This creates emergence: markets for premium models, specialists who arbitrage access, and strategic model selection.

**Why High:** This transforms a major resource (LLM calls) into an emergent economic system. Aligns with core project principles:
- **Physics-first**: Real API rate limits become in-simulation scarcity
- **Emergence over prescription**: Agents figure out which models to use
- **Contracts are flexible**: Model access becomes contractable

---

## References Reviewed

- `src/world/rate_tracker.py` - Existing rolling-window rate limiter
- `src/world/resource_manager.py` - Resource quota management
- `docs/adr/0003-contracts-can-do-anything.md` - Contracts can call LLM, invoker pays
- `docs/adr/0008-token-bucket-rate-limiting.md` - Token bucket design
- `config/config.yaml` - Current single-model configuration
- `src/agents/agent.py` - Where LLM calls originate

---

## Files Affected

- src/world/genesis/model_registry.py (create) - Genesis artifact for model registration
- src/world/genesis/factory.py (modify) - Create genesis_model_registry
- src/world/genesis/__init__.py (modify) - Export GenesisModelRegistry
- src/world/model_access.py (create) - Model access tracking and quota management
- src/config_schema.py (modify) - Add ModelRegistryConfig and models config
- src/agents/agent.py (modify) - Model selection logic
- config/config.yaml (modify) - Multi-model configuration
- config/schema.yaml (modify) - Schema for model configs
- tests/unit/test_model_access.py (create) - Unit tests
- tests/integration/test_model_contracts.py (create) - Contract integration tests

---

## Plan

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    genesis_model_registry                    │
│  Methods: list_models, get_quota, request_access, release   │
├─────────────────────────────────────────────────────────────┤
│  Model              │ Global Limit │ Cost/1K │ Properties   │
│  gemini-2.5-flash   │ 50k rpd      │ 0.002   │ fast, cheap  │
│  gemini-3-flash     │ 10k rpd      │ 0.001   │ experimental │
│  claude-haiku       │ 100k rpd     │ 0.003   │ reliable     │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      ModelAccessManager                      │
│  - Tracks per-agent quotas for each model                   │
│  - Integrates with RateTracker for rolling windows          │
│  - Supports quota transfer/leasing via contracts            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                         Agent                                │
│  - Selects model based on quota availability                │
│  - Can specify fallback preferences                         │
│  - Can trade/contract for additional model access           │
└─────────────────────────────────────────────────────────────┘
```

### Phase 1: Model Registry Genesis Artifact

Create `genesis_model_registry` with methods:

```python
# List available models and their properties
list_models() -> list[ModelInfo]

# Check agent's current quota for a model
get_quota(agent_id: str, model: str) -> QuotaInfo

# Request access to a model (may require payment/contract)
request_access(agent_id: str, model: str, amount: float) -> bool

# Release unused quota back to pool
release_quota(agent_id: str, model: str, amount: float) -> bool

# Transfer quota to another agent (enables trading)
transfer_quota(from_agent: str, to_agent: str, model: str, amount: float) -> bool
```

### Phase 2: Model Access Manager

Integrate with existing ResourceManager/RateTracker:

```python
class ModelAccessManager:
    """Manages per-agent model access quotas.

    Each model is treated as a renewable resource with:
    - Global limit (reflecting real API rate limits)
    - Per-agent quotas (tradeable)
    - Rolling window tracking
    """

    def has_capacity(self, agent_id: str, model: str, tokens: int) -> bool:
        """Check if agent has quota for this model."""

    def consume(self, agent_id: str, model: str, tokens: int) -> None:
        """Record usage against agent's quota."""

    def get_available_models(self, agent_id: str) -> list[str]:
        """Get models agent has quota for, ordered by availability."""
```

### Phase 3: Agent Model Selection

Update Agent to select models dynamically:

```python
# In agent.py
def _select_model(self) -> str:
    """Select best available model based on quota."""
    available = self.model_access.get_available_models(self.agent_id)
    if not available:
        raise NoModelQuotaError(f"{self.agent_id} has no model quota")

    # Use preferred model if available, else fallback
    for preferred in self.model_preferences:
        if preferred in available:
            return preferred
    return available[0]  # Best available
```

### Phase 4: Contracts for Model Access

Enable model access trading via contracts:

```python
# Example contract: Sell model access
{
    "type": "model_access_lease",
    "model": "gemini-2.5-flash",
    "amount": 1000,  # tokens per window
    "price": 10,     # scrip
    "duration": 3600 # seconds
}
```

Agents can:
- Create contracts offering model access
- Purchase access from others
- Lease access temporarily

### Configuration

```yaml
# config/config.yaml
models:
  available:
    - id: "gemini/gemini-2.5-flash"
      global_limit_rpd: 50000
      cost_per_1k_input: 0.002
      cost_per_1k_output: 0.006
      properties: ["fast", "cheap"]

    - id: "gemini/gemini-3-flash"
      global_limit_rpd: 10000
      cost_per_1k_input: 0.001
      cost_per_1k_output: 0.003
      properties: ["experimental"]

  allocation:
    strategy: "equal"  # or "auction", "fixed"
    initial_per_agent: 0.2  # 20% of global limit each

  fallback:
    enabled: true
    order: ["gemini-2.5-flash", "gemini-3-flash"]
```

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_model_access.py` | `test_quota_allocation` | Agents receive initial quotas |
| `tests/unit/test_model_access.py` | `test_quota_consumption` | Usage deducted from quota |
| `tests/unit/test_model_access.py` | `test_quota_exhaustion` | Error when quota exhausted |
| `tests/unit/test_model_access.py` | `test_quota_transfer` | Agents can transfer quota |
| `tests/unit/test_model_access.py` | `test_fallback_model` | Falls back when primary exhausted |
| `tests/integration/test_model_contracts.py` | `test_model_access_contract` | Contract grants model access |
| `tests/integration/test_model_contracts.py` | `test_model_access_market` | Agents trade model access |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_rate_tracker.py` | Rate limiting unchanged |
| `tests/integration/test_runner.py` | Simulation still works |
| `tests/e2e/test_real_e2e.py` | Full E2E with real LLM |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Model quota enforcement | 1. Configure low quota 2. Agent makes many calls 3. Observe fallback/error | Agent uses fallback or gets clear error |
| Model access trading | 1. Agent A has excess quota 2. Agent B needs access 3. Trade via contract | B acquires A's quota, both balances change |

```bash
pytest tests/e2e/test_real_e2e.py -v --run-external
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 113`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] **E2E verification passes:** `pytest tests/e2e/test_real_e2e.py -v --run-external`

### Documentation
- [ ] `docs/architecture/current/resources.md` updated
- [ ] Genesis artifact documented
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released
- [ ] Branch merged or PR created

---

## Notes

**Emergence opportunities:**
- **Model arbitrage**: Agent accumulates quota when cheap, sells when scarce
- **Specialization**: One agent becomes "model broker"
- **Quality differentiation**: Agents choose models based on task importance
- **Market signals**: Model prices indicate demand/value

**Design decisions:**
- Global limits reflect real API constraints (physics-first)
- Initial allocation is configurable (equal, auction, fixed)
- Contracts enable trading without kernel changes
- Fallback is optional (agents can choose to fail instead)

**Relationship to existing systems:**
- Builds on `RateTracker` for rolling window limits
- Uses `ResourceManager` patterns for quota tracking
- Integrates with contract system for trading
- `genesis_model_registry` follows genesis artifact patterns

**Future extensions:**
- Model quality scoring (track success rates)
- Dynamic pricing based on demand
- Model capability discovery (agents learn which models work for what)
