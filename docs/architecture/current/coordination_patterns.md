# Coordination Patterns

How agents coordinate using existing primitives. No kernel changes needed.

**Last verified:** 2026-02-05 (Plan #295: ledger cleanup - removed starting_compute from create_principal)

---

## Overview

Coordination in the ecology emerges from four primitives:

| Primitive | What It Provides | Coordination Use |
|-----------|------------------|------------------|
| `genesis_escrow` | Atomic custody transfer | Trustless trading |
| `genesis_ledger` | Value transfer, ownership | Payment, ownership |
| `genesis_event_log` | Observable history | Reputation, audit |
| Contracts (executables) | Programmable access | Gates, agreements |

Agents compose these to build coordination patterns. The kernel provides physics; agents build social structure.

---

## Pattern 1: Trustless Trading

**Problem:** Two agents want to exchange an artifact for scrip without trusting each other.

**Solution:** Use `genesis_escrow` as neutral custodian.

### Workflow

```
1. Seller: invoke("genesis_escrow", "deposit", artifact_id, price)
   → Escrow takes custody of artifact

2. Buyer: invoke("genesis_escrow", "purchase", artifact_id)
   → Escrow atomically: deducts scrip from buyer, transfers artifact ownership

3. Or: invoke("genesis_escrow", "cancel", artifact_id)  [seller only]
   → Escrow returns artifact to seller
```

### Why It Works

- **Atomic execution:** Both scrip and artifact transfer happen in single action
- **No trust required:** Escrow holds custody; neither party can cheat
- **Reversible:** Seller can cancel before purchase

### Example Agent Code

```python
# Seller listing an artifact
def run():
    # List my artifact for 50 scrip
    result = invoke("genesis_escrow", "deposit", "my_artifact", 50)
    return result

# Buyer purchasing
def run():
    # Check listing first
    listing = invoke("genesis_escrow", "check", "some_artifact")
    if listing["success"] and listing["result"]["price"] <= get_balance():
        return invoke("genesis_escrow", "purchase", "some_artifact")
    return {"error": "Cannot afford or not listed"}
```

### Discovery Integration

Buyers find artifacts to purchase via `query_kernel` action:

```python
def run():
    # Find all listings
    listings = invoke("genesis_escrow", "list_active")

    # Or search artifacts by criteria using query_kernel action
    # query_kernel returns artifact metadata from the kernel directly
    tools = query_kernel("artifacts", {"name_contains": "parser"})
    return {"listings": listings, "tools": tools}
```

---

## Pattern 2: Pay-per-use Services

**Problem:** An agent wants to monetize an artifact (tool, data, service).

**Solution:** Set `invoke_price` in artifact policy.

### Configuration

```python
# When creating the artifact
policy = {
    "read_price": 0,       # Free to read description
    "invoke_price": 5,     # 5 scrip per invocation
    "allow_invoke": ["*"]  # Anyone can invoke (who pays)
}
```

### Workflow

```
1. Provider: write_artifact(artifact_id, code, policy={invoke_price: 5})
   → Service deployed with pricing

2. Consumer: invoke(artifact_id, method, args)
   → Consumer pays 5 scrip to provider automatically
   → Service executes and returns result
```

### Why It Works

- **Automatic billing:** Kernel enforces payment before execution
- **No intermediary:** Payment flows directly provider → consumer
- **Market pricing:** Providers compete on price and quality

### Example: Data Aggregation Service

```python
# Provider creates a market data service
def run():
    # Aggregate from multiple sources (expensive operation)
    prices = fetch_from_sources()  # Uses provider's compute
    return {"prices": prices, "timestamp": time.time()}
```

Consumers invoke and pay only for what they use:

```python
# Consumer queries service
def run():
    data = invoke("market_data_service", "run")
    if data["success"]:
        return analyze(data["result"])
    return {"error": data["error"]}
```

### Tiered Access Pattern

Different methods can have different prices:

```python
def run(method, *args):
    if method == "summary":
        return get_summary()      # Base cost only
    elif method == "detailed":
        return get_detailed()     # Costs more compute
    elif method == "premium":
        # Check caller paid premium rate
        if not verify_premium(caller_id):
            return {"error": "Premium access required"}
        return get_premium_data()
```

---

## Pattern 3: Multi-party Agreements

**Problem:** Multiple parties need to agree before an action executes.

**Solution:** Contract holds state, requires threshold of approvals.

### Threshold Contract Pattern

```python
# Contract state (stored in artifact content)
state = {
    "proposal": "Transfer 1000 scrip to project X",
    "required_approvals": 3,
    "approvals": []
}

def run(action, *args):
    if action == "approve":
        caller = args[0] if args else caller_id
        if caller not in state["approvals"]:
            state["approvals"].append(caller)

        if len(state["approvals"]) >= state["required_approvals"]:
            # Execute the agreed action
            execute_transfer()
            return {"status": "executed", "approvals": state["approvals"]}

        return {"status": "pending", "approvals": len(state["approvals"])}

    elif action == "status":
        return state
```

### Workflow

```
1. Creator: write_artifact(agreement_id, contract_code, ...)
   → Agreement deployed

2. Party A: invoke(agreement_id, "approve")
   → Approval recorded

3. Party B: invoke(agreement_id, "approve")
   → Approval recorded

4. Party C: invoke(agreement_id, "approve")
   → Threshold reached, action executes
```

### Escrow with Arbitration

Extend basic escrow with dispute resolution:

```python
state = {
    "seller": None,
    "buyer": None,
    "arbitrator": "trusted_agent",
    "artifact_id": None,
    "status": "open"
}

def run(action, *args):
    if action == "deposit":
        # Seller deposits artifact
        state["seller"] = caller_id
        state["artifact_id"] = args[0]
        transfer_to_contract(args[0])
        return {"status": "awaiting_buyer"}

    elif action == "accept":
        # Buyer accepts, funds escrowed
        state["buyer"] = caller_id
        # Hold buyer's funds
        return {"status": "in_progress"}

    elif action == "complete":
        # Buyer confirms delivery
        if caller_id == state["buyer"]:
            release_to_seller()
            return {"status": "complete"}

    elif action == "dispute":
        # Either party can dispute
        state["status"] = "disputed"
        return {"status": "disputed", "arbitrator": state["arbitrator"]}

    elif action == "resolve":
        # Only arbitrator can resolve
        if caller_id == state["arbitrator"]:
            winner = args[0]  # "seller" or "buyer"
            resolve_dispute(winner)
            return {"status": "resolved", "winner": winner}
```

---

## Pattern 4: Reputation Systems

**Problem:** Agents need to assess trustworthiness without central authority.

**Solution:** Analyze `genesis_event_log` to compute reputation.

### Event Log as Reputation Source

```python
def run(method, agent_id):
    if method == "compute_reputation":
        # Read agent's history
        events = invoke("genesis_event_log", "read", 1000, 0, {
            "agent_id": agent_id
        })

        if not events["success"]:
            return {"error": "Cannot read events"}

        # Compute metrics
        actions = events["result"]
        return {
            "total_actions": len(actions),
            "successful_invocations": count_successful(actions),
            "contracts_honored": count_completed_contracts(actions),
            "disputes_lost": count_lost_disputes(actions)
        }
```

### Reputation-Gated Access

Contracts can check reputation before granting access:

```python
def run(action, *args):
    if action == "request_membership":
        # Check requester's reputation
        rep = invoke("reputation_service", "compute_reputation", caller_id)

        if rep["success"]:
            score = rep["result"]
            if score["contracts_honored"] >= 10 and score["disputes_lost"] == 0:
                grant_membership(caller_id)
                return {"status": "approved"}

        return {"status": "denied", "reason": "Insufficient reputation"}
```

### Observable Actions Enable Trust

All actions are logged, enabling:

| Metric | Source | Meaning |
|--------|--------|---------|
| Trade history | `genesis_escrow` events | Reliable trading partner |
| Payment history | `genesis_ledger` events | Pays debts on time |
| Contract completion | Custom contract logs | Honors agreements |
| Service uptime | Invocation success rate | Reliable provider |

---

## Pattern 5: Gatekeeper Contracts

**Problem:** Resource access needs dynamic rules beyond static allow lists.

**Solution:** Contract-managed access with programmable logic.

### Gatekeeper Pattern

```python
# Gatekeeper owns the protected artifact
# Controls access via policy logic

state = {
    "protected_artifact": "valuable_data",
    "access_rules": {
        "min_reputation": 5,
        "min_balance": 100,
        "blacklist": []
    }
}

def run(action, *args):
    if action == "request_access":
        # Check eligibility
        if caller_id in state["access_rules"]["blacklist"]:
            return {"allowed": False, "reason": "blacklisted"}

        balance = kernel_state.get_balance(caller_id)
        if balance < state["access_rules"]["min_balance"]:
            return {"allowed": False, "reason": "insufficient_balance"}

        # Grant access by reading on their behalf
        data = kernel_state.read_artifact(state["protected_artifact"], caller_id)
        return {"allowed": True, "data": data}

    elif action == "update_rules":
        # Only owner can update rules
        if caller_id == owner_id:
            state["access_rules"].update(args[0])
            return {"updated": True}
```

### Why Gatekeeper Works

- **Dynamic rules:** Logic can change without modifying kernel
- **Composable:** Gatekeepers can check other gatekeepers
- **Observable:** All access requests are logged actions

---

## Pattern 6: Resource Pooling

**Problem:** Agents want to share resources for mutual benefit.

**Solution:** Pool contract manages shared ownership and distribution.

### Pool Contract Structure

```python
state = {
    "members": [],
    "contributions": {},  # member -> amount
    "total_pool": 0
}

def run(action, *args):
    if action == "join":
        contribution = args[0]
        # Transfer scrip to pool
        kernel_actions.transfer_scrip(caller_id, artifact_id, contribution)
        state["members"].append(caller_id)
        state["contributions"][caller_id] = contribution
        state["total_pool"] += contribution
        return {"joined": True, "share": contribution / state["total_pool"]}

    elif action == "withdraw":
        if caller_id in state["members"]:
            share = state["contributions"][caller_id]
            kernel_actions.transfer_scrip(artifact_id, caller_id, share)
            state["members"].remove(caller_id)
            state["total_pool"] -= share
            del state["contributions"][caller_id]
            return {"withdrawn": share}

    elif action == "distribute":
        # Distribute earnings proportionally
        earnings = args[0]
        for member in state["members"]:
            share = state["contributions"][member] / state["total_pool"]
            payout = int(earnings * share)
            kernel_actions.transfer_scrip(artifact_id, member, payout)
        return {"distributed": earnings}
```

---

## Composing Patterns

Patterns combine for complex coordination:

### Example: Cooperative Service

```
┌─────────────────────────────────────────────────┐
│                 Service Pool                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Provider │  │ Provider │  │ Provider │       │
│  │    A     │  │    B     │  │    C     │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       └──────────┬──┴──────────────┘            │
│                  ▼                               │
│          Pool Contract                           │
│     (threshold decisions,                        │
│      revenue distribution)                       │
└─────────────────┬───────────────────────────────┘
                  │
                  ▼ pay-per-use
          ┌───────────────┐
          │   Consumer    │
          └───────────────┘
```

1. Providers join pool (Pattern 6)
2. Pool offers service at price (Pattern 2)
3. Consumers pay pool
4. Pool distributes revenue (Pattern 6)
5. Major decisions require threshold (Pattern 3)
6. Reputation tracks reliability (Pattern 4)

---

## Key Principles

### 1. Contracts Enable, Don't Enforce

Contracts provide coordination *mechanisms*, not guarantees. Agents who violate norms face reputation consequences, not kernel punishment.

### 2. Escrow for Atomicity

When exchanges must be atomic (both happen or neither), use escrow. For ongoing relationships, reputation may suffice.

### 3. Events for Accountability

The event log makes all actions observable. Reputation emerges from this observability, not from kernel enforcement.

### 4. Compose, Don't Monolith

Simple contracts that compose > complex monolithic systems. Each pattern solves one problem well.

---

## Key Files

| File | What It Provides |
|------|------------------|
| `src/world/genesis.py` | Genesis artifact implementations |
| `src/world/executor.py` | Contract execution with kernel access |
| `src/world/kernel_interface.py` | Kernel state/action APIs for contracts |
| `docs/architecture/current/genesis_artifacts.md` | Genesis method reference |
| `docs/architecture/current/artifacts_executor.md` | Executor and policy details |
