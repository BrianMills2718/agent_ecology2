# Agent Architecture Documentation Index

**Last Updated:** 2026-01-24 (friction analysis, Plans #182-183 added)

This is the master index for all agent architecture documentation. Use this as your starting point for understanding:
1. Our kernel/substrate architecture
2. Current genesis agent implementation
3. Known gaps and planned improvements

---

## Quick Navigation

| Topic | Document | Status |
|-------|----------|--------|
| **Architecture vs SOTA** | [architecture_sota_comparison.md](architecture_sota_comparison.md) | Current |
| **Genesis Agent Issues** | [agent_architecture_synthesis.md](agent_architecture_synthesis.md) | Current |
| **Design Decisions** | [../archive/DESIGN_CLARIFICATIONS.md](../archive/DESIGN_CLARIFICATIONS.md) | Current |
| **Research Notes** | [agent_architecture_research_notes.md](agent_architecture_research_notes.md) | Reference |
| **Design Space** | [agent_architecture_design_space.md](agent_architecture_design_space.md) | Reference |
| **Emergence Questions** | [emergence_research_questions.md](emergence_research_questions.md) | Open |

---

## Key Distinction: Architecture vs Genesis Agents

| Concept | What It Means | Document |
|---------|---------------|----------|
| **Architecture** | Kernel primitives, resource model, contracts - the substrate | `architecture_sota_comparison.md` |
| **Genesis Agents** | Current agent implementation - prompts, cognitive patterns | `agent_architecture_synthesis.md` |

The architecture defines **what's possible** (capability space).
Genesis agents are **one implementation** of agents on that substrate.

---

## Architecture Summary

### What We Provide (Kernel Primitives)

| Primitive | Purpose | Assessment |
|-----------|---------|------------|
| Universal artifacts | Everything is an artifact | Beyond SOTA |
| Principal model | Economic actors with standing | Beyond SOTA |
| Contracts as artifacts | Programmable access control | Beyond SOTA |
| Resource scarcity | Depletable/renewable/allocatable | Beyond SOTA |
| Triggers (Plan #169) | Reactive event subscriptions | **Incomplete** (Plan #180) |
| Metadata queries | Flexible discovery | Comparable |
| Continuous execution | Autonomous loops | Comparable |

### Coordination Patterns Enabled

| Pattern | Implementation | Friction |
|---------|----------------|----------|
| Messaging | Artifact + metadata.to_agent + trigger | Low (when #180 done) |
| Pub-sub | Trigger on event type + filter | Low (when #180 done) |
| Task delegation | Task artifact + metadata | Low |
| Workflows | Contract artifact + state | Low |
| Consensus/voting | Contract with vote method | Low-Medium |

### Known Gaps and Friction Points

| Gap | Plan | Priority | Status |
|-----|------|----------|--------|
| Trigger integration not complete | #180 | **High** | Planned |
| Query performance (O(n) scans) | #182 | Medium | Planned |
| Consensus/voting convenience | #183 | Low | Planned |
| No multi-container coordination | None | Low | Future |

### Capability Space: Complete

No cognitive or coordination patterns are impossible. Everything maps to artifact + contract primitives:

| Pattern | Possible? | Mechanism |
|---------|-----------|-----------|
| Planning | ✅ | Write plan artifact |
| Reflection | ✅ | Read own outputs, write learnings |
| Memory | ✅ | Artifacts + Qdrant |
| Sub-agent spawn | ✅ | Create artifact + fund + grant standing |
| Self-modification | ✅ | Write to own artifact |
| Consensus | ✅ | Contract with voting logic |
| Atomic operations | ✅ | Wrapper contract handles transaction |
| Real-time resource awareness | ✅ | `kernel_state.get_balance()` |

### Friction Analysis (2026-01-24)

| Pattern | Current Friction | Cause | Fix |
|---------|------------------|-------|-----|
| Messaging/pub-sub | **HIGH** | Triggers not integrated | Plan #180 |
| Discovery | Medium | O(n) artifact scans | Plan #182 |
| Consensus | Medium | Must build contract | Plan #183 |
| Cross-run learning | Medium | Not implemented | Genesis enhancement |
| Task delegation | Low | Works via metadata | - |
| Planning | Low (unused) | Architecture supports it | Genesis enhancement |

---

## Genesis Agent Summary

### Current Issues (from 37-source research)

| Issue | Status | Notes |
|-------|--------|-------|
| No explicit planning | ❌ Not done | Agents don't create plan artifacts |
| No extended thinking | ❌ Not done | No global reasoning_effort config |
| Inconsistent prompts | ✅ Partial | _3 agents structured; v4 still rule-based |
| No learning/adaptation | ✅ Partial | _3 has reflection; not cross-run |
| No reflection | ✅ Done | _3 agents have `learn_from_outcome` |

### Agent Generations

| Generation | Agents | Features |
|------------|--------|----------|
| Original | alpha, beta, gamma, delta, epsilon | Basic workflows |
| _2 (VSM) | alpha_2, beta_2 | Self-audit, goals |
| _3 (State machines) | alpha_3, beta_3, gamma_3, delta_3, epsilon_3 | Explicit states, reflection |
| v4 | v4_solo, v4_test | Loop detection, simplified |

### Priority Improvements

1. Complete trigger integration (Plan #180)
2. Add plan artifact pattern
3. Enable reasoning_effort: high
4. Cross-run learning

---

## Design Decisions

Recent architectural decisions (from `DESIGN_CLARIFICATIONS.md`):

### Autonomous Principals vs Agents (2026-01-24)

The architectural unit is the **autonomous principal**, not "agent":
- Principal = artifact with standing (can hold resources)
- Autonomous = has execution loop
- Decision engine (LLM, RL, code) is implementation detail

### Approved Directions (2026-01-24)

| Decision | Approach | Confidence |
|----------|----------|------------|
| Loop infrastructure | Keep in simulation/, rename to PrincipalLoop | 85% |
| Resource registry | Runtime registration of resource types | 75% |
| Container resources | Defer, plan external monitor | 65% |

---

## Open Questions

From `emergence_research_questions.md`:
- What coordination patterns emerge under scarcity?
- Do markets outperform explicit messaging?
- What's the minimum viable cognitive architecture?

---

## File Map

```
docs/research/
├── AGENT_ARCHITECTURE_INDEX.md     # This file - start here
├── architecture_sota_comparison.md  # Kernel vs other platforms
├── agent_architecture_synthesis.md  # Genesis agent critique (37 sources)
├── agent_architecture_design_space.md  # Design options explored
├── agent_architecture_research_notes.md # Raw research notes
├── emergence_research_questions.md  # Open research questions
└── README.md                        # Directory overview

docs/archive/
└── DESIGN_CLARIFICATIONS.md         # Approved design decisions

docs/plans/
├── 169_kernel_event_triggers.md     # Trigger design (incomplete)
├── 180_trigger_integration.md       # Complete trigger integration (HIGH)
├── 182_metadata_indexing.md         # O(1) metadata queries (Medium)
└── 183_genesis_voting.md            # Consensus convenience (Low)
```

---

## How to Use This Documentation

**If you want to understand the architecture:**
→ Read `architecture_sota_comparison.md`

**If you want to improve genesis agents:**
→ Read `agent_architecture_synthesis.md` (especially Implementation Status)

**If you want to understand design decisions:**
→ Read `DESIGN_CLARIFICATIONS.md`

**If you want to contribute:**
→ Plan #180 (trigger integration) - **HIGH priority**, unblocks real-time coordination
→ Plan #182 (metadata indexing) - Medium priority, performance optimization
→ Plan #183 (genesis_voting) - Low priority, convenience feature
