#!/usr/bin/env python3
"""Compare metrics between two simulation runs (Plan #227).

Compares per-agent and aggregate metrics between experiments to measure
the effect of changes (e.g., new agent designs, configuration changes).

Usage:
    python scripts/compare_experiments.py logs/baseline logs/treatment
    python scripts/compare_experiments.py metrics_a.json metrics_b.json
    python scripts/compare_experiments.py --baseline logs/run_1 --treatment logs/run_2

Output shows deltas for key metrics with percentage changes.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from collect_metrics import collect_metrics, AgentMetrics, AggregateMetrics


def load_metrics(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    """Load metrics from a path (directory or JSON file).

    Args:
        path: Path to log directory (with events.jsonl) or metrics.json file

    Returns:
        Tuple of (per_agent_dict, aggregate_dict)
    """
    if path.suffix == ".json":
        # Load pre-computed metrics
        data = json.loads(path.read_text())
        return data.get("agents", {}), data.get("aggregate", {})

    # Load from events.jsonl
    events_path = path / "events.jsonl" if path.is_dir() else path
    if not events_path.exists():
        raise FileNotFoundError(f"Events file not found: {events_path}")

    agents, aggregate = collect_metrics(events_path)
    return (
        {aid: agent.to_dict() for aid, agent in agents.items()},
        aggregate.to_dict(),
    )


def compare_values(
    baseline: float | int,
    treatment: float | int,
    name: str,
    higher_is_better: bool = True,
) -> dict[str, Any]:
    """Compare two values and compute delta.

    Args:
        baseline: Baseline value
        treatment: Treatment value
        name: Metric name
        higher_is_better: Whether higher values are improvements

    Returns:
        Comparison dict with absolute and percent delta
    """
    delta = treatment - baseline
    if baseline != 0:
        pct_change = delta / baseline * 100
    else:
        pct_change = 100.0 if delta > 0 else (0.0 if delta == 0 else -100.0)

    # Determine if change is an improvement
    is_improvement = (delta > 0) == higher_is_better if delta != 0 else None

    return {
        "name": name,
        "baseline": baseline,
        "treatment": treatment,
        "delta": delta,
        "pct_change": round(pct_change, 2),
        "is_improvement": is_improvement,
    }


def compare_aggregates(
    baseline: dict[str, Any],
    treatment: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare aggregate metrics between runs.

    Args:
        baseline: Baseline aggregate metrics dict
        treatment: Treatment aggregate metrics dict

    Returns:
        List of comparison results
    """
    comparisons = []

    # Key metrics to compare and whether higher is better
    metrics = [
        ("total_actions", True),
        ("overall_success_rate", True),
        ("overall_noop_rate", False),  # Lower noop rate is better
        ("total_artifacts_created", True),
        ("total_tokens", False),  # Lower is more efficient
        ("total_api_cost", False),  # Lower is better
        ("mint_tasks_completed", True),
    ]

    for metric, higher_is_better in metrics:
        b_val = baseline.get(metric, 0)
        t_val = treatment.get(metric, 0)
        comparisons.append(compare_values(b_val, t_val, metric, higher_is_better))

    return comparisons


def compare_agents(
    baseline_agents: dict[str, dict[str, Any]],
    treatment_agents: dict[str, dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Compare per-agent metrics between runs.

    Args:
        baseline_agents: Baseline per-agent metrics
        treatment_agents: Treatment per-agent metrics

    Returns:
        Dict mapping agent_id to list of comparisons
    """
    all_agents = set(baseline_agents.keys()) | set(treatment_agents.keys())
    result = {}

    metrics = [
        ("success_rate", True),
        ("noop_rate", False),
        ("total_actions", True),
        ("total_tokens", False),
        ("api_cost", False),
        ("artifacts_created", True),
    ]

    for agent_id in sorted(all_agents):
        b_agent = baseline_agents.get(agent_id, {})
        t_agent = treatment_agents.get(agent_id, {})

        comparisons = []
        for metric, higher_is_better in metrics:
            b_val = b_agent.get(metric, 0)
            t_val = t_agent.get(metric, 0)
            comparisons.append(compare_values(b_val, t_val, metric, higher_is_better))

        result[agent_id] = comparisons

    return result


def format_delta(delta: float, pct: float, is_improvement: bool | None) -> str:
    """Format a delta value with indicator."""
    if delta == 0:
        return "  0 (0.0%)"

    sign = "+" if delta > 0 else ""
    indicator = ""
    if is_improvement is True:
        indicator = " ✓"
    elif is_improvement is False:
        indicator = " ✗"

    if isinstance(delta, float) and abs(delta) < 1:
        return f"{sign}{delta:.4f} ({sign}{pct:.1f}%){indicator}"
    return f"{sign}{delta:.2f} ({sign}{pct:.1f}%){indicator}"


def format_comparison_table(
    baseline_path: Path,
    treatment_path: Path,
    aggregate_comparisons: list[dict[str, Any]],
    agent_comparisons: dict[str, list[dict[str, Any]]],
) -> str:
    """Format comparison results as a table."""
    lines: list[str] = []

    lines.append("=" * 90)
    lines.append("EXPERIMENT COMPARISON")
    lines.append("=" * 90)
    lines.append(f"\nBaseline:  {baseline_path}")
    lines.append(f"Treatment: {treatment_path}")

    # Aggregate comparison
    lines.append("\n## Aggregate Metrics\n")
    lines.append(f"{'Metric':<25} {'Baseline':>15} {'Treatment':>15} {'Delta':>25}")
    lines.append("-" * 90)

    for comp in aggregate_comparisons:
        baseline_str = _format_value(comp["baseline"], comp["name"])
        treatment_str = _format_value(comp["treatment"], comp["name"])
        delta_str = format_delta(comp["delta"], comp["pct_change"], comp["is_improvement"])
        lines.append(f"{comp['name']:<25} {baseline_str:>15} {treatment_str:>15} {delta_str:>25}")

    # Per-agent comparison - focus on key metrics
    lines.append("\n## Per-Agent Comparison\n")

    # Noop rate comparison (often most important)
    lines.append("### Noop Rate (lower is better)\n")
    lines.append(f"{'Agent':<25} {'Baseline':>12} {'Treatment':>12} {'Delta':>20}")
    lines.append("-" * 70)

    for agent_id, comparisons in agent_comparisons.items():
        noop_comp = next((c for c in comparisons if c["name"] == "noop_rate"), None)
        if noop_comp:
            lines.append(
                f"{agent_id:<25} "
                f"{noop_comp['baseline']:>11.1%} "
                f"{noop_comp['treatment']:>11.1%} "
                f"{format_delta(noop_comp['delta'], noop_comp['pct_change'], noop_comp['is_improvement']):>20}"
            )

    # Success rate comparison
    lines.append("\n### Success Rate (higher is better)\n")
    lines.append(f"{'Agent':<25} {'Baseline':>12} {'Treatment':>12} {'Delta':>20}")
    lines.append("-" * 70)

    for agent_id, comparisons in agent_comparisons.items():
        success_comp = next((c for c in comparisons if c["name"] == "success_rate"), None)
        if success_comp:
            lines.append(
                f"{agent_id:<25} "
                f"{success_comp['baseline']:>11.1%} "
                f"{success_comp['treatment']:>11.1%} "
                f"{format_delta(success_comp['delta'], success_comp['pct_change'], success_comp['is_improvement']):>20}"
            )

    # Token efficiency
    lines.append("\n### Token Usage (lower is better)\n")
    lines.append(f"{'Agent':<25} {'Baseline':>12} {'Treatment':>12} {'Delta':>20}")
    lines.append("-" * 70)

    for agent_id, comparisons in agent_comparisons.items():
        token_comp = next((c for c in comparisons if c["name"] == "total_tokens"), None)
        if token_comp:
            lines.append(
                f"{agent_id:<25} "
                f"{token_comp['baseline']:>12,} "
                f"{token_comp['treatment']:>12,} "
                f"{format_delta(token_comp['delta'], token_comp['pct_change'], token_comp['is_improvement']):>20}"
            )

    return "\n".join(lines)


def _format_value(value: Any, metric_name: str) -> str:
    """Format a value based on metric type."""
    if "rate" in metric_name:
        return f"{value:.1%}"
    if "cost" in metric_name:
        return f"${value:.4f}"
    if isinstance(value, float):
        return f"{value:.2f}"
    if isinstance(value, int) and value > 1000:
        return f"{value:,}"
    return str(value)


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Compare metrics between two simulation runs (Plan #227)"
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Two paths: baseline and treatment (directories or JSON files)",
    )
    parser.add_argument(
        "--baseline", "-b",
        help="Baseline log directory or metrics JSON",
    )
    parser.add_argument(
        "--treatment", "-t",
        help="Treatment log directory or metrics JSON",
    )
    parser.add_argument(
        "--output", "-o",
        help="Output JSON file for comparison results",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output JSON format instead of table",
    )

    args = parser.parse_args()

    # Determine baseline and treatment paths
    if args.baseline and args.treatment:
        baseline_path = Path(args.baseline)
        treatment_path = Path(args.treatment)
    elif len(args.paths) == 2:
        baseline_path = Path(args.paths[0])
        treatment_path = Path(args.paths[1])
    else:
        parser.print_help()
        print("\nError: Provide two paths (baseline and treatment)", file=sys.stderr)
        return 1

    # Load metrics
    try:
        baseline_agents, baseline_agg = load_metrics(baseline_path)
        treatment_agents, treatment_agg = load_metrics(treatment_path)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}", file=sys.stderr)
        return 1

    # Compare
    aggregate_comparisons = compare_aggregates(baseline_agg, treatment_agg)
    agent_comparisons = compare_agents(baseline_agents, treatment_agents)

    # Output
    if args.json or args.output:
        output = {
            "baseline": str(baseline_path),
            "treatment": str(treatment_path),
            "aggregate": aggregate_comparisons,
            "agents": agent_comparisons,
        }
        json_str = json.dumps(output, indent=2)

        if args.output:
            Path(args.output).write_text(json_str)
            print(f"Comparison written to {args.output}")
        else:
            print(json_str)
    else:
        print(format_comparison_table(
            baseline_path, treatment_path, aggregate_comparisons, agent_comparisons
        ))

    return 0


if __name__ == "__main__":
    sys.exit(main())
