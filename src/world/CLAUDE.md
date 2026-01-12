# World Module - Core Simulation Kernel

This is the heart of the simulation. All world state, resources, and execution live here.

## Module Responsibilities

| File | Responsibility |
|------|----------------|
| `world.py` | Central state manager, tick lifecycle, artifact store |
| `ledger.py` | Resource accounting (flow/stock), scrip balances, transfers |
| `genesis.py` | System artifacts (ledger, oracle, escrow, event_log, rights_registry) |
| `executor.py` | Safe code execution, invoke() support, timeout protection |
| `artifacts.py` | Artifact storage, policies, ownership |
| `actions.py` | Action definitions (noop, read, write, invoke) |
| `simulation_engine.py` | API budget tracking, token costs |
| `logger.py` | Event logging to JSONL |
| `oracle_scorer.py` | LLM-based artifact scoring for auctions |

## Key Patterns

### Ledger Uses Decimal
```python
from decimal import Decimal
# All monetary values use Decimal for precision
scrip_balance: Decimal
```

### No Negative Balances
```python
# This will raise, not return False silently
ledger.deduct_resource(agent_id, "compute", amount)
```

### Genesis Artifacts Are Proxies
Genesis artifacts are not special code - they're proxies to kernel functions:
```python
# genesis_ledger.transfer() calls ledger.transfer_scrip()
# genesis_escrow.deposit() calls escrow handling in genesis.py
```

## Strict Couplings

Changes here MUST update `docs/architecture/current/`:

| Source | Doc |
|--------|-----|
| `world.py` | `execution_model.md` |
| `ledger.py`, `simulation_engine.py` | `resources.md` |
| `genesis.py` | `genesis_artifacts.md` |
| `artifacts.py`, `executor.py`, `actions.py` | `artifacts_executor.md` |

## Testing

```bash
pytest tests/test_ledger.py tests/test_executor.py tests/test_escrow.py -v
```
