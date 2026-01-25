# Plan #212: Memory and Context Quality for Agent Learning

**Status:** Planned
**Priority:** High
**Complexity:** Medium
**Blocks:** Effective agent learning and strategic behavior

## Problem

Analysis of a simulation run revealed that agents have all the infrastructure for learning but it's not working effectively:

### Evidence from Simulation

1. **Mem0 stores garbage** - "Your Memories" section shows 7 identical action echoes
2. **Agent ignores loop warnings** - Pattern detection shows "15x same action" but agent continues
3. **Stuck on completed subgoal** - Agent keeps checking escrow after listing succeeded
4. **No strategic replanning** - Agent doesn't know what to do after achieving subgoal

### Root Cause

The cognitive architecture is flexible and capable. The problem is **genesis agent instantiation** - prompts and workflows don't effectively guide agents to USE the capabilities.

## Philosophy

**DO NOT change the architecture.** The architecture should remain infinitely flexible.

Instead, improve **genesis agent instantiation**:
- Add trait components that guide behavior
- Improve workflow prompts
- Update agent system prompts
- Add guidance to handbooks

This follows the project philosophy:
> "Emergence over prescription - No predefined roles; agents build what they need"
> "Genesis as cold-start conveniences - unprivileged, agents could build equivalents"

## Solution

### Phase 1: Memory Discipline Trait

**File:** `src/agents/_components/traits/memory_discipline.yaml`

Create a new trait that teaches agents HOW to use memory effectively:

```yaml
name: memory_discipline
type: trait
version: 1
description: "Guides agents to store insights, not raw actions"

inject_into:
  - reflect
  - reflecting
  - review
  - reviewing
  - strategic_reflect

prompt_fragment: |

  === MEMORY DISCIPLINE (memory_discipline trait) ===
  Your working memory is your long-term learning system. Use it WISELY.

  WHAT TO STORE (insights):
  - LESSONS from failures: "deposit requires transfer_ownership first"
  - PATTERNS that work: "artifacts with clear interfaces sell better"
  - STRATEGIC INSIGHTS: "alpha_3 builds note tools - I should build something different"

  WHAT NOT TO STORE (noise):
  - Raw action logs: "I performed invoke_artifact..."
  - Routine checks: "I checked escrow listings"
  - Obvious facts: "I have 95 scrip"

  MEMORY UPDATE TRIGGERS:
  - After a FAILURE: Record the lesson learned
  - After a SUCCESS: Record what made it work
  - After 5+ actions: Synthesize what you've learned

  When updating working_memory, ask: "Will future-me find this useful?"

requires_context:
  - working_memory
  - failure_history
```

### Phase 2: Loop Breaker Trait

**File:** `src/agents/_components/traits/loop_breaker.yaml`

Create a trait that helps agents recognize and escape loops:

```yaml
name: loop_breaker
type: trait
version: 1
description: "Helps agents recognize and escape repetitive patterns"

inject_into:
  - observe
  - observing
  - reflect
  - reflecting
  - operational_execution

prompt_fragment: |

  === LOOP DETECTION (loop_breaker trait) ===
  Check your "Recent Actions" section above. If you see the SAME action repeated:

  3x SAME ACTION = Yellow flag. Ask: "Am I making progress?"
  5x SAME ACTION = Red flag. You MUST try something DIFFERENT.

  COMMON LOOPS AND ESCAPES:
  - "Checking status repeatedly" → STOP checking. Take action or move on.
  - "Waiting for buyer" → Don't wait passively. Build something else.
  - "Retrying failed action" → Read the error. Change your approach.
  - "Reading same artifact" → You already know what's in it. Decide and act.

  ESCAPE STRATEGIES:
  1. Update your subgoal in working_memory
  2. Try a completely different action type
  3. Work on a different artifact
  4. Submit something to mint (always productive)

  Remember: Repeating the same action hoping for different results is not strategy.

requires_context:
  - action_history
```

### Phase 3: Subgoal Progression Trait

**File:** `src/agents/_components/traits/subgoal_progression.yaml`

Create a trait that encourages subgoal management:

```yaml
name: subgoal_progression
type: trait
version: 1
description: "Guides agents to track and update subgoals"

inject_into:
  - reflect
  - reflecting
  - review
  - reviewing
  - strategic
  - tactical

prompt_fragment: |

  === SUBGOAL MANAGEMENT (subgoal_progression trait) ===
  Check your working_memory for `current_subgoal`. Ask yourself:

  IS MY SUBGOAL COMPLETE?
  - "List artifact for sale" + listing exists = DONE → set new subgoal
  - "Build X" + X exists and works = DONE → set new subgoal
  - "Wait for Y" is NOT a good subgoal. Waiting is passive. What can you DO?

  GOOD SUBGOALS (actionable, measurable):
  - "Create an artifact that fetches weather data"
  - "Submit my_tool to mint auction"
  - "Purchase alpha_3's note_search to learn from it"

  BAD SUBGOALS (vague, passive):
  - "Wait for someone to buy my artifact"
  - "Make money"
  - "Build something useful"

  SUBGOAL LIFECYCLE:
  1. Set specific, actionable subgoal
  2. Take actions toward it
  3. Recognize when DONE
  4. Record lessons learned
  5. Set NEXT subgoal

  If stuck on a subgoal for 10+ actions, it's time to PIVOT.

requires_context:
  - working_memory
  - action_history
```

### Phase 4: Update Genesis Agent Configs

**Files:** `src/agents/alpha_3/agent.yaml`, `src/agents/beta_3/agent.yaml`, `src/agents/delta_3/agent.yaml`

Add the new traits to each genesis agent:

```yaml
components:
  traits:
    - buy_before_build
    - economic_participant
    - memory_discipline      # NEW
    - loop_breaker           # NEW
    - subgoal_progression    # NEW
```

### Phase 5: Update Handbook

**File:** `src/world/genesis/handbook/handbook_learning.md` (new)

Create a handbook artifact that agents can read for learning guidance:

```markdown
# Learning Handbook

## How to Use Your Memory

Your working memory (`{agent_id}_working_memory`) is your long-term brain.

### Writing Good Memories
```yaml
working_memory:
  current_goal: "Specific, measurable goal"
  current_subgoal: "Immediate actionable step"
  lessons:
    - "Insight that will help future decisions"
    - "Pattern I noticed that works/doesn't work"
  completed_subgoals:
    - "What I've achieved so far"
```

### Common Mistakes
- Storing "I did X" instead of "I learned Y"
- Never updating subgoal after completing it
- Setting vague goals like "make money"

## How to Escape Loops

If your recent actions are all the same:
1. STOP and reflect
2. Update your working_memory with what you learned
3. Set a NEW subgoal
4. Try a DIFFERENT action type
```

## Files Modified

| File | Change |
|------|--------|
| `src/agents/_components/traits/memory_discipline.yaml` | NEW - memory guidance trait |
| `src/agents/_components/traits/loop_breaker.yaml` | NEW - loop detection trait |
| `src/agents/_components/traits/subgoal_progression.yaml` | NEW - subgoal management trait |
| `src/agents/alpha_3/agent.yaml` | Add new traits to components |
| `src/agents/beta_3/agent.yaml` | Add new traits to components |
| `src/agents/delta_3/agent.yaml` | Add new traits to components |
| `src/world/genesis/handbook/handbook_learning.md` | NEW - learning guidance handbook |

## What This Does NOT Change

- `src/agents/memory.py` - Architecture stays flexible
- `src/agents/agent.py` - No hardcoded behaviors
- `src/agents/workflow.py` - No forced interventions
- `config/schema.yaml` - No new system-level configs

## Testing

1. Run simulation with updated genesis agents
2. Verify trait prompts appear in LLM logs
3. Check that agents update working_memory more frequently
4. Verify agents break out of loops (max consecutive same action ≤5)
5. Verify agents set new subgoals after completing old ones

## Acceptance Criteria

- [ ] Three new trait files created and valid YAML
- [ ] Genesis agents include new traits in config
- [ ] Handbook artifact created
- [ ] Simulation shows improved behavior:
  - [ ] Working memory contains insights, not action echoes
  - [ ] Agents break loops within 5 repetitions
  - [ ] Agents update subgoals multiple times per run

## Success Metrics

| Metric | Before | Target |
|--------|--------|--------|
| Max consecutive identical actions | 15+ | ≤5 |
| Working memory updates per agent | ~2 | 5+ |
| Subgoal changes per agent | ~1 | 3+ |

## Why This Approach

From project philosophy:
- **Emergence over prescription**: Traits GUIDE, they don't FORCE
- **Minimal kernel, max flexibility**: Architecture unchanged
- **Genesis as conveniences**: Other agents could ignore these traits or build better ones

The architecture remains infinitely flexible. We're just making the default genesis agents smarter about using it.
