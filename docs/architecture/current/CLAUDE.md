# Current Architecture Documentation

These docs describe what IS implemented today. They are the source of truth for current behavior.

## When Working Here

- **After any code change in src/**, update the relevant doc here
- **CI enforces this** via doc-code coupling (strict)
- **Update "Last verified" date** at top of each file you modify

## File Purposes

| File | Describes |
|------|-----------|
| `README.md` | Architecture overview and system summary |
| `execution_model.md` | Tick loop, two-phase commit, timing |
| `agents.md` | Agent lifecycle, thinking, memory |
| `agent_cognition.md` | Agent decision-making, memory, and learning systems |
| `contracts.md` | Contract system and access control |
| `coordination_patterns.md` | How agents coordinate using existing primitives |
| `resources.md` | Flow/stock resources, scrip, ledger |
| `genesis_artifacts.md` | System services (ledger, mint, escrow) |
| `genesis_agents.md` | Default agents that ship with the system |
| `mint.md` | Artifact scoring and scrip minting |
| `artifacts_executor.md` | Artifact storage, policies, code execution |
| `configuration.md` | Config loading, Pydantic validation |
| `running.md` | Practical guide to running simulations |
| `supporting_systems.md` | Checkpoint, logging, dashboard |
| `ci.md` | GitHub Actions CI pipeline |

## Coupling to Source

These files are strictly coupled to source:

| Source | Doc |
|--------|-----|
| `src/simulation/runner.py`, `src/world/world.py` | `execution_model.md` |
| `src/world/ledger.py`, `src/world/simulation_engine.py` | `resources.md` |
| `src/world/genesis.py` | `genesis_artifacts.md` |
| `src/agents/*.py` | `agents.md` |
| `src/world/artifacts.py`, `executor.py`, `actions.py` | `artifacts_executor.md` |
| `src/config.py`, `src/config_schema.py` | `configuration.md` |

## Verification Command

```bash
python scripts/check_doc_coupling.py --suggest
```
