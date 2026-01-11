# Target Resource Model

What we're building toward.

**See current:** [../current/resources.md](../current/resources.md)

---

## Resource Terminology

**Distinct resources - do not conflate:**

| Resource | Type | What it is |
|----------|------|------------|
| LLM API $ | Stock | Real dollars spent on API calls |
| LLM rate limit | Flow | Provider limits (TPM, RPM) |
| Compute | Flow | Local CPU capacity |
| Memory | Stock | Local RAM |
| Disk | Stock | Storage quota (reclaimable via delete) |
| Scrip | Currency | Internal economy, not a "resource" |

**LLM tokens ≠ Compute.** LLM tokens are API cost ($), compute is local machine capacity.

---

## Flow Resources: Token Bucket

### Rolling Window (NOT Discrete Refresh)

Flow accumulates continuously. No "tick reset" moments.

```python
class TokenBucket:
    rate: float      # Tokens per second
    capacity: float  # Max tokens
    balance: float   # Current tokens
    last_update: float

    def available(self) -> float:
        elapsed = now() - self.last_update
        self.balance = min(self.capacity, self.balance + elapsed * self.rate)
        self.last_update = now()
        return self.balance

    def spend(self, amount: float) -> bool:
        if self.available() >= amount:
            self.balance -= amount
            return True
        self.balance -= amount  # Go into debt
        return False
```

### Why Not Discrete Refresh

| Discrete (Current) | Rolling (Target) |
|--------------------|------------------|
| "Spend before reset" pressure | No artificial urgency |
| Wasteful end-of-tick spending | Smooth resource usage |
| Gaming reset boundaries | No boundaries to game |

### Examples

```
Rate = 10 tokens/sec, Capacity = 100

T=0:  balance = 100
T=5:  spend 60 → balance = 40
T=10: balance = min(100, 40 + 5*10) = 90
T=12: spend 100 → balance = -10 (debt!)
T=15: balance = -10 + 3*10 = 20 (recovering)
```

---

## Debt Model

### Compute Debt Allowed

Unlike current system, agents CAN go into debt for compute:

- Negative balance = cannot initiate new actions
- Accumulation continues in background
- Must wait until balance >= 0 to act again

### Natural Throttling

```
Agent spends 150 compute (has 100):
  → balance = -50
  → Cannot act
  → Accumulates at 10/sec
  → After 5 seconds: balance = 0
  → Can act again
```

Expensive operations → debt → forced wait → fewer concurrent actions.

### Scrip Debt = Contracts (NOT Negative Balance)

Scrip balance stays >= 0. Debt is handled differently:

```
Agent A borrows 50 scrip from Agent B:
  1. B transfers 50 scrip to A
  2. Debt artifact created: "A owes B 50 scrip"
  3. B owns the debt artifact (tradeable claim)
  4. A's scrip balance never goes negative
```

Like M1 vs M2 money - debt instruments are separate from base currency.

---

## Stock Resources

### Unchanged from Current

| Resource | Behavior |
|----------|----------|
| Disk | Quota decreases on write, reclaimable via delete |
| LLM Budget | System-wide $, stops all when exhausted |
| Memory | Docker container limit (new) |

### Docker as Real Constraint

Stock resources map to container limits:

```bash
docker run --memory=4g --cpus=2 agent-ecology
```

These ARE the constraints. Not abstract numbers.

---

## System-Wide Throttling

### Flow Rate IS The Throttle

```
Rate = 10 tokens/sec per agent
5 agents = 50 tokens/sec max system throughput
Configure rate so 50 tokens/sec = sustainable for container
```

### No Hardcoded Agent Limits

- Don't limit "max N agents per tick"
- Let flow rate naturally limit throughput
- Agents in debt skip actions (fewer concurrent)

---

## Transfers

### Unilateral (Sender's Right)

You can transfer YOUR assets without recipient consent:

```python
# Agent A can do this without Agent B's permission
transfer(from=A, to=B, amount=50, resource="compute")
```

Enables:
- Vulture capitalists rescuing frozen agents
- Gifts, subsidies, strategic resource sharing

### What Can Be Transferred

| Resource | Transferable? |
|----------|---------------|
| Scrip | Yes |
| Compute quota | Yes (TBD) |
| Disk quota | Yes (TBD) |
| Debt artifacts | Yes (tradeable) |

---

## Migration Notes

### Breaking Changes
- `advance_tick()` no longer resets flow resources
- `ledger.set_resource()` replaced with token bucket
- Negative compute balances allowed
- New debt artifact type for scrip borrowing

### Preserved
- Stock resource behavior (disk)
- Scrip transfer mechanics
- Genesis artifact cost model
- Thinking cost calculation (input/output tokens)

### New Components
- TokenBucket class
- Debt artifact type
- Docker integration for limits
