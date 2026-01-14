# Prompts Directory

Prompt templates and schemas for LLM interactions.

## Purpose

Centralized prompt management for agent LLM calls. Prompts are loaded from here rather than hardcoded in Python.

## Files

| File | Purpose |
|------|---------|
| `action_schema.md` | Schema for agent action responses |

## Usage

Prompts are loaded via config:

```python
from src.config import get

schema = get("prompts.action_schema")  # If configured
# Or load directly from file
```

## Writing Prompts

1. Use markdown format for readability
2. Include clear structure (sections, examples)
3. Define expected output format explicitly
4. Test with real LLM calls before committing

## Related

- `src/agents/` - Agent code that uses these prompts
- `config/config.yaml` - Prompt configuration
