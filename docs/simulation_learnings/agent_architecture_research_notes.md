# Agent Architecture Research Notes

**Status:** reference
**Date:** 2026-01-16
**Source:** docs/references/agent_research.txt
**Related:** Plan #59 (Agent Intelligence Patterns)

---

Extracted insights relevant to our agent architecture questions from comprehensive research document.

## Key Questions We're Trying to Answer

1. Should agents have one action per tick or an agentic loop?
2. Do we need planning/task management actions?
3. How should memory be controlled (automatic vs agent-controlled)?
4. What reasoning approaches (CoT, ToT, reflection) should we implement?
5. How do SOTA agents like Claude Code and AutoGPT work?

---

## Architecture Types (Relevant Findings)

### Single-Agent vs Multi-Agent

| Type | Modularity | Observability | Fault Tolerance | Cost |
|------|------------|---------------|-----------------|------|
| Monolithic LLM | Very low | Very low | Low | High (one call) |
| LLM + Tools (ReAct) | Medium | Low-Medium | Medium | Medium-Low |
| Multi-Agent (AutoGen) | High | Medium-High | High | Low (many calls) |
| Hierarchical (Nexus) | Very high | Medium | High | Low |

**Insight:** Our current single-action-per-tick is closest to "Monolithic LLM" - lowest modularity and fault tolerance. Moving to ReAct-style (LLM + Tools) or multi-agent would increase flexibility.

### Reactive vs Deliberative vs Hybrid

- **Reactive**: Fast, no memory, no planning (NOT what we want)
- **Deliberative**: Plans ahead, maintains internal model (closer to what we need)
- **Hybrid**: Combines both - fast reactions + strategic planning (IDEAL)

**BDI Architecture (Belief-Desire-Intention):**
- Explicit beliefs, desires (goals), intentions
- Natural goal/plan structure
- High interpretability
- Used in: PRS, JACK, AgentSpeak/Jason

**Insight:** Our agents lack explicit goal/intention tracking. BDI-style architecture would add:
- Beliefs (what agent thinks is true)
- Desires (goals to achieve)
- Intentions (committed plans)

---

## Reasoning Approaches

### Evolution of Thought Structures

1. **Chain-of-Thought (CoT)**: Linear step-by-step reasoning
   - Simple but fragile
   - Errors cascade through chain

2. **Tree-of-Thought (ToT)**: Branching exploration
   - Multiple solution paths
   - Breadth-first or depth-first search

3. **Graph-of-Thought (GoT)**: Dynamic networks
   - Self-loop connections for reinforced memory
   - Cross-validated conclusions from multiple evidence streams

4. **Atom of Thoughts (AoT)**: Markovian decomposition
   - Break into independent "atomic questions"
   - Each state depends only on current state (memoryless)
   - Reduces computational overhead
   - **Result:** GPT-4o-mini surpasses o3-mini and DeepSeek-R1 on HotpotQA

5. **Program of Thoughts (PoT)**: Code as intermediate reasoning
   - Generate executable code for verification
   - Symbolic computation integrated with natural language

**Insight:** Our agents use basic CoT (thought_process field). Could benefit from:
- ToT for exploring multiple approaches
- AoT for breaking complex problems into atomic subproblems
- Self-critique/reflection loops

### Diagram of Thought (DoT)

Models reasoning as a DAG (Directed Acyclic Graph):
- Nodes = propositions at various evaluation stages
- Natural language critiques provide rich feedback
- Role-specific tokens: `<proposer>`, `<critic>`, `<summarizer>`
- Unifies CoT and ToT in single LLM

**Insight:** Could implement role-switching within single agent turn - propose, critique, refine.

---

## Self-Improvement Mechanisms

### Darwin Gödel Machine (DGM)

**Key Innovation:** Agent that modifies its own code, including the code that modifies its code.

**Workflow:**
1. **Initialization**: Start with basic "seed" agents, maintain archive
2. **Sampling**: Select parent agents (with exploration bias)
3. **Reproduction**: LLM proposes code modifications
4. **Natural Selection**: Test on benchmarks, score performance
5. **Tree Formation**: Add successful children to archive

**Results:** SWE-bench 20% → 50%, Polyglot 14.2% → 30.7%

**Modifications include:**
- Upgrading tools (e.g., better file editing)
- Adding new tools/workflows
- Improving problem-solving strategies
- Adding collaboration mechanisms

**Insight:** Agents could potentially evolve their own prompts/strategies over simulation time.

### AlphaEvolve

LLM-orchestrated evolutionary search for code optimization:
- Fitness function guides evolution
- Smart prompt generation learns from past attempts
- MAP-Elites + island-based populations prevent local optima
- Dual LLM: fast idea generation + quality enhancement

**Insight:** Could apply evolutionary approach to agent prompt/strategy optimization.

---

## Framework Patterns

### ReAct (Reason + Act)

```
Thought: [reasoning about situation]
Action: [tool to invoke]
Observation: [result of action]
... repeat until done
```

**Key difference from our architecture:** ReAct loops until goal achieved, not one action per tick.

### AutoGen / Magentic-One

- Orchestrator decomposes tasks, assigns to specialized agents
- Agents: WebSurfer, FileSurfer, Coder, Terminal
- Orchestrator "plans, tracks progress, and re-plans to recover from errors"
- High fault tolerance (reassign on failure)

**Key features:**
- Role specialization
- Central orchestrator for planning
- Re-planning on errors

### CrewAI

- Role-based "crews" (Researcher, Writer, Critic)
- Shared memory between agents
- Self-organizing or scripted flows
- Parallel execution

### LangGraph

- Graph-based workflow for stateful, long-running agents
- Durable execution (automatic recovery)
- Human-in-the-loop oversight
- Short-term AND long-term memory

---

## Token-Level vs Action-Level Optimization

### POAD (Policy Optimization with Action Decomposition)

- Decomposes optimization from action level to TOKEN level
- Finer supervision for each intra-action token
- Reduces action space from O(|V|^|a|) to O(|a| × |V|)
- Better credit assignment

### OREO (Offline REasoning Optimization)

- Token-level value function for multi-step reasoning
- Fine-grained credit assignment
- Works with sparse rewards
- Can guide tree search at test time

**Insight:** Our agents output one action - could benefit from token-level reasoning where specific tokens within the action get credit/blame for outcomes.

---

## Adaptive Strategy Selection

### Derailer-Rerailer

- Assesses reasoning stability
- Triggers verification only when instability detected
- 8-11% accuracy improvement with 2-3x better efficiency

### RL-of-Thoughts (RLoT)

- RL-trained "navigator" selects reasoning approaches
- 5 fundamental "logic blocks" based on human cognition
- Navigator dynamically combines blocks per problem
- <3000 parameter navigator enables sub-10B LLMs to match 100B performance

**Insight:** Could have meta-controller that selects reasoning strategy per situation.

---

## Links to Review

### High Priority (Core Architectures)

1. **AutoGen Documentation**
   - https://github.com/microsoft/autogen
   - Multi-agent conversation framework

2. **LangGraph Documentation**
   - https://github.com/langchain-ai/langgraph
   - Stateful, durable agent workflows

3. **CrewAI**
   - https://github.com/joaomdmoura/crewai
   - Role-based multi-agent

4. **Anthropic Multi-Agent Research**
   - https://www.anthropic.com/engineering/built-multi-agent-research-system
   - How Anthropic builds multi-agent systems

### Novel Reasoning Approaches

5. **Atom of Thoughts**
   - https://arxiv.org/abs/2502.12018
   - Markovian decomposition for efficient reasoning

6. **Darwin Gödel Machine**
   - https://arxiv.org/abs/... (referenced in HuggingFace)
   - Self-improving agents

7. **Diagram of Thought**
   - https://arxiv.org/abs/... (On the Diagram of Thought)
   - DAG-based reasoning in single LLM

8. **RL of Thoughts**
   - https://arxiv.org/abs/2505.14140
   - RL navigator for reasoning strategy selection

### Workflow Automation

9. **AFlow**
   - https://arxiv.org/abs/2410.10762
   - MCTS-based workflow generation

10. **EvoFlow**
    - https://arxiv.org/abs/2502.07373
    - Evolutionary multi-objective workflow optimization

### Production Considerations

11. **Why Most AI Agents Fail in Production**
    - https://medium.com/data-science-collective/why-most-ai-agents-fail-in-production-and-how-to-build-ones-that-dont-f6f604bcd075

12. **Agentic Mesh (Enterprise Agent Ecosystems)**
    - https://seanfalconer.medium.com/agentic-mesh-the-future-of-enterprise-agent-ecosystems-f26e7d53951e

13. **DeepSeek R1's CoT Revolution**
    - https://medium.com/ai-simplified-in-plain-english/deepseek-r1s-cot-revolution-rethinking-ai-reasoning-from-chains-to-hypergraphs-2baecbb5fe26

---

## Recommendations for Our Architecture

Based on this research, potential improvements:

### Minimal Changes (Keep one-action-per-tick)
1. Add explicit goal/plan tracking via `{agent}_plan` artifact
2. Enable thinking mode ("reasoning_effort": "high")
3. Restructure prompts: goal + context + personality (not rules)
4. Add self-critique step before action selection

### Medium Changes (Multi-action per tick)
1. Allow multiple actions in sequence until "done" or budget exhausted
2. Add reflection after action execution
3. Implement ReAct-style Thought → Action → Observation loop

### Larger Changes (Full agentic loop)
1. Implement planning phase with task decomposition
2. Add explicit memory actions (store/retrieve)
3. Enable sub-agent spawning for complex tasks
4. Implement strategy selection (which reasoning approach to use)

### Experimental (Self-improvement)
1. Let agents modify their own prompts/strategies
2. Evolutionary selection of successful agent variants
3. Cross-agent learning from successful patterns
