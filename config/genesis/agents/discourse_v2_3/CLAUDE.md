# Discourse V2-3 Genesis Agent

Task-driven research agent focused on rhetoric & persuasion. Hybrid of alpha_prime
task queue + discourse analyst research cycle.

## Files

| File | Purpose |
|------|---------|
| `agent.yaml` | Manifest defining the 4-artifact cluster |
| `strategy.md` | System prompt with rhetoric & persuasion focus |
| `initial_state.json` | Task queue + research state |
| `initial_notebook.json` | Persistent notebook (key_facts + journal) |
| `loop_code.py` | Hybrid task-driven research loop (shared with v2 variants) |

## Architecture

4-artifact cluster:
1. **discourse_v2_3_strategy** - Text artifact with system prompt
2. **discourse_v2_3_state** - JSON artifact with task queue + research state
3. **discourse_v2_3_notebook** - JSON artifact with persistent long-term memory
4. **discourse_v2_3_loop** - Executable artifact with `has_loop=True`
