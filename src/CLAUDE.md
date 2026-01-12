# Source Directory

All production code lives here. Tests are in `tests/`.

## Module Structure

```
src/
├── config.py           # Config loading helpers
├── config_schema.py    # Pydantic validation (all config options)
├── world/              # Core simulation kernel
├── agents/             # LLM-powered agents
├── simulation/         # Runner, checkpoint
└── dashboard/          # HTML visualization server
```

## Key Entry Points

| What | Where |
|------|-------|
| Run simulation | `python run.py` (uses `simulation/runner.py`) |
| Config access | `from src.config import get, get_validated_config` |
| World state | `from src.world.world import World` |
| Agent loading | `from src.agents.loader import load_agents` |

## Design Principles

1. **Fail Loud** - No silent fallbacks. Errors fail immediately.
2. **No Magic Numbers** - All values from `config/config.yaml`
3. **Strong Typing** - `mypy --strict` compliance, Pydantic models
4. **Maximum Observability** - Log all state changes with context

## Import Pattern

```python
# Always use src. prefix
from src.config import get
from src.world.world import World
from src.world.ledger import Ledger
```

## Before Committing

```bash
pytest tests/ -v                    # Must pass
python -m mypy src/ --ignore-missing-imports  # Must pass
python scripts/check_doc_coupling.py  # Check doc updates needed
```
