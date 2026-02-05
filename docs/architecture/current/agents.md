# Current Agent Model

How agents work TODAY.

**Last verified:** 2026-02-05 (Plan #299: Legacy agent system removed)

**See target:** [../target/agents.md](../target/agents.md)

---

## Agent Model (Plan #299)

Agents are now **3-artifact clusters** loaded by the genesis system:

1. **Strategy artifact** (text) - System prompt and instructions
2. **State artifact** (JSON) - Agent's working memory and state
3. **Loop artifact** (executable, has_loop=True) - Autonomous behavior code

### Example: alpha_prime

```
config/genesis/agents/alpha_prime/
├── agent.yaml         # Manifest (declares 3 artifacts)
├── strategy.md        # Strategy artifact content
├── initial_state.json # State artifact initial value
└── loop_code.py       # Loop artifact code (has_loop=True)
```

The genesis loader creates these as artifacts during World initialization.

---

## Agent Lifecycle

Agents run via `ArtifactLoopManager`. Each has_loop=True artifact runs autonomously:

1. **Discovery** - ArtifactLoopManager finds has_loop artifacts
2. **Start loop** - Each loop runs in its own async task
3. **Execute** - Loop code reads state, calls `_syscall_llm()`, executes action
4. **Repeat** - Until stopped or resources exhausted

```
ArtifactLoopManager.start_all():
  for artifact in artifacts where has_loop=True:
    asyncio.create_task(run_artifact_loop(artifact))

run_artifact_loop(artifact):
  while not stopped:
    1. Invoke artifact (executor runs loop code)
    2. Loop code uses _syscall_llm() for LLM calls
    3. Loop code writes to state artifact
    4. Sleep/backoff as needed
```

**Duration mode:** Use `--duration N` to run for N seconds. Agents run autonomously (no tick synchronization).

---

## Loop Code Pattern

```python
# loop_code.py - executed by executor when artifact is invoked
def run():
    # Read state
    state_str = kernel_state.read_artifact("agent_state", caller_id)
    state = json.loads(state_str) if state_str else {}

    # Read strategy
    strategy = kernel_state.read_artifact("agent_strategy", caller_id)

    # Build prompt
    prompt = f"{strategy}\n\nCurrent state: {json.dumps(state)}\n\nDecide action."

    # Call LLM via kernel primitive
    result = _syscall_llm("gemini/gemini-3-flash-preview", [
        {"role": "user", "content": prompt}
    ])

    # Parse response and execute action
    action = json.loads(result["content"])

    # Update state
    state["last_action"] = action
    kernel_actions.write_artifact(caller_id, "agent_state", json.dumps(state))

    return {"action": action}
```

---

## Key Properties

| Property | Meaning |
|----------|---------|
| `has_loop=True` | Artifact runs autonomously via ArtifactLoopManager |
| `has_standing=True` | Artifact can hold resources (scrip, quotas) |
| `is_agent` | Both has_loop and has_standing are True |
| `is_principal` | Same as has_standing |

---

## Legacy System (Removed)

The previous system (~8600 lines) has been deleted:

| Component | Was | Replaced By |
|-----------|-----|-------------|
| `agent.py` | 77-method LLM wrapper | Loop code + `_syscall_llm()` |
| `workflow.py` | State machine engine | State in JSON artifact |
| `loader.py` | Agent discovery | Genesis loader |
| `memory.py` | Mem0/Qdrant integration | State artifacts |
| `schema.py` | Action schemas | Loop code parsing |

Historical reference: `docs/catalog.yaml` contains agent lineage tracking.

---

## Configuration

Agents are configured in `config/genesis/agents/{name}/agent.yaml`:

```yaml
enabled: true
artifacts:
  - id: "{name}_strategy"
    type: text
    source: strategy.md
  - id: "{name}_state"
    type: json
    source: initial_state.json
  - id: "{name}_loop"
    type: executable
    source: loop_code.py
    has_loop: true
    has_standing: true
```

---

## See Also

- `config/genesis/agents/alpha_prime/` - Reference implementation
- `src/simulation/artifact_loop.py` - ArtifactLoopManager
- `src/world/executor.py` - Loop code execution with `_syscall_llm()`
