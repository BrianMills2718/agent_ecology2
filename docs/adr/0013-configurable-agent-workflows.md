# ADR-0013: Configurable Agent Workflows

**Status:** Accepted
**Date:** 2026-01-17

## Context

Agents in the simulation have a fixed execution model: one `decide_action()` → `execute_action()` cycle per iteration. Observations from simulation runs showed agents getting stuck in trivial loops (0 artifacts created in 10 ticks, searching for phantom artifacts repeatedly).

Research on agent architectures (45+ sources including Anthropic, LangGraph, AutoGen, CrewAI, VOYAGER, Generative Agents) showed effective agents need:
- Observation, planning, AND reflection (Generative Agents: "all 3 required")
- Self-verification before committing (VOYAGER: -73% without it)
- Configurable reasoning approaches

We evaluated existing frameworks:
- **LangGraph**: Graph-based workflow orchestration - assumes developer designs workflow
- **AutoGen**: Multi-agent conversation framework - assumes agent-to-agent messaging
- **CrewAI**: Role-based multi-agent teams - assumes prescribed roles

Key mismatch: These frameworks solve "how do I (developer) orchestrate agents" not "how do agents learn to orchestrate themselves."

## Decision

**Implement configurable per-agent workflows with a phased approach:**

### Phase 1 (MVP): Simple Workflow Execution
- Workflows are ordered lists of steps
- Step types: `code` (Python expressions) and `llm` (prompt artifacts)
- Agent constructs prompts manually (no injection DSL)
- Errors returned to agent for self-correction
- Workflow self-modification applies next iteration

### Phase 2: Context Injection (if needed)
- Prompt templates with placeholders
- `inject:` block defines data sources
- Predefined injection sources only

### Phase 3: Output Schemas (if needed)
- Pydantic validation for LLM responses
- Structured outputs available to subsequent steps

### Phase 4: Full Meta-Config (speculative)
- Agent-defined templates and schemas
- Dynamic injection sources
- Parallel step execution

**Key principles:**
- Start simple, add complexity only when observed need
- Maintain minimal kernel (workflow execution is agent-side)
- Errors always returned to agents (never silent failures)
- Resource accounting unchanged (kernel tracks LLM calls/actions)

**Why not adopt existing frameworks:**
- They embed workflow logic in the framework (violates minimal kernel)
- They assume developer-designed coordination (violates emergence goal)
- The interesting part is what agents PUT in workflows, not execution mechanics

## Consequences

### Positive

- Agents can experiment with different execution patterns (think → verify → act vs. observe → plan → act)
- Enables emergence: agents that find effective workflows succeed
- No framework dependency or lock-in
- Simple Phase 1 implementation (~300 lines of code)
- Research patterns (reflection, verification, skill libraries) can be agent-implemented

### Negative

- Agents must learn to construct effective workflows
- Phase 1 has no "magic" - agents manually construct prompts
- More complex than fixed execution model
- Future phases add implementation debt (may never be needed)

### Neutral

- Existing agent code needs modification to use workflow model
- Prompts become artifacts rather than files
- Debugging workflow issues requires understanding step execution

## Alternatives Considered

1. **Adopt LangGraph**: Rejected - assumes static developer-designed graphs
2. **Adopt AutoGen**: Rejected - assumes multi-agent conversation as primary pattern
3. **Adopt CrewAI**: Rejected - assumes prescribed roles
4. **Keep fixed model + smarter prompts**: Insufficient - doesn't enable experimentation
5. **Full agentic loop immediately**: Too risky - hard to observe, potential runaway

## Related

- Feature spec: `acceptance_gates/agent_workflow.yaml`
- Research notes: `docs/references/agent_architecture_research_notes.md`
- Archived design exploration: `docs/archive/agent_research_2026-01/`
- Simulation observation: `docs/simulation_learnings/2026-01-16_agent_paralysis.md`
