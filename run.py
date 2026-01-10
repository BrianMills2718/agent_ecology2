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
import json
import time
from pathlib import Path
from typing import Any, TypedDict

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from world import World
from world.actions import parse_intent_from_json, ActionIntent
from agents import Agent
from agents.loader import load_agents
from agents.schema import ActionType


class PrincipalConfig(TypedDict):
    """Configuration for a principal (agent) in the simulation."""

    id: str
    starting_scrip: int


class CheckpointData(TypedDict):
    """Structure for checkpoint file data."""

    tick: int
    balances: dict[str, int]
    cumulative_api_cost: float
    artifacts: list[dict[str, Any]]
    agent_ids: list[str]
    reason: str


def load_config(config_path: str = "config/config.yaml") -> dict[str, Any]:
    """Load configuration from YAML file"""
    with open(config_path) as f:
        result: dict[str, Any] = yaml.safe_load(f)
        return result


def save_checkpoint(
    world: World,
    agents: list[Agent],
    cumulative_cost: float,
    config: dict[str, Any],
    reason: str,
) -> str:
    """Save simulation state to checkpoint file for later resumption."""
    checkpoint_file: str = config.get("budget", {}).get(
        "checkpoint_file", "checkpoint.json"
    )
    checkpoint: CheckpointData = {
        "tick": world.tick,
        "balances": world.ledger.get_all_balances(),
        "cumulative_api_cost": cumulative_cost,
        "artifacts": [a.to_dict() for a in world.artifacts.artifacts.values()],
        "agent_ids": [a.agent_id for a in agents],
        "reason": reason,
    }
    with open(checkpoint_file, "w") as f:
        json.dump(checkpoint, f, indent=2)
    return checkpoint_file


def run_simulation(
    config: dict[str, Any],
    max_agents: int | None = None,
    verbose: bool = True,
    delay: float | None = None,
) -> World:
    """Run the simulation.

    Args:
        config: Configuration dictionary
        max_agents: Limit number of agents (optional)
        verbose: Print progress (default True)
        delay: Seconds between LLM calls (defaults to config value)
    """
    # Use delay from config if not specified
    if delay is None:
        delay = config.get("llm", {}).get("rate_limit_delay", 15.0)

    # Budget configuration
    budget_config: dict[str, Any] = config.get("budget", {})
    max_api_cost: float = budget_config.get("max_api_cost", 0)  # 0 = unlimited
    cumulative_api_cost: float = 0.0

    # Load agents from directory structure
    agent_configs: list[dict[str, Any]] = load_agents()
    if max_agents:
        agent_configs = agent_configs[:max_agents]

    # Get default starting scrip from config
    default_starting_scrip: int = config.get("scrip", {}).get("starting_amount", 100)

    # Build principals list for world initialization
    principals: list[PrincipalConfig] = [
        {
            "id": a["id"],
            "starting_scrip": a.get(
                "starting_scrip", a.get("starting_credits", default_starting_scrip)
            ),
        }
        for a in agent_configs
    ]
    config["principals"] = principals

    # Initialize world
    world: World = World(config)

    # Extract token rates from config
    costs: dict[str, Any] = config.get("costs", {})
    rate_input: int = costs.get("per_1k_input_tokens", 1)
    rate_output: int = costs.get("per_1k_output_tokens", 3)

    # Initialize agents
    agents: list[Agent] = []
    for a in agent_configs:
        agent = Agent(
            agent_id=a["id"],
            llm_model=a.get("llm_model") or config["llm"]["default_model"],
            system_prompt=a.get("system_prompt", ""),
            action_schema=a.get("action_schema", ""),
            log_dir=config["logging"]["log_dir"],
        )
        agents.append(agent)

    if verbose:
        print("=== Agent Ecology Simulation ===")
        print(f"Max ticks: {world.max_ticks}")
        print(f"Agents: {[a.agent_id for a in agents]}")
        print(
            f"Token rates: {rate_input} compute/1K input, {rate_output} compute/1K output"
        )
        if max_api_cost > 0:
            print(f"API budget: ${max_api_cost:.2f}")
        print(f"Starting scrip: {world.ledger.get_all_scrip()}")
        print(f"Compute quota/tick: {world.rights_config.get('default_compute_quota', 50)}")
        print()

    # Main simulation loop
    while world.advance_tick():
        if verbose:
            print(f"--- Tick {world.tick} ---")

        # Each agent proposes an action
        for agent in agents:
            state: dict[str, Any] = world.get_state_summary()
            compute_before: int = world.ledger.get_compute(agent.agent_id)
            scrip_before: int = world.ledger.get_scrip(agent.agent_id)

            if verbose:
                print(
                    f"  {agent.agent_id} thinking... (compute: {compute_before}, scrip: {scrip_before})"
                )

            # Check budget before LLM call
            if max_api_cost > 0 and cumulative_api_cost >= max_api_cost:
                checkpoint_file: str = save_checkpoint(
                    world, agents, cumulative_api_cost, config, "budget_exhausted"
                )
                if verbose:
                    print("\n=== BUDGET EXHAUSTED ===")
                    print(f"API cost: ${cumulative_api_cost:.4f} >= ${max_api_cost:.2f}")
                    print(f"Checkpoint saved to: {checkpoint_file}")
                    print(f"Simulation paused at tick {world.tick}")
                world.logger.log(
                    "budget_pause",
                    {
                        "tick": world.tick,
                        "cumulative_api_cost": cumulative_api_cost,
                        "max_api_cost": max_api_cost,
                        "checkpoint_file": checkpoint_file,
                    },
                )
                return world

            # Get action from LLM (events require genesis_event_log)
            proposal: dict[str, Any] = agent.propose_action(state)

            # Extract token usage and deduct thinking cost
            usage: dict[str, Any] = proposal.get("usage", {})
            api_cost: float = usage.get("cost", 0.0)
            cumulative_api_cost += api_cost
            input_tokens: int = usage.get("input_tokens", 0)
            output_tokens: int = usage.get("output_tokens", 0)

            # Deduct thinking cost
            thinking_result: tuple[bool, int] = world.ledger.deduct_thinking_cost(
                agent.agent_id, input_tokens, output_tokens, rate_input, rate_output
            )
            thinking_success: bool = thinking_result[0]
            thinking_cost: int = thinking_result[1]

            if verbose:
                cost_str: str = (
                    f" (${api_cost:.4f}, total: ${cumulative_api_cost:.4f})"
                    if api_cost > 0
                    else ""
                )
                print(
                    f"    Tokens: {input_tokens} in, {output_tokens} out -> {thinking_cost} compute{cost_str}"
                )

            if not thinking_success:
                # Agent can't afford to think - skip turn (no compute left)
                world.logger.log(
                    "thinking_failed",
                    {
                        "tick": world.tick,
                        "principal_id": agent.agent_id,
                        "reason": "insufficient_compute",
                        "thinking_cost": thinking_cost,
                        "compute_before": compute_before,
                        "tokens": {"input": input_tokens, "output": output_tokens},
                    },
                )
                if verbose:
                    print(
                        f"    -> OUT OF COMPUTE: Can't afford thinking cost ({thinking_cost} > {compute_before})"
                    )
                if delay > 0:
                    time.sleep(delay)
                continue

            # Log token usage
            world.logger.log(
                "thinking",
                {
                    "tick": world.tick,
                    "principal_id": agent.agent_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "thinking_cost": thinking_cost,
                    "compute_after": world.ledger.get_compute(agent.agent_id),
                },
            )

            if "error" in proposal:
                # Log the rejection (still paid thinking cost!)
                world.logger.log(
                    "intent_rejected",
                    {
                        "tick": world.tick,
                        "principal_id": agent.agent_id,
                        "error": proposal["error"],
                        "raw_response": (proposal.get("raw_response") or "")[:500],
                    },
                )
                if verbose:
                    print(f"    -> REJECTED: {proposal['error'][:100]}")
                if delay > 0:
                    time.sleep(delay)
                continue

            # Parse and execute the action
            action_dict: dict[str, Any] = proposal["action"]
            intent: ActionIntent | str = parse_intent_from_json(
                agent.agent_id, json.dumps(action_dict)
            )

            if isinstance(intent, str):
                # Parse error (still paid thinking cost!)
                world.logger.log(
                    "intent_rejected",
                    {
                        "tick": world.tick,
                        "principal_id": agent.agent_id,
                        "error": intent,
                        "action_dict": action_dict,
                    },
                )
                if verbose:
                    print(f"    -> PARSE ERROR: {intent}")
                continue

            # Execute the action
            result = world.execute_action(intent)
            if verbose:
                status: str = "SUCCESS" if result.success else "FAILED"
                print(f"    -> {status}: {result.message}")

            # Feed result back to agent for next prompt
            # Extract action_type and cast to ActionType (defaults to "noop" if invalid)
            raw_action_type: str = action_dict.get("action_type", "noop")
            action_type: ActionType = raw_action_type if raw_action_type in (
                "noop", "read_artifact", "write_artifact", "invoke_artifact", "transfer"
            ) else "noop"
            agent.set_last_result(action_type, result.success, result.message)

            # Record action to agent's memory
            action_details: str = json.dumps(action_dict)
            agent.record_action(action_type, action_details, result.success)

            # Rate limit delay
            if delay > 0:
                time.sleep(delay)

        if verbose:
            print(f"  End of tick. Scrip: {world.ledger.get_all_scrip()}")
            print()

    # Final summary
    if verbose:
        print("=== Simulation Complete ===")
        print(f"Final tick: {world.tick}")
        print(f"Final scrip: {world.ledger.get_all_scrip()}")
        print(f"Total artifacts: {world.artifacts.count()}")
        print(f"Log file: {config['logging']['output_file']}")

    return world


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
        help="Delay between LLM calls (defaults to config value)",
    )
    args: argparse.Namespace = parser.parse_args()

    config: dict[str, Any] = load_config(args.config)

    if args.ticks:
        config["world"]["max_ticks"] = args.ticks

    run_simulation(config, max_agents=args.agents, verbose=not args.quiet, delay=args.delay)


if __name__ == "__main__":
    main()
