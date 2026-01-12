# Architecture Documentation

Structured documentation of system architecture.

## Directory Structure

```
architecture/
├── current/    # What IS implemented (source of truth)
├── target/     # What we WANT (aspirational)
└── GAPS.md     # DEPRECATED - see docs/plans/CLAUDE.md
```

## Current vs Target

| Directory | Purpose | Trust Level |
|-----------|---------|-------------|
| `current/` | Describes actual implementation | High - should match code |
| `target/` | Describes desired future state | Reference only - verify before using |

## Working on Architecture

1. **Implementing a feature?**
   - Read `current/` for how things work now
   - Read `target/` for the vision
   - Follow plan in `docs/plans/`

2. **Finished implementing?**
   - Update `current/` to reflect new reality
   - Update plan status in `docs/plans/`

3. **Making architecture decisions?**
   - Update `target/` with new vision
   - Document rationale in `docs/DESIGN_CLARIFICATIONS.md`

## GAPS.md Status

`GAPS.md` is superseded by `docs/plans/CLAUDE.md`. It remains for historical reference and will be archived.
