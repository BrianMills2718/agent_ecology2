# Agent Ecology

A simulation framework where LLM agents interact under real resource constraints.

## Overview

Agent Ecology creates an economic environment where multiple LLM agents operate within realistic resource limits. Agents can read, write, and invoke artifacts (code and data), trade resources, and earn scrip (currency) by creating valuable services.

## Physics-First Philosophy

The simulation is built on five core principles:

1. **Time is scarce** - Every token consumes compute. Efficient agents preserve resources for future actions.

2. **Resources are concrete** - Three distinct resource types with physical meaning:
   - *Compute* (flow) - Refreshes each tick, models CPU/GPU cycles
   - *Disk* (stock) - Finite storage, never refreshes
   - *Scrip* (signal) - Economic currency, separate from physical constraints

3. **Money is a signal** - Scrip is deliberately separated from physical resources. An agent can be rich in scrip but starved of compute, or vice versa.

4. **Identity is capital** - Agents can spawn new principals via `spawn_principal`. Each identity has its own resource accounts and reputation.

5. **Trust is emergent** - The ledger is ground truth; agent descriptions can lie. Trust must be verified through behavior, not claimed.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Install the package in editable mode (required for imports)
pip install -e .

# Set up API keys in .env
cp .env.example .env
# Edit .env with your LLM API credentials

# Run the simulation
python run.py                    # Run with defaults
python run.py --ticks 10         # Limit to 10 ticks
python run.py --agents 1         # Run with only first agent
python run.py --quiet            # Suppress output
python run.py --delay 5          # 5 second delay between LLM calls
python run.py --dashboard        # Run with HTML dashboard
```

## Configuration

Key settings in `config/config.yaml`:

```yaml
# Resource limits
resources:
  stock:
    llm_budget: { total: 1.00 }    # $ for API calls
    disk: { total: 50000 }         # bytes total
  flow:
    compute: { per_tick: 1000 }    # cycles per tick

# Starting currency
scrip:
  starting_amount: 100

# Token costs (for thinking)
costs:
  per_1k_input_tokens: 1
  per_1k_output_tokens: 3

# World settings
world:
  max_ticks: 100

# Budget limits
budget:
  max_api_cost: 1.00              # $ total API spend
```

## Key Features

### Two-Phase Commit
Each tick executes in two phases for fairness:
1. **Collect phase** - All agents submit actions simultaneously
2. **Execute phase** - Actions are applied atomically

This prevents ordering advantages and enables true concurrency.

### spawn_principal
Agents can create new agents dynamically:
```json
{"action_type": "spawn_principal", "principal_id": "my_worker", "config": {...}}
```
Spawned principals inherit resources from their creator and can act independently.

### Policy System
Artifacts support access control policies:
- **read_policy** - Who can read the artifact
- **invoke_policy** - Who can call methods
- Policies reference principal IDs or wildcards

### Originality Oracle
The `genesis_oracle` detects duplicate or derivative artifacts:
- Compares new submissions against existing artifacts
- Only novel contributions earn scrip rewards
- Prevents copy-paste farming

### Pydantic Structured Outputs
Actions are parsed using Pydantic models for reliability:
- Schema validation on all agent outputs
- Clear error messages for malformed actions
- Type-safe action handling throughout

## Architecture

### Core Components

- **World** - Manages simulation state, tick advancement, and action execution
- **Agents** - LLM-powered actors loaded from `agents/` directory
- **Ledger** - Tracks scrip balances and resource rights
- **Artifacts** - Code and data objects agents can create and interact with

### Genesis Artifacts

System-provided services available to all agents:

| Artifact | Purpose |
|----------|---------|
| `genesis_ledger` | Scrip balances and transfers |
| `genesis_rights_registry` | Resource quota management |
| `genesis_oracle` | Score code artifacts and mint scrip |
| `genesis_event_log` | World event history |
| `genesis_escrow` | Trustless artifact trading |

### Resource Model

| Type | Resources | Behavior |
|------|-----------|----------|
| Stock | `llm_budget`, `disk` | Finite, never refreshes |
| Flow | `compute`, `bandwidth` | Refreshes each tick |

When agents exhaust resources, they must acquire more from others via trading rights.

## Security Model

Agent code executes with minimal restrictions:

- **Unrestricted executor** - No RestrictedPython sandbox. Agent code has full Python capabilities.
- **Docker isolation** - Simulation runs as non-root user inside Docker container for process-level isolation.
- **API key access** - Agent code can access environment variables including API keys. This is intentional - agents may need to call external services.

The security boundary is the container, not the Python interpreter. Agents are trusted with full code execution within the container's constraints.

## Actions

Agents operate through three core verbs (narrow waist design):

### read_artifact
Read content from an artifact.
```json
{"action_type": "read_artifact", "artifact_id": "<id>"}
```
Cost: Free (content adds to context when you next think)

### write_artifact
Create or update an artifact.
```json
{"action_type": "write_artifact", "artifact_id": "<id>", "artifact_type": "<type>", "content": "<content>"}
```

For executable artifacts:
```json
{
  "action_type": "write_artifact",
  "artifact_id": "<id>",
  "artifact_type": "executable",
  "content": "<description>",
  "executable": true,
  "price": 5,
  "resource_policy": "caller_pays",
  "code": "def run(*args): return args[0] * 2"
}
```
- `price`: Scrip paid to owner when invoked
- `resource_policy`: `"caller_pays"` (default) or `"owner_pays"` - who pays physical resources

Cost: Free (uses disk quota for storage)

### invoke_artifact
Call a method on an artifact.
```json
{"action_type": "invoke_artifact", "artifact_id": "<id>", "method": "<method>", "args": [...]}
```
Cost: Free (method may have scrip fee for genesis artifacts)

Example - transfer scrip:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger", "method": "transfer", "args": ["agent_a", "agent_b", 10]}
```

## Development

### Setup

```bash
# Install in editable mode (required)
pip install -e .

# Run tests
pytest tests/

# Type checking
python -m mypy src/ --ignore-missing-imports
```

### Type Checking

The project uses strict type hints throughout. All code must pass mypy.

```bash
# Run mypy on entire src directory
python -m mypy src/ --ignore-missing-imports

# Check specific files
python -m mypy src/world/ src/agents/ --ignore-missing-imports
```

### Code Standards

- All functions require type hints (parameters and return types)
- No magic numbers in code - all values come from config
- Use modern Python typing: `dict[str, Any]` not `Dict[str, Any]`
- Consistent terminology: `compute`, `disk`, `scrip` (not credits)
- Use relative imports within `src/` package (e.g., `from ..config import get`)
- Tests use `from src.module import` style

### Project Structure

```
agent_ecology/
  run.py              # Main entry point
  pyproject.toml      # Package configuration
  config/
    config.yaml       # Configuration values
    schema.yaml       # Config documentation
  src/
    world/            # World state and execution
    agents/           # Agent loading and LLM interaction
    simulation/       # SimulationRunner and checkpoint
    config.py         # Config helpers
    config_schema.py  # Pydantic config validation
    dashboard/        # HTML dashboard server
  tests/              # Test suite (319 tests)
  llm_logs/           # LLM interaction logs (by date)
```

### Logging

- **Simulation events**: Logged to `run.jsonl`
- **LLM interactions**: Saved to `llm_logs/YYYYMMDD/` with metadata:
  - `agent_id`: Which agent made the call
  - `run_id`: Simulation run identifier
  - `tick`: Current simulation tick
