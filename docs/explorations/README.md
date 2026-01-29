# Design Explorations

This directory contains extended reasoning for significant architectural decisions.

## Purpose

**For questioning decisions, not implementing them.**

When implementing, read the ADR - it has the decision.
When questioning why, read the exploration - it has the full reasoning.

## Structure

Each exploration documents:
- The question being explored
- All alternatives considered
- Tradeoffs of each alternative
- Prior art / how others solved it
- Key insights from discussion
- Why we chose what we chose
- Remaining concerns

## Files

| File | ADR | Topic |
|------|-----|-------|
| `access_control.md` | ADR-0024 | Artifact self-handled access control |
| `resolved_questions.md` | Various | Historical Q&A from model development |
| `escrow_stress_test.md` | - | Insights from escrow artifact walkthrough |
| `ostrom_rights_mapping.md` | - | Mapping to Ostrom's rights framework |

## When to Create an Exploration

Create an exploration when:
- The decision is significant (affects architecture)
- Multiple viable alternatives exist
- You had extended discussion to reach the decision
- Future readers might wonder "why not X?"

Don't create an exploration for:
- Simple decisions
- Decisions with obvious answers
- Implementation details

## Relationship to Other Docs

```
PRD.md                  # What we're trying to achieve
    ↓
explorations/           # How we explored options (read when questioning)
    ↓
adr/                    # What we decided (read when implementing)
    ↓
CONCEPTUAL_MODEL.yaml   # What IS (read for understanding)
    ↓
CONCERNS.md             # What to watch (read for monitoring)
```
