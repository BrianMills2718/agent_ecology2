# World Module - Core Simulation Kernel

This is the heart of the simulation. All world state, resources, and execution live here.

## Module Responsibilities

| File | Responsibility |
|------|----------------|
| `world.py` | Central state manager, tick lifecycle, artifact store |
| `ledger.py` | Resource accounting (flow/stock), scrip balances, transfers |
| `artifacts.py` | Artifact storage, policies, ownership |
| `executor.py` | Safe code execution, invoke() support, timeout protection |
| `actions.py` | Action definitions (noop, read, write, invoke) |
| `genesis.py` | System artifacts (ledger, mint, escrow, event_log, store) |
| `genesis_contracts.py` | Built-in access control contracts |
| `contracts.py` | Contract types and permission checking |
| `kernel_interface.py` | KernelState/KernelActions for artifact sandbox |
| `invocation_registry.py` | Track artifact invocations |
| `rate_tracker.py` | Token bucket rate limiting |
| `simulation_engine.py` | API budget tracking, token costs |
| `mcp_bridge.py` | MCP server integration |
| `mint_scorer.py` | LLM-based artifact scoring for auctions |
| `errors.py` | Error response conventions |
| `logger.py` | Event logging to JSONL |

## Key Patterns

### Kernel Interfaces (Plan #39)
Artifacts access kernel state via injected interfaces:
```python
def run():
    balance = kernel_state.get_balance("alice")  # Read-only
    kernel_actions.transfer_scrip(caller_id, "bob", 50)  # Write with verification
```

### Genesis Artifacts Are Not Privileged
Genesis artifacts use the same kernel interfaces as agent-built artifacts.
They're cold-start conveniences, not special code.

### Ledger Uses Decimal
```python
from decimal import Decimal
scrip_balance: Decimal  # Precision for monetary values
```

## Strict Couplings

Changes here MUST update `docs/architecture/current/`:

| Source | Doc |
|--------|-----|
| `world.py` | `execution_model.md` |
| `ledger.py`, `simulation_engine.py` | `resources.md` |
| `genesis.py` | `genesis_artifacts.md` |
| `artifacts.py`, `executor.py`, `kernel_interface.py` | `artifacts_executor.md` |

## Testing

```bash
pytest tests/unit/test_ledger.py tests/unit/test_executor.py tests/integration/test_escrow.py -v
```
