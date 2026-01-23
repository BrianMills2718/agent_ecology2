# Plan #160: Phase 1 - Cognitive Self-Modification

**Status:** In Progress
**Priority:** High
**Goal:** Test whether limited self-modification ability improves agent intelligence

---

## Context

This is Phase 1 of a phased approach to determine whether we need the full #155 refactor (agents as patterns). Each phase gathers evidence:

- **Phase 1 works** → Maybe we don't need #155
- **Phase 1 fails** → Move to Phase 2 (cognitive patterns as artifacts)
- **Phase 2 fails** → Full #155 or rethink

---

## Phase 1 Components

### 1. Agent Config as Readable Artifact

**Current:** Agent config loaded from `agent.yaml`, agent can't see it.

**Change:** Create `{agent_id}_config` artifact at init containing agent's config. Agent can read it to understand its own setup.

**Why:** Agent needs self-awareness to self-modify. Can't improve what you can't see.

### 2. Config Self-Modification

**Current:** Config is fixed at startup.

**Change:** If agent writes to `{agent_id}_config`, those values override base config on next action cycle.

**Modifiable parameters (safe to change):**
- `working_memory` - lessons, heuristics, goals
- `preferences` - strategies, priorities
- `self_imposed_rules` - agent's own rules it creates

**Not modifiable (safety):**
- `llm_model` - resource implications
- `starting_scrip` - economic integrity

**Why:** Let agent experiment with its own cognition within bounds.

### 3. Metacognitive Prompting

**Current:** Prompt asks for action directly.

**Change:** Add metacognitive section before action:
```
## Before Acting
Briefly assess:
1. Are my recent actions making progress toward my goal?
2. If I've tried the same approach multiple times without success, what should I try instead?
3. Should I update my working memory with any lessons learned?
```

**Why:** Encourage reflection without forcing it. Agent chooses whether to act on the assessment.

### 4. Action Pattern Analysis

**Current:** Shows action history but doesn't analyze patterns.

**Change:** Analyze action history and show:
- Which actions are being repeated (3+ times)
- Success/failure rate per action pattern
- Prompt agent to evaluate if repeated actions are working

**Why:** Make patterns visible so agent can self-evaluate. No enforcement, just information.

---

## Implementation Order

1. **Metacognitive prompting** - Simplest, just prompt changes
2. **Action pattern analysis** - Prompt changes + analysis method
3. **Config as artifact** - World init changes
4. **Config self-modification** - Agent loader changes

---

## Success Criteria

Run simulation and check:
- [ ] Agent doesn't repeat same failing action 10+ times
- [ ] Agent updates working memory with lessons
- [ ] Agent tries different strategies when one isn't working
- [ ] No hardcoded enforcement rules in our code

---

## Non-Goals

- No hardcoded loop detection/blocking
- No forced reflection triggers
- No action rejection based on rules we write
- Agent decides its own behavior based on better information

---

## Files Affected

- src/agents/agent.py (modify) - Metacognitive prompt, action pattern analysis
- src/world/world.py (modify) - Create config artifacts at init
- src/agents/loader.py (modify) - Check for config override artifacts
- .claude/hooks/check-file-scope.sh (modify) - Fix worktree path pattern

---

## Rollback

If this makes things worse, revert to previous prompt structure. Changes are isolated to prompt construction and artifact creation.
