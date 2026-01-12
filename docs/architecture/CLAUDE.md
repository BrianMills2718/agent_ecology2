# Architecture Documentation

Structured documentation of system architecture.

## Directory Structure

```
architecture/
├── current/    # What IS implemented (source of truth)
├── target/     # What we WANT (aspirational)
├── gaps/       # Comprehensive gap analysis (142 gaps)
└── GAPS.md     # DEPRECATED - see docs/plans/CLAUDE.md
```

## Current vs Target

| Directory | Purpose | Trust Level |
|-----------|---------|-------------|
| `current/` | Describes actual implementation | High - should match code |
| `target/` | Describes desired future state | Reference only - verify before using |
| `gaps/` | Comprehensive gap analysis | Reference - 142 detailed gaps |

## Gap Tracking

Two levels of gap documentation:

| Location | Gaps | Purpose |
|----------|------|---------|
| `docs/plans/` | 34 high-level | Active tracking (status, CC-IDs) |
| `gaps/` | 142 detailed | Comprehensive analysis (reference) |

The 142 gaps are a finer breakdown of the 34 in `docs/plans/`.

## Working on Architecture

1. **Implementing a feature?**
   - Read `current/` for how things work now
   - Read `target/` for the vision
   - Check `gaps/` for detailed gap definition
   - Follow plan in `docs/plans/`

2. **Finished implementing?**
   - Update `current/` to reflect new reality
   - Update plan status in `docs/plans/`

3. **Making architecture decisions?**
   - Update `target/` with new vision
   - Document rationale in `docs/DESIGN_CLARIFICATIONS.md`

## GAPS.md Status

`GAPS.md` is superseded by `docs/plans/CLAUDE.md`. It remains for historical reference and will be archived.
