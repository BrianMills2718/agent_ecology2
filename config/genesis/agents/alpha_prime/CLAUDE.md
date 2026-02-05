# Alpha Prime Genesis Agent

BabyAGI-style task-driven autonomous agent (Plans #256, #273, #298).

## Files

| File | Purpose |
|------|---------|
| `agent.yaml` | Manifest defining the 3-artifact cluster |
| `strategy.md` | The constitution (system prompt) |
| `initial_state.json` | Initial BabyAGI task queue state |
| `loop_code.py` | The metabolism (executable loop) |

## Architecture

Alpha Prime is a 3-artifact cluster:
1. **alpha_prime_strategy** - Text artifact with system prompt
2. **alpha_prime_state** - JSON artifact with persistent task queue
3. **alpha_prime_loop** - Executable artifact with `has_loop=True`

## Configuration

Enable via `config/config.yaml`:
```yaml
alpha_prime:
  enabled: true
  starting_scrip: 100
  starting_llm_budget: 1.0
  model: gemini/gemini-2.5-flash
```

The model is stored in `initial_state.json` and can be updated at runtime.
