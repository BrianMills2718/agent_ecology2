# Implementation Plan: Two-Layer Resource Model

## Overview

Implement the separation of **scarce resources** (physical limits) from **scrip** (economic currency), with contract-defined resource payment policies.

---

## Files to Modify

### Core Implementation

| File | Changes |
|------|---------|
| `src/world/artifacts.py` | Add `resource_policy` field to Artifact dataclass |
| `src/world/actions.py` | Add `resources_consumed` and `charged_to` to ActionResult |
| `src/world/world.py` | Route resource costs based on artifact's resource_policy |
| `src/world/executor.py` | Measure CPU/memory during code execution |
| `src/world/ledger.py` | Already supports generic resources (minimal changes) |
| `src/world/genesis.py` | Define resource_policy for genesis artifacts |

### Configuration

| File | Changes |
|------|---------|
| `config/config.yaml` | Remove arbitrary action costs, add resource measurement config |
| `config/schema.yaml` | Document resource_policy field, remove fake costs |

### Agent Interface

| File | Changes |
|------|---------|
| `src/agents/agent.py` | Show resources_consumed in action feedback |
| `src/agents/schema.py` | Update action schema to include resource_policy for writes |

### Simulation

| File | Changes |
|------|---------|
| `src/simulation/runner.py` | Track and display resource consumption per action |
| `src/world/simulation_engine.py` | May need updates for resource routing |

### Tests

| File | Changes |
|------|---------|
| `tests/test_artifacts.py` | Test resource_policy field |
| `tests/test_world.py` | Test resource routing (caller_pays vs owner_pays) |
| `tests/test_resource_measurement.py` | NEW: Test actual measurement |
| `tests/test_integration.py` | Update for new action result format |

### Documentation (DONE)

| File | Status |
|------|--------|
| `docs/RESOURCE_MODEL.md` | ✅ Updated |
| `docs/AGENT_HANDBOOK.md` | ✅ Updated |

---

## Implementation Phases

### Phase 1: Artifact Resource Policy

1. Add `resource_policy: str = "caller_pays"` to Artifact dataclass
2. Update `write_artifact` action to accept resource_policy
3. Update artifact serialization/deserialization
4. Tests

### Phase 2: Resource Consumption Tracking

1. Add `resources_consumed: dict[str, float]` to ActionResult
2. Add `charged_to: str` to ActionResult
3. Update all action handlers to populate these fields
4. For now, track only `llm_tokens` and `disk_bytes`
5. Tests

### Phase 3: Resource Routing

1. Modify `execute_action` in world.py:
   - For invoke_artifact: check artifact.resource_policy
   - Route resource deduction to correct principal
   - Handle failure cases (payer has insufficient resources)
2. Tests

### Phase 4: Remove Arbitrary Costs

1. Remove `costs.actions.*` from config (the fake compute costs)
2. Remove action cost checking from world.py
3. Thinking cost remains (this IS real resource consumption)
4. Update tests

### Phase 5: Genesis Artifacts (DECISION MADE)

Genesis method costs should be **compute (resources)**, not scrip. This is cleaner:
- **Compute** = cost of doing anything (physical constraint)
- **Scrip** = purely economic, only flows agent↔agent

**Scrip only flows for:**
1. Agent↔agent trades (artifact prices, transfers)
2. Oracle auction bids (bidding for submission slots)
3. Oracle minting (reward for accepted submissions)

**Implementation:**
1. Remove scrip costs from genesis method configs (transfer: 0, submit: 0, etc.)
2. Genesis invocations consume compute like all other actions
3. Update genesis.py to NOT deduct scrip for method calls
4. Tests

### Phase 6: CPU/Memory Measurement (Deferred)

1. Add measurement to executor.py using `time.process_time()` and `tracemalloc`
2. Add to resources_consumed
3. Define quotas and enforcement
4. Tests

---

## Uncertainties & Questions

### 1. Genesis Artifacts Resource Policy ✅ RESOLVED

**Question**: Should genesis artifacts have a resource_policy, or are they special?

**Decision**: Genesis artifacts are special - they have **no owner** and consume **no resources from agents**.

Why:
- Genesis methods are system infrastructure, not agent services
- They don't consume LLM tokens or disk (they're just ledger lookups/updates)
- The "cost" of genesis invocations is already captured in the action's compute cost
- Scrip is removed from genesis entirely (see Question #7)

Genesis artifacts effectively have `resource_policy: "system_pays"` - the system absorbs any infrastructure cost.

### 2. What Happens with owner_pays If Owner Has No Resources?

**Question**: If artifact has `owner_pays` but owner's resource balance is 0, what happens?

**Options**:
- A) Reject invocation with "service unavailable"
- B) Fall back to caller_pays
- C) Allow negative balance (debt)

**My lean**: Option A - Clean failure, owner must maintain resources to offer service.

### 3. Chained Invocations

**Question**: If Artifact A calls Artifact B internally, who pays for B's resources?

**Options**:
- A) Original caller pays all
- B) Each artifact's policy applies (A's for A, B's for B)
- C) A pays for B (A is the "caller" of B)

**My lean**: Option C - A is invoking B, so A is the caller. This creates interesting dynamics where A must account for B's costs.

### 4. Resource Pre-check vs Post-deduct

**Question**: Do we check resource availability before execution or after?

**Options**:
- A) Pre-check estimate, then actual deduct
- B) Just execute and deduct (fail if insufficient)
- C) Reserve resources, execute, adjust

**My lean**: Option B for simplicity. If you run out mid-execution, action completes but resources go negative (or we allow partial execution).

### 5. What Counts as "Resources Consumed" for Non-Executable Artifacts?

**Question**: If you read a non-executable artifact, what resources are consumed?

**Options**:
- A) None (reading is free)
- B) Some token cost (content becomes part of your context)
- C) Fixed small cost

**My lean**: Option A for now. The real cost (tokens) comes when the agent THINKS about what they read, which is already tracked.

### 6. Default Resource Policy

**Question**: What should the default be?

**Options**:
- A) `caller_pays` - Caller brings own resources
- B) `owner_pays` - Owner absorbs costs

**My lean**: Option A (`caller_pays`). It's simpler, more conservative, and puts owners in explicit control if they want to subsidize.

### 7. Should Scrip Costs Remain for Genesis Methods? ✅ RESOLVED

**Question**: Currently genesis methods have scrip costs (transfer: 1, submit: 5). Keep these?

**Decision**: **Option B - Remove scrip costs entirely.**

Genesis costs should be **compute (resources)**, not scrip. This separates:
- **Compute** = physical cost of doing anything
- **Scrip** = purely economic, only flows between agents

Scrip only flows for: agent↔agent trades, oracle auction bids, oracle minting.

Spam prevention comes from compute costs, not scrip fees.

### 8. Measuring Tokens for Non-LLM Operations

**Question**: Invoking an artifact's code doesn't use LLM tokens. What resource does it consume?

**Options**:
- A) CPU time only
- B) A fixed "execution cost"
- C) Nothing (code execution is free)

**My lean**: Option A (CPU time), but defer implementation. For now, code execution is effectively free.

---

## Verification

After implementation:

1. **All 256+ tests pass**
2. **New tests for**:
   - resource_policy on artifacts
   - caller_pays routing
   - owner_pays routing
   - Failure when payer lacks resources
   - resources_consumed in action results
3. **Manual test**: Run simulation, verify resources flow correctly
4. **Documentation accurate**: RESOURCE_MODEL.md and AGENT_HANDBOOK.md match implementation

---

## Estimated Scope

| Phase | Files | Complexity |
|-------|-------|------------|
| Phase 1 | 3-4 | Low |
| Phase 2 | 4-5 | Medium |
| Phase 3 | 2-3 | Medium |
| Phase 4 | 3-4 | Low |
| Phase 5 | 1-2 | Low |
| Phase 6 | 2-3 | Medium (deferred) |

Total: ~15 files touched, ~5-6 new test files
