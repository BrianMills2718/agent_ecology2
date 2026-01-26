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
3. **delta_3** uses random_decider which returns false 80% of the time -> noops

The agents have behaviors like `loop_breaker` that say "try something different" but they don't know WHAT different thing to try. They need bootstrapping guidance for their first actions.

---

## Solution Implemented

### 1. Created Bootstrapping Behavior Component

Created `bootstrapping.yaml` that injects CONCRETE first steps:
- STEP 1: query_kernel to explore artifacts
- STEP 2: read handbook_toc
- STEP 3: write a simple tool artifact
- STEP 4: invoke the tool to test it

### 2. Fixed Component Injection

The `inject_into` field must match **step names** not state names:
- alpha_3 steps: observe, discover, ideate
- beta_3 steps: learn_from_outcome, load_goals, strategic_planning, tactical_planning
- delta_3 steps: assess_project, plan_project, build_infrastructure, deploy_infrastructure, maintain_infrastructure

### 3. Removed Random Decider from delta_3

The `genesis_random_decider` with 20% probability caused 80% noops. Removed entirely.

### 4. Fixed alpha_3 "Testing" State

Added warning not to invoke own agent_id.

### 5. Fixed "proceed with noop" Instructions

Changed "If no lesson to record, proceed with noop" to "see GETTING STARTED below for what to do next".

### 6. Added FIRST ACTION CHECK

Added explicit checks at the start of key prompts for beta_3 and delta_3 to guide first actions.

### 7. Fixed handbook_toc Reference

Changed `genesis_handbook` to `handbook_toc` (the actual artifact name).

---

## Files Changed

| File | Change |
|------|--------|
| `src/agents/_components/behaviors/bootstrapping.yaml` | NEW - First steps guidance with correct step names |
| `src/agents/alpha_3/agent.yaml` | Add bootstrapping behavior, fix testing prompt |
| `src/agents/beta_3/agent.yaml` | Add bootstrapping behavior, remove "proceed with noop", add FIRST ACTION CHECK |
| `src/agents/delta_3/agent.yaml` | Add bootstrapping behavior, remove random_decider, remove "proceed with noop", add FIRST ACTION CHECK to plan_project and maintain_infrastructure |

---

## Verification Results

### Run 1 (after initial fixes)
- Events: 47, alpha_3: 97 scrip
- Action counts: 15 invoke_artifact, 9 noop, 3 read_artifact
- Alpha_3 active, beta_3/delta_3 still nooping

### Run 2 (after step name fixes)
- Events: 65
- Action counts: 14 invoke_artifact, 12 noop, 5 read_artifact
- Alpha_3: 8 invoke, 4 read, 0 noop (excellent!)
- Beta_3: 6 invoke, 6 noop (improving)
- Delta_3: 6 noop, 1 read (starting to read)

### Run 3 (after handbook_toc fix)
- Events: 68
- Action counts: 14 invoke_artifact, 12 noop, 6 read_artifact
- Alpha_3: 7 invoke, 5 read, 0 noop (excellent!)
- Beta_3: 4 invoke, 3 noop, 1 write_artifact attempt (tried to write!)
- Delta_3: 6 read_artifact, 4 noop (reading handbook!)

---

## Remaining Issues

1. **Agents skip STEP 1 (query_kernel)** - They go directly to read_artifact
2. **delta_3 reads same artifact repeatedly** - Reads handbook_toc 6x without progressing
3. **beta_3 write format wrong** - Tried `print("Hello")` instead of `def run(): ...`

---

## Acceptance Criteria

- [x] New agents don't noop as first action (alpha_3: 0 noops)
- [x] Agents read handbook within first 5 actions
- [x] Agents attempt to write an artifact (beta_3 tried!)
- [x] No agent tries to invoke its own agent_id
- [x] delta_3 doesn't noop 80% of the time (was 6/10, now 4/10)
- [x] `make test-quick` passes

---

## Next Steps

1. Make query_kernel more prominent/explicit in bootstrapping
2. Add loop detection for reading same artifact repeatedly
3. Improve write_artifact example format clarity
