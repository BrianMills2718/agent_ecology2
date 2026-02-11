# Discourse V2 Genesis Agent

Task-driven research agent focused on argument & logic. Hybrid of alpha_prime
task queue + discourse analyst research cycle.

## Files

| File | Purpose |
|------|---------|
| `agent.yaml` | Manifest defining the 4-artifact cluster |
| `strategy.md` | System prompt with argument & logic focus |
| `initial_state.json` | Task queue + research state |
| `initial_notebook.json` | Persistent notebook (key_facts + journal) |
| `loop_code.py` | Hybrid task-driven research loop |

## Architecture

4-artifact cluster:
1. **discourse_v2_strategy** - Text artifact with system prompt
2. **discourse_v2_state** - JSON artifact with task queue + research state
3. **discourse_v2_notebook** - JSON artifact with persistent long-term memory
4. **discourse_v2_loop** - Executable artifact with `has_loop=True`

## Key Differences from V1

- Task queue drives action (not wandering research phases)
- Auto-progression: can't get stuck in "investigating" forever
- Knowledge base accumulates across iterations
- Failed attempts tracked to avoid repetition
- Build-first: initial tasks push creation, not investigation
- Action results feed back into next iteration's context
