# Exploration: Access Control Architecture

**Decision:** ADR-0024
**Date:** 2026-01-29
**Status:** Decided

## The Question

When Agent A wants to read/write/invoke Artifact B, who checks if A is allowed?

## Alternatives Explored

### Alternative 1: Kernel Enforces access_contract_id

**How it works:**
```
Request → Kernel checks access_contract_id → Invoke contract → If allowed, proceed
```

Every artifact has an `access_contract_id` field pointing to a contract artifact. The kernel checks this before allowing any operation.

**Tradeoffs:**

| Pro | Con |
|-----|-----|
| Guaranteed enforcement - artifact can't skip | Kernel has policy (knows "contracts" are special) |
| Separation of concerns | Must define null behavior |
| Familiar (like OS permissions) | Less flexible |
| | Still has bugs in contract code |

**Why rejected:** Adds complexity to kernel without preventing bugs. The null behavior question kept reintroducing "owner" confusion.

### Alternative 2: Artifact Code Handles Everything (CHOSEN)

**How it works:**
```
Request → Kernel routes with verified caller_id → Artifact code decides
```

Artifact's code handles all access logic. Can delegate to other artifacts if desired.

**Tradeoffs:**

| Pro | Con |
|-----|-----|
| Simpler kernel | Artifacts could have bugs |
| Maximum flexibility | Every artifact needs access logic |
| Follows smart contract model | No forced separation of concerns |
| No null ambiguity | |

**Why chosen:** Matches prior art (DAOs/smart contracts). Kernel stays minimal. Bugs exist either way - at least this way the model is simpler.

### Alternative 3: Hybrid (check if field present)

**How it works:**
```
If access_contract_id set → Kernel enforces
If null → Artifact code handles
```

**Why rejected:** Two code paths, still need to define null behavior, complexity without benefit.

### Alternative 4: Full Process Sandboxing

**How it works:**
Each artifact runs in a separate subprocess. Kernel is the only communication channel. Lying is physically impossible.

**Why rejected:** Complexity and performance overhead. The middle ground (observable violations + selection pressure) is sufficient.

## Key Insights

### Why Kernel Provides Verified Identity

In a same-process Python environment:
```python
# A could lie about who's calling
B.handle_request(caller="I'm C, trust me", ...)
```

The kernel knows which code is actually executing. It provides verified `caller_id` that artifacts can trust. This is the ONLY reason the kernel is involved in routing.

### The "Owner" Misconception

We kept falling into thinking `created_by` = owner with special rights. This is wrong:

- `created_by` is immutable metadata with NO permission implications
- "Owner" is a pattern contracts MAY implement
- Rights are Ostrom-style bundles, not unified ownership
- An artifact "has an owner" only if its code explicitly grants that pattern

Why the misconception persists:
- Most systems have creator = owner by default
- `created_by` sounds like "this is mine"
- People expect creator to have special rights

Solution: Documented explicitly. No kernel concept of owner. Code patterns only.

### Contracts as Middle Ground

We don't need full sandboxing because:
- Violations are observable (history logs everything)
- Selection pressure punishes cheaters
- Reputation emerges from observation

Lying is possible but costly - others stop interacting with you.

### Why Not access_contract_id as Kernel Field?

We explored whether artifacts even need `access_contract_id`:

**If the artifact handles its own access in code:**
- It can check inline
- Or invoke another artifact for the check
- No special field needed

**If access_contract_id exists:**
- It's just a convention/pattern
- Kernel doesn't need to check it
- Artifact's code does `kernel.invoke(self.access_contract_id, "check", ...)`

Conclusion: `access_contract_id` can exist as artifact metadata for documentation/discovery, but kernel doesn't enforce it.

### Bootstrap Without Genesis Contracts

Original concern: First artifact needs a contract, contracts are artifacts. Chicken-egg?

Resolution: Artifacts can handle their own access:
- First agent created by kernel/config
- First agent's code handles its own access (inline)
- First agent creates other artifacts with whatever patterns it wants
- No genesis contracts needed

## Prior Art

| System | Model | Notes |
|--------|-------|-------|
| **Smart Contracts / DAOs** | Code handles access | No separate access layer. Common patterns become libraries (OpenZeppelin). Execution guaranteed by blockchain. |
| **Operating Systems** | Kernel enforces | Files have permissions, kernel checks before access. |
| **Actor Systems (Erlang)** | Actor handles | Actors receive messages, decide what to do. |
| **Capability-based** | Reference = permission | Having the reference means you can call. |

We follow the **smart contract model**.

## Rejected Patterns

### Kernel Defaults for Null Contract

Options we considered:
1. `null` = deny all
2. `null` = allow all (public)
3. `null` = only `created_by` can access

All rejected because having kernel know about null behavior reintroduces policy. With artifact-handled access, there's no null - there's just code.

### Self-Referential access_contract_id

If `access_contract_id` points to self, kernel would:
- Need to invoke artifact to check access
- But invoking requires checking access first
- Infinite loop

This complexity disappears when artifact code just handles access inline.

## What The Kernel Actually Does

Arrived at from first principles:

| Function | Why Kernel |
|----------|------------|
| **Storage** | Artifacts can't persist themselves |
| **Resource metering** | Can't trust self-reporting |
| **Verified identity** | Caller can't spoof |
| **History** | Append-only, immutable |

| Function | Why NOT Kernel |
|----------|----------------|
| Access control | Artifact code pattern |
| "Contract" concept | Just artifacts |
| Null handling | No null needed |

## Remaining Concerns

Documented in CONCERNS.md:
- ArtifactStore has no locking (Ledger does)
- Access control bugs possible (selection pressure mitigates)
- Boilerplate in artifact code (reusable patterns mitigate)
- "Owner" misconception keeps recurring

## Decision Confidence

80% - High enough to proceed, documented well enough to revisit if needed.

## References

- ADR-0024: The formal decision
- Plan #155: Agents as patterns (deferred, related context)
- docs/archive/design_discussions_jan11.md: Earlier MCP-lite discussion
