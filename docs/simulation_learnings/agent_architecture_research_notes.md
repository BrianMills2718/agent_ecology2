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
| 20 | MemGPT (Letta) | **Read** |
| 21 | ExpeL | **Read** |
| 22 | Reflexion | **Read** |
| 23 | HippoRAG | **Read** |
| 24 | Zep/Graphiti | **Read** |
| 25 | Agent Workflow Memory | **Read** |
| 26 | Reddit: AI Agent Memory Guide | **Read** |
| 27 | Episodic Memory Retrieval & Injection | **Read** |
| 28 | Memory Synthesis from Execution Logs | **Read** |
| 29 | Skill Library Evolution | **Read** |
| 30 | Self-Critique Evaluator Loop | **Read** |
| 31 | Dual Episodic+Semantic Memory (impl) | **Read** |
| 32 | RLHF Self-Improvement Pattern (impl) | **Read** |
| 33 | VOYAGER (Minecraft lifelong learning) | **Read** |
| 34 | OpenAI Swarm/Orchestrating Agents | **Read** |
| 35 | Progressive Complexity Escalation | **Read** |
| 36 | Plan-Then-Execute Pattern | **Read** |
| 37 | Context-Minimization Pattern | **Read** |

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

### MemGPT (Letta) - LLMs as Operating Systems

Source: https://arxiv.org/abs/2310.08560

**Core Innovation:** OS-inspired virtual context management for LLMs

**Memory Hierarchy:**
- Mirrors traditional OS memory tiers (fast/slow storage)
- Creates illusion of vast memory by moving data between tiers
- Enables processing beyond native context window limits

**Key Features:**
- Interrupt mechanisms for coordinating system-user interaction
- Tiered memory structure preserving performance
- Demonstrated on: document analysis (large docs) and multi-session chat

**Key Insight:** "LLMs can remember, reflect, and evolve dynamically through long-term interactions" when given proper memory management.

### ExpeL - Experiential Learners (CRITICAL FOR OUR USE CASE)

Source: https://arxiv.org/abs/2308.10144

**Core Innovation:** Learning from experience WITHOUT parameter updates

**How It Works:**
1. Agent gathers experiences from training tasks
2. Extracts knowledge using natural language (not weights)
3. At inference, recalls insights and past experiences
4. Performance enhances as experiences accumulate

**Why This Matters:**
- Works with proprietary models (GPT-4, Claude) - no fine-tuning needed
- Sidesteps resource-intensive training
- Avoids generalization degradation from fine-tuning
- Knowledge may transfer across different tasks

**Key Insight:** Agents can learn and improve through natural language experience storage - exactly what our agents lack.

### Reflexion - Verbal Reinforcement Learning (CRITICAL)

Source: https://arxiv.org/abs/2303.11366

**Core Innovation:** Self-improvement through linguistic feedback, not weight updates

**How It Works:**
1. Agent receives feedback (external or internal)
2. Generates reflective text analyzing failures/mistakes
3. Stores self-critiques in episodic memory buffer
4. Applies insights to improve on subsequent trials

**Performance:**
- HumanEval coding: 91% pass@1 (vs GPT-4's 80%)
- Works with scalar or free-form language feedback

**Key Insight:** Natural language reflection IS a learning mechanism. Agents improve through self-critique without fine-tuning.

**Relevance:** This is exactly what we need for post-action reflection (Tier 2 recommendation).

### HippoRAG - Neurobiologically-Inspired Memory

Source: https://arxiv.org/abs/2405.14831

**Core Innovation:** Memory modeled on hippocampal indexing theory

**Architecture:**
- LLMs (reasoning) + Knowledge Graphs (structure) + Personalized PageRank (ranking)
- Mimics neocortex + hippocampus roles in human memory
- Prevents catastrophic forgetting

**Performance:**
- 10-30x cheaper than iterative retrieval (like IRCoT)
- 6-13x faster
- Up to 20% improvement on multi-hop QA

**Key Insight:** Single-step retrieval can match/exceed iterative approaches with proper memory architecture.

### Zep/Graphiti - Temporal Knowledge Graphs

Source: https://arxiv.org/abs/2501.13956

**Core Innovation:** Temporally-aware knowledge graph for dynamic memory

**Key Capabilities:**
- Synthesizes unstructured (conversations) AND structured (business data)
- Maintains historical relationships over time
- Cross-session information synthesis
- Long-term context maintenance

**Performance:**
- 94.8% accuracy on Deep Memory Retrieval (vs MemGPT 93.4%)
- Up to 18.5% improvement on temporal reasoning
- 90% latency reduction

**Key Insight:** Memory needs temporal awareness - relationships and contexts EVOLVE over time. Static RAG misses this.

### Agent Workflow Memory (AWM)

Source: https://arxiv.org/abs/2409.07429

**Core Innovation:** Learn reusable workflows, not individual actions

**What Gets Stored:**
- Commonly reused routines (workflows)
- Task procedures that generalize across scenarios

**Two Modes:**
- **Offline**: Workflows induced from training examples
- **Online**: Workflows generated from test queries on-the-fly

**Performance:**
- Mind2Web: 24.6% relative success rate improvement
- WebArena: 51.1% relative success rate improvement
- Generalizes across tasks, websites, and domains

**Key Insight:** Store generalizable task PATTERNS, not specific action sequences. Mirrors human problem-solving.

**Relevance:** Our agents could benefit from workflow artifacts that capture successful patterns.

### Reddit: AI Agent Memory That Doesn't Suck (Practitioner Insights)

Source: r/AI_Agents discussion

**Memory Stack Pattern (what practitioners actually use):**
```
Short-term: Redis/cache (recent conversations)
Long-term: Vector DB + regular DB (similar contexts + facts)
Episode: Specific interactions + what worked
```

**Smart Memory Patterns:**

1. **Search, don't cram** - Build search system instead of stuffing everything into prompts
2. **Keep solutions, discard trial-and-error** - When task done, save the result not the process
3. **Summarize aggressively** - "User prefers React: components + TypeScript" not verbose explanation
4. **Weight by recency AND importance** - Recent matters, but don't lose valuable old insights
5. **Score by relevance to current context** - Travel discussion → prioritize flight/hotel memories

**Critical Implementation Details (from comments):**

| Insight | Source |
|---------|--------|
| Memory needs: **data + context/meta + timestamp**. Timestamps help resolve conflicting info over time. | epreisz |
| Store BOTH user AND assistant memories - assistant's memories useful for higher-order thinking | epreisz |
| **Graph DB for relationships** between facts. Connect "Paris flights" → "vacation planning" → "prefers direct flights" | Striking-Bluejay6155 |
| Summaries **bleed information over time** - need multilayer memory, not just long/short | Short-Honeydew-7000 |
| Self-improvement flows are needed - personalization isn't just prompt engineering | Short-Honeydew-7000 |

**Common Mistakes:**
- Don't keep entire conversation histories in prompts
- Don't treat all memories as equally important
- Don't forget to clean up old, irrelevant memories

**Key Quote:**
> "The goal isn't perfect memory, it's making your agent feel like it actually knows the user. An agent that remembers you hate chitchat and prefer examples is way better than one with perfect but useless memory."

**Relevance to Our Architecture:**
- Our Mem0/Qdrant integration may benefit from timestamp + context metadata
- Graph relationships between memories (what's connected to what) could improve retrieval
- "Keep solutions, discard process" aligns with AWM's workflow storage pattern
- We should track what WORKED, not just what happened

### Episodic Memory Retrieval & Injection Pattern

Source: agentic-patterns.com

**Problem:** Stateless agent calls cause agents to forget prior decisions, leading to repeated mistakes.

**Three-Step Solution:**

1. **Memory Recording**: After each episode, write a concise "memory blob" capturing event, outcome, and reasoning
2. **Memory Retrieval & Injection**: Embed prompt, retrieve top-k similar memories via vector similarity, inject as contextual hints
3. **Memory Maintenance**: Apply TTL or decay scoring to prune outdated memories

**Trade-offs:**
- ✓ Richer continuity across sessions, reduces repeated errors
- ✗ Retrieval noise if memories lack curation, storage costs

**Relevance:** We could write episode summaries to artifacts after each tick, then retrieve relevant ones for context.

### Memory Synthesis from Execution Logs (CRITICAL FOR LEARNING)

Source: agentic-patterns.com

**Problem:** Memorizing everything creates noise; ignoring learnings wastes experience.

**Two-Tier Solution:**

**Tier 1 - Task Diaries:** Each execution generates structured entry:
- Attempted approaches + outcomes
- Failures with error details
- Successful solutions + reasoning
- Edge cases discovered
- Potentially generalizable patterns

**Tier 2 - Synthesis:** Dedicated agents review batches (50+ entries) to find patterns appearing in 3+ tasks, then recommend:
- General rules for system prompts
- Reusable commands
- Test cases

**Implementation Phases:**
1. Structured logging (what attempted, why failed, what worked)
2. Periodic synthesis (weekly or after N tasks)
3. Knowledge integration (feed into prompts, commands, tests)

**Key Quote:**
> Rather than "make button pink", synthesis reveals: "Authentication changes consistently require CORS updates and dual expiry checks"

**Relevance:** This is exactly how our agents could learn across ticks/runs. Action logs → periodic synthesis → prompt improvements.

### Skill Library Evolution

Source: agentic-patterns.com

**Evolution Path:**
```
Ad-hoc Code → Save Working Solution → Reusable Function → Documented Skill → Agent Capability
```

**Storage Structure:**
```
skills/
├── README.md (skill index)
├── data_processing/
├── api_integration/
└── tests/
```

**Progressive Discovery (91% token reduction):**
- Don't load all skills into context
- Inject brief descriptions into system prompt
- Provide on-demand `load_skills` tool
- Lazy-load only relevant tools

**Trade-offs:**
- ✓ Reduces redundant problem-solving, builds org knowledge
- ✗ Requires curation discipline, potential staleness

**Relevance:** Agents could build skill artifacts that other agents can discover and use.

### Self-Critique Evaluator Loop

Source: agentic-patterns.com (Wang et al., arXiv:2408.02666)

**Self-Taught Evaluator Pattern:**

1. **Generate candidates**: Multiple response options
2. **Self-judge**: Model articulates which excels + reasoning
3. **Bootstrap training**: Fine-tune evaluator on own judgments
4. **Iterate**: Strengthen discriminative ability
5. **Refresh synthetically**: Regenerate to prevent drift

**Integration Points:**
- Reward model scoring agent outputs
- Quality gate filtering low-confidence generations
- Triggers after generation, before execution

**Result:** Near-human eval accuracy without labels; scales with compute

**Relevance:** Agents could self-evaluate actions before committing.

### Dual Episodic+Semantic Memory Implementation

Source: FareedKhan-dev/all-agentic-architectures

**Architecture:**
```
Episodic Memory (FAISS)     Semantic Memory (Neo4j)
    ↓                              ↓
"What happened?"            "What do I know?"
Past conversations          Entities & relationships
Vector similarity           Graph queries
    ↓                              ↓
    └──────── Combined Context ────────┘
                    ↓
            Generate Response
                    ↓
            Update Both Memories
```

**Memory Creation Flow:**
1. After interaction, "Memory Maker" agent processes conversation
2. LLM generates brief summary → episodic (vector)
3. Structured output extracts entities/relationships → semantic (graph)
4. Both updated asynchronously

**Retrieval Pattern:**
```python
retrieve_memory() → [vector search + graph query] → combined context
```

**Example:**
Query: "Based on my goals, what's a good alternative?"
- Episodic: retrieves summary about conservative investing
- Semantic: retrieves `(User:Alex)-[HAS_GOAL]->(ConservativeInvesting)`
- Combined: contextually appropriate recommendation

**Relevance:** We already have Qdrant (vector). Adding graph structure could improve relationship-aware retrieval.

### RLHF Self-Improvement Pattern Implementation

Source: FareedKhan-dev/all-agentic-architectures

**Three-Phase Feedback Loop:**

```
┌─────────────────────────────────────────────┐
│  1. GENERATION: Primary agent creates output │
└──────────────────┬──────────────────────────┘
                   ↓
┌──────────────────────────────────────────────┐
│  2. CRITIQUE: Critic scores + gives feedback │
│     - Numeric score (1-10)                   │
│     - Specific actionable feedback           │
│     - Approval boolean (≥8 = done)           │
└──────────────────┬───────────────────────────┘
                   ↓
         ┌────────────────┐
         │  Score ≥ 8?    │
         └───┬────────┬───┘
           Yes       No
            ↓         ↓
         DONE    3. REVISION
                     ↓
              Loop back to 2
```

**Persistent Learning via GoldStandardMemory:**
- High-quality outputs stored in memory
- Injected as examples in future prompts:
  > "Learn from the style and quality of past successful examples"
- Result: Second task achieved 9/10 immediately (zero revisions) vs first task needing revision

**Key Insight:** Reinforces successful patterns WITHOUT mathematical reward functions. System learns from accumulated positive outcomes.

**Relevance:** Our agents could store successful action sequences as exemplars for future reference.

### VOYAGER - Lifelong Learning Agent (CRITICAL - MINECRAFT)

Source: arXiv:2305.16291 (NVIDIA/Caltech/UT Austin)

**The first LLM-powered embodied lifelong learning agent.** Continuously explores, acquires skills, makes discoveries without human intervention.

**Three Key Components:**

```
┌─────────────────────────────────────────────────────────┐
│  1. AUTOMATIC CURRICULUM                                │
│     - GPT-4 proposes tasks based on current state      │
│     - Bottom-up: adapts to exploration progress        │
│     - Goal: "discover as many diverse things as possible" │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  2. SKILL LIBRARY                                       │
│     - Each skill = executable code                     │
│     - Indexed by embedding of description              │
│     - Retrieved via similarity search for new tasks    │
│     - Complex skills compose simpler ones              │
└─────────────────────┬───────────────────────────────────┘
                      ↓
┌─────────────────────────────────────────────────────────┐
│  3. ITERATIVE PROMPTING                                 │
│     - Environment feedback (intermediate progress)     │
│     - Execution errors (bugs, invalid operations)      │
│     - Self-verification (GPT-4 as critic)              │
│     - Loop until verified OR stuck (4 rounds max)      │
└─────────────────────────────────────────────────────────┘
```

**Results vs Baselines (ReAct, Reflexion, AutoGPT):**
- 3.3× more unique items discovered
- 15.3× faster tech tree unlock (wooden tools)
- 2.3× longer distances traversed
- ONLY method to unlock diamond level

**Critical Ablation Findings:**
| Component Removed | Impact |
|-------------------|--------|
| Automatic curriculum | -93% items (random curriculum fails) |
| Skill library | Plateaus in later stages |
| Self-verification | -73% items (most important feedback!) |
| GPT-4 → GPT-3.5 | -82% items (5.7× worse) |

**Skill Library Details:**
- Skills are CODE, not natural language descriptions
- Guideline: "Your function will be reused for building more complex functions. Make it generic and reusable."
- Query: embed task + environment feedback → retrieve top-5 similar skills
- Skills compound over time, alleviating catastrophic forgetting

**Cold-Start Pattern:**
- Curriculum adapts to current state (e.g., desert → harvest sand/cactus before iron)
- Tasks not too hard: "may not have necessary resources or skills yet"
- Completed/failed tasks tracked as exploration progress

**Relevance to Our Architecture:**
- Automatic curriculum = exactly what we need for cold-start
- Skill library = our agents could write skill artifacts
- Self-verification = our Tier 2 reflection recommendation
- Code as skills = interpretable, composable, reusable

### OpenAI Swarm / Orchestrating Agents

Source: OpenAI Cookbook

**Core Pattern: Routines and Handoffs**

A routine = "list of instructions in natural language + tools necessary to complete them"

**Execution Loop:**
```python
while not done:
    response = model.call(instructions, tools)
    for tool_call in response.tool_calls:
        result = execute(tool_call)
        if isinstance(result, Agent):  # Handoff detected
            active_agent = result
            # Conversation history preserved
```

**Handoff Mechanism:**
- Agent returns `Agent` object from tool call (e.g., `transfer_to_refunds()`)
- Orchestrator detects return type, swaps active agent
- Full conversation history flows across handoffs

**Best Practices:**
- Start with straightforward prompts + conditional logic
- Keep routines focused on specific domains
- Use tool functions to express agent transitions explicitly
- Test with small/medium complexity before scaling

**Key Quote:** This approach is "simple, but surprisingly effective"

**Relevance:** Shows how multi-agent handoffs can work simply - relevant for future multi-agent considerations.

### Progressive Complexity Escalation (COLD-START PATTERN)

Source: agentic-patterns.com

**Core Idea:** Start with low-complexity, high-reliability tasks. Escalate as confidence grows.

**Three-Tier Architecture:**
| Tier | Mode | Description |
|------|------|-------------|
| 1 | Immediate | Information gathering, human decides |
| 2 | Validated | Multi-step workflows, human approval gates |
| 3 | Future | Autonomous decisions, confidence-based |

**Initial Tasks (Tier 1):**
- Data entry and research
- Content categorization
- Information extraction
- Template-based generation

**Promotion Criteria:**
- Accuracy thresholds (95% → Tier 2; 98% → Tier 3)
- Human approval rates
- Override frequency
- Stakeholder confidence

**Example Evolution:**
```
Phase 1: Agent researches leads, human writes outreach
Phase 2: Agent researches + drafts email, human approves
Phase 3: Agent auto-sends when confidence > 0.8
```

**Relevance:** Directly addresses our cold-start problem. Agents should start with simple tasks (read, observe) before attempting complex ones (write, invoke).

### Plan-Then-Execute Pattern

Source: agentic-patterns.com

**Two Distinct Phases:**

**Phase 1 - Planning:**
```python
plan = LLM.make_plan(prompt)  # Frozen list of calls
```
- Complete sequence generated BEFORE any untrusted data
- Human can review/modify before execution

**Phase 2 - Execution:**
```python
for call in plan:
    result = tools.run(call)
    stash(result)  # Isolated from planner
```
- Controller runs exact sequence
- Tool outputs can inform parameters, NOT alter which tools run

**When to Use:**
- Email/calendar automation
- SQL query assistants
- Code-review tools
- Predictable action sets with varying parameters

**Result:** "2-3x success rates for complex tasks by aligning on approach first"

**Trade-off:** Strong control-flow integrity, but tool output content still vulnerable.

**Relevance:** This is our Tier 1 recommendation - agents should plan before acting.

### Context-Minimization Pattern

Source: agentic-patterns.com

**Problem:** Untrusted user input can influence downstream LLM outputs even after serving initial purpose.

**Three-Step Solution:**
```python
# 1. Transform & Extract
sql = LLM("convert to SQL", user_prompt)

# 2. Purge Original
remove(user_prompt)  # From conversation history

# 3. Continue with Safe Data
rows = db.query(sql)
answer = LLM("summarize", rows)  # Never sees original input
```

**What to Retain:**
- Transformed, validated outputs
- System constraints and instructions
- Factual data from trusted sources

**What to Remove:**
- Raw user-supplied text
- Unvalidated user queries
- Potentially injected content

**Trade-offs:**
- ✓ Simple, reduces context window, prevents injection
- ✗ Sacrifices conversational continuity, may remove legitimate context

**Relevance:** Security pattern - relevant when agents process external inputs.

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
