# Spec Review: Gaps, Inconsistencies, Questions

Comparison of `specs_summary.md` (original spec) vs current implementation and target architecture.

---

## Summary

| Status | Count | Notes |
|--------|-------|-------|
| Aligned | 12 | Spec matches target |
| Gap (needs implementation) | 5 | Code changes needed |
| Inconsistency (resolved) | 5 | Documented in DESIGN_CLARIFICATIONS.md |
| Question (resolved) | 7 | All clarified, see below |

**Update 2026-01-11:** All questions resolved. All inconsistencies documented. Remaining gaps are implementation work.

---

## Aligned (Spec matches current/target)

1. **Physics-first design** - Spec and implementation align on resources as real constraints
2. **Flow/Stock distinction** - Both have compute (flow) and disk (stock)
3. **Artifacts** - Persistent, addressable, costed
4. **Narrow action waist** - Only 4 action types (noop, read, write, invoke)
5. **Emergence over prescription** - No hardcoded agent types
6. **Observability** - Event logging exists
7. **Executable vs non-executable artifacts** - Distinction exists
8. **Standing/Principals** - Implemented via ledger principals
9. **No direct state mutation** - All changes via actions
10. **Costs on all actions** - Thinking costs, genesis method costs
11. **LLM as external oracle** - LLM proposes, world disposes
12. **Artifact-mediated coordination** - genesis_handbook, escrow, etc.

---

## Gaps (Spec feature not implemented)

### 1. Contracts as First-Class System
**Spec says:** Contracts are executable policy artifacts that govern actions. Replace ownership, access control, permissions.

**Current:** We have artifact `policy` fields (allow_read, read_price, etc.) but these are not "contracts" in the spec sense - not executable, not composable, not tradeable.

**Gap:** Need contract system where policies are actual artifacts that can be created, modified, traded.

---

### 2. Freezing Mechanism
**Spec says:** Entities with sufficiently negative balances are "frozen" - cannot initiate actions but state persists, can receive transfers.

**Current:** We discussed debt for compute but haven't implemented explicit freezing threshold or freeze state.

**Target:** Token bucket allows debt, but no freeze threshold defined.

**Gap:** Need `is_frozen` state and configurable freeze threshold.

---

### 3. Admission Control vs Settlement
**Spec says:** Two-phase cost model:
- Admission: Can action begin? (conservative estimate)
- Settlement: What did it actually cost? (measured)

**Current:** We deduct after execution but don't have explicit admission check before.

**Gap:** May need pre-execution resource check that's conservative (proxy), then actual settlement.

---

### 4. Communication as Derived Action
**Spec says:** Messaging is NOT a primitive. It's writing to shared artifacts, invoking recipient interfaces.

**Current:** We don't have explicit messaging. Agents coordinate via artifacts.

**Status:** Actually aligned! But worth confirming there's no hidden messaging.

---

### 5. Rejected Action Costs
**Spec says:** "Rejected actions may still incur costs, especially for evaluation, validation, or contract checking."

**Current:** Failed actions return error but don't charge. Only successful thinking charges compute.

**Gap:** Should failed actions cost something? At least evaluation cost?

---

### 6. Action Modification/Clipping
**Spec says:** Actions can be "Modified/Clipped" - execute in constrained form, logged explicitly.

**Current:** Actions either succeed or fail. No partial execution with modification.

**Gap:** Consider adding clipped execution for edge cases.

---

### 7. External Minting Oracle (Reddit demos)
**Spec says:** External feedback (Reddit upvotes, etc.) acts as minting oracle.

**Current:** Oracle scores artifacts via LLM, no external feedback integration.

**Gap:** External feedback mechanism for minting. Deferred to later phase.

---

### 8. Visual Demo Harness
**Spec says:** Browser as measurement instrument, Puppeteer for evidence artifacts.

**Current:** Dashboard exists for observability, but no demo harness.

**Gap:** Demo rendering and measurement system. Deferred.

---

## Inconsistencies (Spec says X, we do Y)

### 1. Tick Semantics
**Spec says:** "Time is discrete and explicit, advancing via ticks, steps, execution windows." Flow "renews over time" with a "window."

**Current:** Tick-synchronized execution where tick IS the execution trigger.

**Target:** Continuous execution, ticks are just metrics windows.

**Issue:** Neither current nor target exactly matches spec's "flow renews within a window" - we're moving to rolling window (token bucket) which is different from discrete window.

**Question:** Is token bucket compatible with spec's flow model, or does spec expect discrete windows?

---

### 2. Negative Balances Allowed
**Spec says:** "Negative balances are allowed" and "sufficiently negative entities may be frozen."

**Current:** Ledger enforces balance >= 0 (can't go negative).

**Target:** Compute can go negative (debt), scrip stays >= 0 with debt as contracts.

**Issue:** Partial alignment. Need to decide: can scrip go negative, or only compute?

---

### 3. Contract-Governed Access
**Spec says:** "Access to artifacts is governed by contracts, not by artifact type or origin."

**Current:** Access governed by `policy` dict on artifact (allow_read, allow_write, etc.).

**Issue:** Our policies are not contracts - they're static config on artifacts. Not composable, not tradeable, not dynamic.

---

### 4. Ownership as Contract Pattern
**Spec says:** "Ownership" is NOT primitive - it's a bundle of contractual rights.

**Current:** We have `owner_id` as a field on artifacts. Ownership IS primitive in our system.

**Issue:** Spec explicitly rejects this. We should model ownership as a set of rights (read, write, delete, transfer, charge for access) that can be unbundled.

---

### 5. No Central Scheduler
**Spec says:** "There is no global scheduler... Scheduling authority is the ability to consistently get actions accepted."

**Current:** Runner IS a central scheduler - it decides when agents think.

**Target:** Continuous loops remove the scheduler, but agents still need something to "run" them.

**Issue:** Even in target, something orchestrates agent lifecycles. Is that a scheduler?

---

## Questions Needing Clarification

### 1. What exactly is a "Contract" in implementation terms?
**Spec says:** Executable policy artifact that evaluates proposed actions.

**RESOLVED:** Contracts are executable artifacts with a `check_permission` tool. See [target/contracts.md](architecture/target/contracts.md) and [DESIGN_CLARIFICATIONS.md](DESIGN_CLARIFICATIONS.md).

### 2. How do contracts compose?
**Spec says:** "If multiple contracts apply to an action, all are evaluated, their effects composed deterministically."

**RESOLVED:** Composition via delegation. Contracts can invoke other contracts. No kernel-imposed composition rules - contract author decides. See DESIGN_CLARIFICATIONS.md.

### 3. Standing vs Principal - are these the same?
**Spec uses:** "Standing" as the concept, "Principal" as an entity with standing.

**RESOLVED:** Principal = artifact with `has_standing: true`. See DESIGN_CLARIFICATIONS.md "Ontological Resolutions" section.

### 4. What makes an artifact "executable"?
**Spec says:** Executable artifacts encapsulate logic that can be invoked.

**RESOLVED:** `has_loop: true` property + required `interface` field (MCP-compatible schema). See DESIGN_CLARIFICATIONS.md.

### 5. How do firms/organizations emerge?
**Spec says:** Firms are "bundles of contracts and artifacts."

**RESOLVED:** Firms are contracts. A firm IS a contract that governs access to shared artifacts. Multi-sig, DAO, etc. are contract implementations. See DESIGN_CLARIFICATIONS.md.

### 6. How does delegation work?
**Spec says:** "Delegation does not automatically transfer standing; responsibility remains with the principal."

**RESOLVED:** Payment follows `has_standing`. Standing = pays own costs. No standing = invoker pays. See [target/resources.md](architecture/target/resources.md) "Invocation Cost Model".

### 7. Token bucket vs "flow window"
**Spec says:** Flow "renews within a window" (seems discrete).

**RESOLVED:** Token bucket is compatible interpretation. Continuous accumulation within capacity limit. No discrete refresh boundaries. See DESIGN_CLARIFICATIONS.md.

---

## Recommendations

### High Priority - RESOLVED
1. ~~**Define contract model**~~ - DONE. Contracts are executable artifacts with `check_permission` tool. See [target/contracts.md](architecture/target/contracts.md).
2. ~~**Add freezing**~~ - DONE. Freeze threshold documented in DESIGN_CLARIFICATIONS.md.
3. ~~**Reconcile ownership**~~ - DONE. `access_contract_id` is only authority, no owner bypass. See DESIGN_CLARIFICATIONS.md.

### Medium Priority - PARTIALLY RESOLVED
4. ~~**Admission control**~~ - DECIDED: Skip. Debt model is sufficient. See DESIGN_CLARIFICATIONS.md.
5. ~~**Failed action costs**~~ - DONE. Failed actions cost resources. See DESIGN_CLARIFICATIONS.md.
6. ~~**Clarify standing**~~ - DONE. Principal = artifact with `has_standing: true`. See DESIGN_CLARIFICATIONS.md.

### Low Priority (Defer)
7. **Action clipping** - Not implemented. Partial execution model deferred.
8. **External minting** - Not implemented. Reddit/external feedback deferred.
9. **Demo harness** - Not implemented. Visual measurement system deferred.

---

## Resolution Status

| Area | Status | Reference |
|------|--------|-----------|
| Contract model | Documented | target/contracts.md |
| Freezing | Documented | DESIGN_CLARIFICATIONS.md |
| Ownership model | Documented | DESIGN_CLARIFICATIONS.md |
| Admission control | Decided (skip) | DESIGN_CLARIFICATIONS.md |
| Failed action costs | Documented | DESIGN_CLARIFICATIONS.md |
| Standing/principal | Documented | DESIGN_CLARIFICATIONS.md |
| Token bucket | Documented | target/resources.md |
| All 7 questions | Resolved | See above |

---

## Remaining Implementation Gaps

These require code changes, not design decisions:

1. **Continuous execution model** - Current code is tick-synchronized
2. **Token bucket implementation** - Current code uses discrete refresh
3. **Contract artifacts** - Current code uses policy fields on artifacts
4. **Docker isolation** - Not yet containerized
5. **MCP-style interfaces** - Artifacts don't have interface fields yet

See [architecture/GAPS.md](architecture/GAPS.md) for implementation priority.
