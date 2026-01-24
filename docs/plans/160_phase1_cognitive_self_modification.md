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

**All config is modifiable** - including `llm_model`. Economic constraints (scrip, LLM budget) are enforced by the ledger/resource system, not by restricting config changes. If an agent changes to an expensive model, their budget limits still apply.

**Note on scrip:** `starting_scrip` in config is only the initial value credited at simulation start. Actual scrip balance lives in the ledger - agents cannot give themselves more scrip because the ledger doesn't expose `credit_scrip` to them.

**Frictionless loading:** Config/prompt artifacts are loaded automatically into agent context at cycle start. Agent doesn't need to call `read_artifact` - the loader handles this. Changes take effect on next action cycle.

**Why:** Let agent experiment with its own cognition. Economic constraints enforced by resource system, not config restrictions.

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

- src/agents/agent.py (modify) - Metacognitive prompt, action pattern analysis, economic context
- src/agents/schema.py (modify) - Clarify interface requirements for executables
- src/agents/alpha_3/agent.yaml (modify) - Add economic context to workflow prompts
- src/world/world.py (modify) - Create config artifacts at init, self-invoke feedback
- src/world/artifacts.py (modify) - Improve success feedback messages
- src/world/genesis/escrow.py (modify) - Improve error messages with type diagnostics
- src/world/genesis/ledger.py (modify) - Improve transfer method error clarity
- src/agents/loader.py (modify) - Check for config override artifacts
- .claude/hooks/check-file-scope.sh (modify) - Fix worktree path pattern
- docs/architecture/current/agents.md (modify) - Update verification date
- docs/architecture/current/execution_model.md (modify) - Update verification date
- docs/architecture/current/contracts.md (modify) - Clarify kernel defaults vs cold-start conveniences
- docs/architecture/current/genesis_artifacts.md (modify) - Note that genesis contracts are separate category
- docs/architecture/current/artifacts_executor.md (modify) - Update verification date
- CLAUDE.md (modify) - Clarify genesis artifacts heuristic
- src/agents/alpha_3/system_prompt.md (modify) - Add self-modification hints
- src/agents/beta_3/system_prompt.md (modify) - Add self-modification hints
- src/agents/gamma_3/system_prompt.md (modify) - Add self-modification hints
- src/agents/delta_3/system_prompt.md (modify) - Add self-modification hints
- src/agents/epsilon_3/system_prompt.md (modify) - Add self-modification hints

---

## Rollback

If this makes things worse, revert to previous prompt structure. Changes are isolated to prompt construction and artifact creation.
