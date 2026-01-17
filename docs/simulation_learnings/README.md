# Simulation Learnings

Observations, insights, and questions from running simulations.

## Purpose

Capture what we learn from watching agents operate so insights aren't lost. This includes:
- Bugs discovered during simulation
- Behavioral patterns (expected and unexpected)
- Architecture limitations revealed under load
- Questions raised for future investigation

## Format

One file per significant observation. Minimal structure to reduce friction:

```markdown
# Title

**Status:** open | resolved | wontfix
**Date:** YYYY-MM-DD
**Simulation:** path/to/run.jsonl (if applicable)
**Related:** Plan #N, Issue #N, etc.

---

[Freeform content - observations, analysis, questions, uncertainties, etc.]
```

**Status values:**
- `open` - Issue identified, not yet addressed
- `resolved` - Fixed or addressed (add resolution notes)
- `wontfix` - Decided not to address (document why)

## Naming Convention

`YYYY-MM-DD_short_description.md`

Examples:
- `2026-01-16_agent_paralysis.md`
- `2026-01-17_escrow_race_condition.md`

## Finding Learnings

```bash
# All open issues
grep -l "Status.*open" docs/simulation_learnings/*.md

# Related to a specific plan
grep -l "Plan #59" docs/simulation_learnings/*.md
```

## Relationship to Plans

Simulation learnings may spawn new plans when:
- A bug needs fixing (create plan or issue)
- An architecture change is needed (create plan)
- A new feature would help (create plan)

But not everything needs a plan - some learnings are just observations or questions for future reference.
