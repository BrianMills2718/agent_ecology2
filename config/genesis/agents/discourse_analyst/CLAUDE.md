# Discourse Analyst Genesis Agent

Research agent focused on understanding discourse and arguments (Plan #299).

## Files

| File | Purpose |
|------|---------|
| `agent.yaml` | Manifest defining the 3-artifact cluster |
| `strategy.md` | System prompt with research focus |
| `initial_state.json` | Initial research cycle state |
| `loop_code.py` | Research loop (executable artifact) |

## Architecture

3-artifact cluster:
1. **discourse_analyst_strategy** - Text artifact with system prompt
2. **discourse_analyst_state** - JSON artifact with research state
3. **discourse_analyst_loop** - Executable artifact with `has_loop=True`

## Research Cycle States

- questioning → investigating → building → analyzing → reflecting → questioning

## Configuration

Enable via `config/config.yaml`:
```yaml
discourse_analyst:
  enabled: true
  starting_scrip: 100
  starting_llm_budget: 1.0
```
