# Configuration Directory

All runtime configuration lives here. No magic numbers in code.

## Files

| File | Purpose |
|------|---------|
| `config.yaml` | Runtime values (the one you edit) |

## Key Sections in config.yaml

| Section | What it controls |
|---------|------------------|
| `resources` | Stock (llm_budget, disk) and flow (compute) resources |
| `scrip` | Starting currency amount |
| `costs` | Token costs per 1K input/output |
| `genesis` | Which genesis artifacts enabled, method costs |
| `executor` | Timeout, preloaded imports |
| `llm` | Default model, timeout, rate limit delay |
| `execution` | Autonomous loop settings |
| `budget` | Global API cost limit, checkpoint settings |
| `dashboard` | Server host/port |
| `memory` | Qdrant/Mem0 settings |

## Config Access in Code

```python
from src.config import get, get_validated_config

# Dict access (legacy)
value = get("genesis.mint.mint_ratio")

# Typed access (preferred)
config = get_validated_config()
ratio = config.genesis.mint.mint_ratio  # Type-safe
```

## Validation

All config validated at startup via Pydantic (`src/config_schema.py`).
Typos and invalid values fail immediately with clear errors.

## Hierarchical Defaults

Schema has sensible defaults for everything. You only need to specify overrides:

```yaml
# Minimal config - everything else uses defaults
# Simulation runs in autonomous mode by default (no tick limits)
execution:
  use_autonomous_loops: true
```

## Doc Coupling

Changes to `src/config.py` or `src/config_schema.py` require updating:
- `docs/architecture/current/configuration.md`

## Environment Variables

API keys should be in `.env` (gitignored):

```bash
GEMINI_API_KEY=your_key_here
# or
OPENAI_API_KEY=your_key_here
```
