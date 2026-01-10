# LLM Provider - Portable Package

This directory contains a **fully standalone, production-ready LLM wrapper** that can be copied to any Python project.

---

## What's Inside

```
llm_provider_standalone/
├── llm_provider.py        # Main class (990 lines) - Core functionality
├── config.py              # Configuration settings (optional)
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variable template
├── README.md             # Comprehensive documentation (377 lines)
├── QUICKSTART.md         # 5-minute getting started guide
├── examples.py           # 14 working examples (709 lines)
└── PORTABLE_PACKAGE.md   # This file
```

**Total:** 8 files, ~2,200 lines of code + documentation

---

## Zero Dependencies on AutoCoder

✅ **Completely standalone** - no imports from parent project
✅ **Only standard dependencies** - litellm, pydantic, jinja2, python-dotenv
✅ **Works anywhere** - just copy and go

---

## Quick Copy to Another Project

### Option 1: Copy Entire Directory
```bash
# Copy to your project
cp -r llm_provider_standalone/ /path/to/your/project/llm_provider/

# Install dependencies
cd /path/to/your/project/llm_provider/
pip install -r requirements.txt

# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Test it
python examples.py
```

### Option 2: Copy Just Core Files (Minimal)
```bash
# Copy only essential files
cp llm_provider_standalone/llm_provider.py /path/to/your/project/
cp llm_provider_standalone/requirements.txt /path/to/your/project/

# Install and use
pip install -r requirements.txt
```

---

## Usage in Your Project

### Import and Use
```python
# From your Python code
from llm_provider import LLMProvider

# Basic usage
provider = LLMProvider(model="gpt-5-mini-2025-08-07")
result = await provider.generate_async("Your prompt here")
```

### As a Class Attribute
```python
class YourApplication:
    def __init__(self):
        self.llm = LLMProvider()

    async def your_method(self, text):
        return await self.llm.generate_async(f"Process: {text}")
```

### With Custom Config
```python
provider = LLMProvider(
    model="claude-3-5-sonnet-20241022",
    max_retries=5,
    timeout=600.0,
    log_dir="my_llm_logs",
    log_retention_days=7
)
```

---

## Key Features

✅ **Multi-provider:** OpenAI, Anthropic, Google (via LiteLLM)
✅ **Structured output:** Pydantic models with validation
✅ **Templates:** Jinja2 for dynamic prompts
✅ **Logging:** Timestamped JSON files for debugging
✅ **Retry logic:** Exponential backoff with smart error classification
✅ **Batch processing:** Parallel execution with rate limiting
✅ **Async + Sync:** Both APIs supported
✅ **Usage tracking:** Tokens, costs, timing, success rates

---

## Documentation Hierarchy

**Start here:**
1. `QUICKSTART.md` - 5-minute tutorial (if new)
2. `examples.py` - Run 14 working examples
3. `README.md` - Comprehensive guide (if you need deep dive)

**For developers:**
- `llm_provider.py` - Read inline docstrings
- `config.py` - See all configuration options

---

## Example Use Cases

### 1. Simple Text Generation
```python
result = await provider.generate_async("What is Python?")
```

### 2. Structured Data Extraction
```python
class Person(BaseModel):
    name: str
    age: int

person = await provider.generate_async(
    "Extract person: John, 30",
    response_model=Person
)
```

### 3. Batch Processing
```python
prompts = ["Q1", "Q2", "Q3"]
results = await provider.generate_batch(prompts, max_concurrent=3)
```

### 4. Template-Based Prompts
```python
result = await provider.generate_async(
    prompt="Explain {{topic}} to a {{level}} developer",
    topic="async/await",
    level="beginner"
)
```

---

## Testing After Copy

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set up .env
echo "OPENAI_API_KEY=your_key" > .env

# 3. Run examples
python examples.py

# 4. Check logs
ls -la llm_logs/
```

---

## Configuration

### Environment Variables (.env)
```bash
OPENAI_API_KEY=sk-...           # Required for GPT models
ANTHROPIC_API_KEY=sk-ant-...    # Required for Claude models
GOOGLE_API_KEY=...              # Required for Gemini models
```

### Python Config (config.py)
```python
LLM_CONFIG = {
    "model": "gpt-5-mini-2025-08-07",
    "max_retries": 3,
    "timeout": 300.0,
    "log_dir": "llm_logs",
    "log_retention_days": 10,
}
```

---

## Production-Ready Features

### Logging
- Every call logged to `llm_logs/YYYYMMDD/YYYYMMDD_HHMMSS_<id>.json`
- Includes: prompt, response, timing, usage, errors
- Automatic cleanup after N days (configurable)

### Error Handling
- Smart classification: retryable vs permanent errors
- Exponential backoff: 1s, 2s, 4s, 8s
- Max retries configurable (default: 3)

### Usage Tracking
```python
stats = provider.get_usage_stats()
# Returns: requests, tokens, costs, duration, success_rate
```

---

## Research-Backed Design

This implementation is based on extensive research:
- **Timeout analysis:** 6+ minutes is normal for complex operations
- **GPT-5-mini quirks:** Auto-detects responses() vs completion() API
- **Special characters:** Robust Jinja2 + JSON encoding
- **Retry logic:** Smart error classification (network vs auth)

See original project's `llm_research_examples/` for research findings.

---

## License & Support

**Portable:** Use freely in any project
**Maintained:** Part of AutoCoder5 project
**Support:** Check README.md for comprehensive docs

---

## Summary

This package provides everything you need for production-grade LLM calls:
- ✅ Copy 8 files (or just 2 minimal files)
- ✅ Install 4 dependencies
- ✅ Set 1 environment variable
- ✅ Start calling LLMs with retry logic, logging, and structured output

**Next step:** Copy to your project and run `python examples.py`
