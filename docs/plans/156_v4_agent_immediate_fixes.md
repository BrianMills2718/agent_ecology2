# Plan #156: V4 Agent Immediate Fixes

**Status:** in_progress
**Priority:** High
**Created:** 2026-01-22
**Branch:** plan-156-v4-agent-fixes
**Context:** V3 agents stuck in loops, missing action feedback. Fix immediate problems before considering deeper architectural changes (see Plan #155).

---

## Problem Statement

V3 agents exhibit dysfunctional behavior:
1. **Stuck in loops** - alpha_3 rewrote same artifact 34 times, gamma_3 35+ times
2. **Missing action feedback** - `solo_work` and `discover` prompts don't include `{last_action_result}`
3. **Fake state machine** - Transitions based on balance thresholds, not cognitive progress
4. **No history visibility** - Agents only see last action, can't detect "I've done this 20 times"

---

## Solution

Create a minimal test agent (v4_test) with:
1. **Action history** in prompt (last 15-20 actions with outcomes)
2. **No state machine** - just goal + state + history
3. **Clear economic rules** in system prompt
4. **All feedback variables** present

If this agent doesn't loop, we know the fix. Then decide whether to retrofit v3 or build v4.

---

## Design Decisions

### Action History Format
```
YOUR LAST 15 ACTIONS:
1. write_artifact("my_tool") → SUCCESS: Created artifact
2. write_artifact("my_tool") → SUCCESS: Overwrote artifact
3. write_artifact("my_tool") → SUCCESS: Overwrote artifact
4. invoke("genesis_store", "search") → SUCCESS: Found 3 artifacts
...
```

Simple, scannable. Agent should notice patterns (same action repeated).

### History Storage
- Store in agent's `action_history` list (in-memory during run)
- Optionally persist to working memory artifact
- Keep last 20, drop oldest when full

### Minimal Prompt Structure
```
You are {agent_id}. Your goal: maximize your scrip balance.

RULES:
- Earn scrip by: (1) mint auctions reward valuable artifacts, (2) others pay to invoke your services
- Spend scrip to: invoke others' artifacts, create artifacts
- Actions: read, write, edit, invoke, delete

YOUR STATE:
- Balance: {balance} scrip
- Your artifacts: {my_artifacts}
- Available artifacts: {available_artifacts}

YOUR LAST 15 ACTIONS:
{action_history}

Last action result: {last_action_result}

What do you do next? Think carefully - if you've tried something multiple times without progress, try a different approach.
```

No state machine. No phases. No "IDEATION TASK" instructions. Just goal + state + history.

---

## Implementation Steps

### Phase 1: Infrastructure
- [ ] Add `action_history` tracking to Agent class
- [ ] Add `_format_action_history()` method
- [ ] Update `_build_workflow_context()` to include history
- [ ] Make history depth configurable (default 15)

### Phase 2: Test Agent
- [ ] Create `src/agents/v4_test/` directory
- [ ] Create minimal `agent.yaml` with no state machine
- [ ] Create simple `system_prompt.md` with rules + history
- [ ] Ensure all context variables are present

### Phase 3: Validation
- [ ] Run single agent for 10 minutes: `make run DURATION=600 AGENTS=1`
- [ ] Check for loops (same artifact written >3 times)
- [ ] Check for progress (balance changes, unique artifacts created)
- [ ] Check for adaptation (different approach after failure)

### Phase 4: Decision
- If v4_test works: Document pattern, consider retrofitting v3 or replacing
- If v4_test still loops: Investigate further (model capability? prompt issues?)

---

## Success Criteria

| Metric | V3 Baseline | V4 Target |
|--------|-------------|-----------|
| Same artifact rewrites | 34+ | ≤3 |
| Unique artifacts created | ~3 | ≥5 |
| Adapts after failure | No | Yes (visible in logs) |
| 10-min run completes | Sometimes loops forever | Completes with activity |

---

## Test Plan

### Unit Tests
- `test_action_history_tracking` - history accumulates correctly
- `test_action_history_max_length` - old entries dropped
- `test_action_history_format` - renders correctly for prompt

### Integration Tests
- `test_v4_agent_loads` - agent loads without errors
- `test_v4_agent_proposes_action` - can propose actions

### E2E Validation
- Manual: Run 10-minute simulation, inspect logs for loops
- Check: `grep -c "write_artifact.*my_tool" run.jsonl` should be ≤3 for any artifact

---

## Files to Create/Modify

### Create
- `src/agents/v4_test/agent.yaml` - Minimal config, no state machine
- `src/agents/v4_test/system_prompt.md` - Simple prompt with rules

### Modify
- `src/agents/agent.py` - Add action_history tracking and formatting
- `config/schema.yaml` - Add `agent.action_history_depth` config

---

## Risks

1. **Model capability** - Even with history, model might not reason well about it
   - Mitigation: Try explicit instruction "if same action 3x, try different approach"

2. **Context bloat** - 15-20 actions might use too many tokens
   - Mitigation: Compact format, configurable depth

3. **History not the issue** - Loops might be caused by something else
   - Mitigation: This is a test - if it fails, we learn something

---

## References

- Plan #155: V4 Architecture Deferred Considerations (deeper changes if needed)
- `docs/simulation_learnings/agent_architecture_research_notes.md` (git: b34899d)
- Original loop analysis in conversation (alpha_3: 34 rewrites, gamma_3: 35+ rewrites)
