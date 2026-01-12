# Architecture Documentation

Structured documentation of system architecture.

## Directory Structure

```
architecture/
├── current/    # What IS implemented (source of truth)
├── target/     # What we WANT (aspirational)
└── gaps/       # Gap tracking system (single source of truth)
    ├── CLAUDE.md           # Master index with epics and status
    ├── GAPS_SUMMARY.yaml   # Overview and metrics
    ├── ws*.yaml            # Detailed gap definitions by workstream
    └── plans/              # Implementation plans
```

## Current vs Target

| Directory | Purpose | Trust Level |
|-----------|---------|-------------|
| `current/` | Describes actual implementation | High - should match code |
| `target/` | Describes desired future state | Reference only - verify before using |
| `gaps/` | Gap tracking and implementation | **Single source of truth for gaps** |

## Gap Tracking

**Single source:** `gaps/CLAUDE.md`

| Content | Location |
|---------|----------|
| Epic status (31 high-level features) | `gaps/CLAUDE.md` |
| Sub-gap status (142 detailed gaps) | `gaps/CLAUDE.md` |
| Gap definitions | `gaps/ws*.yaml` |
| Implementation plans | `gaps/plans/*.md` |
| CC coordination | `gaps/CLAUDE.md` |

## Working on Architecture

1. **Implementing a feature?**
   - Read `current/` for how things work now
   - Read `target/` for the vision
   - Check `gaps/CLAUDE.md` for epic and sub-gap status
   - Check `gaps/ws*.yaml` for detailed gap definition
   - Check `gaps/plans/` for implementation plan

2. **Finished implementing?**
   - Update `current/` to reflect new reality
   - Update gap status in `gaps/CLAUDE.md`

3. **Making architecture decisions?**
   - Update `target/` with new vision
   - Document rationale in `docs/DESIGN_CLARIFICATIONS.md`

## Archived

`docs/plans_archived/` contains the old 31-gap tracking system. It has been merged into `gaps/`. Do not update those files.
