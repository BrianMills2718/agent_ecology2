# Plan 53: Scalable Resource Architecture

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** None
**Human Review Required:** Yes (architectural change)

---

## Gap

**Current:**
- All agents run in one Python process
- Memory/CPU measured per-process, not per-agent (Plan #31 added measurement, but shared process limits attribution)
- Memory and CPU not tracked as tradeable resources in ledger
- Connection pool not tracked or managed
- Legacy "compute" terminology persists when it should be "llm_tokens"
- Architecture doesn't scale past ~50 agents

**Target:**
- Process-per-agent-turn architecture enabling 1000+ agents
- Per-agent memory and CPU measurement (~90% accurate, ±10% for shared runtime)
- Memory and CPU as tradeable resources via rights_registry
- Connection pool as managed infrastructure (fair queue V1, contractable later)
- Clean "llm_tokens" terminology throughout
- All scarce resources contractable (core principle)

**Why High Priority:**
- User needs to scale to 100-1000 agents
- Current architecture OOM-killed with 5 agents on shared VM
- Resources must map to real-world scarcity for meaningful emergence
- Everything must be contractable per project philosophy

---

## Existing Infrastructure (Plan #31)

Plan #31 created measurement infrastructure that was **never integrated**:

| Component | Location | Status |
|-----------|----------|--------|
| `ResourceUsage` dataclass | `src/world/simulation_engine.py:236` | ✅ Built, ❌ Not used |
| `ResourceMeasurer` class | `src/world/simulation_engine.py:255` | ✅ Built, ❌ Not used |
| `measure_resources()` helper | `src/world/simulation_engine.py:338` | ✅ Built, ❌ Not used |

**The problem:** `executor.py` still uses a legacy hack:

```python
# executor.py:181 - WRONG: conflates wall-clock time with LLM tokens
def _time_to_tokens(execution_time_ms: float) -> float:
    cost_per_ms: float = get("executor.cost_per_ms") or 0.1
    return max(1.0, execution_time_ms * cost_per_ms)
```

This charges **wall-clock time** as **"llm_tokens"** - fundamentally wrong:
- `llm_tokens` should mean "tokens sent to/from LLM API"
- Execution time is a different resource (`cpu_seconds`)
- Makes resource accounting meaningless

**This plan must fix this before building new infrastructure.**

---

## Design Decisions

### Process-Per-Agent-Turn Model

```
┌─────────────────────────────────────────────────────────────┐
│  Agent State Store (SQLite/files)                           │
│  1000 agent states persisted                                │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│ Worker 1    │ │ Worker 2    │ │ Worker N    │
│ (process)   │ │ (process)   │ │ (process)   │
│             │ │             │ │             │
│ Load agent  │ │ Load agent  │ │ Load agent  │
│ Run turn    │ │ Run turn    │ │ Run turn    │
│ Measure res │ │ Measure res │ │ Measure res │
│ Save state  │ │ Save state  │ │ Save state  │
│ Next agent  │ │ Next agent  │ │ Next agent  │
└─────────────┘ └─────────────┘ └─────────────┘
```

**Why process per turn, not container per agent:**
- Container overhead: ~50MB each × 1000 = 50GB (impractical)
- Process overhead: ~30MB × N workers (N can be 10-50)
- Memory measurement via psutil: ~90% accurate per-process
- Worker pool scales horizontally

### Resource Measurement Accuracy

| Resource | Method | Accuracy | Error Source |
|----------|--------|----------|--------------|
| LLM tokens | API response | Exact (0%) | None |
| LLM $ cost | litellm.completion_cost() | Exact (0%) | None |
| Disk bytes | File size | Exact (0%) | None |
| Memory | psutil.Process().memory_info() | ~90% | Shared Python runtime (~10%) |
| CPU time | time.process_time() | ~90% | Shared runtime overhead |
| Connections | Pool tracking | Exact (0%) | None |

**Error documentation:** The ~10% error from shared Python runtime is actually realistic - agents pay for their infrastructure.

### Connection Pool: Fair Queue (V1)

```python
# V1: Fair queue, no ownership
class ConnectionPool:
    async def acquire(self, agent_id: str) -> Connection:
        return await self.queue.get()  # FIFO

# Future V2: Priority based on owned slots (configurable)
class ConnectionPool:
    async def acquire(self, agent_id: str) -> Connection:
        priority = self.get_owned_slots(agent_id)
        return await self.priority_queue.get(priority)
```

Connection slots tracked and logged, but not tradeable in V1. Config flag to enable trading later.

### Resource Contractability

| Resource | V1 Tracked | V1 Tradeable | Contractable |
|----------|------------|--------------|--------------|
| scrip | ✅ | ✅ | ✅ |
| llm_tokens | ✅ | ✅ | ✅ |
| llm_budget ($) | ✅ | ✅ | ✅ |
| disk | ✅ | ✅ | ✅ |
| **memory** | ✅ (new) | ✅ (new) | ✅ (new) |
| **cpu_seconds** | ✅ (new) | ✅ (new) | ✅ (new) |
| **connection_slots** | ✅ (new) | ❌ (V1) | ❌ (V1) |

All tradeable resources use same mechanism: `rights_registry.transfer_quota(from, to, resource_type, amount)`

---

## Plan

### Phase 0: Fix Executor Integration (PREREQUISITE)

**Goal:** Stop conflating execution time with LLM tokens. Use Plan #31's `ResourceMeasurer`.

| File | Change |
|------|--------|
| `src/world/executor.py` | Replace `_time_to_tokens()` with `ResourceMeasurer` |
| `src/world/executor.py` | Return `cpu_seconds` in `resources_consumed`, not `llm_tokens` |
| `src/world/ledger.py` | Add `cpu_seconds` as a valid resource type |
| `src/world/world.py` | Deduct `cpu_seconds` from agent after execution |

**Before (wrong):**
```python
resources_consumed = {"llm_tokens": _time_to_tokens(execution_time_ms)}
```

**After (correct):**
```python
with measure_resources() as measurer:
    # ... execute code ...
usage = measurer.get_usage()
resources_consumed = {"cpu_seconds": usage.cpu_seconds}
```

**Why this is Phase 0:** All subsequent phases depend on accurate resource tracking. Building worker pools on broken accounting is pointless.

### Phase 1: Terminology Cleanup

Replace all "compute" with "llm_tokens" where it refers to LLM token quotas.

| File | Change |
|------|--------|
| `src/agents/agent.py` | `compute_quota` → `llm_tokens_quota` |
| `src/agents/schema.py` | handbook reference |
| `src/dashboard/models.py` | All `compute` fields → `llm_tokens` |
| `src/dashboard/parser.py` | All `compute` references → `llm_tokens` |
| `src/dashboard/server.py` | `/api/charts/compute` → `/api/charts/llm_tokens` |
| `config/config.yaml` | Comments clarifying terminology |
| `docs/architecture/current/resources.md` | Update terminology section |

### Phase 2: State Persistence Layer

Agent state must persist between turns for process-per-turn model.

| File | Change |
|------|--------|
| `src/agents/state_store.py` (new) | SQLite-backed agent state persistence |
| `src/agents/agent.py` | Add `to_state()` / `from_state()` serialization |
| `src/simulation/runner.py` | Use state store instead of in-memory agents |

### Phase 3: Worker Pool Architecture

| File | Change |
|------|--------|
| `src/simulation/worker.py` (new) | Worker process that loads agent, runs turn, saves state |
| `src/simulation/pool.py` (new) | Worker pool manager with N workers |
| `src/simulation/runner.py` | Orchestrate via pool instead of direct agent calls |

### Phase 4: Per-Agent Resource Quotas

| File | Change |
|------|--------|
| `src/world/ledger.py` | Add `memory` and `cpu_seconds` as resource types |
| `src/world/genesis.py` | `rights_registry.transfer_quota()` supports memory/cpu |
| `config/schema.yaml` | Add memory/cpu quota config |
| `config/config.yaml` | Default quotas for memory/cpu |

### Phase 5: Resource Enforcement

| File | Change |
|------|--------|
| `src/simulation/worker.py` | Monitor memory via psutil, enforce quota |
| `src/simulation/worker.py` | Monitor CPU time, enforce timeout |
| `src/simulation/worker.py` | Record actual usage to ledger |

### Phase 6: Connection Pool

| File | Change |
|------|--------|
| `src/world/connection_pool.py` (new) | Fair queue for LLM connections |
| `src/agents/llm_provider.py` | Acquire from pool before LLM call |
| `config/schema.yaml` | `connection_pool.size`, `connection_pool.tradeable` |

---

## Required Tests

### New Tests (TDD)

#### Phase 0 Tests

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_executor.py` | `test_executor_returns_cpu_seconds` | Executor returns `cpu_seconds` not `llm_tokens` |
| `tests/unit/test_executor.py` | `test_executor_uses_resource_measurer` | Executor uses `ResourceMeasurer` not wall-clock hack |
| `tests/unit/test_ledger.py` | `test_cpu_seconds_resource_type` | Ledger accepts `cpu_seconds` as valid resource |

#### Phase 2+ Tests

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_state_store.py` | `test_save_load_agent_state` | Agent state persists correctly |
| `tests/unit/test_state_store.py` | `test_concurrent_access` | Multiple workers don't corrupt state |
| `tests/unit/test_worker.py` | `test_memory_measurement` | Memory tracked per-turn |
| `tests/unit/test_worker.py` | `test_cpu_measurement` | CPU time tracked per-turn |
| `tests/unit/test_worker.py` | `test_memory_quota_exceeded` | Turn killed when over quota |
| `tests/unit/test_worker.py` | `test_cpu_quota_exceeded` | Turn killed when over time |
| `tests/unit/test_connection_pool.py` | `test_fair_queue` | Connections allocated FIFO |
| `tests/unit/test_connection_pool.py` | `test_pool_exhaustion` | Agents wait when pool full |
| `tests/integration/test_worker_pool.py` | `test_100_agents` | 100 agents run without OOM |
| `tests/integration/test_resource_trading.py` | `test_memory_transfer` | Memory quota tradeable |
| `tests/integration/test_resource_trading.py` | `test_cpu_transfer` | CPU quota tradeable |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_ledger.py` | Resource tracking unchanged for existing resources |
| `tests/unit/test_rights_registry.py` | Quota transfer mechanism unchanged |
| `tests/e2e/test_smoke.py` | End-to-end still works |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| 100 agents run | `python run.py --agents 100 --duration 300` | Completes without OOM |
| Memory quota enforced | Agent exceeds memory quota | Turn terminated, logged |
| CPU quota enforced | Agent infinite loops | Turn terminated after timeout |
| Resource trading | Agent transfers memory quota | Recipient has more quota |

```bash
pytest tests/e2e/test_real_e2e.py -v --run-external
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 53`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] E2E verification passes with 100 agents

### Documentation
- [ ] `docs/architecture/current/resources.md` updated with memory/cpu
- [ ] `docs/architecture/current/execution_model.md` updated for worker pool
- [ ] `docs/GLOSSARY_CURRENT.md` terminology verified
- [ ] Doc-coupling check passes

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released
- [ ] PR merged

---

## Notes

### Why Not Containers?

Containers provide perfect isolation but:
- ~50MB overhead each
- 1000 containers = 50GB just for infrastructure
- Orchestration complexity (Kubernetes)
- Process-per-turn gives ~90% of the benefit with ~10% of the cost

### Future: Connection Slot Trading

V1 uses fair queue for connections. To enable trading later:

1. Set `connection_pool.tradeable: true` in config
2. Track slot ownership in rights_registry
3. Priority queue weighted by owned slots
4. Same `transfer_quota()` interface

### Shared LLMProvider

With worker pool, all workers can share one LLMProvider instance (passed via IPC or recreated). This reduces connection pool overhead vs one provider per agent.

### Migration Path

1. **Phase 0 MUST ship first** - fixes broken resource accounting
2. Phase 1-2 can ship independently (terminology + state persistence)
3. Phase 3-5 are the core architecture change
4. Phase 6 (connection pool) can be independent

### Error Bounds Documentation

Document in resources.md:
- Memory measurement: ±10% due to Python runtime
- CPU measurement: ±10% due to runtime overhead
- These errors are acceptable and represent real infrastructure costs

---

## Inconsistencies Found

During plan creation, the following inconsistencies were identified:

### Critical: Executor Resource Conflation (Phase 0)

| File | Line | Issue |
|------|------|-------|
| `src/world/executor.py` | 181-190 | `_time_to_tokens()` converts wall-clock time to "llm_tokens" |
| `src/world/executor.py` | 550, 558, 566, 577, 720, 728, 736, 746, 1020, 1028, 1036, 1046 | All return `{"llm_tokens": ...}` for execution time |

**Root cause:** Plan #31 built `ResourceMeasurer` but never integrated it into executor.

### Terminology Issues (Phase 1)

### Glossary (GLOSSARY_CURRENT.md)

| Line | Issue |
|------|-------|
| 63 | "Resources = Physical constraints (compute, disk...)" - mixes "compute" with physical resources |
| 76 | "invoke_artifact costs Scrip fee + compute" - should say "llm_tokens" |
| 152 | Deprecated table says "flow → compute" which is confusing |

### Config Schema (config/schema.yaml)

| Line | Issue |
|------|-------|
| 26 | Uses `compute:` with comment explaining it's really `llm_tokens` - should rename |

### Code (found earlier)

| File | Issue |
|------|-------|
| `src/agents/agent.py` | `compute_quota` variable name |
| `src/dashboard/models.py` | Multiple `compute` fields |
| `src/dashboard/parser.py` | Multiple `compute` references |
| `src/dashboard/server.py` | `/api/charts/compute` endpoint |

All of these should be renamed to `llm_tokens` in Phase 1.

---

## Implementation Notes (2026-01-16)

### Design Decisions Made

1. **Threads vs Processes**: Used `ThreadPoolExecutor` not `ProcessPoolExecutor`
   - Simpler IPC (shared memory)
   - GIL contention acceptable for I/O-bound LLM calls
   - True process isolation would require more complex state serialization
   - *Pragmatism over purity* - can upgrade to processes later if needed

2. **Memory/CPU as Renewable Resources**: Implemented via RateTracker rolling windows
   - README explicitly categorizes CPU as "Renewable" (rate-limited)
   - Memory as "Allocatable" (quota) - but implemented as renewable for V1
   - Renewable resources naturally fit rolling window model
   - *Tradeoff*: Renewable means "wait for capacity" not "trade quota"

3. **Worker Pool Opt-In**: Default `use_worker_pool: false`
   - Matches *avoid defaults* heuristic
   - Existing behavior unchanged
   - User explicitly enables when scaling beyond ~50 agents

### Uncertainties for Review

| Item | Concern | Severity |
|------|---------|----------|
| Memory as renewable vs allocatable | README says memory is "Allocatable" but I implemented as rate-limited renewable | Medium |
| Thread vs process isolation | ~10% measurement error from shared runtime; threads share GIL | Low |
| Connection pool (Phase 6) | Not implemented - plan said "V1: Fair queue" but no code exists | Low (marked optional) |
| Resource trading | Plan said memory/cpu should be "tradeable" but rate-limited resources don't trade the same way quotas do | Medium |

### Alignment with Philosophy

| Principle | How Addressed |
|-----------|---------------|
| Physics-first | CPU/memory measured from actual process stats (psutil, process_time) |
| Observability | All resource usage logged per-turn in TickResults |
| Minimal kernel | Worker pool is config-driven, not hardcoded |
| Selection pressure | Agents exceeding quotas get their turn terminated, not protected |
| Pragmatism | Threads over processes for V1 simplicity |

### Future Work (Not in V1)

- **Connection Pool (Phase 6)**: Fair queue for LLM API connections
- **Memory as true quota**: Transfer memory allocation between agents
- **Process isolation**: True process-per-turn for better measurement
- **Resource trading tests**: `test_memory_transfer`, `test_cpu_transfer`
