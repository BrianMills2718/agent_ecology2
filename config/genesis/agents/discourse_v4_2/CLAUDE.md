# Discourse V4-2 Genesis Agent (The Theorist)

Model-building researcher specializing in pattern recognition, abstraction,
and formal frameworks for discourse analysis. V4 experiment: genuine cognitive
specialization with no prescribed cooperation.

## V4 Design Principles

- **Genuine specialization**: Strength in model building, weakness in empirical grounding
- **No prescribed cooperation**: Bootstrap tasks are self-directed only
- **Persistent aspirations**: Self-evaluation drives discovery of what's missing
- **Same kernel physics**: No scarcity manipulation; same budget/scrip as v3

## Files

| File | Purpose |
|------|---------|
| `agent.yaml` | Manifest defining the 4-artifact cluster |
| `strategy.md` | System prompt with theorist cognitive framework |
| `initial_state.json` | Bootstrap tasks (read corpus, create contract, build model) |
| `initial_notebook.json` | Persistent notebook (key_facts + journal) |
| `loop_code.py` | Cognitive loop (ORIENT-DECIDE-ACT-REFLECT-UPDATE) |

## Architecture

4-artifact cluster:
1. **discourse_v4_2_strategy** - Text artifact with theorist system prompt
2. **discourse_v4_2_state** - JSON artifact with task queue + research state
3. **discourse_v4_2_notebook** - JSON artifact with persistent long-term memory
4. **discourse_v4_2_loop** - Executable artifact with `has_loop=True`
