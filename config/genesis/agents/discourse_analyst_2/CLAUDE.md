# Discourse Analyst 2 Genesis Agent

Research agent focused on understanding narrative (Plan #299).

## Files

| File | Purpose |
|------|---------|
| `agent.yaml` | Manifest defining the 3-artifact cluster |
| `strategy.md` | System prompt with narrative focus |
| `initial_state.json` | Initial research cycle state |
| `loop_code.py` | Research loop (executable artifact) |

## Architecture

3-artifact cluster:
1. **discourse_analyst_2_strategy** - Text artifact with system prompt
2. **discourse_analyst_2_state** - JSON artifact with research state
3. **discourse_analyst_2_loop** - Executable artifact with `has_loop=True`

## Research Focus

- Temporal structure in narratives
- Causal chains and what drives stories
- Character agency and motivation
- Thematic patterns
