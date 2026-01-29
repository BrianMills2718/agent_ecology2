# Exploration: Ostrom Rights Mapping

**Status:** Analysis complete
**Date:** 2026-01-28

Analysis of how our artifact model maps to Ostrom's bundle of rights framework.

## Rights Coverage

| Ostrom Right | Definition | Our Model | Covered? |
|--------------|------------|-----------|----------|
| **Access** | Enter and enjoy non-subtractive benefits | `read` | Yes |
| **Withdrawal** | Obtain resource units or products | `invoke` | Yes |
| **Management** | Regulate internal use patterns, transform resource | `write`, `edit` on artifact | Yes |
| **Exclusion** | Determine who has access/withdrawal rights | `write`/`edit` on the CONTRACT governing the artifact | Yes |
| **Alienation** | Sell or transfer management and exclusion rights | `write`/`edit` on contract's self-access rules | Yes* |

*Alienation requires escrow pattern for atomic handoff.

## Potential Gaps

### Proposed Change Visibility

**Status:** CONFIRMED GAP (Medium importance, 70% confidence)

**Description:** For fine-grained edit control (e.g., "you can add but not remove"), contracts need to see WHAT the edit will do, not just that an edit is happening.

**Current behavior:**
- Contract receives: caller, operation, target_state
- Contract does NOT receive: proposed_content, old_string, new_string

**Workaround:** Use semantic methods (`add_reader`, `remove_reader`) instead of raw edit. Contract controls methods via invoke permissions with args checking.

**If we fix:**
```python
context["proposed_content"] = intent.content
context["proposed_code"] = intent.code
```

---

### Atomic Transfers

**Status:** CONFIRMED GAP (Low importance - escrow handles it, 60% confidence)

**Description:** Alienation requires "give rights AND lose them" atomically. Two separate edits could leave inconsistent intermediate state.

**Workaround:** Escrow pattern provides atomicity.

**If we fix later:** Would need ACID-style transactions. Complex. Defer as tech debt.

---

### Per-Method Invoke Control

**Status:** NOT A GAP - ALREADY IMPLEMENTED

**Description:** Contracts CAN control access per-method and check argument values.

**Code reference** (`src/world/permission_checker.py:188-191`):
```python
if action == "invoke":
    context["method"] = method
    context["args"] = args if args is not None else []
```

**Example:**
```python
# Contract can express:
if method == "add" and all(arg < 42 for arg in args):
    return ALLOW
```

## Key Insight

Ostrom's framework maps well to our model. The main gap (atomic transfers) is handled by the escrow pattern rather than requiring kernel-level transactions. This aligns with our "contracts handle policy" principle.
