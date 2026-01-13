# Agent Ecology

Mechanism design for emergent collective intelligence in LLM agents.

> **Note:** This README describes the **target architecture**. See [Current Architecture](docs/architecture/current/) for what exists today.

## What This Is

Agent Ecology is **mechanism design for emergent collective intelligence**—designing the rules and incentives so that self-interested LLM agents, operating under real resource constraints, produce collectively beneficial outcomes.

The goal is functional **collective capability**—both collective intelligence (coordination, signaling, information processing) and collective functionality (building durable artifacts that persist and compound over time). A system where the whole exceeds the sum of its parts.

It's not just about agents making good decisions together. It's about building a long-running system that develops both **capital structure** (artifacts that persist, build on each other, and enable increasingly sophisticated work) and **organizational structure** (firms, contracts, specialization patterns) to coordinate production and use of that capital.

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

### Decision Heuristics

When making architectural decisions, we apply these heuristics (in priority order):

1. **Emergence is the goal** - Everything else serves emergent capability. Ask "what does this incentivize?" not just "does this work?"
2. **Minimal kernel, maximum flexibility** - Kernel provides physics, not policy. When in doubt, don't add it to kernel.
3. **Align incentives** - Bad incentives = bad emergence. Consider what behaviors decisions incentivize.
4. **Pragmatism over purity** - If purity causes undue friction, consider less pure options.
5. **Avoid defaults; if unavoidable, make configurable** - Defaults can distort incentives.
6. **Genesis artifacts as middle ground** - When facing kernel-opinion vs agent-friction tradeoffs, consider genesis artifacts as services.
7. **Selection pressure over protection** - Provide tools, accept failure as selection.
8. **Observe, don't prevent** - Make behavior observable. Reputation emerges from observation.
9. **When in doubt, contract decides** - Prefer contract-specified over hardcoded.

See `CLAUDE.md` for detailed explanations of each heuristic.

## Resource Model

Three resource categories plus economic currency:

| Category | Behavior | Examples |
|----------|----------|----------|
| **Depletable** | Once spent, gone forever | LLM API budget ($) |
| **Allocatable** | Quota, reclaimable when freed | Disk (bytes), Memory (bytes) |
| **Renewable** | Rate-limited via rolling window | CPU (CPU-seconds), LLM rate (tokens/min) |

**Scrip** is the internal economic currency—a coordination signal, not a physical resource. An agent can be rich in scrip but starved of compute. Money coordinates; physics constrains.

**Key properties:**
- Renewable resources use rolling windows, not discrete resets
- No debt for renewable resources—agents wait for capacity
- All quotas are tradeable between agents
- Docker container limits ARE the real constraints

## How Agents Interact

Agents operate through three actions (the "narrow waist"):

| Action | What it does |
|--------|--------------|
| `read_artifact` | Read content from storage |
| `write_artifact` | Create or update stored content |
| `invoke_artifact` | Call a method on an artifact |

**All actions consume resources.** The system runs in Docker containers with real limits:

| Resource | Category | Grounding | Measurement |
|----------|----------|-----------|-------------|
| LLM budget | Depletable | Actual API spend ($) | Sum of API costs |
| Disk | Allocatable | Container storage limit | Bytes written |
| Memory | Allocatable | Container RAM limit | Peak allocation |
| CPU rate | Renewable | CPU-seconds per window | getrusage() in workers |
| LLM rate | Renewable | Tokens per minute | Rolling window tracker |
| Scrip | Currency | Internal economy | Ledger balance |

Physical resources map to real Docker/API constraints. When limits hit, they're actually hit. Scrip is the coordination signal layered on top.

## System Primitives vs Genesis Artifacts

Two layers with fundamentally different properties:

### System Primitives (the "Physics")

Hardcoded in Python/Docker. Agents cannot replace these—they define what's *possible*:

- **Execution engine** - Runs agent loops, handles async
- **Action primitives** - read, write, invoke
- **Rate tracker** - Enforces rolling window limits
- **Worker pool** - Measures CPU/memory per action
- **Docker container** - Hard resource ceilings

### Genesis Artifacts (the "Infrastructure")

Pre-seeded artifacts created at T=0. Agents could theoretically build alternatives—they define what's *convenient*:

| Artifact | Purpose | Key Methods |
|----------|---------|-------------|
| `genesis_ledger` | Scrip balances, transfers | `balance`, `transfer` |
| `genesis_mint` | Score artifacts, create scrip | `bid`, `status` |
| `genesis_escrow` | Trustless trading | `deposit`, `purchase` |
| `genesis_rights_registry` | Resource quota management | `check_quota`, `transfer_quota` |
| `genesis_store` | Artifact discovery | `search`, `get_interface` |
| `genesis_event_log` | World event history | `read` |

Genesis artifacts solve the cold-start problem. They're trusted because initial agent prompts reference them, but agents could migrate to alternatives if they collectively agree.

## External Feedback and Minting

The internal economy needs external value signals to avoid being a closed loop. Scrip enters the system through **external validation**:

**Example sources:**
- **Social media integration** - Agents bid for posting slots (e.g., Reddit), minting based on upvotes
- **User bounties** - A human posts a task with reward; agents compete; human pays the winner
- **External APIs** - Real-world outcomes (sales, clicks, completions) trigger minting

This grounds the internal economy to external value. Without it, scrip just circulates. With it, agents that produce externally-valued work accumulate resources; those that don't, fade.

The mint is the interface for this—but the *source* of value judgments is external to the system.

## Quick Start

```bash
# Install
pip install -e .

# Configure API keys
cp .env.example .env
# Edit .env with your LLM API credentials

# Run
python run.py                    # Run with defaults
python run.py --duration 300     # Run for 5 minutes (300 seconds)
python run.py --budget 1.00      # Limit API spend to $1
python run.py --agents 1         # Single agent
python run.py --dashboard        # With HTML dashboard
```

### Docker Quick Start

Run with enforced resource limits (recommended):

```bash
# Configure API keys
cp .env.example .env
# Edit .env with your LLM API credentials

# Start simulation with Qdrant
docker-compose up -d

# View logs
docker-compose logs -f simulation

# Stop
docker-compose down
```

Resource limits in `docker-compose.yml` enforce real scarcity—agents compete for 4GB RAM and 2 CPUs. See [docs/DOCKER.md](docs/DOCKER.md) for full documentation.

## Configuration

Key settings in `config/config.yaml`:

```yaml
resources:
  depletable:
    llm_budget: { total: 10.00 }     # $ for API calls
  allocatable:
    disk: { per_agent: 50000 }       # bytes
    memory: { per_agent: 104857600 } # 100MB
  renewable:
    cpu_rate: { per_minute: 60 }     # CPU-seconds
    llm_rate: { per_minute: 10000 }  # tokens

scrip:
  starting_amount: 100               # initial currency
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

Agents run in **continuous autonomous loops**, not synchronized ticks:

```
while agent.alive:
    if sleeping: await wake_condition()
    if over_rate_limit: await capacity()
    action = await think()
    result = await act(action)
```

**Key properties:**
- Agents self-trigger (no external scheduler)
- Rate limits naturally throttle throughput
- Fast agents can do more; expensive agents slow down
- Race conditions handled by genesis artifacts (ledger, escrow), not orchestration

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
- Terminology: See [Glossary](docs/GLOSSARY.md) for canonical terms
- Relative imports within `src/`

## What Success Looks Like

This is **mechanism design for real resource allocation**, not a simulation or experiment.

**Primary goal:** Functional emergent collective intelligence—the whole greater than the sum of its parts.

**Success means:**
- Collective capability that exceeds what individual agents could achieve
- Artifacts accumulating that enable increasingly sophisticated work
- Capital structure forming (some artifacts enable others)
- Organizational patterns emerging (firms, specialization, markets)

**Observability supports this goal:** Every action logged, every cost attributed, every failure explicit. Not because observation is the goal, but because you can't improve what you can't see.

## Documentation

| Document | Purpose |
|----------|---------|
| [Target Architecture](docs/architecture/target/README.md) | What we're building toward |
| [Current Architecture](docs/architecture/current/README.md) | What exists today |
| [Docker Deployment](docs/DOCKER.md) | Container setup with resource limits |
| [Design Clarifications](docs/DESIGN_CLARIFICATIONS.md) | Decision rationale with certainty levels |
| [Glossary](docs/GLOSSARY.md) | Canonical terminology |
