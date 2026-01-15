# V1 Acceptance Criteria

This document defines what "V1" means for the Agent Ecology project.

**V1 = Minimal Viable Agent Ecology** - sufficient to demonstrate emergent collective capability under resource constraints.

---

## Core Capabilities (Must Have for V1)

### 1. Multi-Agent Execution

**Requirement:** Multiple agents can run simultaneously without interference.

**Acceptance Criteria:**
- [x] 2+ agents execute actions in the same simulation
- [x] Each agent's balance is tracked separately
- [x] No crashes from concurrent execution
- [x] Genesis artifacts accessible by all agents

**Test:** `test_multi_agent_execution`

### 2. Artifact System

**Requirement:** Agents can discover, create, read, and invoke artifacts.

**Acceptance Criteria:**
- [x] genesis_store lists discoverable artifacts
- [x] Agents can create new artifacts via store.write
- [x] Created artifacts are retrievable
- [x] Artifact ownership is tracked correctly
- [x] Artifact methods (interfaces) are invocable

**Tests:** `test_artifact_discovery`, `test_artifact_creation`, `test_artifact_invocation`

### 3. Economic Primitives

**Requirement:** Scrip transfers work and balances are tracked correctly.

**Acceptance Criteria:**
- [x] Transfers reduce sender balance
- [x] Transfers increase receiver balance
- [x] Total scrip is conserved (no creation/destruction)
- [x] Balance queries return accurate values

**Test:** `test_scrip_transfer`

### 4. Resource Constraints

**Requirement:** Rate limiting and quotas are enforced.

**Acceptance Criteria:**
- [x] Rate limiter exists and is configurable
- [x] Simulation runs with rate limiting enabled
- [x] Exceeding rate limits has observable effect (delay/block)
- [x] No crashes from rate limit enforcement

**Test:** `test_resource_rate_limiting`

### 5. Coordination

**Requirement:** Contracts and escrow enable trustless coordination.

**Acceptance Criteria:**
- [x] genesis_escrow artifact exists
- [x] Deposit: Artifact can be listed for sale
- [x] Purchase: Buyer can buy listed artifact
- [x] Ownership transfers to buyer on purchase
- [x] Scrip transfers from buyer to seller on purchase

**Test:** `test_escrow_coordination`

### 6. Observability

**Requirement:** Actions are logged and traceable.

**Acceptance Criteria:**
- [x] Event log records all actions
- [x] Events have timestamps
- [x] Events are retrievable via logger.read_recent()
- [x] Tick boundaries are logged

**Test:** `test_action_logging`

---

## Not in V1 (Explicitly Excluded)

These features are planned for post-V1:

| Feature | Plan | Why Excluded |
|---------|------|--------------|
| Agent rights trading | #8 | Adds complexity without core value |
| Scrip debt contracts | #9 | Requires trust model refinement |
| Memory persistence | #10 | Agent can function without it |
| Library installation | #29 | Security complexity |
| LLM budget trading | #30 | Requires robust metering |

---

## Verification

### Running V1 Acceptance Tests

```bash
# All V1 acceptance tests (requires real LLM)
pytest tests/e2e/test_v1_acceptance.py -v --run-external

# Individual test
pytest tests/e2e/test_v1_acceptance.py::TestV1MultiAgentExecution -v --run-external
```

### Cost Estimate

V1 acceptance test suite costs approximately **$0.05-0.15** per run (real LLM calls).

### Pass Criteria

**V1 is complete when:**
1. All tests in `test_v1_acceptance.py` pass with `--run-external`
2. No smoke test regressions (`test_smoke.py` still passes)
3. No real E2E regressions (`test_real_e2e.py` still passes)

---

## V1 Declaration

When V1 acceptance tests pass, the project can be declared **V1 Complete**.

This does not mean "done" - it means the minimal viable agent ecology is functional and can demonstrate emergent collective capability.

Post-V1 work focuses on:
- Expanding capabilities (trading, memory, etc.)
- Improving robustness
- Performance optimization
- Production readiness

---

## References

- [Plan #51: V1 Acceptance Criteria](docs/plans/51_v1_acceptance.md)
- [Test File](tests/e2e/test_v1_acceptance.py)
- [README.md](README.md) - Full philosophy and goals
