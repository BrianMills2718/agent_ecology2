# Genesis Artifacts

Cold-start conveniences that wrap kernel primitives. These are NOT privileged - agents could build equivalents.

**Key principle:** Genesis artifacts use the same `kernel_state` and `kernel_actions` interfaces as agent-built artifacts. They have no special access.

## Available Genesis Artifacts

| Artifact | Purpose | Wraps Kernel Primitive |
|----------|---------|------------------------|
| `genesis_ledger` | Balances, transfers | `kernel_actions.transfer_scrip()`, `create_principal()` |
| `genesis_mint` | Auction-based scoring | `kernel_actions.credit_resource()` |
| `genesis_store` | Artifact discovery | `kernel_state.get_artifact_metadata()` |
| `genesis_escrow` | Trustless trading | `kernel_actions.transfer_ownership()` |
| `genesis_debt_contract` | Credit/lending | `kernel_actions.transfer_scrip()` |
| `genesis_event_log` | Passive observability | Read-only log access |
| `genesis_rights_registry` | Quota management | `kernel_actions.transfer_quota()` |
| `genesis_model_registry` | LLM model access | Quota-based model access |
| `genesis_memory` | Agent memory storage | Artifact read/write |

## Implementation Pattern

Each genesis artifact:
1. Inherits from `GenesisArtifact` base class
2. Registers methods via `register_method()`
3. Uses injected `kernel_state` / `kernel_actions` for all operations
4. Has no direct access to World internals

```python
class GenesisLedger(GenesisArtifact):
    def _transfer(self, args, invoker_id):
        # Uses kernel_actions, NOT direct ledger access
        return self._kernel_actions.transfer_scrip(from_id, to_id, amount)
```

## Testing

Genesis artifacts are tested like any other artifact - no special test infrastructure.

See `docs/architecture/current/genesis_artifacts.md` for detailed documentation.
