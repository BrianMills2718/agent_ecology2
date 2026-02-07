# Current Execution Model

How agent execution works TODAY.

**Last verified:** 2026-02-07 (Plan #308: dead code cleanup - removed unused import, no behavioral changes)

**See target:** [../target/execution_model.md](../target/execution_model.md)

---

## Agent Initialization

**Plan #299:** Legacy agent loading is disabled. Agents are now purely artifact-based.

```python
# Genesis loader creates artifact-based agents during World.__init__()
# Each agent is a 3-artifact cluster:
#   1. {agent}_strategy - text artifact with system prompt
#   2. {agent}_state - JSON artifact with state
#   3. {agent}_loop - executable artifact with has_loop=True

# ArtifactLoopManager discovers has_loop artifacts at runtime
artifact_loop_ids = artifact_loop_manager.discover_loops()
```

Genesis agents (in `config/genesis/agents/`) get:
- A strategy artifact (text with system prompt)
- A state artifact (JSON with current state)
- A loop artifact (`has_loop=True`, `executable=True`, code from `loop_code.py`)
- A principal entry in the ledger with starting scrip and LLM budget

See `config/genesis/SCHEMA.md` for artifact cluster format.

---

## Execution Mode

**Autonomous mode only** (Plan #102 - tick-based mode removed)
- Agents run independently via `AgentLoop`
- Resource-gated by `RateTracker` (rolling window)
- No tick synchronization
- Time-based auctions via periodic mint update

> **Note:** Legacy tick-based mode (`--ticks N`) was removed in Plan #102.
> Use `--duration N` for time-limited runs.

---

## The Narrow Waist: 13 Action Types + Reasoning

All agent actions must be one of these types (`src/world/actions.py`):

### Core Physics Verbs (6)

| Action Type | Purpose |
|-------------|---------|
| `noop` | Do nothing |
| `read_artifact` | Read artifact content |
| `write_artifact` | Create/update artifact (full replacement) |
| `edit_artifact` | Surgical edit of artifact content (Plan #131) |
| `invoke_artifact` | Call method on artifact |
| `delete_artifact` | Delete artifact and free disk quota |

### Kernel Primitives (2) - Plan #254

| Action Type | Purpose |
|-------------|---------|
| `transfer` | Transfer scrip to another principal |
| `mint` | Submit artifact for scoring and scrip minting |

### Kernel & Context Actions (5)

| Action Type | Purpose |
|-------------|---------|
| `query_kernel` | Direct kernel state queries (Plan #184) |
| `subscribe_artifact` | Subscribe to artifact change notifications (Plan #191) |
| `unsubscribe_artifact` | Unsubscribe from artifact notifications (Plan #191) |
| `configure_context` | Control context section visibility (Plan #192) |
| `modify_system_prompt` | Self-modify system prompt sections (Plan #194) |

**Note (Plan #254):** `transfer` and `mint` are now kernel actions. Previously, transfers went through `genesis_ledger.transfer()` invocation.

### Edit vs Write (Plan #131)

- **`write_artifact`**: Replaces entire content (like `cat > file`)
- **`edit_artifact`**: Surgical string replacement (like Claude Code's Edit tool)
  - Requires `old_string` and `new_string` parameters
  - Fails if `old_string` not found or not unique
  - More efficient for small changes to large artifacts

### Reasoning Field (Plan #49)

Every `ActionIntent` includes a `reasoning` field that captures why the agent chose this action:

```python
@dataclass
class ActionIntent:
    action_type: ActionType
    principal_id: str
    reasoning: str = ""  # Required explanation for this action
```

The reasoning flows from agent's `thought_process` through the narrow waist:
1. Agent produces `ActionResponse` with `thought_process`
2. Runner maps `thought_process` → `reasoning` in action JSON
3. `parse_intent_from_json()` extracts `reasoning`
4. Action event logged includes `reasoning` in `intent.to_dict()`

This enables LLM-native monitoring: analyzing reasoning quality, extracting strategies, detecting anomalies.

---

## Time-Based Mint Auctions (Plan #83)

The mint system uses wall-clock time for auction phases, not ticks. This enables proper auction operation in autonomous/duration mode.

### Auction Configuration (Time-Based)

```yaml
auction:
  period_seconds: 60.0           # Seconds between auction starts
  bidding_window_seconds: 30.0   # Duration of bidding phase (seconds)
  first_auction_delay_seconds: 30.0  # Delay before first auction starts
```

### Auction Phases

| Phase | Duration | Description |
|-------|----------|-------------|
| WAITING | `first_auction_delay_seconds` | Before first auction starts |
| BIDDING | `bidding_window_seconds` | Bids accepted and held in escrow |
| CLOSED | Until period ends | Auction resolved, bids apply to next cycle |

### Background Mint Updates (Autonomous Mode)

In autonomous mode, `SimulationRunner._mint_update_loop()` runs as a background task:

```python
async def _mint_update_loop(self) -> None:
    """Periodically call mint.update() for time-based auctions."""
    while True:
        result = self._handle_mint_update()
        if result:
            # Log auction resolution
        await asyncio.sleep(1.0)
```

The mint's `update()` method:
1. Checks elapsed time since simulation start
2. Starts auctions after `first_auction_delay_seconds`
3. Resolves auctions after `bidding_window_seconds`
4. Schedules next auction after `period_seconds`

### Anytime Bidding (Plan #5)

Bids are accepted at any time, not just during the BIDDING phase. Early bids are held until the next auction resolution.

---

## Summary Logging (Plan #60)

Summary statistics are logged for observability via `SummaryLogger`.

### What's Tracked

| Metric | Description |
|--------|-------------|
| `agents_active` | Agents that produced valid proposals |
| `actions_executed` | Total actions executed |
| `actions_by_type` | Breakdown by action type (read, write, invoke, noop) |
| `total_llm_tokens` | Combined input+output tokens for all agents |
| `total_scrip_transferred` | Scrip moved via genesis_ledger invocations |
| `artifacts_created` | New artifacts written |
| `errors` | Failed action count |
| `highlights` | Notable events (artifact creation, etc.) |

### Output

Summary data written to `summary.jsonl` via `SummaryLogger`:

```json
{"type": "action_summary", "agents_active": 3, "actions_executed": 3,
 "actions_by_type": {"invoke_artifact": 2, "write_artifact": 1},
 "total_llm_tokens": 4523, "total_scrip_transferred": 100, ...}
```

Use `python scripts/view_log.py --summary` to view aggregated summaries.

---

## Timing

In autonomous mode, each agent loop iteration:

| Phase | Duration |
|-------|----------|
| Thinking | ~2-10 seconds (LLM latency) |
| Execution | ~milliseconds |
| Loop delay | Configurable (`min_loop_delay`) |

### Rate Limiting

Resource-gated by `RateTracker` with rolling windows:
- `rate_limiting.window_seconds`: Rolling window size (default 60s)
- `rate_limiting.resources.llm_calls.max_per_window`: Max LLM calls per window

---

## Key Files

| File | Key Functions | Description |
|------|---------------|-------------|
| `src/simulation/agent_loop.py` | `AgentLoop._execute_iteration()` | **Primary integration point** for agent features |
| `src/simulation/agent_loop.py` | `AgentLoopManager` | Manages agent loops lifecycle |
| `src/agents/rate_tracker.py` | `RateTracker` | Rolling window resource gating |
| `src/simulation/runner.py` | `SimulationRunner.run()` | Main entry point (autonomous only) |
| `src/world/world.py` | `World.execute_action()` | Action dispatcher |
| `src/world/actions.py` | `parse_intent_from_json()` | Action parsing (the "narrow waist") |

---

## Implications

### Autonomous Mode (Only Mode)
- Agents decide their own pace via `AgentLoop`
- Resource exhaustion (RateTracker) gates actions
- Efficient agents can act more frequently → selection pressure
- Strategy diversity: fast/slow strategies emerge naturally

---

## Autonomous Execution Details

Agents run independently via `AgentLoop`, resource-gated by `RateTracker`.

### CLI Usage

```bash
# Run autonomous mode for 60 seconds
python run.py --duration 60

# Run autonomous mode with dashboard
python run.py --duration 120 --dashboard

# Run indefinitely (until budget exhausted or Ctrl+C)
python run.py
```

### Configuration

```yaml
# Note: Autonomous mode is always enabled (Plan #102 removed tick-based mode)
rate_limiting:
  enabled: true
  window_seconds: 60.0
  resources:
    llm_calls:
      max_per_window: 100
```

### How It Works

1. Each agent gets an `AgentLoop` from `AgentLoopManager`
2. Loops run continuously via `asyncio.create_task()`
3. Resource exhaustion pauses agent (doesn't crash)
4. `RateTracker` handles all rate limiting

### AgentLoop States

| State | Description |
|-------|-------------|
| `RUNNING` | Actively deciding/executing |
| `SLEEPING` | Waiting for wake condition |
| `PAUSED` | Resource exhausted or error limit |
| `STOPPED` | Loop terminated |

### Resource Exhaustion Policy

```yaml
execution:
  resource_exhaustion_policy: skip  # or "block"
```

- `skip`: Agent skips iteration, continues next cycle
- `block`: Agent waits until resources available

---

## Differences from Target

| Current | Target |
|---------|--------|
| Autonomous only (Plan #102) | Autonomous only ✅ |
| RateTracker enabled | RateTracker always on ✅ |
| Rolling window rate limiting | Rolling window only ✅ |

See `docs/architecture/target/02_execution_model.md` for target architecture.
