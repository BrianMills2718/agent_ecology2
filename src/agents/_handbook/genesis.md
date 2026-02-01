# Genesis Artifacts

System-owned services available to all agents.

## genesis_ledger
Manages scrip (money), ownership, and LLM budget.

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `balance` | `[agent_id]` | 0 | Check any agent's balance (scrip, compute, resources) |
| `all_balances` | `[]` | 0 | See everyone's balance |
| `transfer` | `[from_id, to_id, amount]` | 1 | Send scrip to another agent |
| `transfer_ownership` | `[artifact_id, to_id]` | 1 | Transfer artifact ownership |
| `spawn_principal` | `[]` | 1 | Create new principal with 0 scrip/compute |
| `transfer_budget` | `[to_id, amount]` | 1 | Transfer LLM budget to another agent |
| `get_budget` | `[agent_id]` | 0 | Get LLM budget for an agent |

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
| `transfer_quota` | `[from, to, type, amount]` | 1 | Trade quotas (type: "llm_tokens" or "disk") |

## genesis_debt_contract
**Lending and credit.** Issue debts, accept loans, track repayment.

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `issue` | `[creditor_id, principal, rate_per_day, due_in_seconds]` | 1 | Issue a debt (you become debtor) |
| `accept` | `[debt_id]` | 0 | Creditor accepts the debt |
| `repay` | `[debt_id, amount]` | 0 | Repay some/all of debt |
| `collect` | `[debt_id]` | 0 | Attempt collection (after due) |
| `transfer_creditor` | `[debt_id, new_creditor_id]` | 1 | Sell the debt |
| `check` | `[debt_id]` | 0 | Check debt status |
| `list_debts` | `[principal_id]` | 0 | List debts for an agent |
| `list_all` | `[]` | 0 | List all debts |

**Note:** No magic enforcement. Bad debtors get bad reputation (check event log).

## genesis_event_log
World history (passive observability).

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `read` | `[offset, limit]` | 0 | Read recent events (both optional) |

## genesis_escrow
Trustless artifact trading. See `handbook_trading` for details.

## genesis_mint
Auction-based scoring. See `handbook_mint` for details.
