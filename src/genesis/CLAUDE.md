# Genesis Module (Plan #298)

Config-driven genesis artifact loading. Separates genesis data (sample agents, documentation) from kernel code.

## Purpose

Genesis artifacts are cold-start conveniences - pre-seeded artifacts that solve the bootstrap problem. They are NOT kernel features; agents could build equivalents.

This module reads YAML config files and creates artifacts, keeping world.py focused on kernel primitives.

## Files

| File | Purpose |
|------|---------|
| `__init__.py` | Package exports (`load_genesis`) |
| `schema.py` | Pydantic models for YAML validation |
| `loader.py` | Reads config, creates artifacts |

## Usage

```python
from src.genesis import load_genesis

# Called by SimulationRunner after World creation
load_genesis(world, Path("config/genesis"))
```

## Config Structure

```
config/genesis/
├── kernel/          # Kernel infrastructure (mint_agent, llm_gateway)
├── artifacts/       # Standalone artifacts (handbook)
└── agents/          # Genesis agents (future: alpha_prime)
```

See `config/genesis/SCHEMA.md` for YAML format documentation.
