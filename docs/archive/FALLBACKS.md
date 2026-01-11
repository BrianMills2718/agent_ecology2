# Fallbacks Registry

This document tracks all intentional fallback behaviors in the codebase. Each fallback must:
1. Have clear justification for why it exists
2. Have a feature flag that disables it during development
3. Fail loudly in dev mode, gracefully in production

---

## Active Fallbacks

| ID | Location | Behavior | Justification | Feature Flag |
|----|----------|----------|---------------|--------------|
| (none yet) | | | | |

---

## How to Add a Fallback

1. **Question if you need it** - Can the code just fail loudly instead?
2. **Document here first** - Add entry to table above before implementing
3. **Implement with flag** - Check `config.get("fallbacks.<id>.enabled")`
4. **Default OFF in dev** - `fallbacks.<id>.enabled: false` in config.yaml
5. **Log when triggered** - Always log.warning() when fallback activates

### Example Implementation

```python
# In config.yaml:
# fallbacks:
#   memory_search:
#     enabled: false  # OFF during development

# In code:
from src.config import get

def search_memories(query: str) -> list[dict]:
    try:
        return memory.search(query)
    except ConnectionError as e:
        fallback_enabled = get("fallbacks.memory_search.enabled") or False
        if fallback_enabled:
            logger.warning("Memory search failed, returning empty: %s", e)
            return []
        else:
            # Fail loudly in development
            raise RuntimeError(f"Memory search failed: {e}") from e
```

---

## Anti-Patterns

**DON'T:**
```python
# Silent swallow - hides bugs
except Exception:
    pass

# Undocumented fallback - nobody knows this exists
except APIError:
    return default_value

# Always-on fallback - masks production issues
try:
    result = api_call()
except Exception:
    result = cached_value  # Always falls back
```

**DO:**
```python
# Loud failure in dev, documented fallback in prod
except APIError as e:
    if get("fallbacks.api_cache.enabled"):
        logger.warning("API failed, using cache: %s", e)
        return cached_value
    raise
```

---

## Fallback Review Checklist

When reviewing code with fallbacks:
- [ ] Is the fallback documented in this file?
- [ ] Is there a feature flag?
- [ ] Is the flag OFF by default?
- [ ] Does it log when triggered?
- [ ] Could the code just fail loudly instead?
