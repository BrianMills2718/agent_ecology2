# Agent Ecology V1 - Design Draft

> **⚠️ OUTDATED**: This document is from early design phase.
> See `docs/IMPLEMENTATION_PLAN.md` for current architecture.

## What This Is

A minimal "world" where LLM agents interact under resource constraints.
The goal is emergence - agents developing strategies, specializations, and
coordination patterns that weren't explicitly programmed.

## Core Primitives (Current)

| Primitive | Description |
|-----------|-------------|
| **Credits** | Single resource. Actions cost credits. Renewed per tick. |
| **Artifacts** | Persistent objects agents create. Have owner, type, content. |
| **Actions** | What agents can do: noop, read, write, transfer. |
| **Principals** | Agents with identity, balance, and LLM brain. |
| **Ticks** | Discrete time steps. Credits renew. All agents act. |

## Files in This Directory

| File | Purpose |
|------|---------|
| `v1_target_config.yaml` | What the full V1 config looks like (5 agents, all features) |
| `actions_spec.yaml` | All actions: implemented, planned, and deferred |
| `roadmap.yaml` | Thin slices from current state to V1 |
| `OVERVIEW.md` | This file |

## Current State vs Target

```
CURRENT (Slice 0.5)          TARGET (V1)
─────────────────────        ─────────────────────
2 agents                     5 agents
4 actions                    6 actions (+ list, delete)
No seed artifacts            Seed artifacts
Basic logging                Rich visualization
No minting                   Simple minting rules
No agent memory              Agent memory/context
```

## Recommended Next Slice

**Slice 1.0: Populated World**
- Add 3 more agents (trivial config change)
- Create seed artifacts (give agents something to discover)
- Add list_artifacts action (cheap discovery)

This is ~1-2 hours of work and dramatically increases interaction potential.

## Key Design Decisions

1. **Single resource (credits)** - Simplest possible. Can add more later.
2. **Hard limits** - No debt. Can't act if broke.
3. **Ownership is simple** - Creator owns. Only owner modifies.
4. **No contracts yet** - Hardcoded rules for V1. Contracts are V2.
5. **Agents see logs** - Transparency. Everyone sees everything.

## Open Questions

1. **How to make agents actually coordinate?**
   - Current: they don't really
   - Need: incentives for transfer, shared goals

2. **What makes an artifact "valuable"?**
   - Current: nothing, just content
   - Possible: read count → minting rewards

3. **How to prevent degenerate strategies?**
   - e.g., agents that just noop forever
   - Need: selection pressure, finite lifespans?

4. **What's the minimal viable emergence?**
   - Two agents trading?
   - Specialization patterns?
   - Information markets?
