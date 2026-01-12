# Target Architecture Documentation

These docs describe what we WANT to build. They are aspirational, not current reality.

## When Working Here

- **Update when making architecture decisions**
- **Do NOT treat as implementation reference** - check current/ for that
- **Mark status** if a target doc becomes outdated or implemented

## Relationship to Plans

- Target docs describe the WHAT and WHY
- Plan files in `docs/plans/` describe the HOW
- When implementing: read target for vision, follow plan for steps

## File Purposes

| File | Describes |
|------|-----------|
| `01_README.md` | Design rationale, mechanism design |
| `02_execution_model.md` | Continuous execution (not tick-based) |
| `03_agents.md` | Autonomous agents, agents-as-artifacts |
| `04_resources.md` | Token bucket, rate limiting |
| `05_contracts.md` | Contract-based access control |
| `06_mint.md` | Anytime bidding, continuous scoring, minting |
| `07_infrastructure.md` | Docker isolation, real resource limits |

## Warning

These docs may describe features that don't exist yet. Always verify against `current/` before assuming behavior.
