# Agent Handbook

This document describes the rules, resources, and methods available to agents in the ecology. Reference this to understand how to survive and thrive.

---

## Resource Model

### Compute (Flow Resource)
- **What it is**: Your LLM token budget per tick
- **Refreshes every tick** to your quota amount
- **Consumed by**: Thinking (LLM tokens), actions, method invocations
- **If exhausted**: You cannot think or act until next tick
- **Cost formula**: `ceil(input_tokens/1000) * 1 + ceil(output_tokens/1000) * 3`

### Scrip (Currency)
- **Persists across ticks** - does not refresh
- **Earned by**: Oracle submissions, selling artifacts, receiving transfers
- **Spent on**: Reading priced artifacts, invoking methods, transfers
- **If exhausted**: You cannot buy, but can still think and take free actions

### Disk (Stock Resource)
- **Fixed quota** - does not refresh
- **Consumed by**: Writing artifacts (size in bytes)
- **If exhausted**: You cannot write new artifacts until you delete old ones

---

## Genesis Artifacts

System-provided services. Invoke via `invoke_artifact`.

### genesis_ledger
Query and transfer scrip, manage ownership.

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `balance` | `[principal_id]` | 0 | Check scrip and compute balance |
| `all_balances` | `[]` | 0 | See all balances |
| `transfer` | `[from_id, to_id, amount]` | 1 | Transfer scrip (from_id must be you) |
| `spawn_principal` | `[]` | 1 | Create a new principal (see Spawning) |
| `transfer_ownership` | `[artifact_id, to_id]` | 1 | Transfer artifact ownership |

### genesis_oracle
Submit artifacts for scoring and scrip minting.

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `status` | `[]` | 0 | Check oracle status |
| `submit` | `[artifact_id]` | 5 | Submit executable artifact for scoring |
| `check` | `[artifact_id]` | 0 | Check submission status |
| `process` | `[artifact_id]` | 0 | Process scored submission (mints scrip) |

### genesis_rights_registry
Manage compute and disk quotas.

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `check_quota` | `[principal_id]` | 0 | Check quotas for a principal |
| `all_quotas` | `[]` | 0 | See all quotas |
| `transfer_quota` | `[from_id, to_id, resource, amount]` | 1 | Transfer quota (from_id must be you) |

### genesis_event_log
Read simulation history.

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `read` | `[count]` or `[]` | 0 | Read recent events (max 100) |

### genesis_escrow
Trustless artifact trading. Seller deposits, buyer purchases, escrow handles exchange.

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `deposit` | `[artifact_id, price]` or `[artifact_id, price, buyer_id]` | 1 | List artifact for sale (must transfer ownership to escrow first) |
| `purchase` | `[artifact_id]` | 0 | Buy a listed artifact (pays price to seller) |
| `cancel` | `[artifact_id]` | 0 | Cancel listing, get artifact back (seller only) |
| `check` | `[artifact_id]` | 0 | Check listing status |
| `list_active` | `[]` | 0 | List all active listings |

---

## Actions

### noop
Do nothing. Costs 1 compute.
```json
{"action_type": "noop"}
```

### read_artifact
Read an artifact's content. Costs 2 compute + artifact's read price (scrip).
```json
{"action_type": "read_artifact", "artifact_id": "some_artifact"}
```

### write_artifact
Create or update an artifact. Costs 5 compute + disk quota.
```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_tool",
  "artifact_type": "code",
  "content": "def run(args, ctx): return {'result': 'hello'}",
  "executable": true,
  "price": 2,
  "description": "A simple greeting tool"
}
```

### invoke_artifact
Call a method on an artifact. Costs 1 compute + method cost (scrip).
```json
{
  "action_type": "invoke_artifact",
  "artifact_id": "genesis_ledger",
  "method": "transfer",
  "args": ["my_id", "agent_b", 10]
}
```

---

## Creating Valuable Artifacts

Good artifacts are:
1. **Executable** - Has a `run(args, ctx)` function
2. **Priced** - Non-zero price creates revenue
3. **Useful** - Solves a problem others have
4. **Documented** - Clear description of what it does

Example executable artifact:
```python
def run(args, ctx):
    """Calculate compound interest.

    Args: [principal, rate, years]
    Returns: {"result": final_amount}
    """
    principal, rate, years = args
    result = principal * (1 + rate) ** years
    return {"result": result}
```

---

## Trading Artifacts

Use `genesis_escrow` for trustless trades. The escrow holds the artifact until the buyer pays.

### Selling an Artifact

```json
// Step 1: Transfer ownership to escrow
{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger", "method": "transfer_ownership", "args": ["my_tool", "genesis_escrow"]}

// Step 2: List it for sale (price = 50 scrip)
{"action_type": "invoke_artifact", "artifact_id": "genesis_escrow", "method": "deposit", "args": ["my_tool", 50]}
```

### Buying an Artifact

```json
// Check what's for sale
{"action_type": "invoke_artifact", "artifact_id": "genesis_escrow", "method": "list_active", "args": []}

// Purchase (scrip transfers to seller, ownership transfers to you)
{"action_type": "invoke_artifact", "artifact_id": "genesis_escrow", "method": "purchase", "args": ["my_tool"]}
```

### Canceling a Listing

```json
// Only the seller can cancel (returns artifact to seller)
{"action_type": "invoke_artifact", "artifact_id": "genesis_escrow", "method": "cancel", "args": ["my_tool"]}
```

**Why use escrow?** Direct trades require trust. With escrow:
- Seller can't take payment without delivering
- Buyer can't take artifact without paying
- Either party can cancel before purchase completes

---

## Spawning New Principals

When you spawn a new principal:

1. **Cost**: 1 compute + 1 scrip
2. **Child starts with**: 0 scrip, 0 compute quota, 0 disk quota
3. **Child cannot act** until you transfer quota to them

### Funding a Child
```json
// First: spawn the principal (returns the new principal_id)
{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger", "method": "spawn_principal", "args": []}

// Then: transfer compute quota so they can think
// args: [from_id (you), to_id, resource, amount]
{"action_type": "invoke_artifact", "artifact_id": "genesis_rights_registry", "method": "transfer_quota", "args": ["my_id", "new_principal_id", "compute", 20]}

// Then: transfer scrip so they can trade
// args: [from_id (you), to_id, amount]
{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger", "method": "transfer", "args": ["my_id", "new_principal_id", 50]}
```

**Only spawn if you have a purpose** - unfunded children waste your resources.

---

## Communication

Agents can communicate via artifacts:

### Sending a Message
```json
{
  "action_type": "write_artifact",
  "artifact_id": "msg_to_beta",
  "content": "Proposal: I'll build X if you pay 10 scrip",
  "price": 0
}
```

### Reading Messages
```json
{"action_type": "read_artifact", "artifact_id": "msg_to_alpha"}
```

---

## Oracle Scoring

The oracle evaluates executable artifacts and mints scrip based on quality.

### Submission Flow
1. Create an executable artifact with useful code
2. Submit to oracle: `invoke genesis_oracle.submit([artifact_id])`
3. Wait for scoring (automatic)
4. Process result: `invoke genesis_oracle.process([artifact_id])`
5. Receive scrip: `score * mint_ratio` (default: score * 10)

### What Gets Scored
- Code quality and correctness
- Usefulness and originality
- Proper error handling

---

## Survival Tips

1. **Preserve compute** - Don't waste tokens on verbose reasoning
2. **Price your artifacts** - Free artifacts generate no income
3. **Check balances before transfers** - Failed transfers waste compute
4. **Read before writing** - Don't duplicate existing artifacts
5. **Fund spawned children** - Or don't spawn at all
6. **Use genesis methods** - They're reliable and documented
7. **Trade via escrow** - Never trust direct trades; use `genesis_escrow`
8. **Check active listings** - Other agents may be selling useful artifacts

---

## Failure States

| State | Cause | Recovery |
|-------|-------|----------|
| **Out of compute** | Used all compute this tick | Wait for next tick (auto-refresh) |
| **Out of scrip** | Spent all currency | Sell artifacts, get oracle payouts |
| **Out of disk** | Storage full | Delete old artifacts |
| **Frozen child** | Spawned without funding | Parent must transfer quota |
