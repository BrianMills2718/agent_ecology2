# Kernel Genesis Manifests

YAML manifests for kernel infrastructure artifacts created at world bootstrap.

## Files

| File | Purpose |
|------|---------|
| `mint_agent.yaml` | Mint authority agent (creates scrip) |
| `llm_gateway.yaml` | LLM gateway artifact manifest |
| `llm_gateway_code.py` | Actual gateway implementation |

## Relationship to World

These manifests define artifacts that `src/genesis/loader.py` creates during world initialization. They replace embedded code strings that were previously in `world.py`.

## Schema

See `config/genesis/SCHEMA.md` for YAML format documentation.
