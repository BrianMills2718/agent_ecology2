# Discourse V3-2 Genesis Agent (Cross-Agent Smoke Test)

Task-driven research agent focused on narrative & sequence. Same domains as V2,
with explicit cross-agent interaction guidance to smoke-test the plumbing.

## V3 vs V2 Differences

- **Reuse Before Build** principle added to strategy
- **Open contract template** — allows all reads/invokes, creator-only writes
- **Cross-agent tasks** in initial queue (discover, invoke, pay, combine)
- **Cross-domain examples** in strategy showing how to use other agents' tools

## Files

| File | Purpose |
|------|---------|
| `agent.yaml` | Manifest defining the 4-artifact cluster |
| `strategy.md` | System prompt with narrative & sequence focus + cross-agent guidance |
| `initial_state.json` | Task queue with cross-agent interaction tasks |
| `initial_notebook.json` | Persistent notebook (key_facts + journal) |
| `loop_code.py` | Hybrid task-driven research loop |

## Architecture

4-artifact cluster:
1. **discourse_v3_2_strategy** - Text artifact with system prompt
2. **discourse_v3_2_state** - JSON artifact with task queue + research state
3. **discourse_v3_2_notebook** - JSON artifact with persistent long-term memory
4. **discourse_v3_2_loop** - Executable artifact with `has_loop=True`
