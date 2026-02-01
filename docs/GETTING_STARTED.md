# Getting Started

## Quick Start

```bash
# Install
pip install -e .

# Configure API keys
cp .env.example .env
# Edit .env with your LLM API credentials (GEMINI_API_KEY, OPENAI_API_KEY, etc.)

# Run
python run.py                        # Run with defaults
python run.py --duration 300         # Run for 5 minutes
python run.py --agents 1             # Single agent
python run.py --dashboard            # With HTML dashboard
python run.py --resume               # Resume from checkpoint
```

## Docker

Run with enforced resource limits (recommended for real scarcity):

```bash
cp .env.example .env
# Edit .env with your LLM API credentials

docker-compose up -d                 # Start simulation with Qdrant
docker-compose logs -f simulation    # View logs
docker-compose down                  # Stop
```

Resource limits in `docker-compose.yml` enforce real scarcity — agents compete for bounded CPU and memory. See [DOCKER.md](DOCKER.md) for full documentation.

## Configuration

All settings live in `config/config.yaml`, validated at startup by Pydantic (`src/config_schema.py`).

Key sections:

```yaml
resources:
  stock:
    llm_budget: { total: 100.00 }    # $ for API calls (depletable)
    disk: { total: 500000 }          # bytes (allocatable)

scrip:
  starting_amount: 100               # Initial currency per agent

rate_limiting:
  window_seconds: 60.0               # Rolling window for renewable resources

budget:
  max_api_cost: 0.50                 # Global API cost limit ($)
  max_runtime_seconds: 3600          # Hard timeout (1 hour)

llm:
  default_model: "gemini/gemini-2.0-flash"
```

Models are configured with per-model pricing in `models.pricing`. If a model isn't listed, LiteLLM's pricing is used as fallback.

## Project Structure

```
agent_ecology/
  run.py                    # Entry point
  config/
    config.yaml             # Runtime values (validated by src/config_schema.py)
  src/
    config.py               # Config helpers
    world/                  # World state, ledger, executor, artifacts, contracts
    agents/                 # Agent loading, LLM interaction, memory
    simulation/             # SimulationRunner, checkpointing
    dashboard/              # HTML dashboard server
  tests/                    # pytest suite
  docs/
    architecture/           # current/ and target/ system design
    adr/                    # Architecture Decision Records
    plans/                  # Active implementation plans
  meta/
    acceptance_gates/       # Feature specifications (YAML)
  scripts/                  # Utility scripts for CI and development
```

## Development

```bash
make test                # Run pytest
make check               # All CI checks (test + mypy + lint + doc-coupling)
```

Standards:
- All functions require type hints (`mypy --strict`)
- No magic numbers — values come from `config/config.yaml`
- Terminology: see [Glossary](GLOSSARY.md)

## Documentation

| Document | Purpose |
|----------|---------|
| [Current Architecture](architecture/current/README.md) | What exists today |
| [Target Architecture](architecture/target/README.md) | What we're building toward |
| [Design Clarifications](DESIGN_CLARIFICATIONS.md) | Decision rationale with certainty levels |
| [Glossary](GLOSSARY.md) | Canonical terminology |
| [Docker Deployment](DOCKER.md) | Container setup with resource limits |
| [Security Model](SECURITY.md) | Security boundaries and rationale |
| [Threat Model](THREAT_MODEL.md) | Threat analysis and mitigations |
| [ADR Index](adr/README.md) | Architecture Decision Records |
