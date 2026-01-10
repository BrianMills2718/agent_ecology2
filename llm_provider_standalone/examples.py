#!/usr/bin/env python3
"""
LLM Provider Usage Examples

Consolidated examples showing all usage patterns:
1. Simple usage (sequential unstructured)
2. Structured output (Pydantic models)
3. Parallel processing (batch)
4. Templates (Jinja2)
5. Mixed patterns
6. Real-world application patterns

See also: GUIDE.md for detailed explanations
"""

import asyncio
import time
from pydantic import BaseModel, Field
from typing import List
from jinja2 import Template

# Import from same directory
from llm_provider import LLMProvider


# ============================================================================
# STRUCTURED OUTPUT MODELS
# ============================================================================

class Person(BaseModel):
    """Example person model"""
    name: str
    age: int
    occupation: str
    active: bool = True


class City(BaseModel):
    """Example city model"""
    name: str
    country: str
    population: int
    famous_for: str


class CodeExample(BaseModel):
    """Example code generation model"""
    language: str
    code: str
    explanation: str


class Analysis(BaseModel):
    """Example analysis model"""
    summary: str
    key_points: List[str]
    sentiment: str  # positive, negative, neutral


class MathProblem(BaseModel):
    """Example with special characters"""
    problem: str
    solution: str
    explanation: str


# ============================================================================
# SECTION 1: SIMPLE USAGE
# ============================================================================

async def example_1_simple_text():
    """
    Simplest usage - just call generate_async() with a prompt.

    When to use:
    - Single prompt
    - Plain text response
    - No special formatting needed
    """
    print("\n" + "="*80)
    print("EXAMPLE 1: Simple Text Generation")
    print("="*80)

    provider = LLMProvider(model="gpt-5-mini-2025-08-07")

    result = await provider.generate_async("What is 2+2? Explain briefly.")
    print(f"Result: {result}")


# ============================================================================
# SECTION 2: STRUCTURED OUTPUT
# ============================================================================

async def example_2_structured():
    """
    Get structured data back as Pydantic models.

    When to use:
    - Need to parse/validate output
    - Specific data format required
    - Type safety important
    - Integrate with database/API
    """
    print("\n" + "="*80)
    print("EXAMPLE 2: Structured Output (Pydantic)")
    print("="*80)

    provider = LLMProvider(model="gpt-5-mini-2025-08-07")

    # Get Pydantic model back
    person = await provider.generate_async(
        prompt="Generate a person named Alice who is 28 years old and works as a software engineer",
        response_model=Person
    )

    print(f"Person: {person.model_dump_json(indent=2)}")
    print(f"Type: {type(person)}")  # <class 'Person'>

    # Access fields with type safety
    print(f"\nName: {person.name}")
    print(f"Age: {person.age}")
    print(f"Occupation: {person.occupation}")


async def example_3_structured_city():
    """
    Another structured example with more complex data.
    """
    print("\n" + "="*80)
    print("EXAMPLE 3: Structured Output (City)")
    print("="*80)

    provider = LLMProvider(model="gpt-5-mini-2025-08-07")

    city = await provider.generate_async(
        "Tell me about Paris, France",
        response_model=City
    )

    print(f"City: {city.name}, {city.country}")
    print(f"Population: {city.population:,}")
    print(f"Famous for: {city.famous_for}")


# ============================================================================
# SECTION 3: PARALLEL PROCESSING
# ============================================================================

async def example_4_parallel_unstructured():
    """
    Process multiple prompts in parallel (unstructured text).

    When to use:
    - Multiple independent prompts
    - Need faster total execution
    - Batch processing
    - No dependencies between prompts
    """
    print("\n" + "="*80)
    print("EXAMPLE 4: Parallel + Unstructured")
    print("="*80)

    provider = LLMProvider(model="gpt-5-mini-2025-08-07")

    prompts = [
        "What is Python?",
        "What is JavaScript?",
        "What is Rust?",
    ]

    start = time.time()
    results = await provider.generate_batch(prompts, max_concurrent=3)
    duration = time.time() - start

    for prompt, result in zip(prompts, results):
        if isinstance(result, Exception):
            print(f"❌ {prompt}: {result}")
        else:
            print(f"✅ {prompt}: {result[:60]}...")

    print(f"\n⏱️  Duration: {duration:.1f}s (parallel)")


async def example_5_parallel_structured():
    """
    Process multiple prompts in parallel (structured Pydantic models).

    When to use:
    - Multiple independent prompts
    - Need structured output
    - Batch processing with validation
    """
    print("\n" + "="*80)
    print("EXAMPLE 5: Parallel + Structured")
    print("="*80)

    provider = LLMProvider(model="gpt-5-mini-2025-08-07")

    prompts = [
        "Tell me about Paris",
        "Tell me about Tokyo",
        "Tell me about New York",
    ]

    start = time.time()
    cities = await provider.generate_batch(
        prompts,
        response_model=City,
        max_concurrent=3
    )
    duration = time.time() - start

    for city in cities:
        if isinstance(city, Exception):
            print(f"❌ Error: {city}")
        else:
            print(f"City: {city.name}, {city.country} - Pop: {city.population:,}")

    print(f"\n⏱️  Duration: {duration:.1f}s (parallel)")


# ============================================================================
# SECTION 4: TEMPLATES (JINJA2)
# ============================================================================

async def example_6_templates():
    """
    Use Jinja2 templates for dynamic prompts.

    When to use:
    - Prompts with variable data
    - Reusable prompt templates
    - Complex prompt construction
    """
    print("\n" + "="*80)
    print("EXAMPLE 6: Jinja2 Templates")
    print("="*80)

    provider = LLMProvider(model="gpt-5-mini-2025-08-07")

    template = """
Explain {{concept}} to a {{level}} programmer.
Focus on: {{', '.join(topics)}}
Keep it under {{max_words}} words.
"""

    result = await provider.generate_async(
        prompt=template,
        concept="async/await",
        level="beginner",
        topics=["syntax", "use cases", "common pitfalls"],
        max_words=150
    )

    print(f"Result:\n{result}")


# ============================================================================
# SECTION 5: SPECIAL CHARACTERS & EDGE CASES
# ============================================================================

async def example_7_special_characters():
    """
    Handle prompts with special characters, math symbols, etc.

    When to use:
    - Math/science problems
    - Code with special chars
    - International characters
    """
    print("\n" + "="*80)
    print("EXAMPLE 7: Special Characters")
    print("="*80)

    provider = LLMProvider(model="gpt-5-mini-2025-08-07")

    special_prompt = """
Solve this math problem and explain:

Problem: "What is ∫(x² + 2x) dx from x=0 to x=5?"

Include symbols like: ≤, ≥, ∑, ∏, √, π in your explanation.
"""

    result = await provider.generate_async(
        prompt=special_prompt,
        response_model=MathProblem
    )

    print(f"Problem: {result.problem}")
    print(f"Solution: {result.solution}")
    print(f"Explanation: {result.explanation[:100]}...")


# ============================================================================
# SECTION 6: MIXED PATTERNS
# ============================================================================

async def example_8_mixed():
    """
    Mix structured and unstructured in the same workflow.

    When to use:
    - Different outputs for different tasks
    - Some need validation, some don't
    - Flexible workflow
    """
    print("\n" + "="*80)
    print("EXAMPLE 8: Mixed Structured + Unstructured")
    print("="*80)

    provider = LLMProvider(model="gpt-5-mini-2025-08-07")

    # Unstructured text
    summary = await provider.generate_async(
        "Summarize Python in one sentence"
    )
    print(f"Summary (text): {summary}")

    # Structured data
    city = await provider.generate_async(
        "Tell me about London",
        response_model=City
    )
    print(f"\nCity (structured): {city.name}, {city.country}")

    # More unstructured
    explanation = await provider.generate_async(
        "Explain decorators briefly"
    )
    print(f"\nExplanation (text): {explanation[:100]}...")


async def example_9_complex_parallel():
    """
    Process different types in parallel using asyncio.gather.

    When to use:
    - Multiple different tasks at once
    - Mix of structured/unstructured
    - Maximum performance
    """
    print("\n" + "="*80)
    print("EXAMPLE 9: Complex Parallel (Different output types)")
    print("="*80)

    provider = LLMProvider(model="gpt-5-mini-2025-08-07")

    start = time.time()

    # Run different tasks in parallel
    results = await asyncio.gather(
        provider.generate_async("What is Python?"),
        provider.generate_async("Tell me about Berlin", response_model=City),
        provider.generate_async("Explain decorators briefly"),
        provider.generate_async(
            "Show me a Python list comprehension example",
            response_model=CodeExample
        ),
    )

    duration = time.time() - start

    text1, city, text2, code = results

    print(f"Text 1: {text1[:60]}...")
    print(f"City: {city.name}, {city.country}")
    print(f"Text 2: {text2[:60]}...")
    print(f"Code: {code.language} - {code.explanation[:50]}...")

    print(f"\n⏱️  Duration: {duration:.1f}s")


# ============================================================================
# SECTION 7: SYNCHRONOUS USAGE
# ============================================================================

def example_10_sync():
    """
    Use synchronous wrapper for non-async code.

    When to use:
    - Can't use async/await
    - Simple scripts
    - Interactive use
    """
    print("\n" + "="*80)
    print("EXAMPLE 10: Synchronous Usage")
    print("="*80)

    provider = LLMProvider(model="gpt-5-mini-2025-08-07")

    # Use .generate() instead of .generate_async()
    result = provider.generate("What is machine learning? One sentence.")

    print(f"Result: {result}")


# ============================================================================
# SECTION 8: PROGRESS & STATS
# ============================================================================

async def example_11_progress():
    """
    Track progress with callbacks.

    When to use:
    - Long-running batch operations
    - User feedback needed
    - Progress bars/logging
    """
    print("\n" + "="*80)
    print("EXAMPLE 11: Progress Tracking")
    print("="*80)

    def progress_callback(info):
        print(f"  Progress: {info['message']}")

    provider = LLMProvider(
        model="gpt-5-mini-2025-08-07",
        progress_callback=progress_callback
    )

    prompts = [
        "What is Python?",
        "What is JavaScript?",
        "What is Rust?",
    ]

    print(f"Processing {len(prompts)} prompts...")
    results = await provider.generate_batch(
        prompts,
        max_concurrent=3,
        system_prompt="Answer in one sentence only."
    )

    print(f"\nCompleted {len(results)} prompts")


async def example_12_stats():
    """
    Get usage statistics.

    When to use:
    - Monitor API usage
    - Track costs
    - Performance analysis
    """
    print("\n" + "="*80)
    print("EXAMPLE 12: Usage Statistics")
    print("="*80)

    provider = LLMProvider(model="gpt-5-mini-2025-08-07")

    # Make some calls
    await provider.generate_async("Test 1")
    await provider.generate_async("Test 2")
    await provider.generate_async("Test 3")

    # Get stats
    stats = provider.get_usage_stats()
    print(f"Statistics:")
    print(f"  Total requests: {stats['requests']}")
    print(f"  Successful: {stats['successful_requests']}")
    print(f"  Failed: {stats['failed_requests']}")
    print(f"  Success rate: {stats.get('success_rate', 0)*100:.1f}%")
    print(f"  Total tokens: {stats['total_tokens']}")
    print(f"  Total cost: ${stats['total_cost']:.4f}")


# ============================================================================
# SECTION 9: REAL-WORLD APPLICATION PATTERN
# ============================================================================

class MyApplication:
    """Example of how to use in a real application"""

    def __init__(self):
        # Initialize provider once in __init__
        self.llm = LLMProvider(model="gpt-5-mini-2025-08-07")

    async def analyze_text(self, text: str) -> str:
        """Analyze text using LLM"""
        return await self.llm.generate_async(
            f"Analyze this text and summarize: {text}"
        )

    async def translate(self, text: str, target_lang: str) -> str:
        """Translate text"""
        return await self.llm.generate_async(
            f"Translate to {target_lang}: {text}"
        )

    async def generate_code(self, description: str) -> CodeExample:
        """Generate code from description"""
        return await self.llm.generate_async(
            f"Generate Python code for: {description}",
            response_model=CodeExample
        )


async def example_13_real_world():
    """
    Real-world application pattern.

    When to use:
    - Building an application
    - Reusable LLM interface
    - Clean architecture
    """
    print("\n" + "="*80)
    print("EXAMPLE 13: Real-World Application Pattern")
    print("="*80)

    app = MyApplication()

    # Use the app methods
    summary = await app.analyze_text(
        "Python is a high-level programming language known for readability..."
    )
    print(f"Summary: {summary[:100]}...")

    translation = await app.translate("Hello world", "Spanish")
    print(f"Translation: {translation}")

    code = await app.generate_code("function to calculate factorial")
    print(f"Code generated: {code.language}")
    print(f"Explanation: {code.explanation[:60]}...")


# ============================================================================
# SECTION 10: PERFORMANCE COMPARISON
# ============================================================================

async def example_14_performance():
    """
    Compare performance of sequential vs parallel.

    Shows: Parallel is much faster for independent tasks
    """
    print("\n" + "="*80)
    print("EXAMPLE 14: Performance Comparison (Sequential vs Parallel)")
    print("="*80)

    provider = LLMProvider(model="gpt-5-mini-2025-08-07")

    prompts = [
        "What is Python?",
        "What is Rust?",
        "What is Go?",
        "What is JavaScript?",
        "What is TypeScript?",
    ]

    # Sequential
    print(f"\nProcessing {len(prompts)} prompts sequentially...")
    start = time.time()
    for prompt in prompts:
        await provider.generate_async(prompt)
    seq_duration = time.time() - start
    print(f"⏱️  Sequential: {seq_duration:.1f}s")

    # Parallel
    print(f"\nProcessing {len(prompts)} prompts in parallel...")
    start = time.time()
    await provider.generate_batch(prompts, max_concurrent=5)
    par_duration = time.time() - start
    print(f"⏱️  Parallel: {par_duration:.1f}s")

    speedup = seq_duration / par_duration
    print(f"\n🚀 Speedup: {speedup:.1f}x faster with parallel processing!")


# ============================================================================
# DECISION GUIDE
# ============================================================================

def print_decision_guide():
    """Guide for choosing the right approach"""
    print("\n" + "="*80)
    print("DECISION GUIDE: When to Use What")
    print("="*80)

    print("""
╔══════════════════════════════════════════════════════════════════════════╗
║ WHEN TO USE SEQUENTIAL vs PARALLEL                                      ║
╚══════════════════════════════════════════════════════════════════════════╝

SEQUENTIAL (one at a time):
  ✅ Results depend on each other
  ✅ Rate limiting concerns
  ✅ Simple workflow
  ✅ Single prompt

PARALLEL (all at once):
  ✅ Multiple independent prompts
  ✅ Need faster total execution
  ✅ Batch processing
  ✅ No dependencies

╔══════════════════════════════════════════════════════════════════════════╗
║ WHEN TO USE UNSTRUCTURED vs STRUCTURED                                  ║
╚══════════════════════════════════════════════════════════════════════════╝

UNSTRUCTURED (plain text):
  ✅ Natural language output
  ✅ Summaries, explanations
  ✅ Creative writing
  ✅ Don't need to parse

STRUCTURED (Pydantic):
  ✅ Need to parse/validate
  ✅ Specific data format required
  ✅ Type safety important
  ✅ Integrate with database/API

╔══════════════════════════════════════════════════════════════════════════╗
║ QUICK REFERENCE                                                         ║
╚══════════════════════════════════════════════════════════════════════════╝

Sequential + Unstructured:
  await provider.generate_async("prompt")

Parallel + Unstructured:
  await provider.generate_batch(prompts)

Sequential + Structured:
  await provider.generate_async("prompt", response_model=Model)

Parallel + Structured:
  await provider.generate_batch(prompts, response_model=Model)

Mixed:
  await asyncio.gather(...)

Synchronous:
  provider.generate("prompt")  # No await
""")


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("LLM PROVIDER - COMPREHENSIVE EXAMPLES")
    print("="*80)
    print("\nSee GUIDE.md for detailed explanations of each pattern")

    try:
        # Section 1: Simple
        await example_1_simple_text()

        # Section 2: Structured
        await example_2_structured()
        await example_3_structured_city()

        # Section 3: Parallel
        await example_4_parallel_unstructured()
        await example_5_parallel_structured()

        # Section 4: Templates
        await example_6_templates()

        # Section 5: Edge cases
        await example_7_special_characters()

        # Section 6: Mixed
        await example_8_mixed()
        await example_9_complex_parallel()

        # Section 7: Sync
        example_10_sync()

        # Section 8: Progress & Stats
        await example_11_progress()
        await example_12_stats()

        # Section 9: Real-world
        await example_13_real_world()

        # Section 10: Performance
        await example_14_performance()

        # Decision guide
        print_decision_guide()

        print("\n" + "="*80)
        print("✅ ALL EXAMPLES COMPLETED")
        print("="*80)
        print("\nCheck 'llm_logs/' directory for detailed logs of each call.")
        print("See GUIDE.md for more detailed explanations.")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
