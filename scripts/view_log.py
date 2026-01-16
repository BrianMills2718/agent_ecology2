#!/usr/bin/env python3
"""
Log viewer - summarize and analyze simulation runs

Usage:
    python view_log.py                    # Summary of run.jsonl
    python view_log.py --full             # Full event log
    python view_log.py --artifacts        # List all artifacts
    python view_log.py --report           # Quick tick summary report (from summary.jsonl)
    python view_log.py run2.jsonl         # View different log file
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict


def load_events(log_file: str) -> list:
    """Load all events from JSONL file"""
    events = []
    with open(log_file) as f:
        for line in f:
            if line.strip():
                events.append(json.loads(line))
    return events


def summarize(events: list) -> None:
    """Print summary statistics"""
    # Extract data
    init_event = next((e for e in events if e["event_type"] == "world_init"), None)
    tick_events = [e for e in events if e["event_type"] == "tick"]
    action_events = [e for e in events if e["event_type"] == "action"]
    rejected_events = [e for e in events if e["event_type"] == "intent_rejected"]

    # Agent stats
    agent_stats = defaultdict(lambda: {"actions": 0, "success": 0, "failed": 0, "spent": 0})
    for e in action_events:
        agent_id = e["intent"]["principal_id"]
        agent_stats[agent_id]["actions"] += 1
        if e["result"]["success"]:
            agent_stats[agent_id]["success"] += 1
            agent_stats[agent_id]["spent"] += e.get("cost", 0)
        else:
            agent_stats[agent_id]["failed"] += 1

    # Action type breakdown
    action_types = defaultdict(int)
    for e in action_events:
        action_types[e["intent"]["action_type"]] += 1

    # Print summary
    print("=" * 60)
    print("SIMULATION SUMMARY")
    print("=" * 60)

    if init_event:
        print(f"\nConfiguration:")
        print(f"  Max ticks: {init_event.get('max_ticks', '?')}")
        print(f"  Credits per tick: {init_event.get('credits_per_tick', '?')}")
        print(f"  Costs: {init_event.get('costs', {})}")

    print(f"\nRun Statistics:")
    print(f"  Total ticks: {len(tick_events)}")
    print(f"  Total actions: {len(action_events)}")
    print(f"  Rejected intents: {len(rejected_events)}")

    print(f"\nAction Types:")
    for action_type, count in sorted(action_types.items()):
        print(f"  {action_type}: {count}")

    print(f"\nAgent Statistics:")
    last_tick = tick_events[-1] if tick_events else {}
    final_balances = last_tick.get("balances", {})

    for agent_id, stats in sorted(agent_stats.items()):
        final_bal = final_balances.get(agent_id, "?")
        print(f"\n  {agent_id}:")
        print(f"    Actions: {stats['actions']} ({stats['success']} success, {stats['failed']} failed)")
        print(f"    Credits spent: {stats['spent']}")
        print(f"    Final balance: {final_bal}")

    # Show artifacts
    artifacts = set()
    for e in action_events:
        if e["intent"]["action_type"] == "write_artifact":
            artifacts.add(e["intent"].get("artifact_id", "?"))

    print(f"\nArtifacts Created: {len(artifacts)}")
    for a in sorted(artifacts):
        print(f"  - {a}")


def show_full_log(events: list) -> None:
    """Print full event log in readable format"""
    print("=" * 60)
    print("FULL EVENT LOG")
    print("=" * 60)

    for e in events:
        event_type = e.get("event_type", "?")
        ts = e.get("timestamp", "")[:19]  # Truncate to seconds

        if event_type == "world_init":
            print(f"\n[{ts}] WORLD INIT")
            print(f"  Principals: {[p['id'] for p in e.get('principals', [])]}")

        elif event_type == "tick":
            print(f"\n[{ts}] TICK {e.get('tick', '?')}")
            print(f"  Balances: {e.get('balances', {})}")
            print(f"  Artifacts: {e.get('artifact_count', 0)}")

        elif event_type == "action":
            intent = e.get("intent", {})
            result = e.get("result", {})
            status = "OK" if result.get("success") else "FAIL"
            print(f"\n[{ts}] ACTION ({status})")
            print(f"  Agent: {intent.get('principal_id', '?')}")
            print(f"  Type: {intent.get('action_type', '?')}")
            if intent.get("artifact_id"):
                print(f"  Artifact: {intent.get('artifact_id')}")
            if intent.get("content"):
                content = intent.get("content", "")
                print(f"  Content: {content[:80]}{'...' if len(content) > 80 else ''}")
            print(f"  Result: {result.get('message', '?')}")
            print(f"  Cost: {e.get('cost', 0)}, Balance after: {e.get('balance_after', '?')}")

        elif event_type == "intent_rejected":
            print(f"\n[{ts}] REJECTED")
            print(f"  Agent: {e.get('principal_id', '?')}")
            print(f"  Error: {e.get('error', '?')}")


def show_artifacts(events: list) -> None:
    """Show all artifacts and their contents"""
    print("=" * 60)
    print("ARTIFACTS")
    print("=" * 60)

    artifacts = {}
    for e in events:
        if e.get("event_type") == "action" and e["intent"].get("action_type") == "write_artifact":
            intent = e["intent"]
            aid = intent.get("artifact_id", "?")
            artifacts[aid] = {
                "type": intent.get("artifact_type", "?"),
                "content": intent.get("content", ""),
                "owner": intent.get("principal_id", "?"),
                "tick": e.get("tick", "?")
            }

    for aid, data in sorted(artifacts.items()):
        print(f"\n--- {aid} ---")
        print(f"Type: {data['type']}, Owner: {data['owner']}, Tick: {data['tick']}")
        print(f"Content:\n{data['content']}")


def show_report(summary_file: str) -> None:
    """Show quick tick summary report from summary.jsonl (Plan #60).

    Displays a concise overview of the simulation run:
    - Per-tick statistics
    - Total actions by type
    - Notable highlights
    """
    summaries = []
    with open(summary_file) as f:
        for line in f:
            if line.strip():
                summaries.append(json.loads(line))

    if not summaries:
        print("No tick summaries found.")
        return

    print("=" * 60)
    print("TICK SUMMARY REPORT")
    print("=" * 60)

    # Aggregate stats
    total_actions = sum(s.get("actions_executed", 0) for s in summaries)
    total_tokens = sum(s.get("total_llm_tokens", 0) for s in summaries)
    total_scrip = sum(s.get("total_scrip_transferred", 0) for s in summaries)
    total_artifacts = sum(s.get("artifacts_created", 0) for s in summaries)
    total_errors = sum(s.get("errors", 0) for s in summaries)

    # Action type breakdown across all ticks
    action_types = defaultdict(int)
    for s in summaries:
        for action_type, count in s.get("actions_by_type", {}).items():
            action_types[action_type] += count

    # All highlights
    all_highlights = []
    for s in summaries:
        for h in s.get("highlights", []):
            all_highlights.append((s.get("tick", "?"), h))

    print(f"\nRun Overview:")
    print(f"  Total ticks: {len(summaries)}")
    print(f"  Total actions: {total_actions}")
    print(f"  Total LLM tokens: {total_tokens:,}")
    print(f"  Total scrip transferred: {total_scrip}")
    print(f"  Artifacts created: {total_artifacts}")
    print(f"  Total errors: {total_errors}")

    if action_types:
        print(f"\nAction Types:")
        for action_type, count in sorted(action_types.items(), key=lambda x: -x[1]):
            print(f"  {action_type}: {count}")

    if all_highlights:
        print(f"\nHighlights:")
        for tick, highlight in all_highlights[-10:]:  # Last 10 highlights
            print(f"  [Tick {tick}] {highlight}")
        if len(all_highlights) > 10:
            print(f"  ... and {len(all_highlights) - 10} more")

    # Per-tick summary table
    print(f"\nPer-Tick Summary:")
    print(f"  {'Tick':>5} {'Agents':>7} {'Actions':>8} {'Tokens':>8} {'Errors':>6}")
    print(f"  {'-'*5} {'-'*7} {'-'*8} {'-'*8} {'-'*6}")
    for s in summaries[:20]:  # Show first 20 ticks
        tick = s.get("tick", "?")
        agents = s.get("agents_active", 0)
        actions = s.get("actions_executed", 0)
        tokens = s.get("total_llm_tokens", 0)
        errors = s.get("errors", 0)
        print(f"  {tick:>5} {agents:>7} {actions:>8} {tokens:>8} {errors:>6}")
    if len(summaries) > 20:
        print(f"  ... and {len(summaries) - 20} more ticks")


def main():
    parser = argparse.ArgumentParser(description="View simulation logs")
    parser.add_argument("log_file", nargs="?", default="run.jsonl", help="Log file to view")
    parser.add_argument("--full", action="store_true", help="Show full event log")
    parser.add_argument("--artifacts", action="store_true", help="Show artifacts")
    parser.add_argument("--report", action="store_true", help="Show tick summary report (reads summary.jsonl)")
    args = parser.parse_args()

    # Handle --report mode (reads summary.jsonl, not events.jsonl)
    if args.report:
        # Determine summary file location
        log_path = Path(args.log_file)
        if log_path.name in ("run.jsonl", "events.jsonl"):
            # Look for summary.jsonl in same directory
            summary_file = log_path.parent / "summary.jsonl"
        elif log_path.is_dir():
            # Directory provided - look for summary.jsonl inside
            summary_file = log_path / "summary.jsonl"
        else:
            # Assume it's the summary file itself
            summary_file = log_path

        if not summary_file.exists():
            print(f"Error: {summary_file} not found")
            print("Hint: --report reads summary.jsonl (created in per-run mode)")
            return

        show_report(str(summary_file))
        return

    if not Path(args.log_file).exists():
        print(f"Error: {args.log_file} not found")
        return

    events = load_events(args.log_file)

    if args.full:
        show_full_log(events)
    elif args.artifacts:
        show_artifacts(events)
    else:
        summarize(events)


if __name__ == "__main__":
    main()
