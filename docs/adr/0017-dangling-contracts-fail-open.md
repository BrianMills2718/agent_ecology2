# ADR-0017: Dangling Contracts Fail Open

**Status:** Accepted
**Date:** 2026-01-19
**Supersedes:** Plan #100 decision on dangling contracts (was fail-closed)

## Context

What happens when an artifact's `access_contract_id` points to a deleted contract?

Previous decision (Plan #100) was **fail-closed**: artifacts become permanently inaccessible if their contract is deleted. Rationale: "Selection pressure over protection - agents learn to use stable contracts."

On reconsideration, fail-closed creates harsh, punitive outcomes without clear learning benefit. The artifact being permanently locked doesn't teach anyone anything useful - it's just friction.

## Decision

**Dangling contracts fail open to a configurable default contract.**

### 1. Configurable Default Contract

```yaml
# config.yaml
contracts:
  default_on_missing: "genesis_freeware_contract"  # Configurable
```

### 2. Permission Check Behavior

```python
def check_permission(artifact, caller, action):
    contract = get_artifact(artifact.access_contract_id)

    if contract is None:
        # Contract was deleted - use default
        log.warning(f"Dangling contract: {artifact.access_contract_id} for {artifact.id}")
        default_id = config.get("contracts.default_on_missing")
        contract = get_artifact(default_id)

    return contract.check_permission(caller, action, artifact.id, context)
```

### 3. Observable Degradation

When an artifact falls back to default contract:
- Log warning with full context
- Include in event log for observability
- Agents can query which artifacts have dangling contracts

### 4. Selection Pressure Preserved

The agent whose contract was deleted still experiences consequences:
- Their custom access control is gone
- Artifact now uses freeware semantics (or whatever default is configured)
- If they wanted restricted access, they've lost it

This is a consequence without being catastrophic.

## Consequences

### Positive

- **No permanent lockout** - artifacts remain accessible
- **Learning preserved** - agents still see consequences of contract deletion
- **Observable** - dangling contracts are logged and queryable
- **Configurable** - default behavior can be changed per deployment
- **Aligned with "accept risk, observe outcomes"** - not punitive

### Negative

- **Security implication** - deleting a restrictive contract opens up access
- **Unexpected behavior** - artifact might behave differently than creator intended

### Neutral

- Selection pressure still exists, just less severe
- Agents can still create stable, undeletable contracts if they want guarantees

## Alternatives Considered

### Fail-Closed (Previous Decision)
- Artifacts permanently inaccessible
- Rejected: too punitive, no learning benefit

### Prevent Contract Deletion
- Contracts referenced by artifacts cannot be deleted
- Rejected: adds referential integrity complexity, contracts become immortal

### No Default (Error)
- Missing contract = error on every access attempt
- Rejected: similar to fail-closed, just noisier

## Related

- ADR-0015: Contracts as Artifacts
- Plan #100: Contract System Overhaul (supersedes dangling contract decision)
- `docs/architecture/target/05_contracts.md`
