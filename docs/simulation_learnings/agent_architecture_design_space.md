# Agent Architecture Design Space

**Status:** open (design exploration)
**Date:** 2026-01-16
**Related:** Plan #59, simulation_learnings/agent_paralysis, agent_architecture_research_notes

---

This document captures the full design space for improving agent intelligence, including alternatives, tradeoffs, concerns, and open questions. The goal is to think through options before committing to implementation.

---

## Current State

```
Per Tick:
  1. Agent receives world state summary
  2. Agent makes ONE LLM call
  3. LLM returns thought_process + action
  4. Action executed
  5. Next tick

Memory: Automatic (system stores/retrieves, agent has no control)
Planning: None (no explicit goals, tasks, or plans)
Reflection: None (no self-critique or revision)
Strategy Selection: None (same approach for all problems)
```

**Observed Problems:**
- Agents got stuck searching for phantom artifacts (trivial confusion breaks everything)
- No artifact creation in 10 ticks (cold-start deadlock)
- Prompts are rule-sets rather than goal+context
- One action per tick prevents iteration/refinement

---

## Design Dimensions

### 1. Actions Per Tick

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Single action (current)** | One action per tick, forced | Simple, predictable, easy to log | No iteration, can't refine, can't recover |
| **B. Multi-action batch** | Return list of actions, execute in sequence | Some iteration, still bounded | Commit to sequence upfront (no mid-course correction) |
| **C. Agentic loop** | Loop until agent says "done" or budget exhausted | Full flexibility, matches SOTA | Harder to observe, could infinite loop, expensive |
| **D. Bounded loop** | Loop with max iterations (e.g., 5) | Flexibility with guardrails | Arbitrary bound, might not be enough or too much |

**Considerations:**
- Our tick model is central to simulation - changing it affects the whole system
- Multi-agent research shows loops are valuable but 15x more tokens
- Bounded loop is pragmatic middle ground

**Concerns:**
- If we allow loops, how do we prevent runaway token consumption?
- How do we log/observe multi-step reasoning within a tick?
- Does this break the "physics" of our simulation (one action per unit time)?

**Questions:**
- Is the tick model sacred, or is it just an implementation detail?
- Should loops be opt-in per agent (configurable)?
- How do we charge for multi-action ticks (resource accounting)?

---

### 2. Planning Mechanism

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. None (current)** | No explicit planning | Simple, emergent | Agents lack direction, get stuck |
| **B. Plan artifact** | Agent writes `{agent}_plan` artifact | Observable, tradeable, fits our model | Extra action to maintain plan |
| **C. Dedicated plan field** | Add `current_plan` to agent state | Always available, no action needed | Special-cased, not emergent |
| **D. TodoWrite-style action** | New action type for plan management | Explicit, structured | More kernel complexity |
| **E. Genesis planning service** | `genesis_planner` artifact agents can invoke | Fits genesis pattern, optional | Indirection, might not be used |

**Considerations:**
- Option B (plan artifact) aligns with our "everything is an artifact" philosophy
- Anthropic persists plans to external memory - artifact store is our equivalent
- Plans should be observable (other agents can read them)

**Concerns:**
- Will agents actually use planning if it's optional?
- How do we seed initial planning behavior without prescribing it?
- If plans are artifacts, should they have special properties (auto-update, etc.)?

**Questions:**
- Should plans be public (other agents can read) or private?
- How granular should plans be? High-level goals vs detailed task lists?
- Should the system automatically inject an agent's plan into their context?

---

### 3. Memory Control

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Automatic (current)** | System stores/retrieves based on heuristics | Simple for agents | No strategic control |
| **B. Explicit actions** | Add `store_memory`, `recall_memory` actions | Full control, strategic | Uses action slots, more complex |
| **C. Hybrid** | Auto-store important things, explicit recall | Best of both? | Complex rules for "important" |
| **D. Memory as artifacts** | Write to `{agent}_memories` artifact | Fits our model, observable | Chunky, not fine-grained |
| **E. Genesis memory service** | `genesis_memory` with store/search methods | Optional, composable | Indirection |

**Considerations:**
- Current Mem0/Qdrant integration is automatic - we'd need to expose controls
- Memory-as-artifact makes memories tradeable/observable (interesting economics)
- Anthropic uses external memory when context exceeds limits

**Concerns:**
- Explicit memory control might overwhelm agents with choices
- How do we prevent memory bloat?
- Memory costs (storage, retrieval) - should these be charged?

**Questions:**
- What's the right granularity for memory items?
- Should agents be able to forget/delete memories?
- How does memory interact with the plan artifact?

---

### 4. Reflection / Self-Critique

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. None (current)** | No reflection step | Simple | Agents don't learn from mistakes |
| **B. Post-action reflection** | After action result, reflect before next | Catches errors, enables learning | Extra LLM call per tick |
| **C. Critic in prompt** | Add critic persona to system prompt | No extra calls | Limited depth, prompt bloat |
| **D. Periodic reflection** | Every N ticks, dedicated reflection phase | Amortized cost | Delayed feedback |
| **E. On-failure reflection** | Only reflect when action fails | Targeted, efficient | Only reactive, not proactive |

**Considerations:**
- Anthropic uses "interleaved thinking" after tool results
- DoT (Diagram of Thought) uses `<proposer>`, `<critic>`, `<summarizer>` roles
- Reflection is where agents could catch the "45 vs 30 artifacts" confusion

**Concerns:**
- Extra LLM calls = more cost, more latency
- How do we know if reflection actually helps?
- Could reflection become an infinite regress?

**Questions:**
- Should reflection be mandatory or optional?
- How do we measure the value of reflection?
- Should reflection output be logged/observable?

---

### 5. Reasoning Strategy Selection

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Fixed (current)** | Same prompt/approach for all problems | Simple, consistent | Suboptimal for varying difficulty |
| **B. Difficulty-based** | Simple problems get less thinking | Efficient | Need to estimate difficulty |
| **C. Problem-type routing** | Different strategies for different tasks | Specialized | Need to classify problems |
| **D. RLoT-style navigator** | Small model selects strategy | Adaptive, learned | Complex, needs training |
| **E. Agent-configured** | Each agent has preferred strategies in config | Customizable | Manual tuning |

**Considerations:**
- RLoT achieves 13.4% improvement with <3000 param navigator
- Derailer-Rerailer shows adaptive verification improves efficiency
- Our agents all use same approach - no specialization

**Concerns:**
- Strategy selection adds complexity
- How do we implement without a trained navigator?
- Risk of over-engineering

**Questions:**
- Is reasoning_effort="high" sufficient for now?
- Should different genesis agents have different default strategies?
- Can strategy selection emerge from agent behavior rather than be prescribed?

---

### 6. Prompt Structure

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Monolithic (current)** | Single system_prompt.md file | Simple | Rule-sets, not modular |
| **B. YAML sections** | Separate goal/personality/context/metacognition | Modular, configurable | More files, parsing |
| **C. Template + variables** | Base template with per-agent substitutions | Reusable patterns | Indirection |
| **D. Hierarchical** | Base prompt + agent-specific overrides | Inheritance, DRY | Complexity |
| **E. Dynamic assembly** | Build prompt from components at runtime | Maximum flexibility | Hard to understand |

**Considerations:**
- Current prompts create cold-start deadlock ("check what exists first")
- User wants: goal + context + personality (not rules)
- Metacognition guidance ("when to accept uncertainty") is missing

**Concerns:**
- Too much modularity = fragmentation
- Need to test prompt changes carefully (sensitive)
- How do we ensure consistency across agents?

**Questions:**
- What should be shared vs. per-agent?
- How do we validate prompt quality?
- Should prompts evolve during simulation?

---

### 7. Thinking Mode / Reasoning Effort

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. Default low (current)** | LiteLLM defaults to low | Fast, cheap | Shallow reasoning |
| **B. Default high** | Set reasoning_effort="high" globally | Deeper thinking | More expensive, slower |
| **C. Per-agent config** | Each agent specifies in agent.yaml | Customizable | Manual tuning |
| **D. Adaptive** | Adjust based on problem complexity | Optimal | Need complexity estimation |
| **E. Per-action-type** | High for write/invoke, low for read | Task-appropriate | Heuristic might be wrong |

**Considerations:**
- Anthropic uses "extended thinking mode" for planning
- Gemini 3 supports reasoning_effort: minimal/low/medium/high
- Current agents think in ~500 chars - might be too shallow

**Concerns:**
- High reasoning = more cost per tick
- How do we know if thinking is actually better?
- Risk of over-thinking simple actions

**Questions:**
- What's the cost multiplier for high vs low reasoning?
- Should we A/B test different reasoning levels?
- How do we expose this in config?

---

### 8. Sub-Agent / Task Delegation

| Option | Description | Pros | Cons |
|--------|-------------|------|------|
| **A. None (current)** | Each agent is independent | Simple | No task decomposition |
| **B. Spawn sub-agents** | Agents can create temporary workers | Matches Anthropic pattern | Complex lifecycle |
| **C. Invoke other agents** | Request help from existing agents | Uses existing entities | Coordination overhead |
| **D. Task artifacts** | Create task artifacts others can claim | Emergent, market-based | Slow, indirect |
| **E. Genesis task service** | Central task queue for delegation | Structured | Centralized, less emergent |

**Considerations:**
- Anthropic spawns 10+ subagents for complex tasks
- Our philosophy prefers emergence over prescription
- Task artifacts (option D) fits "everything is artifact"

**Concerns:**
- Sub-agents massively increase token usage (15x)
- How do we prevent sub-agent explosion?
- Lifecycle management is complex

**Questions:**
- Is delegation necessary for our use case?
- Can we achieve similar results with better single-agent reasoning?
- Should delegation emerge from agent behavior?

---

## Cross-Cutting Concerns

### Token Economics
- Multi-agent and loops use significantly more tokens
- Need to account for this in resource model
- Should thinking/reflection be charged?

### Observability
- More complex agent behavior = harder to debug
- Need to log intermediate steps
- How do we visualize multi-step reasoning?

### Emergence vs. Prescription
- Our philosophy favors emergence
- But agents need enough capability to emerge
- Where's the line between enabling and prescribing?

### Backward Compatibility
- Changes to tick model affect existing code
- Need migration path
- Should old behavior be an option?

### Testing
- How do we test that agents are "smarter"?
- Need benchmarks for agent intelligence
- A/B testing across configurations

---

## Production Failure Research (Critical Warnings)

From research on why 95% of AI agent projects fail:

### The Learning Gap
Most GenAI systems don't retain feedback, don't accumulate knowledge, and don't improve over time. Every query is treated as first.

**Relevance to us:** Our agents have memory, but no explicit learning loop. Do they actually improve?

### Six Architecture Patterns That Fail

| Pattern | Our Risk Level | Notes |
|---------|---------------|-------|
| 1. Agents for simple problems | **Medium** | Some tasks might not need full agent |
| 2. PoC becomes production | **High** | We're in early stage, need to plan for scale |
| 3. Brittle tool integrations | **Low** | Our action set is simple |
| 4. No testing framework | **Medium** | We have tests but no agent intelligence benchmarks |
| 5. Lack of observability | **Low** | We have good logging |
| 6. All-in rollout | **N/A** | Not deploying to users |

### Tool Calling Reliability
Even well-engineered systems have 3-15% tool failure rates. Each step compounds:
- 5% failure per step
- 10 steps = 40% chance of at least one failure

**Implication:** More actions per tick increases failure surface.

### Key Recommendations from Research

1. **Start narrow**: One agent that works > ten that demo well
2. **Re-architect after PoC**: Don't polish prototypes
3. **Test from day one**: Maintain datasets of hard cases
4. **Design for failure**: Graceful handling of errors
5. **Incremental rollout**: Shadow mode before full deployment

---

## Philosophy Alignment Check

| Principle | Implications for This Design |
|-----------|------------------------------|
| **Emergence is the goal** | Don't prescribe specific strategies; provide capabilities and let behavior emerge |
| **Minimal kernel, max flexibility** | New actions/features should be optional, not required |
| **Align incentives** | Planning/reflection should have costs; don't make them free |
| **Pragmatism over purity** | If pure emergence doesn't work, consider gentle nudges |
| **Genesis as middle ground** | New capabilities could be genesis artifacts (optional services) |
| **Observe, don't prevent** | Log everything; don't block "bad" agent behavior |

---

## Open Questions Requiring Answers

### Fundamental
1. Is the tick model (one action per unit time) essential to the simulation, or just convenient?
2. Should all agents have the same capabilities, or can they differ?
3. How much can we change before it's a different system?

### Technical
4. How do we implement agentic loops within the current executor?
5. What's the performance impact of high reasoning_effort?
6. How do we handle action failures in a loop context?

### Economic
7. How should multi-action ticks be charged?
8. Should reflection/thinking cost resources?
9. Do smarter agents deserve larger budgets?

### Validation
10. How do we measure agent intelligence improvement?
11. What benchmarks should we use?
12. How do we avoid overfitting to specific test cases?

### Scope
13. Which changes are Plan #59 vs. new plans?
14. What's the MVP for testing these ideas?
15. Can we run experiments without full implementation?

---

## Proposed Evaluation Criteria

Before implementing anything, we should define how we'll evaluate success:

| Metric | How to Measure | Baseline |
|--------|----------------|----------|
| Artifact creation rate | write_artifact actions / total actions | 0% (in 10-tick test) |
| Cold-start time | Ticks until first artifact created | Never (in test) |
| Confusion recovery | Ticks to resolve contradictory information | Never recovered |
| Token efficiency | Useful actions / tokens consumed | Unknown |
| Emergent behavior | Novel strategies observed | None yet |

---

## Next Steps

1. **Answer fundamental questions** - especially about tick model
2. **Choose MVP scope** - smallest change that tests the hypothesis
3. **Define success metrics** - before implementing
4. **Run controlled experiment** - compare old vs new
5. **Document results** - in simulation_learnings

---

## Appendix: Research Summary

See `agent_architecture_research_notes.md` for detailed findings from:
- Anthropic multi-agent (orchestrator-worker, 90.2% improvement)
- LangGraph (cycles for reasoning loops, checkpointing)
- RLoT (adaptive strategy selection, 13.4% improvement)
- FunSearch (evolutionary search + LLM)
- Atom of Thoughts (Markovian decomposition)
- AutoGen (publish-subscribe messaging)
- AFlow (MCTS workflow optimization)
