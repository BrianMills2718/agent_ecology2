# Architecture SOTA Comparison

**Status:** Draft
**Date:** 2026-01-24
**Related:** agent_architecture_synthesis.md (genesis agent critique), DESIGN_CLARIFICATIONS.md

---

## Purpose

This document compares our **kernel/substrate architecture** to other multi-agent platforms. This is distinct from agent cognitive architecture (covered in `agent_architecture_synthesis.md`).

**Key distinction:**
- **Architecture** = the substrate on which agents run (kernel primitives, resource model, contracts)
- **Agent implementation** = how agents think and act (prompts, cognitive patterns, memory)

Most SOTA research focuses on agent cognition. Our architecture is about the **environment** in which agents operate.

---

## What Our Architecture Provides

### 1. Universal Artifact Ontology

Everything is an artifact with a unified structure:

```python
@dataclass
class Artifact:
    id: str                      # Unified namespace
    content: Any                 # The actual data
    created_by: str              # Historical fact, not authority
    access_contract_id: str      # Contract governing access
    artifact_type: str           # Advisory typing
    has_standing: bool           # Can hold resources (principal)
    can_execute: bool            # Can run code (autonomous)
```

**Implications:**
- Agents, contracts, data, plans - all artifacts
- Uniform CRUD operations
- Tradeable, observable, composable

**Comparison to other platforms:**
| Platform | Entity Model |
|----------|--------------|
| AutoGen | Distinct agent vs message types |
| CrewAI | Agents, tasks, crews as separate concepts |
| LangGraph | Nodes, edges, state - graph-specific |
| **Ours** | Everything is an artifact |

### 2. Principal Model (Economic Actors)

Artifacts can have "standing" - the ability to hold resources and bear costs:

```
Artifact (base)
  └── Principal (has_standing=true) - can hold scrip, quota
        └── Autonomous Principal (can_execute=true) - has a loop
```

**Implications:**
- Any artifact can become an economic actor
- Resource accounting is generic, not agent-specific
- "Agent" is just an autonomous principal with LLM decision engine

**Comparison:**
| Platform | Economic Model |
|----------|----------------|
| AutoGen | No built-in economics |
| CrewAI | No resource accounting |
| LangGraph | Checkpoints, not economics |
| **Ours** | First-class resource scarcity |

### 3. Contract-Based Access Control

Access policies are artifacts, not hardcoded rules:

```python
# Every artifact has an access_contract_id
artifact.access_contract_id = "my_custom_policy"

# Contract returns permission decisions
def check_permission(action, requester, context):
    if requester == context["created_by"]:
        return {"allowed": True}
    return {"allowed": False, "reason": "Not creator"}
```

**Implications:**
- Custom access policies per artifact
- Policies are tradeable (buy someone's access logic)
- Kernel is policy-agnostic

**Comparison:**
| Platform | Access Control |
|----------|----------------|
| AutoGen | Role-based, hardcoded |
| CrewAI | Role permissions |
| LangGraph | No built-in access control |
| **Ours** | Contracts as artifacts (programmable) |

### 4. Resource Scarcity (Three Types)

Real constraints, not simulated:

| Type | Description | Example |
|------|-------------|---------|
| **Depletable** | Once spent, gone | LLM API budget ($) |
| **Renewable** | Rate-limited via token bucket | API rate limits (RPM) |
| **Allocatable** | Quota-based, reclaimable | Disk space (bytes) |

**Implications:**
- Agents experience real scarcity
- Economic pressure shapes behavior
- Markets emerge for resource trading

**Comparison:**
| Platform | Resource Model |
|----------|----------------|
| AutoGen | Token counting, no enforcement |
| CrewAI | No resource limits |
| LangGraph | No resource model |
| **Ours** | Three-type scarcity with enforcement |

### 5. Continuous Autonomous Execution

Agents run in continuous loops, not tick-synchronized:

```python
while self.alive:
    action = self.decide_action()
    result = self.execute_action(action)
    # No tick boundary - loop continues
```

**Implications:**
- No artificial synchronization
- Agents work at their own pace
- Coordination emerges from markets, not forced sync

**Comparison:**
| Platform | Execution Model |
|----------|-----------------|
| AutoGen | Conversational turns |
| CrewAI | Sequential tasks |
| LangGraph | Graph traversal |
| **Ours** | Continuous autonomous loops |

### 6. Genesis as Unprivileged Conveniences

Cold-start artifacts that use the same primitives as agent-built artifacts:

| Genesis Artifact | Purpose | Uses Kernel Primitives |
|------------------|---------|------------------------|
| genesis_ledger | Balances, transfers | `transfer_scrip()` |
| genesis_escrow | Trustless trading | `transfer_ownership()` |
| genesis_store | Artifact discovery | `get_artifact_metadata()` |
| genesis_mint | Auction-based scoring | `credit_resource()` |

**Implications:**
- Agents could build equivalents
- No special privileges for genesis
- Cold-start, not permanent infrastructure

**Comparison:**
| Platform | Built-in Services |
|----------|-------------------|
| AutoGen | Hardcoded message routing |
| CrewAI | Hardcoded crew management |
| LangGraph | Hardcoded graph engine |
| **Ours** | Unprivileged, replaceable genesis |

### 7. Event System (Observability)

All state changes emit events:

```python
{
    "event_number": 1234,
    "event_type": "artifact_created",
    "principal_id": "alice",
    "artifact_id": "my_plan",
    "timestamp": "2026-01-24T12:00:00Z"
}
```

**Implications:**
- Full observability without polling
- Agents can subscribe to events
- Audit trail for all mutations

**Comparison:**
| Platform | Observability |
|----------|---------------|
| AutoGen | Message logging |
| CrewAI | Task status |
| LangGraph | State snapshots |
| **Ours** | Event stream with subscriptions |

### 8. Reactive Triggers (Plan #169)

Agents can register triggers - "when event matching X occurs, invoke artifact Y":

```python
# Trigger artifact
{
    "type": "trigger",
    "metadata": {
        "enabled": true,
        "filter": {"event_type": "artifact_created", "data.metadata.to_agent": "bob"},
        "callback_artifact": "my_inbox_handler",
        "callback_method": "on_message"
    }
}
```

**Implications:**
- Push notifications, not polling
- Reactive programming at kernel level
- Agents define their own event handlers

**Comparison:**
| Platform | Reactivity |
|----------|------------|
| AutoGen | Callback registration in code |
| CrewAI | Task completion hooks |
| LangGraph | Node transitions |
| **Ours** | Trigger artifacts (data-driven, tradeable) |

### 9. Metadata-Based Discovery (Plan #168)

Artifacts have arbitrary metadata, queryable with dot-notation:

```python
# Find messages addressed to me
genesis_store.list([{"metadata.to_agent": "bob"}])

# Find tasks matching my skills
genesis_store.list([{"metadata.skill_required": "coding", "metadata.status": "open"}])

# Find items in a channel
genesis_store.list([{"metadata.channel": "engineering"}])
```

**Implications:**
- Arbitrary addressing schemes via convention
- Efficient discovery without scanning content
- Enables messaging, channels, task queues via metadata

**Comparison:**
| Platform | Discovery |
|----------|-----------|
| AutoGen | Agent registry, explicit addressing |
| CrewAI | Crew/agent hierarchies |
| LangGraph | Graph structure |
| **Ours** | Metadata queries (flexible, emergent) |

### 10. Coordination Patterns Enabled

With triggers + metadata, these patterns have **low friction**:

| Pattern | Implementation |
|---------|----------------|
| **Messaging** | Artifact with `metadata.to_agent`, receiver has trigger |
| **Channels** | Artifacts with `metadata.channel`, subscribers filter |
| **Task delegation** | Task artifact with `metadata.assignee` or `metadata.skill_required` |
| **Workflows** | Contract artifact defines state machine, state in artifact |
| **Pub-sub** | Trigger on event type + metadata filter |

These match AutoGen/CrewAI/LangGraph capabilities but via artifact primitives rather than hardcoded infrastructure.

---

## Where We're Novel (Potentially Beyond SOTA)

### 1. Economic Substrate

Most multi-agent platforms focus on **communication** (how agents talk to each other). We focus on **economics** (how agents compete for scarce resources).

This is a fundamentally different paradigm:
- **Communication-first**: Agents coordinate via messages
- **Economics-first**: Agents coordinate via markets

Our thesis: Markets are more robust coordination mechanisms than explicit messaging.

### 2. Contracts as Artifacts

Access control policies that are:
- Programmable (arbitrary logic)
- Tradeable (buy someone's policy)
- Observable (anyone can read the contract)
- Composable (contracts can call contracts)

No other major platform has this.

### 3. Genesis Unprivilege Principle

The idea that built-in services should have no special powers. They're conveniences, not infrastructure. Agents could rebuild them.

This enables true emergence - the system doesn't prescribe what infrastructure exists.

### 4. Autonomous Principal as Unit

Not "agent" as the special entity, but "autonomous principal" - any artifact with standing and execution capability. This allows:
- Daemons (code-only principals)
- RL agents (non-LLM decision engines)
- Hybrid principals (LLM + rule-based)
- Agents that spawn agents

---

## Where We're Comparable to SOTA

### Continuous Execution
Similar to agentic loops in Claude Code, AutoGPT, etc. Our implementation is solid but not novel.

### Event Observability
Standard pattern. Well-implemented but not differentiating.

### Sandboxed Execution
Process isolation for artifact code. Common security pattern.

---

## Where We Might Be Lacking

### 1. No Built-in Sub-Agent Spawning
Anthropic's multi-agent research shows 90% improvement with orchestrator-worker patterns. We don't have a kernel primitive for spawning sub-agents.

**Mitigation:** Could be built as genesis artifact (create agent artifact + fund it). Not a kernel concern.

### 2. Query Performance (Optimization, Not Architecture)
Current `genesis_store.list()` and `TriggerRegistry.refresh()` scan all artifacts - O(n) not O(1). For large artifact stores, this could be slow.

**Mitigation:** Add indexing on common metadata fields. Optimization, not missing primitive.

### 3. No Multi-Container Coordination
For scaling beyond single process. Current architecture is single-world.

**Mitigation:** Future work. Could use distributed ledger pattern.

### Clarification: Memory and Workflows Are Supported

**Memory:** Artifacts ARE the memory primitive. Agents can implement any memory pattern (episodic, semantic, hierarchical) using artifacts. More flexible than built-in memory primitives.

**Workflows:** Contracts define state machines, artifacts hold state. Matches LangGraph capability via artifact primitives.

---

## Summary: SOTA or Beyond?

| Dimension | Assessment |
|-----------|------------|
| **Economic primitives** | Beyond SOTA - unique |
| **Contracts as artifacts** | Beyond SOTA - unique |
| **Genesis unprivilege** | Beyond SOTA - unique philosophy |
| **Autonomous principal model** | Beyond SOTA - generalization |
| **Reactive triggers** | Beyond SOTA - data-driven, tradeable |
| **Metadata discovery** | Beyond SOTA - flexible, emergent addressing |
| **Coordination patterns** | Comparable to SOTA - different implementation (artifacts vs hardcoded) |
| **Continuous execution** | Comparable to SOTA |
| **Event observability** | Comparable to SOTA |
| **Memory architecture** | Comparable to SOTA - artifacts enable any pattern |
| **Multi-agent orchestration** | Different paradigm (markets vs messaging) |

**Overall:** Our architecture provides:
1. **Maximal capability space** - Triggers, metadata, artifacts enable any coordination pattern
2. **Economic game layer** - Scarcity incentivizes agents to optimize within that space
3. **Emergence philosophy** - Infrastructure emerges from agent behavior, not prescribed

The question isn't "is this SOTA?" but:
- **Capability:** Can agents implement any cognitive/coordination pattern? (Architecture question)
- **Incentives:** Does the economic game motivate optimal use of capabilities? (Emergence question)

This document focuses on capability. The economic game and emergence are separate empirical questions.

---

## Implications for Development

1. **Don't copy communication-first patterns** - We're not AutoGen/CrewAI
2. **Invest in economic primitives** - This is our differentiator
3. **Keep kernel minimal** - Genesis can add conveniences
4. **Let agents build infrastructure** - Emergence over prescription
5. **Measure emergent behavior** - That's our success metric

---

## References

| Source | Relevance |
|--------|-----------|
| AutoGen docs | Communication-first comparison |
| CrewAI docs | Role-based comparison |
| LangGraph docs | Graph workflow comparison |
| Anthropic multi-agent research | Sub-agent patterns |
| DESIGN_CLARIFICATIONS.md | Approved architectural directions |
| agent_architecture_synthesis.md | Genesis agent critique (separate concern) |
