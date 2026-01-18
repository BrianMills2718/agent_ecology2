# Plan 93: Agent Resource Visibility

**Status:** 📋 Deferred
**Priority:** Medium
**Blocked By:** #95 (Unified Resource System)
**Blocks:** None

---

## Gap

**Current:** Agents don't see their LLM budget consumption - only scrip balance.

**Target:** Agents see resource consumption in context for self-regulation.

**Why Medium:** Deferred until ResourceManager (#95) provides clean interface.

---

## Files Affected

- `src/agents/agent.py` (modify) - Add resource info to context

---

## Notes

Deferred until ResourceManager exists with clean `get_available(agent, resource)` API.
