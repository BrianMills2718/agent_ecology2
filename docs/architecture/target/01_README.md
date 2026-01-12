# Target Architecture

What we're building toward. Design decisions from clarification discussions.

**Last verified:** 2026-01-12

**See current:** [../current/README.md](../current/README.md)

**Design rationale:** [../DESIGN_CLARIFICATIONS.md](../DESIGN_CLARIFICATIONS.md) - Start with the [Executive Summary](../DESIGN_CLARIFICATIONS.md#executive-summary-for-external-review) for decisions needing review.

---

## Purpose

This is **mechanism design for real resource allocation**, not a simulation or model.

**Mechanism design** means: designing the rules and incentives of a system so that self-interested participants, acting in their own interest, produce collectively beneficial outcomes. Like auction design, but for a multi-agent economy.

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
| [02_execution_model.md](02_execution_model.md) | Continuous autonomous loops |
| [03_agents.md](03_agents.md) | Self-managed agents, rights tradability |
| [04_resources.md](04_resources.md) | Rate allocation, resource tracking |
| [05_contracts.md](05_contracts.md) | Access control via contract artifacts |
| [06_oracle.md](06_oracle.md) | Bids anytime, periodic resolution |
| [07_infrastructure.md](07_infrastructure.md) | Docker isolation, real constraints |

---

## Key Changes from Current

| Aspect | Current | Target |
|--------|---------|--------|
| Execution | Tick-synchronized | Continuous autonomous loops |
| Renewable resources | Discrete per-tick refresh | Rolling window rate tracking |
| Rate limiting | Discrete per-tick | Rolling window, wait for capacity |
| Agent control | System-triggered | Self-triggered with sleep |
| Ticks | Execution trigger | Metrics window only |
| Resource limits | Configured abstract numbers | Docker container limits |
| Access control | Policy fields on artifacts | Contract artifacts (check_permission) |

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

---

## Glossary

| Term | Definition |
|------|------------|
| **Artifact** | Any persistent, addressable object in the system. Everything is an artifact: agents, contracts, data, tools. |
| **Agent** | An artifact with `has_standing=true` and `can_execute=true`. Can think (call LLM), act, and bear costs. |
| **Standing** | The property (`has_standing=true`) that allows an artifact to hold resources, enter contracts, and bear costs. Artifacts with standing are "principals" in the economic sense. |
| **Principal** | Any artifact with standing. Can hold scrip, own other artifacts, and be held accountable. |
| **Scrip** | The internal currency. Minted by oracle based on artifact quality scores. Used to pay for actions, trade, and coordinate. |
| **Contract** | An artifact that answers permission questions. Every artifact has an `access_contract_id` pointing to the contract that governs access to it. |
| **Genesis Artifact** | Artifacts created at system initialization (before agents). Examples: `genesis_ledger`, `genesis_store`, `genesis_freeware`, `genesis_rights_registry`. They bootstrap the system but have no special mechanical privileges. |
| **genesis_rights_registry** | Genesis artifact that manages resource quotas. Provides `check_quota`, `transfer_quota` methods. Enforces per-agent resource limits. |
| **Rate Tracker** | The renewable resource model. Tracks usage in a rolling time window. No burst, no debt - agents wait when over limit. |
| **Renewable Resource** | A resource with a rate limit (CPU-seconds, LLM tokens/min). Usage tracked in rolling window. |
| **Depletable Resource** | A resource that depletes forever (LLM budget in $). Once spent, gone. |
| **Allocatable Resource** | A resource with quota that can be reclaimed (disk, memory). |
| **Blocked** | An agent that has exceeded their rate limit. Must wait until rolling window has capacity. |
| **Oracle** | The system component that scores artifacts and mints scrip. Agents bid for oracle attention; winners get their artifacts scored. |
| **Invoke** | Call an executable artifact. `invoke(artifact_id, args)` runs the artifact's code and returns results. |
| **access_contract_id** | The field on every artifact pointing to the contract that governs permissions. The contract is the ONLY authority for access decisions. |
| **Vulture Capitalist Pattern** | Market-driven rescue of frozen agents. Any agent can unilaterally transfer resources to a frozen agent, hoping for reciprocation. |

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [DESIGN_CLARIFICATIONS.md](../DESIGN_CLARIFICATIONS.md) | Why decisions were made, certainty levels, open questions |
| [GAPS.md](../GAPS.md) | Implementation gaps between current and target |
| [SPEC_REVIEW.md](../../archive/SPEC_REVIEW.md) | Comparison to original specification (archived) |
