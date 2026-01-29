# ADR-0024: Artifact Self-Handled Access Control

**Status:** Accepted
**Date:** 2026-01-29
**Exploration:** [docs/explorations/access_control.md](../explorations/access_control.md) (full reasoning)

## Decision

**Artifacts handle their own access control in their code. The kernel does not enforce access.**

## Kernel Responsibilities

| Does | Doesn't |
|------|---------|
| Storage (persistence) | Access control |
| Resource metering | "Contract" concept |
| Verified caller identity | Null behavior handling |
| History (append-only) | |

## Why

- Follows smart contract model (code IS access control)
- Kernel stays minimal
- No null behavior ambiguity
- No "owner" concept confusion
- See [exploration](../explorations/access_control.md) for full alternatives analysis

## Implementation

**Inline access:**
```python
def handle_request(caller, operation, args):
    if caller not in self.allowed_callers:
        return {"error": "denied"}
    # ... do operation
```

**Delegated access:**
```python
def handle_request(caller, operation, args):
    result = kernel.invoke("my_access_policy", "check", {"caller": caller})
    if not result["allowed"]:
        return {"error": "denied"}
    # ... do operation
```

## Key Points

- `access_contract_id` is NOT a kernel concept - just artifact metadata
- Kernel provides verified `caller_id` - artifacts can't spoof identity
- "Owner" doesn't exist - ownership is a code pattern, not kernel feature
- Bootstrap: first agent handles own access, creates patterns for others

## Concerns

See CONCERNS.md. Key ones:
- ArtifactStore has no locking (Medium)
- Access bugs possible (Medium, mitigated by selection pressure)

## Supersedes

- ADR-0019 (unified permission architecture) - replaced by this simpler model

## Confidence

80%
