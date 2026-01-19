# ADR-0018: Bootstrap Phase and Eris

**Status:** Accepted
**Date:** 2026-01-19

## Context

If contracts are artifacts, and artifacts need contracts for access control, we have a chicken-and-egg problem:
- `genesis_freeware_contract` needs an `access_contract_id`
- But `genesis_freeware_contract` doesn't exist yet when we're creating it

Additionally:
- Who is `created_by` for genesis artifacts?
- How do we prevent ID collisions with genesis artifacts?
- How do we distinguish genesis APIs from the kernel concepts they expose?

## Decision

### 1. Bootstrap Phase at t=0

During `World.__init__()`, a bootstrap phase exists where normal physics don't apply:

```python
class World:
    def __init__(self):
        self._bootstrapping = True

        # Create genesis artifacts (no permission checks)
        self._create_genesis_artifacts()

        self._bootstrapping = False
        # Physics now applies - all access through contracts

    def check_permission(self, artifact, ...):
        if self._bootstrapping:
            return PermissionResult(allowed=True, reason="bootstrap")
        # Normal contract-based checks...
```

Bootstrap is instantaneous - the constructor - not a time period. Once `World()` returns, bootstrap is over.

**Analogy:** The initial conditions of the universe aren't explained by physics. Physics describes what happens after the initial state exists.

### 2. Eris as Bootstrap Creator

Genesis artifacts are created by `Eris`:

```python
genesis_freeware_contract = Artifact(
    id="genesis_freeware_contract",
    created_by="Eris",
    ...
)
```

**Why Eris?**
- Greek goddess of discord and strife
- Central to Discordianism - chaos as creative force
- Fits project philosophy: emergence over prescription, accept risk, selection pressure
- Short, memorable, not overloaded with programming baggage
- Small delight when agents discover who created genesis artifacts

`Eris` is registered in the ID namespace as a principal that exists but has no agent behind it. It cannot act post-bootstrap.

### 3. Reserved `genesis_` Prefix

The `genesis_` prefix is reserved for system artifacts:

```python
def write_artifact(self, artifact):
    if artifact.id.startswith("genesis_") and not self._bootstrapping:
        raise Error("genesis_ prefix reserved for system artifacts")
    # proceed...
```

This prevents confusion and accidental collision with future genesis additions.

### 4. Genesis Naming Convention

Genesis artifacts use suffixes to clarify their role:

| Suffix | Meaning | Example |
|--------|---------|---------|
| `_api` | Accessor to kernel state | `genesis_ledger_api`, `genesis_event_log_api` |
| `_contract` | Access control contract | `genesis_freeware_contract`, `genesis_private_contract` |

This distinguishes the artifact (an API or contract) from the kernel concept it exposes. The ledger is kernel state; `genesis_ledger_api` is an artifact that provides access to it.

### 5. Genesis Contracts Are Self-Referential

Genesis contracts govern themselves:

```python
genesis_freeware_contract = Artifact(
    id="genesis_freeware_contract",
    access_contract_id="genesis_freeware_contract",  # Self-referential
    ...
)
```

This works because:
- Permission check asks "can I invoke freeware?"
- Freeware's logic: "invoke" action → allowed
- Recursion terminates naturally

Contracts that don't allow invoke become useless (can't check permissions through them).

## Consequences

### Positive

- **Clean bootstrap** - no permission checks during world initialization
- **Clear semantics** - `Eris` is the primordial creator, not a privileged actor
- **Namespace protection** - `genesis_` prefix prevents collisions
- **Self-documenting** - `_api` and `_contract` suffixes clarify purpose
- **Self-referential works** - no infinite recursion

### Negative

- **Bootstrap is special** - one moment where normal rules don't apply
- **Eris is immortal** - can't be deleted, exists forever in ID namespace
- **Reserved prefix** - agents can't use `genesis_` for their artifacts

### Neutral

- Genesis artifacts are otherwise normal artifacts post-bootstrap
- `Eris` appears in logs, queries, etc. as a historical fact

## Related

- ADR-0015: Contracts as Artifacts
- ADR-0016: created_by Replaces owner_id
- Plan #100: Contract System Overhaul
- Discordianism and the Principia Discordia
