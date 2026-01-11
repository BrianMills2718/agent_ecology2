# Target Architecture

What we're building toward. Design decisions from clarification discussions.

**See current:** [../current/README.md](../current/README.md)

---

## Purpose

This is **mechanism design for real resource allocation**, not a simulation or model.

**Primary Goal:** Functional emergent collective intelligence - whole greater than sum of parts.

**Design Goals:**
- Operate within real-world constraints (computer capacity, API budget)
- Create markets that optimally allocate scarce resources among agents
- Resources ARE the real constraints, not proxies for them
- No artificial constraints on agent productivity

**Non-Goals:**
- Research reproducibility (doesn't matter)
- Simulating human societies or other systems
- Deterministic behavior

---

## Documents

| Document | Description |
|----------|-------------|
| [execution_model.md](execution_model.md) | Continuous autonomous loops |
| [agents.md](agents.md) | Self-managed agents, rights tradability |
| [resources.md](resources.md) | Token bucket, debt model |
| [oracle.md](oracle.md) | Bids anytime, periodic resolution |
| [infrastructure.md](infrastructure.md) | Docker isolation, real constraints |

---

## Key Changes from Current

| Aspect | Current | Target |
|--------|---------|--------|
| Execution | Tick-synchronized | Continuous autonomous loops |
| Flow resources | Discrete per-tick refresh | Rolling window (token bucket) |
| Debt | Not allowed | Allowed (compute), contract-based (scrip) |
| Agent control | System-triggered | Self-triggered with sleep |
| Ticks | Execution trigger | Metrics window only |
| Resource limits | Configured abstract numbers | Docker container limits |

---

## Architectural Principles

### Agents Are Autonomous
- Agents decide when to act
- Continuous loops, not tick-triggered
- Can self-sleep and wake on conditions

### Markets Allocate Resources
- No hardcoded limits on agents
- Flow rate limits total throughput
- Agents compete via markets for resources

### Constraints Are Real
- Docker limits = actual resource constraints
- LLM budget = actual $ spent
- No abstract "compute tokens" disconnected from reality

### Conflict Resolution in Artifacts
- Race conditions handled by genesis artifacts
- Ledger, escrow ensure atomic operations
- Orchestration layer doesn't resolve conflicts
