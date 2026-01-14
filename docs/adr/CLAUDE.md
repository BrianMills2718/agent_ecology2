# ADR Directory

Architecture Decision Records - immutable logs of architectural decisions.

## Purpose

ADRs capture significant architectural decisions with context, rationale, and consequences. Once accepted, they are immutable - supersede with a new ADR if decisions change.

## File Structure

| Pattern | Purpose |
|---------|---------|
| `NNNN-short-title.md` | Individual ADR (sequential numbering) |
| `TEMPLATE.md` | Template for new ADRs |
| `README.md` | Human-readable index and instructions |

## Creating ADRs

1. Copy `TEMPLATE.md` to next number in sequence
2. Fill in Context, Decision, Consequences
3. Set status to `Proposed`
4. Submit PR for review
5. Change to `Accepted` when approved

## ADR Statuses

| Status | Meaning |
|--------|---------|
| Proposed | Under discussion |
| Accepted | Decision in effect |
| Deprecated | No longer applies |
| Superseded | Replaced by another ADR |

## Governance Integration

ADRs are linked to source files via `scripts/governance.yaml`. Governed files show which ADRs apply in their header comments. See `docs/meta/08_adr-governance.md` for the pattern.

## Key Commands

```bash
python scripts/sync_governance.py --check   # Verify governance headers
python scripts/sync_governance.py --apply   # Update governance headers
```

## When to Create an ADR

- Significant architectural decisions
- Technology choices with long-term impact
- Patterns that affect multiple modules
- Trade-offs that future developers should understand

Do NOT create ADRs for implementation details or trivial decisions.
