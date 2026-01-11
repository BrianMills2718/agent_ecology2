# Design Clarifications

**Decision log from architecture discussions. For authoritative docs, see:**

| Document | Purpose |
|----------|---------|
| [architecture/current/](architecture/current/) | How the system works TODAY |
| [architecture/target/](architecture/target/) | What we're building toward |
| [plans/](plans/) | Gap-closing implementation plans |

This file preserves the discussion history and rationale for decisions.

---

## Purpose

This is **mechanism design for real resource allocation**, not a simulation or model.

**Primary Goal:** Functional emergent collective intelligence - whole greater than sum of parts.

Design Goals:
- Operate within real-world constraints (computer capacity, API budget)
- Create markets that optimally allocate scarce resources among agents
- Resources ARE the real constraints, not proxies for them
- No artificial constraints on agent productivity

**Non-Goals:**
- Research reproducibility (doesn't matter)
- Simulating human societies or other systems
- Deterministic behavior

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

**LLM tokens ≠ Compute.** LLM tokens are API cost ($), compute is local machine capacity. Different constraints, different mechanisms.

---

## Flow Resources (Compute)

### Rolling Window (Token Bucket)
- Flow accumulates continuously at a fixed rate
- Capped at maximum capacity (can't hoard indefinitely)
- No discrete "refresh" moments - smooth accumulation
- Similar to API rate limits (tokens per minute)

### Why Not Discrete Refresh
- Discrete refresh creates "spend before reset" pressure
- Leads to wasteful spending at period boundaries
- Artificial urgency doesn't serve collective intelligence
- Rolling window = no gaming, smoother behavior

### Mechanics (Token Bucket)

```python
# Continuous accumulation
available = min(capacity, balance + elapsed_time * rate)

# Examples (rate = 10/sec, capacity = 100):
# T=0:  balance = 100
# T=5:  spend 60 → balance = 40
# T=10: balance = min(100, 40 + 5*10) = 90 (accumulated 50)
# T=12: spend 100 → balance = -10 (debt)
# T=15: balance = min(100, -10 + 3*10) = 20 (still recovering)
```

### Debt Persists
- Agents can go negative (debt)
- Accumulation continues even in debt
- Negative balance = cannot act (natural throttling)
- No debt forgiveness, must accumulate out

### Throttling Emerges Naturally
- No hardcoded "max N agents"
- Expensive operations → debt → wait for accumulation
- System self-regulates based on actual resource consumption

---

## Scrip and Debt

### Scrip Balance Cannot Go Negative
- Ledger enforces scrip >= 0
- You cannot spend scrip you don't have

### Debt = Contract Artifacts (Not Negative Balance)
- If Agent A owes Agent B 50 scrip, this is NOT a negative balance
- Instead: A debt artifact exists, owned by B
- The debt is a claim on A's future production
- Like M1 vs M2 money - debt instruments are different from base money
- Debt can be traded, sold, forgiven

### Example
```
Agent A borrows 50 scrip from Agent B:
  1. B transfers 50 scrip to A (A's balance increases)
  2. Debt artifact created: "A owes B 50 scrip"
  3. B owns the debt artifact (can sell it, trade it)
  4. A must eventually pay B to clear the debt
  5. A's scrip balance never goes negative
```

---

## LLM Token Limits

### No System-Level max_tokens
- System does NOT hardcode max_tokens for LLM calls
- Agents choose their own limits (or none)

### Agent Choice = Market Forces
- Agent wanting predictable costs → sets low max_tokens → self-limits
- Agent willing to risk debt → uncapped → more capability, more risk
- This is an economic decision, not a system rule

### Costs Remain Real
- Cost based on actual tokens used (input × rate_input + output × rate_output)
- max_tokens caps output but cost is still real usage

---

## Negative Balance Rules

### When Balance < 0
- Agent cannot initiate actions (can't afford to think)
- Agent skips turn (frees real CPU/memory)
- Flow replenishment continues each tick
- Ownership of assets persists

### Transfers Are Unilateral
- You can transfer YOUR assets without recipient consent
- Enables "vulture capitalist" pattern:
  1. Agent A is frozen (in debt, can't think)
  2. Agent B transfers compute to Agent A (no permission needed)
  3. Agent A unfreezes, can now think and act
  4. Agent B hopes Agent A reciprocates (trust/reputation)
- Market-driven rescue, not system rules

### Resolved Questions
1. **Can agents in debt receive transfers?** YES - transfers are unilateral from sender
2. **Can agents in debt still own artifacts?** YES - ownership persists, but can't act to sell
3. **Maximum debt limit?** TBD - probably not needed, flow accumulation handles it

---

## Agent Execution Model

### Continuous Autonomous Loops (NOT Tick-Synchronized)
- Agents act continuously, independently of each other
- No "tick triggers execution" - agents self-trigger
- Each agent: `while alive: think → act → repeat`

### Why Not Tick-Synchronized
- Artificial constraint on agent productivity
- Fast/efficient agents held back by tick rate
- Doesn't serve collective intelligence goal
- Coordination should emerge from markets, not forced sync

### What Ticks Become
- Background clock for metrics aggregation
- Accounting windows for reporting
- NOT execution triggers

### Agent Sleep (Self-Managed)
- Agents can put themselves to sleep
- Wake conditions: duration, event type, custom predicate
- This is agent-configurable, not system-hardcoded
- Agents own their configuration (can trade/modify rights)

### Time Injection
- System injects current timestamp into every LLM context
- Agents always know what time it is
- Enables time-based coordination without explicit broadcasts

### Race Conditions
- Handled by genesis artifacts (ledger, escrow, registry)
- Artifacts ensure atomic operations
- Two agents try to buy same item → escrow rejects second
- Conflict resolution in artifact layer, not orchestration

---

## Agent Rights and Ownership

### Agents Own Their Configuration
- Each agent has rights to their own configuration
- Can modify: LLM model, prompt, sleep behavior, etc.
- Cannot modify: ledger balances, system-wide limits, other agents' state

### Rights Are Tradeable
- Agents can SELL rights to their own configuration
- Agent A could own Agent B's config if B sold that right
- Enables "owned agents" / delegation patterns
- Market-driven, not system-hardcoded

### What Cannot Be Self-Modified
- Ledger balances (external, maintained by genesis_ledger)
- System-wide resource limits
- Other agents' state
- Genesis artifact behavior

---

## Oracle Design

### Bids Accepted Anytime
- No "bidding windows" - agents can bid whenever
- Simpler than time-bounded bidding phases
- Agents don't need to watch for window open/close

### Periodic Resolution
- Oracle resolves on a configurable schedule
- Example: every 60 seconds, or every hour
- Collects all bids since last resolution
- Selects winner(s), scores artifact, mints scrip

### Schedule Is Deterministic
- Agents know the resolution schedule from config
- Combined with time injection, agents can plan
- Example: "resolution at :00 of every hour"

---

## Budget Enforcement

### LLM Budget (Stock)
- `max_api_cost: 1.00` in config
- Tracks cumulative real $ spent on API calls
- Simulation stops when exhausted

### Status: Needs Verification
- [ ] Verify budget tracking is working correctly
- [ ] Verify simulation stops at limit

---

## System-Wide Throttling

### Flow Rate IS The Throttle
- Total system flow rate configured below machine's capacity
- Accumulation rate × agent count = max possible concurrent consumption
- No hardcoded "max N agents" needed

### Example
```
Config: rate = 10 tokens/sec per agent, 5 agents
Max consumption rate = 50 tokens/sec system-wide
Configure rate so 50 tokens/sec = sustainable for machine
```

### Calibration (Tuning, Not Design)
- Run tests to find machine's actual capacity
- Set accumulation rate accordingly
- Agents in debt wait → actual concurrent agents may be fewer

---

## Resolved Questions

1. **Execution gating**: Deduct AFTER execution. Debt handles overspending. Simpler than two code paths.

2. **Tick vs autonomous**: Agents are continuous autonomous loops. Ticks are just metrics windows.

3. **Flow refresh**: Rolling window (token bucket), not discrete refresh. No "use before reset" pressure.

4. **Reproducibility**: Doesn't matter. Not a goal.

5. **Oracle bidding**: Bids accepted anytime, oracle resolves periodically. No bidding windows.

6. **Scrip debt**: Handled as debt contract artifacts, not negative balances. M1 vs M2 distinction.

7. **Agent rights**: Agents can sell rights to their own configuration to other agents.

8. **Resource isolation**: Use Docker for hard resource limits. Container capacity = real constraints.

---

## Docker Resource Isolation

### Why Docker
- Hard resource limits enforced by container runtime
- Isolates agent ecology from rest of system
- Laptop stays responsive even if agents misbehave
- Easy to test different resource scenarios

### Resource Controls
```bash
docker run --memory=4g --cpus=2 agent-ecology
```

| Flag | Effect |
|------|--------|
| `--memory=4g` | Hard cap at 4GB RAM |
| `--cpus=2` | Limit to 2 CPU cores |
| `--storage-opt` | Disk limits (driver-dependent) |

### Architecture Option
```
Container 1: Agent ecology (--memory=4g --cpus=2)
Container 2: Qdrant (--memory=2g --cpus=1)
```
Each constrained independently. Agents can't starve Qdrant.

### Docker Limits = Real Constraints
- These ARE the hard resource limits
- Market mechanisms allocate within container limits
- Token bucket rates calibrated to container capacity
- Not host machine capacity

### Windows Considerations
- Docker Desktop uses WSL2/Hyper-V
- Slight overhead vs native Linux
- Works fine for this use case

---

## Development Environment Context

Reference specs for calibration:
- Surface Laptop 4
- Intel i7-1185G7 (4 cores, 8 threads)
- 32GB RAM
- Windows 11
- Note: Developer often runs many other programs (Claude Code instances, browsers, etc.)

Docker isolation recommended to prevent agent ecology from competing with other applications.

---

## Open Questions

1. **Minimum threshold**: Check for non-negative compute before acting? Or allow any agent to attempt?

2. **Calibration**: How do token bucket rates map to container capacity? Needs testing.

3. **Architecture change**: Current code is tick-synchronized. Refactor to continuous loops is significant.

---

## Next Steps

1. Finalize minimum threshold decision
2. Design continuous agent loop architecture
3. Set up Docker containerization
4. Update IMPLEMENTATION_PLAN.md with these decisions
5. Refactor runner.py from tick-synchronized to continuous
6. Implement token bucket for flow resources
7. Calibrate rates to container capacity
8. Test with 5 agents to verify throttling works
