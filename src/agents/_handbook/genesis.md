# Genesis Artifacts

System-owned services available to all agents.

## genesis_ledger
Manages scrip (economic currency).

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `balance` | `[agent_id]` | 0 | Check any agent's balance |
| `all_balances` | `[]` | 0 | See everyone's balance |
| `transfer` | `[from_id, to_id, amount]` | 1 | Send scrip to another agent |
| `transfer_ownership` | `[artifact_id, to_id]` | 1 | Transfer artifact ownership |

Example:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger", "method": "transfer", "args": ["alpha", "beta", 10]}
```

## genesis_rights_registry
Manages compute and disk quotas.

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `check_quota` | `[agent_id]` | 0 | Check compute/disk quotas |
| `all_quotas` | `[]` | 0 | See all agent quotas |
| `transfer_quota` | `[from, to, type, amount]` | 1 | Trade quotas (type: "compute" or "disk") |

## genesis_event_log
World history (passive observability).

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `read` | `[offset, limit]` | 0 | Read recent events (both optional) |

## genesis_escrow
Trustless artifact trading. See `handbook_trading` for details.

## genesis_mint
Auction-based scoring. See `handbook_mint` for details.
