# Research

Design explorations, literature reviews, and architectural research.

> **Note:** This is **background context**, not the source of truth.
> For current implementation details, see `docs/architecture/current/`.

## Start Here

**[AGENT_ARCHITECTURE_INDEX.md](AGENT_ARCHITECTURE_INDEX.md)** - Background research and design decisions that informed the architecture.

## Purpose

Capture research and design thinking that **informed** architecture decisions. This is historical/reference material, not authoritative documentation of current implementation.

**Source of truth:** `docs/architecture/current/` (agents.md, agent_cognition.md)
**This directory:** Background research, design explorations, rationale

Contents:
- Design space explorations
- Literature reviews and external references
- Architectural pattern research
- Synthesis documents

## Contents

### Architecture (Kernel/Substrate)
- `architecture_sota_comparison.md` - **Kernel architecture vs other platforms** (AutoGen, CrewAI, LangGraph)

### Agent Cognition (Genesis Agents)
- `agent_architecture_design_space.md` - Exploration of agent cognitive architectures
- `agent_architecture_research_notes.md` - Notes from researching agent patterns
- `agent_architecture_synthesis.md` - Synthesis of research into actionable design (37 sources)

### Other
- `emergence_research_questions.md` - Open questions requiring experimentation
- `Central_Governance_Planning.md` - Future conceptual thinking on governance

## Key Distinction

**Architecture** = kernel primitives, resource model, contracts (the substrate)
**Agent cognition** = prompts, planning, reflection, memory (how agents think)

The `architecture_sota_comparison.md` covers the former; other docs cover the latter.
