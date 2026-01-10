#!/usr/bin/env python3
"""
Log viewer - summarize and analyze simulation runs

Usage:
    python view_log.py                    # Summary of run.jsonl
    python view_log.py --full             # Full event log
    python view_log.py --artifacts        # List all artifacts
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


def main():
    parser = argparse.ArgumentParser(description="View simulation logs")
    parser.add_argument("log_file", nargs="?", default="run.jsonl", help="Log file to view")
    parser.add_argument("--full", action="store_true", help="Show full event log")
    parser.add_argument("--artifacts", action="store_true", help="Show artifacts")
    args = parser.parse_args()

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
