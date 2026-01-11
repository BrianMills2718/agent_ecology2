#!/usr/bin/env python3
"""
Agent Ecology - Main runner script

Usage:
    python run.py                    # Run with defaults from config/config.yaml
    python run.py --ticks 10         # Override max ticks
    python run.py --agents 1         # Run with only first N agents
"""

from __future__ import annotations

import sys
import yaml
import argparse
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from world import World
from simulation import SimulationRunner, load_checkpoint, CheckpointData


def load_config(config_path: str = "config/config.yaml") -> dict[str, Any]:
    """Load configuration from YAML file."""
    with open(config_path) as f:
        result: dict[str, Any] = yaml.safe_load(f)
        return result


def run_simulation(
    config: dict[str, Any],
    max_agents: int | None = None,
    verbose: bool = True,
    delay: float | None = None,
    checkpoint: CheckpointData | None = None,
) -> World:
    """Run the simulation.

    Args:
        config: Configuration dictionary
        max_agents: Limit number of agents (optional)
        verbose: Print progress (default True)
        delay: Seconds between ticks (defaults to config value)
        checkpoint: Checkpoint data to resume from (optional)

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
    return runner.run_sync()


async def run_simulation_async(
    config: dict[str, Any],
    max_agents: int | None = None,
    verbose: bool = True,
    delay: float | None = None,
    checkpoint: CheckpointData | None = None,
) -> World:
    """Run the simulation asynchronously.

    Args:
        config: Configuration dictionary
        max_agents: Limit number of agents (optional)
        verbose: Print progress (default True)
        delay: Seconds between ticks (defaults to config value)
        checkpoint: Checkpoint data to resume from (optional)

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
    return await runner.run()


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
    args: argparse.Namespace = parser.parse_args()

    config: dict[str, Any] = load_config(args.config)

    if args.ticks:
        config["world"]["max_ticks"] = args.ticks

    # Load checkpoint if resuming
    checkpoint: CheckpointData | None = None
    if args.resume:
        checkpoint = load_checkpoint(args.resume)
        if checkpoint is None and not args.quiet:
            print(f"Warning: Checkpoint file '{args.resume}' not found. Starting fresh.")

    run_simulation(
        config,
        max_agents=args.agents,
        verbose=not args.quiet,
        delay=args.delay,
        checkpoint=checkpoint,
    )


if __name__ == "__main__":
    main()
