#!/usr/bin/env python3
"""
Agent Ecology - Main runner script

Usage:
    python run.py                    # Run with defaults from config/config.yaml
    python run.py --ticks 10         # Override max ticks
    python run.py --agents 1         # Run with only first N agents
    python run.py --dashboard        # Run with HTML dashboard (opens browser)
    python run.py --dashboard-only   # Only run dashboard (view existing run.jsonl)
"""

from __future__ import annotations

# Suppress noisy warnings from dependencies BEFORE importing them
import warnings
import logging
warnings.filterwarnings("ignore", message=".*Pydantic serializer warnings.*")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
logging.getLogger("mem0").setLevel(logging.WARNING)
logging.getLogger("mem0.memory.main").setLevel(logging.WARNING)
logging.getLogger("LiteLLM").setLevel(logging.WARNING)

import sys
import shutil
import asyncio
import webbrowser
import yaml
import argparse
import socket
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Clear llm_provider_standalone cache to ensure fresh code on every run
# (prevents stale bytecode issues after code changes)
_llm_cache = Path(__file__).parent / "llm_provider_standalone" / "__pycache__"
if _llm_cache.exists():
    shutil.rmtree(_llm_cache)

# Load environment variables
load_dotenv()

from src.world import World
from src.simulation import SimulationRunner, load_checkpoint, CheckpointData


def load_config(config_path: str = "config/config.yaml") -> dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        result: dict[str, Any] = yaml.safe_load(f)
        return result


# =============================================================================
# ERROR OBSERVABILITY (Plan #129)
# =============================================================================

# Known model patterns for validation
KNOWN_MODEL_PREFIXES = [
    "gemini/",
    "openai/",
    "anthropic/",
    "gpt-",
    "claude-",
    "gemini-",
]

# Error suggestions for common issues
ERROR_SUGGESTIONS: dict[str, str] = {
    "RateLimitError": "API rate limit hit. Options: 1) Wait and retry, 2) Reduce concurrent agents, 3) Increase rate_limit_delay in config",
    "RESOURCE_EXHAUSTED": "API quota exhausted. Check your billing at https://ai.google.dev/ or https://platform.openai.com/",
    "quota": "API quota exhausted. Check your billing dashboard.",
    "AuthenticationError": "Invalid API key. Check GEMINI_API_KEY or OPENAI_API_KEY in .env",
    "invalid_api_key": "Invalid API key. Check your .env file.",
    "BadRequestError": "Invalid request to LLM API. Check model name and parameters.",
    "properties.*non-empty": "Schema incompatible with model. The interface field may need adjustment.",
    "model_not_found": "Model not found. Check the model name in config.yaml",
    "context_length_exceeded": "Prompt too long. Reduce agent memory or prompt size.",
}


def get_error_suggestion(error_message: str) -> str | None:
    """Get actionable suggestion for an error message.

    Returns suggestion string or None if no match found.
    """
    import re
    error_lower = error_message.lower()
    for pattern, suggestion in ERROR_SUGGESTIONS.items():
        if pattern.lower() in error_lower or re.search(pattern, error_message, re.IGNORECASE):
            return suggestion
    return None


def validate_llm_config(config: dict[str, Any], verbose: bool = True) -> list[str]:
    """Validate LLM configuration at startup.

    Checks:
    - Model name looks valid (known prefix)
    - API key environment variable is set

    Returns list of warning messages (empty if all OK).
    """
    warnings_list: list[str] = []

    llm_config = config.get("llm", {})
    default_model = llm_config.get("default_model", "")

    # Check model name looks valid
    if default_model:
        has_known_prefix = any(
            default_model.startswith(prefix) or prefix in default_model
            for prefix in KNOWN_MODEL_PREFIXES
        )
        if not has_known_prefix:
            warnings_list.append(
                f"Unknown model format: '{default_model}'. "
                f"Expected prefixes: {', '.join(KNOWN_MODEL_PREFIXES[:3])}..."
            )

    # Check for API key based on model
    import os
    if "gemini" in default_model.lower():
        if not os.environ.get("GEMINI_API_KEY"):
            warnings_list.append(
                "GEMINI_API_KEY not set in environment. "
                "Add it to .env file or export it."
            )
    elif "openai" in default_model.lower() or "gpt" in default_model.lower():
        if not os.environ.get("OPENAI_API_KEY"):
            warnings_list.append(
                "OPENAI_API_KEY not set in environment. "
                "Add it to .env file or export it."
            )
    elif "anthropic" in default_model.lower() or "claude" in default_model.lower():
        if not os.environ.get("ANTHROPIC_API_KEY"):
            warnings_list.append(
                "ANTHROPIC_API_KEY not set in environment. "
                "Add it to .env file or export it."
            )

    # Print warnings if verbose
    if verbose and warnings_list:
        print("\n" + "=" * 60)
        print("LLM CONFIGURATION WARNINGS")
        print("=" * 60)
        for warning in warnings_list:
            print(f"  - {warning}")
        print("=" * 60 + "\n")

    return warnings_list


def find_free_port(start_port: int, max_attempts: int = 10) -> int:
    """Find a free port starting from start_port."""
    for offset in range(max_attempts):
        port = start_port + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start_port}-{start_port + max_attempts}")


def run_simulation(
    config: dict[str, Any],
    max_agents: int | None = None,
    verbose: bool = True,
    delay: float | None = None,
    checkpoint: CheckpointData | None = None,
    duration: float | None = None,
) -> World:
    """Run the simulation.

    Args:
        config: Configuration dictionary
        max_agents: Limit number of agents (optional)
        verbose: Print progress (default True)
        delay: Seconds between ticks (defaults to config value)
        checkpoint: Checkpoint data to resume from (optional)
        duration: Seconds to run in autonomous mode (optional)

    Returns:
        The World instance after simulation completes.
    """
    runner = SimulationRunner(
        config=config,
        max_agents=max_agents,
        verbose=verbose,
        delay=delay,
        checkpoint=checkpoint,
    )
    return asyncio.run(runner.run(duration=duration))


async def run_simulation_async(
    config: dict[str, Any],
    max_agents: int | None = None,
    verbose: bool = True,
    delay: float | None = None,
    checkpoint: CheckpointData | None = None,
    duration: float | None = None,
) -> World:
    """Run the simulation asynchronously.

    Args:
        config: Configuration dictionary
        max_agents: Limit number of agents (optional)
        verbose: Print progress (default True)
        delay: Seconds between ticks (defaults to config value)
        checkpoint: Checkpoint data to resume from (optional)
        duration: Seconds to run in autonomous mode (optional)

    Returns:
        The World instance after simulation completes.
    """
    runner = SimulationRunner(
        config=config,
        max_agents=max_agents,
        verbose=verbose,
        delay=delay,
        checkpoint=checkpoint,
    )
    return await runner.run(duration=duration)


async def run_with_dashboard(
    config: dict[str, Any],
    max_agents: int | None = None,
    verbose: bool = True,
    delay: float | None = None,
    checkpoint: CheckpointData | None = None,
    open_browser: bool = True,
    duration: float | None = None,
) -> World:
    """Run simulation with dashboard server in parallel."""
    import uvicorn
    from src.dashboard import create_app

    # Get dashboard config
    dashboard_config = config.get("dashboard", {})
    host = dashboard_config.get("host", "0.0.0.0")
    configured_port = dashboard_config.get("port", 8080)
    port = find_free_port(configured_port)
    if port != configured_port:
        print(f"Port {configured_port} in use, using {port} instead")
    jsonl_file = dashboard_config.get("jsonl_file", "run.jsonl")

    # Create dashboard app in live mode (new simulation - don't parse old logs)
    app = create_app(jsonl_path=jsonl_file, live_mode=True)

    # Create uvicorn server config
    server_config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
    )
    server = uvicorn.Server(server_config)

    # Create simulation runner
    runner = SimulationRunner(
        config=config,
        max_agents=max_agents,
        verbose=verbose,
        delay=delay,
        checkpoint=checkpoint,
    )

    # Open browser after short delay
    async def open_browser_delayed() -> None:
        await asyncio.sleep(1.0)
        url = f"http://localhost:{port}"
        if verbose:
            print(f"\nDashboard available at: {url}")
            print("(Note: In WSL, open this URL manually in your browser)")
        if open_browser:
            webbrowser.open(url)

    # Run both concurrently
    if verbose:
        print(f"Starting dashboard server on port {port}...")

    async def run_server() -> None:
        await server.serve()

    async def run_sim() -> World:
        # Small delay to let server start
        await asyncio.sleep(0.5)
        return await runner.run(duration=duration)

    # Start all tasks
    browser_task = asyncio.create_task(open_browser_delayed())
    server_task = asyncio.create_task(run_server())
    sim_task = asyncio.create_task(run_sim())

    # Wait for simulation to complete
    try:
        world = await sim_task
        # Give dashboard a moment to show final state
        await asyncio.sleep(2.0)
        return world
    finally:
        browser_task.cancel()
        server.should_exit = True
        await asyncio.sleep(0.5)


def run_dashboard_only(config: dict[str, Any]) -> None:
    """Run only the dashboard server (no simulation)."""
    from src.dashboard import run_dashboard

    dashboard_config = config.get("dashboard", {})
    host = dashboard_config.get("host", "0.0.0.0")
    configured_port = dashboard_config.get("port", 8080)
    port = find_free_port(configured_port)
    if port != configured_port:
        print(f"Port {configured_port} in use, using {port} instead")
    jsonl_file = dashboard_config.get("jsonl_file", "run.jsonl")

    print(f"Starting dashboard server on http://localhost:{port}")
    print(f"Monitoring: {jsonl_file}")
    print("Press Ctrl+C to stop")

    webbrowser.open(f"http://localhost:{port}")
    run_dashboard(host=host, port=port, jsonl_path=jsonl_file)


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="Run Agent Ecology simulation"
    )
    parser.add_argument(
        "--config", default="config/config.yaml", help="Path to config file"
    )
    parser.add_argument("--ticks", type=int, help="Override max ticks")
    parser.add_argument("--agents", type=int, help="Limit number of agents")
    parser.add_argument("--quiet", action="store_true", help="Suppress output")
    parser.add_argument(
        "--delay",
        type=float,
        default=None,
        help="Delay between ticks (defaults to config value)",
    )
    parser.add_argument(
        "--resume",
        type=str,
        nargs="?",
        const="checkpoint.json",
        default=None,
        help="Resume from checkpoint file (default: checkpoint.json)",
    )
    parser.add_argument(
        "--dashboard",
        action="store_true",
        help="Run with HTML dashboard (auto-opens browser)",
    )
    parser.add_argument(
        "--dashboard-only",
        action="store_true",
        help="Only run dashboard server (view existing run.jsonl)",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't auto-open browser when using --dashboard",
    )
    parser.add_argument(
        "--duration",
        type=float,
        help="Run in autonomous mode for N seconds (enables continuous agent loops)",
    )
    parser.add_argument(
        "--autonomous",
        action="store_true",
        help="Enable autonomous mode (agents run continuously). Use with --duration.",
    )
    args: argparse.Namespace = parser.parse_args()

    config: dict[str, Any] = load_config(args.config)

    # Validate LLM config at startup (Plan #129)
    validate_llm_config(config, verbose=not args.quiet)

    if args.ticks:
        config["world"]["max_ticks"] = args.ticks

    # Enable autonomous mode if --duration or --autonomous specified
    if args.duration or args.autonomous:
        if "execution" not in config:
            config["execution"] = {}
        config["execution"]["use_autonomous_loops"] = True
        if "rate_limiting" not in config:
            config["rate_limiting"] = {}
        config["rate_limiting"]["enabled"] = True

    # Dashboard-only mode
    if args.dashboard_only:
        run_dashboard_only(config)
        return

    # Load checkpoint if resuming
    checkpoint: CheckpointData | None = None
    if args.resume:
        checkpoint = load_checkpoint(args.resume)
        if checkpoint is None and not args.quiet:
            print(f"Warning: Checkpoint file '{args.resume}' not found. Starting fresh.")

    # Run with or without dashboard
    if args.dashboard:
        asyncio.run(run_with_dashboard(
            config,
            max_agents=args.agents,
            verbose=not args.quiet,
            delay=args.delay,
            checkpoint=checkpoint,
            open_browser=not args.no_browser,
            duration=args.duration,
        ))
    else:
        run_simulation(
            config,
            max_agents=args.agents,
            verbose=not args.quiet,
            delay=args.delay,
            checkpoint=checkpoint,
            duration=args.duration,
        )


if __name__ == "__main__":
    main()
