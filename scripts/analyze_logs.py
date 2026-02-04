#!/usr/bin/env python3
"""Log analysis tool for simulation runs.

Provides multiple views into simulation logs to understand agent behavior,
detect patterns, and identify collaboration opportunities.

Usage:
    python scripts/analyze_logs.py [LOG_DIR]              # Full analysis
    python scripts/analyze_logs.py [LOG_DIR] --summary    # Quick summary only
    python scripts/analyze_logs.py [LOG_DIR] --journeys   # Agent journeys
    python scripts/analyze_logs.py [LOG_DIR] --collab     # Collaboration metrics
    python scripts/analyze_logs.py [LOG_DIR] --loops      # Loop detection
    python scripts/analyze_logs.py --latest               # Use most recent log dir

If LOG_DIR is omitted, uses the most recent run in logs/.
"""

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class AgentStats:
    """Statistics for a single agent."""

    agent_id: str
    events: list[tuple[int, str, dict[str, Any]]] = field(default_factory=list)
    actions: Counter = field(default_factory=Counter)
    action_sequence: list[str] = field(default_factory=list)
    states: list[tuple[int, str, str]] = field(default_factory=list)
    artifacts_read: set[str] = field(default_factory=set)
    artifacts_written: set[str] = field(default_factory=set)
    artifacts_subscribed: set[str] = field(default_factory=set)
    reasoning_snippets: list[tuple[int, str]] = field(default_factory=list)
    total_tokens: int = 0
    total_cost: float = 0.0
    queries_with_results: int = 0
    queries_without_results: int = 0


@dataclass
class SimulationAnalysis:
    """Full analysis of a simulation run."""

    log_file: Path
    events: list[dict[str, Any]] = field(default_factory=list)
    event_counts: Counter = field(default_factory=Counter)
    agents: dict[str, AgentStats] = field(default_factory=dict)
    artifacts_created: dict[str, dict[str, Any]] = field(default_factory=dict)
    cross_agent_reads: list[tuple[int, str, str, str]] = field(default_factory=list)

    def load(self) -> None:
        """Load and parse the log file."""
        with open(self.log_file) as f:
            for line in f:
                event = json.loads(line)
                self.events.append(event)
                self._process_event(event)

    def _process_event(self, e: dict[str, Any]) -> None:
        """Process a single event."""
        etype = e.get("event_type", "?")
        seq = e.get("sequence", 0)
        self.event_counts[etype] += 1

        # Get agent ID from various places
        agent_id = (
            e.get("principal_id") or
            e.get("agent_id") or
            e.get("intent", {}).get("principal_id")
        )

        # Track artifact creation
        if etype == "artifact_written":
            aid = e.get("artifact_id")
            creator = e.get("created_by")
            if aid:
                self.artifacts_created[aid] = {
                    "creator": creator,
                    "created_at": seq,
                    "type": e.get("type", "?"),
                }

        # Skip non-agent events
        if not agent_id or agent_id == "kernel_mint_agent":
            return

        # Get or create agent stats
        if agent_id not in self.agents:
            self.agents[agent_id] = AgentStats(agent_id=agent_id)
        agent = self.agents[agent_id]
        agent.events.append((seq, etype, e))

        # Process by event type
        if etype == "thinking":
            agent.total_tokens += e.get("input_tokens", 0) + e.get("output_tokens", 0)
            agent.total_cost += e.get("api_cost", 0)
            reason = e.get("reasoning", "")[:150]
            if reason:
                agent.reasoning_snippets.append((seq, reason))

        elif etype == "action":
            self._process_action(agent, e, seq)

        elif etype == "workflow_state_changed":
            from_s = e.get("from_state", "?")
            to_s = e.get("to_state", "?")
            agent.states.append((seq, from_s, to_s))

    def _process_action(self, agent: AgentStats, e: dict[str, Any], seq: int) -> None:
        """Process an action event."""
        intent = e.get("intent", {})
        result = e.get("result", {})
        action_type = intent.get("action_type", "?")
        success = result.get("success", False)

        agent.actions[action_type] += 1

        # Build action signature for sequence tracking
        target = intent.get("artifact_id", "") or intent.get("params", {}).get("name_pattern", "")
        action_sig = f"{action_type}:{target[:30]}"
        agent.action_sequence.append(action_sig)

        # Track specific action types
        if action_type == "read_artifact":
            aid = intent.get("artifact_id", "")
            if success and aid:
                agent.artifacts_read.add(aid)
                # Check for cross-agent read
                if aid in self.artifacts_created:
                    creator = self.artifacts_created[aid].get("creator")
                    if creator and creator != agent.agent_id:
                        self.cross_agent_reads.append((seq, agent.agent_id, aid, creator))

        elif action_type == "write_artifact":
            aid = intent.get("artifact_id", "")
            if success and aid:
                agent.artifacts_written.add(aid)

        elif action_type == "subscribe_artifact":
            aid = intent.get("artifact_id", "")
            if success and aid:
                agent.artifacts_subscribed.add(aid)

        elif action_type == "query_kernel":
            data = result.get("data", {})
            if isinstance(data, dict):
                total = data.get("total", 0)
                if total > 0:
                    agent.queries_with_results += 1
                else:
                    agent.queries_without_results += 1


def print_summary(analysis: SimulationAnalysis) -> None:
    """Print quick summary of the simulation."""
    print("=" * 70)
    print("SIMULATION SUMMARY")
    print("=" * 70)

    print(f"\nLog file: {analysis.log_file}")
    print(f"Total events: {len(analysis.events)}")
    print(f"Agents: {len([a for a in analysis.agents if 'alpha_prime' not in a])}")

    print("\nEvent counts:")
    for etype, count in analysis.event_counts.most_common(10):
        print(f"  {etype}: {count}")

    # Quick agent summary
    print("\nAgent summary:")
    for agent_id, agent in sorted(analysis.agents.items()):
        if "alpha_prime" in agent_id:
            continue
        print(f"  {agent_id}:")
        print(f"    Actions: {sum(agent.actions.values())}, Tokens: {agent.total_tokens:,}, Cost: ${agent.total_cost:.4f}")
        print(f"    Read: {len(agent.artifacts_read)}, Written: {len(agent.artifacts_written)}, Subscribed: {len(agent.artifacts_subscribed)}")


def print_journeys(analysis: SimulationAnalysis) -> None:
    """Print detailed agent journey view."""
    print("=" * 70)
    print("AGENT JOURNEYS")
    print("=" * 70)

    for agent_id, agent in sorted(analysis.agents.items()):
        if "alpha_prime" in agent_id:
            continue

        print(f"\n{'=' * 70}")
        print(f"AGENT: {agent_id}")
        print(f"{'=' * 70}")

        print(f"\nTokens: {agent.total_tokens:,}  |  Cost: ${agent.total_cost:.4f}")
        print(f"Queries: {agent.queries_with_results} with results, {agent.queries_without_results} empty")

        print(f"\nActions: {dict(agent.actions)}")
        print(f"Artifacts read: {agent.artifacts_read or 'none'}")
        print(f"Artifacts written: {agent.artifacts_written or 'none'}")
        print(f"Subscriptions: {agent.artifacts_subscribed or 'none'}")

        # State transitions
        if agent.states:
            print(f"\nState transitions (first 5):")
            for seq, from_s, to_s in agent.states[:5]:
                print(f"  [{seq:3d}] {from_s} → {to_s}")
            if len(agent.states) > 5:
                print(f"  ... and {len(agent.states) - 5} more")

        # Action timeline
        print(f"\nAction sequence:")
        for i, action in enumerate(agent.action_sequence[:15], 1):
            print(f"  {i:2d}. {action}")
        if len(agent.action_sequence) > 15:
            print(f"  ... and {len(agent.action_sequence) - 15} more")

        # Key reasoning
        if agent.reasoning_snippets:
            print(f"\nKey reasoning (first 3):")
            for seq, reason in agent.reasoning_snippets[:3]:
                print(f"  [{seq:3d}] {reason}...")


def print_collaboration(analysis: SimulationAnalysis) -> None:
    """Print collaboration metrics."""
    print("=" * 70)
    print("COLLABORATION METRICS")
    print("=" * 70)

    # Cross-agent reads
    print("\nCross-agent artifact reads:")
    if analysis.cross_agent_reads:
        for seq, reader, aid, creator in analysis.cross_agent_reads:
            print(f"  [{seq:3d}] {reader} read {aid} (by {creator})")
    else:
        print("  NONE - agents only read their own artifacts or handbooks")

    # Subscriptions
    print("\nSubscriptions:")
    any_subs = False
    for agent_id, agent in sorted(analysis.agents.items()):
        if agent.artifacts_subscribed:
            any_subs = True
            for aid in agent.artifacts_subscribed:
                print(f"  {agent_id} → {aid}")
    if not any_subs:
        print("  NONE - no agents subscribed to any artifacts")

    # What could have been discovered
    agent_artifacts = {
        aid: info for aid, info in analysis.artifacts_created.items()
        if "handbook" not in aid.lower() and info.get("creator")
    }

    if agent_artifacts:
        print("\nDiscoverable agent artifacts:")
        for aid, info in sorted(agent_artifacts.items(), key=lambda x: x[1]["created_at"]):
            was_read = any(
                aid in agent.artifacts_read
                for agent in analysis.agents.values()
                if agent.agent_id != info.get("creator")
            )
            status = "✓ read by others" if was_read else "✗ never read by others"
            print(f"  [{info['created_at']:3d}] {aid} ({status})")


def print_loops(analysis: SimulationAnalysis) -> None:
    """Print loop/repetition detection."""
    print("=" * 70)
    print("LOOP / REPETITION DETECTION")
    print("=" * 70)

    for agent_id, agent in sorted(analysis.agents.items()):
        if "alpha_prime" in agent_id:
            continue

        print(f"\n{agent_id}:")

        # Count repeated actions
        action_counts = Counter(agent.action_sequence)
        repeated = [(a, c) for a, c in action_counts.most_common() if c > 1]

        if repeated:
            print("  Repeated actions:")
            for action, count in repeated[:5]:
                print(f"    {count}x {action}")
        else:
            print("  No repeated actions")

        # Detect patterns (simple: consecutive duplicates)
        consecutive = 0
        max_consecutive = 0
        prev = None
        for action in agent.action_sequence:
            if action == prev:
                consecutive += 1
                max_consecutive = max(max_consecutive, consecutive)
            else:
                consecutive = 1
            prev = action

        if max_consecutive > 1:
            print(f"  ⚠ Max consecutive identical actions: {max_consecutive}")

        # Check for cycles (simplified: look for repeated subsequences)
        seq = agent.action_sequence
        if len(seq) >= 4:
            # Check for 2-action cycles
            for i in range(len(seq) - 3):
                pattern = (seq[i], seq[i+1])
                if (seq[i+2], seq[i+3]) == pattern:
                    print(f"  ⚠ Potential cycle detected: {pattern[0]} → {pattern[1]}")
                    break

    # Summary
    print("\n" + "-" * 70)
    print("LOOP ANALYSIS SUMMARY")
    print("-" * 70)

    total_queries_failed = sum(
        agent.queries_without_results
        for agent in analysis.agents.values()
    )
    total_queries = total_queries_failed + sum(
        agent.queries_with_results
        for agent in analysis.agents.values()
    )

    if total_queries > 0:
        fail_rate = total_queries_failed / total_queries * 100
        print(f"Query success rate: {100-fail_rate:.0f}% ({total_queries - total_queries_failed}/{total_queries})")
        if fail_rate > 50:
            print("  ⚠ High query failure rate suggests agents searching for non-existent artifacts")


def find_latest_log_dir() -> Path | None:
    """Find the most recent log directory."""
    logs_dir = Path("logs")
    if not logs_dir.exists():
        return None

    run_dirs = sorted(logs_dir.glob("run_*"), reverse=True)
    for d in run_dirs:
        if (d / "events.jsonl").exists():
            return d
    return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze simulation logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "log_dir",
        nargs="?",
        help="Log directory to analyze (default: latest)"
    )
    parser.add_argument(
        "--latest", "-l",
        action="store_true",
        help="Use most recent log directory"
    )
    parser.add_argument(
        "--summary", "-s",
        action="store_true",
        help="Show summary only"
    )
    parser.add_argument(
        "--journeys", "-j",
        action="store_true",
        help="Show agent journeys"
    )
    parser.add_argument(
        "--collab", "-c",
        action="store_true",
        help="Show collaboration metrics"
    )
    parser.add_argument(
        "--loops", "-p",
        action="store_true",
        help="Show loop/repetition detection"
    )

    args = parser.parse_args()

    # Find log directory
    if args.log_dir:
        log_dir = Path(args.log_dir)
    else:
        log_dir = find_latest_log_dir()
        if not log_dir:
            print("Error: No log directory found. Run a simulation first.", file=sys.stderr)
            return 1

    log_file = log_dir / "events.jsonl"
    if not log_file.exists():
        print(f"Error: {log_file} not found", file=sys.stderr)
        return 1

    # Load and analyze
    analysis = SimulationAnalysis(log_file=log_file)
    analysis.load()

    # Determine what to show
    show_all = not any([args.summary, args.journeys, args.collab, args.loops])

    if args.summary or show_all:
        print_summary(analysis)

    if args.journeys or show_all:
        print()
        print_journeys(analysis)

    if args.collab or show_all:
        print()
        print_collaboration(analysis)

    if args.loops or show_all:
        print()
        print_loops(analysis)

    return 0


if __name__ == "__main__":
    sys.exit(main())
