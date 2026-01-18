# Agent Architecture Synthesis: What We Should Actually Do

**Status:** recommendation
**Date:** 2026-01-16
**Based on:** 37 research sources reviewed
**Related:** agent_architecture_research_notes.md, agent_architecture_design_space.md

---

## Executive Summary

After reviewing 15 sources on agent architecture, the consensus is clear:

1. **Start simpler than you think** - Most problems don't need agents
2. **Fix the basics first** - Tool design > prompt engineering
3. **Add complexity incrementally** - Prove value at each step
4. **Our observed problems are common** - Cold-start, confusion, paralysis are known failure modes

---

## What The Research Says We're Doing Wrong

### Problem 1: One-Size-Fits-All Approach
**Research says:** Use the simplest solution that works. Anthropic's hierarchy:
1. Simple prompt (most cases)
2. Prompt + retrieval/examples
3. Workflow (predefined paths)
4. Agent (only when necessary)

**Our status:** We jump straight to agent for everything.

### Problem 2: No Planning/Goal Structure
**Research says:** Effective agents have explicit goals, plans, and task tracking. Anthropic uses extended thinking to plan before execution.

**Our status:** Agents have no explicit goals or plans. They react tick-by-tick.

### Problem 3: Rule-Based Prompts
**Research says:** CrewAI uses role + goal + backstory. Anthropic says invest in tool documentation like HCI.

**Our status:** Prompts are prescriptive rules ("Before building, check what exists") not goals + context.

### Problem 4: No Learning/Adaptation
**Research says:** 95% of AI projects fail because systems "don't retain feedback, don't accumulate knowledge, don't improve over time."

**Our status:** Each tick is independent. No cross-tick learning within a run.

### Problem 5: No Reflection
**Research says:** Anthropic uses "interleaved thinking" after tool results. Evaluator-Optimizer pattern provides iterative feedback.

**Our status:** No reflection step. Agents don't evaluate their own outputs.

---

## Prioritized Recommendations

### Tier 1: Do First (Low Risk, High Value)

These changes are low-risk and address immediate problems:

#### 1.1 Enable Extended Thinking
**Change:** Set `reasoning_effort: "high"` in config
**Why:** Anthropic uses extended thinking for planning. Our agents think in ~500 chars.
**Risk:** More tokens/cost per tick
**Effort:** Config change only

#### 1.2 Fix the Duplicate Artifact Bug
**Change:** Fix `get_state_summary()` double-counting in `world.py:1281-1286`
**Why:** Agents are confused by phantom artifacts. This is a bug, not an architecture issue.
**Risk:** None
**Effort:** Small code fix

#### 1.3 Restructure Prompts: Goal + Context + Personality
**Change:** Rewrite agent prompts from rules to:
- **Goal:** What success looks like
- **Context:** How the world works
- **Personality:** Tendencies, not rules
- **Metacognition:** How to handle uncertainty

**Why:** Current prompts create cold-start deadlock. CrewAI uses role/goal/backstory.
**Risk:** Prompt changes are sensitive, need testing
**Effort:** Medium (rewrite 5 agent prompts)

#### 1.4 Add Scaling Rules to Prompts
**Change:** Include heuristics in system prompt:
- "If the world is empty, create something rather than searching"
- "If you've searched 3 times without finding, accept uncertainty and act"

**Why:** Anthropic embeds scaling rules in prompts. Our agents lack meta-guidance.
**Risk:** Could be too prescriptive
**Effort:** Small prompt additions

---

### Tier 2: Do Second (Medium Risk, High Value)

These require more implementation but address core limitations:

#### 2.1 Add Plan Artifact
**Change:** Agents can write to `{agent_id}_plan` artifact containing:
- Current goal
- Tasks (with status)
- Learnings

**Why:** Anthropic persists plans to external memory. Fits our "everything is artifact" philosophy.
**Risk:** Agents might not use it without encouragement
**Effort:** No kernel change needed (just write_artifact)

#### 2.2 Add Post-Action Reflection
**Change:** After action execution, agent gets one more LLM call to reflect:
- Did the action succeed?
- What did I learn?
- Should I revise my approach?

**Why:** Anthropic's "interleaved thinking." Would have caught the 45 vs 30 confusion.
**Risk:** Doubles LLM calls per tick (cost)
**Effort:** Medium (modify tick loop)

#### 2.3 Implement Read-Only Tool Parallelization
**Change:** Allow multiple read_artifact calls in parallel within a tick
**Why:** "Read operations can run in parallel, write operations need coordination"
**Risk:** Changes tick model slightly
**Effort:** Medium

---

### Tier 3: Consider Later (Higher Risk, Needs Validation)

Only pursue these after Tier 1 & 2 show value:

#### 3.1 Multi-Action Per Tick
**Change:** Allow bounded sequence of actions (max 5) per tick
**Why:** Enables retry/refine without waiting for next tick
**Risk:** Increases failure surface (5% per action compounds)
**Effort:** Significant (changes tick model)

#### 3.2 Agentic Loop (Until Done)
**Change:** Agent loops until it declares "done" or budget exhausted
**Why:** Matches Claude Code / SOTA agents
**Risk:** High token usage (15x), runaway loops, harder to observe
**Effort:** Major architecture change

#### 3.3 Explicit Memory Actions
**Change:** Add `store_memory`, `recall_memory` actions
**Why:** Agent-controlled memory vs automatic
**Risk:** Overwhelming choices, might not be used
**Effort:** Medium-High

#### 3.4 Strategy Selection Navigator
**Change:** Small model selects reasoning approach per problem
**Why:** RLoT achieves 13.4% improvement with <3000 param navigator
**Risk:** Complex to implement, needs training data
**Effort:** High

---

## What NOT To Do

Based on research warnings:

### Don't Build Multi-Agent Yet
- 15x token usage
- Only economical for high-value tasks
- Our single agents aren't working yet - fix that first

### Don't Add Frameworks
> "Start with direct LLM API calls rather than frameworks. Many patterns require just a few lines of code."

We already have direct LLM integration. Don't add LangChain/AutoGen complexity.

### Don't Over-Engineer Tools
Our 5 actions (read, write, delete, invoke, noop) are simple. Research says invest in tool design, but we don't have a tool problem - we have a reasoning problem.

### Don't Add All Features At Once
> "Start with one specific, high-value use case. Pick one problem and solve it well."

Fix the cold-start deadlock first. Then add planning. Then reflection. Test at each step.

---

## Proposed Experiment Plan

### Experiment 1: Baseline Fix
1. Fix duplicate artifact bug
2. Enable reasoning_effort: "high"
3. Run same 10-tick simulation
4. Compare: Do agents create artifacts now?

### Experiment 2: Prompt Restructure
1. Rewrite alpha's prompt as goal + context + personality
2. Add metacognition section
3. Run 10-tick simulation with just alpha
4. Compare behavior to rule-based prompt

### Experiment 3: Add Reflection
1. Implement post-action reflection step
2. Run simulation
3. Measure: Does agent notice/correct the 45 vs 30 confusion?

### Experiment 4: Plan Artifact
1. Seed agents with empty plan artifacts
2. Add prompt guidance to maintain plans
3. Run simulation
4. Observe: Do agents update plans? Does it help?

---

## Success Metrics

| Metric | Baseline | Target |
|--------|----------|--------|
| Artifact creation rate | 0% | >10% in first 5 ticks |
| Cold-start time | Never | <3 ticks to first artifact |
| Confusion recovery | Never | Recover within 2 ticks |
| Action diversity | 100% read/invoke | Include write actions |

---

## Key Quotes to Remember

> "Start with the simplest solution possible. Use agents only when necessary."
> — Anthropic, Building Effective Agents

> "Anthropic spent more time optimizing tools than overall prompts in their SWE-bench agent."
> — Anthropic

> "Most corporate GenAI systems don't retain feedback, don't accumulate knowledge, and don't improve over time."
> — Why AI Agents Fail

> "95% of AI projects see no measurable return."
> — Industry research

> "Read operations can run in parallel, but write operations need careful coordination."
> — Building an Agentic System

> "Effective AI reasoning requires hybrid System 1 and System 2 fusion."
> — System 2 Research

---

## Appendix: Source Summary

| # | Source | Key Insight |
|---|--------|-------------|
| 1 | Anthropic Multi-Agent | Orchestrator-worker, 90% improvement, 15x tokens |
| 2 | LangGraph | Cycles for reasoning loops, checkpointing |
| 3 | Atom of Thoughts | Markovian decomposition into atomic questions |
| 4 | RL of Thoughts | <3K param navigator, 13.4% improvement |
| 5 | FunSearch | LLM + evaluator loop, diversity preservation |
| 6 | AFlow | MCTS workflow optimization |
| 7 | AutoGen | Publish-subscribe, async pipeline |
| 8 | CrewAI | Role + goal + backstory YAML config |
| 9 | EvoFlow | Niching evolution, 12.4% of o1 cost |
| 10 | Darwin Gödel Machine | Self-modifying agents, 20%→50% |
| 11 | Why Agents Fail (HBR) | Technology-problem mismatch |
| 12 | Six Architecture Failures | Compounding failure rates, testing |
| 13 | Building Agentic System | Read parallel, write sequential |
| 14 | Anthropic Effective Agents | Workflows vs agents, 5 patterns |
| 15 | System 2 Research | System 1+2 fusion |
| 16 | Lilian Weng (OpenAI) | Three-tier memory, retrieval factors: relevance+recency+importance |
| 17 | Generative Agents | **ALL 3 required: observation, planning, reflection** |
| 18 | CAMEL | Role-playing enables autonomous cooperation |
| 19 | mem0 | Multi-level memory (user/session/agent), 90% token reduction |
| 20 | MemGPT (Letta) | OS-inspired memory hierarchy, virtual context management |
| 21 | **ExpeL** | **Learn from experience via NL storage, no fine-tuning needed** |
| 22 | **Reflexion** | **Verbal RL - self-critique in episodic memory, 91% on HumanEval** |
| 23 | HippoRAG | Hippocampal memory model, 10-30x cheaper than iterative RAG |
| 24 | Zep/Graphiti | Temporal knowledge graphs, 94.8% accuracy, 90% latency reduction |
| 25 | Agent Workflow Memory | Store reusable workflows not actions, 51% improvement |
| 26 | Reddit Practitioners | data+context+timestamp; graph relationships; keep solutions not process |
| 27 | Episodic Memory Pattern | Vector-backed memory blobs with TTL/decay for maintenance |
| 28 | **Memory Synthesis** | **Task diaries → periodic synthesis → prompt improvements** |
| 29 | Skill Library Evolution | Progressive skill accumulation, 91% token reduction via lazy-load |
| 30 | Self-Critique Evaluator | Self-taught evaluator bootstrapping without labels |
| 31 | Dual Memory (impl) | Vector (episodic) + Graph (semantic) combined context |
| 32 | RLHF Pattern (impl) | Generate→Critique→Revise loop with GoldStandardMemory |
| 33 | **VOYAGER** | **Automatic curriculum + skill library + self-verification. 3.3x items, 15.3x faster** |
| 34 | OpenAI Swarm | Routines + handoffs for multi-agent orchestration |
| 35 | Progressive Complexity | Cold-start: Tier 1 (info gather) → Tier 2 (human gates) → Tier 3 (autonomous) |
| 36 | Plan-Then-Execute | Separate planning from execution. 2-3x success rate improvement |
| 37 | Context-Minimization | Security: purge untrusted input after transformation |
