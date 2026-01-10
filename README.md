# Agent Ecology

A simulation framework where LLM agents interact under real resource constraints.

## Overview

Agent Ecology creates an economic environment where multiple LLM agents operate within realistic resource limits. Agents can read, write, and invoke artifacts (code and data), trade resources, and earn scrip (currency) by creating valuable services.

The simulation models actual physical and financial scarcity:

- **Compute** - CPU/GPU cycles, refreshes each tick
- **Disk** - Storage bytes, finite pool
- **Scrip** - Economic currency for trading and payments

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up API keys in .env
cp .env.example .env
# Edit .env with your LLM API credentials

# Run the simulation
python run.py                    # Run with defaults
python run.py --ticks 10         # Limit to 10 ticks
python run.py --agents 1         # Run with only first agent
python run.py --quiet            # Suppress output
python run.py --delay 5          # 5 second delay between LLM calls
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

# Action costs (compute units)
costs:
  actions:
    read_artifact: 2
    write_artifact: 5
    invoke_artifact: 1
  per_1k_input_tokens: 1
  per_1k_output_tokens: 3

# World settings
world:
  max_ticks: 100

# Budget limits
budget:
  max_api_cost: 1.00              # $ total API spend
```

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

### Resource Model

| Type | Resources | Behavior |
|------|-----------|----------|
| Stock | `llm_budget`, `disk` | Finite, never refreshes |
| Flow | `compute`, `bandwidth` | Refreshes each tick |

When agents exhaust resources, they must acquire more from others via trading rights.

## Actions

Agents operate through three core verbs (narrow waist design):

### read_artifact
Read content from an artifact.
```json
{"action_type": "read_artifact", "artifact_id": "<id>"}
```
Cost: 2 compute + input token cost on next turn

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
  "code": "def run(*args): return args[0] * 2"
}
```
Cost: 5 compute + disk quota

### invoke_artifact
Call a method on an artifact.
```json
{"action_type": "invoke_artifact", "artifact_id": "<id>", "method": "<method>", "args": [...]}
```
Cost: 1 compute + method fee + 2 gas (for executables)

Example - transfer scrip:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_ledger", "method": "transfer", "args": ["agent_a", "agent_b", 10]}
```

## Development

### Type Checking

The project uses strict type hints throughout.

```bash
# Run mypy
mypy --strict src/

# Or check specific files
mypy --strict run.py src/world/
```

### Code Standards

- All functions require type hints (parameters and return types)
- No magic numbers in code - all values come from config
- Use modern Python typing: `dict[str, Any]` not `Dict[str, Any]`
- Consistent terminology: `compute`, `disk`, `scrip` (not credits)

### Project Structure

```
agent_ecology/
  run.py              # Main entry point
  config/
    config.yaml       # Configuration values
    schema.yaml       # Config documentation
  src/
    world/            # World state and execution
    agents/           # Agent loading and LLM interaction
    config.py         # Config helpers
  agents/             # Agent definitions (prompts, configs)
  llm_logs/           # LLM interaction logs
```

### Logging

Simulation events are logged to `run.jsonl`. LLM interactions are saved to `llm_logs/`.
