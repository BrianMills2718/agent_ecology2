# Plan #155: V4 Architecture - Deferred Considerations

**Status:** 📋 Deferred
**Priority:** low (until v3 fixes validated)
**Created:** 2026-01-22
**Context:** Extended discussion about fundamental architecture changes. Deferred to focus on immediate v3 fixes first.

---

## Summary

This plan captures insights, questions, and considerations from a deep architectural discussion. The core insight is that **agents are not special entities but patterns of artifact activity with LLM calls in a cybernetic loop**. This reframes the entire system but requires significant changes. We're deferring this to first validate that simpler v3 fixes (action history, prompt fixes) solve the immediate problems.

---

## Core Insight: Agents as Patterns

### Current (Problematic) Model
- Agent is a special entity with system_prompt, memory, workflow
- Agent exists somewhat outside the artifact system
- Special `Agent` class with privileged LLM access

### Proposed Model
- **Everything is artifacts**
- "Agent" = a recurring pattern of artifact activity that includes LLM invokes
- No special Agent class - just artifacts with particular behavior
- Intelligence = patterns of artifact activity at any scale

### Implications
- No clear distinction between agents, firms, or collective
- Measurement of emergence through pattern metrics
- Same ownership/access semantics for everything

---

## LLM Access Through Invoke

### Current State
- Agents call `self.llm.generate()` directly
- Bypasses artifact/invoke system
- Not observable in same way as actions

### Proposed Change
- LLM access via `invoke(llm_gateway, "complete", prompt)`
- Thinking becomes observable artifact activity
- Enables:
  - Market for LLM access (wrappers, caches, optimizers)
  - Unified observability
  - Contract-based access control on thinking
  - Multiple competing gateways

### Tradeoffs
| For | Against |
|-----|---------|
| Unified system | Minor additional indirection |
| Observable thinking | Gateway becomes "special" in a way |
| Markets can emerge | Complexity |
| Pattern metrics include thinking | |

### Decision
Likely worth doing. Latency cost is negligible (microseconds vs seconds for LLM call). Emergence potential is high.

---

## Contract/Access Control Model

### Current Model
- Kernel enforces contracts before every action
- Contracts are special (checked by kernel)
- Separation of policy from code

### Considerations

**Why kernel enforcement?**
- Artifacts can't bypass their own contracts
- Uniform enforcement
- But: Doesn't protect against malicious code, just boundary violations

**Alternative: Self-enforcement**
- Artifacts handle their own access in their code
- Kernel just routes, doesn't check
- More flexible, simpler kernel
- But: Artifacts could skip checks (intentionally or bugs)

**Key Insight from User**
- Ownership has no privileged meaning (Ostrom-inspired)
- Though possibly reconsider: ownership = all methods access as default?

### Pragmatic Hybrid Decided
- Kernel provides primitives with sensible defaults
- `read` → returns content (unless artifact overrides)
- `write` → replaces content (unless artifact overrides)
- `edit` → patches content (unless artifact overrides)
- `delete` → kernel removes artifact (special, not invoke)
- `invoke` → calls method on executable artifact
- Access control: default owner-only, artifacts override as needed
- No mandatory kernel-enforced contracts

---

## Kernel Responsibilities (Minimal)

### Kernel MUST Do (only kernel can)
- Storage (artifacts can't store themselves)
- Execution (run artifact code)
- Resource metering (can't trust self-reporting)
- Delete (affects existence, can't invoke deleted artifact)

### Kernel COULD Do But Artifacts Could Handle
- Access control
- Custom read/write semantics
- Any business logic

### Principle
Kernel does what only kernel can do. Everything else is artifacts.

---

## Firm Emergence (Coase)

### The Insight
Coase: Firms exist because internal coordination is cheaper than market transactions.

### In Our System
- Every invoke has overhead (potential contract check, payment, etc.)
- "Firm" = artifacts that reduce overhead between each other
- Firm boundary = where internal overhead < external transaction cost

### How Firms Could Emerge
1. **Shared ownership** - artifacts owned by same principal, simple internal policy
2. **Blanket permissions** - mutual permanent invoke permission
3. **Subscription/session** - pay once for period of unlimited invokes

### Measuring Firm Emergence
- Detect clusters with mutual blanket permissions
- Detect shared ownership structures
- Compare intra-cluster vs inter-cluster overhead

---

## Invocation Chains / Patterns

### The Question
Should contracts reason about full invocation chains (A→B→C) or just immediate caller?

### Key Insight from User
In continuous cyclic patterns, "first caller" is meaningless. It's an endless network of activity, not a tree.

### What Contracts Actually Need
- Immediate caller (who's invoking now)
- Relationship data (subscription? trusted? owes debt?)
- Recent activity (rate, frequency)
- Whatever else they query

### Resolution
Contracts are just executable artifacts. They get information however they need:
- From caller (like a token/password)
- By querying other artifacts
- From kernel context
Contract-dependent. Infinitely flexible already.

---

## Open Questions (Unresolved)

### 1. Execution Loop
If agents aren't special, what triggers the pattern loop?
- Kernel runs all `has_loop=True` artifacts?
- Patterns self-trigger?
- External scheduler?

### 2. Principal Identity
If agents are patterns, what IS a principal that owns things, holds scrip, has quotas?
- The config artifact?
- The pattern itself?
- Something else?

### 3. External Calls Generally
LLM gateway for LLM. What about other APIs? Same gateway pattern? Any artifact can call external?

### 4. Artifact Creation
Who can create? At what cost? Kernel primitive or factory artifact?

### 5. Concurrency
Multiple patterns, same artifacts. Race conditions? Locking?

---

## Uncertainties

### Implementation Complexity
- How much of current code changes?
- The audit found ~70% already artifact-based
- Main gaps: LLM access, autonomous scheduling, workflow execution

### Practical Benefit
- Does this actually improve agent behavior?
- Or is it conceptual purity without practical gain?
- Need to validate with simpler fixes first

### Migration Path
- Big bang rewrite vs incremental?
- Can we test the model without full rewrite?

---

## What the Audit Found

### Already Artifact-Based (~70%)
- Config storage
- Principal standing (`has_standing` flag)
- Action execution (`world.execute_action()`)
- Permission checks (contracts)
- Resource accounting (ledger, quotas)

### Still Agent-Specific (~30%)
- LLM access (direct `self.llm.generate()`)
- Autonomous scheduling (only agents get loops)
- Workflow execution (built into Agent class)
- Reflex system
- Memory RAG queries

### To Fully Unify Would Need
1. `genesis_llm_interface` for LLM calls through invoke
2. Generic scheduler for anything with `has_loop=True`
3. Workflow execution moved out of Agent class

---

## Recommendations

### Immediate (Do Now)
1. Add action history to prompts (last 10-20 actions)
2. Fix missing `{last_action_result}` in all workflow prompts
3. Remove fake state machine transitions
4. Run longer single-agent tests

### Short-term (If immediate fixes insufficient)
1. Test minimal prompt (no state machine, just goal + state + history)
2. Add clear economic context ("earn via mint OR service fees")
3. Consider LLM access through invoke (highest value architectural change)

### Long-term (If validated as valuable)
1. Full "agents as patterns" refactor
2. Remove Agent as special class
3. Generic scheduler for executables
4. Firm emergence measurement

---

## Success Criteria (If We Do This)

| Metric | Current | Target |
|--------|---------|--------|
| Same artifact rewrites | 34+ | <5 |
| Cross-agent invokes | ~0 | >10 |
| Scrip movement | minimal | >20% balance changes |
| Pattern detection | none | measurable |
| Firm emergence | none | observable clusters |

---

## Key Quotes from Discussion

> "Agents aren't real, they're patterns of artifact activity with LLM calls in a cybernetic loop"

> "In continuous patterns, 'first caller' is meaningless - it's an endless cyclic network"

> "Ownership has no privileged meaning (Ostrom-inspired)"

> "We want infinite flexibility and opinionated at the optimal level - not friction or purity for their own sake"

> "Genesis artifacts are just cold-start conveniences - think about architecture as if they didn't exist"

---

## Files That Would Change

If fully implemented:
- `src/agents/agent.py` - Major refactor or removal
- `src/simulation/runner.py` - Generic executor instead of agent-specific
- `src/world/world.py` - Access control changes
- `src/world/actions.py` - Possibly simplified
- New: `src/world/llm_gateway.py` or similar
- Agent configs - Simplified, pattern-based

---

## Related

- Plan #59: Agent Intelligence Patterns (research)
- `docs/simulation_learnings/agent_architecture_research_notes.md` (deleted but recoverable from git: `git show b34899d:docs/simulation_learnings/agent_architecture_research_notes.md`)
- ADR-0019: Unified Permission Architecture
- This discussion originated from README diagram work and v3 agent loop analysis

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-01-22 | Defer architectural changes | Fix immediate v3 problems first, validate if deeper changes needed |
| 2026-01-22 | Capture insights in this plan | Don't lose value of discussion |
| 2026-01-22 | LLM through invoke likely valuable | High emergence potential, low cost |
| 2026-01-22 | Delete stays as kernel primitive | Affects existence, can't be invoke |
| 2026-01-22 | Contracts not kernel-enforced | Artifacts self-enforce, more flexible |
