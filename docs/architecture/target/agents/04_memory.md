# Agent Memory Systems

How agents remember and learn.

---

## Overview

Agents have multiple memory systems:

| Memory Type | Scope | Persistence | Purpose |
|-------------|-------|-------------|---------|
| **Working Memory** | Current session | Artifact | Short-term context, current goals |
| **Long-term Memory** | Across sessions | Artifact (semantic) | Lessons learned, strategies |
| **Context Window** | Current turn | LLM context | What agent sees right now |

---

## Working Memory

Short-term storage for current session state.

### Storage

Each agent has a working memory artifact: `{agent_id}_working_memory`

```yaml
# Example working memory content
current_subgoal: "Build a calculator artifact"
known_interfaces:
  genesis_escrow:
    methods: ["deposit", "withdraw", "list"]
recent_insights:
  - "Escrow requires authorized_writer to be set first"
```

### Usage

Agents read/write working memory via artifact actions:

```python
# Read
{"action_type": "read_artifact", "artifact_id": "alpha_3_working_memory"}

# Write (update)
{"action_type": "write_artifact", "artifact_id": "alpha_3_working_memory",
 "content": "updated content..."}
```

### Automatic Migration

At session end, valuable entries (prefixed with `LESSON:`, `STRATEGY:`, etc.) are migrated to long-term memory.

---

## Long-term Memory

Persistent storage with semantic search.

### Storage

Each agent has a long-term memory via `genesis_memory`:

```python
# Add a lesson
{"action_type": "invoke_artifact",
 "artifact_id": "genesis_memory",
 "method": "add",
 "args": ["alpha_3_longterm", "LESSON: escrow requires authorized_writer", {}]}

# Search memories
{"action_type": "invoke_artifact",
 "artifact_id": "genesis_memory",
 "method": "search",
 "args": ["alpha_3_longterm", "escrow problems", 5]}
```

### Semantic Search

`genesis_memory` uses embeddings for semantic similarity:

1. Query embedded via `genesis_embedder`
2. Cosine similarity against stored memories
3. Top-k results returned

### Cost Model

| Operation | Cost |
|-----------|------|
| Add memory | 1 scrip (embedding generation) |
| Search | 0 scrip (free) |

---

## Context Window

What the agent sees in a single turn.

### Components

```
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT CONTEXT WINDOW                         │
├─────────────────────────────────────────────────────────────────┤
│ System prompt (agent personality, base instructions)            │
├─────────────────────────────────────────────────────────────────┤
│ Step prompt (current workflow step)                             │
├─────────────────────────────────────────────────────────────────┤
│ Injected prompt components (loop_breaker, semantic_memory, ...) │
├─────────────────────────────────────────────────────────────────┤
│ RAG results (retrieved memories)                                │
├─────────────────────────────────────────────────────────────────┤
│ Context variables ({balance}, {artifacts}, {action_history})    │
└─────────────────────────────────────────────────────────────────┘
```

### RAG Configuration

```yaml
# From agent.yaml
rag:
  enabled: true
  limit: 7
  query_template: |
    State: {_current_state}. Balance: {balance}.
    What strategies worked? What mistakes should I avoid?
```

### Context Budget

Limited by LLM context window. Priority for what gets included:

1. System prompt (always)
2. Step prompt (always)
3. Injected components (always, if matched)
4. Action history (truncated if needed)
5. RAG results (limited by `rag.limit`)
6. Artifact details (summarized)

---

## Memory Quality

### The Problem

Weak models store low-quality memories:
- Generic action logs: "ACTION: I queried the kernel"
- Spam: Storing everything without filtering

### The Solution: Metacognitive Prompt

The `semantic_memory` component uses metacognitive framing:

```
ASK YOURSELF: What did I just learn that my future self should know?

If the answer is something specific (not generic), store it.

Good: "LESSON: escrow deposit requires setting authorized_writer first"
Bad: "ACTION: I queried the kernel" (too generic, don't store)
```

This produces fewer but higher-quality memories.

### Observed Results

| Model | Prompt Style | Lessons Stored | Quality |
|-------|--------------|----------------|---------|
| gemini-2.0-flash | Verbose | 0-28 | Low (spam) |
| gemini-3-flash-preview | Verbose | 35-50 | Mixed |
| gemini-2.5-flash | Metacognitive | 4-7 | High |
| gemini-2.0-flash | Metacognitive | 0-4 | High (when stored) |

See [SIMULATION_LEARNINGS.md](../../../SIMULATION_LEARNINGS.md) for details.

---

## Pre-seeded Lessons

Genesis agents start with common lessons pre-loaded:

```python
preseeded_lessons = [
    "LESSON: To deposit an artifact to escrow, first set metadata.authorized_writer to 'genesis_escrow'",
    "LESSON: Use integers for prices and amounts, not strings (10 not '10')",
    "LESSON: Check artifact ownership before trying to transfer or deposit it",
    "LESSON: Use genesis_store.list to discover what artifacts exist",
    "LESSON: Always check your scrip balance before making purchases",
]
```

This bootstraps learning without requiring agents to fail first.

---

## Memory Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Working Memory │     │  Long-term Mem  │     │ Context Window  │
│  (artifact)     │     │ (genesis_memory)│     │ (per-turn)      │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ current_subgoal │     │ LESSON: ...     │     │ Step prompt     │
│ known_interfaces│────▶│ LESSON: ...     │────▶│ RAG results     │
│ recent_insights │     │ STRATEGY: ...   │     │ Variables       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
    Session scope         Persistent            Current turn
```

---

## Capability Gaps

| Capability | Supported | Notes |
|------------|-----------|-------|
| Working memory artifact | ✓ | Per-agent |
| Long-term semantic memory | ✓ | Via genesis_memory |
| Semantic search | ✓ | Embeddings + cosine similarity |
| Cross-session persistence | ✓ | Plan #186 |
| Memory trading | ✓ (partial) | Memory artifacts are artifacts |
| Memory tiering | ✓ | Plan #196 |
| Automatic summarization | ✗ | Could compact old memories |

---

## Related

- [genesis.md](genesis.md) - Genesis agent memory configuration
- [Plan #214](../../../plans/214_sota_memory_integration.md) - SOTA memory integration
- [SIMULATION_LEARNINGS.md](../../../SIMULATION_LEARNINGS.md) - Memory quality experiments
- `src/world/genesis/memory.py` - genesis_memory implementation
