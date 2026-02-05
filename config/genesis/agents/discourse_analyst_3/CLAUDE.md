# Discourse Analyst 3 Genesis Agent

Research agent focused on understanding rhetoric (Plan #299).

## Files

| File | Purpose |
|------|---------|
| `agent.yaml` | Manifest defining the 3-artifact cluster |
| `strategy.md` | System prompt with rhetoric focus |
| `initial_state.json` | Initial research cycle state |
| `loop_code.py` | Research loop (executable artifact) |

## Architecture

3-artifact cluster:
1. **discourse_analyst_3_strategy** - Text artifact with system prompt
2. **discourse_analyst_3_state** - JSON artifact with research state
3. **discourse_analyst_3_loop** - Executable artifact with `has_loop=True`

## Research Focus

- Appeals (ethos, pathos, logos)
- Framing and contextualization
- Audience analysis
- Persuasion patterns
