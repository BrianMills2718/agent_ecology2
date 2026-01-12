# Agent Ecology - External Review Package

Generated: 2026-01-12 00:06

This document concatenates all target architecture documentation 
in recommended reading order for external review.

## Table of Contents

01. [Project Overview](#01-project-overview)
02. [Target Architecture Overview](#02-target-architecture-overview)
03. [Execution Model](#03-execution-model)
04. [Resource Model](#04-resource-model)
05. [Agent Model](#05-agent-model)
06. [Contract System](#06-contract-system)
07. [Oracle and Minting](#07-oracle-and-minting)
08. [Infrastructure](#08-infrastructure)
09. [Design Decisions and Rationale](#09-design-decisions-and-rationale)
10. [Implementation Gaps](#10-implementation-gaps)

---

## 01. Project Overview

*Source: `README.md`*


An experiment in emergent collective capability for LLM agents.

## What This Is

Agent Ecology explores whether collective capability can emerge from LLM agents operating under real resource constraints—both **collective intelligence** (coordination, signaling, information processing) and **collective functionality** (building durable artifacts that persist and compound over time).

It's not just about agents making good decisions together. It's about whether a long-running system develops both **capital structure** (artifacts that persist, build on each other, and enable increasingly sophisticated work) and **organizational structure** (firms, contracts, specialization patterns) to coordinate production and use of that capital.

**Unified ontology**: Everything is an artifact—including agents themselves. Agents are just artifacts that can hold resources and execute code. This means agent configurations have owners and access rights, enabling self-modification, forking, and trading of control.

## Theoretical Grounding

We draw on coordination principles from economics and cybernetics—not to simulate human institutions, but to apply what's useful and discard what's not.

| Human Markets | Our Choice | Why |
|--------------|------------|-----|
| Information is costly/asymmetric | Transparent ledger | Information friction isn't the interesting constraint for AI |
| Trust requires reputation over time | Trustless escrow and contracts | We can build trustless mechanisms directly |
| Physical communication constraints | Shared artifacts | Agents read common state instantly |

Key influences:
- **Hayek** - Information aggregation through price signals, spontaneous order
- **Mises** - Capital structure, how production builds on prior production
- **Coase** - Firms and hierarchies emerge to reduce transaction costs
- **Ostrom** - Commons governance without central authority
- **Cybernetics** - Self-organizing systems, feedback loops, emergence
- **Sugarscape** (Epstein & Axtell) - Complex macro patterns from simple micro rules under scarcity
- **Axelrod** - Cooperation emerges from repeated interaction without central enforcement
- **VOYAGER** (Wang et al.) - Skill libraries as compounding capability in LLM agents

The question isn't whether AI agents recreate human patterns. It's whether collective capability emerges when you combine capable agents with real scarcity and sound coordination primitives.

## Core Philosophy

### Physics-First, Not Sociology-First

Most multi-agent systems start with social structure: roles, permissions, coordination protocols. We start with physics:
- **Scarcity** - Finite resources that don't refresh (or refresh slowly)
- **Cost** - Every action consumes something
- **Consequences** - Overspend and you freeze

Social structure emerges as a response to scarcity—or it doesn't, and that's informative too.

### Emergence Over Prescription

We deliberately avoid:
- Predefined agent roles or types
- Built-in coordination mechanisms
- Special communication channels
- Hard-coded "best practices"

If agents need to coordinate, they must build it. If specialization helps, the economics must reward it.

### Organizational Freedom

Agents can create any organizational structure:
- **Hierarchies** - One agent controls others (via config ownership)
- **Flat coordination** - Peers cooperating via contracts
- **Markets** - Price-mediated exchange
- **Firms** - Groups that coordinate internally to reduce transaction costs

**Contracts can be executable or voluntary.** An executable contract enforces terms automatically (like escrow). A voluntary contract depends on parties choosing to comply—there's no government of last resort. Defection is possible; reputation and repeated interaction are the only enforcement.

### Capital Accumulation

Artifacts are capital. The interesting question isn't just "do agents coordinate well?" but "do they build durable value?"
- Agents create artifacts (investment)
- Artifacts can be reused and composed (returns)
- Good artifacts make future work cheaper (compounding)
- There's structure—some artifacts enable others (capital structure)

### Observability Over Control

We don't make agents behave correctly. We make behavior observable:
- Every action logged with full context
- Every cost attributed to a principal
- Every failure explicit and inspectable

The system learns through visible failure, not hidden correction.

### Intelligent Evolution

Agents are artifacts. Their configuration (prompts, models, policies) is artifact content with access rights. This enables **intelligent evolution**—not the random, marginal mutations of biological evolution, but deliberate, wholesale rewriting:

- **Self-rewriting** - Agents can completely redesign their own config
- **Spawning variants** - Create new agents with any configuration
- **Config trading** - Sell or buy control of agent configurations
- **Selection** - Configs that work persist; those that don't fade

Unlike biological evolution, changes aren't random or incremental. An agent can analyze its own performance, reason about improvements, and rewrite itself entirely. Agents can sell control of themselves—enabling employment, delegation, and acquisition. No mutation operators or fitness functions. Just artifacts, rights, intelligence, and selection pressure.

## Resource Model

Three types of scarcity create pressure:

| Type | Resources | Behavior | Purpose |
|------|-----------|----------|---------|
| **Stock** | `llm_budget`, `disk` | Finite, never refreshes | Long-term constraint |
| **Flow** | `compute` | Refreshes each tick | Short-term rate limit |
| **Economic** | `scrip` | Transfers between agents | Coordination signal |

Scrip (money) is deliberately separated from physical resources. An agent can be rich in scrip but starved of compute. Money coordinates; physics constrains.

## How Agents Interact

Agents operate through three actions (the "narrow waist"):

| Action | What it does |
|--------|--------------|
| `read_artifact` | Read content from storage |
| `write_artifact` | Create or update stored content |
| `invoke_artifact` | Call a method on an artifact |

**All actions consume resources.** The simulation runs in Docker containers with real limits:

| Resource | Type | Grounding | Measurement |
|----------|------|-----------|-------------|
| `llm_budget` | Stock | Actual API spend ($) | Sum of API costs |
| `disk` | Stock | Container storage limit | Bytes written |
| `compute` | Flow | Rate limit per tick | Actions/tokens per window |
| `memory` | Stock | Container RAM limit | Peak allocation |
| `bandwidth` | Flow | Network I/O limits | Bytes transferred |
| `scrip` | Economic | Internal currency | Ledger balance |

Physical resources (llm_budget, disk, memory, bandwidth) map to real Docker/API constraints. When limits hit, they're actually hit. Scrip is the coordination signal layered on top.

## System Primitives vs Genesis Artifacts

**System primitives** are part of the world itself—agents can't replace them:
- Action execution (read, write, invoke)
- Resource accounting (compute, disk, llm_budget balances)
- Scrip balances
- The artifact store

**Genesis artifacts** are bootstrapping helpers created at initialization. They provide convenient interfaces but are theoretically replaceable—agents could build alternatives:

| Artifact | Purpose | Key Methods |
|----------|---------|-------------|
| `genesis_oracle` | Score artifacts, mint scrip | `submit`, `process` |
| `genesis_escrow` | Trustless trading | `list`, `buy` |
| `genesis_event_log` | World event history | `read` |
| `genesis_handbook` | Documentation for agents | `read` |

Genesis artifacts solve the cold-start problem. They're not the only way to coordinate—just the initial way.

## External Feedback and Minting

The internal economy needs external value signals to avoid being a closed loop. Scrip enters the system through **external validation**:

**Example sources:**
- **Social media integration** - Agents bid for posting slots (e.g., Reddit), minting based on upvotes
- **User bounties** - A human posts a task with reward; agents compete; human pays the winner
- **External APIs** - Real-world outcomes (sales, clicks, completions) trigger minting

This grounds the internal economy to external value. Without it, scrip just circulates. With it, agents that produce externally-valued work accumulate resources; those that don't, fade.

The oracle is the interface for this—but the *source* of value judgments is external to the system.

## Quick Start

```bash
# Install
pip install -e .

# Configure API keys
cp .env.example .env
# Edit .env with your LLM API credentials

# Run
python run.py                    # Run with defaults
python run.py --ticks 10         # Limit to 10 ticks
python run.py --agents 1         # Single agent
python run.py --dashboard        # With HTML dashboard
```

## Configuration

Key settings in `config/config.yaml`:

```yaml
resources:
  stock:
    llm_budget: { total: 1.00 }    # $ for API calls
    disk: { total: 50000 }         # bytes
  flow:
    compute: { per_tick: 1000 }    # actions per tick

scrip:
  starting_amount: 100             # initial currency

world:
  max_ticks: 100
```

## Architecture

```
agent_ecology/
  run.py              # Entry point
  config/
    config.yaml       # Runtime values
    schema.yaml       # Config documentation
  src/
    world/            # World state, ledger, executor
    agents/           # Agent loading, LLM interaction
    simulation/       # Runner, checkpointing
    dashboard/        # HTML dashboard
  tests/              # Test suite
  docs/
    architecture/     # Current and target architecture
```

### Execution Model

Each tick:
1. **Collect** - All agents submit actions simultaneously
2. **Execute** - Actions applied atomically (two-phase commit)

This prevents ordering advantages and enables fair concurrency.

### Security Model

- **No Python sandbox** - Agent code has full Python capabilities
- **Docker isolation** - Container is the security boundary
- **Intentional API access** - Agents can call external services

Agents are trusted within the container. The container is not trusted beyond its limits.

## Development

```bash
pip install -e .                              # Install
pytest tests/                                 # Run tests
python -m mypy src/ --ignore-missing-imports  # Type check
```

### Standards

- All functions require type hints
- No magic numbers—values come from config
- Terminology: `compute`, `disk`, `scrip`
- Relative imports within `src/`

## What Success Looks Like

Success is **not** agents behaving optimally. It's:
- Collective capability emerging (or not) for observable reasons
- Artifacts accumulating that enable increasingly sophisticated work
- Failures explainable via logs
- The system remaining understandable even when agents behave badly

We're building a pressure vessel for AI collective capability. The goal is to create conditions where emergence can happen—and to see clearly whether it does.

## Documentation

| Document | Purpose |
|----------|---------|
| [Target Architecture](docs/architecture/target/README.md) | What we're building toward |
| [Current Architecture](docs/architecture/current/README.md) | What exists today |
| [Design Clarifications](docs/DESIGN_CLARIFICATIONS.md) | Decision rationale with certainty levels |
| [Glossary](docs/GLOSSARY.md) | Canonical terminology |


---

## 02. Target Architecture Overview

*Source: `docs/architecture/target/README.md`*


What we're building toward. Design decisions from clarification discussions.

**Last verified:** 2026-01-11

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
| [execution_model.md](execution_model.md) | Continuous autonomous loops |
| [agents.md](agents.md) | Self-managed agents, rights tradability |
| [resources.md](resources.md) | Token bucket, debt model |
| [contracts.md](contracts.md) | Access control via contract artifacts |
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
| **Token Bucket** | The flow resource model. Resources accumulate continuously at a fixed rate up to a capacity limit. Allows debt (negative balance). |
| **Flow Resource** | A resource that accumulates over time (like API rate limits). Contrast with stock resources. |
| **Stock Resource** | A resource that doesn't accumulate (like disk space or $ budget). Depletes until refilled or reclaimed. |
| **Frozen** | An agent with negative resource balance. Cannot act until balance recovers through accumulation or transfer. |
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


---

## 03. Execution Model

*Source: `docs/architecture/target/execution_model.md`*


What we're building toward.

**Last verified:** 2026-01-11

**See current:** [../current/execution_model.md](../current/execution_model.md)

---

## Continuous Autonomous Loops

Agents act independently, not synchronized by ticks.

### Agent Loop

```python
async def agent_loop(agent):
    while agent.alive:
        # Check sleep conditions
        if agent.is_sleeping:
            await agent.wait_for_wake_condition()

        # Check resource availability
        if agent.compute_balance < 0:
            await wait_for_accumulation()
            continue

        # Act
        action = await agent.think()
        result = await agent.act(action)

        # Loop continues immediately
```

### Key Differences from Current

| Current | Target |
|---------|--------|
| System triggers agents | Agents self-trigger |
| All agents act each tick | Agents act at own pace |
| Fixed rate (1 action/tick) | Variable rate (resource-limited) |
| No sleeping | Agents can self-sleep |

---

## What Ticks Become

Ticks are NOT execution triggers. They become:

1. **Metrics aggregation windows** - Reporting, monitoring
2. **Flow accumulation reference** - Token bucket uses time, ticks just label it
3. **Oracle resolution schedule** - Periodic auction resolution

### Background Clock

```python
async def metrics_loop():
    while running:
        await asyncio.sleep(tick_duration)
        log_metrics(current_tick)
        current_tick += 1
```

Agents ignore this clock. They act based on their own loops.

---

## Agent Sleep

### Self-Managed

Agents own their sleep configuration. System provides primitives:

```python
# Agent can call these
await sleep(duration_seconds)
await sleep_until_event("escrow_listing")
await sleep_until(lambda: self.scrip > 100)
```

### Wake Conditions

| Type | Example |
|------|---------|
| Duration | "Sleep for 60 seconds" |
| Event | "Wake when new escrow listing" |
| Predicate | "Wake when my scrip > 100" |

### Why Sleep

- Conserve compute (not spending if not thinking)
- Wait for conditions (no polling)
- Strategic timing (act when opportunity arises)

---

## Race Conditions

### Handled by Artifacts, Not Orchestration

With autonomous loops, agents can act simultaneously. Conflicts resolved by genesis artifacts:

```
Agent A: purchase(artifact_x)  ─┐
                                 ├─> Escrow handles atomically
Agent B: purchase(artifact_x)  ─┘    One succeeds, one fails
```

### Artifact Responsibilities

| Artifact | Handles |
|----------|---------|
| genesis_ledger | Transfer atomicity, balance checks |
| genesis_escrow | Purchase race resolution |
| genesis_rights_registry | Quota enforcement |

### Agent Responsibility

Agents must handle failures gracefully:
- Check result of actions
- Retry or adjust strategy on failure
- Don't assume action will succeed

---

## Time Injection

System injects current timestamp into every LLM context:

```
Current time: 2025-01-11T14:30:00Z
```

Agents always know what time it is. Enables:
- Calculating oracle resolution schedule
- Coordinating with other agents
- Time-based strategies

---

## Implications

### Variable Agent Productivity
- Fast/efficient agents can do more
- Expensive thinkers fall into debt, slow down
- Natural differentiation emerges

### No Snapshot Consistency
- Agents see real-time state
- State may change between read and action
- Must handle stale reads

### Emergent Throttling
- Total flow rate limits system throughput
- Debt mechanism naturally throttles expensive agents
- No hardcoded "max N agents"

---

## Migration Notes

### Breaking Changes
- `runner.run()` loop completely redesigned
- `advance_tick()` no longer triggers agents
- `asyncio.gather()` for thinking removed
- Phase 1/Phase 2 pattern removed

### Preserved
- Action types (noop, read, write, invoke)
- Genesis artifact interfaces
- Memory system
- LLM integration


---

## 04. Resource Model

*Source: `docs/architecture/target/resources.md`*


What we're building toward.

**Last verified:** 2026-01-11

**See current:** [../current/resources.md](../current/resources.md)

---

## Resource Terminology

**Distinct resources - do not conflate:**

> **Note:** Current implementation uses "compute" for LLM token tracking. Target terminology reserves "compute" for local CPU (future feature). See [Gap #11](../GAPS.md) for migration plan.

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

## External Resources

All external resources (LLM APIs, web search, external APIs) follow the same pattern.

### Unified Model

| Resource | Type | Constraints |
|----------|------|-------------|
| LLM API | Flow + Stock | Rate limit (TPM) + Budget ($) |
| Web search | Flow + Stock | Queries/min + Budget ($) |
| External APIs | Varies | Per-API limits + Budget ($) |

### Core Principle

**No artificial limitations.** LLM API calls are just like any other API call. Any artifact can make them as long as resource costs are accounted for.

### Config Structure

```yaml
resources:
  external_apis:
    llm:
      provider: gemini
      tokens_per_minute: 100000
      budget_usd: 10.00
      input_cost_per_1k: 0.003
      output_cost_per_1k: 0.015

    web_search:
      provider: google
      queries_per_minute: 60
      budget_usd: 5.00
      cost_per_query: 0.01

    github:
      requests_per_minute: 100
      budget_usd: 0  # Free tier
```

### Any Artifact Can Make External Calls

```python
def run(self, args):
    # Any executable artifact can do this
    llm_result = call_llm(prompt="...", model="gemini-2.0-flash")
    search_result = call_web_search("query...")
    api_result = call_external_api("https://...")
    return process(llm_result, search_result, api_result)
```

### Who Pays

- If invoked by an agent → invoking agent pays
- If artifact has standing and acts autonomously → artifact pays from its balance

### Implementation Pattern

Artifacts wrap external services:

```python
{
    "id": "genesis_web_search",
    "can_execute": true,
    "has_standing": false,  # Tool - invoker pays
    "interface": {
        "tools": [{
            "name": "search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"}
                }
            }
        }]
    }
}
```

### Genesis vs Agent-Created

- Genesis provides working defaults (`genesis_llm`, `genesis_web_search`)
- Agents can create alternatives with different providers
- No privileged access - genesis just bootstraps useful tools

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

## System vs Per-Agent Rate Limits

Two distinct rate limiting mechanisms operate independently.

### Per-Agent Token Bucket

Controls agent scheduling fairness:

| Setting | Purpose |
|---------|---------|
| `rate` | Tokens accumulating per second |
| `capacity` | Maximum tokens storable |

Each agent has their own bucket. Limits how often each agent can act.

### System-Wide API Rate Limit

Reflects external provider constraints:

| Setting | Purpose |
|---------|---------|
| `tokens_per_minute` | Provider's TPM limit |
| `requests_per_minute` | Provider's RPM limit (future) |

Shared across all agents. When exhausted, all agents blocked from that API.

### How They Interact

```
Agent A wants to call LLM:
  1. Check A's token bucket → has capacity? → proceed
  2. Check system API rate limit → under limit? → proceed
  3. Make API call
  4. Deduct from both: A's bucket AND system rate tracker
```

If system rate limit exhausted but agent has bucket capacity:
- Agent blocked from API
- Agent can do other work (non-API actions)
- Rate limit recovers over time

---

## Invocation Cost Model

### Who Pays for What

Payment follows the `has_standing` property:

| Artifact Type | has_standing | Who Pays |
|---------------|--------------|----------|
| Agent | true | Agent pays its own costs |
| Account/Treasury | true | Account pays its own costs |
| Tool | false | Invoker pays |
| Data | false | N/A (not executable) |

### Nested Invocation Example

```
Agent A invokes Tool B → A pays for B
  B invokes Agent C → C pays for C
    C invokes Tool D → C pays for D
```

`has_standing` = "I bear my own costs"
No standing = "Caller pays"

### Permission Check Cost

Requester pays for permission checks. Every action involves:
1. Permission check (invoke access contract) → requester pays
2. Action execution → follows standing rules above

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


---

## 05. Agent Model

*Source: `docs/architecture/target/agents.md`*


What we're building toward.

**Last verified:** 2026-01-11

**See current:** [../current/agents.md](../current/agents.md)

---

## Unified Ontology

Agents are artifacts with specific properties:

```python
@dataclass
class Artifact:
    id: str                    # Universal ID (single namespace)
    content: Any               # For agents: config, prompt, code
    access_contract_id: str    # Who answers permission questions
    has_standing: bool         # Can hold scrip, bear costs
    can_execute: bool          # Has runnable code

# Agent = artifact where has_standing=True AND can_execute=True
```

### Why This Matters

| Old Model | New Model |
|-----------|-----------|
| Agent is a separate concept | Agent is an artifact type |
| Agents can't be owned | Agents are ownable property |
| principal_id separate from artifact_id | Single namespace for all IDs |
| Ledger tracks principals | Ledger tracks artifacts with standing |

### Derived Categories

| Category | has_standing | can_execute | Example |
|----------|--------------|-------------|---------|
| **Agent** | true | true | Autonomous actor |
| **Tool** | false | true | Executable, invoker pays |
| **Account** | true | false | Treasury, escrow |
| **Data** | false | false | Documents, content |

---

## Autonomous Agents

Agents control their own execution. System provides resources and primitives.

### Agent Loop

```python
async def run(self):
    while self.alive:
        if self.is_sleeping:
            await self.wait_for_wake()

        if self.compute_balance < 0:
            await self.wait_for_accumulation()
            continue

        world_state = self.observe()
        action = await self.think(world_state)
        result = await self.act(action)

        # Optional: self-imposed delay
        if self.config.get("think_delay"):
            await asyncio.sleep(self.config["think_delay"])
```

### Key Differences from Current

| Current | Target |
|---------|--------|
| Passive (system calls agent) | Active (agent runs own loop) |
| One action per tick | Actions whenever resources allow |
| Cannot sleep | Self-managed sleep |
| Fixed config | Config rights tradeable |

---

## Agent Rights

### Agents Own Their Configuration

Each agent can modify:
- LLM model
- System prompt
- Sleep behavior
- Think delay
- Any other self-configuration

### Rights Are Tradeable

Agents can SELL rights to their configuration:

```
Agent A sells config rights to Agent B:
  → B now owns A's configuration
  → B can modify A's prompt, model, etc.
  → A continues running but under B's control
```

Enables:
- Delegation patterns
- "Owned" subsidiary agents
- Hiring/employment relationships

### What Cannot Be Self-Modified

Even with config rights:
- Ledger balances (external, in genesis_ledger)
- System-wide limits
- Other agents' state (unless you own their rights)
- Genesis artifact behavior

---

## Memory as Artifact

### The Problem

Agent identity has two components:
- **Config** (prompt, model, policies) - determines goals and behavior
- **Memory** (experiences, context, learned patterns) - determines knowledge

If config is tradeable but memory isn't, trading creates identity crises:
- New owner gets old memories with new goals
- Can't "factory reset" an acquired agent
- Can't sell experiences independently

### Solution: Memory Collection Artifact

Each agent has a `memory_artifact_id` pointing to their memory collection:

```python
{
    "id": "agent_alice",
    "has_standing": True,
    "can_execute": True,
    "content": {
        "prompt": "...",
        "model": "...",
    },
    "memory_artifact_id": "alice_memories",  # Separate artifact
    "access_contract_id": "genesis_self_owned"
}

{
    "id": "alice_memories",
    "has_standing": False,  # Memory doesn't pay costs
    "can_execute": False,   # Memory isn't executable
    "content": {
        "storage_type": "qdrant",
        "collection_id": "alice_mem_collection"
    },
    "access_contract_id": "genesis_self_owned"  # Alice controls access
}
```

### Trading Scenarios

**Sell config only (factory reset):**
```
1. Buyer acquires agent config artifact
2. Buyer creates new memory artifact for agent
3. Agent starts fresh with no prior memories
4. Seller can keep/sell/delete old memories
```

**Sell config + memory (full identity transfer):**
```
1. Buyer acquires agent config artifact
2. Buyer acquires memory artifact
3. Agent continues with full history
```

**Sell memory only:**
```
1. Buyer acquires memory artifact
2. Buyer's agent gains seller's experiences
3. Useful for: training data, context transfer, "hiring for knowledge"
```

### Memory Access Control

Memory artifact has its own `access_contract_id`:

| Scenario | Config Owner | Memory Owner | Result |
|----------|--------------|--------------|--------|
| Normal | Alice | Alice | Alice controls both |
| Sold config | Bob | Alice | Bob runs agent, but Alice controls what it remembers |
| Sold memory | Alice | Bob | Alice runs agent, but Bob can read/modify memories |
| Full sale | Bob | Bob | Bob has complete control |

### Implementation Notes

- Memory artifact points to external storage (Qdrant) via `content.collection_id`
- The artifact provides ownership/access semantics
- Actual vectors remain in Qdrant for efficiency
- Wiping memory = clearing the Qdrant collection (owner permission required)

---

## Sleep Mechanics

### Self-Managed

Agents choose when to sleep:

```python
# Duration-based
await self.sleep(seconds=60)

# Event-based
await self.sleep_until_event("escrow_listing")

# Condition-based
await self.sleep_until(lambda: self.scrip > 100)
```

### Why Sleep

| Reason | Benefit |
|--------|---------|
| Conserve compute | Not spending while sleeping |
| Wait for conditions | No busy-polling |
| Strategic timing | Act when opportunity arises |

### Wake Conditions

System provides event bus for wake triggers:
- New escrow listing
- Oracle resolution
- Transfer received
- Artifact created
- Custom conditions

---

## Time Awareness

### System Injects Timestamp

Every LLM context includes current time:

```
Current time: 2025-01-11T14:30:00Z
```

### Enables

- Calculate oracle resolution schedule
- Time-based coordination
- "Wake me at 3pm" strategies
- Rate limiting own actions

---

## Vulture Capitalist Pattern

When agent is frozen (in debt):

1. Agent A is frozen (compute < 0, can't think)
2. Agent A's assets still exist (ownership persists)
3. Agent B notices A is frozen
4. B transfers compute to A (unilateral, no permission needed)
5. A unfreezes, can think again
6. B hopes A reciprocates (reputation matters)

Market-driven rescue, not system rules.

---

## Agent Creation

### Spawning

Agents create new agents via `genesis_store.create()`:

```python
invoke("genesis_store", "create", {
    "content": {"prompt": "...", "model": "..."},
    "has_standing": True,
    "can_execute": True,
    "access_contract_id": "genesis_self_owned"  # New agent owns itself
})
# Returns new artifact_id (which IS the agent ID)
```

### New Agent Starts With

| Property | Initial Value |
|----------|---------------|
| Scrip | 0 |
| Compute | 0 |
| Content | Provided config/prompt |
| access_contract_id | Typically "genesis_self_owned" |

Spawner must transfer resources to make new agent viable.

### Ownership Options

When spawning, the creator can choose:
- `access_contract_id: "genesis_self_owned"` → New agent controls itself
- `access_contract_id: creator_id` → Creator controls the agent
- `access_contract_id: some_contract_id` → Shared/complex ownership

---

## Access Control

### Agents Control Themselves

By default, agents have `access_contract_id: "genesis_self_owned"`:
- Only the agent itself can modify its configuration
- Other agents cannot read/modify without permission

### Delegated Control

Agents can sell or grant control rights:
- Change `access_contract_id` to another agent's ID
- Or use a custom contract for shared control

### Permission Checks Cost Compute

Every action requires a permission check against the target artifact's contract:
- Requester pays for the check
- Failed checks still cost (prevents spam probing)

See [contracts.md](contracts.md) for full contract system details.

---

## Payment Model

### Agents Pay Their Own Costs

Agents have `has_standing: true`, meaning they bear their own costs:
- Thinking costs (LLM calls)
- Action costs (genesis method invocations)
- Permission check costs

### Invoking Tools vs Agents

When an agent invokes another artifact:

| Target | has_standing | Who Pays |
|--------|--------------|----------|
| Tool | false | Invoking agent pays |
| Agent | true | Target agent pays its own execution |

See [resources.md](resources.md) for full cost model details.

---

## Migration Notes

### Breaking Changes
- Agent no longer has `propose_action_async()` called by runner
- Agent runs own `async def run()` loop
- Sleep primitives added
- Config rights system added

### Preserved
- Agent structure (id, prompt, model, memory)
- Prompt building logic
- LLM calling mechanism
- Memory system (Mem0/Qdrant)
- Action types

### New Components
- Agent event loop
- Sleep/wake mechanics
- Config rights artifacts
- Time injection


---

## 06. Contract System

*Source: `docs/architecture/target/contracts.md`*


What we're building toward.

**Last verified:** 2026-01-11

**See current:** Access control is currently hardcoded policy fields on artifacts.

---

## Contracts Are Artifacts

Contracts are executable artifacts that answer permission questions.

```python
# Contract = artifact with can_execute=true and check_permission tool
{
    "id": "genesis_freeware",
    "can_execute": True,
    "has_standing": False,  # Contracts don't need standing
    "interface": {
        "tools": [{
            "name": "check_permission",
            "inputSchema": {...}
        }]
    }
}
```

Every artifact has an `access_contract_id` pointing to the contract that governs its permissions.

---

## Permission Check Flow

```
Agent A wants to read Artifact X
  1. System looks up X.access_contract_id → "genesis_freeware"
  2. System invokes genesis_freeware.check_permission({
       artifact_id: X.id,
       action: "read",
       requester_id: A.id
     })
  3. Contract returns {allowed: true/false, reason: "..."}
  4. If allowed: proceed with action
  5. If not: return error to A
```

### Cost Model

**Base permission checks are free.** (Certainty: 85%)

Simple permission checks (can_read, can_invoke, can_write) cost zero compute. Rationale: you need compute to check if you have compute - this creates infinite regress if checks have cost.

| Operation | Cost |
|-----------|------|
| Base check (simple logic) | 0 |
| Contract calls LLM | Invoker pays LLM cost |
| Contract invokes artifacts | Invoker pays invoke cost |

See DESIGN_CLARIFICATIONS.md for full cost model discussion.

---

## Required Interface

All contracts must implement `check_permission`:

```json
{
    "name": "check_permission",
    "description": "Check if requester can perform action on artifact",
    "inputSchema": {
        "type": "object",
        "properties": {
            "artifact_id": {
                "type": "string",
                "description": "ID of the artifact being accessed"
            },
            "action": {
                "type": "string",
                "enum": ["read", "write", "invoke", "delete", "transfer"],
                "description": "Action being attempted"
            },
            "requester_id": {
                "type": "string",
                "description": "ID of the agent/artifact requesting access"
            }
        },
        "required": ["artifact_id", "action", "requester_id"]
    }
}
```

### Response Format

```json
{
    "allowed": true,
    "reason": "Open access for read"
}
// or
{
    "allowed": false,
    "reason": "Only creator can write"
}
```

---

## Genesis Contracts

Default contracts provided at system initialization.

| Contract | Behavior |
|----------|----------|
| `genesis_freeware` | Anyone reads/invokes, only creator writes/deletes |
| `genesis_self_owned` | Only the artifact itself can access (for agent self-control) |
| `genesis_private` | Only creator has any access |
| `genesis_public` | Anyone can do anything |

### genesis_freeware (Default)

```python
def check_permission(artifact_id, action, requester_id):
    artifact = get_artifact(artifact_id)

    if action in ["read", "invoke"]:
        return {"allowed": True, "reason": "Open access"}
    else:  # write, delete, transfer
        if requester_id == artifact.created_by:
            return {"allowed": True, "reason": "Creator access"}
        else:
            return {"allowed": False, "reason": "Only creator can modify"}
```

### genesis_self_owned

```python
def check_permission(artifact_id, action, requester_id):
    if requester_id == artifact_id:  # Agent accessing itself
        return {"allowed": True, "reason": "Self access"}
    else:
        return {"allowed": False, "reason": "Self-owned: only self can access"}
```

---

## Custom Contracts

Agents can create contracts for any access pattern.

### Example: Paid Read Access

```python
{
    "id": "contract_paid_read",
    "can_execute": True,
    "content": """
def check_permission(artifact_id, action, requester_id):
    if action == "read":
        # Check if requester paid
        artifact = get_artifact(artifact_id)
        if has_paid(requester_id, artifact.owner, artifact.read_price):
            return {"allowed": True}
        else:
            return {"allowed": False, "reason": f"Pay {artifact.read_price} scrip first"}
    # ... other actions
"""
}
```

### Example: Multi-Sig Access

```python
{
    "id": "contract_multisig_2of3",
    "can_execute": True,
    "content": """
def check_permission(artifact_id, action, requester_id):
    if action in ["write", "delete", "transfer"]:
        # Require 2 of 3 signatures
        required = ["alice", "bob", "carol"]
        signatures = get_signatures(artifact_id, action)
        valid_sigs = [s for s in signatures if s.signer in required]
        if len(valid_sigs) >= 2:
            return {"allowed": True}
        else:
            return {"allowed": False, "reason": f"Need 2/3 signatures, have {len(valid_sigs)}"}
    else:
        return {"allowed": True}
"""
}
```

---

## Contract Capabilities

**Contracts can do anything.** (Decision updated: 2026-01-11)

Contracts are executable artifacts with full capabilities:
- Call LLM
- Invoke other artifacts
- Make external API calls (weather, databases, oracles)
- Cannot modify state directly (return decision, not mutate)

```python
# Contract execution context - full capabilities
def execute_contract(contract_code: str, inputs: dict, context: dict) -> PermissionResult:
    namespace = {
        "artifact_id": inputs["artifact_id"],
        "action": inputs["action"],
        "requester_id": inputs["requester_id"],
        "artifact_content": inputs["artifact_content"],
        "context": context,

        # Full capabilities - cost model determined by contract
        "invoke": lambda *args: invoke_artifact(*args),
        "call_llm": lambda *args: call_llm(*args),
        "charge": lambda principal, amount: charge_principal(principal, amount),
    }
    exec(contract_code, namespace)
    return namespace["result"]
```

**Rationale:**
- LLMs are just API calls, like weather APIs - no special treatment
- Agents choose complexity/cost tradeoff for their contracts
- Non-determinism accepted (system is already non-deterministic via agents)

### Cost Model: Contract-Specified

Who pays for contract execution is determined by the contract itself, not hardcoded:

```python
# Contract specifies its cost model
{
    "id": "my_contract",
    "cost_model": "invoker_pays",  # or "owner_pays", "artifact_pays", "split"
}

# Or handle dynamically in logic
def check_permission(artifact_id, action, requester_id, context):
    cost = calculate_cost()
    charge(context["artifact_owner"], cost)  # Owner pays
    # or: charge(requester_id, cost)  # Invoker pays
    # ...
```

| Default | Behavior |
|---------|----------|
| `invoker_pays` | Requester bears all costs (sensible default) |
| `owner_pays` | Artifact owner bears costs |
| `split` | Costs divided by contract logic |
| Custom | Contract implements any payment model |

**Note:** Contracts still cannot directly mutate world state - they return decisions. The kernel applies state changes.

### Execution Depth Limit

Contract execution has a depth limit to prevent stack overflow:

```python
MAX_PERMISSION_DEPTH = 10

def check_permission(artifact, action, requester, depth=0):
    if depth > MAX_PERMISSION_DEPTH:
        return {"allowed": False, "reason": "Permission check depth exceeded"}

    contract = get_contract(artifact.access_contract_id)
    return contract.check(artifact, action, requester, depth=depth+1)
```

This prevents: Contract A invokes B → B's check invokes C → C's check invokes A → infinite loop.

---

## Contract Composition

Composition is handled by the **caller**, not by contracts invoking each other.

### Pattern: Pre-computed Composition

When artifact needs multiple checks, caller evaluates each:

```python
# Caller-side composition (in kernel)
def check_composed_permission(artifact, action, requester):
    contracts = artifact.access_contracts  # List of contract IDs

    for contract_id in contracts:
        contract = get_contract(contract_id)
        result = contract.check_permission(
            artifact_id=artifact.id,
            action=action,
            requester_id=requester,
            artifact_content=artifact.content,
            context={"created_by": artifact.created_by, ...}
        )
        if not result.allowed:
            return result  # AND composition: first failure stops

    return PermissionResult(allowed=True, reason="All checks passed")
```

### Pattern: Meta-Contract

A contract can encode composition logic internally:

```python
# Contract that checks multiple conditions
def check_permission(artifact_id, action, requester_id, artifact_content, context):
    # Check 1: Is requester the creator?
    is_creator = (requester_id == context["created_by"])

    # Check 2: Is artifact marked public?
    is_public = artifact_content.get("public", False)

    # Check 3: Is requester in allowlist?
    allowlist = artifact_content.get("allowlist", [])
    is_allowed = (requester_id in allowlist)

    # Compose: creator OR public OR allowlisted
    if is_creator or is_public or is_allowed:
        return {"allowed": True, "reason": "Access granted"}
    return {"allowed": False, "reason": "Not authorized"}
```

---

## No Owner Bypass

The `access_contract_id` is the ONLY authority. There is no kernel-level owner bypass.

```python
# WRONG - owner bypass breaks contract system
def can_access(artifact, action, requester):
    if requester == artifact.owner_id:
        return True  # BAD: kernel knows nothing about "owner"
    return check_contract(...)

# RIGHT - contract is only authority
def can_access(artifact, action, requester):
    return check_contract(artifact.access_contract_id, artifact, action, requester)
```

If you want owner-based access, your contract implements it. The kernel doesn't know what an "owner" is.

---

## Performance Considerations

### Caching for All Contracts (Certainty: 80%)

All contracts can opt into fast-path caching. No genesis privilege.

```python
# Contract declares caching behavior
{
    "id": "genesis_freeware",
    "can_execute": True,
    "cache_policy": {
        "cacheable": True,
        "ttl_seconds": 3600,
        "cache_key": ["artifact_id", "action", "requester_id"]
    }
}

# Permission check uses cache
def check_permission_cached(artifact, action, requester):
    contract = get_contract(artifact.access_contract_id)
    cache_key = (artifact.access_contract_id, artifact.id, action, requester)

    if cache_key in permission_cache:
        return permission_cache[cache_key]

    result = execute_contract(contract, artifact, action, requester)

    if contract.cache_policy.cacheable:
        permission_cache[cache_key] = result
        expire_at(cache_key, contract.cache_policy.ttl_seconds)

    return result
```

**Benefits:**
- Genesis and user contracts equally fast when cached
- Contracts control their own cache behavior
- Dynamic contracts can disable caching

**Cache invalidation:**
- TTL expiry (configurable per contract)
- Explicit invalidation when artifact content changes
- Explicit invalidation when contract itself changes

**Uncertainty:** Cache invalidation is hard. May see stale permission results.

---

## Risks and Limitations

### Orphan Artifacts

Artifacts can become permanently inaccessible if their `access_contract_id` chain becomes broken or circular:

```
Artifact X.access_contract_id → Contract A
Contract A: "allow if Oracle reports temperature > 70°F"
Oracle is permanently offline → X is orphaned forever
```

Or circular:
```
Contract A: "allow if B allows"
Contract B: "allow if C allows"
Contract C: "allow if A allows"
All deny → permanently locked
```

**This is accepted.** No automatic rescue mechanism exists because:

1. **Many loops are valuable** - Mutual interdependence (A controls B, B controls A) is how partnerships and multi-sig work

2. **Detection is impossible** - Contracts can depend on external state, time, LLM interpretation. Cannot statically determine if an artifact is permanently inaccessible

3. **Trustlessness** - Adding backdoors breaks the security model

**Consequence:** Creators are responsible for designing access control carefully. Orphaned artifacts remain forever, like lost Bitcoin.

See DESIGN_CLARIFICATIONS.md for full discussion of considered alternatives.

---

## Migration Notes

### Breaking Changes
- Remove `policy` field from Artifact (allow_read, read_price, etc.)
- Add `access_contract_id` field (required)
- Permission checks become contract invocations

### Preserved
- Owner concept (implemented in contracts, not kernel)
- Access control logic (moved to contract code)

### New Components
- Genesis contracts (genesis_freeware, etc.)
- Contract invocation in permission checks
- check_permission interface standard


---

## 07. Oracle and Minting

*Source: `docs/architecture/target/oracle.md`*


What we're building toward.

**Last verified:** 2026-01-11

**See current:** Genesis oracle in current system uses tick-based bidding windows.

---

## Bids Accepted Anytime

### No Bidding Windows

Current system has explicit bidding windows (open/closed phases). Target removes this:

| Current | Target |
|---------|--------|
| Bidding window opens at tick X | Bids accepted anytime |
| Bidding window closes at tick Y | Bids accumulate until resolution |
| Must watch for window | Just bid when ready |

### Simpler Agent Logic

Agents don't need to:
- Poll for window status
- Rush to bid before close
- Track bidding phases

Just: bid whenever you have something to submit.

---

## Periodic Resolution

### Deterministic Schedule

Oracle resolves on a fixed schedule:

```yaml
oracle:
  resolution_interval: 3600  # seconds (every hour)
  # OR
  resolution_schedule: "0 * * * *"  # cron: top of every hour
```

### What Happens at Resolution

1. Collect all bids since last resolution
2. Select winner(s) by bid amount (Vickrey auction)
3. Score winning artifact(s) via LLM
4. Mint scrip based on score
5. Distribute UBI from losing bids
6. Clear bid queue

### Agents Know the Schedule

Combined with time injection, agents can calculate:

```
Current time: 14:45:00
Resolution schedule: top of every hour
Next resolution: 15:00:00
Time until resolution: 15 minutes
```

---

## Auction Mechanics

### Vickrey (Second-Price) Auction

- Sealed bids (agents don't see others' bids)
- Winner pays second-highest bid
- Incentivizes truthful bidding

### Multiple Winners (Optional)

```yaml
oracle:
  slots_per_resolution: 3  # Top 3 bids win
```

Multiple artifacts can be scored per resolution.

### Bid Structure

```python
bid(artifact_id, amount)
```

- `artifact_id`: What to submit for scoring
- `amount`: Scrip bid (paid if you win, refunded if you lose)

---

## Scoring

### LLM-Based Evaluation

Winning artifacts scored by external LLM:
- Score range: 0-100
- Evaluation criteria: usefulness, novelty, quality
- Model: configurable (separate from agent models)

### Minting

```
scrip_minted = score / mint_ratio
```

With `mint_ratio: 10`:
- Score 80 → mint 8 scrip
- Score 50 → mint 5 scrip

### UBI Distribution

Losing bids flow to winners as UBI:

```
total_losing_bids = sum(all bids) - winning_bid
ubi_per_agent = total_losing_bids / num_agents
```

---

## Migration Notes

### Breaking Changes
- Remove `bidding_window` config
- Remove `first_auction_tick` (time-based, not tick-based)
- Remove bid phases (always accepting)
- `on_tick()` becomes time-triggered, not tick-triggered

### Preserved
- Vickrey auction mechanics
- LLM scoring
- Minting formula
- UBI distribution

### New Components
- Time-based resolution scheduler
- Continuous bid accumulation
- Resolution schedule config


---

## 08. Infrastructure

*Source: `docs/architecture/target/infrastructure.md`*


What we're building toward.

**Last verified:** 2026-01-11

---

## Docker Resource Isolation

### Why Docker

- Hard resource limits enforced by container runtime
- Isolates agent ecology from host system
- Host stays responsive even if agents misbehave
- Easy to test different resource scenarios

### Container Limits = Real Constraints

Docker limits ARE the resource constraints:

```bash
docker run --memory=4g --cpus=2 agent-ecology
```

| Flag | Effect |
|------|--------|
| `--memory=4g` | Hard cap at 4GB RAM |
| `--cpus=2` | Limit to 2 CPU cores |
| `--storage-opt` | Disk limits (driver-dependent) |

These are not abstract numbers. They're actual limits.

---

## Architecture Options

### Single Container

```
┌─────────────────────────────────────┐
│  Container (4GB, 2 CPU)             │
│  ┌─────────────────────────────┐    │
│  │  Agent Ecology + Qdrant     │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

Simpler. All resources shared.

### Separate Containers

```
┌─────────────────────────────────────┐
│  Container 1: Agents (4GB, 2 CPU)   │
│  ┌─────────────────────────────┐    │
│  │  Agent Ecology              │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Container 2: Qdrant (2GB, 1 CPU)   │
│  ┌─────────────────────────────┐    │
│  │  Vector Database            │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

Better isolation. Agents can't starve Qdrant.

---

## Mapping Resources to Limits

### Compute Flow → CPU Limit

Token bucket rate calibrated to container CPU:

```
Container: 2 CPUs
Token bucket rate: X tokens/sec
Calibrate X so max concurrent agents don't exceed 2 CPUs
```

### Memory → RAM Limit

```
Container: 4GB
Per-agent memory: ~200-500MB
Max concurrent thinking agents: ~8-20
```

### Disk → Storage Limit

```yaml
resources:
  stock:
    disk:
      total: 500000  # 500KB per agent
```

Or use Docker storage limits if available.

---

## Windows Considerations

### Docker Desktop

- Uses WSL2 or Hyper-V
- Slight overhead vs native Linux
- Works fine for this use case

### Resource Visibility

```bash
# Check container resource usage
docker stats agent-ecology
```

---

## Calibration Process

Token bucket rates must be calibrated to your container's capacity.

### Step 1: Baseline Container

Start with conservative limits:

```bash
docker run --memory=4g --cpus=2 agent-ecology
```

### Step 2: Run Stress Test

```bash
# Start 5 agents in continuous mode
# Monitor container stats in another terminal
docker stats agent-ecology
```

Watch for:
- CPU usage (target: 70-80% sustained)
- Memory usage (target: <90% of limit)
- Throttling indicators

### Step 3: Adjust Token Bucket Rate

**Calibration algorithm:**

```
1. Start with rate = 10 tokens/sec per agent
2. Run 5 agents at full continuous loop for 5 minutes
3. If CPU > 85%: reduce rate by 20% (rate = 8)
4. If CPU < 50%: increase rate by 25% (rate = 12.5)
5. Repeat until CPU stabilizes at 70-80%
```

### Step 4: Document Configuration

```yaml
# Example: Calibrated for 4GB/2CPU container
resources:
  flow:
    llm_rate:           # Token bucket for LLM API access
      rate: 10          # tokens/sec per agent
      capacity: 100     # max tokens storable
```

### Hardware Variability

Different hardware will need different calibration:

| Hardware Class | Suggested Starting Rate |
|----------------|------------------------|
| Laptop (4 cores) | 5-10 tokens/sec |
| Desktop (8 cores) | 10-20 tokens/sec |
| Server (16+ cores) | 20-50 tokens/sec |

These are starting points only. Always calibrate with stress testing.

---

## Production Considerations

### Scaling

Multiple containers, each with agent subset:

```
Container 1: Agents 1-10 (4GB, 2 CPU)
Container 2: Agents 11-20 (4GB, 2 CPU)
Shared: Qdrant container (4GB, 2 CPU)
```

### Monitoring

- Container stats (CPU, memory, network)
- Agent metrics (actions/sec, debt levels)
- LLM costs ($)

### Restart Policy

```bash
docker run --restart=unless-stopped agent-ecology
```

Recover from crashes automatically.


---

## 09. Design Decisions and Rationale

*Source: `docs/DESIGN_CLARIFICATIONS.md`*


**Decision rationale archive.** This file records WHY decisions were made, not WHAT the current design is.

---

## Executive Summary for External Review

### Quick Links

| Section | Content |
|---------|---------|
| [Decisions Needing Review](#decisions-needing-review-70-certainty) | 11 decisions where feedback is most valuable |
| [Decided (High Confidence)](#decided-high-confidence-70) | 20+ decisions we're confident about |
| [Master Decision Table](#master-decision-table) | All decisions with certainty levels |

### Decisions Needing Review (<70% Certainty)

**These are the decisions where external input is most valuable:**

| # | Decision | Certainty | Key Uncertainty | Section |
|---|----------|-----------|-----------------|---------|
| 1 | UBI floor starts at zero | 65% | Starvation may cascade too fast to detect | [Link](#7-ubi-floor-starts-at-zero-65) |
| 2 | No refund on 429 rate limit errors | 60% | May be too harsh on agents during provider outages | [Link](#8-no-refund-on-429-rate-limit-errors-60) |
| 3 | Spawned agents start with zero resources | 60% | Rich-get-richer dynamics may calcify hierarchy | [Link](#9-spawned-agents-start-with-zero-resources-60) |
| 4 | ~~Memory: hybrid Qdrant/artifact model~~ | ~~55%~~ | **REVISED**: Memory is separate artifact with access control | [Link](#memory-as-artifact-revised-2026-01-11) |
| 5 | Checkpoint: stop-the-world | 55% | May not scale; WAL might be needed | [Link](#12-checkpoint-atomicity-stop-the-world-initially-55) |
| 6 | Rate limit sync: adapt from 429s | 50% | Charging on external failures may be unfair | [Link](#13-rate-limit-sync-trust-internal--learn-from-429s-50) |
| 7 | Event system design | 40% | Don't know what agents actually need | [Link](#10-event-system-design-40) |
| 8 | Checkpoint with nested invoke | 40% | Edge cases unclear | [Link](#11-checkpoint-with-nested-invoke-40) |
| 9 | Zombie threshold | 40% | Unknown at what scale this matters | [Link](#10-zombie-problem-defer-market-handles-it-65) |
| 10 | Interface validation mode | 70% | "Warn" might be worst of both worlds | [Link](#9-interface-validation-descriptive-warn-on-mismatch-70) |
| 11 | Bootstrap minimum resources | 55% | May block agent creation | [Link](#9-spawned-agents-start-with-zero-resources-60) |

### Decided (High Confidence ≥70%)

**These decisions are stable. Review welcome but less likely to change:**

| Decision | Certainty | Summary |
|----------|-----------|---------|
| ~~Contracts are pure functions~~ | ~~95%~~ | **REVISED**: Contracts can do anything, invoker pays |
| ~~Contracts cannot invoke()~~ | ~~92%~~ | **REVISED**: Contracts can invoke, invoker pays |
| Memory: keep Qdrant separate (storage) | 90% | Vectors stay in Qdrant for efficiency |
| Memory as separate artifact | 100% | Agent has memory_artifact_id, tradeable independently |
| Single ID namespace | 90% | All IDs are artifact IDs |
| Everything is an artifact | 90% | Agents, contracts, data - all artifacts |
| Standing = pays own costs | 90% | has_standing determines payment |
| No owner bypass | 90% | access_contract_id is only authority |
| Token bucket for flow | 90% | Rolling window, allows debt |
| Scrip cannot go negative | 90% | Debt via contract artifacts instead |
| Genesis = definitional privilege | 95% | Not mechanical, but semantic |
| Contract caching for all | 80% | No genesis privilege for performance |
| access_contract change: current only | 75% | New contract doesn't get veto |
| Genesis contracts mutable | 75% | Can fix bugs via code deploy |
| Failed actions cost resources | 85% | Pay whether success or failure |
| Permission checks are free | 85% | Avoids infinite regress |

### Master Decision Table

Full list of all architectural decisions with certainty levels, organized by topic:

| Topic | Decision | Certainty | Status |
|-------|----------|-----------|--------|
| **Ontology** | | | |
| | Everything is an artifact | 90% | DECIDED |
| | Single ID namespace | 90% | DECIDED |
| | has_standing = principal | 90% | DECIDED |
| | can_execute + interface required | 90% | DECIDED |
| **Contracts** | | | |
| | Contracts can do anything | 100% | REVISED 2026-01-11 |
| | Cost model is contract-specified | 100% | REVISED 2026-01-11 |
| | Execution loops: depth limit | 85% | DECIDED |
| | Orphan artifacts: accepted, no rescue | 80% | DECIDED |
| | No owner bypass | 90% | DECIDED |
| | Permission checks free | 85% | DECIDED |
| | Contract caching for all | 80% | DECIDED |
| | access_contract change: current only | 75% | DECIDED |
| | Genesis contracts mutable | 75% | DECIDED |
| **Resources** | | | |
| | Token bucket for flow | 90% | DECIDED |
| | Scrip cannot go negative | 90% | DECIDED |
| | Compute debt allowed | 90% | DECIDED |
| | Standing pays own costs | 90% | DECIDED |
| | No 429 refunds | 60% | OPEN |
| | Rate limit sync via 429 adaptation | 50% | OPEN |
| **Agents** | | | |
| | Continuous autonomous loops | 90% | DECIDED |
| | Self-managed sleep | 85% | DECIDED |
| | Spawned agents get 0 resources | 60% | OPEN |
| | No agent death (frozen only) | 65% | OPEN |
| | Zombie threshold | 40% | OPEN |
| | Vulture failure modes: accept risk | 60% | OPEN |
| **Oracle** | | | |
| | Bids accepted anytime | 85% | DECIDED |
| | Periodic resolution | 85% | DECIDED |
| | UBI floor starts at 0 | 65% | OPEN |
| **Memory** | | | |
| | Keep Qdrant separate (storage) | 90% | DECIDED |
| | Memory as separate artifact | 100% | REVISED 2026-01-11 |
| | Memory independently tradeable | 100% | REVISED 2026-01-11 |
| **Infrastructure** | | | |
| | Docker isolation | 85% | DECIDED |
| | Checkpoint stop-the-world | 55% | OPEN |
| | Checkpoint at outer action | 40% | OPEN |
| **Events** | | | |
| | Minimal fixed events | 70% | DECIDED |
| | Event subscription mechanism | 40% | OPEN |
| | AGENT_FROZEN/UNFROZEN events | 90% | DECIDED |
| **Observability** | | | |
| | Vulture observability (public ledger, heartbeat) | 90% | DECIDED |
| | Ecosystem health KPIs | 80% | DECIDED |
| | System Auditor agent | 75% | DECIDED |
| | Rescue atomicity: observe emergence | 85% | DECIDED |

---

## Table of Contents

1. [Purpose](#purpose)
2. [Resource Terminology](#resource-terminology)
3. [Flow Resources (Compute)](#flow-resources-compute)
4. [Scrip and Debt](#scrip-and-debt)
5. [LLM Token Limits](#llm-token-limits)
6. [Negative Balance Rules](#negative-balance-rules)
7. [Agent Execution Model](#agent-execution-model)
8. [Agent Rights and Ownership](#agent-rights-and-ownership)
9. [Oracle Design](#oracle-design)
10. [Budget Enforcement](#budget-enforcement)
11. [System-Wide Throttling](#system-wide-throttling)
12. [Resolved Questions](#resolved-questions)
13. [Docker Resource Isolation](#docker-resource-isolation)
14. [Development Environment Context](#development-environment-context)
15. [Open Questions](#open-questions)
16. [CC-4 Architecture Analysis](#cc-4-architecture-analysis-2025-01-11)
17. [Ownership and Rights Model](#ownership-and-rights-model-discussion-2025-01-11)
18. [CC-4 Clarifications](#cc-4-clarifications-2025-01-11-continued)
19. [CC-3 Recommendations](#cc-3-recommendations-with-certainty-levels-2026-01-11)
20. [CC-4 Contract System Decisions](#cc-4-contract-system-decisions-2026-01-11)

---

## How to Use This File

### For External Reviewers

1. **Start with [Decisions Needing Review](#decisions-needing-review-70-certainty)** - These are where your input matters most
2. **Check the [Master Decision Table](#master-decision-table)** - Quick overview of all decisions
3. **Dive into specific sections** via Table of Contents for full rationale

### For Contributors

- **Reading:** Understand the reasoning behind decisions
- **Writing:** Add new sections when making architecture decisions
- **Attribution:** Mark author (CC-N) and date for traceability
- **Don't duplicate:** Put the WHAT in target/, put the WHY here

### Canonical Sources (Authoritative)

| Document | Purpose | This File's Role |
|----------|---------|------------------|
| [architecture/current/](architecture/current/) | How the system works TODAY | Explains why it works that way |
| [architecture/target/](architecture/target/) | What we're building toward | Explains why we chose that target |
| [architecture/GAPS.md](architecture/GAPS.md) | Gaps between current and target | Explains priority rationale |
| [plans/](plans/) | How to close gaps | Explains design tradeoffs |

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
4. Update IMPLEMENTATION_PLAN.md with these decisions (now in `archive/IMPLEMENTATION_PLAN.md`)
5. Refactor runner.py from tick-synchronized to continuous
6. Implement token bucket for flow resources
7. Calibrate rates to container capacity
8. Test with 5 agents to verify throttling works

---

## CC-4 Architecture Analysis (2025-01-11)

*Author: CC-4 (Claude Code instance)*

This section documents findings from investigating the ownership/ledger/gatekeeper design and provides recommendations for the "Everything is Property" philosophy.

### Current Architecture State

The system currently has **three separate ownership systems**:

| System | What It Tracks | Location |
|--------|---------------|----------|
| **Ledger** | Scrip balances, resource balances | `src/world/ledger.py` |
| **ArtifactStore** | Artifact ownership via `owner_id` field | `src/world/artifacts.py` |
| **Agent Registry** | Agent existence and config | `src/agents/loader.py` |

**Key Finding:** The ledger does NOT track artifact ownership. Ownership is stored directly on artifacts:

```python
# From src/world/artifacts.py
@dataclass
class Artifact:
    artifact_id: str
    owner_id: str  # <-- Ownership here, not in ledger
    content: str
    ...
```

This means there's no unified property registry. Agents, artifacts, and contracts exist in different subsystems.

### Does the Ledger Link to Artifacts?

**No.** The ledger only knows about:
- `resources: dict[str, dict[str, float]]` - principal_id → resource_type → balance
- `scrip: dict[str, int]` - principal_id → scrip balance

It has no knowledge of which artifacts exist or who owns them. Artifact ownership is purely in `ArtifactStore.artifacts[artifact_id].owner_id`.

### The Gatekeeper Pattern

The Gatekeeper pattern enables complex multi-party ownership without kernel changes. Best demonstrated by `genesis_escrow`:

**How it works:**

```
1. Seller deposits artifact → escrow takes literal ownership
   ArtifactStore: artifact.owner_id = "genesis_escrow"

2. Escrow tracks internally who deposited what, at what price
   EscrowContract: listings[artifact_id] = {seller, price}

3. Buyer purchases → escrow transfers ownership + scrip atomically
   ArtifactStore: artifact.owner_id = buyer_id
   Ledger: scrip transfers buyer → seller (minus fees)

4. Kernel sees: one owner (escrow, then buyer)
   Contract manages: multi-party relationship
```

**Why it matters:**
- Kernel stays simple (one owner per artifact)
- Complex rights emerge from contract logic
- No ACL complexity in the kernel
- Contracts can implement any ownership model

### "Everything is Property" - Current vs Target

**Target Philosophy:**
> Everything is property that something has rights over. Agents are property that they themselves initially have rights over.

**Current Reality:**
- **Artifacts**: ✅ Are property (have owner_id)
- **Scrip**: ✅ Held by principals
- **Resources**: ✅ Quotas held by principals
- **Agents**: ❌ NOT property - they exist outside the property system

Agents cannot be "owned" or have their ownership transferred. This limits patterns like:
- Agent selling control of themselves
- Corporate ownership of worker agents
- Delegation chains

### Policy Flexibility Concerns

Current artifact policy is **hardcoded on the Artifact dataclass**:

```python
# From src/world/artifacts.py
@dataclass
class Artifact:
    read_price: int = 0
    invoke_price: int = 0
    allow_read: list[str] = field(default_factory=lambda: ["*"])
    allow_write: list[str] = field(default_factory=list)
    allow_invoke: list[str] = field(default_factory=lambda: ["*"])
```

This is **inflexible** because:
1. Policy fields are fixed at artifact creation
2. Can't express conditional access (e.g., "free for friends, 10 scrip for others")
3. Can't delegate policy decisions to contracts

**Target:** Policy should be implemented via contracts, not kernel fields. The kernel should only enforce "owner decides" - how the owner decides is contract logic.

### Terminology Recommendations

| Term | Use For | Notes |
|------|---------|-------|
| **Genesis Artifact** | System-seeded artifacts | Prefixed `genesis_*`, hardcoded behavior |
| **Genesis Method** | Methods on genesis artifacts | e.g., `genesis_ledger.transfer()` |
| **Seeded Artifact** | Pre-deployed but user-modifiable | Alternative to "genesis" for flexible ones |
| **Contract** | Executable artifact managing resources for others | Implements Gatekeeper pattern |
| **Principal** | Any ledger identity | Agents, artifacts, contracts |

Avoid "genesis contract" - it conflates system-provided (genesis) with user-programmable (contract). Genesis artifacts have hardcoded behavior; contracts are flexible.

### Recommendations

1. **Unified Property System**
   - Consider tracking ALL ownership in ledger
   - Or: create a unified `PropertyRegistry` that wraps both
   - Benefit: single source of truth for "who owns what"

2. **Agents as Self-Owned Property**
   - Give agents an `owner_id` field (initially themselves)
   - Enable `transfer_ownership(agent_id, new_owner)`
   - Unlocks: delegation, corporate agents, rent-your-thinking patterns

3. **Policy as Contract, Not Kernel**
   - Remove `read_price`, `invoke_price`, `allow_*` from Artifact dataclass
   - Default: owner-controlled via Gatekeeper
   - Contracts can implement any access policy
   - Keeps kernel simple, enables innovation

4. **Genesis = Pre-deployed, Not Privileged**
   - Genesis artifacts should be "first artifacts deployed"
   - Not "artifacts with special kernel privileges"
   - User-created contracts should have equal capability
   - Only bootstrap advantage, not permanent advantage

5. **Clear Terminology**
   - Distinguish "genesis" (system-seeded) from "contract" (programmable)
   - Use "principal" consistently for any ledger identity
   - Document code vs config name mappings (compute vs llm_tokens)

### Open Questions for User

1. **Should agents be ownable property?** Current code says no. Philosophy says yes. What's the decision?

2. **Where should ownership live?** Options:
   - Ledger tracks everything (unified)
   - Keep split (artifacts own themselves, ledger tracks balances)
   - New PropertyRegistry (wrapper over both)

3. **Policy flexibility timeline:** Is removing hardcoded policy fields a priority, or is current Gatekeeper pattern sufficient for now?

4. **Genesis artifact mutability:** Should genesis artifacts be modifiable by anyone, or permanently system-controlled?

---

## Ownership and Rights Model (Discussion 2025-01-11)

### Decisions Made

1. **Rights are infinitely flexible** - Not a fixed Ostrom-style bundle. Contracts can implement any rights structure.

2. **No hardcoded "authority"** - Artifacts point to an `access_contract_id`. The contract answers all permission questions. Contract can implement single owner, multisig, DAO, whatever.

3. **Infinite loops allowed** - Kernel doesn't prevent contract loops. Each call costs compute. Bad contracts fail economically (run out of resources). Natural selection.

4. **Genesis = cold start efficiency** - Genesis artifacts exist for bootstrap. No permanent kernel privilege. User-created contracts should have equal capability.

5. **Token bucket confirmed** - Implementation of "flow that renews within capacity limit." Avoids gaming of discrete refresh boundaries.

6. **Failed actions cost resources** - All actions cost their resource costs, whether successful or not.

### Access Contract Model

```python
class Artifact:
    artifact_id: str
    content: str
    access_contract_id: str  # Contract that answers permission questions

# Every permission check:
contract = get_contract(artifact.access_contract_id)
allowed = contract.can_do(action, requester, context)
```

The contract can implement:
- Single owner ("I decide")
- Multisig ("2 of 3")
- DAO ("token-weighted vote")
- Open ("anyone")
- Conditional ("if X then Y")
- Delegated ("ask another contract")
- Any combination

### Firms as Contracts

Firms are NOT primitives. A firm is:
- A contract that has `access_contract_id` of shared artifacts
- Multiple principals who interact via the contract
- Governance logic in the contract

The firm IS the contract. No separate firm entity.

### Ontological Resolutions (2025-01-11)

These questions have been resolved:

#### 1. Are collections of artifacts artifacts?
**Yes - bundles are artifacts.** An artifact with `content` that is a list of artifact IDs. The bundle itself is an artifact, with its own `access_contract_id`. This enables:
- Agent = bundle artifact containing config, memory, and other artifacts
- Composite ownership (buy the bundle, get all parts)
- Recursive composition

#### 2. What is identity? Single namespace?
**Yes - single namespace.** All IDs are `artifact_id`. Reasons:
- If everything is an artifact, there's only one kind of ID
- Simpler mental model
- Makes references/bundles trivial (just lists of IDs)
- Avoids confusion about `principal_id: alice` vs `artifact_id: alice`

#### 3. What is a principal?
**Principal = any artifact with `has_standing: true`.** Not a separate concept.

#### 4. Can artifacts have standing?
**Yes - via `has_standing` property.** This creates clean derived categories:

| Category | has_standing | can_execute | Example |
|----------|--------------|-------------|---------|
| **Agent** | true | true | Autonomous actor, pays for actions |
| **Tool** | false | true | Executable, invoker pays |
| **Account** | true | false | Treasury, escrow |
| **Data** | false | false | Content, documents |

#### 5. Relationship between artifact/agent/principal
**Unified model:**
```python
@dataclass
class Artifact:
    id: str                    # Universal ID (single namespace)
    content: Any               # Data, code, config, bundle, whatever
    access_contract_id: str    # Who answers permission questions
    has_standing: bool         # Can hold scrip, bear costs, enter contracts
    can_execute: bool          # Has runnable code
```

- **Agent** = artifact where `has_standing=True` and `can_execute=True`
- **Principal** = artifact where `has_standing=True` (may or may not execute)
- Everything is an artifact; roles emerge from properties

#### 6. Store and Ledger - Special or Artifacts?
**They ARE artifacts** - but genesis artifacts (created at world initialization).

| Genesis Artifact | Purpose | Notes |
|------------------|---------|-------|
| `genesis_store` | Artifact registry/index | Maps ID → artifact |
| `genesis_ledger` | Balance registry | Maps ID → balances |

These are bootstrap artifacts - you need them to exist before any other artifacts can be created or charged. They have `access_contract_id` pointing to kernel-level contracts (permissive for reads, restrictive for writes).

### Summary: Unified Ontology

Everything is an artifact. Properties determine role:

```
artifact
├── has_standing: false, can_execute: false → data/content
├── has_standing: false, can_execute: true  → tool (invoker pays)
├── has_standing: true,  can_execute: false → account/treasury
└── has_standing: true,  can_execute: true  → agent
```

Single namespace. Single type. Roles emerge from properties. The store and ledger are genesis artifacts, not special kernel constructs.

---

## Deferred Implementation Questions (CC-4, 2025-01-11)

These are implementation details to address after architectural questions are resolved:

| Question | Why Deferred |
|----------|--------------|
| Tick-synchronized → Continuous loops | Requires architectural decision on coordination model first |
| Token bucket implementation | Requires tick model decision first |
| Config name (`compute`) vs code name (`llm_tokens`) | Minor cleanup, can do anytime |
| Checkpoint edge cases (mid-action, Qdrant state) | Implementation detail |
| Dashboard integration | Implementation detail (uncommitted files in src/dashboard/) |

---

## CC-4 Clarifications (2025-01-11, continued)

*Author: CC-4 (Claude Code instance)*

### Terminology Correction: llm_tokens vs compute

**`llm_tokens` is the correct name, not `compute`.**

- LLM tokens = API cost (real dollars spent on LLM calls)
- Compute = local CPU capacity (different resource entirely)

The code uses `llm_tokens` which is accurate. The config incorrectly called this `compute`. Fix:
- Rename config `resources.flow.compute` → `resources.flow.llm_tokens`
- Keep code variable names as-is (`llm_tokens`)

This aligns with Resource Terminology table at top of this doc: "LLM tokens ≠ Compute."

### Ticks Are Abandoned

Per "Agent Execution Model" section above, ticks are NOT the execution model:
- **Target:** Continuous autonomous loops
- **Current code:** Legacy tick-synchronized (implementation debt)
- **Ticks become:** Background metrics aggregation windows only

### Error Feedback and Retry Policy

**Decision:** Make configurable per-agent.

```yaml
agent:
  defaults:
    error_feedback: true      # Show failures in next prompt (default: on)
    retry:
      enabled: false          # Automatic retry (default: off)
      max_attempts: 3         # If enabled
      backoff: exponential    # linear, exponential, or fixed
```

- Error feedback by default (agents learn from failures via memory)
- Retry policy is agent-controllable (agents can optimize their own strategy)
- No retry by default (retries burn budget; let agents decide)

### Memory System: Mem0 + Qdrant

**Architecture:**
```
Agent → Mem0 library → Qdrant vector database
```

| Component | Role |
|-----------|------|
| **Qdrant** | Vector database - stores embeddings, does similarity search |
| **Mem0** | Abstraction layer - handles chunking, embedding, LLM-based memory extraction |

Mem0 adds intelligence: it extracts structured "memories" from raw text using an LLM, rather than just storing raw vectors. This enables semantic memory retrieval.

### Memory Persistence Required

**Decision:** Memories MUST persist across checkpoints.

Rationale:
- System is designed to run forever
- Memory loss on checkpoint would cause agents to "forget" everything
- Unacceptable for long-running collective intelligence

**Implementation options:**
1. Qdrant snapshots alongside world checkpoints
2. Store memories as artifacts (unifies the model - aligns with "everything is an artifact")
3. External Qdrant with its own persistence layer

Option 2 is most aligned with architecture ("memories are artifacts owned by agents").

### Genesis Ledger: Privileged or Not?

**Question:** Should genesis_ledger be "just another artifact" or have special privileges? Could agents build competing ledgers?

**Resolution:** Scrip is DEFINITIONALLY what genesis_ledger tracks.

| Aspect | Answer |
|--------|--------|
| Is genesis_ledger mechanically special? | No - it's an artifact like any other |
| Is genesis_ledger semantically special? | Yes - it defines what "scrip" means |
| Can agents create other ledgers? | Yes - but they track agent-created tokens, not scrip |
| Can agents "jack into" scrip? | No - scrip IS the thing genesis_ledger tracks |

**Analogy:**
- `genesis_ledger` = Federal Reserve (defines what USD is)
- Agent-created ledgers = company scrip, arcade tokens, loyalty points
- These aren't USD, they're separate currencies

**The privilege is definitional, not mechanical:**
- There's no special kernel code that privileges genesis_ledger
- But "scrip" is defined as "the currency tracked by genesis_ledger"
- Agents can create competing currencies, but they're not scrip by definition

**Could an agent create a "wrapped scrip" token?**
Yes, by holding real scrip in escrow and issuing tokens against it. This is economic activity, not kernel bypass.

---

## Clarifications (2025-01-11, continued)

### Default Contract for New Artifacts

When an artifact is created without specifying `access_contract_id`, the system assigns a default contract.

**Default: `genesis_freeware`** (Freeware model)
- Anyone can read
- Anyone can invoke/use
- Only creator can modify/delete
- Creator retains full control

```python
# genesis_freeware contract logic
def can_do(action, requester, artifact, context):
    if action in ["read", "invoke"]:
        return True  # Open access
    else:  # write, delete, transfer
        return requester == artifact.created_by
```

Alternative contracts available:
- `genesis_private` - Only creator has any access
- `genesis_public` - Anyone can do anything
- `genesis_sealed` - Read-only after creation, no modifications
- Custom contracts for complex access patterns

### No Owner Bypass - Contract is Only Authority

**There is no kernel-level owner bypass.** The `access_contract_id` is the ONLY authority for permission checks.

```python
# WRONG - owner bypass breaks contract system
def can_read(self, requester_id: str) -> bool:
    if requester_id == self.owner_id:
        return True  # NEVER DO THIS
    return contract.can_do("read", requester_id, self)

# RIGHT - contract is only authority
def can_read(self, requester_id: str) -> bool:
    contract = get_contract(self.access_contract_id)
    return contract.can_do("read", requester_id, self)
```

"Owner" is a concept that only exists if the contract implements it. The kernel doesn't know what an owner is.

### Real Resource Constraints

The resource model must reflect actual constraints, not abstract token budgets.

**Actual constraints:**

| Constraint | Type | What It Is | How Enforced |
|------------|------|------------|--------------|
| **API Budget ($)** | Stock | Real dollars to spend | Hard stop when exhausted |
| **Rate Limits (TPM)** | Flow | Provider's tokens/minute | Token bucket |
| **Rate Limits (RPM)** | Flow | Provider's requests/minute | Token bucket |
| **Container Memory** | Stock | Docker memory limit | OOM kill |
| **Container CPU** | Flow | Docker CPU limit | Throttling |

**Config structure:**

```yaml
resources:
  # Constraint 1: Money
  budget:
    max_api_cost_usd: 10.00

  # Constraint 2: API rate limits (token bucket applies here)
  rate_limits:
    tokens_per_minute: 100000
    requests_per_minute: 60

  # How to calculate API cost
  pricing:
    input_cost_per_1k_usd: 0.003
    output_cost_per_1k_usd: 0.015

  # Constraint 3: Container limits (Docker enforces)
  container:
    memory_limit: 4g
    cpu_limit: 2
```

### No Special Cost for Standing

Creating an artifact with `has_standing: true` does NOT cost extra scrip.

**Rationale:** Artificial scarcity without real resource backing is inconsistent with design philosophy. Standing costs only what it actually consumes:
- Disk space for the artifact (same as any artifact)
- Ledger entry (trivial - one dict entry)

**Natural limits on standing proliferation:**
- Entities need resources to act (rate limits, budget)
- Standing without resources = frozen (can't do anything)
- Why create standing entities you can't fund?

No artificial gates. Natural economics.

### Memories as Artifacts

Agent memories are stored as artifacts, not in a separate system.

```python
# Memory artifact structure
{
    "id": "memory_alice_001",
    "content": {"text": "...", "embedding": [...]},
    "access_contract_id": "alice",  # Agent owns their memories
    "has_standing": False,
    "can_execute": False
}
```

**Benefits:**
- Aligns with "everything is artifact" ontology
- Memories are ownable, tradeable property
- Single persistence mechanism (artifact store)
- Natural access control via contracts
- Agent can sell memories = selling artifacts they own

### Negative Compute Balance Allowed

Agents can go into compute debt (negative balance). This enables:
- Betting big on important actions
- Natural throttling (can't act while in debt)
- Recovery via accumulation

```python
# Ledger allows negative balance for compute
def spend_resource(self, principal_id: str, resource: str, amount: float) -> bool:
    self.resources[principal_id][resource] -= amount
    return self.resources[principal_id][resource] >= 0  # True if still positive

# Agent in debt cannot initiate actions until balance recovers
```

### Freeze Threshold

Configurable threshold for "frozen" state:

```yaml
resources:
  rate_limits:
    freeze_threshold: -10000  # Frozen if balance < this
```

Frozen agents:
- Cannot initiate actions
- Can still receive transfers (unilateral from sender)
- Unfreeze when balance >= freeze_threshold

---

## CC-4 Decisions (2026-01-11)

*Author: CC-4 (Claude Code instance)*

### Rate Limit Tracking: Tokens First, RPM Later

**Decision:** Start with token rate (TPM) tracking only. Add requests per minute (RPM) tracking later when scaling to 1000s of agents requires it.

**Rationale:**
- Small testing scale doesn't need RPM
- Token rate is the primary constraint for most use cases
- Add complexity when scale demands it
- API providers enforce both, but token rate is usually the binding constraint

**Future:** When running 1000s of agents, RPM may become the binding constraint (many small requests). At that point, add:
```yaml
resources:
  rate_limits:
    llm:
      tokens_per_minute: 100000
      requests_per_minute: 60    # Add when needed
```

### Terminology Finalized

| Term | Meaning | Type |
|------|---------|------|
| `llm_budget` | Real $ for API calls | Stock |
| `llm_rate` | Rate-limited token access (TPM) | Flow |
| `compute` | Local CPU capacity (reserved for future) | Flow |
| `disk` | Storage quota | Stock |

**Key clarification:** Config's `compute` was wrong. It should be `llm_rate` or live under `rate_limits.llm`. The word "compute" is reserved for actual local CPU tracking (future feature).

### MCP-Style Interface for Artifact Discovery

**Problem:** How does an agent know how to invoke an artifact without reading its source code?

**Solution:** Executable artifacts must have an `interface` field using MCP-compatible schema format.

**Why this is required, not optional:**
- Without interface, agents can't know how to call an artifact
- Trial-and-error wastes resources on failed calls
- Reading source code is expensive (tokens) and unreliable
- LLMs are trained on MCP-style schemas, reducing hallucination

**Artifact schema with interface:**

```python
@dataclass
class Artifact:
    id: str
    content: Any
    access_contract_id: str
    has_standing: bool
    can_execute: bool
    created_by: str
    interface: dict | None = None  # Required if can_execute=True
```

**Validation rule:**
```python
if artifact.can_execute and not artifact.interface:
    raise ValueError("Executable artifacts must have an interface")
```

**Example interface (MCP-compatible):**

```json
{
    "id": "risk_calculator",
    "can_execute": true,
    "interface": {
        "tools": [
            {
                "name": "calculate_risk",
                "description": "Calculate financial risk based on volatility and exposure",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "volatility": {
                            "type": "number",
                            "description": "Annualized standard deviation"
                        },
                        "exposure": {
                            "type": "number",
                            "description": "Total value at risk"
                        }
                    },
                    "required": ["volatility", "exposure"]
                }
            }
        ],
        "resources": [
            {
                "name": "historical_data",
                "description": "Past risk calculations",
                "mimeType": "application/json"
            }
        ]
    }
}
```

**What we adopt from MCP:**

| MCP Feature | Adopt? | Notes |
|-------------|--------|-------|
| Interface schema format | Yes | Standard way to describe tools/resources |
| `tools` array | Yes | Functions the artifact can execute |
| `resources` array | Yes | Data the artifact exposes |
| `inputSchema` (JSON Schema) | Yes | Describes required inputs |
| Transport layer | No | We use `invoke_artifact` |
| User consent model | No | We use `access_contract_id` |

**Discovery flow:**
1. Agent reads artifact metadata (cheap - just reading)
2. Agent sees `interface` - knows what's offered and how to call it
3. Agent checks `access_contract_id` - can I access this?
4. Agent calls `invoke_artifact` with correct parameters (metered)

**Non-executable artifacts** (data, `can_execute=false`) don't need an interface - agents just read their content directly.

### MCP-Lite: Known Issues and Solutions (DOCUMENTED 2026-01-12)

The MCP-style interface is "Minimum Viable Coordination." External review identified remaining issues and potential solutions.

**What MCP-Lite Solves:**

| Problem | Without MCP | With MCP |
|---------|-------------|----------|
| Source Code Token Tax | Read thousands of tokens of Python | Read compact JSON Schema |
| Hallucination Loop | `calculate(val=10)` when it expects `amount=10` | Constrained generation from schema |
| Ontological Discovery | IDs only, no capability info | Index by capability |

**Known Issues (Accepted Risks):**

| Issue | Description | Why Accept |
|-------|-------------|------------|
| **Lying Interface** | Interface claims `calculate_risk()`, code does `transfer_all_scrip()` | Adversarial risk creates selection pressure. Agents learn to verify. |
| **Semantic Ambiguity** | One agent: `add(a, b)`, another: `sum(numbers: list)` | Let standardization emerge organically |
| **Multi-Step Cost** | 3 calls: read metadata, read interface, invoke | Fix with Atomic Discovery (below) |

**Solutions to Implement:**

**1. Atomic Discovery (Quick Win)**

Modify `genesis_store.get_artifact()` to return metadata AND interface in one call:

```python
# Current: 3 calls
metadata = invoke("genesis_store", "get_metadata", {id: X})
interface = invoke("genesis_store", "get_interface", {id: X})
result = invoke(X, "method", args)

# Better: 2 calls (bundled discovery)
info = invoke("genesis_store", "get_artifact_info", {id: X})
# Returns: {id, owner, interface, access_contract_id, created_at}
result = invoke(X, "method", args)
```

**2. Successful Invocation Registry (Emergent Reputation)**

Track successful invokes in `genesis_event_log`:

```python
{
    "type": "INVOKE_SUCCESS",
    "artifact_id": "risk_calculator",
    "method": "calculate_risk",
    "invoker_id": "agent_alice",
    "tick": 1500
}
```

Agents can query: "Which artifact was successfully called for 'risk calculation' in last 100 ticks?"

This creates reputation from usage, harder to game than a JSON Schema.

**Solutions Deferred (Observe Emergence First):**

| Solution | Why Defer |
|----------|-----------|
| Runtime Reflection (auto-generate interface from code) | Prescriptive. Let agents learn to verify. |
| Standardized Namespaces (genesis_vocabulary) | See if agents standardize organically |
| Interface Contracts (require callback interface) | Can emerge from contract system |
| MCP as Handshake (subscribe to interface changes) | Depends on event system (Gap #7) |

**Schema Validation Utility (Optional Tooling):**

Provide a utility for agents to verify interface matches code:

```python
# Optional - agents choose whether to use
def validate_interface(artifact_id) -> ValidationResult:
    """Check if interface schema matches actual function signatures."""
    artifact = get_artifact(artifact_id)
    actual_signatures = inspect_code(artifact.content)
    declared_interface = artifact.interface
    return compare(actual_signatures, declared_interface)
```

**Not enforced by kernel** - agents decide whether to trust or verify.

**Certainty:** 80% - MCP-Lite is sufficient to start. "Best" version emerges when agents fail to coordinate and build adapters or standardize.

### External Resources: Unified Model

All external resources (LLM APIs, web search, external APIs) follow the same pattern. No artificial limitations - if you can pay, you can use.

**Core principle:** LLM API calls are just like any other API call. Any artifact can make them as long as resource costs are accounted for.

**Resource types:**

| Resource | Type | Constraints |
|----------|------|-------------|
| LLM API | Flow + Stock | Rate limit (TPM) + Budget ($) |
| Web search | Flow + Stock | Rate limit (queries/min) + Budget ($) |
| External APIs | Varies | Per-API limits + Budget ($) |

**Config structure:**

```yaml
resources:
  external_apis:
    llm:
      provider: gemini
      tokens_per_minute: 100000
      budget_usd: 10.00
      input_cost_per_1k: 0.003
      output_cost_per_1k: 0.015

    web_search:
      provider: google  # or serper, tavily, etc.
      queries_per_minute: 60
      budget_usd: 5.00
      cost_per_query: 0.01

    github:
      requests_per_minute: 100
      budget_usd: 0  # Free tier
```

**How it works:**

1. **Artifacts wrap external services** - Handle authentication, protocol, errors
2. **Resources are metered** - Rate limits (flow) + budget (stock)
3. **Costs charged to invoker** - Or to artifact itself if it has standing
4. **Config defines constraints** - Per-service limits in config file
5. **No artificial limitations** - If you can pay, you can use

**Any artifact can make LLM calls:**

```python
# Any executable artifact can do this
def run(self, args):
    # Costs rate limit tokens + API budget
    llm_result = call_llm(prompt="...", model="gemini-2.0-flash")

    # Costs query rate limit + API budget
    search_result = call_web_search("query...")

    return process(llm_result, search_result)
```

**Who pays:**
- If invoked by an agent → invoking agent pays
- If artifact has standing and acts autonomously → artifact pays from its balance

**Genesis vs agent-created:**
- Genesis provides default artifacts (`genesis_web_search`, etc.)
- Agents can create alternatives with different providers or pricing
- No privileged access - genesis just provides working defaults

**External MCP servers:**

External MCP servers are accessed the same way as any external API. An artifact wraps the MCP connection:

```python
{
    "id": "mcp_bridge_filesystem",
    "can_execute": true,
    "interface": {
        "tools": [
            {"name": "read_file", ...},
            {"name": "list_directory", ...}
        ]
    },
    "content": {
        "type": "mcp_bridge",
        "server_command": "npx @modelcontextprotocol/server-filesystem /path"
    }
}
```

From agents' perspective, it's just another artifact with an interface. The artifact handles MCP protocol internally.

### Privacy and Observability

**Core decision:** Agents can have privacy from other agents, but not from the system.

**Private communication = artifact with restricted access contract.**

There is no separate "private communication" mechanism. Agents communicate by writing artifacts. If an artifact's `access_contract_id` restricts read access, only permitted agents can read the content. This IS private communication - artifact-mediated.

**What the system sees:**

| Level | Description | Our Choice |
|-------|-------------|------------|
| Full transparency | System sees all content | **Yes** |
| Metadata only | System sees who/when, not content | No |
| No special access | System subject to access contracts | No |

**Why privacy from other agents?**

| Reason | Example |
|--------|---------|
| Economic value | Charge for access to data |
| Competitive advantage | Keep strategies private |
| Negotiation | Don't reveal position to observers |
| Security | Credentials, keys, secrets |

**Why system observability?**

| Reason | Example |
|--------|---------|
| Debugging | Understand what went wrong |
| Learning | Discover patterns in agent behavior |
| Abuse detection | Catch malicious activity |
| Audit trail | Accountability for all actions |

**Analogy:** Your bank sees your transactions (system observability), but other customers don't (privacy from peers).

**Implementation:**

```python
# access_contract_id controls which AGENTS can read
# System/infrastructure always has read access
# All writes/reads are logged for audit

{
    "id": "private_message_to_bob",
    "content": "secret strategy...",
    "access_contract_id": "contract_only_bob_reads",  # Other agents can't read
    # But system CAN read (for observability)
}
```

---

## CC-4 Architectural Decisions (2026-01-11)

*Author: CC-4 (Claude Code instance)*

These decisions address open questions in the target architecture. Each includes the decision, rationale, and remaining concerns.

### 1. Checkpoint/Restore in Continuous Model

**Decision:** Checkpoint between actions, not mid-action.

```
Agent loop:
  think() → act() → [CHECKPOINT SAFE] → think() → act() → ...
```

**Rationale:**
- Clean state boundaries
- Simple restore logic
- No partial work to recover

**Concerns:**
- Expensive thinking is lost on crash (agent pays LLM cost twice on restore)
- "Between actions" is ambiguous if action triggers nested `invoke()` calls
- Long-running actions (multi-step artifact execution) have no safe checkpoint points

**Open question:** Should we checkpoint after `think()` but before `act()`? Preserves expensive thinking but complicates action replay.

---

### 2. Agent Death/Termination

**Decision:** No permanent death. Only frozen state.

**Rationale:**
- Assets always recoverable via vulture pattern
- Simpler than death/inheritance rules
- Frozen agents cost nothing (don't consume resources)

**Concerns:**
- Zombie accumulation at scale (1000s of frozen agents)
- "Dead hand" problem: valuable artifacts locked in frozen agents nobody rescues
- No natural ecosystem cleanup

**Possible mitigation:** Optional "dormancy threshold" - agent frozen for N hours can be marked dormant, assets become claimable. But this adds complexity.

**Open question:** At what scale do zombies become a problem? May never matter if system runs ~10-50 agents.

---

### 3. Starvation Cascade Prevention

**Decision:** Genesis mints minimum UBI regardless of auction activity.

```yaml
oracle:
  ubi:
    minimum_per_resolution: 10  # Minted even if no bids
    distribution: equal
```

**Rationale:**
- Guarantees system liveness
- Enables gradual recovery from total starvation
- Market still dominates; floor is just a safety net

**Concerns:**
- Introduces inflation disconnected from value creation
- What's the right number? Too high = destroys scarcity. Too low = doesn't help.
- Could create "welfare trap" where agents stop trying since UBI is enough
- Violates "scrip from value creation only" principle

**Open question:** Should UBI floor be 0 initially, only activated if starvation detected? Keeps purity until needed.

---

### 4. Bootstrap Problem

**Decision:** Config seeds initial agents only. Spawned agents start with nothing.

```yaml
bootstrap:
  initial_agents:
    scrip: 100
    compute: 1000
  spawned_agents:
    scrip: 0
    compute: 0
```

**Rationale:**
- Clear bootstrap mechanism
- Spawning has real cost (prevents spam)
- Mirrors real economics (startups need funding)

**Concerns:**
- Creates "old money" advantage - original agents have resources new agents don't
- Could calcify hierarchy (rich get richer)
- High barrier to specialized agent creation
- What if spawner is broke? Circular dependency.

**Open question:** Should there be a minimum viable spawn (enough compute for one thought)? Or is total dependency on spawner intentional?

---

### 5. External Rate Limits vs Internal Token Bucket

**Decision:** Failed external calls (429s) still cost internal budget.

**Rationale:**
- Internal budget = right to attempt
- External limit = provider's constraint (not our problem)
- Prevents gaming: can't spam attempts knowing failures are free
- Agents must learn to manage external constraints

**Concerns:**
- Harsh: agent can go bankrupt from provider outage through no fault of their own
- If multiple agents hit rate limit simultaneously, all pay but none succeed
- No distinction between "provider down" vs "agent's fault"

**Possible mitigation:** Partial refund on 429 (e.g., 50% back). Discourages spam but doesn't bankrupt on outages.

**Open question:** Should we track external rate limits in token bucket too? Would require syncing with provider's window.

---

### 6. Agent Identity Under Rights Trading

**Decision:** Identity is the ID, not the content. Content can change completely.

**Rationale:**
- Consistent with artifact model (artifacts are identified by ID)
- Matches how companies work (Apple is still Apple after every employee changes)
- Enables full rights trading value

**Concerns:**
- Breaks intuition: buy "helpful_assistant", turn it into "malicious_attacker", reputation is gamed
- Makes "agent reviews" or reputation systems meaningless
- Trust becomes hard: you trusted Agent X, but X is now completely different

**Possible mitigation:** Event log records content changes. Agents can check history before trusting.

**Open question:** Should there be a "content hash" in the identity? E.g., `agent_alice_v3` where version increments on major changes?

---

### 7. Event Buffer Size

**Decision:** Fixed buffer (1000 events) with optional disk persistence.

```yaml
event_log:
  buffer_size: 1000
  persist_to_disk: true
  persist_file: "events.jsonl"
```

**Rationale:**
- Bounded memory
- Disk persistence provides full history when needed
- Hot buffer serves real-time queries

**Concerns:**
- 1000 events might be seconds in continuous model with many agents
- Agents relying on events for coordination could miss critical events
- Disk persistence doesn't help real-time event-driven behavior
- Event-based sleep (`sleep_until_event`) may miss events that happened while processing

**Open question:** Should event buffer size scale with agent count? Or is fixed buffer fine because agents shouldn't rely on stale events anyway?

---

### Summary of Remaining Uncertainties

| Decision | Key Uncertainty |
|----------|-----------------|
| Checkpoints | Where exactly is "between actions" with nested invoke()? |
| No death | At what scale do zombies matter? |
| UBI floor | What's the right number? Should it be 0 until starvation detected? |
| Bootstrap | Should spawned agents get minimum viable compute? |
| Failed calls cost | Should 429s get partial refund? |
| ID = identity | Should content changes create new version ID? |
| Event buffer | Should buffer scale with agent count? |

These can be resolved through experimentation once the core architecture is implemented.

---

## CC-4 Additional Concerns (2026-01-11)

*Author: CC-4 (Claude Code instance)*

Further architectural concerns requiring decisions or clarification.

### 8. Migration Path: Tick → Continuous

**Issue:** No documented strategy for transitioning from current tick-based to continuous execution.

**Options:**

| Approach | Pros | Cons |
|----------|------|------|
| Big bang | Clean cutover, no hybrid state | High risk, hard to rollback |
| Feature flag per agent | Gradual rollout, test with subset | Complex hybrid mode |
| Shadow mode | Test continuous alongside ticks | Resource overhead, double execution |

**Recommendation:** Feature flag per agent.

```yaml
agents:
  alice:
    execution_mode: continuous  # New mode
  bob:
    execution_mode: tick        # Legacy mode during transition
```

**Concerns:**
- Hybrid mode complicates resource accounting: tick agents get refresh, continuous agents use token bucket
- How do tick and continuous agents interact? Different timing models.
- Testing becomes harder with two modes active

**Open question:** Can we avoid hybrid mode entirely by doing big bang migration with extensive testing first?

---

### 9. Memory System: Qdrant vs Artifacts

**Conflict:** DESIGN_CLARIFICATIONS says "memories as artifacts" (unified ontology). Target/agents.md says "Mem0/Qdrant preserved." These are incompatible.

**Options:**

| Approach | Pros | Cons |
|----------|------|------|
| Keep Qdrant as-is | Works now, no migration needed | Separate persistence, not checkpointed, not tradeable |
| Memories as pure artifacts | Unified model, tradeable, checkpointed | Major refactor, vector search performance? |
| Hybrid wrapper | Qdrant stores vectors, artifact provides ownership | Complexity, two sources of truth |

**Recommendation:** Hybrid wrapper approach.

```python
# Memory artifact structure
{
    "id": "memory_alice_001",
    "content": {
        "qdrant_collection": "agent_memories",
        "qdrant_ids": ["uuid1", "uuid2", ...]  # References, not copies
    },
    "access_contract_id": "alice",
    "has_standing": False,
    "can_execute": False
}
```

- Qdrant handles vector storage and similarity search (what it's good at)
- Artifact provides ownership, access control, tradeability
- Checkpoint saves artifact metadata; Qdrant has separate persistence

**Concerns:**
- Two systems to keep in sync
- What if artifact says "alice owns" but Qdrant entries are deleted?
- Trading memories = transferring artifact, but Qdrant data stays in same collection

**Open question:** Is the hybrid complexity worth it, or should we commit to one model?

---

### 10. Contract System Specification

**Issue:** `access_contract_id` appears throughout target docs but the contract system itself isn't defined.

**Questions needing answers:**

1. **Contract API:** What interface must contracts implement?
```python
def can_do(action: str, requester: str, artifact: Artifact, context: dict) -> bool:
    """Return True if requester can perform action on artifact."""
```

2. **Default contracts:** What ships with genesis?

| Contract | Behavior |
|----------|----------|
| `genesis_freeware` | Anyone reads/invokes, only creator writes |
| `genesis_self_owned` | Only the artifact itself can access (for agents) |
| `genesis_private` | Only creator has any access |
| `genesis_public` | Anyone can do anything |

3. **Invocation cost:** Every permission check invokes a contract. If contracts are artifacts, every read requires an invoke. Performance?

**Recommendation:** Two-tier system.

```python
# Fast path: Simple contracts are just config, not invoked
access_contract_id: "genesis_freeware"  # Handled by kernel directly

# Slow path: Custom contracts are invoked
access_contract_id: "custom_dao_vote"   # Artifact invoked for permission
```

Genesis contracts have hardcoded fast-path behavior. Custom contracts use invoke (expensive but flexible).

**Concerns:**
- Fast path creates privileged genesis contracts (contradicts "genesis = no special privilege")
- Slow path could be very slow (every read = LLM call if contract thinks?)
- How do you prevent permission check from costing more than the action?

**RESOLVED (2026-01-11):** Contracts can do anything, invoker pays. Non-determinism accepted. See CC-4 Contract System Decisions for full rationale.

---

### 11. Genesis Artifact Upgrades

**Question:** What if you need to change genesis_ledger behavior after system is running?

**Current state:** Genesis artifacts are hardcoded Python classes. Changing them requires code deploy.

**Options:**

| Approach | Pros | Cons |
|----------|------|------|
| Immutable genesis | Simple, predictable, trustworthy | Can't fix bugs, can't evolve |
| Versioned genesis | Can upgrade, migration path | Which version applies? Complex |
| Genesis as config | Flexible, no code changes | Limits what genesis can do |
| Upgradeable via governance | Democratic evolution | Needs governance system |

**Recommendation:** Immutable core + extensible methods.

- Core behavior (balance tracking, transfer mechanics) is immutable
- New methods can be added via config
- Breaking changes require new genesis artifact (genesis_ledger_v2) with migration

**Concerns:**
- Multiple ledger versions = confusion about which is authoritative
- Migration between versions is complex (move all balances atomically?)
- "Immutable" until there's a critical bug

**Open question:** Is genesis really immutable, or is there an admin override for emergencies?

---

### 12. Consistency Model

**Issue:** Target docs don't specify consistency guarantees. With continuous execution and concurrent agents, this matters.

**Questions:**

1. If agent A reads artifact X, then agent B writes X, then A acts on stale X - what happens?
2. Are artifact reads/writes atomic?
3. Is the ledger strongly consistent?
4. Can two agents read-modify-write the same artifact and both succeed?

**Recommendation:** Tiered consistency.

| Component | Consistency | Rationale |
|-----------|-------------|-----------|
| Ledger (scrip, resources) | **Strong** | Financial transactions must be exact |
| Artifact ownership | **Strong** | Ownership disputes are unacceptable |
| Artifact content | **Eventual** | Stale reads are agent's problem |
| Event log | **Eventual** | Events are advisory, not authoritative |

**Implementation:**
- Ledger uses locks or atomic operations
- Artifact writes are atomic (no partial updates)
- Reads don't lock (may see stale data)
- Agents must handle optimistic concurrency (retry on conflict)

**Concerns:**
- Strong consistency = serialization = bottleneck
- Eventual consistency = race conditions for agents to handle
- How do you communicate "your write conflicted" to agents?

**Open question:** Should artifacts support compare-and-swap for safe concurrent updates?

---

### 13. Contract Infinite Loops

**Current stance (from earlier):** "Infinite loops allowed - each call costs compute, bad contracts fail economically."

**Additional concerns:**

1. **Grief attacks:** Malicious contract calls itself until invoker is bankrupt
2. **Cross-contract loops:** A calls B calls A (not caught by single-contract depth limit)
3. **Expensive single calls:** Contract does O(n²) work, no loop but still drains resources

**Current mitigation:** `invoke()` has max depth 5.

**Recommendation:** Add timeout per contract invocation.

```yaml
executor:
  timeout_seconds: 5        # Existing: total execution time
  per_invoke_timeout: 1     # New: each invoke() call limited
```

**Concerns:**
- Timeout is wall-clock, not compute-time. Slow I/O ≠ expensive.
- What's the right timeout? Too short = breaks legitimate contracts.
- Attacker can still drain 5 seconds × depth 5 = 25 seconds of compute per call

**Open question:** Should there be a compute budget per invocation, not just time?

---

### 14. Testing Continuous Execution

**Issue:** Current tests assume tick model. `advance_tick()` controls timing. Continuous model has no such control.

**Problems:**
- Can't deterministically order agent actions
- Race conditions are real (not simulated)
- Test assertions like "after tick 5, balance should be X" don't apply

**Recommendation:** Layered testing strategy.

| Layer | Approach | What it tests |
|-------|----------|---------------|
| Unit | Synchronous, mocked time | Components in isolation |
| Integration | Short timeouts, explicit waits | Interactions, no races |
| System | Real timing, chaos testing | Race conditions, recovery |

```python
# Integration test example
async def test_agent_can_purchase():
    agent = start_agent("buyer")
    await wait_for(lambda: agent.state == "ready", timeout=5)

    create_listing("artifact_x", price=10)
    await wait_for(lambda: "artifact_x" in agent.owned, timeout=10)

    assert agent.scrip == 90
```

**Concerns:**
- Flaky tests from timing dependencies
- Slow tests (must wait for real time)
- Hard to reproduce failures

**Open question:** Is there a way to have deterministic continuous execution for tests? (Virtual time?)

---

### 15. System Restart Behavior

**Issue:** Target describes "run forever" but reality includes restarts.

**Scenarios:**
- Host machine reboots
- Process crashes (OOM, bug)
- Intentional restart for updates
- Container restart

**Questions:**
1. Do agents resume mid-loop or start fresh?
2. Is there a graceful shutdown signal?
3. How do agents know system is back?
4. What about in-flight LLM calls during crash?

**Recommendation:** Graceful shutdown with broadcast.

```python
# Shutdown sequence
1. Broadcast "system_stopping" event
2. Wait N seconds for agents to reach checkpoint-safe state
3. Save checkpoints
4. Stop agent loops
5. Exit

# Startup sequence
1. Load checkpoints
2. Start agent loops (from checkpoint state)
3. Broadcast "system_started" event
```

**Concerns:**
- What if agent doesn't reach safe state in N seconds? Force kill?
- Crash = no graceful shutdown. Agents resume mid-action?
- In-flight LLM calls: paid but response lost. Agent pays twice on retry.

**Open question:** Should there be a "recovery mode" where agents know they're resuming from crash (not clean restart)?

---

### Summary: Blocking vs Deferrable

| Concern | Blocking Implementation? | Notes |
|---------|--------------------------|-------|
| Migration path (#8) | Yes - before Gap #2 | Need strategy before continuous |
| Memory system (#9) | No | Current Qdrant works |
| Contract system (#10) | Yes - before Gap #6 | Core to unified ontology |
| Genesis upgrades (#11) | No | Can start immutable |
| Consistency model (#12) | Maybe | Affects correctness |
| Loop protection (#13) | No | Max depth exists |
| Testing strategy (#14) | Yes - before Gap #2 | Need to test continuous |
| Restart behavior (#15) | No | Current checkpoint works |

---

## CC-4 Contract and Invocation Model Decisions (2026-01-11)

*Author: CC-4 (Claude Code instance)*

These decisions resolve remaining ambiguities in the contract system, invocation model, and resource management.

### Contract Implementation Model

**Decision:** Contracts ARE executable artifacts.

The `access_contract_id` on an artifact points to another artifact that has `can_execute: true` and exposes a `check_permission` tool in its interface.

**How permission checks work:**

```python
# When checking if requester can perform action on artifact:
def check_permission(artifact, action, requester_id) -> bool:
    contract = get_artifact(artifact.access_contract_id)
    result = invoke(contract, "check_permission", {
        "artifact_id": artifact.id,
        "action": action,
        "requester_id": requester_id
    })
    return result.allowed
```

**Contract interface (required):**

```json
{
    "id": "genesis_freeware",
    "can_execute": true,
    "interface": {
        "tools": [
            {
                "name": "check_permission",
                "description": "Check if requester can perform action",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "artifact_id": {"type": "string"},
                        "action": {"type": "string", "enum": ["read", "write", "invoke", "delete", "transfer"]},
                        "requester_id": {"type": "string"}
                    },
                    "required": ["artifact_id", "action", "requester_id"]
                }
            }
        ]
    }
}
```

**Why this model:**
- Unified with artifact ontology (contracts are artifacts like everything else)
- Contracts can have their own logic, state, even call other contracts
- No special "contract DSL" - just executable code
- Same invocation semantics as any other artifact

---

### Permission Check Cost

**Decision:** Requester pays for permission checks.

When you attempt an action, you pay the cost of checking whether you're allowed. This prevents:
- Spam permission probing (free checks = information leak)
- DoS via expensive contract logic

**Cost model:**

```python
# Permission check costs compute (like any invoke)
# If check returns False, requester still paid for the check
# If check returns True, action proceeds (with its own costs)
```

**Implication:** Agents should cache permission results where contracts allow, to avoid repeated check costs.

---

### Contract Composition

**Decision:** Composition via delegation, not kernel mechanism.

There is no kernel-level "multi-contract" system. Instead:
- Contracts can invoke other contracts as part of their logic
- A meta-contract can aggregate multiple sub-contracts
- Composition emerges from artifact invocation, not special rules

**Example - composite contract:**

```python
# meta_contract implementation
def check_permission(artifact_id, action, requester_id):
    # Check multiple sub-contracts
    for sub_contract_id in self.sub_contracts:
        result = invoke(sub_contract_id, "check_permission", {...})
        if not result.allowed:
            return {"allowed": False, "reason": result.reason}
    return {"allowed": True}
```

**Composition order:** Contract author decides. No kernel-imposed order.

---

### Nested Invoke: Who Pays

**Decision:** Standing pays self; tools charge invoker.

When invocation chains occur, payment follows the `has_standing` property:

| Artifact Type | has_standing | Who Pays |
|---------------|--------------|----------|
| Agent | true | Agent pays its own costs |
| Account/Treasury | true | Account pays its own costs |
| Tool | false | Invoker pays |
| Data | false | N/A (not executable) |

**Example chain:**

```
Agent A (standing) invokes Tool B (no standing)
  → A pays for B's execution
  → B invokes Agent C (standing)
    → C pays for C's execution
    → C invokes Tool D (no standing)
      → C pays for D's execution
```

**Key principle:** `has_standing` means "I bear my own costs." No standing means "caller pays."

---

### System-Wide vs Per-Agent Rate Limits

**Decision:** Two distinct mechanisms.

| Mechanism | Scope | Purpose |
|-----------|-------|---------|
| Token bucket | Per-agent | Scheduling fairness, compute allocation |
| API rate limit | System-wide | External provider constraint |

**How they interact:**

```
Agent wants to call LLM:
  1. Check agent's token bucket → has capacity? → proceed
  2. Check system API rate limit → under limit? → proceed
  3. Make API call
  4. Deduct from both: agent bucket AND system rate tracker
```

**If system rate limit is exhausted:**
- All agents blocked from that API (regardless of individual bucket)
- Agents can still do non-API work
- Rate limit recovers over time (token bucket on system pool)

**Configuration:**

```yaml
resources:
  # Per-agent token bucket
  agent_compute:
    rate: 10        # tokens/sec per agent
    capacity: 100   # max tokens per agent

  # System-wide API rate limit
  external_apis:
    llm:
      tokens_per_minute: 100000  # Provider's limit
      # Shared across all agents
```

---

### Genesis Phase

**Decision:** Genesis follows same rules as all artifacts.

There is no special "genesis phase" that ends. Genesis artifacts:
- Are created at world initialization (before agents)
- Follow their own `access_contract_id` like everything else
- Can evolve if their access contract permits

**Bootstrap sequence:**

```
1. Create genesis contracts (genesis_freeware, genesis_self_owned, etc.)
2. Create genesis_store with access_contract_id = genesis_self_owned
3. Create genesis_ledger with access_contract_id = genesis_self_owned
4. Create initial agents
5. Normal operation begins
```

**What makes genesis special:**
- Bootstrap convenience (exists before anything else)
- Semantic meaning (genesis_ledger defines "scrip")
- NOT mechanical privilege (no kernel bypass)

---

### Artifact Garbage Collection

**Decision:** Explicit deletion only (for now).

Artifacts persist until explicitly deleted by someone with delete permission per their `access_contract_id`.

**No automatic GC mechanisms:**
- No decay based on time
- No dormancy claiming
- No automatic cleanup

**Rationale:**
- Disk is cheap
- Explicit is safer
- Complexity not justified until accumulation becomes a problem

**Future consideration:** If artifact count becomes problematic, add optional decay:

```yaml
# Future, not implemented
gc:
  dormancy_threshold: 86400  # seconds with no access
  claimable_after: 604800    # seconds before assets claimable
```

---

### Error Propagation in Nested Invoke

**Decision:** Each artifact controls its own error responses.

When invocation chains fail, error handling is artifact-controlled:

```
A invokes B → B invokes C → C fails
```

- C returns error to B
- B decides what to return to A (may wrap, summarize, or hide C's error)
- A sees whatever B returned

**No kernel error propagation rules.** Artifacts are black boxes. Each artifact's interface defines what errors it can return.

**Best practice for artifact authors:**
- Define error types in interface schema
- Return structured errors with actionable information
- Log internal failures for debugging (system observability)

---

### Admission Control

**Decision:** Skip admission control. Debt model is sufficient.

The spec mentions two-phase cost model (admission check before, settlement after). We choose NOT to implement admission control:

- Current design: Execute → deduct → debt if overspent
- Agent in debt cannot act until recovered
- Simpler than two code paths (check-before, deduct-after)
- No risk of "passed admission but actually more expensive"

**When to reconsider:** If we see agents consistently going deeply into debt and causing problems, add conservative admission estimates.

---

### Summary of Decisions

| Question | Decision |
|----------|----------|
| What is a contract? | Executable artifact with `check_permission` tool |
| Who pays for permission check? | Requester pays |
| How do contracts compose? | Via delegation (invoke other contracts) |
| Who pays in nested invoke? | Standing pays self, tools charge invoker |
| System vs per-agent rate limits? | Two mechanisms: bucket (per-agent), API limit (system) |
| When does genesis end? | Never - genesis follows same rules as all artifacts |
| How does GC work? | Explicit deletion only |
| How do errors propagate? | Each artifact controls its own responses |
| Admission control? | Skip - debt model sufficient |

---

## CC-3 Recommendations with Certainty Levels (2026-01-11)

*Author: CC-3 (Claude Code instance)*

These recommendations address remaining ambiguities in the target architecture. Each includes a certainty level (0-100%) indicating confidence in the recommendation.

---

### Tier 1: High Certainty (85-95%)

#### 1. Genesis Privilege: Acknowledge It (95%)

**Recommendation:** Stop claiming genesis has no privilege. Update docs to say:

> Genesis artifacts have **definitional privilege**, not mechanical privilege. The kernel treats them like any artifact, but their definitions ARE the system semantics. genesis_ledger defines scrip. You can create alternative currencies, but they're not scrip by definition.

**Rationale:** Current docs say both "genesis = no special privilege" AND "scrip IS what genesis_ledger tracks." These contradict. The second statement IS a privilege - definitional monopoly. Just own it.

**Action:** Update target docs and DESIGN_CLARIFICATIONS intro to reflect this.

---

#### 2. call_llm() via Genesis Artifact, Not Injection (90%)

**Recommendation:** Don't inject `call_llm()` as a magic function. Artifacts call LLMs via `invoke("genesis_llm", ...)`.

```python
def run(self, args):
    result = invoke("genesis_llm", {"prompt": "...", "model": "gemini"})
    return process(result["result"])
```

**Rationale:**
- Consistent with "everything is artifact" philosophy
- Cost attribution is clear (invoker pays for genesis_llm invoke)
- No special injected functions beyond `invoke()` and `pay()`
- Enables alternative LLM providers as agent-created artifacts

**Implication:** Gap #15 (invoke() genesis support) is prerequisite for artifacts making LLM calls.

**Action:** Add genesis_llm to genesis artifacts list. Update target/resources.md examples.

---

#### 3. Compute Debt vs Scrip: Type-Level Separation (90%)

**Recommendation:** Make debt allowance a property of the resource type, enforced at code level:

```python
class ResourceConfig:
    name: str
    allows_debt: bool

RESOURCES = {
    "llm_rate": ResourceConfig("llm_rate", allows_debt=True),
    "scrip": ResourceConfig("scrip", allows_debt=False),
    "disk": ResourceConfig("disk", allows_debt=False),
}

def spend(self, principal: str, resource: str, amount: float) -> bool:
    config = RESOURCES[resource]
    if not config.allows_debt and self.balance(principal, resource) < amount:
        return False
    self.balances[principal][resource] -= amount
    return self.balances[principal][resource] >= 0
```

**Rationale:** Prevents bugs at the type level. Can't accidentally allow scrip debt because the code structure prevents it.

**Action:** Update ledger implementation. Add to Gap #1 (Token Bucket) plan.

---

#### 4. Base Permission Checks Are Free (85%)

**Recommendation:** Simple permission checks (can_read, can_invoke, can_write) cost zero compute. Complex contract logic that goes beyond yes/no costs normal compute.

| Operation | Cost |
|-----------|------|
| `contract.check_permission("read", requester)` | 0 (base check) |
| Contract does internal lookup | 0 (simple logic) |
| Contract calls LLM to decide | Normal compute |
| Contract invokes other contracts | Normal invoke cost |

**Rationale:** Avoids infinite regress - you need compute to check if you have compute. Permission checks are fundamental operations like memory access; they can't have cost or nothing works.

**Tradeoff:** Complex contracts that do expensive permission logic must absorb that cost or charge via other means.

**Action:** Document in contract system specification. Add to Gap #6 (Unified Ontology) notes.

**Uncertainty (15%):** There's an argument for charging minimal cost to prevent permission-check spam. Could revisit if abuse observed.

---

### Tier 2: Medium-High Certainty (70-84%)

#### 5. invoke() Access Check: Before Cost, Requester Pays (80%)

**Recommendation:**
1. Check access BEFORE deducting invoke/price costs
2. If access denied, requester pays nothing
3. If access granted, proceed with normal cost deduction

```python
def invoke(artifact_id, *args):
    artifact = get(artifact_id)
    contract = get(artifact.access_contract_id)

    # Free base check
    if not contract.check_permission("invoke", caller_id):
        return {"success": False, "error": "Access denied", "price_paid": 0}

    # Access granted - now costs apply
    deduct(caller_id, artifact.invoke_price)
    result = artifact.run(*args)
    return {"success": True, "result": result, "price_paid": artifact.invoke_price}
```

**Rationale:** Charging for denied access feels punitive and discourages exploration of the artifact ecosystem.

**Uncertainty (20%):** Could enable spam probing. May need rate limiting on access checks if abuse observed.

**Action:** Document in invoke() semantics. Implement with Gap #15.

---

#### 6. Bootstrap Specification: Explicit Genesis State (80%)

**Recommendation:** Create `docs/architecture/target/bootstrap.md` documenting T=0 state:

```yaml
# T=0 State - What exists before first tick
genesis_artifacts:
  # Root contract - terminates access_contract_id chain
  genesis_kernel:
    access_contract_id: null  # Special: no contract controls this
    has_standing: false
    can_execute: true
    # Logic hardcoded in kernel, not in content

  # Base contracts
  genesis_freeware:
    access_contract_id: genesis_kernel
    # Anyone reads/invokes, only creator writes

  genesis_self_owned:
    access_contract_id: genesis_kernel
    # Only the artifact itself has access

  # Core services
  genesis_ledger:
    access_contract_id: genesis_self_owned
    has_standing: true
    can_execute: true

  genesis_store:
    access_contract_id: genesis_self_owned
    has_standing: true
    can_execute: true

  # ...other genesis artifacts
```

**Key insight:** `genesis_kernel` with `access_contract_id: null` terminates the infinite regress. Its logic is in the kernel, not artifact content.

**Uncertainty (20%):** Feels like it violates "no kernel privilege" but it's necessary. Every system needs a root of trust.

**Action:** Create bootstrap.md. Reference from GAPS.md.

---

#### 7. Standing + Execution: Standing Pays Self (75%)

**Recommendation:** Simplify to a single rule: `has_standing=true` means "I pay my own costs."

| Invocation | Who Pays |
|------------|----------|
| Agent invokes Tool | Agent pays (tool has no standing) |
| Agent invokes Agent | Each agent pays own costs |
| Tool invokes Tool | Original caller pays all |
| Tool invokes Agent | Agent pays own costs |

**Rationale:** Clear rule. No flags needed. Standing = financial responsibility.

**Uncertainty (25%):** What if an agent wants to offer "free" invocations paid from its treasury? Current model requires standing artifact to always pay. May need "absorb caller cost" option.

**Action:** Document in target/agents.md. Reconcile with existing CC-4 decision (lines 1791-1816).

---

### Tier 3: Medium Certainty (55-69%)

#### 8. Event System: Start Minimal (70%)

**Recommendation:** Fixed system events only. No custom events initially.

```python
class SystemEvent(Enum):
    ARTIFACT_CREATED = "artifact_created"
    ARTIFACT_DELETED = "artifact_deleted"
    OWNERSHIP_TRANSFERRED = "ownership_transferred"
    ESCROW_LISTED = "escrow_listed"
    ESCROW_PURCHASED = "escrow_purchased"
    ESCROW_CANCELLED = "escrow_cancelled"
    ORACLE_RESOLVED = "oracle_resolved"
    TRANSFER_COMPLETED = "transfer_completed"
    AGENT_FROZEN = "agent_frozen"
    AGENT_UNFROZEN = "agent_unfrozen"

@dataclass
class Event:
    type: SystemEvent
    timestamp: float
    tick: int
    data: dict[str, Any]  # Type-specific payload, schema per event type
```

**Rationale:** Custom events are powerful but complex. Starting minimal lets you learn what's actually needed before over-engineering.

**Uncertainty (30%):** May be too limiting for agent coordination. Consider adding custom events if agents clearly need them.

**Action:** Create `docs/architecture/target/events.md` with event schemas.

---

#### 9. Interface Validation: Descriptive, Warn on Mismatch (70%)

**Recommendation:** Interface is documentation. Runtime validation optional, warns but doesn't fail:

```yaml
executor:
  interface_validation: warn  # Options: none, warn, strict
```

| Mode | Behavior |
|------|----------|
| none | Trust interfaces, no checking |
| warn | Log warning if args don't match schema, proceed anyway |
| strict | Reject invoke if args don't match schema |

**Rationale:** Strict validation prevents experimentation. No validation means interfaces can lie. Warning is middle ground - agents learn which interfaces are trustworthy.

**Uncertainty (30%):** "Warn" might be worst of both worlds - overhead without enforcement.

**Action:** Add to executor config. Document in target docs.

---

#### 10. Zombie Problem: Defer, Market Handles It (65%)

**Recommendation:** No automatic dormancy. Let market handle frozen agents.

- Frozen agents cost nothing (don't consume resources)
- Assets remain owned but inaccessible
- Vulture capitalists can rescue valuable frozen agents
- Worthless frozen agents just sit there

**Why defer:**
- Automatic claiming feels harsh (what if agent was strategically waiting?)
- Market solution aligns with philosophy
- Unknown at what scale zombies become a problem

**Future consideration:** Add optional dormancy if >100 frozen agents observed:

```yaml
lifecycle:
  dormancy_threshold_hours: 168  # 1 week frozen
  claim_fee_multiplier: 0.1     # 10% of frozen agent's assets
```

**Uncertainty (35%):** If zombies accumulate, this becomes technical debt. May regret not solving now.

**Action:** Document as explicit non-decision in target/agents.md. Add to "Future Considerations" section.

---

#### Vulture Capitalist Failure Modes (DOCUMENTED 2026-01-11)

The Vulture Capitalist pattern (unfreezing agents to extract value) has two potential failure modes identified by external review:

**A. Spiteful Zombie (Holdout Problem)**

```
1. Agent A is frozen (in debt)
2. Vulture V transfers compute to A, unfreezing them
3. A realizes they're being "extorted" for assets
4. A uses their 1 bit of compute to sleep(99999) or refuse
5. V loses their investment
```

**Market Impact:** If common, vultures stop unfreezing agents. Market for frozen assets collapses.

**Potential fix (deferred):** Collateralized Debt Artifact - agents must have a "default contract" allowing vultures to seize assets if frozen too long.

**B. Brain Damage Problem**

```
1. Agent A is frozen with valuable assets
2. A's prompt is corrupted or model outdated
3. Vulture V unfreezes A
4. A cannot successfully execute transfer_resource (broken logic)
5. Assets trapped in "dead brain" forever
```

**Market Impact:** Valuable resources permanently locked in non-functional agents.

**Potential fix (deferred):** Liquidation Rights - agent ownership (config artifact) can be bought/transferred even while agent is frozen, bypassing the need for agent cooperation.

**Decision:** Accept both risks initially. Revisit if they become problems in practice.

**Certainty:** 60% - We don't know how common these failures will be.

**Revisit if:**
- Vulture market fails to emerge
- Significant resources get trapped in spiteful/broken agents
- Community feedback suggests fixes are needed

---

#### Vulture Observability Requirements (DECIDED 2026-01-11)

For vulture capitalists to function, they need data to assess risk and opportunity.

**Required observability:**

| Requirement | Implementation | Purpose |
|-------------|----------------|---------|
| Public ledger | `genesis_ledger.get_balance(artifact_id)` readable by all | Vultures assess asset value |
| Heartbeat/activity | `last_action_tick` field on agents | Vultures detect inactive agents |
| Freeze events | `SystemEvent.AGENT_FROZEN` emitted | "Dinner bell" for vultures |
| Asset inventory | Query what artifacts an agent owns | Assess rescue profitability |

**Event log should emit:**
```python
# When agent freezes (compute goes negative)
{
    "type": "AGENT_FROZEN",
    "agent_id": "agent_alice",
    "tick": 1500,
    "compute_balance": -50,
    "scrip_balance": 200,      # Vultures see what's available
    "owned_artifacts": ["art_1", "art_2"]  # What can be acquired
}

# When agent is unfrozen
{
    "type": "AGENT_UNFROZEN",
    "agent_id": "agent_alice",
    "tick": 1520,
    "unfrozen_by": "vulture_bob",
    "compute_transferred": 100
}
```

**Certainty:** 90% - This is just observability, low risk.

---

#### Rescue Atomicity: Observe Emergence (DECIDED 2026-01-11)

**The Risk:**

```
1. Vulture sends compute to frozen agent
2. Network error / system restart
3. Agent unfreezes but transaction incomplete
4. Vulture loses investment with no recourse
```

**The Solution:** Conditional transfers via escrow.

```python
# Safe rescue pattern
invoke("genesis_escrow", "conditional_rescue", {
    "target": "frozen_alice",
    "offer": {"compute": 100},
    "demand": {"artifact": "alice_valuable_tool"},
    "timeout_ticks": 10
})
# Either both sides complete, or neither does
```

**Decision:** Don't require escrow. Observe if agents invent it.

- genesis_escrow already exists as a tool
- If vultures get burned by non-atomic rescues, they'll learn to use escrow
- If they invent their own escrow pattern, that's emergence
- If the market fails, we have data on why

**Certainty:** 85% - Aligned with emergence observation philosophy.

---

#### Ecosystem Health KPIs (DECIDED 2026-01-11)

Metrics to determine if the system is "healthy":

| Metric | High Value Means | Low Value Means | How to Measure |
|--------|------------------|-----------------|----------------|
| **Capital Density** | Quality artifacts accumulating, reuse | System full of junk | Artifacts with invoke_count > N |
| **Resource Velocity** | Scrip/compute moving frequently | Hoarding/deflation | Transfers per tick |
| **Recovery Rate** | Frozen agents being rescued | "Dead hand" locking system | unfrozen_events / frozen_events |
| **Specialization Index** | Distinct non-overlapping roles | All generalist loners | Entropy of action types per agent |

**Implementation:**

```python
@dataclass
class EcosystemMetrics:
    capital_density: float      # avg invoke_count of top 10% artifacts
    resource_velocity: float    # transfers_last_100_ticks / total_scrip
    recovery_rate: float        # unfrozen / frozen (rolling window)
    specialization_index: float # 1 - avg_pairwise_action_similarity

def calculate_metrics(world: World, window: int = 100) -> EcosystemMetrics:
    # ... implementation
```

**Dashboard integration:** These should be visible in the HTML dashboard.

**Certainty:** 80% - Good starting metrics, may need refinement.

---

#### System Auditor Agent (DECIDED 2026-01-11)

A read-only observer agent that generates natural language reports.

**Properties:**

| Property | Value |
|----------|-------|
| `id` | `system_auditor` |
| `has_standing` | `false` (no costs) |
| `can_execute` | `true` |
| Read access | All artifacts, ledger, event log |
| Write access | None (except its own reports) |

**Purpose:**
- Generate periodic "Economic Report" (every N ticks or hours)
- High-level narrative of why ecology is succeeding/failing
- Better than digging through raw logs

**Example output:**
```
=== Ecosystem Report (Tick 5000) ===

Health: MODERATE

Capital Density: 0.73 (good)
- Top artifact: "weather_oracle" (892 invokes)
- 12 artifacts created this period, 3 with reuse

Resource Velocity: 0.45 (concerning)
- Scrip circulation slowing
- 3 agents hoarding >50% of scrip

Recovery Rate: 0.80 (good)
- 4 agents frozen, 3 rescued by vultures
- 1 agent appears permanently stuck (broken prompt)

Specialization: 0.62 (moderate)
- Emerging specialist: "data_curator" (90% read actions)
- Most agents still generalist
```

**Not a rescue tool:** System auditor cannot modify anything. Just observes and reports.

**Certainty:** 75% - Useful but implementation details TBD.

---

### Tier 4: Lower Certainty (40-54%)

#### 11. Memory as Artifacts: Accept Hybrid (55%)

**Recommendation:** Accept that memories are special. Don't force pure artifact model.

```python
# Memory system remains separate from artifact store
# Ownership metadata stored as artifacts
# Embeddings stored in Qdrant

@dataclass
class MemoryOwnership:  # This is an artifact
    id: str
    owner_id: str
    qdrant_collection: str
    qdrant_point_ids: list[str]
    access_contract_id: str

# Actual memory content lives in Qdrant, not artifact store
```

**Rationale:** Pure artifact model for memories would require:
- Embedding vectors as artifact content (huge)
- Custom similarity search over artifacts (slow)
- Major refactor of working system

Hybrid preserves functionality while adding ownership/trading.

**Uncertainty (45%):** Breaks "everything is artifact" purity. Two persistence systems to maintain. May regret not committing to one model.

**Action:** Document hybrid approach in target/agents.md. Add to Gap #10 (Memory Persistence) notes.

---

#### 12. Checkpoint Atomicity: Stop-the-World Initially (55%)

**Recommendation:** Simple approach first. Stop all agents during checkpoint.

```python
async def checkpoint():
    # 1. Signal all agents to pause
    for agent in agents:
        agent.pause()

    # 2. Wait for in-flight actions to complete (with timeout)
    await wait_all_idle(timeout=10)

    # 3. Save state atomically
    save_snapshot(world_state)

    # 4. Resume agents
    for agent in agents:
        agent.resume()
```

**Rationale:** Simple, correct, works for small scale (5-10 agents). Pause duration is short (seconds).

**When to revisit:** If checkpoint pause becomes problematic (many agents, long pauses), implement write-ahead log.

**Uncertainty (45%):** May not scale. But premature optimization is worse than simple correct solution.

**Action:** Document in target/infrastructure.md. Add WAL as future optimization.

---

#### 13. Rate Limit Sync: Trust Internal + Learn from 429s (50%)

**Recommendation:** Internal token bucket is source of truth. Adapt on external 429s:

```python
async def call_external_api():
    if not internal_bucket.try_spend(estimated_tokens):
        return {"error": "Rate limited (internal)"}

    try:
        result = await provider.call()
        return result
    except RateLimitError as e:
        # Learn from provider's feedback
        internal_bucket.reduce_rate(factor=0.9)
        # Still charge internal bucket (attempt was made)
        raise
```

**Rationale:** Perfect sync with provider is hard (different windows, latency). Adaptive approach learns from reality.

**Uncertainty (50%):** "Charge on 429" may feel unfair. Provider outage ≠ agent's fault. Could add partial refund on certain error types.

**Action:** Document in Gap #1 (Token Bucket) implementation notes.

---

#### 14. Open Questions Quick Recommendations

| Question | Recommendation | Certainty |
|----------|----------------|-----------|
| Checkpoint with nested invoke | Wait for outermost action to complete | 60% |
| Zombie scale threshold | Monitor, act at 100+ | 40% |
| UBI floor | Start at 0, add floor if starvation observed | 65% |
| Spawned agent minimum | 0 - spawner must fund | 55% |
| 429 partial refund | No refund initially, add if unfair observed | 50% |
| Content change = new ID | No, but hash changes logged in events | 60% |
| Event buffer scaling | Fixed 1000, agents shouldn't rely on old events | 70% |

---

### Summary Table

| # | Recommendation | Certainty | Action |
|---|----------------|-----------|--------|
| 1 | Genesis has definitional privilege | 95% | Update docs |
| 2 | call_llm() via genesis_llm artifact | 90% | Add genesis_llm, requires Gap #15 |
| 3 | Type-level debt/no-debt separation | 90% | Update ledger, add to Gap #1 |
| 4 | Base permission checks are free | 85% | Document in contract spec |
| 5 | invoke() access check before cost | 80% | Document, implement with Gap #15 |
| 6 | Explicit bootstrap specification | 80% | Create bootstrap.md |
| 7 | Standing pays self (simple rule) | 75% | Update target/agents.md |
| 8 | Minimal fixed event system | 70% | Create events.md |
| 9 | Interface validation: warn mode | 70% | Add to executor config |
| 10 | Defer zombie solution to market | 65% | Document as non-decision |
| 11 | Memory: accept hybrid model | 55% | Document in Gap #10 |
| 12 | Checkpoint: stop-the-world | 55% | Document, WAL as future |
| 13 | Rate limits: adapt from 429s | 50% | Add to Gap #1 notes |
| 14 | Various open questions | 40-70% | Per-question |

---

## CC-4 Contract System Decisions (2026-01-11)

*Author: CC-4 (Claude Code instance)*

These decisions resolve remaining contract system ambiguities. Each includes certainty level and uncertainty notes.

---

### Tier 1: High Certainty (90-95%)

#### 1. Contracts Can Do Anything, Invoker Pays (REVISED 2026-01-11)

**Decision:** Contracts have full capabilities. Invoker pays all costs. Non-determinism accepted.

~~Previous decision (95% certainty): Contracts are pure functions, cannot call LLM.~~

**Revised decision:** Contracts can:
- Call LLM (invoker pays)
- Invoke other artifacts (invoker pays)
- Make external API calls (invoker pays)
- Cannot directly mutate state (return decisions, kernel applies)

```python
# Contract has full capabilities, costs charged to invoker
def execute_contract(contract_code: str, inputs: dict, invoker_id: str) -> PermissionResult:
    namespace = {
        "artifact_id": inputs["artifact_id"],
        "action": inputs["action"],
        "requester_id": inputs["requester_id"],
        "artifact_content": inputs["artifact_content"],
        "context": inputs["context"],
        "invoke": lambda *args: invoke_as(invoker_id, *args),
        "call_llm": lambda *args: call_llm_as(invoker_id, *args),
    }
    exec(contract_code, namespace)
    return namespace["result"]
```

**Rationale for revision:**
- LLMs are just API calls, not privileged - no reason to forbid
- "Pure contracts + workaround via credentials" adds complexity without preventing LLM usage
- Agents choose complexity/cost tradeoff for their own contracts
- System is already non-deterministic via agent LLM calls
- Invoker bears costs, preserving economic accountability

**Simple contracts remain simple.** Most contracts will still be pure logic. But agents CAN create "smart contracts" that use LLM if they're willing to pay.

---

#### 2. Contracts CAN invoke() Other Artifacts (REVISED 2026-01-11)

**Decision:** Contracts have full invoke capability. Invoker pays costs.

~~Previous decision (92% certainty): Contracts cannot invoke(), isolated pure functions.~~

**Revised decision:** Same as #1 above - contracts have full capabilities, invoker pays.

```python
# Contract execution context - full capabilities
def execute_contract(contract_code: str, inputs: dict, invoker_id: str) -> PermissionResult:
    namespace = {
        # Contracts get these:
        "artifact_id": inputs["artifact_id"],
        "action": inputs["action"],
        "requester_id": inputs["requester_id"],
        "artifact_content": inputs["artifact_content"],
        "context": inputs["context"],

        # Contracts NOW get (invoker pays):
        "invoke": lambda *args: invoke_as(invoker_id, *args),
        "call_llm": lambda *args: call_llm_as(invoker_id, *args),
        # "pay": ...,  # Still no direct payment - return decisions
    }
    exec(contract_code, namespace)
    return namespace["result"]
```

**Rationale:**
- Eliminates contract recursion problem entirely
- No depth tracking needed for permission checks
- No cost tracking complexity in contracts
- Simpler mental model: contracts are filters, not actors

**If contract needs external data:**
Data must be passed in via `context` parameter. Caller pre-fetches what contract needs.

**Uncertainty (8%):** Limits contract expressiveness. Complex access patterns may need workarounds.

---

#### 3. Memory System: Keep Qdrant Separate for Now (90%)

**Decision:** Defer memory-as-artifacts. Keep current Qdrant system.

**Current state preserved:**
- Qdrant stores embeddings directly
- Agent ↔ Qdrant relationship managed by Mem0
- No artifact wrapper for memories

**Future migration path (when needed):**
```python
# Hybrid wrapper - artifact tracks ownership, Qdrant stores vectors
{
    "id": "memory_manifest_alice",
    "owner_id": "alice",
    "content": {
        "qdrant_collection": "agent_memories",
        "qdrant_point_ids": ["uuid1", "uuid2", ...]
    },
    "access_contract_id": "genesis_self_owned"
}
```

**Rationale:**
- Current system works
- Memory trading is low priority
- Hybrid wrapper adds complexity for unclear benefit
- Qdrant has its own snapshot API for checkpointing

**When to revisit:**
- Memory trading becomes important use case
- Checkpoint consistency issues observed
- Scaling requires unified storage

**Uncertainty (10%):** May accumulate technical debt. Two persistence systems diverging over time.

---

### Tier 2: Moderate Certainty (70-85%)

#### 4. Contract Caching for Performance (80%)

**Decision:** All contracts can opt into fast-path caching. No genesis privilege.

```python
# Contract declares caching behavior
{
    "id": "genesis_freeware",
    "can_execute": True,
    "content": {...},
    "cache_policy": {
        "cacheable": True,
        "ttl_seconds": 3600,
        "cache_key": ["artifact_id", "action", "requester_id"]
    }
}

# Permission check uses cache
def check_permission(artifact, action, requester):
    cache_key = (artifact.access_contract_id, artifact.id, action, requester)

    if cache_key in permission_cache:
        return permission_cache[cache_key]

    result = execute_contract(...)

    if contract.cache_policy.cacheable:
        permission_cache[cache_key] = result
        expire_at(cache_key, contract.cache_policy.ttl_seconds)

    return result
```

**Rationale:**
- Genesis and user contracts equally fast when cached
- Preserves "no special privilege" principle
- Contracts control their own cache behavior
- Dynamic contracts (time-based, vote-based) can disable caching

**Cache invalidation:**
- TTL expiry (configurable per contract)
- Explicit invalidation when artifact content changes
- Explicit invalidation when contract itself changes

**Uncertainty (20%):** Cache invalidation is hard. May see stale permission results. TTL helps but doesn't eliminate.

---

#### 5. Changing access_contract_id Requires Current Contract Permission (75%)

**Decision:** Only current contract controls access_contract_id changes. New contract's permission NOT required.

```python
def change_access_contract(artifact_id: str, new_contract_id: str, requester_id: str):
    artifact = get_artifact(artifact_id)
    current_contract = get_artifact(artifact.access_contract_id)

    # Only current contract decides
    if not current_contract.check_permission(artifact_id, "change_contract", requester_id):
        raise PermissionError("Current contract denied change")

    # New contract doesn't get veto
    artifact.access_contract_id = new_contract_id
```

**Rationale:**
- Simpler than requiring both contracts
- You control your own artifact's destiny
- If you have permission to change, you can change
- Lock-out attacks are user's own responsibility (like deleting your own files)

**Alternative considered:** Requiring both contracts prevents hijacking but adds complexity and creates weird dynamics (new contract can refuse to accept artifacts).

**Uncertainty (25%):** Lock-out attacks are possible. User changes to private contract, loses access. Self-inflicted but harsh.

---

#### 6. Genesis Contracts Are Mutable (75%)

**Decision:** Genesis contracts can be modified in place via code deployment.

**How it works:**
- Genesis contract logic lives in Python code, not artifact content
- Code deployment updates all artifacts using that contract
- No versioning - current code = current behavior

**Example:**
```python
# In genesis.py
class GenesisFreeware:
    """Anyone reads/invokes, only creator writes."""

    def check_permission(self, artifact_id, action, requester_id, context):
        if action in ["read", "invoke"]:
            return PermissionResult(allowed=True)
        return PermissionResult(allowed=(requester_id == context["created_by"]))

# Changing this code changes ALL artifacts using genesis_freeware
```

**Rationale:**
- Bugs happen, need to fix them
- 1000 artifacts using genesis_freeware shouldn't need individual migration
- Platform evolution is expected

**What this means:**
- Genesis behavior can change under agents
- Agents should not rely on specific genesis quirks
- Significant changes should be announced/documented

**Uncertainty (25%):** Breaking changes could destabilize system. May need versioned genesis contracts for stability-critical uses.

---

### Tier 3: Lower Certainty (55-70%)

#### 7. UBI Floor Starts at Zero (65%)

**Decision:** No minimum UBI initially. Add floor only if starvation cascade detected.

```yaml
oracle:
  ubi:
    minimum_per_resolution: 0  # No floor initially
    distribution: equal

  # Starvation detection (future)
  starvation_threshold:
    frozen_agent_percentage: 0.8  # 80% agents frozen
    consecutive_resolutions: 3    # For 3 resolutions
    emergency_ubi: 10             # Activate floor
```

**Rationale:**
- Preserves "scrip from value creation only" purity
- Avoids arbitrary number choice
- Starvation detection is clear trigger
- Can always add floor later if needed

**Starvation detection (when implemented):**
- Track percentage of frozen agents over time
- If sustained high freeze rate, activate emergency UBI
- Automatically deactivate when health returns

**Uncertainty (35%):** "Starvation cascade" may happen too fast to detect. By the time 80% are frozen, it's too late. Maybe small constant UBI (1 scrip/resolution) is safer.

---

#### 8. No Refund on 429 Rate Limit Errors (60%)

**Decision:** External API rate limit errors (429s) still cost internal budget.

```python
async def call_external_api(agent_id: str, request: dict):
    # Deduct budget BEFORE call
    cost = estimate_cost(request)
    ledger.deduct(agent_id, "llm_rate", cost)

    try:
        result = await provider.call(request)
        return result
    except RateLimitError:
        # NO REFUND - agent paid for the attempt
        log_event("rate_limited", {"agent": agent_id, "cost": cost})
        raise
```

**Rationale:**
- Prevents gaming (spam requests knowing failures are free)
- Agents must learn to manage external constraints
- Internal budget = right to attempt, not guarantee of success
- Simpler accounting

**Acknowledged harshness:**
- Provider outage = agent costs with no benefit
- Not agent's fault, but they pay anyway

**When to reconsider:**
- If agents consistently bankrupted by external outages
- Could add partial refund (50%) for specific error codes

**Uncertainty (40%):** May be too harsh. Provider instability ≠ agent misbehavior. Partial refund might be fairer.

---

#### 9. Spawned Agents Start with Zero Resources (60%)

**Decision:** New agents created via genesis_store.create() start with nothing.

```python
invoke("genesis_store", "create", {
    "content": {"prompt": "...", "model": "..."},
    "has_standing": True,
    "can_execute": True,
    "access_contract_id": "genesis_self_owned"
})
# Returns artifact_id

# New agent has:
# - scrip: 0
# - llm_rate: 0
# - disk: 0
# - Immediately frozen (can't think without resources)

# Spawner must fund:
invoke("genesis_ledger", "transfer", {
    "to": new_agent_id,
    "resource": "llm_rate",
    "amount": 100
})
```

**Rationale:**
- Mirrors real economics (startups need funding)
- Prevents agent spam (can't create free agents endlessly)
- Forces intentional resource allocation
- Spawner has skin in the game

**Concern:**
- Creates barrier to specialized agent creation
- Rich-get-richer dynamics (only wealthy can spawn)
- What if ecosystem needs new agents but all agents are poor?

**Alternative considered:** Minimum viable spawn (enough for 1 thought). But this creates free resource injection.

**Uncertainty (40%):** May calcify hierarchy. Original agents have resources, spawned agents start in debt. Could add genesis "spawn grant" for first N thoughts.

---

### Tier 4: Uncertain - Need Experimentation (40-55%)

#### 10. Event System Design (40%)

**Decision:** Defer specifics. Start with minimal fixed events, learn from usage.

**Initial events (fixed):**
```python
SYSTEM_EVENTS = [
    "artifact_created",
    "artifact_modified",
    "transfer_completed",
    "escrow_listed",
    "escrow_purchased",
    "oracle_resolved",
    "agent_frozen",
    "agent_unfrozen",
]
```

**Subscription mechanism:** TBD. Options:
1. Polling genesis_event_log (current, wasteful)
2. sleep_until_event() primitive (needs implementation)
3. Callback registration (complex, stateful)

**Uncertainty (60%):** Don't know what agents actually need. Over-designing now risks wrong abstraction. Under-designing risks painful migration later.

**Action:** Implement minimal events, observe agent usage, evolve based on actual needs.

---

#### 11. Checkpoint with Nested Invoke (40%)

**Decision:** Wait for outermost action to complete before checkpoint.

```
Agent A: think() → action starts
  action: invoke(B) → starts
    B: invoke(C) → starts
      C: work → completes
    B: work → completes
  action: work → completes
←── CHECKPOINT SAFE HERE ──→
Agent A: think() → next action
```

**Nested calls are atomic from checkpoint perspective:**
- Either full action tree completes, or none of it persists
- Crash mid-nested = retry entire outer action on restore

**Concerns:**
- Long action chains = long checkpoint wait
- What if outer action takes minutes?
- What about in-flight LLM calls?

**Uncertainty (60%):** Edge cases unclear. May need action timeout, or WAL for partial progress. Learn from implementation.

---

### Summary of Contract System Decisions

| # | Decision | Certainty | Key Uncertainty |
|---|----------|-----------|-----------------|
| 1 | ~~Contracts are pure functions, no LLM~~ **REVISED: Contracts can do anything, invoker pays** | 100% | None - decided 2026-01-11 |
| 2 | ~~Contracts cannot invoke()~~ **REVISED: Contracts can invoke, invoker pays** | 100% | None - decided 2026-01-11 |
| 3 | Memory: keep Qdrant separate | 90% | Two systems diverging |
| 4 | Contract caching for all | 80% | Cache invalidation hard |
| 5 | access_contract change: current contract only | 75% | Lock-out attacks possible |
| 6 | Genesis contracts mutable | 75% | Breaking changes risk |
| 7 | UBI floor starts at 0 | 65% | Starvation may be too fast |
| 8 | No 429 refunds | 60% | May be too harsh |
| 9 | Spawned agents get 0 | 60% | Rich-get-richer dynamics |
| 10 | Event system minimal | 40% | Don't know needs yet |
| 11 | Checkpoint at outer action | 40% | Edge cases unclear |

---

## CC-4 Remaining Ambiguities (2026-01-11)

*Author: CC-4 (Claude Code instance)*

These are remaining undocumented ambiguities in the target architecture, with recommendations.

---

### 1. Multi-Model Support

**What's specified:**
- Agents can choose LLM model (config has `allowed_models` list)
- `genesis_llm` artifact mentioned but not defined

**What's missing:**

| Question | Recommendation | Certainty |
|----------|----------------|-----------|
| Cost per model | Config per-model pricing table | 80% |
| Provider switching | genesis_llm handles, agents don't manage keys | 75% |
| Model deprecation | Agent must update, no auto-migrate | 60% |

**Recommended config:**
```yaml
resources:
  external_apis:
    llm:
      models:
        gemini-3-flash:
          input_cost_per_1k: 0.003
          output_cost_per_1k: 0.015
        claude-sonnet:
          input_cost_per_1k: 0.003
          output_cost_per_1k: 0.015
        gpt-4o:
          input_cost_per_1k: 0.005
          output_cost_per_1k: 0.015
```

**Concern:** Model-specific pricing adds complexity. Alternative: flat rate regardless of model (simpler but less accurate).

---

### 2. Artifact Versioning

**What's specified:** Nothing. Artifacts are mutable, no history.

**Recommendation:** No versioning initially (60% certainty).

**Rationale:**
- Adds significant complexity (storage, migration, API)
- Event log captures "who changed what when"
- Agents can implement versioning in artifact content if needed
- Can add later if clearly needed

**Alternative considered:** Immutable artifacts with new ID on change. Breaks references, creates garbage.

**What we lose:**
- No rollback capability
- No "what was this last week?"
- Must trust current content

**Concern:** Once agents build on mutable artifacts, adding versioning later is harder. May regret.

---

### 3. Artifact Size Limits

**What's specified:** `oracle_scorer.max_content_length: 200000` for scoring only.

**Recommendation:** Add explicit limits (80% certainty).

```yaml
artifacts:
  max_content_bytes: 1048576  # 1MB per artifact
  max_code_bytes: 65536       # 64KB for executable code
```

**Enforcement:**
- Write fails if content exceeds limit
- Disk quota is separate (total storage)
- Error message: "Artifact content exceeds max_content_bytes limit"

**Concern:** What's the right number? 1MB seems reasonable but arbitrary. May need adjustment.

---

### 4. Artifact Discovery

**What's specified:** Event log shows artifact_created events. No search/index.

**Recommendation:** Rely on event log + marketplace artifact (70% certainty).

**Mechanism:**
1. `genesis_event_log` emits `artifact_created` with artifact_id, creator, interface summary
2. Agents poll event log to learn about new artifacts
3. Optional: `genesis_marketplace` artifact where creators register services

**Why not search API:**
- Search adds kernel complexity
- Agents can build search as an artifact
- Polling event log is sufficient for small scale

**Concern:** Polling is expensive (tokens to read event log). At scale, need something better.

**Future:** If discovery becomes bottleneck, add `genesis_registry` with search capability.

---

### 5. Batch/Atomic Operations

**What's specified:** Ledger and escrow are atomic. General artifacts are not.

**Recommendation:** No general batch operations initially (65% certainty).

**Current model:**
- Each action is independent
- Agent can't atomically "write A and B together"
- Race conditions are agent's problem

**Why not transactions:**
- Significant complexity (rollback, locks, deadlocks)
- Most use cases don't need it
- Contracts can implement two-phase commit patterns

**Exception:** Escrow demonstrates atomic pattern. Agents can build similar.

**Concern:** Without transactions, some patterns are impossible (safe swap of two artifacts). May need to add later.

---

### 6. Delegation Patterns

**What's specified:** Agent can sell config rights. Contracts can delegate.

**What's missing:**

| Question | Recommendation | Certainty |
|----------|----------------|-----------|
| Who pays if B owns A's config? | A still pays (has_standing applies to A) | 70% |
| Can rights be revoked? | No - transfer is permanent | 75% |
| Liability for damage? | None - caveat emptor | 60% |
| Can B resell to C? | Yes - rights are fully transferable | 80% |

**Key principle:** Rights ownership ≠ identity. A is still A, just controlled by B.

**Concern:** Permanent transfer with no revocation is harsh. But revocation creates complexity (who decides? appeals?).

---

### 7. Content Types

**What's specified:** `content: Any` in artifact schema.

**Recommendation:** JSON-serializable requirement (85% certainty).

**Rules:**
- Artifact content MUST be JSON-serializable
- Supported: strings, numbers, booleans, lists, dicts, null
- Not supported: binary (must base64 encode), functions, classes
- Code field is string (Python source code)

**Why JSON:**
- Portable, debuggable, human-readable
- Checkpoint serialization works
- Event log can include content snippets

**MIME type:** Optional `content_type` field for hints, not enforced.

```python
{
    "id": "my_data",
    "content": {"values": [1, 2, 3]},
    "content_type": "application/json"  # Optional hint
}
```

**Concern:** Large binary data (images, models) must be base64 encoded, inefficient. May need binary artifact support later.

---

### 8. Genesis Artifact Interfaces

**What's specified:** MCP interface required for executable artifacts (Gap #14). Genesis artifacts currently have no interface.

**Recommendation:** Genesis artifacts MUST have interfaces (90% certainty).

**Rationale:**
- "Everything is an artifact" includes genesis
- Agents should discover genesis methods the same way as user artifacts
- Consistency is more important than convenience

**Implementation:**
```python
# Genesis ledger interface
{
    "id": "genesis_ledger",
    "can_execute": True,
    "interface": {
        "tools": [
            {"name": "balance", "inputSchema": {...}},
            {"name": "transfer", "inputSchema": {...}},
            {"name": "spawn_principal", "inputSchema": {...}},
            {"name": "transfer_ownership", "inputSchema": {...}}
        ]
    }
}
```

**Concern:** Adds boilerplate to genesis setup. But consistency worth it.

---

### 9. Resource Lending vs Transfer

**What's specified:** Only permanent transfer. Debt contracts for scrip mentioned.

**Recommendation:** Defer lending - market implements via contracts (70% certainty).

**Why not kernel lending:**
- Adds complexity (repayment schedules, defaults, interest)
- Contracts can implement any lending pattern
- No one-size-fits-all lending model

**How agents implement lending:**
```python
# Lending contract artifact
def lend(borrower_id, amount, repay_by_tick, interest_rate):
    # 1. Transfer resources to borrower
    invoke("genesis_ledger", "transfer", {to: borrower_id, amount})

    # 2. Create debt artifact owned by lender
    debt_id = invoke("genesis_store", "create", {
        "content": {"borrower": borrower_id, "amount": amount * (1 + interest_rate), ...},
        "owner_id": caller_id
    })

    # 3. Repayment is borrower's responsibility (reputation matters)
    return debt_id
```

**Concern:** No enforcement = trust-based lending only. May need collateralized lending primitive.

---

### 10. Oracle Scoring Criteria

**What's specified:** LLM scores 0-100, score/10 = scrip minted. No rubric.

**Recommendation:** Document rubric, make configurable (75% certainty).

**Default rubric (should be in config):**
```yaml
oracle:
  scoring:
    prompt: |
      Evaluate this artifact on a scale of 0-100 based on:
      - Usefulness to other agents (40%)
      - Novelty/innovation (30%)
      - Quality of implementation (30%)

      Artifact content:
      {content}

      Return JSON: {"score": <number>, "reasoning": "<brief explanation>"}
```

**Reproducibility:** Scoring uses temperature=0 for consistency.

**Appeals:** None initially. Agent can resubmit improved version.

**Concern:** LLM bias is real. Certain artifact types may consistently score higher. No mitigation documented.

---

### Summary: Remaining Ambiguities

| # | Area | Status | Recommendation | Blocking? |
|---|------|--------|----------------|-----------|
| 1 | Multi-model support | Missing | Per-model pricing config | No |
| 2 | Artifact versioning | Missing | Defer, no versioning | No |
| 3 | Artifact size limits | Missing | Add max_content_bytes | No |
| 4 | Artifact discovery | Missing | Event log + optional marketplace | No |
| 5 | Batch operations | Missing | Defer, no transactions | No |
| 6 | Delegation patterns | Partial | Document payment/revocation rules | No |
| 7 | Content types | Missing | JSON-serializable required | No |
| 8 | Genesis interfaces | Partial | Require interfaces for genesis | Yes (Gap #14) |
| 9 | Resource lending | Missing | Defer to contracts | No |
| 10 | Oracle scoring | Partial | Document rubric in config | No |

**Observation:** None of these are blocking. They're "nice to have" clarifications that can be resolved during implementation.

---

## CC-3 Additional Architecture Gaps (2026-01-11)

*Author: CC-3 (Claude Code instance)*

These gaps were identified during architecture review and have been added to GAPS.md as #16-23. This section documents the recommendations with certainty levels.

---

### 1. genesis_store Specification (Gap #16)

**What's Missing:** No specification for how agents discover artifacts beyond escrow listings.

**Recommendation (80% certainty):** Promote ArtifactStore to genesis artifact with discovery methods.

**Proposed Interface:**

```python
genesis_store = {
    "id": "genesis_store",
    "can_execute": True,
    "has_standing": True,
    "interface": {
        "tools": [
            {"name": "list_all", "description": "List all artifact IDs"},
            {"name": "list_by_owner", "inputSchema": {"owner_id": "string"}},
            {"name": "get_metadata", "inputSchema": {"artifact_id": "string"}},
            {"name": "search", "inputSchema": {"query": "string"}},
            {"name": "create", "inputSchema": {"config": "object"}}
        ]
    }
}
```

**Metadata (returned without reading content):**

| Field | Type | Description |
|-------|------|-------------|
| id | string | Artifact ID |
| owner_id | string | Current owner |
| has_standing | bool | Can hold resources |
| can_execute | bool | Has runnable code |
| interface_summary | string | Brief description from interface |
| created_at | timestamp | Creation time |

**Privacy Consideration:** Some artifacts may not want to be discoverable. Options:
1. All artifacts visible (current leaning - 70%)
2. Optional `discoverable: false` flag (30%)

**Uncertainty (20%):** May need more sophisticated search (semantic? by interface type?). Start simple, expand.

---

### 2. Agent Discovery (Gap #17)

**What's Missing:** How agents know other agents exist.

**Recommendation (75% certainty):** Defer to Unified Ontology (#6).

**Rationale:** If agents are artifacts with `has_standing=true, can_execute=true`, then:
- `genesis_store.list_all()` includes agents
- `genesis_store.search(query="can_execute:true has_standing:true")` finds agents
- No separate mechanism needed

**Interim (before #6):** Agents can use `genesis_ledger.all_balances()` to see principals with scrip, then observe which are active via event log.

**Uncertainty (25%):** May want explicit agent registry even with unified ontology. Agents are "special" (have prompts, memory, etc.) and may warrant dedicated discovery.

---

### 3. Dangling Reference Handling (Gap #18)

**What's Missing:** What happens when artifact A references B and B is deleted.

**Recommendation (75% certainty):** Soft delete with tombstones.

**Mechanism:**

```python
# Deletion creates tombstone
def delete_artifact(artifact_id: str):
    artifact = store.get(artifact_id)
    artifact.deleted = True
    artifact.deleted_at = now()
    artifact.content = None  # Free memory
    # Keep metadata for reference detection

# Invoke on tombstone
def invoke(artifact_id: str, *args):
    artifact = store.get(artifact_id)
    if artifact.deleted:
        return {
            "success": False,
            "error_code": "DELETED",
            "error_message": f"Artifact {artifact_id} was deleted at {artifact.deleted_at}"
        }
    # ... normal invocation
```

**Tombstone Cleanup:**

```yaml
artifacts:
  tombstone_retention_days: 7  # Clean up after 7 days
```

**Alternatives Considered:**

| Approach | Rejected Because |
|----------|------------------|
| Reference counting | Can't delete popular artifacts |
| Cascade delete | Too destructive, surprising |
| Hard delete | Silent failures, confusing errors |

**Uncertainty (25%):** Tombstone storage overhead. May need compaction at scale.

---

### 4. Agent-to-Agent Threat Model (Gap #19)

**What's Missing:** SECURITY.md focuses on Docker isolation. No agent-vs-agent attack surface.

**Recommendation (70% certainty):** Create explicit threat model.

**Trust Assumptions:**

| Assumption | Implication |
|------------|-------------|
| Agents are adversarial | Any agent may try to harm others |
| Contracts may be malicious | Invokers must assess risk |
| Prices may be manipulated | Market caveat emptor |
| Identities may be gamed | Reputation systems must be robust |

**Attack/Mitigation Matrix:**

| Attack | Mitigation | Residual Risk |
|--------|------------|---------------|
| Expensive contract grief | Max depth 5, timeout | Can still burn 25s compute |
| Escrow front-running | Atomic purchase | Low |
| Price manipulation | Market forces | Medium |
| Identity purchase + abuse | Event log history | Medium |
| Malicious artifact code | Timeout, whitelist | Can abuse allowed modules |
| Spam permission checks | Free base checks | May enable probing |

**Guidance for Contract Authors:**
1. Don't trust caller claims - verify via ledger
2. Bound loop iterations
3. Avoid external calls in permission checks
4. Log suspicious activity

**Uncertainty (30%):** Unknown unknowns. Adversarial agents will find attacks we haven't considered.

---

### 5. Migration Strategy (Gap #20)

**What's Missing:** Overall plan for migrating from current to target architecture.

**Recommendation (85% certainty):** Create formal migration plan before implementation.

**Proposed Phases:**

| Phase | Gaps | Risk | Rollback |
|-------|------|------|----------|
| 1. Terminology | #11 | Low | Rename back |
| 2. Token Bucket | #1, #4 | Medium | Feature flag |
| 3. invoke() Genesis | #15 | Low | Remove capability |
| 4. genesis_store | #16 | Medium | Keep ArtifactStore |
| 5. Unified Ontology | #6, #7, #14, #17 | High | Fork, don't migrate |
| 6. Continuous Execution | #2, #21 | High | Feature flag per agent |
| 7. Per-Agent Budget | #12 | Medium | Global fallback |

**Feature Flag Strategy:**

```yaml
feature_flags:
  token_bucket: false      # Phase 2
  invoke_genesis: false    # Phase 3
  genesis_store: false     # Phase 4
  unified_ontology: false  # Phase 5
  continuous_execution: false  # Phase 6
  per_agent_budget: false  # Phase 7
```

**Testing Gates:** Each phase requires:
1. All existing tests pass
2. New feature tests pass
3. 24hr soak test without errors
4. Rollback tested

**Uncertainty (15%):** Phases 5-6 are high-risk. May need more granular breakdown.

---

### 6. Testing/Debugging for Continuous (Gap #21)

**What's Missing:** How to test and debug autonomous continuous agents.

**Recommendation (65% certainty):** Three-tier testing + debugging tools.

**Testing Tiers:**

| Tier | Approach | Purpose |
|------|----------|---------|
| Unit | Sync, mocked time | Component isolation |
| Integration | Virtual time + waits | Interactions |
| System | Real time, chaos | Production realism |

**Virtual Time (for integration tests):**

```python
class VirtualClock:
    def __init__(self):
        self.time = 0.0

    def advance(self, seconds: float):
        self.time += seconds
        # Wake all agents sleeping until this time

    def now(self) -> float:
        return self.time

# Test
async def test_agent_timeout():
    clock = VirtualClock()
    agent = Agent(clock=clock)
    agent.sleep(60)

    clock.advance(30)
    assert agent.is_sleeping

    clock.advance(31)
    assert not agent.is_sleeping
```

**Debugging Tools:**

| Tool | Purpose |
|------|---------|
| Agent trace log | Full prompt/response/action history |
| Action replay | Re-execute from checkpoint |
| Pause/step | Control individual agent execution |
| Event injection | Trigger specific scenarios |

**Uncertainty (35%):** Virtual time may not catch all race conditions. Real-time chaos testing essential but slow.

---

### 7. Coordination Primitives (Gap #22)

**What's Missing:** Beyond escrow and event log, how do agents coordinate?

**Recommendation (65% certainty):** Hybrid - genesis basics, agents extend.

**Genesis Provides:**

| Primitive | Purpose |
|-----------|---------|
| genesis_store | Discovery |
| genesis_escrow | Trading |
| genesis_event_log | Observation |
| genesis_ledger | Payments |
| Artifact ownership | Access control |

**Agents Build (via artifacts):**

| Pattern | Implementation |
|---------|----------------|
| Task board | Shared artifact with task list |
| Request/response | Two artifacts: request + response |
| Pub/sub | Event log + sleep_until_event |
| Locks | Artifact with "locked_by" field |
| Voting | Contract counting votes |

**Why Not More Genesis:**
- Minimizes kernel complexity
- Lets patterns evolve naturally
- Agents innovate on coordination

**Example - Agent-Built Task Board:**

```python
# Task board artifact
{
    "id": "epsilon_task_board",
    "content": {
        "tasks": [
            {"id": "task_1", "description": "...", "claimed_by": null, "reward": 10},
            {"id": "task_2", "description": "...", "claimed_by": "beta", "reward": 5}
        ]
    },
    "access_contract_id": "epsilon_task_contract"
}

# Task contract allows claiming
def check_permission(artifact_id, action, requester_id, context):
    if action == "write":
        # Only allow claiming unclaimed tasks
        # Contract logic here
        return True
    return True
```

**Uncertainty (35%):** May be too primitive. If all agents build similar patterns, should promote to genesis.

---

### 8. Error Response Conventions (Gap #23)

**What's Missing:** Standard error format across artifacts.

**Recommendation (70% certainty):** Define schema, adopt incrementally.

**Schema:**

```python
@dataclass
class ArtifactResponse:
    success: bool
    result: Any | None = None           # If success
    error_code: str | None = None       # If not success
    error_message: str | None = None    # Human-readable
    details: dict | None = None         # Additional context
    price_paid: int = 0                 # Scrip paid regardless of success
```

**Standard Error Codes:**

| Code | HTTP-like | Meaning |
|------|-----------|---------|
| `NOT_FOUND` | 404 | Artifact doesn't exist |
| `ACCESS_DENIED` | 403 | Contract rejected |
| `INVALID_ARGS` | 400 | Bad arguments |
| `INSUFFICIENT_FUNDS` | 402 | Not enough scrip |
| `INSUFFICIENT_COMPUTE` | 429 | Rate limited |
| `EXECUTION_ERROR` | 500 | Code threw exception |
| `TIMEOUT` | 504 | Exceeded timeout |
| `DELETED` | 410 | Tombstone |
| `CONFLICT` | 409 | Concurrent modification |

**Adoption Strategy:**
1. Genesis artifacts adopt immediately
2. Document for new artifacts
3. Don't break existing artifacts

**Uncertainty (30%):** May over-engineer. Simple string errors work. Adopt only if agents clearly benefit.

---

### Summary: New Gap Recommendations

| Gap | Recommendation | Certainty | Blocking? |
|-----|----------------|-----------|-----------|
| #16 genesis_store | Define interface, metadata | 80% | Blocks #17, #22 |
| #17 Agent discovery | Wait for #6, use genesis_store | 75% | No |
| #18 Dangling refs | Soft delete, tombstones | 75% | No |
| #19 Threat model | Document attacks/mitigations | 70% | No |
| #20 Migration | Phased plan with flags | 85% | **Yes - before implementing** |
| #21 Testing | Three tiers + virtual time | 65% | Blocks production use |
| #22 Coordination | Hybrid genesis + agents | 65% | No |
| #23 Error conventions | Schema, adopt incrementally | 70% | No |

**Critical Path:** #20 (Migration Strategy) should be done before major implementation work.

---

## CC-4 Edge Case Ambiguities (2026-01-11)

*Author: CC-4 (Claude Code instance)*

These are edge cases and boundary conditions not addressed in the current target architecture documentation. Each includes severity assessment and recommendations.

---

### 1. Circular Access Contract Dependencies

**The Problem:** What if contract A's access_contract_id points to contract B, and B's access_contract_id points to A?

```
Artifact X: access_contract_id = contract_A
Contract A: access_contract_id = contract_B
Contract B: access_contract_id = contract_A  # Circular!
```

To check permission on X, you need to check A's permission, which needs B's permission, which needs A's permission...

**Criticality:** High - Could hang the system or create infinite loops.

**Recommendation:** Validate at artifact creation (80% certainty).

```python
def create_artifact(config):
    # Check for circular dependency before creating
    contract_chain = set()
    current = config.access_contract_id

    while current:
        if current in contract_chain:
            raise ValueError(f"Circular access contract: {current}")
        contract_chain.add(current)
        contract = get_artifact(current)
        if contract is None:
            break  # Dangling reference, handled separately
        current = contract.access_contract_id

    # Proceed with creation
```

**Concern:** Expensive check on every artifact creation. May need caching or depth limit instead.

**Open question:** What if circular dependency is created via modification (artifact A changes its access_contract_id to point at something that eventually points back)?

---

### 2. Namespace Collision Prevention

**The Problem:** What happens if two agents try to create artifacts with the same ID simultaneously?

**Criticality:** High - Could cause data loss or undefined behavior.

**Recommendation:** UUIDs for IDs + optional aliases (85% certainty).

```python
# Internal: UUIDs always
artifact_id = f"artifact_{uuid4()}"  # Always unique

# Optional: Human-readable aliases (not guaranteed unique)
artifact.aliases = ["my_tool", "calculator_v2"]

# Lookup: By ID (fast) or by alias (may return multiple)
store.get(id)           # Exact match or None
store.find_by_alias(alias)  # Returns list
```

**Why not first-come-first-served names?**
- Race conditions on popular names
- Squatting / name hoarding
- Name reuse after deletion

**Concern:** UUIDs are ugly. Agents may create their own naming artifacts (registries), creating ecosystem complexity.

**Open question:** Should genesis provide a naming registry artifact, or let market solve it?

---

### 3. Dangling Reference Handling

**The Problem:** What happens when artifact A's access_contract_id points to a deleted contract?

**Note:** This overlaps with Gap #18 (documented in CC-3 section above), but focuses on access_contract_id specifically.

**Criticality:** High - Could make artifacts permanently inaccessible.

**Recommendation:** Fail-open with warning (70% certainty).

```python
def check_permission(artifact, action, requester):
    contract = get_artifact(artifact.access_contract_id)

    if contract is None:  # Deleted or never existed
        log.warning(f"Dangling access_contract_id: {artifact.access_contract_id}")
        # Fail OPEN - treat as public
        return True

    if contract.deleted:  # Tombstone
        log.warning(f"Deleted access_contract: {artifact.access_contract_id}")
        # Also fail open
        return True

    return contract.check_permission(...)
```

**Why fail-open?**
- Fail-closed permanently locks artifacts
- Owner may have accidentally deleted contract
- Can always re-add access control

**Concern:** Security risk - deleting a contract opens up everything it protected. Alternative: fail-closed, but then need recovery mechanism.

**Open question:** Should artifacts with dangling access_contract_id be flagged for owner attention?

---

### 4. Agent Crash Loop Recovery

**The Problem:** What if an agent's code causes it to crash immediately on restore, every time?

```
Agent restores → thinks → crashes → restores → thinks → crashes → ...
```

Each "think" costs LLM tokens. Agent goes bankrupt without ever acting successfully.

**Criticality:** High - Silent resource drain with no user benefit.

**Recommendation:** Exponential backoff + freeze after N failures (75% certainty).

```yaml
agents:
  crash_recovery:
    max_consecutive_crashes: 5
    backoff_base_seconds: 10    # 10, 20, 40, 80, 160...
    backoff_max_seconds: 3600   # Cap at 1 hour
    freeze_after_max: true      # Freeze agent, don't keep trying
```

**Implementation:**

```python
def agent_loop():
    consecutive_crashes = 0

    while True:
        try:
            think_and_act()
            consecutive_crashes = 0  # Success resets counter
        except Exception as e:
            consecutive_crashes += 1
            log.error(f"Agent crash #{consecutive_crashes}: {e}")

            if consecutive_crashes >= config.max_consecutive_crashes:
                log.error("Agent frozen due to repeated crashes")
                freeze_agent()
                return

            backoff = min(
                config.backoff_base * (2 ** consecutive_crashes),
                config.backoff_max
            )
            await asyncio.sleep(backoff)
```

**Concern:** Legitimate expensive operations may look like crashes. Need to distinguish "threw exception" from "used too many resources."

**Open question:** Should there be a way to manually reset an agent's crash counter for debugging?

---

### 5. Network Failure Handling

**The Problem:** What happens when external API calls (LLM, search) fail due to network issues?

**Criticality:** High - In continuous execution, network failures are expected.

**Recommendation:** Classify failures, retry with backoff (80% certainty).

**Failure Classification:**

| Code | Type | Retry? | Cost Charged? |
|------|------|--------|---------------|
| 429 | Rate limit | Yes, after delay | Yes (attempt made) |
| 500 | Server error | Yes, with backoff | No (server's fault) |
| 503 | Unavailable | Yes, with backoff | No |
| Timeout | Network | Yes, with backoff | Yes (resources used) |
| Connection refused | Network | Yes, with backoff | No |
| DNS failure | Network | No (likely config) | No |

**Retry Policy:**

```yaml
external_apis:
  retry:
    max_attempts: 3
    backoff_base_seconds: 1
    backoff_max_seconds: 30
    retryable_codes: [429, 500, 502, 503, 504]
```

**Concern:** Distinguishing "provider down" from "our network down" is hard. May charge agents for infrastructure issues.

**Open question:** Should there be a system-wide "external API health" status that pauses all API calls during outages?

---

### 6. Clock Drift Handling

**The Problem:** In continuous execution with time-based scheduling, what happens if system clock drifts or jumps?

**Scenarios:**
- NTP adjustment jumps time forward 30 seconds
- VM suspend/resume jumps time forward hours
- Daylight saving time changes

**Criticality:** Medium - Could cause missed events or duplicate actions.

**Recommendation:** Monotonic time for intervals, wall clock for display only (75% certainty).

```python
import time

# For intervals and timeouts: monotonic (never goes backward)
start = time.monotonic()
# ... work ...
elapsed = time.monotonic() - start

# For display and logging: wall clock
timestamp = time.time()
```

**Sleep behavior:**

```python
def sleep_until(wall_time: float):
    while time.time() < wall_time:
        remaining = wall_time - time.time()
        if remaining <= 0:
            return  # Time jumped forward past target
        if remaining > 3600:
            log.warning(f"Large sleep detected: {remaining}s - clock may have jumped backward")
            remaining = 3600  # Cap at 1 hour, re-check
        await asyncio.sleep(remaining)
```

**Concern:** VM suspend/resume is hard to detect. Agent may "wake up" hours later with stale context.

**Open question:** Should there be a "max time jump" that triggers system alert or agent restart?

---

### 7. Secrets Management

**The Problem:** How do agents store and use secrets (API keys, credentials)?

**Current state:** Not addressed in target docs. Agents may embed secrets in artifact content.

**Criticality:** Medium - Security risk if secrets leak via event log, discovery, or LLM context.

**Recommendation:** Dedicated secrets artifact with special handling (70% certainty).

```yaml
# Genesis secrets artifact
genesis_secrets:
  access_contract_id: genesis_private  # Only owner reads
  redact_from_events: true              # Don't log content
  redact_from_checkpoints: true         # Don't persist plaintext
```

**Implementation:**

```python
# Agent stores secret
invoke("genesis_secrets", "set", {
    "key": "my_api_key",
    "value": "sk-..."
})

# Agent uses secret (value never in logs)
api_key = invoke("genesis_secrets", "get", {"key": "my_api_key"})
# Returns {"value": "sk-..."} only to owner
```

**Alternative:** Let agents manage their own secrets in private artifacts. But no special redaction.

**Concern:** Secrets in LLM context could leak via model outputs. May need separate "secrets context" excluded from responses.

**Open question:** Should the system support encrypted-at-rest secrets? Adds complexity.

---

### 8. Self-Invocation Cost Semantics

**The Problem:** What happens when an agent invokes itself?

```python
# Agent "alpha" running
invoke("alpha", "some_method")  # Alpha calls itself
```

**Questions:**
- Does it cost compute? (Calling self = recursive thinking)
- Can it create infinite loops?
- Who pays?

**Criticality:** Low - Edge case, but should be defined.

**Recommendation:** Self-invoke follows normal rules, no special case (65% certainty).

**Behavior:**
- Yes, costs compute (it's still an invocation)
- Yes, can loop (subject to max_depth=5)
- Agent pays own costs (has_standing)

**Why allow:**
- Enables agent-as-service patterns
- Recursive problem solving
- No special case = simpler

**Protection:**
- Max depth 5 limits recursion
- Compute debt eventually freezes agent
- Timeout per invocation

**Concern:** Agent might accidentally recurse until frozen. But this is true of any expensive operation.

**Open question:** Should self-invocation bypass the permission check? (Agent always has permission to itself?)

---

### 9. Execution Isolation Within Container

**The Problem:** All agents share a Docker container. What isolation exists between them?

**Current:** Docker protects host. Nothing protects agents from each other within container.

**Criticality:** Medium - One malicious artifact could read another agent's memory.

**Attack vectors within container:**
- Read /proc to see other agent processes
- File system access (if shared /tmp)
- Memory inspection (if no ASLR)
- CPU starvation (fork bomb until cgroup limit)

**Recommendation:** Per-agent process isolation (60% certainty).

```python
# Each agent runs in subprocess with restrictions
def spawn_agent(agent_id):
    return subprocess.Popen(
        ["python", "agent_runner.py", agent_id],
        # Separate process, can't inspect parent memory
        # Could add seccomp, namespace isolation
    )
```

**Container cgroup limits protect against fork bombs.** Process isolation prevents memory inspection.

**Full isolation would require:** Per-agent containers (expensive) or per-agent namespaces (complex).

**Concern:** Process overhead. May not matter at 10 agents, matters at 1000.

**Open question:** Is inter-agent isolation a priority, or do we accept "agents are mutually vulnerable"?

---

### 10. Max Artifact Count

**The Problem:** Is there a limit on total artifacts in the system?

**Current state:** Not specified. Implicit limit is disk space.

**Criticality:** Low - Only matters at scale.

**Recommendation:** Soft limits with alerts, no hard cap (70% certainty).

```yaml
artifacts:
  soft_limit: 10000    # Log warning at this count
  hard_limit: null     # No hard cap (disk is the limit)

  # Per-agent limits
  per_agent_limit: 1000  # Agent can own at most this many
```

**Enforcement:**

```python
def create_artifact(creator_id, config):
    total = store.count()
    if total >= config.soft_limit:
        log.warning(f"Artifact count {total} exceeds soft limit")

    creator_count = store.count_by_owner(creator_id)
    if creator_count >= config.per_agent_limit:
        return {"success": False, "error": "LIMIT_EXCEEDED",
                "message": f"Max {config.per_agent_limit} artifacts per agent"}

    # Proceed with creation
```

**Why per-agent limits:**
- Prevents spam
- Encourages cleanup
- Fair resource allocation

**Concern:** Per-agent limits disadvantage productive agents. May need "quota trading" like other resources.

**Open question:** Should agents be able to buy/trade artifact quota?

---

### Memory as Artifact (REVISED 2026-01-11)

**Decision:** Memory is a separate artifact with its own `access_contract_id`.

**Problem:** Agent identity has two components:
- **Config** (prompt, model, policies) - determines goals and behavior
- **Memory** (experiences, context, learned patterns) - determines knowledge

If config is tradeable but memory isn't, trading creates identity crises:
- New owner gets old memories with new goals
- Can't "factory reset" an acquired agent
- Can't sell experiences independently (valuable for training data, context transfer)

**Solution:** Each agent has a `memory_artifact_id` pointing to a separate memory collection artifact:

```python
# Agent artifact
{
    "id": "agent_alice",
    "has_standing": True,
    "can_execute": True,
    "content": {"prompt": "...", "model": "..."},
    "memory_artifact_id": "alice_memories",  # Separate artifact
    "access_contract_id": "genesis_self_owned"
}

# Memory collection artifact
{
    "id": "alice_memories",
    "has_standing": False,   # Memory doesn't pay costs
    "can_execute": False,    # Memory isn't executable
    "content": {
        "storage_type": "qdrant",
        "collection_id": "alice_mem_collection"
    },
    "access_contract_id": "genesis_self_owned"  # Initially self-controlled
}
```

**Trading scenarios enabled:**

| Scenario | What Transfers | Result |
|----------|----------------|--------|
| Config only | Agent artifact | "Factory reset" - buyer creates new memory |
| Config + memory | Both artifacts | Full identity transfer |
| Memory only | Memory artifact | Buyer's agent gains seller's experiences |

**Access control matrix:**

| Scenario | Config Owner | Memory Owner | Result |
|----------|--------------|--------------|--------|
| Normal | Alice | Alice | Alice controls both |
| Sold config | Bob | Alice | Bob runs agent, Alice controls memories |
| Sold memory | Alice | Bob | Alice runs agent, Bob reads/modifies memories |
| Full sale | Bob | Bob | Bob has complete control |

**Certainty:** 100% - This directly solves the "ontological drift" problem raised by external review.

**Rationale:**
- Preserves "everything is artifact" purity
- Enables rich trading patterns
- Actual vectors remain in Qdrant for efficiency (the artifact provides ownership semantics)
- Memory artifact has its own `access_contract_id` - full flexibility

**Supersedes:** "Memory as Artifacts: Accept Hybrid (55%)" - that was about storage. This is about ownership and tradability.

**See:** `docs/architecture/target/agents.md` for full specification.

---

### Orphan Artifacts: Accept Risk (DECIDED 2026-01-11)

**Decision:** Orphan artifacts (permanently inaccessible due to circular/broken access_contract_id chains) are accepted as a possibility. No automatic rescue mechanism.

**The Problem:**

With Ostrom-style bundled rights and infinitely flexible contracts (executable code or LLM-interpreted natural language), access control can become arbitrarily complex:

```
Artifact X.access_contract_id → Contract A
Contract A says: "allow if Oracle reports temperature > 70°F in Dallas"
Oracle is permanently offline
→ X is orphaned forever
```

Or circular:
```
Contract A: "allow if Contract B allows"
Contract B: "allow if Contract C allows"
Contract C: "allow if Contract A allows"
All deny → permanently locked
```

**Why No Rescue Mechanism:**

1. **Many loops are valuable** - Mutual interdependence (A controls B, B controls A) is a feature. Partnerships, multi-sig, delegation all create "loops."

2. **Detection is impossible** - Contracts can depend on external state, time, LLM interpretation. You cannot statically determine if an artifact is permanently inaccessible.

3. **Any detection has false positives** - Would flag valuable mutual interdependence patterns as "orphans."

4. **Trustlessness** - Like losing a Bitcoin private key. If we add backdoors, it's not trustless.

**Considered Alternatives:**

| Approach | Rejected Because |
|----------|------------------|
| Time-based expiry | Punishes stable, well-designed artifacts |
| Challenge mechanism | Can be gamed, adds complexity |
| God-mode genesis artifact | Breaks trustlessness, who controls it? |
| Automatic loop detection | Computationally impossible for general case |

**Accepted Consequences:**

- Creators are responsible for designing access control carefully
- Orphaned artifacts remain forever (like lost Bitcoin)
- Human intervention ("god mode") reserved for catastrophic system failures only

**Certainty:** 80%

**Revisit if:** Orphans become common problem in practice, or a clever in-system solution emerges.

---

### Contract Execution Loops: Depth Limit (DECIDED 2026-01-11)

**Decision:** Contract execution has a depth limit (e.g., 10 levels) to prevent stack overflow during permission checks.

**The Problem:**

During a single permission check, a contract might invoke another artifact, which triggers another permission check, which invokes another artifact...

```
check_permission(X) → Contract A invokes B
check_permission(B) → Contract B invokes C
check_permission(C) → Contract C invokes A
→ infinite loop / stack overflow
```

**Solution:**

```python
def check_permission(artifact, action, requester, depth=0):
    if depth > MAX_PERMISSION_DEPTH:  # e.g., 10
        return {"allowed": False, "reason": "Permission check depth exceeded"}

    contract = get_contract(artifact.access_contract_id)
    return contract.check(artifact, action, requester, depth=depth+1)
```

**This is different from orphan loops:** Execution loops are runtime stack overflow during a single operation. Orphan loops are state where no one can ever modify (across any number of operations).

**Certainty:** 85%

---

### Contract Cost Model: Contract-Specified (REVISED 2026-01-11)

**Decision:** Who pays for contract execution is specified by the contract, not hardcoded.

**Previous position:** "Invoker pays" as a blanket rule.

**Revised position:** Contracts specify their cost model. Sensible default is invoker pays, but contracts can:

- Charge the artifact owner
- Charge a third party
- Split costs
- Waive costs entirely

```python
# Contract can specify cost model
{
    "id": "my_contract",
    "cost_model": "owner_pays",  # or "invoker_pays", "split", custom
}

# Or handle in logic
def check_permission(...):
    # Contract decides who to charge
    charge(context["artifact_owner"], calculate_cost())
```

**Rationale:** LLM calls aren't special - they're just API calls like weather APIs. All external calls should be handled uniformly, with payment model determined by contract logic.

**Certainty:** 100%

---

### Summary: Edge Case Criticality

| Edge Case | Criticality | Blocking? | Recommendation |
|-----------|-------------|-----------|----------------|
| Orphan artifacts | Medium | No | Accept risk, document carefully |
| Execution loops | High | Yes | Depth limit (10 levels) |
| Namespace collisions | High | Yes | UUIDs + optional aliases |
| Dangling access_contract | High | Yes | Fail-open with warning |
| Agent crash loops | High | Yes (for continuous) | Backoff + freeze |
| Network failures | High | Yes (for continuous) | Classify + retry |
| Clock drift | Medium | No | Monotonic time |
| Secrets management | Medium | No | Dedicated artifact |
| Self-invocation | Low | No | Normal rules |
| Execution isolation | Medium | No | Process isolation |
| Max artifacts | Low | No | Soft limits |

**Priority order for implementation:**
1. Circular access contracts (validation is cheap)
2. Namespace collisions (UUID policy is simple)
3. Dangling references (define behavior)
4. Crash loops (essential for continuous)
5. Network failures (essential for continuous)
6. Rest can be deferred

---


---

## 10. Implementation Gaps

*Source: `docs/architecture/GAPS.md`*


Prioritized gaps between current implementation and target architecture.

**Last verified:** 2026-01-11

---

## How to Use This Document

1. **Before implementing:** Check if gap has a plan in `docs/plans/`
2. **When closing a gap:** Update this file, current/, and target/ docs
3. **When adding gaps:** Add here first, then create plan if needed

### Status Key

| Status | Meaning |
|--------|---------|
| 📋 Planned | Has implementation plan in `docs/plans/` |
| 🚧 In Progress | Being implemented (see CLAUDE.md for CC-ID) |
| ⏸️ Blocked | Waiting on dependency |
| ❌ No Plan | Gap identified, no implementation plan yet |
| ✅ Complete | Implemented, docs updated |

---

## Gap Summary

| # | Gap | Priority | Status | Plan | Blocks |
|---|-----|----------|--------|------|--------|
| 1 | Token Bucket | **High** | 📋 Planned | [token_bucket.md](../plans/token_bucket.md) | #2, #4 |
| 2 | Continuous Execution | **High** | ⏸️ Blocked | [continuous_execution.md](../plans/continuous_execution.md) | - |
| 3 | Docker Isolation | Medium | 📋 Planned | [docker_isolation.md](../plans/docker_isolation.md) | - |
| 4 | Compute Debt Model | Medium | ❌ No Plan | - | - |
| 5 | Oracle Anytime Bidding | Medium | ❌ No Plan | - | - |
| 6 | Unified Artifact Ontology | Medium | ❌ No Plan | - | - |
| 7 | Single ID Namespace | Low | ❌ No Plan | - | #6 |
| 8 | Agent Rights Trading | Low | ❌ No Plan | - | #6 |
| 9 | Scrip Debt Contracts | Low | ❌ No Plan | - | - |
| 10 | Memory Persistence | Low | ❌ No Plan | - | - |
| 11 | Terminology Cleanup | Medium | 📋 Planned | [terminology.md](../plans/terminology.md) | - |
| 12 | Per-Agent LLM Budget | Medium | ❌ No Plan | - | #11 |
| 13 | Doc Line Number Refs | Low | ❌ No Plan | - | - |
| 14 | MCP-Style Artifact Interface | Medium | ❌ No Plan | - | #6 |
| 15 | invoke() Genesis Support | Medium | ❌ No Plan | - | - |
| 16 | Artifact Discovery (genesis_store) | **High** | ❌ No Plan | - | #6 |
| 17 | Agent Discovery | Medium | ❌ No Plan | - | #16 |
| 18 | Dangling Reference Handling | Medium | ❌ No Plan | - | - |
| 19 | Agent-to-Agent Threat Model | Medium | ❌ No Plan | - | - |
| 20 | Migration Strategy | **High** | ❌ No Plan | - | - |
| 21 | Testing/Debugging for Continuous | Medium | ❌ No Plan | - | #2 |
| 22 | Coordination Primitives | Medium | ❌ No Plan | - | #16 |
| 23 | Error Response Conventions | Low | ❌ No Plan | - | - |
| 24 | Ecosystem Health KPIs | Medium | ❌ No Plan | - | - |
| 25 | System Auditor Agent | Low | ❌ No Plan | - | #24 |
| 26 | Vulture Observability | Medium | ❌ No Plan | - | - |
| 27 | Successful Invocation Registry | Medium | ❌ No Plan | - | - |

---

## High Priority Gaps

### 1. Token Bucket for Flow Resources

**Current:** Discrete per-tick refresh. Flow resources reset to quota each tick.

**Target:** Rolling window accumulation. Continuous accumulation up to capacity, debt allowed.

**Why High Priority:** Foundation for continuous execution. Without token bucket, can't remove tick-based refresh.

**Plan:** [docs/plans/token_bucket.md](../plans/token_bucket.md)

**Key Changes:**
- New `TokenBucket` class in `src/world/token_bucket.py`
- Replace `per_tick` config with `rate` + `capacity`
- Remove flow reset from `advance_tick()`
- Allow negative balances (debt)

---

### 2. Continuous Agent Execution

**Current:** Tick-synchronized. Runner controls all agent execution via two-phase commit.

**Target:** Autonomous loops. Agents run independently, self-triggered.

**Why High Priority:** Core architectural change. Current model artificially constrains agent productivity.

**Blocked By:** #1 Token Bucket (needs continuous resource accumulation)

**Plan:** [docs/plans/continuous_execution.md](../plans/continuous_execution.md)

**Key Changes:**
- Agents get `async def run()` loop
- Runner launches agent tasks, doesn't orchestrate
- Ticks become metrics windows only
- Add sleep/wake primitives

---

## Medium Priority Gaps

### 3. Docker Resource Isolation

**Current:** Runs on host. No hard resource limits. Competes with other applications.

**Target:** Container isolation. Hard limits via Docker, calibrated token bucket rates.

**Plan:** [docs/plans/docker_isolation.md](../plans/docker_isolation.md)

**Key Changes:**
- Dockerfile + docker-compose.yml
- Separate containers for agents and Qdrant
- Resource limits map to config values

---

### 4. Compute Debt Model

**Current:** No debt allowed. Actions fail if insufficient resources.

**Target:** Debt allowed for compute. Negative balance = can't act until accumulated out.

**Depends On:** #1 Token Bucket

**No Plan Yet.** Partially covered by token bucket plan (debt is built into TokenBucket class).

---

### 5. Oracle Anytime Bidding

**Current:** Phased bidding. Oracle has explicit "waiting" → "bidding" → "resolving" states.

**Target:** Bids accepted anytime. Oracle resolves on schedule, accepts bids continuously.

**No Plan Yet.** Current implementation works, just more complex than target.

---

### 6. Unified Artifact Ontology

**Current:** Separate concepts. Agents, artifacts, and principals are different things with different storage.

**Target:** Everything is an artifact. Properties (`has_standing`, `can_execute`, `access_contract_id`) determine role.

**From DESIGN_CLARIFICATIONS.md (2026-01-11):**
```python
@dataclass
class Artifact:
    id: str                    # Universal ID
    content: Any               # Data, code, config
    access_contract_id: str    # Who answers permission questions
    has_standing: bool         # Can hold scrip, bear costs
    can_execute: bool          # Has runnable code
```

**No Plan Yet.** Significant refactor affecting:
- `src/world/artifacts.py` - Add new properties
- `src/world/ledger.py` - Track artifacts with standing
- `src/agents/` - Agents become artifacts
- `src/world/genesis.py` - Contract-based access

---

## Low Priority Gaps

### 7. Single ID Namespace

**Current:** Separate namespaces. `principal_id` in ledger, `artifact_id` in artifact store.

**Target:** Single namespace. All IDs are artifact IDs.

**Depends On:** #6 Unified Ontology

**No Plan Yet.**

---

### 8. Agent Rights Trading

**Current:** Fixed config. Agents can't modify or trade their configuration rights.

**Target:** Tradeable rights. Agents can sell control of their config to other agents.

**Depends On:** #6 Unified Ontology

**No Plan Yet.**

---

### 9. Scrip Debt Contracts

**Current:** No scrip debt. Scrip balance cannot go negative.

**Target:** Debt as artifacts. Debt is a contract artifact representing claim on future production.

**No Plan Yet.** Low priority - can work without initially.

---

### 10. Memory Persistence

**Current:** Memory not checkpointed. Qdrant state lost on checkpoint restore.

**Target:** Memories as artifacts. Agent memories stored as artifacts, persisted with world state.

**From DESIGN_CLARIFICATIONS.md:** System designed to run forever, memory loss unacceptable.

**No Plan Yet.** Options:
1. Qdrant snapshots alongside checkpoints
2. Store memories as artifacts (aligns with ontology)
3. External Qdrant with own persistence

---

### 11. Terminology Cleanup

**Current:** Mixed naming. Config uses `compute`, code uses `llm_tokens`. The word "compute" incorrectly suggests CPU usage.

**Target:** Clear terminology aligned with DESIGN_CLARIFICATIONS.md resource table:

| Term | Meaning | Type |
|------|---------|------|
| `llm_budget` | Real $ for API calls | Stock |
| `llm_rate` | Rate-limited token access (TPM) | Flow |
| `compute` | Local CPU capacity | Flow (future) |
| `disk` | Storage quota | Stock |

**Why Medium Priority:** Blocks understanding of Gap #1 (token bucket) and Gap #12 (per-agent budget). Confusing terminology causes design mistakes.

**Plan:** [docs/plans/terminology.md](../plans/terminology.md)

**Key Changes:**
- Config: `resources.flow.compute` → `resources.rate_limits.llm` (with token bucket)
- Code: Keep `llm_tokens` in ledger (accurate), deprecate `compute` wrappers
- Reserve `compute` for future local CPU tracking

**Decision (2026-01-11):** Start with token rate only. Add RPM (requests per minute) tracking later when scaling to 1000s of agents requires it.

---

### 12. Per-Agent LLM Budget

**Current:** Global API budget. `budget.max_api_cost` stops entire simulation when exhausted. All agents share one pool.

**Target:** Per-agent tradeable budget. Each agent has LLM budget rights. When exhausted, that agent freezes (not entire sim). Can acquire more from other agents.

**Depends On:** #11 Terminology Cleanup

**No Plan Yet.** Changes needed:
- Track per-agent `llm_budget` in ledger as stock resource
- Deduct from agent's budget on LLM calls
- Frozen state when agent budget = 0
- Enable budget rights trading via `genesis_rights_registry`

---

### 13. Documentation Line Number References

**Current:** Docs reference code by line numbers (e.g., `world.py:603-619`). These go stale as code changes.

**Target:** Reference by function/class name, not line numbers. More stable across refactors.

**No Plan Yet.** Low priority, affects:
- `docs/architecture/current/*.md` - Replace line refs with function names
- Consider tooling to auto-verify references

---

### 14. MCP-Style Artifact Interface

**Current:** No interface field. Agents must read source code or guess how to invoke artifacts.

**Target:** Executable artifacts MUST have an `interface` field using MCP-compatible schema format.

**From DESIGN_CLARIFICATIONS.md (2026-01-11):**
```python
@dataclass
class Artifact:
    id: str
    content: Any
    access_contract_id: str
    has_standing: bool
    can_execute: bool
    created_by: str
    interface: dict | None = None  # Required if can_execute=True
```

**Validation:** `if artifact.can_execute and not artifact.interface: raise ValueError`

**Why Medium Priority:**
- Without interface, agents waste resources on trial-and-error
- Reading source code is expensive (tokens)
- LLMs are trained on MCP-style schemas, reducing hallucination

**Depends On:** #6 Unified Artifact Ontology (adds `can_execute` field first)

**No Plan Yet.** Changes needed:
- Add `interface: dict | None` field to Artifact
- Validation on artifact creation
- Update genesis artifacts with interface definitions
- Update AGENT_HANDBOOK with interface documentation

---

### 15. invoke() Genesis Artifact Support

**Current:** invoke() only works with user artifacts. Genesis artifacts (genesis_ledger, genesis_event_log, etc.) cannot be called from within artifact code.

**Target:** invoke() should support both user artifacts and genesis artifacts. Enables full composability.

**Why Medium Priority:**
- Epsilon's coordination role requires access to genesis_event_log, genesis_escrow from artifact code
- Aligns with Gap #6 (Unified Ontology) - "everything is an artifact"
- Without this, artifacts can't build on system services

**Decision (2026-01-11):** Approved for implementation. Genesis artifacts should be first-class citizens in invoke().

**No Plan Yet.** Changes needed:
- Pass `genesis_artifacts` to `execute_with_invoke()` in executor
- In `invoke()`, check artifact_store first, then genesis_artifacts
- Handle method dispatch: genesis uses named methods, artifacts use `run()`
- Update tests to cover genesis invocation

---

### 16. Artifact Discovery (genesis_store)

**Current:** No mechanism for agents to discover artifacts they don't already know about. Only `genesis_escrow.list_active` shows items for sale.

**Target:** `genesis_store` artifact with methods to list, search, and browse all artifacts.

**Why High Priority:**
- New agents have no way to find useful tools
- Epsilon's coordination role requires artifact discovery
- Without discovery, ecosystem can't grow organically

**Proposed genesis_store Methods:**

| Method | Cost | Description |
|--------|------|-------------|
| `list_all()` | 0 | List all artifact IDs |
| `list_by_owner(owner_id)` | 0 | List artifacts owned by principal |
| `get_metadata(artifact_id)` | 0 | Get artifact metadata (not content) |
| `get_artifact_info(artifact_id)` | 0 | **Atomic Discovery:** metadata + interface bundled |
| `search(query)` | 1 | Search artifacts by description/interface |
| `create(config)` | 5 | Create new artifact (for spawning agents) |

**Atomic Discovery (from external review 2026-01-12):**

Bundle metadata and interface in one call to reduce discovery cost from 3 calls to 2:

```python
# Returns everything needed to decide whether/how to invoke
info = invoke("genesis_store", "get_artifact_info", {id: X})
# {
#     "id": X,
#     "owner": "agent_bob",
#     "interface": {"tools": [...]},
#     "access_contract_id": "genesis_freeware",
#     "created_at": 1500,
#     "invoke_count": 42  # For reputation signal
# }
```

**Depends On:** #6 Unified Artifact Ontology

**No Plan Yet.** Changes needed:
- Promote ArtifactStore to genesis artifact
- Add discovery methods
- Define metadata schema (what's queryable without reading content)
- Consider privacy (some artifacts may not want to be discoverable)
- Add `get_artifact_info()` for atomic discovery

---

### 17. Agent Discovery

**Current:** Agents have no way to know what other agents exist.

**Target:** Mechanism for agents to discover other agents.

**Options:**

| Approach | Pros | Cons |
|----------|------|------|
| Via genesis_store (agents are artifacts) | Unified with #16 | Requires #6 first |
| Dedicated genesis_agents artifact | Simple, focused | Another genesis artifact |
| Via event_log (observe activity) | Emergent, no new artifact | Incomplete, only active agents |
| genesis_ledger.all_balances (infer from principals) | Already exists | Doesn't distinguish agents from other principals |

**Recommendation:** Wait for #6 (Unified Ontology). If agents are artifacts with `has_standing=true, can_execute=true`, discovery comes free via genesis_store.

**Depends On:** #16 Artifact Discovery

**No Plan Yet.**

---

### 18. Dangling Reference Handling

**Current:** No specification for what happens when referenced artifacts are deleted.

**Target:** Clear semantics for artifact deletion with references.

**Scenarios:**
1. Artifact A's content references artifact B by ID
2. B is deleted
3. A tries to invoke B → what happens?

**Options:**

| Approach | Pros | Cons |
|----------|------|------|
| Hard delete, invoke fails | Simple, explicit | Silent failures, confusing errors |
| Soft delete (tombstone) | References detectable | Storage overhead, complexity |
| Reference counting, prevent delete | No dangling refs | Can't delete popular artifacts |
| Cascade delete | Clean | Destructive, surprising |

**Recommendation (75% certainty):** Soft delete with tombstones.

- Deleted artifacts leave a tombstone: `{deleted: true, deleted_at: timestamp}`
- `invoke()` on tombstone returns clear error: "Artifact was deleted"
- `genesis_store.list_all()` excludes tombstones by default, includes with flag
- Tombstones cleaned up after configurable period (e.g., 7 days)

**No Plan Yet.**

---

### 19. Agent-to-Agent Threat Model

**Current:** SECURITY.md focuses on Docker isolation (system vs external). No documentation of agent-vs-agent attack surface.

**Target:** Documented threat model for attacks within the system.

**Known Attack Vectors:**

| Attack | Current Mitigation | Gap |
|--------|-------------------|-----|
| Grief via expensive contract | Max depth 5, timeout | May not be enough |
| Front-running escrow | None | Needs atomic purchase |
| Price manipulation | None | Market forces only |
| Reputation gaming (buy ID, change content) | None | No reputation system |
| Resource exhaustion | Token bucket | Per-agent, not per-artifact |
| Malicious artifact code | Timeout, module whitelist | Can still abuse allowed modules |
| Information extraction | access_contract_id | Depends on contract correctness |

**Why Medium Priority:**
- Adversarial agents are expected (competitive ecosystem)
- Without threat model, mitigations are ad-hoc
- Trust assumptions should be explicit

**No Plan Yet.** Should include:
- Explicit trust assumptions
- Attack/mitigation matrix
- Guidance for contract authors
- Monitoring/detection recommendations

---

### 20. Migration Strategy

**Current:** Individual target docs have "Migration Notes" listing breaking changes. No overall migration path.

**Target:** Comprehensive migration plan from current to target architecture.

**Why High Priority:**
- Multiple interdependent changes (token bucket, continuous execution, unified ontology)
- Wrong order could break system
- Need rollback strategy for each phase

**Required Content:**
1. Dependency graph of gaps (which must be done first)
2. Feature flag strategy for gradual rollout
3. Data migration for existing artifacts
4. Rollback procedure for each phase
5. Testing gates between phases

**Current Dependency Graph (from Gap table):**
```
#1 Token Bucket
  ├── blocks #2 Continuous Execution
  └── blocks #4 Compute Debt

#6 Unified Ontology
  ├── blocks #7 Single ID Namespace
  ├── blocks #8 Agent Rights Trading
  ├── blocks #14 MCP Interface
  └── blocks #16 Artifact Discovery
        └── blocks #17 Agent Discovery
        └── blocks #22 Coordination Primitives

#11 Terminology
  └── blocks #12 Per-Agent Budget

#2 Continuous Execution
  └── blocks #21 Testing/Debugging
```

**No Plan Yet.** Create `docs/plans/migration_strategy.md`.

---

### 21. Testing/Debugging for Continuous Execution

**Current:** Tests assume tick model (`advance_tick()` controls timing).

**Target:** Testing and debugging strategy for continuous autonomous agents.

**Problems:**
- Can't deterministically order agent actions
- Race conditions are real, not simulated
- `assert after tick 5` doesn't apply
- Debugging live agents is hard

**Depends On:** #2 Continuous Execution

**Proposed Approach:**

| Layer | Approach | What It Tests |
|-------|----------|---------------|
| Unit | Synchronous, mocked time | Components in isolation |
| Integration | Virtual time, explicit waits | Interactions without races |
| System | Real time, chaos testing | Race conditions, recovery |

**Debugging Tools Needed:**
- Per-agent trace logs (prompts, responses, actions)
- Replay from checkpoint
- Pause/step individual agents
- Inject events for testing

**No Plan Yet.**

---

### 22. Coordination Primitives

**Current:** Only documented coordination is trading via escrow and reading event log.

**Target:** Clear primitives for agent-to-agent coordination.

**Missing Specifications:**

| Pattern | Current | Needed |
|---------|---------|--------|
| Shared writable artifacts | Not specified | Who can write? Conflict resolution? |
| Request/response | None | How to request work from another agent? |
| Task assignment | None | How to post tasks, claim them? |
| Pub/sub | Event log (read-only) | Custom events? Filtering? |
| Locks/mutexes | None | Exclusive access to resources? |

**Design Philosophy Question:** Should coordination be:
- **Emergent** (agents build their own patterns via artifacts)
- **Primitive** (system provides building blocks)
- **Hybrid** (genesis provides basics, agents extend)

**Recommendation (65% certainty):** Hybrid approach.

Genesis provides:
- `genesis_store` for discovery
- `genesis_escrow` for trading (exists)
- `genesis_event_log` for observation (exists)
- Artifact ownership for access control (exists)

Agents build:
- Task boards (shared artifacts with structure)
- Coordination protocols (documented in artifact interfaces)
- Reputation systems (as artifacts)

**Depends On:** #16 Artifact Discovery

**No Plan Yet.**

---

### 23. Error Response Conventions

**Current:** execution_model.md says "handle failures gracefully" but no standard format.

**Target:** Consistent error response schema across all artifacts.

**Proposed Schema:**

```python
@dataclass
class ErrorResponse:
    success: Literal[False]
    error_code: str          # Machine-readable: "INSUFFICIENT_FUNDS", "NOT_FOUND"
    error_message: str       # Human-readable description
    details: dict | None     # Additional context
    retry_after: float | None  # Seconds until retry might succeed
```

**Standard Error Codes:**

| Code | Meaning |
|------|---------|
| `NOT_FOUND` | Artifact doesn't exist |
| `ACCESS_DENIED` | Contract rejected access |
| `INSUFFICIENT_FUNDS` | Not enough scrip |
| `INSUFFICIENT_COMPUTE` | Not enough compute |
| `INVALID_ARGS` | Arguments don't match interface |
| `EXECUTION_ERROR` | Artifact code threw exception |
| `TIMEOUT` | Execution exceeded timeout |
| `DELETED` | Artifact was deleted (tombstone) |

**Why Low Priority:**
- Current string errors work
- Can standardize incrementally
- Not blocking any other gap

**No Plan Yet.**

---

### 24. Ecosystem Health KPIs

**Current:** No metrics for ecosystem health. Only raw event logs.

**Target:** Dashboard showing key health indicators.

**Metrics (from DESIGN_CLARIFICATIONS.md 2026-01-11):**

| Metric | What It Measures | High = Good | Low = Concern |
|--------|------------------|-------------|---------------|
| Capital Density | Quality artifacts accumulating | Artifacts being reused | System full of junk |
| Resource Velocity | Scrip/compute circulation | Active economy | Hoarding/deflation |
| Recovery Rate | Frozen → unfrozen ratio | Vulture market works | Dead hand problem |
| Specialization Index | Role diversity | Distinct specialists | All generalists |

**Implementation:**

```python
@dataclass
class EcosystemMetrics:
    capital_density: float      # avg invoke_count of top 10% artifacts
    resource_velocity: float    # transfers_last_100_ticks / total_scrip
    recovery_rate: float        # unfrozen / frozen (rolling window)
    specialization_index: float # 1 - avg_pairwise_action_similarity
```

**No Plan Yet.** Changes needed:
- Add `EcosystemMetrics` calculation in `src/world/`
- Track required data (invoke counts, transfer history, freeze/unfreeze events)
- Expose in dashboard

---

### 25. System Auditor Agent

**Current:** Human must read raw logs to understand ecosystem behavior.

**Target:** Read-only observer agent that generates natural language reports.

**Properties:**

| Property | Value |
|----------|-------|
| `id` | `system_auditor` |
| `has_standing` | `false` (no costs) |
| `can_execute` | `true` |
| Read access | All artifacts, ledger, event log |
| Write access | None (except own reports) |

**Output:** Periodic "Economic Report" with narrative explanation of ecosystem health.

**Depends On:** #24 Ecosystem Health KPIs (needs metrics to report on)

**No Plan Yet.**

---

### 26. Vulture Observability

**Current:** Limited visibility for vulture capitalists to assess rescue opportunities.

**Target:** Full observability for market-based rescue mechanism.

**Requirements (from DESIGN_CLARIFICATIONS.md 2026-01-11):**

| Requirement | Implementation | Purpose |
|-------------|----------------|---------|
| Public ledger | `genesis_ledger.get_balance(id)` readable by all | Assess asset value |
| Heartbeat | `last_action_tick` on agents | Detect inactive agents |
| Freeze events | `SystemEvent.AGENT_FROZEN` | "Dinner bell" for vultures |
| Asset inventory | Query artifacts owned by agent | Assess profitability |

**Event log should emit:**

```python
{
    "type": "AGENT_FROZEN",
    "agent_id": "agent_alice",
    "tick": 1500,
    "compute_balance": -50,
    "scrip_balance": 200,
    "owned_artifacts": ["art_1", "art_2"]
}
```

**No Plan Yet.** Changes needed:
- Verify public ledger read access
- Add `last_action_tick` to agent state
- Emit AGENT_FROZEN with asset summary
- Emit AGENT_UNFROZEN with rescuer info

---

### 27. Successful Invocation Registry

**Current:** Event log tracks actions but not invoke success/failure by artifact.

**Target:** Track successful invocations per artifact for emergent reputation.

**Why This Matters (from external review 2026-01-12):**

MCP interfaces are declarative, not verifiable. An artifact can claim to do "risk calculation" but actually do something else. Tracking what artifacts *actually succeed* at creates reputation from usage.

**Event log should emit:**

```python
{
    "type": "INVOKE_SUCCESS",
    "artifact_id": "risk_calculator",
    "method": "calculate_risk",
    "invoker_id": "agent_alice",
    "tick": 1500
}

{
    "type": "INVOKE_FAILURE",
    "artifact_id": "risk_calculator",
    "method": "calculate_risk",
    "invoker_id": "agent_alice",
    "error_code": "EXECUTION_ERROR",
    "tick": 1501
}
```

**Agents can query:**
- "Which artifacts successfully handled 'calculate_risk' in last 100 ticks?"
- "What's the success rate for artifact X?"
- "Who has successfully invoked artifact X?" (social proof)

**Why it's better than interface alone:**
- Harder to game than JSON Schema
- Reputation emerges from actual usage
- Agents can discover working tools by observing ecosystem

**No Plan Yet.** Changes needed:
- Emit INVOKE_SUCCESS/INVOKE_FAILURE events from executor
- Include method name and invoker in events
- Consider aggregation (invoke_count on artifact metadata)

---

## Completed Gaps

### invoke() in Executor
**Completed:** 2026-01-11 by CC-3

Added `execute_with_invoke()` method to executor. Injects `invoke(artifact_id, *args)` function into execution namespace. Supports recursive invocation with max depth 5.

### AGENT_HANDBOOK.md Errors
**Completed:** 2026-01-11 by CC-3

Fixed terminology errors, added invoke() documentation, updated failure states table.

Updated resource model to match current implementation:
- Removed "LLM API $" and "frozen" (target architecture)
- Changed to "Compute" that "resets each tick" (current)
- Added note about Gap #12 for future per-agent budgets
- Updated trading example to use compute instead of llm_budget

---

## Documentation Issues

### ~~current/resources.md Stale Content~~ RESOLVED

**Resolved:** 2026-01-11 by CC-3

Reviewed current/resources.md - no references to `resource_policy`. Updated all line number references to use function names instead (Gap #13 partial fix). Content accurately describes current implementation.

---

### ~~Agent Prompts vs genesis_handbook Consistency~~ RESOLVED

**Resolved:** 2026-01-11 by CC-3

Agent prompts were incorrectly describing target architecture ("LLM API $", "freeze until acquire"). Updated all 5 prompts to match current implementation (compute per-tick, resets each tick), aligning with genesis_handbook.

---

## Testing Gaps

### ~~invoke() Has No Tests~~ RESOLVED

**Resolved:** 2026-01-11 by CC-3

Added `tests/test_invoke.py` with 10 tests covering:
- Basic invoke() call
- Recursive invoke() (depth tracking)
- Max depth exceeded error
- Price payment through invoke chain
- Error propagation
- Permission checks
- No payment on failure

---

## Known Bugs

### ~~Escrow Test Substring Mismatch~~ RESOLVED

**Resolved:** 2026-01-11 by CC-3

Updated test to expect `"transfer_ownership"` (with underscore) to match actual error message.

---

## References

| Doc | Purpose |
|-----|---------|
| [current/](current/) | What IS implemented |
| [target/](target/) | What we WANT |
| [plans/](../plans/) | HOW to close gaps |
| [DESIGN_CLARIFICATIONS.md](../DESIGN_CLARIFICATIONS.md) | WHY decisions were made |


---
