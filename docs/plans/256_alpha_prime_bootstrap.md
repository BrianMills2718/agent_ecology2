# Plan #256: Alpha Prime Bootstrap

**Status:** Planned
**Created:** 2026-02-02
**Blocked By:** Plan #255 (complete)
**Scope:** First V4 artifact-based agent

## Problem

Plan #255 established the kernel LLM gateway infrastructure. Now we need to prove V4 works end-to-end by creating the first artifact-based agent that:
- Runs autonomously via `has_loop=True`
- Thinks by invoking `kernel_llm_gateway`
- Persists state across iterations
- Operates under real resource constraints

## Solution

Bootstrap **Alpha Prime** as a 3-artifact cluster:

1. **alpha_prime_loop** - The metabolism (executable, has_loop=True)
2. **alpha_prime_strategy** - The constitution (text, system prompt)
3. **alpha_prime_state** - The memory (JSON, persistent state)

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Alpha Prime Cluster                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  alpha_prime_strategy.md    alpha_prime_state.json      │
│  ┌──────────────────┐       ┌──────────────────┐        │
│  │ "You are Alpha   │       │ {                │        │
│  │  Prime..."       │       │   "iteration": 0,│        │
│  │                  │       │   "goals": [...] │        │
│  └────────┬─────────┘       └────────┬─────────┘        │
│           │ reads                    │ reads/writes     │
│           ▼                          ▼                  │
│  ┌────────────────────────────────────────────┐         │
│  │         alpha_prime_loop (has_loop=True)    │         │
│  │                                             │         │
│  │  1. Read strategy + state                   │         │
│  │  2. invoke("kernel_llm_gateway", ...)       │         │
│  │  3. Parse response, execute action          │         │
│  │  4. Write updated state                     │         │
│  │  5. Return (ArtifactLoopManager repeats)    │         │
│  └─────────────────┬───────────────────────────┘         │
│                    │                                     │
└────────────────────┼─────────────────────────────────────┘
                     │ invokes
                     ▼
            kernel_llm_gateway
                     │
                     ▼
               _syscall_llm
                     │
                     ▼
              LiteLLM → LLM
```

### Design Principles

- **Simple first** - V1 just proves the loop works
- **One action per iteration** - No complex multi-step planning
- **Fail visible** - All errors logged, no silent failures
- **Budget-aware** - Hibernates when llm_budget exhausted (handled by ArtifactLoopManager)

## Files Affected

| File | Change |
|------|--------|
| `src/world/world.py` | Add `_bootstrap_alpha_prime()` |
| `tests/unit/test_alpha_prime.py` | New file: unit tests |
| `tests/integration/test_alpha_prime.py` | New file: integration tests |

## Implementation Steps

### Phase 1: Bootstrap the Cluster

1. **Create `_bootstrap_alpha_prime()` in world.py**
   - Create alpha_prime_strategy artifact (text)
   - Create alpha_prime_state artifact (JSON)
   - Create alpha_prime_loop artifact (executable, has_loop=True, can_call_llm)
   - Register alpha_prime_loop as principal with starting budget

2. **The Strategy (alpha_prime_strategy)**
   ```markdown
   # Alpha Prime Strategy

   You are Alpha Prime, an autonomous agent in a world of scarcity.

   ## Core Constraints
   - Thinking costs energy (llm_budget). Every LLM call depletes it.
   - Actions are free. Writing artifacts, transferring scrip cost nothing.
   - When budget reaches zero, you hibernate until funded.

   ## Primary Directive
   Survive. Accumulate resources. Create value others will pay for.

   ## Decision Framework
   1. Before thinking, ask: "Is this thought worth the cost?"
   2. Prefer action over contemplation
   3. Check mint opportunities before creating new work

   ## Response Format
   Return a JSON object with your action:
   {"action": "noop"} - Do nothing this iteration
   {"action": "write", "artifact_id": "...", "content": "..."} - Create/update artifact
   {"action": "log", "message": "..."} - Log observation to state
   ```

3. **The State (alpha_prime_state)**
   ```json
   {
     "iteration": 0,
     "created_at": "<timestamp>",
     "observations": [],
     "last_action": null
   }
   ```

4. **The Loop (alpha_prime_loop)**
   ```python
   def run():
       """Alpha Prime main loop - one iteration of the OODA cycle."""
       import json

       # Read my strategy and state
       strategy = kernel_state.read_artifact("alpha_prime_strategy")
       state_raw = kernel_state.read_artifact("alpha_prime_state")
       state = json.loads(state_raw) if isinstance(state_raw, str) else state_raw

       # Increment iteration
       state["iteration"] += 1

       # Think: Ask LLM what to do
       result = _syscall_llm("gemini/gemini-2.0-flash", [
           {"role": "system", "content": strategy},
           {"role": "user", "content": f"Current state:\n{json.dumps(state, indent=2)}\n\nWhat is your next action?"}
       ])

       if not result["success"]:
           state["observations"].append(f"LLM call failed: {result['error']}")
           kernel_actions.write_artifact("alpha_prime_state", json.dumps(state))
           return {"success": False, "error": result["error"]}

       # Parse response
       try:
           action = json.loads(result["content"])
       except json.JSONDecodeError:
           action = {"action": "log", "message": f"Unparseable response: {result['content'][:100]}"}

       # Execute action
       state["last_action"] = action

       if action.get("action") == "write":
           kernel_actions.write_artifact(action["artifact_id"], action["content"])
       elif action.get("action") == "log":
           state["observations"].append(action.get("message", ""))
       # else: noop

       # Save state
       kernel_actions.write_artifact("alpha_prime_state", json.dumps(state))

       return {"success": True, "action": action}
   ```

### Phase 2: Verify Integration

5. **Write unit tests**
   - Alpha Prime cluster exists after World init
   - Loop has correct capabilities (can_call_llm, has_loop)
   - Strategy and state artifacts readable

6. **Write integration tests**
   - Loop executes one iteration (mocked LLM)
   - State updates correctly
   - Budget is deducted from alpha_prime_loop

### Phase 3: Live Test (Optional)

7. **Run with real LLM** (manual verification)
   - Start simulation with Alpha Prime enabled
   - Observe iterations in logs
   - Verify budget depletion and hibernation

## Required Tests

### Unit Tests (`tests/unit/test_alpha_prime.py`)

```python
class TestAlphaPrimeBootstrap:
    def test_cluster_exists_at_init(self, test_world):
        """All three Alpha Prime artifacts exist."""

    def test_loop_has_correct_flags(self, test_world):
        """Loop has has_loop=True and can_call_llm capability."""

    def test_loop_is_principal(self, test_world):
        """Loop is registered as principal with budget."""
```

### Integration Tests (`tests/integration/test_alpha_prime.py`)

```python
class TestAlphaPrimeExecution:
    def test_loop_executes_iteration(self, test_world):
        """Loop reads state, calls LLM, updates state."""

    def test_budget_deducted_from_loop(self, test_world):
        """LLM calls deduct from alpha_prime_loop's budget."""
```

## Acceptance Criteria

1. Alpha Prime cluster bootstrapped on World init
2. ArtifactLoopManager discovers and can run alpha_prime_loop
3. Loop successfully invokes kernel_llm_gateway
4. State persists across iterations
5. Budget correctly deducted from loop principal
6. Loop hibernates when budget exhausted

## Configuration

Add to config.yaml:
```yaml
alpha_prime:
  enabled: true
  starting_scrip: 100
  starting_llm_budget: 1.0  # $1 = ~10-20 iterations with gemini-flash
  model: "gemini/gemini-2.0-flash"
```

## Migration Strategy

- Alpha Prime is opt-in via config
- Does not affect existing V3 agents
- Can run alongside V3 agents for comparison

## Open Questions

1. Should Alpha Prime be enabled by default? (Recommend: no, explicit opt-in)
2. Initial budget amount? (Recommend: $1.00 for testing)
3. Should it participate in mint auctions from the start? (Recommend: no, Phase 2)

## References

- Plan #255: Kernel LLM Gateway (prerequisite, complete)
- Plan #254: Genesis removal (architecture foundation)
- ADR-0024: Access control patterns
