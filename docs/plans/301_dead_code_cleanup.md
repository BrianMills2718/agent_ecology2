# Plan #301: Dead Code & Legacy Cleanup (Post Plan #299)

**Status:** ✅ Complete

## Summary

Remove provably dead code from runner.py and simulation module after Plan #299
eliminated the legacy agent system. Since `_create_agents()` returned `[]`, all code
iterating over `self.agents` was dead.

## Changes

| File | Change |
|------|--------|
| `src/simulation/runner.py` | Removed 18 dead methods, dead fields, dead imports (1,614 → 609 lines) |
| `src/simulation/types.py` | Removed `ActionProposal`, `ThinkingResult` TypedDicts |
| `src/simulation/__init__.py` | Removed dead exports |
| `src/simulation/pool.py` | Deleted (worker pool, never activated) |
| `src/simulation/worker.py` | Deleted (worker functions, never activated) |
| `src/world/world.py` | Removed unused TypedDicts (`PrincipalConfig`, `LoggingConfig`, `WorldConfig`) |
| `config/config.yaml` | Removed dead `memory:` section (Qdrant/Mem0) |
| `docker-compose.yml` | Removed Qdrant service |

## Impact

- ~1,600 lines removed
- mypy errors: 32 → 12 (20 eliminated)
- runner.py reduced by ~62%
