# ADR-0024: Artifact Self-Handled Access Control

**Status:** Accepted
**Date:** 2026-01-29
**Context:** Extended discussion on kernel vs artifact responsibility for access control

## Decision

**Artifacts handle their own access control in their code. The kernel does not enforce access.**

The kernel's responsibilities are limited to:
1. **Storage** - Persist artifacts
2. **Resource metering** - Track consumption (can't trust self-reporting)
3. **Verified identity** - Provide trusted caller ID to artifact code
4. **History** - Append-only log of events

Access control is an artifact-level pattern, not a kernel concept.

## Goal

Emergent collective capability optimized for real world constraints.

The heuristics (minimal kernel, selection pressure, etc.) serve this goal but are not goals themselves.

## Context

We debated whether the kernel should check an `access_contract_id` field before allowing operations, or whether artifacts should handle access in their own code.

### The Core Question

When Agent A wants to read/write/invoke Artifact B:
- **Option A:** Kernel checks B's `access_contract_id`, invokes that contract, then proceeds if allowed
- **Option B:** Kernel routes request to B's code with verified caller ID; B's code decides what to do

### Why Kernel Must Provide Verified Identity

In a same-process Python environment, artifacts could lie about who's calling:
```python
# Malicious code could claim to be someone else
B.handle_request(caller="I'm C, trust me", ...)
```

The kernel is the trusted intermediary that knows which code is actually executing and provides verified `caller_id` to the target artifact. This is the only reason the kernel is involved in routing.

### Why Not Full Sandboxing?

Full process isolation would make lying physically impossible but adds complexity and performance overhead. Instead, contracts serve as the middle ground:
- Violations are observable (history logs everything)
- Selection pressure punishes bad actors (reputation, others stop interacting)
- Lying is possible but costly

## Alternatives Considered

### Alternative 1: Kernel Enforces access_contract_id

```
Request → Kernel checks access_contract_id → Invoke contract → If allowed, proceed
```

**Pros:**
- Guaranteed enforcement (artifact can't skip check)
- Separation of concerns (access logic separate from business logic)
- Familiar (like OS file permissions)

**Cons:**
- Kernel has policy (knows about "contracts" as special)
- Must define null behavior (source of "owner" confusion)
- Less flexible (kernel defines what access checking means)
- Circular issue for self-referential access
- Bugs can still exist in contract code (kernel enforcement doesn't prevent logic bugs)

### Alternative 2: Artifact Code Handles Everything (CHOSEN)

```
Request → Kernel routes with verified caller_id → Artifact code decides
```

**Pros:**
- Simpler kernel (just routing + identity + resources)
- Maximum flexibility
- Follows smart contract model (code IS the access control)
- No null behavior ambiguity
- No "owner" concept confusion

**Cons:**
- Artifacts could have bugs in access checking
- Every artifact needs access logic (mitigated by reusable patterns)
- No forced separation of concerns (access mixed with code)

### Alternative 3: Hybrid (Kernel checks if field present)

```
If access_contract_id set → Kernel enforces it
If null → Artifact code handles
```

**Cons:**
- Two code paths
- Still need to define null behavior
- Complexity without clear benefit

## Prior Art

| System | Model | Notes |
|--------|-------|-------|
| **Smart Contracts / DAOs** | Code handles access | No separate access layer. Common patterns become libraries (OpenZeppelin). Execution is guaranteed by blockchain. |
| **Operating Systems** | Kernel enforces | Files have permissions, kernel checks before access. |
| **Actor Systems (Erlang)** | Actor handles | Actors receive messages, decide what to do. |
| **Capability-based** | Reference = permission | Having the reference means you can call. |

We follow the **smart contract model**: code is the access control, common patterns get library-ized.

## Consequences

### access_contract_id Field

- **NOT a kernel concept** - Kernel doesn't check it
- **Can exist as artifact metadata** - For documentation/discovery
- **Just a pattern** - Artifacts that want delegation invoke another artifact from their code

### Artifact Code Patterns

**Inline access control:**
```python
def handle_request(caller, operation, args):
    if caller not in self.allowed_callers:
        return {"error": "denied"}
    # ... do operation
```

**Delegation to another artifact:**
```python
def handle_request(caller, operation, args):
    result = kernel.invoke("my_access_policy", "check", {
        "caller": caller, "operation": operation
    })
    if not result["allowed"]:
        return {"error": "denied"}
    # ... do operation
```

Both are just code patterns. Kernel doesn't distinguish.

### Reusable Access Patterns

Instead of genesis contracts, build reusable artifacts:
- Artifacts that check access and return allow/deny
- Other artifacts invoke these from their code
- No special treatment by kernel

### Bootstrap

- First agent created by kernel/config (only genesis artifact)
- First agent's code handles its own access
- First agent creates other artifacts with whatever access patterns it wants
- No other genesis artifacts required

## Concerns and Watch Points

| Concern | Description | Mitigation | Severity |
|---------|-------------|------------|----------|
| **Access bugs** | Artifact code could have bugs in access logic | Selection pressure - buggy artifacts fail. History shows what happened. | Medium |
| **Boilerplate** | Every artifact needs access logic | Reusable pattern artifacts. Templates. | Low |
| **No separation** | Access mixed with business logic | Convention: check access at top of handle_request. | Low |
| **Concurrent access** | ArtifactStore has no locking (Ledger does) | Document as known gap. Add locking if issues arise. | Medium |
| **Long-running code** | Artifact could hog resources | Rate limiting, timeouts already implemented. | Low |
| **Caller spoofing** | Artifact tries to claim false identity | Kernel controls caller_id, artifact can't override. | N/A (solved) |

## "Owner" Clarification

The term "owner" does not exist as a kernel concept.

- `created_by` is immutable metadata with **no permission implications**
- "Ownership" is a pattern contracts MAY implement via code
- An artifact has an "owner" only if its code grants complete rights to some entity
- This is a choice, not a default

Why "owner" is problematic:
- Implies single entity has all rights (but rights are Ostrom-style bundles)
- Implies created_by grants rights (it doesn't - code does)
- Implies clear answer to "who owns X?" (could be complex nested delegation)

Depth limit (configurable, default 10) prevents infinite delegation chains, making rights decidable.

## What Kernel Actually Does

| Function | Why Kernel Does It |
|----------|-------------------|
| **Storage** | Artifacts can't persist themselves |
| **Resource metering** | Can't trust self-reporting |
| **Verified identity** | Caller can't spoof who they are |
| **History** | Append-only, artifacts can't modify past |

| Function | Why Kernel Does NOT Do It |
|----------|--------------------------|
| **Access control** | Artifact code pattern |
| **"Contract" concept** | Just artifacts invoking artifacts |
| **Null behavior** | No null - no kernel access checking |

## Relationship to Other ADRs

- **ADR-0016 (created_by immutability):** created_by is metadata, not permissions - still valid
- **ADR-0019 (unified permission architecture):** Superseded by this simpler model
- **ADR-0001 (everything is artifact):** Contracts are artifacts, access is artifact code - reinforced

## Decision Log

| Date | Topic | Decision | Confidence |
|------|-------|----------|------------|
| 2026-01-29 | Kernel vs artifact access | Artifact handles in code | 80% |
| 2026-01-29 | access_contract_id | Not a kernel concept, just a pattern | 80% |
| 2026-01-29 | null behavior | N/A - no null, no kernel checking | N/A |
| 2026-01-29 | Prior art model | Follow smart contract model | 80% |
| 2026-01-29 | Genesis artifacts | Only first agent, no contracts | 80% |
| 2026-01-29 | Why kernel routes | To provide verified caller identity | 90% |
| 2026-01-29 | Why not full sandbox | Middle ground - observable violations + selection pressure | 75% |
