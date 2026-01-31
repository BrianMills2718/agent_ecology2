# Architecture Documentation

Structured documentation of system architecture.

## Directory Structure

```
architecture/
├── current/    # What IS implemented (source of truth)
├── target/     # What we WANT (aspirational)
└── gaps/       # Gap analysis summary (detailed worksheets in external archive)
```

## Current vs Target

| Directory | Purpose | Trust Level |
|-----------|---------|-------------|
| `current/` | Describes actual implementation | High - should match code |
| `target/` | Describes desired future state | Reference only - verify before using |
| `gaps/` | Gap analysis summary | Reference - summary index of 142 gaps |

## Gap Tracking

| Location | Content | Purpose |
|----------|---------|---------|
| `docs/plans/` | Active implementation plans | Tracking status, ownership |
| `gaps/GAPS_SUMMARY.yaml` | Gap index by workstream | Reference during plan creation |
| External archive | Detailed gap worksheets | Historical reference |

**Methodology:** See `meta-process/patterns/30_gap-analysis.md` (Pattern #30)

## Working on Architecture

1. **Implementing a feature?**
   - Read `current/` for how things work now
   - Read `target/` for the vision
   - Check `gaps/GAPS_SUMMARY.yaml` for gap context
   - Follow plan in `docs/plans/`

2. **Finished implementing?**
   - Update `current/` to reflect new reality
   - Update plan status in `docs/plans/`

3. **Making architecture decisions?**
   - Update `target/` with new vision
   - Document rationale in `docs/DESIGN_CLARIFICATIONS.md`
   - Consider re-running gap analysis on affected workstreams (Pattern #30)
