# LLMProvider - Universal LLM Abstraction Layer

A robust, production-ready LLM abstraction layer with comprehensive logging, structured output support, and advanced features.

## Features

✅ **Multi-provider support** via LiteLLM (OpenAI, Anthropic, Google, etc.)
✅ **GPT-5-mini optimized** with auto-detection of `responses()` vs `completion()` API
✅ **Structured output** via Pydantic models with JSON schema validation
✅ **Jinja2 templates** with robust special character handling
✅ **Comprehensive logging** - timestamped JSON files for every LLM call
✅ **Async-first design** with sync convenience wrappers
✅ **Batch parallel processing** with rate limiting
✅ **Automatic retry logic** with exponential backoff
✅ **Usage tracking** - tokens, costs, timing, success rates
✅ **Progress callbacks** for long-running operations
✅ **No artificial timeouts** (relies on provider timeouts)

## Installation

```bash
# Install dependencies
pip install -r requirements_llm.txt

# Set up environment variables
echo "OPENAI_API_KEY=your_key_here" > .env
```

## Quick Start

### Basic Text Generation

```python
import asyncio
from llm_provider import LLMProvider

async def main():
    provider = LLMProvider(
        model="gpt-5-mini-2025-08-07",
        log_dir="llm_logs"
    )

    result = await provider.generate_async("What is 2+2?")
    print(result)

asyncio.run(main())
```

### Structured Output with Pydantic

```python
from pydantic import BaseModel
from llm_provider import LLMProvider

class Person(BaseModel):
    name: str
    age: int
    occupation: str

async def main():
    provider = LLMProvider()

    person = await provider.generate_async(
        prompt="Generate a person named Alice, age 28, software engineer",
        response_model=Person
    )

    print(person.model_dump_json(indent=2))
```

### Jinja2 Templates

```python
provider = LLMProvider()

template = """
Generate a {{component_type}} with:
- Name: {{name}}
- Features: {{features|join(', ')}}
"""

result = await provider.generate_async(
    prompt=template,
    component_type="service",
    name="AuthService",
    features=["JWT", "OAuth2", "MFA"]
)
```

### Batch Parallel Processing

```python
provider = LLMProvider(
    progress_callback=lambda p: print(f"Progress: {p['message']}")
)

prompts = ["Question 1", "Question 2", "Question 3"]

results = await provider.generate_batch(
    prompts=prompts,
    max_concurrent=3  # Rate limiting
)
```

### Synchronous Usage

```python
provider = LLMProvider()

# Blocks until complete
result = provider.generate("What is Python?")
print(result)
```

## Key Design Decisions

Based on comprehensive research in `llm_research_examples/`:

### 1. **No Artificial Timeouts**
- Research shows 6+ minutes is normal for complex operations
- Relies on provider timeouts (300s safety maximum)
- Prevents false "hanging" perception

### 2. **GPT-5-mini API Auto-Detection**
- Automatically uses `responses()` API for gpt-5 models
- Uses `completion()` API for other models
- Seamless parameter conversion (max_tokens → max_completion_tokens)

### 3. **Temperature Handling**
- GPT-5-mini doesn't support temperature parameter
- Warns user but continues execution (doesn't error)
- Ignored for gpt-5-mini, passed to other models

### 4. **Comprehensive Logging**
- Every call logged to timestamped JSON file in `llm_logs/`
- Includes: prompt (raw + rendered), response, timing, metadata
- Special character handling via `json.dumps(ensure_ascii=False)`
- Logs both successful and failed calls

### 5. **Robust Special Character Handling**
- Jinja2 with `autoescape=False` for literal prompts
- JSON encoding handles all unicode characters
- Stores both raw and rendered prompts in logs

### 6. **Retry Logic**
- Exponential backoff: 1s, 2s, 4s, 8s
- Retries on: network errors, rate limits, timeouts
- No retry on: auth failures, invalid parameters
- Max 3 retries by default

## API Reference

### LLMProvider Class

```python
LLMProvider(
    model: str = "gpt-5-mini-2025-08-07",
    log_dir: str = "llm_logs",
    timeout: float = 300.0,
    max_retries: int = 3,
    progress_callback: Optional[Callable] = None,
    api_key: Optional[str] = None
)
```

**Parameters:**
- `model`: Model identifier (default: gpt-5-mini-2025-08-07)
- `log_dir`: Directory for timestamped log files
- `timeout`: Request timeout in seconds (default: 300s)
- `max_retries`: Number of retry attempts for retryable errors
- `progress_callback`: Optional callback for progress updates
- `api_key`: Optional API key (uses OPENAI_API_KEY env var if not provided)

### Methods

#### `generate_async(prompt, response_model=None, system_prompt=None, temperature=None, **context)`

Async method for generating LLM responses.

**Parameters:**
- `prompt`: Prompt string or Jinja2 Template
- `response_model`: Optional Pydantic model for structured output
- `system_prompt`: Optional system prompt
- `temperature`: Temperature (ignored for gpt-5-mini with warning)
- `**context`: Context variables for Jinja2 template rendering

**Returns:** Generated text or Pydantic model instance

#### `generate(prompt, response_model=None, system_prompt=None, temperature=None, **context)`

Synchronous wrapper for `generate_async()`. Blocks until complete.

#### `generate_batch(prompts, response_model=None, system_prompt=None, temperature=None, max_concurrent=5, **context)`

Generate responses for multiple prompts in parallel.

**Parameters:**
- `prompts`: List of prompts (strings or Templates)
- `response_model`: Optional Pydantic model for structured output
- `system_prompt`: Optional system prompt (applied to all)
- `temperature`: Temperature (ignored for gpt-5-mini)
- `max_concurrent`: Maximum concurrent requests (rate limiting)
- `**context`: Context variables for Jinja2 template rendering

**Returns:** List of generated results (same order as input prompts)

#### `get_usage_stats()`

Returns usage statistics dictionary:
```python
{
    "total_tokens": int,
    "requests": int,
    "successful_requests": int,
    "failed_requests": int,
    "total_cost": float,
    "total_duration": float,
    "avg_duration": float,
    "success_rate": float
}
```

#### `reset_usage_stats()`

Reset usage statistics to zero.

## Log File Format

Each LLM call creates a timestamped JSON log file:

**Filename format:** `llm_logs/YYYYMMDD_HHMMSS_<request_id>.json`

**Example log structure:**
```json
{
  "timestamp": "2025-11-01T14:30:22.123456",
  "request_id": "abc123def456",
  "model": "gpt-5-mini-2025-08-07",
  "parameters": {
    "temperature": null,
    "max_tokens": null,
    "warnings": ["temperature ignored for gpt-5-mini"],
    "response_model": "Person"
  },
  "prompt": {
    "raw": "Generate a {{name}}...",
    "rendered": "Generate a person...",
    "context": {"name": "person"},
    "system_prompt": null,
    "length_chars": 1234,
    "hash": "sha256:abc123..."
  },
  "response": {
    "content": "{\"name\": \"Alice\", ...}",
    "length_chars": 5678,
    "type": "structured",
    "parsed_model": {"name": "Alice", "age": 28}
  },
  "timing": {
    "start": "2025-11-01T14:30:22.123456",
    "end": "2025-11-01T14:31:15.789012",
    "duration_seconds": 53.665556
  },
  "metadata": {
    "api_method": "responses",
    "success": true,
    "error": null,
    "retry_count": 0,
    "usage": {
      "total_tokens": 2345,
      "prompt_tokens": 345,
      "completion_tokens": 2000
    }
  }
}
```

## Error Handling

### Exception Types

- `LLMError`: Base exception for all LLM errors
- `RetryableError`: Network, rate limit, timeout errors (will retry)
- `PermanentError`: Auth, invalid parameter errors (won't retry)

### Example

```python
from llm_provider import LLMProvider, LLMError

try:
    result = await provider.generate_async("test prompt")
except LLMError as e:
    print(f"LLM error: {e}")
    # Check logs for details
```

## Examples

Run comprehensive examples:
```bash
python example_llm_usage.py
```

Run simple tests:
```bash
python test_llm_simple.py
```

## Research Foundation

This implementation is based on extensive research documented in `llm_research_examples/`:

- **Performance benchmarks**: GPT-5-mini (54.6s avg), Gemini 2.5 Flash (8.1s avg)
- **Timeout analysis**: 6+ minutes is normal for complex operations
- **Hanging investigation**: User experience issue, not technical problem
- **API patterns**: Unified wrapper for responses() and completion() APIs
- **Reliability testing**: Retry logic, error classification, fallback chains

Key research files:
- `llm_research_examples/integration_patterns/litellm_integration/tests/final_working_test.py`
- `llm_research_examples/reliability_investigations/hanging_timeout/CORRECTED_CONCLUSIONS.md`
- `llm_research_examples/model_comparisons/cross_model_analysis/timing_comparisons/TIMING_CONCLUSIONS.md`

## Performance Considerations

### Expected Timings (from research)
- **Simple tasks**: 1-17s
- **Component generation**: 22-89s (avg 54.6s)
- **Complex systems**: 91-101s
- **Multi-component systems**: 6+ minutes total

### Optimization Tips
1. Use `generate_batch()` for parallel processing
2. Set appropriate `max_concurrent` to respect rate limits
3. Use structured output for reliability (Pydantic validation)
4. Monitor logs for performance analysis
5. Consider Gemini 2.5 Flash for 6.7x speedup (when multi-provider support added)

## Limitations & Future Work

### Current Limitations
- Single model at a time (no fallback chain yet)
- No streaming support yet
- No caching layer
- GPT-5-mini only (multi-provider support ready to add)

### Planned Features
- [ ] Multi-provider fallback chain
- [ ] Response streaming for real-time feedback
- [ ] LRU cache for identical prompts
- [ ] Token counting and cost estimation before calls
- [ ] Integration with other models (Anthropic, Google, etc.)
- [ ] Prometheus metrics export
- [ ] Response validation and quality scoring

## Contributing

When adding features, ensure:
1. Comprehensive logging of all operations
2. Robust error handling with classification
3. Special character handling in prompts/responses
4. Tests for new functionality
5. Documentation updates

## License

[Your license here]

## Support

For issues or questions:
1. Check `llm_logs/` for detailed call information
2. Review research documentation in `llm_research_examples/`
3. Run test suite: `python test_llm_simple.py`
4. Check usage stats: `provider.get_usage_stats()`
