#!/usr/bin/env python3
"""Check for stale claims and manage active work.

Usage:
    # Check for stale claims (default: >4 hours old)
    python scripts/check_claims.py

    # List all claims
    python scripts/check_claims.py --list

    # Claim work (auto-detects branch as ID)
    python scripts/check_claims.py --claim --task "Implement docker isolation"

    # Claim a plan (checks dependencies first)
    python scripts/check_claims.py --claim --plan 3 --task "Docker isolation"

    # Claim with explicit ID (if not using branches)
    python scripts/check_claims.py --claim --id my-instance --task "..."

    # Check if a task would overlap with existing claims (without claiming)
    python scripts/check_claims.py --check-overlap "Create feature definitions"

    # Release current branch's claim
    python scripts/check_claims.py --release

    # Verify current branch has a claim (CI mode)
    python scripts/check_claims.py --verify-claim

    # Sync YAML to CLAUDE.md table
    python scripts/check_claims.py --sync

    # Clean up old completed entries (>24h)
    python scripts/check_claims.py --cleanup

Branch name is used as instance identity by default.
Primary data store: .claude/active-work.yaml

Overlap Detection:
    When claiming, the script checks for overlapping claims based on:
    - Same plan number (always blocked)
    - Similar task descriptions (keyword-based similarity)
    Use --force to proceed despite overlap warnings.
"""

import argparse
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import yaml


YAML_PATH = Path(".claude/active-work.yaml")
CLAUDE_MD_PATH = Path("CLAUDE.md")
PLANS_DIR = Path("docs/plans")

# Keywords that indicate similar work scopes
SCOPE_KEYWORDS = {
    "feature": ["feature", "features", "definition", "definitions", "yaml"],
    "test": ["test", "tests", "testing", "tdd", "pytest"],
    "doc": ["doc", "docs", "documentation", "readme", "claude.md"],
    "ci": ["ci", "workflow", "github", "actions", "enforcement"],
    "plan": ["plan", "plans", "gap", "gaps", "implementation"],
    "claim": ["claim", "claims", "coordination", "checkout"],
}


def extract_scope_tags(text: str) -> set[str]:
    """Extract scope tags from text based on keywords."""
    text_lower = text.lower()
    tags: set[str] = set()

    for scope, keywords in SCOPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text_lower:
                tags.add(scope)
                break

    return tags


def compute_task_similarity(task1: str, task2: str) -> tuple[float, list[str]]:
    """Compute similarity between two task descriptions.

    Returns (similarity_score, list_of_overlapping_aspects).
    Score is 0.0 to 1.0.
    """
    # Extract scope tags
    tags1 = extract_scope_tags(task1)
    tags2 = extract_scope_tags(task2)

    # Check for overlapping scopes
    overlapping = tags1 & tags2
    if not overlapping:
        return (0.0, [])

    # Calculate Jaccard similarity of scope tags
    union = tags1 | tags2
    similarity = len(overlapping) / len(union) if union else 0.0

    # Boost similarity if exact words match
    words1 = set(task1.lower().split())
    words2 = set(task2.lower().split())
    word_overlap = words1 & words2

    # Filter out common words
    common_words = {"the", "a", "an", "to", "for", "and", "or", "in", "on", "with", "is", "are"}
    significant_overlap = word_overlap - common_words

    if len(significant_overlap) >= 3:
        similarity = min(1.0, similarity + 0.3)

    return (similarity, list(overlapping))


def check_claim_overlap(
    new_task: str,
    new_plan: int | None,
    existing_claims: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], float, list[str]]]:
    """Check if a new claim overlaps with existing claims.

    Returns list of (claim, similarity, overlapping_aspects) for overlapping claims.
    """
    overlaps: list[tuple[dict[str, Any], float, list[str]]] = []

    for claim in existing_claims:
        existing_task = claim.get("task", "")
        existing_plan = claim.get("plan")

        # Exact plan match is always an overlap
        if new_plan and existing_plan and new_plan == existing_plan:
            overlaps.append((claim, 1.0, ["same plan"]))
            continue

        # Check task similarity
        similarity, aspects = compute_task_similarity(new_task, existing_task)

        # Threshold for warning (0.4 = 40% overlap)
        if similarity >= 0.4:
            overlaps.append((claim, similarity, aspects))

    return overlaps


def get_plan_status(plan_number: int) -> tuple[str, list[int]]:
    """Get plan status and its blockers.

    Returns (status, blocked_by_list).
    Status is one of: 'complete', 'in_progress', 'blocked', 'planned', 'needs_plan', 'unknown'
    """
    plan_file = None
    for f in PLANS_DIR.glob(f"{plan_number:02d}_*.md"):
        plan_file = f
        break
    if not plan_file:
        for f in PLANS_DIR.glob(f"{plan_number}_*.md"):
            plan_file = f
            break

    if not plan_file or not plan_file.exists():
        return ("unknown", [])

    content = plan_file.read_text()

    # Parse status
    status = "unknown"
    status_match = re.search(r"\*\*Status:\*\*\s*(.+)", content)
    if status_match:
        raw_status = status_match.group(1).strip().lower()
        if "✅" in raw_status or "complete" in raw_status:
            status = "complete"
        elif "🚧" in raw_status or "in progress" in raw_status:
            status = "in_progress"
        elif "⏸️" in raw_status or "blocked" in raw_status:
            status = "blocked"
        elif "📋" in raw_status or "planned" in raw_status:
            status = "planned"
        elif "❌" in raw_status or "needs plan" in raw_status:
            status = "needs_plan"

    # Parse blockers
    blockers: list[int] = []
    blocked_match = re.search(r"\*\*Blocked By:\*\*\s*(.+)", content)
    if blocked_match:
        blocked_raw = blocked_match.group(1).strip()
        # Extract numbers from patterns like "#1", "#2, #3", "None"
        blocker_numbers = re.findall(r"#(\d+)", blocked_raw)
        blockers = [int(n) for n in blocker_numbers]

    return (status, blockers)


def check_plan_dependencies(plan_number: int) -> tuple[bool, list[str]]:
    """Check if all dependencies for a plan are complete.

    Returns (all_ok, list_of_issues).
    """
    status, blockers = get_plan_status(plan_number)
    issues: list[str] = []

    if not blockers:
        return (True, [])

    for blocker in blockers:
        blocker_status, _ = get_plan_status(blocker)
        if blocker_status != "complete":
            issues.append(f"Plan #{blocker} is not complete (status: {blocker_status})")

    return (len(issues) == 0, issues)


def cleanup_old_completed(data: dict[str, Any], hours: int = 24) -> int:
    """Remove completed entries older than threshold.

    Returns number of entries removed.
    """
    now = datetime.now()
    threshold = timedelta(hours=hours)

    completed = data.get("completed", [])
    original_count = len(completed)

    # Keep only recent completions
    data["completed"] = [
        c for c in completed
        if (ts := parse_timestamp(c.get("completed_at", ""))) is None
        or (now - ts) <= threshold
    ]

    removed = original_count - len(data["completed"])
    if removed > 0:
        save_yaml(data)

    return removed


def get_current_branch() -> str:
    """Get current git branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def verify_has_claim(data: dict[str, Any], branch: str) -> tuple[bool, str]:
    """Verify the current branch has an active claim.

    Returns (has_claim, message).
    """
    claims = data.get("claims", [])

    # Check if this branch has a claim
    for claim in claims:
        if claim.get("cc_id") == branch:
            task = claim.get("task", "")
            return (True, f"Active claim: {task}")

    # Special case: main branch with no active PRs is allowed for reviews
    if branch == "main":
        return (False, "No claim on main branch (use worktree for implementation)")

    return (False, f"No active claim for branch '{branch}'")


def load_yaml() -> dict[str, Any]:
    """Load claims from YAML file."""
    if not YAML_PATH.exists():
        return {"claims": [], "completed": []}

    with open(YAML_PATH) as f:
        data = yaml.safe_load(f) or {}

    return {
        "claims": data.get("claims") or [],
        "completed": data.get("completed") or [],
    }


def save_yaml(data: dict[str, Any]) -> None:
    """Save claims to YAML file."""
    YAML_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(YAML_PATH, "w") as f:
        f.write("# Active Work Lock File\n")
        f.write("# Machine-readable tracking for multi-CC coordination.\n")
        f.write("# Use: python scripts/check_claims.py --help\n\n")
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


def parse_timestamp(ts: str) -> datetime | None:
    """Parse various timestamp formats."""
    if not ts:
        return None

    formats = [
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(ts.strip(), fmt)
        except ValueError:
            continue
    return None


def get_age_string(ts: datetime) -> str:
    """Get human-readable age string."""
    now = datetime.now()
    hours = (now - ts).total_seconds() / 3600

    if hours < 1:
        return f"{int(hours * 60)}m ago"
    elif hours < 24:
        return f"{hours:.1f}h ago"
    else:
        return f"{hours / 24:.1f}d ago"


def check_stale_claims(claims: list[dict], hours: int) -> list[dict]:
    """Return claims older than the threshold."""
    now = datetime.now()
    threshold = timedelta(hours=hours)
    stale = []

    for claim in claims:
        ts = parse_timestamp(claim.get("claimed_at", ""))
        if ts and (now - ts) > threshold:
            claim["age_hours"] = (now - ts).total_seconds() / 3600
            stale.append(claim)

    return stale


def list_claims(claims: list[dict]) -> None:
    """Print all current claims."""
    if not claims:
        print("No active claims.")
        return

    print("Active Claims:")
    print("-" * 70)

    for claim in claims:
        ts = parse_timestamp(claim.get("claimed_at", ""))
        age = get_age_string(ts) if ts else "unknown"

        cc_id = claim.get("cc_id", "?")
        plan = claim.get("plan", "?")
        task = claim.get("task", "")[:35]
        branch = claim.get("branch", "")

        print(f"  {cc_id:8} | Plan #{plan:<3} | {task:35} | {age}")
        if branch:
            print(f"           Branch: {branch}")
        if claim.get("files"):
            print(f"           Files: {', '.join(claim['files'][:3])}")


def add_claim(
    data: dict[str, Any],
    cc_id: str,
    plan: int | None,
    task: str,
    files: list[str] | None = None,
    force: bool = False,
) -> bool:
    """Add a new claim."""
    # Check for existing claim by this instance
    for claim in data["claims"]:
        if claim.get("cc_id") == cc_id:
            existing_task = claim.get("task", "unknown")
            print(f"Error: {cc_id} already has an active claim: {existing_task}")
            print("Release it first with: python scripts/check_claims.py --release")
            return False

    # Check plan dependencies (if plan specified)
    if plan:
        deps_ok, dep_issues = check_plan_dependencies(plan)
        if not deps_ok:
            print(f"DEPENDENCY CHECK FAILED for Plan #{plan}:")
            for issue in dep_issues:
                print(f"  - {issue}")
            if not force:
                print("\nUse --force to claim anyway (not recommended).")
                return False
            print("\n--force specified, proceeding despite dependency issues.\n")

    # Check for overlapping claims (NEW)
    overlaps = check_claim_overlap(task, plan, data["claims"])
    if overlaps:
        print("=" * 60)
        print("⚠️  POTENTIAL OVERLAP DETECTED")
        print("=" * 60)
        for existing_claim, similarity, aspects in overlaps:
            pct = int(similarity * 100)
            existing_cc = existing_claim.get("cc_id", "?")
            existing_task = existing_claim.get("task", "")[:50]
            print(f"\n  Overlap with: {existing_cc}")
            print(f"  Their task:   {existing_task}")
            print(f"  Similarity:   {pct}% (overlapping: {', '.join(aspects)})")

        print("\n" + "-" * 60)
        print("This may cause duplicate work or merge conflicts.")
        print("Check with the other instance before proceeding.")

        if not force:
            print("\nUse --force to claim anyway (coordinates at your own risk).")
            return False
        print("\n--force specified, proceeding despite overlap warning.\n")

    # Check for conflicting claim on same plan (if plan specified)
    # Note: This is now partially redundant with overlap check above,
    # but kept for explicit plan-level warnings
    if plan:
        for claim in data["claims"]:
            if claim.get("plan") == plan:
                print(f"Warning: Plan #{plan} already claimed by {claim.get('cc_id')}")
                print("Proceed with caution to avoid conflicts.")

    new_claim = {
        "cc_id": cc_id,
        "task": task,
        "claimed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }

    if plan:
        new_claim["plan"] = plan
    if files:
        new_claim["files"] = files

    data["claims"].append(new_claim)
    save_yaml(data)

    if plan:
        print(f"Claimed: {cc_id} -> Plan #{plan}: {task}")
    else:
        print(f"Claimed: {cc_id} -> {task}")
    return True


def validate_plan_for_completion(plan_number: int) -> tuple[bool, list[str]]:
    """Run TDD and other validation checks for a plan.

    Returns (passed, list_of_issues).
    """
    issues: list[str] = []

    # Check required tests pass
    result = subprocess.run(
        ["python", "scripts/check_plan_tests.py", "--plan", str(plan_number)],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        if "MISSING" in result.stdout:
            missing_count = result.stdout.count("[MISSING]")
            issues.append(f"{missing_count} required test(s) missing")
        elif "No test requirements defined" not in result.stdout:
            issues.append("Required tests failing")

    # Check full test suite
    result = subprocess.run(
        ["pytest", "tests/", "-q", "--tb=no"],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        match = re.search(r"(\d+) failed", result.stdout)
        fail_count = match.group(1) if match else "some"
        issues.append(f"Test suite: {fail_count} test(s) failing")

    return (len(issues) == 0, issues)


def release_claim(
    data: dict[str, Any],
    cc_id: str,
    commit: str | None = None,
    validate: bool = False,
    force: bool = False,
) -> bool:
    """Release a claim and move to completed."""
    claim_to_remove = None

    for claim in data["claims"]:
        if claim.get("cc_id") == cc_id:
            claim_to_remove = claim
            break

    if not claim_to_remove:
        print(f"No active claim found for {cc_id}")
        return False

    # Run validation if requested
    plan = claim_to_remove.get("plan")
    if validate and plan:
        print(f"Validating Plan #{plan} before release...")
        valid, issues = validate_plan_for_completion(plan)
        if not valid:
            print("VALIDATION FAILED:")
            for issue in issues:
                print(f"  - {issue}")
            if not force:
                print("\nUse --force to release anyway (not recommended).")
                return False
            print("\n--force specified, releasing despite validation failures.\n")
    elif plan and not validate:
        print(f"Tip: Use --validate to check TDD requirements before release.")

    data["claims"].remove(claim_to_remove)

    # Add to completed history
    completion = {
        "cc_id": cc_id,
        "plan": claim_to_remove.get("plan"),
        "task": claim_to_remove.get("task"),
        "completed_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    if commit:
        completion["commit"] = commit

    data["completed"].append(completion)

    # Keep only last 20 completions
    data["completed"] = data["completed"][-20:]

    save_yaml(data)
    print(f"Released: {cc_id} (Plan #{claim_to_remove.get('plan')})")
    return True


def sync_to_claude_md(claims: list[dict]) -> bool:
    """Sync claims from YAML to CLAUDE.md Active Work table."""
    if not CLAUDE_MD_PATH.exists():
        print(f"Error: {CLAUDE_MD_PATH} not found")
        return False

    content = CLAUDE_MD_PATH.read_text()

    # Build new table rows
    if not claims:
        rows = "| - | - | - | - | - |\n"
    else:
        rows = ""
        for claim in claims:
            cc_id = claim.get("cc_id", "?")
            plan = claim.get("plan", "-")
            if plan is None:
                plan = "-"
            task = claim.get("task", "")[:40]
            claimed = claim.get("claimed_at", "")[:16]  # Truncate to minute
            status = "Active"
            rows += f"| {cc_id} | {plan} | {task} | {claimed} | {status} |\n"

    # Replace table content - match the header and separator, then all following rows
    # Separator row is distinguished by having only dashes and pipes, no spaces between pipes
    pattern = (
        r"(\*\*Active Work:\*\*\n"
        r"<!--.*?-->\n"  # Comment (non-greedy, handles > in content)
        r"\|[^\n]+\|\n"  # Header row
        r"\|[-|]+\|\n)"  # Separator row (only dashes and pipes)
        r"(?:\|[^\n]+\|\n)*"  # Data rows (to be replaced)
    )

    replacement = r"\1" + rows

    new_content, count = re.subn(pattern, replacement, content)

    if count == 0:
        print("Warning: Could not find Active Work table in CLAUDE.md")
        return False

    CLAUDE_MD_PATH.write_text(new_content)
    print(f"Synced {len(claims)} claim(s) to CLAUDE.md")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Manage active work claims for multi-CC coordination",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--hours", "-H",
        type=int,
        default=4,
        help="Hours before a claim is considered stale (default: 4)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="List all active claims"
    )
    parser.add_argument(
        "--claim",
        action="store_true",
        help="Claim work (uses current branch as ID)"
    )
    parser.add_argument(
        "--id",
        help="Explicit instance ID (default: current branch)"
    )
    parser.add_argument(
        "--plan", "-p",
        type=int,
        help="Plan number (optional)"
    )
    parser.add_argument(
        "--task", "-t",
        help="Task description"
    )
    parser.add_argument(
        "--release", "-r",
        action="store_true",
        help="Release current branch's claim"
    )
    parser.add_argument(
        "--commit",
        help="Commit hash when releasing (optional)"
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Sync YAML claims to CLAUDE.md table"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove completed entries older than 24h"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force claim even if dependencies not met"
    )
    parser.add_argument(
        "--check-deps",
        type=int,
        metavar="PLAN",
        help="Check dependencies for a plan (without claiming)"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run TDD validation when releasing (recommended for plan claims)"
    )
    parser.add_argument(
        "--verify-claim",
        action="store_true",
        help="CI mode: verify current branch has an active claim (exit 1 if not)"
    )
    parser.add_argument(
        "--check-overlap",
        type=str,
        metavar="TASK",
        help="Check if a task would overlap with existing claims (without claiming)"
    )

    args = parser.parse_args()

    data = load_yaml()
    claims = data.get("claims", [])

    # Determine instance ID (explicit or from branch)
    instance_id = args.id or get_current_branch()

    # Handle check-deps
    if args.check_deps:
        deps_ok, issues = check_plan_dependencies(args.check_deps)
        if deps_ok:
            print(f"Plan #{args.check_deps}: All dependencies satisfied ✓")
            return 0
        else:
            print(f"Plan #{args.check_deps}: Dependencies NOT satisfied:")
            for issue in issues:
                print(f"  - {issue}")
            return 1

    # Handle verify-claim (CI mode)
    if args.verify_claim:
        has_claim, message = verify_has_claim(data, instance_id)
        if has_claim:
            print(f"✓ {message}")
            return 0
        else:
            print("=" * 60)
            print("❌ CLAIM VERIFICATION FAILED")
            print("=" * 60)
            print(f"\n{message}")
            print("\nAll implementation work requires an active claim.")
            print("This ensures coordination between Claude instances.")
            print("\nTo fix:")
            print("  1. Create a worktree: make worktree BRANCH=my-feature")
            print("  2. Claim work: python scripts/check_claims.py --claim --task 'My task'")
            print("  3. Then commit your changes")
            return 1

    # Handle check-overlap (preview mode)
    if args.check_overlap:
        overlaps = check_claim_overlap(args.check_overlap, args.plan, claims)
        if not overlaps:
            print(f"✓ No overlapping claims found for: {args.check_overlap}")
            return 0
        else:
            print("⚠️  Potential overlaps detected:")
            for existing_claim, similarity, aspects in overlaps:
                pct = int(similarity * 100)
                existing_cc = existing_claim.get("cc_id", "?")
                existing_task = existing_claim.get("task", "")[:50]
                print(f"\n  {existing_cc}: {existing_task}")
                print(f"  Similarity: {pct}% (overlapping: {', '.join(aspects)})")
            return 1

    # Handle cleanup
    if args.cleanup:
        removed = cleanup_old_completed(data)
        if removed > 0:
            print(f"Cleaned up {removed} completed entries older than 24h")
        else:
            print("No old completed entries to clean up")
        return 0

    # Handle claim
    if args.claim:
        if not args.task:
            print("Error: --claim requires --task")
            print(f"Example: python scripts/check_claims.py --claim --task 'Implement feature X'")
            return 1
        if instance_id == "main":
            print("Warning: Claiming on 'main' branch. Consider using a feature branch.")
        success = add_claim(data, instance_id, args.plan, args.task, force=args.force)
        if success:
            sync_to_claude_md(data["claims"])
        return 0 if success else 1

    # Handle release
    if args.release:
        success = release_claim(
            data, instance_id, args.commit,
            validate=args.validate, force=args.force
        )
        if success:
            sync_to_claude_md(data["claims"])
        return 0 if success else 1

    # Handle sync
    if args.sync:
        return 0 if sync_to_claude_md(claims) else 1

    # Handle list
    if args.list:
        list_claims(claims)
        return 0

    # Default: check for stale claims
    stale = check_stale_claims(claims, args.hours)

    if not claims:
        print("No active claims.")
        return 0

    if not stale:
        print(f"No stale claims (threshold: {args.hours}h)")
        list_claims(claims)
        return 0

    print(f"STALE CLAIMS (>{args.hours}h old):")
    print("-" * 60)
    for claim in stale:
        print(f"  {claim.get('cc_id', '?'):8} | Plan #{claim.get('plan', '?'):<3} | {claim.get('age_hours', 0):.1f}h old")
        print(f"           Task: {claim.get('task', '')}")

    print()
    print("To release a stale claim:")
    print("  python scripts/check_claims.py --release <CC_ID>")

    return 1


if __name__ == "__main__":
    sys.exit(main())
