# Plan #318: Agent Cognitive Architecture — Persistent Notebook

**Status:** ✅ Complete

## Problem

Plan #317 simulation revealed that all 3 discourse agents successfully created self-referencing contracts by following error message tutorials, but forgot their own contract IDs within 5 iterations. `action_history[-5:]` scrolled off the contract creation event.

This is a missing cognitive primitive: agents have no persistent memory that survives the action history window.

## Solution

Give agents persistent long-term memory via a **notebook artifact** — a regular artifact (not kernel infrastructure) that the loop code reads every iteration and writes to selectively.

### Notebook Format

```json
{
  "key_facts": {},
  "journal": []
}
```

- **key_facts** — Curated dict. Agent updates explicitly via `notebook_update.key_facts_update` in LLM output.
- **journal** — Append-only log. Loop auto-appends every iteration. Last 20 shown in prompt. Capped at 50.

### Additional: Action History Expansion

- Stored history expanded from 5 to 15 entries
- Prompt shows last 10 entries (keeps prompt concise)

## Changes

| File | Change |
|------|--------|
| `config/genesis/agents/discourse_v2/agent.yaml` | Add notebook artifact |
| `config/genesis/agents/discourse_v2_2/agent.yaml` | Add notebook artifact |
| `config/genesis/agents/discourse_v2_3/agent.yaml` | Add notebook artifact |
| `config/genesis/agents/discourse_v2/initial_notebook.json` | New: empty notebook |
| `config/genesis/agents/discourse_v2_2/initial_notebook.json` | New: empty notebook |
| `config/genesis/agents/discourse_v2_3/initial_notebook.json` | New: empty notebook |
| `config/genesis/agents/discourse_v2/loop_code.py` | Read/write notebook, expand action_history |
| `config/genesis/agents/discourse_v2_2/loop_code.py` | Same (identical file) |
| `config/genesis/agents/discourse_v2_3/loop_code.py` | Same (identical file) |
| `config/genesis/agents/discourse_v2/strategy.md` | Add notebook usage section |
| `config/genesis/agents/discourse_v2_2/strategy.md` | Add notebook usage section |
| `config/genesis/agents/discourse_v2_3/strategy.md` | Add notebook usage section |

## What Does NOT Change

- No kernel changes — notebook is a regular artifact
- No action_executor changes
- No new kernel primitives
- No config.yaml changes

## Verification

Run simulation and confirm:
1. Agents record contract IDs in notebook key_facts after creation
2. Agents use recorded contract IDs for subsequent artifacts (no amnesia)
3. Journal entries accumulate showing iteration history
