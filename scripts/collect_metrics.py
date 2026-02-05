#!/usr/bin/env python3
"""Collect metrics from simulation run logs (Plan #227).

Extracts key metrics from events.jsonl for experiment comparison:
- Per-agent: noop_rate, success_rate, revenue, artifacts_created, tokens, cost
- Aggregate: total_transactions, economic_velocity, action distribution

Usage:
    python scripts/collect_metrics.py logs/latest/events.jsonl
    python scripts/collect_metrics.py logs/latest/events.jsonl --output metrics.json
    python scripts/collect_metrics.py --latest
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any


@dataclass
class AgentMetrics:
    """Metrics for a single agent."""

    agent_id: str
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    noop_count: int = 0
    actions_by_type: Counter[str] = field(default_factory=Counter)
    artifacts_created: int = 0
    artifacts_read: int = 0
    artifacts_written: int = 0
    total_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    api_cost: float = 0.0
    scrip_earned: float = 0.0
    scrip_spent: float = 0.0
    mint_submissions: int = 0
    mint_successes: int = 0
    state_transitions: int = 0

    @property
    def success_rate(self) -> float:
        """Calculate action success rate (excluding noops)."""
        non_noop = self.total_actions - self.noop_count
        if non_noop == 0:
            return 0.0
        return self.successful_actions / non_noop

    @property
    def noop_rate(self) -> float:
        """Calculate noop rate."""
        if self.total_actions == 0:
            return 0.0
        return self.noop_count / self.total_actions

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "agent_id": self.agent_id,
            "total_actions": self.total_actions,
            "successful_actions": self.successful_actions,
            "failed_actions": self.failed_actions,
            "noop_count": self.noop_count,
            "success_rate": round(self.success_rate, 4),
            "noop_rate": round(self.noop_rate, 4),
            "actions_by_type": dict(self.actions_by_type),
            "artifacts_created": self.artifacts_created,
            "artifacts_read": self.artifacts_read,
            "artifacts_written": self.artifacts_written,
            "total_tokens": self.total_tokens,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "api_cost": round(self.api_cost, 6),
            "scrip_earned": round(self.scrip_earned, 2),
            "scrip_spent": round(self.scrip_spent, 2),
            "mint_submissions": self.mint_submissions,
            "mint_successes": self.mint_successes,
            "state_transitions": self.state_transitions,
        }


@dataclass
class AggregateMetrics:
    """Aggregate metrics across all agents."""

    total_events: int = 0
    total_agents: int = 0
    total_actions: int = 0
    total_successes: int = 0
    total_failures: int = 0
    total_noops: int = 0
    total_artifacts_created: int = 0
    total_tokens: int = 0
    total_api_cost: float = 0.0
    total_scrip_transferred: float = 0.0
    action_distribution: Counter[str] = field(default_factory=Counter)
    event_counts: Counter[str] = field(default_factory=Counter)
    mint_tasks_created: int = 0
    mint_tasks_completed: int = 0
    duration_seconds: float = 0.0

    @property
    def overall_success_rate(self) -> float:
        """Overall success rate across all agents."""
        non_noop = self.total_actions - self.total_noops
        if non_noop == 0:
            return 0.0
        return self.total_successes / non_noop

    @property
    def overall_noop_rate(self) -> float:
        """Overall noop rate across all agents."""
        if self.total_actions == 0:
            return 0.0
        return self.total_noops / self.total_actions

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON output."""
        return {
            "total_events": self.total_events,
            "total_agents": self.total_agents,
            "total_actions": self.total_actions,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "total_noops": self.total_noops,
            "overall_success_rate": round(self.overall_success_rate, 4),
            "overall_noop_rate": round(self.overall_noop_rate, 4),
            "total_artifacts_created": self.total_artifacts_created,
            "total_tokens": self.total_tokens,
            "total_api_cost": round(self.total_api_cost, 6),
            "total_scrip_transferred": round(self.total_scrip_transferred, 2),
            "action_distribution": dict(self.action_distribution),
            "event_counts": dict(self.event_counts),
            "mint_tasks_created": self.mint_tasks_created,
            "mint_tasks_completed": self.mint_tasks_completed,
            "duration_seconds": round(self.duration_seconds, 2),
        }


def collect_metrics(log_path: Path) -> tuple[dict[str, AgentMetrics], AggregateMetrics]:
    """Collect metrics from an events.jsonl file.

    Args:
        log_path: Path to events.jsonl file

    Returns:
        Tuple of (per_agent_metrics, aggregate_metrics)
    """
    agents: dict[str, AgentMetrics] = {}
    aggregate = AggregateMetrics()

    first_timestamp: str | None = None
    last_timestamp: str | None = None

    # Track scrip changes for economic velocity
    scrip_transfers: list[float] = []

    with open(log_path) as f:
        for line in f:
            if not line.strip():
                continue

            event = json.loads(line)
            aggregate.total_events += 1

            etype = event.get("event_type", "")
            aggregate.event_counts[etype] += 1

            # Track timestamps for duration
            ts = event.get("timestamp", "")
            if ts:
                if first_timestamp is None:
                    first_timestamp = ts
                last_timestamp = ts

            # Get agent ID from various places
            agent_id = (
                event.get("principal_id")
                or event.get("agent_id")
                or event.get("intent", {}).get("principal_id")
            )

            # Skip kernel/system agents for per-agent stats
            if agent_id and "alpha_prime" not in agent_id and agent_id not in ["SYSTEM", "kernel_mint_agent"]:
                if agent_id not in agents:
                    agents[agent_id] = AgentMetrics(agent_id=agent_id)

            # Process by event type
            if etype == "thinking":
                _process_thinking(event, agents, aggregate)
            elif etype == "action":
                _process_action(event, agents, aggregate)
            elif etype == "workflow_state_changed":
                _process_state_change(event, agents)
            elif etype == "artifact_written":
                _process_artifact_written(event, agents, aggregate)
            elif etype == "mint_task_created":
                aggregate.mint_tasks_created += 1
            elif etype == "mint_task_completed":
                aggregate.mint_tasks_completed += 1
                _process_mint_completed(event, agents, scrip_transfers)
            elif etype == "mint_task_submission":
                _process_mint_submission(event, agents)

    # Calculate duration
    if first_timestamp and last_timestamp:
        from datetime import datetime

        try:
            first_dt = datetime.fromisoformat(first_timestamp.replace("Z", "+00:00"))
            last_dt = datetime.fromisoformat(last_timestamp.replace("Z", "+00:00"))
            aggregate.duration_seconds = (last_dt - first_dt).total_seconds()
        except ValueError:
            pass

    # Calculate aggregate totals
    aggregate.total_agents = len(agents)
    for agent in agents.values():
        aggregate.total_actions += agent.total_actions
        aggregate.total_successes += agent.successful_actions
        aggregate.total_failures += agent.failed_actions
        aggregate.total_noops += agent.noop_count
        aggregate.total_tokens += agent.total_tokens
        aggregate.total_api_cost += agent.api_cost
        aggregate.action_distribution.update(agent.actions_by_type)

    aggregate.total_scrip_transferred = sum(scrip_transfers)

    return agents, aggregate


def _process_thinking(
    event: dict[str, Any],
    agents: dict[str, AgentMetrics],
    aggregate: AggregateMetrics,
) -> None:
    """Process a thinking event."""
    agent_id = event.get("principal_id", "")
    if agent_id not in agents or "alpha_prime" in agent_id:
        return

    agent = agents[agent_id]
    input_tokens = event.get("input_tokens", 0)
    output_tokens = event.get("output_tokens", 0)
    api_cost = event.get("api_cost", 0)

    agent.input_tokens += input_tokens
    agent.output_tokens += output_tokens
    agent.total_tokens += input_tokens + output_tokens
    agent.api_cost += api_cost


def _process_action(
    event: dict[str, Any],
    agents: dict[str, AgentMetrics],
    aggregate: AggregateMetrics,
) -> None:
    """Process an action event."""
    intent = event.get("intent", {})
    result = event.get("result", {})
    agent_id = intent.get("principal_id", "")

    if agent_id not in agents or "alpha_prime" in agent_id:
        return

    agent = agents[agent_id]
    action_type = intent.get("action_type", "unknown")
    success = result.get("success", False)

    agent.total_actions += 1
    agent.actions_by_type[action_type] += 1

    if action_type == "noop":
        agent.noop_count += 1
    elif success:
        agent.successful_actions += 1
    else:
        agent.failed_actions += 1

    # Track specific action effects
    if action_type == "read_artifact" and success:
        agent.artifacts_read += 1
    elif action_type == "write_artifact" and success:
        agent.artifacts_written += 1


def _process_state_change(
    event: dict[str, Any],
    agents: dict[str, AgentMetrics],
) -> None:
    """Process a workflow state change event."""
    agent_id = event.get("agent_id", "")
    if agent_id in agents:
        agents[agent_id].state_transitions += 1


def _process_artifact_written(
    event: dict[str, Any],
    agents: dict[str, AgentMetrics],
    aggregate: AggregateMetrics,
) -> None:
    """Process an artifact_written event."""
    created_by = event.get("created_by", "")
    if created_by in agents:
        agents[created_by].artifacts_created += 1
        aggregate.total_artifacts_created += 1


def _process_mint_completed(
    event: dict[str, Any],
    agents: dict[str, AgentMetrics],
    scrip_transfers: list[float],
) -> None:
    """Process a mint task completion event."""
    winner_id = event.get("winner_id", "")
    reward = event.get("reward", 0)

    if winner_id in agents:
        agents[winner_id].scrip_earned += reward
        agents[winner_id].mint_successes += 1

    scrip_transfers.append(float(reward))


def _process_mint_submission(
    event: dict[str, Any],
    agents: dict[str, AgentMetrics],
) -> None:
    """Process a mint task submission event."""
    agent_id = event.get("agent_id", "") or event.get("principal_id", "")
    if agent_id in agents:
        agents[agent_id].mint_submissions += 1


def format_metrics_table(agents: dict[str, AgentMetrics], aggregate: AggregateMetrics) -> str:
    """Format metrics as a human-readable table."""
    lines: list[str] = []

    lines.append("=" * 80)
    lines.append("SIMULATION METRICS")
    lines.append("=" * 80)

    # Aggregate summary
    lines.append("\n## Aggregate Metrics\n")
    lines.append(f"Duration: {aggregate.duration_seconds:.1f}s")
    lines.append(f"Total events: {aggregate.total_events}")
    lines.append(f"Total agents: {aggregate.total_agents}")
    lines.append(f"Total actions: {aggregate.total_actions}")
    lines.append(f"Overall success rate: {aggregate.overall_success_rate:.1%}")
    lines.append(f"Overall noop rate: {aggregate.overall_noop_rate:.1%}")
    lines.append(f"Total tokens: {aggregate.total_tokens:,}")
    lines.append(f"Total API cost: ${aggregate.total_api_cost:.4f}")
    lines.append(f"Artifacts created: {aggregate.total_artifacts_created}")
    lines.append(f"Mint tasks: {aggregate.mint_tasks_completed}/{aggregate.mint_tasks_created} completed")

    # Action distribution
    lines.append("\n## Action Distribution\n")
    total = sum(aggregate.action_distribution.values())
    for action, count in aggregate.action_distribution.most_common():
        pct = count / total * 100 if total > 0 else 0
        lines.append(f"  {action}: {count} ({pct:.1f}%)")

    # Per-agent metrics
    lines.append("\n## Per-Agent Metrics\n")
    lines.append(
        f"{'Agent':<25} {'Actions':>8} {'Success':>8} {'Noop':>8} "
        f"{'Tokens':>10} {'Cost':>10} {'Created':>8}"
    )
    lines.append("-" * 80)

    for agent_id, agent in sorted(agents.items()):
        lines.append(
            f"{agent_id:<25} {agent.total_actions:>8} "
            f"{agent.success_rate:>7.1%} {agent.noop_rate:>7.1%} "
            f"{agent.total_tokens:>10,} ${agent.api_cost:>9.4f} {agent.artifacts_created:>8}"
        )

    return "\n".join(lines)


def find_latest_log() -> Path | None:
    """Find the latest log directory."""
    logs_dir = Path("logs")
    latest = logs_dir / "latest"

    if latest.is_symlink():
        events = latest / "events.jsonl"
        if events.exists():
            return events

    # Fallback: find most recent run_* directory
    run_dirs = sorted(logs_dir.glob("run_*"), reverse=True)
    for run_dir in run_dirs:
        events = run_dir / "events.jsonl"
        if events.exists():
            return events

    return None


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Collect metrics from simulation run logs (Plan #227)"
    )
    parser.add_argument(
        "log_file",
        nargs="?",
        help="Path to events.jsonl file (or use --latest)",
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Use the most recent log directory",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file (default: print to stdout)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON format (default: human-readable table)",
    )

    args = parser.parse_args()

    # Determine log file
    if args.latest:
        log_path = find_latest_log()
        if log_path is None:
            print("Error: No log files found in logs/", file=sys.stderr)
            return 1
    elif args.log_file:
        log_path = Path(args.log_file)
    else:
        # Default to latest
        log_path = find_latest_log()
        if log_path is None:
            print("Error: No log file specified and no logs found", file=sys.stderr)
            print("Usage: python scripts/collect_metrics.py <events.jsonl>", file=sys.stderr)
            return 1

    if not log_path.exists():
        print(f"Error: Log file not found: {log_path}", file=sys.stderr)
        return 1

    # Collect metrics
    agents, aggregate = collect_metrics(log_path)

    # Format output
    if args.json or args.output:
        output = {
            "log_file": str(log_path),
            "aggregate": aggregate.to_dict(),
            "agents": {aid: agent.to_dict() for aid, agent in agents.items()},
        }
        json_str = json.dumps(output, indent=2)

        if args.output:
            Path(args.output).write_text(json_str)
            print(f"Metrics written to {args.output}")
        else:
            print(json_str)
    else:
        print(f"\nLog file: {log_path}\n")
        print(format_metrics_table(agents, aggregate))

    return 0


if __name__ == "__main__":
    sys.exit(main())
