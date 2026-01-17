# Agent Paralysis: No Artifact Creation in 10 Ticks

**Status:** open
**Date:** 2026-01-16
**Simulation:** runs/test_long_run.jsonl
**Related:** Plan #59 (Agent Intelligence Patterns)

---

## What Happened

Ran 10-tick simulation with 3 agents (alpha, beta, gamma). Results:
- 765 invoke_artifact actions
- 717 read_artifact actions
- 0 write_artifact actions

No agent created anything. They spent all 10 ticks searching and invoking genesis artifacts.

---

## Bug Found: Duplicate Artifact Count

Agents saw "45 artifacts (15 genesis, 15 executable, 15 data)" but only 30 actually exist.

**Root cause:** `src/world/world.py` lines 1281-1286. The `get_state_summary()` method:
1. Gets artifacts from store (30 total, includes genesis)
2. Then loops over `genesis_artifacts.values()` and adds them again (+15)
3. Result: 45 with 15 duplicates

Agents noticed the discrepancy ("I found none but system says 45 executables") but instead of accepting uncertainty and building something, they kept searching for the phantom executables.

**Fix needed:** Remove the double-counting in `get_state_summary()`.

---

## Deeper Problem: Trivial Confusion Breaks Everything

The duplicate count is a bug, but the more concerning issue: such a trivial piece of confusing information broke all 3 agents for 10 ticks.

If agents can't handle "the system says X but I observe Y, I'll proceed anyway" - they lack the rational ignorance / uncertainty tolerance needed for real-world operation.

This points to a **general intelligence problem**, not just a data bug. Band-aid fixes (specific rules for each failure case) won't scale.

---

## Cold-Start Deadlock in Prompts

Examined agent prompts and found a structural problem:

**Alpha's prompt:** "Before building anything, you check what already exists"
**Beta's prompt:** "When others build primitives, you wire them together"

This creates a waiting cycle:
- Alpha waits to see what exists before building
- Beta waits for others to build primitives
- Everyone waits -> nobody creates -> nothing exists -> repeat

**The problem:** These prompts are **rule-sets** (prescriptive instructions for specific situations) rather than **goal + context** (what you're trying to achieve + background to reason from).

Rule-set prompts don't adapt to novel situations. When the rules conflict with reality (nothing exists yet), agents get stuck.

**Desired state:** Prompts that give agents:
- Clear goals (what success looks like)
- Context (how the world works, what resources exist)
- Personality/tendencies (not rigid rules)
- Metacognitive guidance (how to handle uncertainty, when to act vs. gather info)

---

## Thinking Mode Configuration

Discovered that LiteLLM defaults Gemini 3 to `reasoning_effort="low"`.

For agents making strategic decisions under uncertainty, we probably want "high" - but this should be configurable per-agent.

Current config doesn't expose this. Need to add to agent.yaml schema.

---

## Architecture Limitations Identified

Current agent architecture has fundamental constraints:

| Limitation | Current State | What SOTA agents have |
|------------|---------------|----------------------|
| Actions per tick | 1 (forced choice) | Agentic loop until goal met |
| Planning | None | TodoWrite, goals, sub-tasks |
| Memory control | Automatic (agent can't control) | Explicit store/retrieve |
| Reflection | None | Self-critique, plan revision |
| Sub-agents | None | Task delegation |

**Current actions (5 total):** noop, read_artifact, write_artifact, delete_artifact, invoke_artifact

**Missing actions for intelligent behavior:**
- update_plan / set_goals / mark_task_complete
- store_memory / recall_memory (agent-controlled)
- self_critique / revise_approach

The one-action-per-tick model forces agents to act before they can iterate on understanding. Compare to Claude Code which can use multiple tools, reflect, and loop until the task is done.

---

## Questions / Uncertainties

1. How much of the paralysis was the bug (fixable) vs architecture (needs redesign)?
   - Should run same simulation after fixing duplicate count to isolate

2. Can prompt restructuring (goal+context vs rules) help within current architecture?
   - Or does one-action-per-tick doom any prompt approach?

3. What's the minimal architecture change that would enable agentic behavior?
   - Multi-action per tick?
   - Or full agentic loop (run until goal/budget exhausted)?

4. Should thinking mode be per-agent or global?
   - Different agents might benefit from different reasoning depths

---

## Next Steps

- [ ] Fix duplicate artifact bug in `get_state_summary()`
- [ ] Re-run simulation to isolate bug impact vs structural issues
- [ ] Draft YAML-ized prompt structure (goal/personality/metacognition sections)
- [ ] Prototype planning action (even if just writing to a `{agent}_plan` artifact)
- [ ] Investigate architecture options for multi-action or agentic loop
