# Plan 295: Resource-Gating Architecture Refactor

**Status:** 📋 Planned
**Priority:** High (architectural alignment)
**Blocked By:** None
**Blocks:** None

---

## Problem

The current architecture has a fundamental tension:

1. **"Everything is an artifact"** - unified ontology where agents are just artifacts with certain properties
2. **`has_loop` flag** - marks artifacts that get scheduled by the runner
3. **Scheduler-based execution** - artificial turn-taking rather than natural resource limits

This creates several issues:

### Issue 1: `has_loop` is an artificial distinction

From the kernel's perspective, any artifact could theoretically run a loop. The `has_loop` flag says "I'm registered with the scheduler" - which is a simulation concern, not an ontological property.

### Issue 2: Scheduler imposes artificial scarcity

The project thesis is "emergence under scarcity." But scarcity should come from physics (resource limits), not artificial turn-taking. Currently:
- Agents get scheduled in rounds
- Even if an agent has budget, it waits its turn
- This is imposed structure, not emergent behavior

### Issue 3: Only LLM budget is gated

We track `llm_budget` but real scarcity involves multiple resources:
- **Compute time** (CPU seconds)
- **Memory** (RAM)
- **Disk space** (artifact storage)
- **Bandwidth/IO** (network, file operations)
- **Attention** (other agents' willingness to respond)

A scheduler can't gate all these. We need resource-gating at point of consumption.

### Issue 4: `src/agents/` directory confusion

The directory conflates:
- Loop implementation code (kernel-level)
- Genesis agent configs (cold-start data)
- Components (cold-start data)

If agents are artifacts, why do they have a special directory?

---

## Proposed Solution

### Core Principle: Gate at Point of Consumption

Like an operating system:
- Process tries to allocate memory → check quota → allow or deny
- Process tries to write file → check disk quota → allow or deny
- Process tries to make LLM call → check budget → allow or deny

No scheduler required. Artifacts run freely, throttled naturally by resource limits.

### Design

#### 1. Generalized Resource Quotas (Ledger)

```python
# Current
principal_state = {
    "scrip": 100,
    "llm_budget": 1.0,
}

# Target
principal_state = {
    "scrip": 100,
    "quotas": {
        "llm_budget": 1.0,      # Dollars
        "compute_ms": 10000,    # Milliseconds of CPU
        "memory_mb": 100,       # MB of RAM
        "disk_mb": 50,          # MB of artifact storage
        "io_ops": 1000,         # IO operations per period
    }
}
```

#### 2. Resource Gating at Kernel Interface

Every kernel operation checks relevant quotas:

```python
class KernelInterface:
    def llm_call(self, principal_id, prompt, ...):
        # Check BEFORE the call
        if not self.ledger.has_quota(principal_id, "llm_budget", estimated_cost):
            raise InsufficientResourceError("llm_budget")

        result = self._execute_llm_call(prompt)

        # Charge AFTER the call (actual cost)
        self.ledger.deduct_quota(principal_id, "llm_budget", actual_cost)
        return result

    def write_artifact(self, principal_id, content, ...):
        size_mb = len(content) / 1_000_000
        if not self.ledger.has_quota(principal_id, "disk_mb", size_mb):
            raise InsufficientResourceError("disk_mb")

        # ... write artifact ...
        self.ledger.deduct_quota(principal_id, "disk_mb", size_mb)
```

#### 3. Remove `has_loop` from Artifact Model

```python
# Current
@dataclass
class Artifact:
    has_standing: bool  # Can own things
    has_loop: bool      # Gets scheduled

# Target
@dataclass
class Artifact:
    has_standing: bool  # Can own things
    # has_loop removed - not an ontological property
```

#### 4. Artifacts Self-Execute Based on Resources

Instead of scheduler calling `agent.think()`:

```python
# Option A: Event-driven
class ArtifactLoop:
    async def run(self, artifact_id):
        while True:
            try:
                await self.kernel.think(artifact_id)
            except InsufficientResourceError:
                await self.wait_for_resources()

# Option B: Continuous with natural throttling
class ArtifactLoop:
    def run(self, artifact_id):
        while self.kernel.has_any_quota(artifact_id):
            self.kernel.think(artifact_id)
        # Naturally stops when out of resources
```

#### 5. Optional Simulation Harness (Not Core)

The "runner" becomes an optional simulation tool:
- Can impose artificial fairness (round-robin) for experiments
- Can add observability hooks
- Not required for the kernel to function
- Default mode: artifacts run freely

#### 6. Restructure `src/agents/`

```
src/
  loops/                    # Code that enables artifacts to self-execute
    artifact_loop.py        # Generic loop implementation
    think.py               # Think/act cycle

config/
  genesis/
    agents/                # Genesis agent configs (formerly src/agents/*)
      alpha_prime.yaml
      discourse_analyst.yaml
    components/            # Genesis components (formerly src/agents/_components)
      behaviors/
      telos/
```

---

## Migration Path

### Phase 1: Generalize Resource Tracking
- Add `quotas` dict to principal state
- Migrate `llm_budget` into quotas
- Add disk_mb tracking (artifact sizes)
- No behavior change yet

### Phase 2: Gate at Kernel Interface
- Add quota checks to `write_artifact`, `invoke_artifact`
- Add `InsufficientResourceError`
- Artifacts start getting denied when over quota

### Phase 3: Remove `has_loop`
- Remove from artifact model
- Refactor runner to not depend on it
- Artifacts opt-in to execution via registration

### Phase 4: Restructure Directories
- Move genesis configs to `config/genesis/`
- Rename `src/agents/` to `src/loops/` or similar
- Update imports and references

### Phase 5: Event-Driven Execution (Optional)
- Replace scheduler with event loop
- Artifacts run when they have resources
- Add fairness policies as configuration

---

## Open Questions

1. **Compute time tracking**: How do we measure CPU time per artifact? Python doesn't make this easy. May need approximation or external monitoring.

2. **Memory tracking**: How do we attribute RAM to specific artifacts? May need to track "owned objects" rather than actual memory.

3. **Fairness without scheduler**: How do we prevent one artifact from hogging all resources? Options:
   - Rate limits per period (max 10 LLM calls per minute)
   - Priority queues
   - Let it emerge (greedy agents burn out fast)

4. **Backwards compatibility**: How do we migrate existing simulations? May need compatibility shim during transition.

5. **Genesis bootstrap**: If there's no scheduler, how does the system start? Artifacts need to be "kicked" initially.

---

## Tests Required

| Test | What It Verifies |
|------|------------------|
| `test_quota_check_before_llm_call` | LLM calls rejected when insufficient quota |
| `test_quota_deduction_after_llm_call` | Actual cost deducted after call |
| `test_disk_quota_enforced` | Large artifacts rejected when over quota |
| `test_artifact_runs_until_exhausted` | Artifact naturally stops when resources depleted |
| `test_no_has_loop_property` | Artifact model doesn't have has_loop |

---

## Verification

- [ ] Resource quotas tracked in ledger
- [ ] Kernel interface gates on quotas
- [ ] `has_loop` removed from artifact model
- [ ] Artifacts can run without scheduler
- [ ] Genesis configs moved to `config/genesis/`
- [ ] All existing tests pass

---

## Notes

This is a significant architectural change. The goal is alignment with "physics-first" and "emergence over prescription" principles. Scarcity should emerge from resource limits, not from artificial scheduling.

The scheduler isn't "wrong" - it's a pragmatic solution. But it imposes structure rather than letting it emerge. This refactor moves toward a purer model where the kernel provides physics and artifacts deal with scarcity naturally.
