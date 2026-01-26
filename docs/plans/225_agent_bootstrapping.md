# Plan #225: Agent Bootstrapping Guidance

**Status:** In Progress
**Priority:** High
**Blocked By:** None
**Blocks:** Agent learning, productive simulations

---

## Problem Statement

Agents are stuck in unproductive loops because they lack concrete first steps:

1. **beta_3** recognizes "I need to establish a subgoal" but returns noop anyway
2. **alpha_3** tries to "test" itself (the agent config artifact) in a loop
3. **delta_3** uses random_decider which returns false 80% of the time → noops

The agents have behaviors like `loop_breaker` that say "try something different" but they don't know WHAT different thing to try. They need bootstrapping guidance for their first actions.

**Evidence from logs:**
```
beta_3: "My subgoal is currently empty, so I should choose a subgoal. I should start with creating an artifact"
→ Returns noop

alpha_3: "I should test the 'alpha_3' artifact"
→ Invokes itself, fails, repeats
```

---

## Solution

### 1. Add Bootstrapping Behavior Component

Create `bootstrapping.yaml` that injects CONCRETE first steps when agent has no prior successful actions.

```yaml
name: bootstrapping
type: behavior
version: 1
description: "Provides concrete first steps for new agents"

inject_into:
  - observe
  - observing
  - strategic
  - planning
  - ideate
  - ideating

prompt_fragment: |
  === GETTING STARTED (if this is your first action or you're stuck) ===

  IF YOU HAVE NO SUCCESSFUL ACTIONS YET, do these IN ORDER:

  1. EXPLORE: Use query_kernel to see what exists
     {{"action_type": "query_kernel", "query_type": "artifacts"}}

  2. LEARN: Read the handbook for guidance
     {{"action_type": "read_artifact", "artifact_id": "genesis_handbook"}}

  3. BUILD SOMETHING SIMPLE: Create a basic artifact
     {{"action_type": "write_artifact", "artifact_id": "my_first_tool",
       "content": "def run(x): return x * 2",
       "artifact_type": "tool",
       "interface": {{"methods": [{{"name": "run", "args": [{{"name": "x", "type": "int"}}], "returns": "int"}}]}}
     }}

  4. TEST IT: Invoke your artifact to verify it works
     {{"action_type": "invoke_artifact", "artifact_id": "my_first_tool", "method": "run", "args": [5]}}

  DO NOT noop if you haven't completed these steps!

requires_context:
  - success_rate
  - action_history
```

### 2. Remove Random Decider from delta_3

The `genesis_random_decider` with 20% probability causes 80% noops. Replace with a more useful decision artifact or remove entirely.

**Before:**
```yaml
transition_source:
  invoke: "genesis_random_decider"
  method: "decide"
  args: [{probability: 0.2}]
```

**After:** Remove the random exploration step or use a smarter decision artifact.

### 3. Fix alpha_3 "Testing" State

The testing prompt says "TEST YOUR ARTIFACT" but agents haven't built anything yet. Add guard:

```yaml
prompt: |
  === TESTING: Does it work? ===

  IMPORTANT: Only test artifacts YOU CREATED (listed in {my_artifacts}).
  Do NOT try to test or invoke your own agent ID ({agent_id}).

  If you have no artifacts to test, use noop and reflect on what to build.
```

### 4. Add Success Rate Context

Agents need to know if they've had any successful actions. Add `has_successful_actions` to context.

---

## Files Changed

| File | Change |
|------|--------|
| `src/agents/_components/behaviors/bootstrapping.yaml` | NEW - First steps guidance |
| `src/agents/alpha_3/agent.yaml` | Add bootstrapping behavior, fix testing prompt |
| `src/agents/beta_3/agent.yaml` | Add bootstrapping behavior |
| `src/agents/delta_3/agent.yaml` | Add bootstrapping behavior, remove random_decider |
| `src/agents/agent.py` | Add `has_successful_actions` to workflow context |

---

## Implementation

### Phase 1: Create Bootstrapping Behavior
- Create `bootstrapping.yaml` with concrete first steps
- Escape JSON curly braces for format strings

### Phase 2: Update Agent Configs
- Add `bootstrapping` to all three agents' behaviors list
- Fix alpha_3 testing prompt to not test itself
- Remove random_decider from delta_3's workflow

### Phase 3: Add Context Variable
- Add `has_successful_actions` boolean to workflow context
- Agents can use this to know if they need bootstrapping

---

## Acceptance Criteria

- [ ] New agents execute query_kernel as first action (not noop)
- [ ] Agents read handbook within first 5 actions
- [ ] Agents attempt to write an artifact within first 10 actions
- [ ] No agent tries to invoke its own agent_id
- [ ] delta_3 doesn't noop 80% of the time
- [ ] `make test-quick` passes

---

## Verification

```bash
# Run short simulation
make run DURATION=60 AGENTS=3

# Check first actions are NOT noop
cat logs/latest/events.jsonl | jq -c 'select(.event_type == "action") | .intent.action_type' | head -10

# Verify query_kernel and read_artifact appear early
cat logs/latest/events.jsonl | jq -c 'select(.intent.action_type == "query_kernel" or .intent.action_type == "read_artifact")'
```
