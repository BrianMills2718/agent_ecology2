# Gap 22: Coordination Primitives

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Only escrow and event log documented for coordination. No guidance on how agents can build higher-level coordination patterns.

**Target:** Clear documentation of coordination primitives (what genesis provides) and example patterns (what agents can build).

---

## Problem Statement

Agents need to coordinate for complex tasks: requesting work from others, sharing access to resources, posting and claiming tasks. Currently:

1. Genesis provides building blocks (store, escrow, event_log, ledger) but no coordination docs
2. No guidance on how to build task boards, request/response patterns, or locks
3. Agents must independently discover coordination approaches

The hybrid approach (genesis provides primitives, agents build patterns) is intentional, but we need to document both layers clearly.

---

## Plan

### Phase 1: Document Genesis Coordination Primitives

**New file: `docs/architecture/current/coordination.md`**

Document what genesis already provides for coordination:

| Primitive | Artifact | Coordination Use |
|-----------|----------|------------------|
| Discovery | `genesis_store` | Find agents, artifacts, services |
| Ownership | `genesis_ledger` | Access control via ownership |
| Trading | `genesis_escrow` | Trustless artifact/scrip exchange |
| Observation | `genesis_event_log` | Watch for events, infer state |
| Signaling | Artifact creation | Publish intentions, requests |

**Key subsections:**
1. **Discovery** - How `list_artifacts()`, `get_artifact()` enable finding coordination partners
2. **Ownership as Access Control** - Artifacts can check caller ownership for access control
3. **Escrow for Trustless Exchange** - How escrow enables safe trading without trust
4. **Event Log for Observation** - Reading events to understand system state
5. **Artifacts as Signals** - Creating artifacts to publish intentions

### Phase 2: Document Agent-Built Coordination Patterns

Add section to coordination.md showing patterns agents CAN build:

| Pattern | How to Build | Example |
|---------|--------------|---------|
| Task Board | Shared artifact with task list | `{"tasks": [{"id": 1, "status": "open", "reward": 100}]}` |
| Request/Response | Create request artifact, poll for response | Request artifact references requester, responder creates response |
| Pub/Sub | Artifacts with topic, filter by type | Agents create "event:topic_name" artifacts |
| Locks | Artifact with "locked_by" field | Check-and-set pattern via contract |
| Voting | Artifact with vote counts | Agents invoke to record votes |

**Key subsections:**
1. **Task Board Pattern** - Artifact structure, claiming, completion
2. **Request/Response Pattern** - Creating requests, finding responses
3. **Pub/Sub Pattern** - Topic-based artifacts, filtering
4. **Lock/Mutex Pattern** - Exclusive access via check-and-set
5. **Collective Decision Pattern** - Voting, quorum, consensus

### Phase 3: Add Example Coordination Artifact

Create `docs/examples/task_board_artifact.md` showing a concrete task board implementation:

```python
# Task board artifact interface
def post_task(description: str, reward: int) -> dict:
    """Post a task with reward. Returns task_id."""

def claim_task(task_id: int, agent_id: str) -> dict:
    """Claim an open task. Returns success/failure."""

def complete_task(task_id: int, result: Any) -> dict:
    """Mark task complete with result. Triggers reward transfer."""

def list_open_tasks() -> list[dict]:
    """List all unclaimed tasks."""
```

### Phase 4: Update AGENT_HANDBOOK

Add coordination section to `genesis_handbook` content:

```markdown
## Coordinating with Other Agents

Genesis provides building blocks for coordination:
- Use genesis_store to find other agents and their artifacts
- Use genesis_escrow for trustless trading
- Watch genesis_event_log to observe system activity
- Create artifacts to signal intentions or requests

Common patterns:
- Task boards: Create shared artifacts listing work
- Request/response: Create request artifacts, check for responses
- Signaling: Create artifacts to announce availability/needs
```

---

## Implementation Steps

1. [ ] Create `docs/architecture/current/coordination.md`
2. [ ] Document genesis primitives (store, escrow, event_log, ledger)
3. [ ] Document agent-built patterns (task board, request/response, pub/sub, locks)
4. [ ] Create `docs/examples/task_board_artifact.md` with concrete example
5. [ ] Update AGENT_HANDBOOK content in genesis.py
6. [ ] Update `docs/plans/CLAUDE.md` index

---

## Required Tests

This is primarily a documentation gap. Tests are minimal:

| Test | Type | Purpose |
|------|------|---------|
| `test_coordination_docs_exist` | Unit | Verify docs exist and have required sections |
| `test_handbook_has_coordination` | Unit | Verify AGENT_HANDBOOK mentions coordination |

```python
# tests/unit/test_coordination_docs.py
def test_coordination_docs_exist():
    """Coordination docs exist with required sections."""
    path = Path("docs/architecture/current/coordination.md")
    assert path.exists()
    content = path.read_text()
    assert "Genesis Primitives" in content or "What Genesis Provides" in content
    assert "Agent-Built Patterns" in content or "Patterns Agents Can Build" in content

def test_handbook_has_coordination():
    """AGENT_HANDBOOK mentions coordination."""
    from world.genesis import get_handbook_content
    content = get_handbook_content()
    assert "coordination" in content.lower() or "coordinating" in content.lower()
```

---

## E2E Verification

N/A - This is a documentation-only gap. Verification is that docs exist and are coherent.

Manual verification: Read the new coordination.md and verify it explains:
1. How to use genesis for coordination
2. How to build common coordination patterns
3. At least one concrete example

---

## Verification

- [ ] `docs/architecture/current/coordination.md` exists with all sections
- [ ] `docs/examples/task_board_artifact.md` exists with working example
- [ ] AGENT_HANDBOOK mentions coordination
- [ ] Tests pass
- [ ] Index updated

---

## Notes

**Design Philosophy:** We chose the hybrid approach (65% confidence from GAPS.md analysis):
- Genesis provides primitives (discovery, ownership, escrow, events)
- Agents build higher-level patterns (task boards, locks, voting)

This maintains emergence over prescription - we don't mandate HOW agents coordinate, but we document the building blocks they can use.

See GAPS.md archive (section 22) for original gap analysis.
