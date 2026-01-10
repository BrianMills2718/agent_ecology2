# Response Caching - Quick Guide

Response caching saves API costs and speeds up repeated prompts by storing LLM responses to disk.

---

## Quick Start

```python
from llm_provider import LLMProvider

# Enable caching
provider = LLMProvider(
    cache_dir="llm_cache",      # Where to store cached responses
    cache_ttl=3600              # Cache expires after 1 hour (optional)
)

# First call - hits API, saves to cache
result1 = await provider.generate_async("What is 2+2?")  # ~5s, costs $0.0001

# Second call - reads from cache
result2 = await provider.generate_async("What is 2+2?")  # ~0.001s, costs $0
```

---

## Benefits

✅ **Cost savings:** Only pay for first call, subsequent calls are free
✅ **Speed:** Cache hits return instantly (milliseconds vs seconds)
✅ **Testing:** Run tests repeatedly without API costs
✅ **Development:** Iterate quickly without waiting for API

---

## Configuration

### No caching (default)
```python
provider = LLMProvider()  # No cache_dir = no caching
```

### Cache forever
```python
provider = LLMProvider(cache_dir="llm_cache")  # No TTL = cache forever
```

### Cache with TTL
```python
provider = LLMProvider(
    cache_dir="llm_cache",
    cache_ttl=3600  # Expire after 1 hour (seconds)
)
```

### Disable cache per call
```python
# Skip cache for this specific call
result = await provider.generate_async("prompt", use_cache=False)
```

---

## How It Works

1. **Cache Key:** Hash of (prompt + model + system_prompt + temperature + response_model)
2. **Cache Miss:** No cached response → call API → save to cache
3. **Cache Hit:** Cached response found → return instantly
4. **TTL:** If set, expired entries are deleted automatically

---

## Cache Statistics

```python
stats = provider.get_usage_stats()

print(f"Cache hits: {stats['cache_hits']}")      # Free, instant
print(f"Cache misses: {stats['cache_misses']}")  # Paid API calls
print(f"Hit rate: {stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses']):.1%}")
```

---

## Cache Management

### Clear all cached responses
```python
count = provider.clear_cache()
print(f"Cleared {count} cached responses")
```

### Cache location
```
llm_cache/
├── abc123def456.json  # Cached response for prompt 1
├── 789012ghi345.json  # Cached response for prompt 2
└── ...
```

Each file contains:
```json
{
  "cached_at": "2025-11-05T14:00:00",
  "content": "The answer is 4",
  "response_type": "text",
  "response_model": null,
  "parsed_model": null
}
```

---

## Examples

### Testing (save costs)
```python
import pytest

@pytest.fixture(scope="session")
def llm():
    # Cache responses across all tests
    return LLMProvider(cache_dir="test_cache")

def test_sentiment(llm):
    # First test run: hits API
    # Subsequent runs: reads cache
    result = await llm.generate_async("Analyze: I love this!")
    assert "positive" in result.lower()
```

### Development (iterate quickly)
```python
# Enable caching during development
provider = LLMProvider(
    cache_dir="dev_cache",
    cache_ttl=86400  # 24 hours
)

# Iterate on prompt without waiting
for i in range(10):
    result = await provider.generate_async("same prompt")
    # Only first iteration hits API, rest use cache
```

### Production (selective caching)
```python
provider = LLMProvider(cache_dir="prod_cache", cache_ttl=3600)

# Cache FAQ responses
faq_answer = await provider.generate_async(user_question)  # Cached

# Don't cache personalized responses
personal = await provider.generate_async(
    f"Hello {user.name}",
    use_cache=False  # Always fresh
)
```

---

## Important Notes

**Cache invalidation:**
- Changing any parameter (model, temperature, system_prompt) creates new cache key
- TTL automatically expires old entries
- Use `clear_cache()` to manually reset

**What's cached:**
- Prompt text (rendered, after Jinja2 substitution)
- Response content
- Structured output (Pydantic models)

**What's NOT cached:**
- Streaming responses (`generate_stream`)
- Calls with `use_cache=False`
- Calls when `cache_dir` not set

**Cache size:**
- ~1-10 KB per cached response
- Monitor disk usage for large caches
- Use TTL to auto-cleanup old entries

---

## Best Practices

1. **Use different cache dirs for different purposes:**
   ```python
   test_provider = LLMProvider(cache_dir="test_cache")
   dev_provider = LLMProvider(cache_dir="dev_cache")
   prod_provider = LLMProvider(cache_dir="prod_cache")
   ```

2. **Set appropriate TTL:**
   ```python
   # Static content: long TTL
   docs_provider = LLMProvider(cache_ttl=86400)  # 24 hours

   # Dynamic content: short TTL
   realtime_provider = LLMProvider(cache_ttl=300)  # 5 minutes
   ```

3. **Add cache to .gitignore:**
   ```
   # .gitignore
   llm_cache/
   test_cache/
   dev_cache/
   ```

4. **Monitor cache effectiveness:**
   ```python
   stats = provider.get_usage_stats()
   hit_rate = stats['cache_hits'] / (stats['cache_hits'] + stats['cache_misses'])

   if hit_rate < 0.3:
       print("⚠️ Low cache hit rate - consider longer TTL")
   ```

---

## Troubleshooting

**Q: Why isn't my response being cached?**
- Check `cache_dir` is set
- Check `use_cache=True` (default)
- Verify disk write permissions

**Q: Why did I get a cache miss?**
- Prompt changed slightly (whitespace, capitalization)
- Parameters changed (temperature, model, etc.)
- Cache expired (TTL)
- Cache was cleared

**Q: How do I force a fresh response?**
```python
result = await provider.generate_async("prompt", use_cache=False)
```

---

## Summary

**Enable caching:**
```python
provider = LLMProvider(cache_dir="llm_cache", cache_ttl=3600)
```

**Benefits:**
- ✅ Free repeated calls
- ✅ Instant responses
- ✅ Perfect for testing/development

**Cost savings example:**
- Without cache: 100 tests × $0.0001 = $0.01 per run
- With cache: First run $0.01, subsequent runs $0

See `README.md` for full documentation.
