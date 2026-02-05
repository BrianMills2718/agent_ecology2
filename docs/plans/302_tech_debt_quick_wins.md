# Plan #302: Tech Debt Quick Wins (TD-011 through TD-014)

**Status:** In Progress

**Problem:** Codebase audit (2026-02-05) identified 4 low-risk, well-defined tech debt items that can be fixed together.

## Changes

### TD-014: Fix dashboard assess_health() type mismatch
- `server.py:184` calls `assess_health(self.parser.state, self.thresholds)` but function expects `(kpis, prev_kpis, thresholds, total_agents)`
- Fix: match the correct call pattern already at line 938

### TD-013: Fix stale doc/config references
- `CORE_SYSTEMS.md:199` - agent_loop.py mislabeled "legacy, unused" (it IS used)
- `CORE_SYSTEMS.md:200` - references deleted `pool.py`
- `resources.md:355,377` - code examples from deleted `worker.py`
- `config.yaml:153,215` - stale "tick"/"due_tick" terminology
- `config_schema.py:336,551,569` - same stale terminology

### TD-012: Wire hardcoded mint auction params to config
- `mint_auction.py:91-93` hardcodes `delay=30, window=60, period=120`
- `mint_auction.py:361` hardcodes `mint_ratio=10`
- Config already exists at `genesis.mint.auction.*` and `genesis.mint.mint_ratio`
- Fix: pass config values through `__init__()` from `world.py`

### TD-011: Add event logging to ledger mutations
- Ledger has zero logging despite being source of truth for all balances
- EventLogger already has helper methods (`log_resource_consumed`, etc.)
- Fix: add optional `logger` to Ledger, log scrip mutations

## Verification
```bash
make check
pytest tests/unit/test_ledger.py tests/integration/test_runner.py -v
```
