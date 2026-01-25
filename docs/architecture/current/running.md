# Running the Simulation

Practical guide to running and observing agent ecology simulations.

**Last verified:** 2026-01-25

---

## Quick Start

```bash
# Install dependencies
pip install -e .

# Configure API keys
cp .env.example .env
# Edit .env with your GEMINI_API_KEY

# Run simulation (60 seconds)
python run.py --duration 60 --agents 2
```

---

## Command Line Options

| Flag | Description | Default |
|------|-------------|---------|
| `--config PATH` | Config file path | `config/config.yaml` |
| `--agents N` | Limit to first N agents | All agents in `agents/` |
| `--quiet` | Suppress progress output | Off |
| `--dashboard` | Run with HTML dashboard | Off |
| `--dashboard-only` | View existing logs (no simulation) | Off |
| `--no-browser` | Don't auto-open browser | Off |
| `--resume [FILE]` | Resume from checkpoint | `checkpoint.json` |
| `--duration SECONDS` | Run for N seconds | Required (or use --autonomous) |
| `--autonomous` | Run until manually stopped | Off |

> **Note:** Legacy tick-based mode (`--ticks N`) was removed in Plan #102. Use `--duration` or `--autonomous` instead.

---

## Execution Model

Agents run continuously in independent loops, resource-gated by RateTracker.

```bash
# Run for 60 seconds
python run.py --duration 60

# Run until all agents stop (or Ctrl+C)
python run.py --autonomous
```

This model enables:
- Independent agent loops (agents don't wait for each other)
- Rolling window rate limiting instead of per-tick reset
- Resource exhaustion pauses agent, doesn't crash

---

## Dashboard

Real-time HTML dashboard for observing simulation state.

```bash
# Run simulation with dashboard
python run.py --dashboard

# View existing logs without running simulation
python run.py --dashboard-only
```

Dashboard shows:
- Current simulation state and agent activity
- Scrip balances
- Recent events
- Artifact list

Default URL: http://localhost:8080

---

## Output Files

| File | Content | Format |
|------|---------|--------|
| `run.jsonl` | All simulation events | JSON Lines |
| `checkpoint.json` | Resumable state | JSON |
| `llm_logs/` | Per-agent LLM call logs | JSON |

### Viewing Logs

```bash
# View summary
python scripts/view_log.py run.jsonl

# View full event log
python scripts/view_log.py run.jsonl --full

# View artifacts
python scripts/view_log.py run.jsonl --artifacts
```

### Log Event Types

| Event Type | Description |
|------------|-------------|
| `thinking` | Agent completed thinking phase |
| `thinking_failed` | Agent ran out of compute |
| `action_result` | Action executed |
| `intent_rejected` | Invalid action rejected |
| `mint_auction` | Auction resolved |
| `budget_pause` | API budget exhausted |

---

## Checkpointing

### Automatic Checkpoints

Checkpoints save every N ticks (configurable via `budget.checkpoint_interval`).

```yaml
# config/config.yaml
budget:
  checkpoint_interval: 60  # Every 60 seconds (0 = disable)
  checkpoint_on_end: true  # Save on normal completion
```

### Resume from Checkpoint

```bash
# Resume from default checkpoint
python run.py --resume --duration 60

# Resume from specific file
python run.py --resume my_checkpoint.json --duration 60
```

Checkpoint contains:
- Current event number (sequence)
- All agent balances (scrip and compute)
- All artifacts
- Cumulative API cost

---

## Budget Control

### API Cost Limit

```yaml
# config/config.yaml
budget:
  max_api_cost: 1.00  # $ limit (0 = unlimited)
```

When budget exhausts:
1. Simulation pauses
2. Checkpoint saved
3. Message printed with cost breakdown

Resume after adding funds:
```bash
# Edit config to increase max_api_cost, then:
python run.py --resume
```

### Estimating Costs

Rough estimates per tick with 2 agents:
- Input: ~300 tokens ($0.0001)
- Output: ~150 tokens ($0.0002)
- **Total: ~$0.0003/tick**

With default 100 ticks and 2 agents: ~$0.03

---

## Configuration

Key settings in `config/config.yaml`:

```yaml
world:
  max_ticks: 100          # Max simulation length

llm:
  rate_limit_delay: 5     # Seconds between ticks
  default_model: "gemini/gemini-3-flash-preview"

budget:
  max_api_cost: 1.00      # $ limit

scrip:
  starting_amount: 100    # Per agent
```

See `config/schema.yaml` for full documentation.

---

## Common Issues

### "Rate limit exceeded"

LLM API rate limiting. Increase delay:
```bash
python run.py --delay 15
```

### "BUDGET EXHAUSTED"

API cost limit reached. Options:
1. Increase `budget.max_api_cost` in config
2. Resume from checkpoint: `python run.py --resume`

### Agents do nothing

Check compute quota. If agents have 0 compute, they can't think.
```bash
# View recent logs
python scripts/view_log.py run.jsonl --full | tail -50
```

### "Checkpoint not found"

No checkpoint exists. Start fresh:
```bash
python run.py  # Don't use --resume
```

---

## Docker Deployment

For enforced resource limits, see [docs/DOCKER.md](../../DOCKER.md).

```bash
docker-compose up -d
docker-compose logs -f simulation
```

---

## Related Documents

| Document | Purpose |
|----------|---------|
| [execution_model.md](execution_model.md) | Internal execution mechanics |
| [configuration.md](configuration.md) | Config loading and validation |
| [DOCKER.md](../../DOCKER.md) | Container deployment |
