# Exploration: Resolved Conceptual Questions

**Status:** Resolved (various ADRs)
**Date:** 2026-01-28

This document captures the full reasoning behind questions that were resolved during conceptual model development. For the current model state, see `CONCEPTUAL_MODEL.yaml`.

## Kernel vs Artifact System

**Question:** Where does contract checking belong - kernel or artifact layer?

**Resolution:** Clean separation: Artifacts define policy, kernel enforces it.

- Artifacts define their own governance (contract is part of artifact's interface)
- Kernel executes the contract logic on behalf of the artifact
- The rules belong to the artifact, but kernel runs them

Analogy: A house has a lock (defined by owner), physics makes the lock work.

This means:
- No artifact needs to implement permission checking
- Artifacts just define their contract (as part of interface)
- Kernel handles execution of all permission checks
- Kernel has privilege to read/invoke any contract for this purpose

**Update (ADR-0024):** Superseded. Artifacts now handle their own access in code. Kernel only routes.

---

## Contract Regress

**Question:** How do we break the infinite regress when checking contracts?

**Resolution:** Kernel invoking contracts for permission checking is a kernel function, not an "access" that needs permission itself.

Like: a judge reading a law to make a ruling doesn't need "permission to read the law."

Specifically:
- Kernel has privilege to read/invoke any contract for permission checking
- This is part of kernel's role as "enforcer of policy defined by artifacts"
- Contracts typically have access_contract_id = null (creator controls)
- If contracts call other contracts, depth limit (e.g., 10) prevents infinite loops

**Implementation:**
- Depth limit: 10 (configurable via `executor.max_contract_depth`)
- On depth exceeded: Deny with reason "Contract permission check depth exceeded"
- Source: `src/world/permission_checker.py:143-147`

---

## Caller Identity

**Question:** Who provides and guarantees caller identity?

**Resolution:** Kernel provides verified caller identity. This is an irreducible kernel responsibility.

- Artifacts can't determine who is calling - they just receive requests
- Kernel knows the true caller (it routes all requests)
- Caller identity is provided as part of the permission check context
- Cannot be spoofed - kernel guarantees it

---

## Kernel Provided Metadata

**Question:** What metadata should kernel provide to contracts to reduce friction?

**Resolution:** Kernel provides (verified in `src/world/contracts.py`):

**Always provided (via function parameters):**
- `caller`: Principal requesting access (verified by kernel)
- `action`: The action being attempted (read, write, invoke, etc.)
- `target`: Artifact ID being accessed

**Provided via context dict:**
- `target_created_by`: Creator of the target artifact (immutable)
- `target_metadata`: Artifact metadata dict (if present)
- `method`: Method name (invoke actions only)
- `args`: Method arguments (invoke actions only)

**For executable contracts (additional):**
- `ledger`: ReadOnlyLedger - Read-only access for balance checks

**Not provided (must query if needed):**
- `caller_created_by`
- `caller_balance`
- `event_number/timestamp`
- `call_chain`

---

## What Governs Contracts

**Question:** What contract governs a contract artifact?

**Resolution:** Contracts are artifacts and can have their own access_contract_id. The chain terminates at null (default: creator has all rights).

Example chain:
- Artifact A → Contract E → Contract F → null
- Null means: creator of Contract F controls it

This works because:
1. Kernel has privilege to read/invoke contracts for permission checking
2. Depth limit prevents infinite chains
3. Null contract (default) provides the base case

**Update (ADR-0024):** Superseded. Artifacts handle access in code. Delegation is explicit invocation.

---

## Actions Specification

**Question:** Should actions be formally specified in the conceptual model?

**Resolution:** Actions fall into three categories:

**Core actions (go through contract permission):**
- `read`, `write`, `edit`, `invoke`, `delete`

**Kernel operations (no permission needed):**
- `noop`, `query_kernel`

**Convenience actions (shortcuts for edit_artifact):**
- `subscribe_artifact`, `unsubscribe_artifact`, `configure_context`, `modify_system_prompt`

**Note:** `subscribe_artifact` doesn't check read permission - this is a code gap.

---

## Scrip Currency

**Question:** How does scrip (internal currency) fit into the model?

**Resolution:** Scrip is KERNEL-TRACKED, not an artifact.

Verified in `src/world/ledger.py`:
- Stored as: `self.scrip = {principal_id: amount}`
- Methods: `get_scrip()`, `transfer_scrip()`, `can_afford_scrip()`

Rationale:
- Scrip is internal accounting, not a "thing" in the world
- Different from physical resources (CPU, memory, API)
- Simpler than making it an artifact (no contract overhead)

Note: Different from "rights" which ARE artifacts.

---

## Time Ordering

**Question:** How are events ordered in world history?

**Resolution:** BOTH event numbers and timestamps, with `event_number` as primary ordering.

Verified in `src/world/world.py`:
- `self.event_number = 0` (monotonic counter)
- Events include both: `{"event_number": N, "timestamp": T}`

Why event_number is primary:
- Deterministic ordering (no clock skew issues)
- Monotonically increasing guarantees
- Timestamps can be ambiguous across systems

---

## Bootstrap

**Question:** What exists at time zero? How does first artifact get created?

**Resolution:** Configuration specifies initial state.

Bootstrap sequence (verified in `src/world/world.py`):
1. Configuration loaded
2. Ledger created
3. Genesis artifacts created
4. Genesis artifacts registered
5. Agents created with starting resources

**Update (ADR-0024):** Bootstrap enabled by:
- First artifact has inline access logic in code (no delegation needed)
- First artifact can serve as contract for future artifacts
- No kernel defaults - agents figure it out through selection pressure

---

## Cross-Artifact Queries

**Question:** Can contracts query artifacts OTHER than the target?

**Resolution:** Yes, artifacts (including contracts) can invoke other artifacts.

In the artifact self-handling model:
- Artifacts handle their own requests via `handle_request()`
- An artifact's handler can invoke other artifacts
- Delegation is just artifact-to-artifact invocation

This enables:
- Hierarchical permissions (department → team contracts)
- Composable policies (AND multiple contracts)
- Shared access control

Depth limit (default 10) prevents infinite delegation chains.

---

## Linearize Function Location

**Question:** How is linearize() defined? Method in interface? Separate field?

**Resolution:** Follow MCP protocols for compatibility. Linearization is optional.

Interface schema (MCP-compatible with optional linearization):
```yaml
interface:
  description: str        # Required
  labels: list[str]       # Required
  methods: list[Method]   # Optional
  inputSchema: JSONSchema # Optional
  outputSchema: JSONSchema # Optional
  linearization: str      # Optional - template for LLM presentation
```

Why MCP:
- Compact JSON Schema reduces token cost
- Constrained generation prevents parameter hallucination
- Compatibility with MCP tooling ecosystem

Why linearization is optional:
- Most artifacts work fine with MCP interface alone
- Optional allows gradual adoption, selection pressure

---

## Read/Write as Methods

**Question:** Should read/write/edit/delete be methods rather than kernel operations?

**Resolution (ADR-0024):** All operations route through artifact's `handle_request`. Kernel routes with verified identity; artifact decides everything.

See `docs/explorations/access_control.md` for full alternatives analysis.
