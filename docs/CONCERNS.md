# Design Concerns Watchlist

Potential issues to monitor. Not bugs, not plans - just things that might become problems.

**Format:** Add concerns with context and what would indicate they're becoming real problems.

---

## Active Concerns

### Plan #222: Artifact-Aware Workflow Engine

| Concern | Risk | Watch For |
|---------|------|-----------|
| **Circular dependencies** | Decision artifacts that need memory/store access might create cycles | Agents hanging, infinite loops, stack overflows during workflow execution |
| **Stale cache** | Per-run caching might return outdated values if agent state changes mid-workflow | Wrong transition decisions after mid-workflow scrip changes |
| **Observability noise** | Including invoke results in thought capture might clutter logs | Hard to trace agent behavior in dashboard, excessive log volume |
| **Decision artifact complexity** | "Simple" decision artifacts might grow complex over time | Decision artifacts that invoke other artifacts, slow workflow execution |

### Cognitive Architecture Flexibility

| Concern | Risk | Watch For |
|---------|------|-----------|
| **Terminology debt** | Current term "traits" is confusing (not standard usage) | New contributors confused, documentation inconsistency |
| **Schema rigidity** | Fixed prompt composition (step + injections appended) limits patterns | Agents wanting to prepend, insert, or conditionally compose prompts |
| **Weak model performance** | Metacognitive prompts work for strong models but weak models still struggle | gemini-2.0-flash agents not storing lessons despite prompt improvements |

### General Architecture

| Concern | Risk | Watch For |
|---------|------|-----------|
| **Agent-specific code (~30%)** | LLM access, scheduling, workflow execution still privileged | Difficulty adding new "agent-like" patterns, code duplication |
| **Genesis artifact sprawl** | Many genesis artifacts, unclear which are truly needed | Agents confused about which genesis artifact to use, overlapping functionality |

---

## Resolved Concerns

| Concern | Resolution | Date |
|---------|------------|------|
| *None yet* | | |

---

## How to Use This File

1. **Add concerns** when making design decisions with known tradeoffs
2. **Add "Watch For"** - concrete signals that the concern is becoming real
3. **Move to Resolved** when concern is addressed (with explanation)
4. **Create a Plan** if concern becomes a real problem requiring implementation

This is NOT for:
- Bugs (use GitHub issues)
- Features (use plans)
- Decisions already made (use ADRs)
