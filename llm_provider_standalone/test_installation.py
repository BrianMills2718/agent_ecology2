#!/usr/bin/env python3
"""
Test script to verify LLM Provider installation.

Run this after copying to a new project to ensure everything works.

Usage:
    python test_installation.py
"""

import sys
import os


def test_imports():
    """Test that all required packages can be imported."""
    print("Testing imports...")

    try:
        import litellm
        print("  ✅ litellm")
    except ImportError:
        print("  ❌ litellm - run: pip install litellm")
        return False

    try:
        import pydantic
        print("  ✅ pydantic")
    except ImportError:
        print("  ❌ pydantic - run: pip install pydantic")
        return False

    try:
        import jinja2
        print("  ✅ jinja2")
    except ImportError:
        print("  ❌ jinja2 - run: pip install jinja2")
        return False

    try:
        import dotenv
        print("  ✅ python-dotenv")
    except ImportError:
        print("  ❌ python-dotenv - run: pip install python-dotenv")
        return False

    try:
        from llm_provider import LLMProvider
        print("  ✅ llm_provider.py")
    except ImportError as e:
        print(f"  ❌ llm_provider.py - {e}")
        return False

    return True


def test_env_vars():
    """Test that API keys are configured."""
    print("\nTesting environment variables...")

    # Try to load .env
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except:
        pass

    has_key = False

    if os.getenv("OPENAI_API_KEY"):
        print("  ✅ OPENAI_API_KEY is set")
        has_key = True
    else:
        print("  ⚠️  OPENAI_API_KEY not set (required for OpenAI models)")

    if os.getenv("ANTHROPIC_API_KEY"):
        print("  ✅ ANTHROPIC_API_KEY is set")
        has_key = True
    else:
        print("  ⚠️  ANTHROPIC_API_KEY not set (required for Claude models)")

    if os.getenv("GOOGLE_API_KEY"):
        print("  ✅ GOOGLE_API_KEY is set")
        has_key = True
    else:
        print("  ⚠️  GOOGLE_API_KEY not set (required for Gemini models)")

    if not has_key:
        print("\n  ⚠️  No API keys found. Set at least one:")
        print("     1. Create .env file: cp .env.example .env")
        print("     2. Edit .env with your API key")
        return False

    return True


def test_provider_creation():
    """Test that LLMProvider can be instantiated."""
    print("\nTesting provider creation...")

    try:
        from llm_provider import LLMProvider
        provider = LLMProvider(
            model="gpt-5-mini-2025-08-07",
            log_dir="llm_logs"
        )
        print("  ✅ LLMProvider created successfully")
        return True
    except Exception as e:
        print(f"  ❌ Failed to create provider: {e}")
        return False


def test_async_support():
    """Test that async functionality works."""
    print("\nTesting async support...")

    try:
        import asyncio
        print("  ✅ asyncio available")

        # Test that we can create event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        print("  ✅ Event loop created")
        loop.close()
        return True
    except Exception as e:
        print(f"  ❌ Async support error: {e}")
        return False


def test_log_directory():
    """Test that log directory can be created."""
    print("\nTesting log directory...")

    from pathlib import Path
    log_dir = Path("llm_logs")

    try:
        log_dir.mkdir(exist_ok=True)
        print(f"  ✅ Log directory created: {log_dir.absolute()}")
        return True
    except Exception as e:
        print(f"  ❌ Failed to create log directory: {e}")
        return False


def test_live_call():
    """Test a live API call (if API key is set)."""
    print("\nTesting live API call...")

    if not os.getenv("OPENAI_API_KEY"):
        print("  ⚠️  Skipped (no OPENAI_API_KEY)")
        return True

    print("  Making test call to OpenAI (this will use API credits)...")

    try:
        import asyncio
        from llm_provider import LLMProvider

        async def make_call():
            provider = LLMProvider(model="gpt-5-mini-2025-08-07")
            result = await provider.generate_async("Say 'test successful' if you can read this.")
            return result

        result = asyncio.run(make_call())
        print(f"  ✅ API call successful")
        print(f"     Response: {result[:80]}...")
        return True
    except Exception as e:
        print(f"  ❌ API call failed: {e}")
        return False


def main():
    """Run all tests."""
    print("="*80)
    print("LLM Provider - Installation Test")
    print("="*80)

    results = []

    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Environment Variables", test_env_vars()))
    results.append(("Provider Creation", test_provider_creation()))
    results.append(("Async Support", test_async_support()))
    results.append(("Log Directory", test_log_directory()))

    # Optional live test
    if "--live" in sys.argv:
        results.append(("Live API Call", test_live_call()))
    else:
        print("\nSkipping live API call test (use --live to enable)")

    # Summary
    print("\n" + "="*80)
    print("Test Summary")
    print("="*80)

    for name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {name}")

    all_passed = all(passed for _, passed in results)

    if all_passed:
        print("\n🎉 All tests passed! Installation is ready.")
        print("\nNext steps:")
        print("  1. Run examples: python examples.py")
        print("  2. Read docs: README.md")
        print("  3. Check logs: ls llm_logs/")
        return 0
    else:
        print("\n❌ Some tests failed. Please fix the issues above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
