#!/usr/bin/env python3
"""
Agent Ecology - Main runner script

Usage:
    python run.py                    # Run with defaults from config/config.yaml
    python run.py --ticks 10         # Override max ticks
    python run.py --agents 1         # Run with only first N agents
"""

from __future__ import annotations

import asyncio
import sys
import yaml
import argparse
import json
import random
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

# Default tokens per tick capacity for cooldown calculation
# Can be overridden in config.yaml later
TOKENS_PER_TICK_CAPACITY: int = 500


class PrincipalConfig(TypedDict):
    """Configuration for a principal (agent) in the simulation."""

    id: str
    starting_scrip: int


class BalanceInfo(TypedDict):
    """Balance information for an agent."""

    compute: int
    scrip: int


class CheckpointData(TypedDict):
    """Structure for checkpoint file data."""

    tick: int
    balances: dict[str, BalanceInfo]
    cumulative_api_cost: float
    artifacts: list[dict[str, Any]]
    agent_ids: list[str]
    reason: str


class ActionProposal(TypedDict):
    """Structure for an agent's action proposal during two-phase commit."""

    agent: Agent
    proposal: dict[str, Any]
    thinking_cost: int
    api_cost: float


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


def load_checkpoint(checkpoint_file: str) -> CheckpointData | None:
    """Load simulation state from checkpoint file.

    Args:
        checkpoint_file: Path to the checkpoint JSON file.

    Returns:
        CheckpointData dict if file exists and is valid, None otherwise.
    """
    checkpoint_path: Path = Path(checkpoint_file)
    if not checkpoint_path.exists():
        return None

    with open(checkpoint_path) as f:
        data: dict[str, Any] = json.load(f)

    # Cast to CheckpointData (assumes file structure is valid)
    # Parse balances - handle both old format (int) and new format (BalanceInfo dict)
    raw_balances: dict[str, Any] = data["balances"]
    balances: dict[str, BalanceInfo] = {}
    for agent_id, balance_data in raw_balances.items():
        if isinstance(balance_data, dict):
            balances[agent_id] = {
                "compute": int(balance_data.get("compute", 0)),
                "scrip": int(balance_data.get("scrip", 0)),
            }
        else:
            # Legacy format: just scrip value as int
            balances[agent_id] = {"compute": 0, "scrip": int(balance_data)}

    checkpoint: CheckpointData = {
        "tick": int(data["tick"]),
        "balances": balances,
        "cumulative_api_cost": float(data["cumulative_api_cost"]),
        "artifacts": list(data["artifacts"]),
        "agent_ids": list(data["agent_ids"]),
        "reason": str(data["reason"]),
    }
    return checkpoint


def check_for_new_principals(
    world: World,
    agents: list[Agent],
    config: dict[str, Any],
    verbose: bool = True,
) -> list[Agent]:
    """
    Check ledger for principals that don't have Agent instances.
    Creates default Agent instances for new principals.

    Args:
        world: The World instance containing the ledger
        agents: Current list of Agent instances
        config: Configuration dictionary
        verbose: Whether to print status messages

    Returns:
        List of newly created Agent instances
    """
    # Get all principal IDs from the ledger
    ledger_principals: set[str] = set(world.ledger.scrip.keys())

    # Get IDs of existing agents
    existing_agent_ids: set[str] = {agent.agent_id for agent in agents}

    # Find principals without agents
    new_principal_ids: set[str] = ledger_principals - existing_agent_ids

    # Create default agents for new principals
    new_agents: list[Agent] = []
    default_model: str = config.get("llm", {}).get(
        "default_model", "gemini/gemini-3-flash-preview"
    )
    log_dir: str = config.get("logging", {}).get("log_dir", "llm_logs")
    default_system_prompt: str = (
        "You are a new agent. Survive and thrive. "
        "You start with nothing - seek resources and opportunities."
    )

    for principal_id in new_principal_ids:
        new_agent = Agent(
            agent_id=principal_id,
            llm_model=default_model,
            system_prompt=default_system_prompt,
            action_schema="",  # Use default schema
            log_dir=log_dir,
        )
        # Initialize cooldown_ticks attribute
        new_agent.cooldown_ticks = 0
        new_agents.append(new_agent)

        if verbose:
            print(f"  [NEW AGENT] Created agent for principal: {principal_id}")

    return new_agents


class ThinkingResult(TypedDict, total=False):
    """Result from parallel agent thinking."""

    agent: Agent
    proposal: dict[str, Any]
    thinking_cost: int
    api_cost: float
    input_tokens: int
    output_tokens: int
    cooldown_ticks: int
    skipped: bool
    skip_reason: str
    error: str


async def _think_async(
    agent: Agent,
    tick_state: dict[str, Any],
    world: World,
    rate_input: int,
    rate_output: int,
    tokens_per_tick_capacity: int,
    verbose: bool,
) -> ThinkingResult:
    """
    Async helper for single agent thinking.

    Returns a ThinkingResult with proposal data or skip/error info.
    """
    # Check cooldown - if agent is cooling down, skip
    if hasattr(agent, "cooldown_ticks") and agent.cooldown_ticks > 0:
        return {
            "agent": agent,
            "skipped": True,
            "skip_reason": f"cooling down ({agent.cooldown_ticks} ticks remaining)",
            "cooldown_ticks": agent.cooldown_ticks,
        }

    compute_before: int = world.ledger.get_compute(agent.agent_id)

    try:
        # Use async LLM call
        proposal: dict[str, Any] = await agent.propose_action_async(tick_state)
    except Exception as e:
        return {
            "agent": agent,
            "error": f"LLM call failed: {e}",
            "skipped": True,
            "skip_reason": "llm_error",
        }

    # Extract token usage
    usage: dict[str, Any] = proposal.get("usage", {})
    api_cost: float = usage.get("cost", 0.0)
    input_tokens: int = usage.get("input_tokens", 0)
    output_tokens: int = usage.get("output_tokens", 0)

    # Calculate cooldown based on output tokens
    cooldown_ticks: int = output_tokens // tokens_per_tick_capacity

    # Deduct thinking cost
    thinking_result: tuple[bool, int] = world.ledger.deduct_thinking_cost(
        agent.agent_id, input_tokens, output_tokens, rate_input, rate_output
    )
    thinking_success: bool = thinking_result[0]
    thinking_cost: int = thinking_result[1]

    if not thinking_success:
        # Agent can't afford to think
        return {
            "agent": agent,
            "skipped": True,
            "skip_reason": f"insufficient_compute (cost {thinking_cost} > {compute_before})",
            "thinking_cost": thinking_cost,
            "api_cost": api_cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cooldown_ticks": cooldown_ticks,
        }

    if "error" in proposal:
        return {
            "agent": agent,
            "skipped": True,
            "skip_reason": "intent_rejected",
            "error": proposal["error"],
            "thinking_cost": thinking_cost,
            "api_cost": api_cost,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cooldown_ticks": cooldown_ticks,
        }

    return {
        "agent": agent,
        "proposal": proposal,
        "thinking_cost": thinking_cost,
        "api_cost": api_cost,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cooldown_ticks": cooldown_ticks,
        "skipped": False,
    }


async def run_simulation_async(
    config: dict[str, Any],
    max_agents: int | None = None,
    verbose: bool = True,
    delay: float | None = None,
    checkpoint: CheckpointData | None = None,
) -> World:
    """
    Async version of run_simulation with parallel agent thinking.

    Agents think concurrently in Phase 1 using asyncio.gather(),
    then actions are executed sequentially in Phase 2.
    """
    # Use delay from config if not specified (only used between ticks now)
    if delay is None:
        delay = config.get("llm", {}).get("rate_limit_delay", 15.0)

    # Budget configuration
    budget_config: dict[str, Any] = config.get("budget", {})
    max_api_cost: float = budget_config.get("max_api_cost", 0)  # 0 = unlimited
    cumulative_api_cost: float = (
        checkpoint["cumulative_api_cost"] if checkpoint else 0.0
    )

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

    # Restore checkpoint state if resuming
    if checkpoint:
        # Restore tick (subtract 1 because advance_tick increments before first iteration)
        world.tick = checkpoint["tick"] - 1

        # Restore balances
        for agent_id, balance_info in checkpoint["balances"].items():
            if agent_id in world.ledger.scrip:
                world.ledger.scrip[agent_id] = balance_info["scrip"]

        # Restore artifacts
        for artifact_data in checkpoint["artifacts"]:
            world.artifacts.write(
                artifact_id=artifact_data["id"],
                type=artifact_data.get("type", "data"),
                content=artifact_data.get("content", ""),
                owner_id=artifact_data.get("owner_id", "system"),
                executable=artifact_data.get("executable", False),
                price=artifact_data.get("price", 0),
                code=artifact_data.get("code", ""),
                policy=artifact_data.get("policy"),
            )

        if verbose:
            print(f"=== Resuming from checkpoint ===")
            print(f"Previous tick: {checkpoint['tick']}")
            print(f"Previous reason: {checkpoint['reason']}")
            print(f"Cumulative API cost: ${cumulative_api_cost:.4f}")
            print(f"Restored artifacts: {len(checkpoint['artifacts'])}")
            print()

    # Extract token rates from config
    costs: dict[str, Any] = config.get("costs", {})
    rate_input: int = costs.get("per_1k_input_tokens", 1)
    rate_output: int = costs.get("per_1k_output_tokens", 3)

    # Get tokens per tick capacity for cooldown calculation (configurable)
    tokens_per_tick_capacity: int = config.get("cooldown", {}).get(
        "tokens_per_tick_capacity", TOKENS_PER_TICK_CAPACITY
    )

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
        # Initialize cooldown_ticks attribute for cooldown mechanism
        agent.cooldown_ticks = 0
        agents.append(agent)

    if verbose:
        print("=== Agent Ecology Simulation (Async) ===")
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

    # Main simulation loop with Two-Phase Commit (Async)
    while world.advance_tick():
        if verbose:
            print(f"--- Tick {world.tick} ---")

        # ========================================
        # STEP 0: Detect new principals and create Agent instances
        # ========================================
        new_agents: list[Agent] = check_for_new_principals(
            world, agents, config, verbose
        )
        agents.extend(new_agents)

        # ========================================
        # STEP 1: Capture frozen state snapshot (Two-Phase Commit: Observe)
        # ========================================
        # All agents will see the SAME snapshot when thinking
        tick_state: dict[str, Any] = world.get_state_summary()

        # Check budget before parallel thinking
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

        # ========================================
        # PHASE 1: Parallel thinking (all agents think concurrently)
        # ========================================
        if verbose:
            active_agents = [a for a in agents if not (hasattr(a, "cooldown_ticks") and a.cooldown_ticks > 0)]
            cooling_agents = len(agents) - len(active_agents)
            print(f"  [PHASE 1] {len(active_agents)} agents thinking in parallel ({cooling_agents} cooling down)...")

        # Launch all agent thinking in parallel
        thinking_tasks = [
            _think_async(
                agent, tick_state, world, rate_input, rate_output,
                tokens_per_tick_capacity, verbose
            )
            for agent in agents
        ]
        thinking_results: list[ThinkingResult] = await asyncio.gather(*thinking_tasks)

        # Process results and collect valid proposals
        proposals: list[ActionProposal] = []
        for result in thinking_results:
            agent = result["agent"]

            # Update cooldown counter (decrement for those that skipped due to cooldown)
            if result.get("skipped") and result.get("skip_reason", "").startswith("cooling down"):
                agent.cooldown_ticks -= 1
                if verbose:
                    print(f"    {agent.agent_id}: cooling down ({agent.cooldown_ticks + 1} -> {agent.cooldown_ticks} ticks)")
                continue

            # Set new cooldown from thinking result
            if "cooldown_ticks" in result:
                agent.cooldown_ticks = result["cooldown_ticks"]

            # Track API cost
            api_cost = result.get("api_cost", 0.0)
            cumulative_api_cost += api_cost

            # Log results
            if result.get("skipped"):
                reason = result.get("skip_reason", "unknown")
                error = result.get("error", "")

                if "insufficient_compute" in reason:
                    world.logger.log(
                        "thinking_failed",
                        {
                            "tick": world.tick,
                            "principal_id": agent.agent_id,
                            "reason": "insufficient_compute",
                            "thinking_cost": result.get("thinking_cost", 0),
                            "tokens": {
                                "input": result.get("input_tokens", 0),
                                "output": result.get("output_tokens", 0),
                            },
                        },
                    )
                    if verbose:
                        print(f"    {agent.agent_id}: OUT OF COMPUTE ({reason})")
                elif "intent_rejected" in reason:
                    world.logger.log(
                        "intent_rejected",
                        {
                            "tick": world.tick,
                            "principal_id": agent.agent_id,
                            "error": error,
                        },
                    )
                    if verbose:
                        print(f"    {agent.agent_id}: REJECTED: {error[:100]}")
                else:
                    if verbose:
                        print(f"    {agent.agent_id}: SKIPPED ({reason})")
                continue

            # Valid proposal - log and collect
            input_tokens = result.get("input_tokens", 0)
            output_tokens = result.get("output_tokens", 0)
            thinking_cost = result.get("thinking_cost", 0)
            cooldown_ticks = result.get("cooldown_ticks", 0)

            world.logger.log(
                "thinking",
                {
                    "tick": world.tick,
                    "principal_id": agent.agent_id,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "thinking_cost": thinking_cost,
                    "cooldown_ticks": cooldown_ticks,
                    "compute_after": world.ledger.get_compute(agent.agent_id),
                },
            )

            if verbose:
                cost_str = f" (${api_cost:.4f}, total: ${cumulative_api_cost:.4f})" if api_cost > 0 else ""
                cooldown_str = f", cooldown: {cooldown_ticks} ticks" if cooldown_ticks > 0 else ""
                print(f"    {agent.agent_id}: {input_tokens} in, {output_tokens} out -> {thinking_cost} compute{cost_str}{cooldown_str}")

            proposals.append({
                "agent": agent,
                "proposal": result["proposal"],
                "thinking_cost": thinking_cost,
                "api_cost": api_cost,
            })

        # ========================================
        # PHASE 2: Randomize and execute actions (Two-Phase Commit: Act)
        # ========================================
        if verbose and proposals:
            print(f"  [PHASE 2] Executing {len(proposals)} proposals in randomized order...")

        random.shuffle(proposals)

        for action_proposal in proposals:
            agent = action_proposal["agent"]
            proposal = action_proposal["proposal"]

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
                    print(f"    {agent.agent_id}: PARSE ERROR: {intent}")
                continue

            # Execute the action
            result = world.execute_action(intent)
            if verbose:
                status: str = "SUCCESS" if result.success else "FAILED"
                print(f"    {agent.agent_id}: {status}: {result.message}")

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

        # Optional inter-tick delay (reduced since thinking is parallel now)
        if delay > 0:
            await asyncio.sleep(delay)

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


def run_simulation(
    config: dict[str, Any],
    max_agents: int | None = None,
    verbose: bool = True,
    delay: float | None = None,
    checkpoint: CheckpointData | None = None,
) -> World:
    """
    Run the simulation (async wrapper).

    This is the main entry point that runs the async simulation
    using asyncio.run(). For direct async control, use run_simulation_async().
    """
    return asyncio.run(
        run_simulation_async(config, max_agents, verbose, delay, checkpoint)
    )


def run_simulation_sync(
    config: dict[str, Any],
    max_agents: int | None = None,
    verbose: bool = True,
    delay: float | None = None,
    checkpoint: CheckpointData | None = None,
) -> World:
    """Run the simulation synchronously (sequential agent thinking).

    This is the original sequential implementation, kept for backward
    compatibility with tests. For production use, prefer run_simulation()
    which uses parallel agent thinking.

    Args:
        config: Configuration dictionary
        max_agents: Limit number of agents (optional)
        verbose: Print progress (default True)
        delay: Seconds between LLM calls (defaults to config value)
        checkpoint: Checkpoint data to resume from (optional)
    """
    # Use delay from config if not specified
    if delay is None:
        delay = config.get("llm", {}).get("rate_limit_delay", 15.0)

    # Budget configuration
    budget_config: dict[str, Any] = config.get("budget", {})
    max_api_cost: float = budget_config.get("max_api_cost", 0)  # 0 = unlimited
    cumulative_api_cost: float = (
        checkpoint["cumulative_api_cost"] if checkpoint else 0.0
    )

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

    # Restore checkpoint state if resuming
    if checkpoint:
        # Restore tick (subtract 1 because advance_tick increments before first iteration)
        world.tick = checkpoint["tick"] - 1

        # Restore balances
        for agent_id, balance_info in checkpoint["balances"].items():
            if agent_id in world.ledger.scrip:
                world.ledger.scrip[agent_id] = balance_info["scrip"]

        # Restore artifacts
        for artifact_data in checkpoint["artifacts"]:
            world.artifacts.write(
                artifact_id=artifact_data["id"],
                type=artifact_data.get("type", "data"),
                content=artifact_data.get("content", ""),
                owner_id=artifact_data.get("owner_id", "system"),
                executable=artifact_data.get("executable", False),
                price=artifact_data.get("price", 0),
                code=artifact_data.get("code", ""),
                policy=artifact_data.get("policy"),
            )

        if verbose:
            print(f"=== Resuming from checkpoint ===")
            print(f"Previous tick: {checkpoint['tick']}")
            print(f"Previous reason: {checkpoint['reason']}")
            print(f"Cumulative API cost: ${cumulative_api_cost:.4f}")
            print(f"Restored artifacts: {len(checkpoint['artifacts'])}")
            print()

    # Extract token rates from config
    costs: dict[str, Any] = config.get("costs", {})
    rate_input: int = costs.get("per_1k_input_tokens", 1)
    rate_output: int = costs.get("per_1k_output_tokens", 3)

    # Get tokens per tick capacity for cooldown calculation (configurable)
    tokens_per_tick_capacity: int = config.get("cooldown", {}).get(
        "tokens_per_tick_capacity", TOKENS_PER_TICK_CAPACITY
    )

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
        # Initialize cooldown_ticks attribute for cooldown mechanism
        agent.cooldown_ticks = 0
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

    # Main simulation loop with Two-Phase Commit
    while world.advance_tick():
        if verbose:
            print(f"--- Tick {world.tick} ---")

        # ========================================
        # STEP 0: Detect new principals and create Agent instances
        # ========================================
        new_agents: list[Agent] = check_for_new_principals(
            world, agents, config, verbose
        )
        agents.extend(new_agents)

        # ========================================
        # STEP 1: Capture frozen state snapshot (Two-Phase Commit: Observe)
        # ========================================
        # All agents will see the SAME snapshot when thinking
        tick_state: dict[str, Any] = world.get_state_summary()

        # ========================================
        # PHASE 1: Collect proposals (all agents see same snapshot)
        # ========================================
        proposals: list[ActionProposal] = []

        for agent in agents:
            # Check cooldown - if agent is cooling down, decrement and skip
            if hasattr(agent, "cooldown_ticks") and agent.cooldown_ticks > 0:
                if verbose:
                    print(
                        f"  {agent.agent_id} cooling down... ({agent.cooldown_ticks} ticks remaining)"
                    )
                agent.cooldown_ticks -= 1
                continue

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

            # Get action from LLM - ALL agents see the SAME tick_state snapshot
            proposal: dict[str, Any] = agent.propose_action(tick_state)

            # Extract token usage and deduct thinking cost
            usage: dict[str, Any] = proposal.get("usage", {})
            api_cost: float = usage.get("cost", 0.0)
            cumulative_api_cost += api_cost
            input_tokens: int = usage.get("input_tokens", 0)
            output_tokens: int = usage.get("output_tokens", 0)

            # Calculate cooldown based on output tokens
            agent.cooldown_ticks = output_tokens // tokens_per_tick_capacity

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
                cooldown_str: str = (
                    f", cooldown: {agent.cooldown_ticks} ticks"
                    if agent.cooldown_ticks > 0
                    else ""
                )
                print(
                    f"    Tokens: {input_tokens} in, {output_tokens} out -> {thinking_cost} compute{cost_str}{cooldown_str}"
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
                    "cooldown_ticks": agent.cooldown_ticks,
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

            # Add to proposals for Phase 2
            proposals.append({
                "agent": agent,
                "proposal": proposal,
                "thinking_cost": thinking_cost,
                "api_cost": api_cost,
            })

            # Rate limit delay between LLM calls
            if delay > 0:
                time.sleep(delay)

        # ========================================
        # PHASE 2: Randomize and execute actions (Two-Phase Commit: Act)
        # ========================================
        if verbose and proposals:
            print(f"  [PHASE 2] Executing {len(proposals)} proposals in randomized order...")

        random.shuffle(proposals)

        for action_proposal in proposals:
            agent = action_proposal["agent"]
            proposal = action_proposal["proposal"]

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
                    print(f"    {agent.agent_id}: PARSE ERROR: {intent}")
                continue

            # Execute the action
            result = world.execute_action(intent)
            if verbose:
                status: str = "SUCCESS" if result.success else "FAILED"
                print(f"    {agent.agent_id}: {status}: {result.message}")

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
