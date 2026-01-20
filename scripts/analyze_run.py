#!/usr/bin/env python3
"""Analyze simulation run metrics.

Usage:
    python scripts/analyze_run.py [RUN_DIR]
    python scripts/analyze_run.py logs/run_20260120_134859
    python scripts/analyze_run.py  # defaults to logs/latest

Outputs key metrics from a simulation run including:
- LLM success rate and thought capture
- Agent activity breakdown
- Invoke success/failure analysis
- Artifact creation stats
- Economic outcomes
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path


def load_events(run_dir: Path) -> list[dict]:
    """Load events from events.jsonl."""
    events_file = run_dir / "events.jsonl"
    if not events_file.exists():
        print(f"Error: {events_file} not found", file=sys.stderr)
        sys.exit(1)

    events = []
    with open(events_file) as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events


def find_llm_logs(run_dir: Path) -> list[Path]:
    """Find LLM log files for this run."""
    # Extract run_id from directory name
    run_id = run_dir.name  # e.g., "run_20260120_134859"

    # Look in llm_logs directory
    llm_logs_dir = run_dir.parent.parent / "llm_logs"
    if not llm_logs_dir.exists():
        return []

    # Find date subdirectory
    # run_20260120_134859 -> 20260120
    if run_id.startswith("run_"):
        date_str = run_id[4:12]  # Extract YYYYMMDD
        date_dir = llm_logs_dir / date_str
        if date_dir.exists():
            # Find files matching this run
            matching = []
            for f in date_dir.glob("*.json"):
                try:
                    with open(f) as fp:
                        data = json.load(fp)
                        if data.get("metadata", {}).get("run_id") == run_id:
                            matching.append(f)
                except (json.JSONDecodeError, KeyError):
                    continue
            return matching
    return []


def compute_llm_metrics(llm_logs: list[Path]) -> dict:
    """Compute LLM success rate from log files."""
    success = 0
    failure = 0

    for log_file in llm_logs:
        try:
            with open(log_file) as f:
                data = json.load(f)
                if data.get("metadata", {}).get("success"):
                    success += 1
                else:
                    failure += 1
        except (json.JSONDecodeError, KeyError):
            continue

    total = success + failure
    rate = success / total if total > 0 else 0
    return {
        "success": success,
        "failure": failure,
        "total": total,
        "rate": rate,
    }


def compute_thought_capture(events: list[dict]) -> dict:
    """Compute thought capture rate from thinking events."""
    total = 0
    captured = 0

    for e in events:
        if e.get("event_type") == "thinking":
            total += 1
            tp = e.get("thought_process", "")
            if tp and tp.strip():
                captured += 1

    rate = captured / total if total > 0 else 0
    return {
        "total": total,
        "captured": captured,
        "rate": rate,
    }


def compute_agent_actions(events: list[dict]) -> dict:
    """Compute action counts per agent and type."""
    by_agent: dict[str, Counter] = defaultdict(Counter)
    by_type: Counter = Counter()

    for e in events:
        if e.get("event_type") == "action":
            intent = e.get("intent", {})
            agent = intent.get("principal_id", "unknown")
            action_type = intent.get("action_type", "unknown")
            by_agent[agent][action_type] += 1
            by_type[action_type] += 1

    return {
        "by_agent": dict(by_agent),
        "by_type": dict(by_type),
    }


def compute_invoke_metrics(events: list[dict]) -> dict:
    """Compute invoke success rate and failure reasons."""
    success = sum(1 for e in events if e.get("event_type") == "invoke_success")
    failure = sum(1 for e in events if e.get("event_type") == "invoke_failure")

    # Collect failure reasons
    failure_reasons: Counter = Counter()
    for e in events:
        if e.get("event_type") == "invoke_failure":
            msg = e.get("error_message", "unknown")
            # Truncate long messages
            if len(msg) > 60:
                msg = msg[:60] + "..."
            failure_reasons[msg] += 1

    total = success + failure
    rate = success / total if total > 0 else 0
    return {
        "success": success,
        "failure": failure,
        "total": total,
        "rate": rate,
        "failure_reasons": dict(failure_reasons.most_common(5)),
    }


def compute_artifacts_created(events: list[dict]) -> dict:
    """Count artifacts created by each agent."""
    by_agent: Counter = Counter()
    by_type: Counter = Counter()

    for e in events:
        if e.get("event_type") == "action":
            intent = e.get("intent", {})
            result = e.get("result", {})
            if intent.get("action_type") == "write_artifact" and result.get("success"):
                agent = intent.get("principal_id", "unknown")
                atype = intent.get("artifact_type", "unknown")
                by_agent[agent] += 1
                by_type[atype] += 1

    return {
        "by_agent": dict(by_agent.most_common()),
        "by_type": dict(by_type.most_common()),
        "total": sum(by_agent.values()),
    }


def compute_economy(events: list[dict]) -> dict:
    """Compute final scrip balances and auction results."""
    # Track last known scrip for each agent
    final_scrip: dict[str, int] = {}
    starting_scrip = 100  # Default

    for e in events:
        if e.get("event_type") == "action":
            agent = e.get("intent", {}).get("principal_id")
            scrip = e.get("scrip_after")
            if agent and scrip is not None:
                final_scrip[agent] = scrip

    # Compute deltas
    scrip_deltas = {
        agent: scrip - starting_scrip
        for agent, scrip in final_scrip.items()
    }

    # Count auctions
    auctions_resolved = sum(
        1 for e in events
        if e.get("event_type") == "mint_auction_resolved"
    )

    total_minted = sum(
        e.get("scrip_minted", 0) or 0
        for e in events
        if e.get("event_type") == "mint_auction_resolved"
    )

    return {
        "final_scrip": final_scrip,
        "scrip_deltas": scrip_deltas,
        "auctions_resolved": auctions_resolved,
        "total_minted": total_minted,
    }


def compute_duration(events: list[dict]) -> str:
    """Compute run duration from first to last event."""
    if not events:
        return "0s"

    try:
        first = events[0].get("timestamp", "")
        last = events[-1].get("timestamp", "")

        # Parse ISO timestamps
        t1 = datetime.fromisoformat(first.replace("Z", "+00:00"))
        t2 = datetime.fromisoformat(last.replace("Z", "+00:00"))

        delta = t2 - t1
        seconds = int(delta.total_seconds())

        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            mins = seconds // 60
            secs = seconds % 60
            return f"{mins}m {secs}s"
        else:
            hours = seconds // 3600
            mins = (seconds % 3600) // 60
            return f"{hours}h {mins}m"
    except (ValueError, TypeError):
        return "unknown"


def format_report(run_dir: Path, events: list[dict], llm_metrics: dict,
                  thought_metrics: dict, action_metrics: dict,
                  invoke_metrics: dict, artifact_metrics: dict,
                  economy_metrics: dict) -> str:
    """Format metrics into a readable report."""
    lines = []

    # Header
    lines.append("=" * 60)
    lines.append(f"Run Analysis: {run_dir.name}")
    lines.append("=" * 60)

    duration = compute_duration(events)
    lines.append(f"Duration: {duration} | Events: {len(events)}")
    lines.append("")

    # LLM Performance
    lines.append("LLM PERFORMANCE:")
    llm_rate = llm_metrics["rate"] * 100
    llm_total = llm_metrics["total"]
    llm_success = llm_metrics["success"]
    status = "✓" if llm_rate >= 95 else "!"
    lines.append(f"  Success rate:    {llm_rate:.1f}% ({llm_success}/{llm_total}) {status}")

    thought_rate = thought_metrics["rate"] * 100
    thought_total = thought_metrics["total"]
    thought_cap = thought_metrics["captured"]
    status = "✓" if thought_rate >= 95 else "!"
    lines.append(f"  Thought capture: {thought_rate:.1f}% ({thought_cap}/{thought_total}) {status}")
    lines.append("")

    # Agent Activity
    lines.append("AGENT ACTIVITY:")
    by_agent = action_metrics["by_agent"]
    for agent in sorted(by_agent.keys()):
        counts = by_agent[agent]
        total = sum(counts.values())
        parts = [f"{k}:{v}" for k, v in sorted(counts.items())]
        lines.append(f"  {agent:12} {total:4} actions ({', '.join(parts)})")
    lines.append("")

    # Invoke Results
    lines.append("INVOKE RESULTS:")
    inv_rate = invoke_metrics["rate"] * 100
    inv_total = invoke_metrics["total"]
    inv_success = invoke_metrics["success"]
    status = "✓" if inv_rate >= 90 else "!"
    lines.append(f"  Success rate: {inv_rate:.1f}% ({inv_success}/{inv_total}) {status}")

    if invoke_metrics["failure_reasons"]:
        lines.append("  Top failures:")
        for reason, count in invoke_metrics["failure_reasons"].items():
            lines.append(f"    - {reason} ({count})")
    lines.append("")

    # Artifacts Created
    lines.append("ARTIFACTS CREATED:")
    art_by_agent = artifact_metrics["by_agent"]
    if art_by_agent:
        parts = [f"{agent}: {count}" for agent, count in art_by_agent.items()]
        lines.append(f"  {' | '.join(parts)}")
        lines.append(f"  Total: {artifact_metrics['total']} ({dict(artifact_metrics['by_type'])})")
    else:
        lines.append("  None")
    lines.append("")

    # Economy
    lines.append("ECONOMY:")
    scrip_parts = []
    for agent, scrip in sorted(economy_metrics["final_scrip"].items()):
        delta = economy_metrics["scrip_deltas"].get(agent, 0)
        sign = "+" if delta >= 0 else ""
        scrip_parts.append(f"{agent}: {scrip} ({sign}{delta})")
    if scrip_parts:
        lines.append(f"  {' | '.join(scrip_parts)}")

    auctions = economy_metrics["auctions_resolved"]
    minted = economy_metrics["total_minted"]
    if auctions > 0:
        lines.append(f"  Auctions: {auctions} resolved, {minted} scrip minted")
    lines.append("")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze simulation run metrics")
    parser.add_argument(
        "run_dir",
        nargs="?",
        default="logs/latest",
        help="Path to run directory (default: logs/latest)"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON instead of formatted text"
    )
    args = parser.parse_args()

    # Resolve run directory
    run_dir = Path(args.run_dir)
    if run_dir.is_symlink():
        run_dir = run_dir.resolve()

    if not run_dir.exists():
        print(f"Error: Run directory not found: {run_dir}", file=sys.stderr)
        sys.exit(1)

    # Load data
    events = load_events(run_dir)
    llm_logs = find_llm_logs(run_dir)

    # Compute metrics
    llm_metrics = compute_llm_metrics(llm_logs)
    thought_metrics = compute_thought_capture(events)
    action_metrics = compute_agent_actions(events)
    invoke_metrics = compute_invoke_metrics(events)
    artifact_metrics = compute_artifacts_created(events)
    economy_metrics = compute_economy(events)

    if args.json:
        # JSON output
        output = {
            "run_dir": str(run_dir),
            "event_count": len(events),
            "llm": llm_metrics,
            "thought_capture": thought_metrics,
            "actions": action_metrics,
            "invokes": invoke_metrics,
            "artifacts": artifact_metrics,
            "economy": economy_metrics,
        }
        print(json.dumps(output, indent=2))
    else:
        # Formatted output
        report = format_report(
            run_dir, events, llm_metrics, thought_metrics,
            action_metrics, invoke_metrics, artifact_metrics, economy_metrics
        )
        print(report)


if __name__ == "__main__":
    main()
