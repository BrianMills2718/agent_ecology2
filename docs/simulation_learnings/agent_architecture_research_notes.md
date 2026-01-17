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

## Verified Findings from Source Links (2026-01-16)

### Anthropic Multi-Agent Architecture (CRITICAL)

Source: https://www.anthropic.com/engineering/built-multi-agent-research-system

**Orchestrator-Worker Pattern:**
- Lead agent analyzes queries, develops strategy, spawns subagents
- Subagents operate in parallel exploring different aspects
- Each subagent gets: objective, output format, tool guidance, clear boundaries

**Planning & Memory:**
- Lead agents use **extended thinking mode** to plan before execution
- Plans persisted to external memory (context can exceed 200K tokens)
- Agents summarize completed phases, store essential info before proceeding

**Scaling Rules (embedded in prompts):**
- Simple queries: 1 agent, 3-10 tool calls
- Complex research: 10+ subagents
- Parallel execution cuts research time by up to 90%

**Tool Strategy:**
- Examine all tools first, match to intent
- Bad tool descriptions "send agents down completely wrong paths"
- Specialized tools > generic tools
- Interleaved thinking after tool results to evaluate quality

**Performance:**
- Multi-agent (Opus lead + Sonnet workers) outperformed single Opus by **90.2%**
- Token usage explains 80% of performance variance
- Multi-agent uses ~15x more tokens than single chat
- Only economical for high-value tasks

### LangGraph Core Concepts

Source: https://docs.langchain.com/oss/python/langgraph/overview

**What It Solves:**
- Long-running, stateful agents
- Failure recovery
- Human oversight of autonomous systems

**State Management:**
- Centralized state object (not function call passing)
- All nodes read/write same state dictionary
- Checkpointing enables persistence and time-travel debugging

**Control Flow:**
- Conditional edges (route based on state)
- Cycles (nodes feed outputs back as inputs = reasoning loops)
- Subgraphs (hierarchical composition)
- START/END explicit entry/exit

**Durable Execution:**
- Workflows persist through failures
- Resume from checkpoints
- Thread-based resumption
- Time travel to previous states

**Human-in-the-loop:** Interrupts pause execution for human decisions

### RL of Thoughts (RLoT)

Source: https://arxiv.org/abs/2505.14140

**Key Innovation:** Tiny RL navigator (<3000 params) selects reasoning strategies

**Logic Blocks:** 5 basic blocks from human cognition perspective (combined per task)

**Results:**
- Outperforms established techniques by up to 13.4%
- Sub-10B LLMs match 100B-scale performance
- Trained on one LLM-task pair, generalizes to unseen LLMs and tasks

**Mechanism:** Navigator dynamically selects and combines logic blocks into task-specific structures based on problem characteristics.

### FunSearch (DeepMind)

Source: https://deepmind.google/discover/blog/funsearch-making-new-discoveries-in-mathematical-sciences-using-large-language-models/

**Architecture:** LLM + automated evaluator in iterative loop
- LLM generates code solutions
- Evaluator filters hallucinations
- Best solutions feed back into pool

**Key Design:**
1. Favors compact, human-readable code (interpretability)
2. Diversity preservation prevents stagnation
3. Parallel evolutionary branches
4. Human-AI collaboration (researchers refine problems from insights)

**Results:** Largest increase in cap set problem in 20 years; bin-packing algorithms beat established heuristics.

### Atom of Thoughts (AoT)

Source: https://arxiv.org/abs/2502.12018

**Core Idea:** Markovian decomposition - minimize reliance on historical context

**Atomic Units:** Self-contained, low-complexity reasoning chunks that don't require extensive history

**Compatible:** Works with tree search, reflective refinement, both reasoning and non-reasoning models

**Result:** Consistently outperforms baselines as computational budgets increase

### AutoGen Communication Pattern

Source: Microsoft AutoGen docs

**Publish-Subscribe Model:**
- Agents don't communicate directly
- Publish messages to topics
- Runtime handles delivery and lifecycle

**Asynchronous Pipeline:**
- Agent A processes → publishes to topic
- Agent B subscribes → receives → processes → publishes
- Continues until termination condition

### AFlow (Workflow Automation)

Source: https://arxiv.org/abs/2410.10762

**Approach:** Monte Carlo Tree Search for workflow optimization

**Results:**
- 5.7% average improvement over SOTA baselines
- Smaller LLMs outperform GPT-4o at 4.55% of inference cost

---

### CrewAI

Source: https://github.com/joaomdmoura/crewai

**Two Approaches:**
- **Crews**: Autonomous agent collaboration with role-based teamwork
- **Flows**: Event-driven workflows with conditional branching

**Role Definition (YAML):**
- Role: Professional title
- Goal: Primary objective
- Backstory: Character context explaining expertise

**Collaboration:**
- Sequential or hierarchical processes
- Autonomous delegation
- Context sharing between tasks

### EvoFlow

Source: https://arxiv.org/abs/2502.07373

**Niching Evolutionary Algorithm:**
- Tag-based retrieval of parent workflows
- Crossover and mutation to generate variants
- Niching-based selection preserves diversity

**Results:**
- Outperforms handcrafted workflows by 1.23%-29.86%
- Beats o1-preview at 12.4% of inference cost
- Evolves workflows from simple I/O to complex multi-turn

### Darwin Gödel Machine (DGM)

Source: https://sakana.ai/dgm/

**How It Works:**
- Self-improving coding agent combining LLMs with evolution
- Unlike theoretical Gödel Machine, uses empirical validation not proofs

**Code Self-Modification:**
1. Self-Understanding: Reads and modifies own Python codebase
2. Performance Evaluation: Tests against benchmarks
3. Parallel Exploration: Multiple evolutionary pathways simultaneously

**Agent Archive:**
- Repository of diverse agents
- Branching point for future modifications
- Prevents premature convergence

**Results:**
- SWE-bench: 20% → 50%
- Polyglot: 14.2% → 30.7%
- Improvements transfer across models and languages

### Why AI Agents Fail in Production (CRITICAL)

Sources: [HBR](https://hbr.org/2025/10/why-agentic-ai-projects-fail-and-how-to-set-yours-up-for-success), [Softcery](https://softcery.com/lab/why-ai-agent-prototypes-fail-in-production-and-how-to-fix-it), [Directual](https://www.directual.com/blog/ai-agents-in-2025-why-95-of-corporate-projects-fail)

**Failure Statistics:**
- 95% of AI projects see no measurable return
- 80%+ never make it to production
- Tool calling fails 3-15% of the time in production

**Six Architecture Patterns That Fail:**

| Pattern | Problem | Fix |
|---------|---------|-----|
| 1. Agents for simple problems | Hallucination compounds (5% per step) | Use agents only where flexibility essential |
| 2. PoC becomes production | Overloaded prompts, no decomposition | Re-architect after PoC |
| 3. Brittle tool integrations | No pagination, strict matching, unclear errors | Treat tool design as first-class |
| 4. No testing framework | Can't catch regressions | Build tests immediately after PoC |
| 5. Lack of observability | Can't diagnose failures | Structured logging from day one |
| 6. All-in rollout | Everything breaks at once | Incremental rollout, shadow mode |

**Key Insight - The Learning Gap:**
Most corporate GenAI systems don't retain feedback, don't accumulate knowledge, and don't improve over time. Every query is treated as if it's the first.

**HBR Recommendations:**
1. Develop strategic technology roadmap
2. Adopt composite AI (multiple techniques)
3. Rigorous cost-benefit analysis
4. Assess technical readiness first
5. Focus on enterprise-wide impact

---

### Building an Agentic System (Practical Guide)

Source: https://gerred.github.io/building-an-agentic-system/print.html

**Three-Layer Architecture:**
1. Terminal UI Layer
2. Intelligence Layer (LLM with streaming)
3. Tools Layer (standardized plugin architecture)

**Tool System Design:**
- Read-only classification enables parallel execution
- "Read operations can run in parallel, but write operations need careful coordination"
- Smart concurrency: read tools simultaneous, write tools sequenced

**Permission & Safety:**
- Explicit permission gates for modifications
- Risk-based UI styling communicates impact
- Beyond simple confirmation dialogs

**System Prompt Architecture:**
- Base Instructions (identity, rules, tone)
- Environment Info (cwd, git status, platform)
- Agent-Specific Prompts (tool instructions)

**Key Principle:** "Keep responses short, since they will be displayed on command line interface."

### Anthropic: Building Effective Agents (CRITICAL)

Source: https://www.anthropic.com/research/building-effective-agents

**Workflows vs Agents:**
- **Workflows**: LLMs orchestrated through predefined code paths
- **Agents**: LLMs dynamically direct their own processes and tool usage

**Five Workflow Patterns:**

| Pattern | Use Case |
|---------|----------|
| Prompt Chaining | Fixed subtasks, trade latency for accuracy |
| Routing | Complex tasks with distinct categories |
| Parallelization | Speed gains or higher confidence |
| Orchestrator-Workers | Unpredictable subtask requirements |
| Evaluator-Optimizer | Clear evaluation criteria, refinement helps |

**When to Use Agents:**
- Open-ended problems with unpredictable steps
- Model needs autonomous decision-making
- Trusted environments only
- **NOT for**: Well-defined tasks (use workflows) or most applications (use simple prompts)

**Core Principles:**
1. Simplicity - maintain straightforward design
2. Transparency - explicitly display planning steps
3. Tool Documentation - invest in ACI like HCI

**Critical Insight:**
> "Start with direct LLM API calls rather than frameworks. Many patterns require just a few lines of code."

> "Anthropic spent more time optimizing tools than overall prompts in their SWE-bench agent."

### System 2 Research

Source: https://github.com/open-thought/system-2-research

**Key Approaches:**
- Cognitive architectures (SOAR, ACT-R, LIDA)
- Chain/Tree/Graph of Thought
- Process Reward Models (PRMs) for intermediate step evaluation
- Test-time compute scaling (repeated sampling matches larger models)

**Key Finding:**
> "Effective AI reasoning requires hybrid System 1 and System 2 fusion - combining rapid pattern recognition with deliberate, verifiable problem-solving."

---

## Links to Review

| # | Source | Status |
|---|--------|--------|
| 1 | Anthropic Multi-Agent | **Read** |
| 2 | LangGraph | **Read** |
| 3 | Atom of Thoughts | **Read** |
| 4 | RL of Thoughts | **Read** |
| 5 | FunSearch | **Read** |
| 6 | AFlow | **Read** |
| 7 | AutoGen | **Read** |
| 8 | CrewAI | **Read** |
| 9 | EvoFlow | **Read** |
| 10 | Darwin Gödel Machine | **Read** |
| 11 | Why Agents Fail (HBR) | **Read** |
| 12 | Six Architecture Failures | **Read** |
| 13 | Building Agentic System | **Read** |
| 14 | Anthropic Effective Agents | **Read** |
| 15 | System 2 Research | **Read** |
| 16 | Lilian Weng (OpenAI) Agent Blog | **Read** |
| 17 | Generative Agents (Stanford) | **Read** |
| 18 | CAMEL (NeurIPS 2023) | **Read** |
| 19 | mem0 | **Read** |

---

## Additional Sources (2026-01-16)

### Lilian Weng - LLM Powered Autonomous Agents (OpenAI)

Source: https://lilianweng.github.io/posts/2023-06-23-agent/

**Three-Tier Memory System (mirrors human cognition):**
- **Sensory**: Embedding representations of raw inputs
- **Short-term**: In-context learning bounded by transformer context (~4000 tokens)
- **Long-term**: External vector stores enabling infinite information retention

**Memory Retrieval Factors:**
- Relevance (semantic similarity)
- Recency (how recent the memory)
- Importance (salience/significance)

**Tool Use Requirements:**
1. **Knowing when** to call tools (determining necessity)
2. **Identifying which** tool solves the problem (API selection)
3. **Refining calls** based on results (iterative improvement)

**MRKL Architecture:**
- LLMs as routers directing queries to specialized expert modules
- Can route to neural OR symbolic components based on task

**ReAct Pattern:**
```
Thought: [reasoning about situation]
Action: [tool to invoke]
Observation: [result of action]
... repeat until done
```

**Reflexion Framework:**
- Dynamic memory for detecting hallucinations and inefficient trajectories
- Enables course correction mid-execution

**Key Limitations Identified:**
1. Finite context windows limit historical information integration
2. Long-term planning remains brittle when facing unexpected errors
3. Natural language interfaces create parsing overhead and output reliability issues

### Generative Agents (Stanford - "Smallville")

Source: https://arxiv.org/abs/2304.03442

**Memory Architecture:**
- Complete natural language record of agent's experiences
- Not just storage - **synthesis into higher-level reflections over time**
- Dynamic retrieval to inform planning and behavior

**Three Critical Components (ALL REQUIRED):**
1. **Observation**: Recording what happens
2. **Planning**: Deciding what to do
3. **Reflection**: Synthesizing meaning from experiences

> "Testing confirmed that observation, planning, and reflection--each contribute critically to the believable agent behavior."

**Emergent Social Behavior:**
- From single user input ("host a Valentine's Day party"), agents autonomously:
  - Spread invitations over two days
  - Made new acquaintances
  - Asked each other out on dates
  - Coordinated to show up together

**Key Insight:** Coherent long-term behavior emerges from the combination of all three components - removing any one breaks believability.

### CAMEL (NeurIPS 2023)

Source: https://arxiv.org/abs/2303.17760

**Role-Playing Framework:**
- Agents adopt specific roles to maintain focus and behavioral constraints
- Roles provide context that guides collaboration

**Inception Prompting:**
- Guides chat-based agents toward task completion
- Enables structured conversations without constant human intervention
- Maintains alignment with human intentions

**Autonomous Cooperation:**
- Agents engage in back-and-forth exchanges
- Role assignments provide behavioral constraints
- Can resolve complex problems through dialogue

**Research Value:**
- Multi-agent conversations generate valuable datasets
- Insights into "cognitive" processes of language models
- Open-sourced CAMEL library for community research

### mem0 - Memory Layer for LLM Agents

Source: https://github.com/mem0ai/mem0

**Multi-Level Memory Management:**
- **User-level**: Individual preferences and long-term patterns
- **Session-level**: Context within conversation threads
- **Agent-level**: Autonomous system state and behavior

**Performance:**
- 91% faster responses vs full-context retention
- 90% token reduction
- Semantic search with vector DB backend

**Key Design Features:**
- Integration with any LLM (default GPT-4)
- Automatic capture and storage of conversation content
- REST endpoints and SDKs (Python/TypeScript/JavaScript)
- Multiple vector database backends

**Architectural Pattern:**
- Hierarchical memory (user → session → agent) is proven effective
- Separation of memory tiers enables targeted retrieval

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
