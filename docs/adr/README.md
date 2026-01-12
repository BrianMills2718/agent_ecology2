# Architecture Decision Records

This directory contains Architecture Decision Records (ADRs) - a log of architectural decisions made in this project.

## What is an ADR?

An ADR captures a single architectural decision, including:
- The context and problem
- The decision made
- The consequences and trade-offs

ADRs are **immutable** once accepted. If a decision changes, create a new ADR that supersedes the old one.

## How to Use

### Reading ADRs

Browse the list below or check `scripts/governance.yaml` to see which ADRs govern specific source files.

### Creating a New ADR

1. Copy `TEMPLATE.md` to `NNNN-short-title.md` (next number in sequence)
2. Fill in the template
3. Set status to `Proposed`
4. Submit PR for review
5. Once approved, change status to `Accepted`

### Statuses

| Status | Meaning |
|--------|---------|
| **Proposed** | Under discussion, not yet decided |
| **Accepted** | Decision made, in effect |
| **Deprecated** | No longer applies (but kept for history) |
| **Superseded** | Replaced by another ADR |

## Governance

ADRs are linked to source files via `scripts/governance.yaml`. When you read a governed file, you'll see a `GOVERNANCE` block listing relevant ADRs.

```python
# Example: src/world/contracts.py
"""Contract-based access control.

# --- GOVERNANCE START (do not edit) ---
# ADR-0003: Contracts can do anything
# ADR-0005: No owner bypass
# --- GOVERNANCE END ---
"""
```

To update governance:
1. Edit `scripts/governance.yaml`
2. Run `python scripts/sync_governance.py --apply`
3. Commit both the yaml and updated source files

## ADR Index

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-everything-is-artifact.md) | Everything is an artifact | Accepted |
| [0002](0002-no-compute-debt.md) | No compute debt | Accepted |
| [0003](0003-contracts-can-do-anything.md) | Contracts can do anything | Accepted |
| [0005](0005-unified-documentation-graph.md) | Unified documentation graph | Proposed |

---

## References

- [Original ADR proposal by Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- `scripts/governance.yaml` - File-to-ADR mappings
- `scripts/sync_governance.py` - Governance sync tool
