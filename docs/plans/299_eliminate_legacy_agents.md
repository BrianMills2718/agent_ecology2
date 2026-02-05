# Plan #299: Eliminate Legacy Agent System - Agents as Pure Artifacts

**Status:** 🚧 In Progress
**Priority:** High
**Theme:** Architecture Simplification

---

## Problem

Two parallel systems exist for agents:

1. **Legacy system** (`src/agents/`): ~9000 lines
   - `agent.py` (108KB) - massive LLM wrapper with 77 methods
   - `workflow.py` (45KB) - state machine engine
   - Creates its own `LLMProvider`, bypasses kernel

2. **Artifact system** (alpha_prime): ~200 lines
   - Uses kernel primitive `_syscall_llm()` in executor.py
   - State stored in JSON artifact
   - Clean, aligned with "everything is an artifact"

The legacy system contradicts the thesis that agents are emergent patterns of artifact activity.

---

## Goal

- Delete `src/agents/*.py` (~9000 lines)
- Delete all agent directories
- Convert discourse_analyst variants to artifact-based
- Agents = executable artifact + state artifact + prompt artifact

---

## Implementation

### Phase 1: Create discourse_analyst artifacts
- `config/genesis/agents/discourse_analyst/` (4 files each × 3 variants)
- agent.yaml, strategy.md, initial_state.json, loop_code.py

### Phase 2: Update runner.py
- Remove legacy agent loading
- Use artifact loops only

### Phase 3: Delete legacy code
- `src/agents/*.py` (~15 files)
- `src/agents/*/` (~18 directories)

### Phase 4: Cleanup
- Move catalog.yaml to docs/
- Update tests
- Update docs

---

## Files Changed

| Action | Files |
|--------|-------|
| Create | `config/genesis/agents/discourse_analyst*/` |
| Delete | `src/agents/*.py`, `src/agents/*/` |
| Modify | `src/simulation/runner.py` |
| Move | `src/agents/catalog.yaml` → `docs/` |

---

## Acceptance Criteria

- [ ] Discourse analyst runs as artifact-based agent
- [ ] `src/agents/` contains only __init__.py and CLAUDE.md
- [ ] `make run DURATION=60` works
- [ ] `make check` passes
