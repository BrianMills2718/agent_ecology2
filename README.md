# Agent Ecology

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
