# Prioritized Actions: Juice to Squeeze

**Status:** draft (pending discussion)
**Date:** 2026-01-17
**Based on:** 45 research sources + README goals review
**Related:** agent_architecture_synthesis.md, agent_architecture_research_notes.md

---

## Agent Ecology Goals (from README)

1. **Emergence over prescription** - No predefined roles, coordination emerges from scarcity
2. **Capital accumulation** - Artifacts build on artifacts, compounding value
3. **Observability** - Every action logged, every failure explicit
4. **Physics-first** - Real resource constraints drive behavior
5. **Minimal kernel, maximum flexibility** - Simple primitives, complex behaviors emerge

---

## Observed Problems

| Problem | Evidence | Root Cause |
|---------|----------|------------|
| **Cold-start deadlock** | 0 artifacts in 10 ticks | Agents search before creating; prompts say "check what exists first" |
| **Phantom artifact confusion** | Agents search for artifacts that don't exist | State summary had duplicate counting bug |
| **No iteration** | Can't retry/refine within tick | One action per tick model |
| **No planning** | Tick-by-tick reactive | No explicit goals/plans |
| **No learning** | Same mistakes repeated | No cross-tick memory synthesis |

---

## Prioritized Actions by Juice:Squeeze Ratio

### 🟢 Tier 1: High Juice, Low Squeeze (DO FIRST)

| # | Action | Juice | Squeeze | Why |
|---|--------|-------|---------|-----|
| **1.1** | Fix duplicate artifact bug | 🍋🍋🍋🍋🍋 | 🔧 | Bug causes phantom confusion. 5 lines of code. |
| **1.2** | Enable `reasoning_effort: "high"` | 🍋🍋🍋🍋 | 🔧 | Config change only. Anthropic uses extended thinking. |
| **1.3** | Add metacognition rules to prompts | 🍋🍋🍋🍋 | 🔧🔧 | "If empty world, create. If searched 3x, act." Breaks deadlock. |
| **1.4** | Restructure prompts: Goal + Context | 🍋🍋🍋🍋 | 🔧🔧🔧 | CrewAI pattern. Goals not rules. Medium effort (5 prompts). |

**Expected outcome:** Agents create artifacts within 3 ticks. Cold-start solved.

---

### 🟡 Tier 2: High Juice, Medium Squeeze (DO SECOND)

| # | Action | Juice | Squeeze | Why |
|---|--------|-------|---------|-----|
| **2.1** | Plan artifact pattern | 🍋🍋🍋🍋 | 🔧🔧🔧 | Agents write `{id}_plan`. No kernel change. Fits "everything is artifact". |
| **2.2** | Post-action reflection | 🍋🍋🍋🍋 | 🔧🔧🔧🔧 | Extra LLM call after action. Catches confusion early. |
| **2.3** | Experience base pattern | 🍋🍋🍋 | 🔧🔧🔧 | Agent Hospital: store successes + corrected failures. Dual buffer. |
| **2.4** | Reading/reasoning separation | 🍋🍋🍋 | 🔧🔧🔧 | StructGPT pattern. Agents first query, then decide. Reduces confusion. |

**Expected outcome:** Agents self-correct, build on successes, reason more effectively.

---

### 🟠 Tier 3: Medium Juice, Medium Squeeze (CONSIDER)

| # | Action | Juice | Squeeze | Why |
|---|--------|-------|---------|-----|
| **3.1** | Multi-action per tick (max 5) | 🍋🍋🍋 | 🔧🔧🔧🔧 | Enables iteration within tick. Risk: 5% failure compounds. |
| **3.2** | Read parallelization | 🍋🍋 | 🔧🔧🔧 | Multiple reads in parallel. Minor tick model change. |
| **3.3** | Composable action sequences | 🍋🍋🍋 | 🔧🔧🔧🔧 | Digimon KG pattern. Actions as operators, strategies as sequences. |

**Expected outcome:** More efficient agent execution, flexible strategies.

---

### 🔴 Tier 4: Variable Juice, High Squeeze (DEFER)

| # | Action | Juice | Squeeze | Why |
|---|--------|-------|---------|-----|
| **4.1** | Full agentic loop | 🍋🍋🍋🍋🍋 | 🔧🔧🔧🔧🔧 | Loop until done. Matches SOTA but 15x tokens, runaway risk. |
| **4.2** | Explicit memory actions | 🍋🍋 | 🔧🔧🔧🔧 | `store_memory`, `recall_memory`. Agents might not use. |
| **4.3** | Strategy navigator | 🍋🍋🍋 | 🔧🔧🔧🔧🔧 | Small model picks reasoning approach. Needs training data. |
| **4.4** | Multi-agent orchestration | 🍋🍋🍋🍋 | 🔧🔧🔧🔧🔧 | 15x tokens. Our single agents don't work yet. Fix those first. |

---

## Research Insights Applied

| Research | Key Pattern | Application |
|----------|-------------|-------------|
| **Anthropic** | Extended thinking, workflows before agents | 1.2, tier ordering |
| **CrewAI** | Role + Goal + Backstory | 1.4 prompt restructure |
| **Agent Hospital** | Case base + Experience base | 2.3 dual buffers |
| **StructGPT** | Read → Linearize → Reason → Iterate | 2.4 separation |
| **Digimon KG** | 19 composable operators | 3.3 action sequences |
| **VOYAGER** | Skill library, automatic curriculum | Future: emergent skills |
| **Reflexion** | Self-critique in episodic memory | 2.2 reflection |
| **MedAgentSim** | Start with nothing, actively gather | Change default behavior |

---

## Success Metrics

| Metric | Baseline | Tier 1 Target | Tier 2 Target |
|--------|----------|---------------|---------------|
| Artifact creation (5 ticks) | 0% | >20% | >40% |
| Cold-start time | Never | <3 ticks | <2 ticks |
| Confusion recovery | Never | <3 ticks | <2 ticks |
| Action diversity | 100% read/invoke | Include writes | Balanced |
| Self-correction | Never | Detects errors | Fixes errors |

---

## What NOT to Do

1. **Don't add multi-agent** - 15x tokens, single agents don't work yet
2. **Don't add frameworks** - We have direct LLM access, keep it simple
3. **Don't over-engineer tools** - We have 5 actions, that's fine
4. **Don't add everything at once** - Prove value at each step
5. **Don't prescribe strategies** - Let them emerge from the primitives

---

## Discussion Points

Before implementing any of these, we should discuss:

1. **Tier 1.1 (bug fix)** - Is this a real bug or by design?
2. **Tier 1.2 (reasoning_effort)** - System uses Gemini, not Anthropic. Need different approach?
3. **Tier 1.3-1.4 (prompts)** - These are architecture decisions. Need ADR?
4. **Overall approach** - Do we want to make agents "smarter" or observe emergence from current primitives?

The core question: **Is agent intelligence a kernel concern or should it emerge from agent self-modification?**
