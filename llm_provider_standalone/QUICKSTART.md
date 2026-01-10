# LLMProvider - Quick Start

A production-ready, standalone LLM wrapper for multi-provider LLM calls with comprehensive logging, response caching, structured output, and retry logic.

---

## Installation

### 1. Copy Files to Your Project
```bash
# Copy entire directory
cp -r llm_provider_standalone/ /path/to/your/project/

# Or copy individual files
cp llm_provider_standalone/llm_provider.py /path/to/your/project/
cp llm_provider_standalone/requirements.txt /path/to/your/project/
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Set Up Environment Variables
```bash
# Create .env file
echo "OPENAI_API_KEY=your_key_here" > .env
```

---

## Quick Start (5 minutes)

### Basic Text Generation
```python
import asyncio
from llm_provider import LLMProvider

async def main():
    provider = LLMProvider(model="gpt-5-mini-2025-08-07")
    result = await provider.generate_async("What is 2+2?")
    print(result)

asyncio.run(main())
```

### Structured Output (Pydantic)
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
        "Generate a person named Alice, age 28, software engineer",
        response_model=Person
    )
    print(person.model_dump_json(indent=2))
```

### Batch Parallel Processing
```python
provider = LLMProvider()

prompts = ["Question 1", "Question 2", "Question 3"]
results = await provider.generate_batch(prompts, max_concurrent=3)

for result in results:
    print(result)
```

### Synchronous Usage (for non-async code)
```python
provider = LLMProvider()
result = provider.generate("What is Python?")  # No await
print(result)
```

---

## Configuration

Edit `config.py` or pass parameters to `LLMProvider()`:

```python
provider = LLMProvider(
    model="gpt-5-mini-2025-08-07",  # or "claude-3-5-sonnet-20241022"
    log_dir="llm_logs",              # Where to store logs
    timeout=300.0,                   # 5 minutes
    max_retries=3,                   # Retry on network errors
    log_retention_days=10            # Auto-delete old logs
)
```

---

## Key Features

✅ **Multi-provider support** (OpenAI, Anthropic, Google, etc.)
✅ **Structured output** via Pydantic models
✅ **Jinja2 templates** for dynamic prompts
✅ **Comprehensive logging** (timestamped JSON files)
✅ **Automatic retry** with exponential backoff
✅ **Batch processing** with rate limiting
✅ **Usage tracking** (tokens, costs, timing)
✅ **Async + sync** APIs

---

## Next Steps

1. **Read full docs:** `README.md` (comprehensive guide)
2. **Run examples:** `python examples.py` (14 working examples)
3. **Check logs:** All calls logged to `llm_logs/YYYYMMDD/` directory

---

## Common Patterns

### Pattern: Simple LLM Call
```python
result = await provider.generate_async("Your prompt here")
```

### Pattern: Structured Output
```python
result = await provider.generate_async(
    "Your prompt",
    response_model=YourPydanticModel
)
```

### Pattern: Template with Variables
```python
result = await provider.generate_async(
    prompt="Explain {{topic}} to a {{level}} developer",
    topic="async/await",
    level="beginner"
)
```

### Pattern: Retry with Custom Model
```python
provider = LLMProvider(
    model="claude-3-5-sonnet-20241022",
    max_retries=5
)
result = await provider.generate_async("Your prompt")
```

---

## Files in This Package

- `llm_provider.py` - Main class (990 lines)
- `config.py` - Configuration settings
- `requirements.txt` - Python dependencies
- `README.md` - Comprehensive documentation
- `examples.py` - 14 working examples
- `QUICKSTART.md` - This file

---

## Support

For detailed documentation, see `README.md` (377 lines of comprehensive guide).

For working code examples, run `python examples.py` (14 different patterns).

For debugging, check logs in `llm_logs/` directory (timestamped JSON files).

---

## License

Portable across projects - use freely in any project.
