#!/usr/bin/env python3
"""Meta-process status aggregator for Claude Code coordination.

Gathers claims, PRs, plan progress, and worktree status into a single
view. Claude Code reads this output and provides analysis/recommendations.

Usage:
    python scripts/meta_status.py          # Full status
    python scripts/meta_status.py --brief  # One-line summary
"""

import argparse
import subprocess
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path


def run_cmd(cmd: list[str], cwd: str | None = None) -> tuple[bool, str]:
    """Run command and return (success, output)."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=cwd,
            env={**subprocess.os.environ, "GIT_CONFIG_NOSYSTEM": "1"},
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def get_claims() -> list[dict]:
    """Get active claims from .claude/active-work.yaml."""
    claims_file = Path(".claude/active-work.yaml")
    if not claims_file.exists():
        return []
    
    try:
        with open(claims_file) as f:
            data = yaml.safe_load(f) or {}
        return data.get("claims", [])
    except Exception:
        return []


def get_open_prs() -> list[dict]:
    """Get open PRs from GitHub."""
    success, output = run_cmd([
        "gh", "pr", "list", 
        "--state", "open",
        "--json", "number,title,headRefName,createdAt,author"
    ])
    
    if not success or not output:
        return []
    
    try:
        import json
        return json.loads(output)
    except Exception:
        return []


def get_plan_progress() -> dict:
    """Get plan completion statistics."""
    plans_dir = Path("docs/plans")
    if not plans_dir.exists():
        return {"total": 0, "complete": 0, "in_progress": 0, "planned": 0}
    
    stats = {"total": 0, "complete": 0, "in_progress": 0, "planned": 0, "plans": []}
    
    for plan_file in sorted(plans_dir.glob("[0-9][0-9]_*.md")):
        content = plan_file.read_text()
        plan_num = plan_file.name.split("_")[0]
        
        stats["total"] += 1
        
        if "✅ Complete" in content:
            stats["complete"] += 1
            status = "complete"
        elif "🚧 In Progress" in content:
            stats["in_progress"] += 1
            status = "in_progress"
        elif "📋 Planned" in content:
            stats["planned"] += 1
            status = "planned"
        else:
            status = "unknown"
        
        # Extract title from first heading
        title = "Unknown"
        for line in content.split("\n"):
            if line.startswith("# "):
                title = line[2:].strip()
                break
        
        stats["plans"].append({
            "number": plan_num,
            "title": title,
            "status": status,
            "file": plan_file.name,
        })
    
    return stats


def get_worktrees() -> list[dict]:
    """Get git worktree information."""
    success, output = run_cmd(["git", "worktree", "list", "--porcelain"])
    if not success:
        return []
    
    worktrees = []
    current = {}
    
    for line in output.split("\n"):
        if line.startswith("worktree "):
            if current:
                worktrees.append(current)
            current = {"path": line[9:]}
        elif line.startswith("HEAD "):
            current["head"] = line[5:]
        elif line.startswith("branch "):
            current["branch"] = line[7:].replace("refs/heads/", "")
        elif line == "bare":
            current["bare"] = True
        elif line == "detached":
            current["detached"] = True
    
    if current:
        worktrees.append(current)
    
    return worktrees


def get_recent_commits(limit: int = 5) -> list[dict]:
    """Get recent commits on main."""
    success, output = run_cmd([
        "git", "log", 
        "-n", str(limit),
        "--format=%H|%s|%ar|%an",
        "main"
    ])
    
    if not success:
        return []
    
    commits = []
    for line in output.split("\n"):
        if "|" in line:
            parts = line.split("|")
            if len(parts) >= 4:
                commits.append({
                    "hash": parts[0][:7],
                    "message": parts[1],
                    "when": parts[2],
                    "author": parts[3],
                })
    
    return commits


def get_review_status() -> list[dict]:
    """Get PR review status from CLAUDE.md Awaiting Review table."""
    import re
    claude_md = Path("CLAUDE.md")
    if not claude_md.exists():
        return []

    try:
        content = claude_md.read_text()
        # Find the Awaiting Review table
        match = re.search(
            r"\*\*Awaiting Review:\*\*.*?\n\|.*?\n\|[-|\s]+\n((?:\|.*?\n)*)",
            content,
            re.DOTALL
        )
        if not match:
            return []

        reviews = []
        for line in match.group(1).strip().split("\n"):
            if not line.strip() or not line.startswith("|"):
                continue
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) >= 4:
                pr_num = cells[0].replace("#", "").strip()
                if not pr_num or pr_num == "-":
                    continue
                reviews.append({
                    "pr": pr_num,
                    "title": cells[1] if len(cells) > 1 else "",
                    "reviewer": cells[2] if len(cells) > 2 else "",
                    "started": cells[3] if len(cells) > 3 else "",
                    "status": cells[4] if len(cells) > 4 else "Awaiting",
                })
        return reviews
    except Exception:
        return []


def format_time_ago(iso_time: str) -> str:
    """Convert ISO timestamp to 'X ago' format."""
    try:
        dt = datetime.fromisoformat(iso_time.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        delta = now - dt
        
        if delta.days > 0:
            return f"{delta.days}d ago"
        elif delta.seconds >= 3600:
            return f"{delta.seconds // 3600}h ago"
        elif delta.seconds >= 60:
            return f"{delta.seconds // 60}m ago"
        else:
            return "just now"
    except Exception:
        return iso_time


def identify_issues(claims: list, prs: list, plans: dict, worktrees: list) -> list[str]:
    """Identify potential issues needing attention."""
    issues = []
    
    # Stale claims (> 4 hours with no corresponding PR)
    for claim in claims:
        claimed_at = claim.get("claimed_at", "")
        plan_num = claim.get("plan")
        
        # Check if there's a PR for this plan
        has_pr = any(
            f"Plan #{plan_num}" in pr.get("title", "") or
            f"plan-{plan_num}" in pr.get("headRefName", "")
            for pr in prs
        )
        
        if not has_pr and claimed_at:
            try:
                dt = datetime.fromisoformat(claimed_at.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                hours = (now - dt).total_seconds() / 3600
                if hours > 4:
                    issues.append(f"Claim on Plan #{plan_num} is {hours:.0f}h old with no PR")
            except Exception:
                pass
    
    # PRs that might conflict (same plan number)
    plan_prs: dict[str, list] = {}
    for pr in prs:
        title = pr.get("title", "")
        branch = pr.get("headRefName", "")
        
        # Extract plan number
        import re
        match = re.search(r"Plan #(\d+)", title) or re.search(r"plan-(\d+)", branch)
        if match:
            plan_num = match.group(1)
            if plan_num not in plan_prs:
                plan_prs[plan_num] = []
            plan_prs[plan_num].append(pr.get("number"))
    
    for plan_num, pr_nums in plan_prs.items():
        if len(pr_nums) > 1:
            issues.append(f"Plan #{plan_num} has multiple PRs: {pr_nums} - may conflict")
    
    # Orphaned worktrees (no recent commits)
    for wt in worktrees:
        if wt.get("path", "").endswith("/agent_ecology"):
            continue  # Skip main
        branch = wt.get("branch", "")
        if branch and not any(pr.get("headRefName") == branch for pr in prs):
            issues.append(f"Worktree '{branch}' has no open PR - orphaned?")
    
    # Old PRs (> 24h)
    for pr in prs:
        created = pr.get("createdAt", "")
        if created:
            try:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                hours = (now - dt).total_seconds() / 3600
                if hours > 24:
                    issues.append(f"PR #{pr.get('number')} is {hours:.0f}h old - needs merge or review?")
            except Exception:
                pass
    
    return issues


def print_status(brief: bool = False) -> None:
    """Print meta-process status."""
    claims = get_claims()
    prs = get_open_prs()
    reviews = get_review_status()
    plans = get_plan_progress()
    worktrees = get_worktrees()
    commits = get_recent_commits()
    issues = identify_issues(claims, prs, plans, worktrees)

    if brief:
        # One-line summary
        in_review = len([r for r in reviews if r.get("status") == "In Review"])
        print(f"Claims: {len(claims)} | PRs: {len(prs)} | Reviews: {in_review} active | Plans: {plans['complete']}/{plans['total']} | Issues: {len(issues)}")
        return
    
    print("=" * 60)
    print("META-PROCESS STATUS")
    print("=" * 60)
    print()
    
    # Claims
    print("## Active Claims")
    if claims:
        print()
        print("| Branch | Plan | Task | Claimed |")
        print("|--------|------|------|---------|")
        for claim in claims:
            branch = claim.get("branch", "-")
            plan = claim.get("plan", "-")
            task = claim.get("task", "-")[:40]
            claimed = format_time_ago(claim.get("claimed_at", ""))
            print(f"| {branch} | #{plan} | {task} | {claimed} |")
    else:
        print("No active claims.")
    print()
    
    # Open PRs
    print("## Open PRs")
    if prs:
        print()
        print("| # | Title | Branch | Created |")
        print("|---|-------|--------|---------|")
        for pr in prs:
            num = pr.get("number", "?")
            title = pr.get("title", "?")[:45]
            branch = pr.get("headRefName", "?")[:25]
            created = format_time_ago(pr.get("createdAt", ""))
            print(f"| {num} | {title} | {branch} | {created} |")
    else:
        print("No open PRs.")
    print()

    # Review Status
    print("## Review Status")
    if reviews:
        print()
        print("| PR | Title | Reviewer | Status |")
        print("|----|-------|----------|--------|")
        for r in reviews:
            pr_num = r.get("pr", "?")
            title = r.get("title", "?")[:35]
            reviewer = r.get("reviewer", "-") or "-"
            status = r.get("status", "Awaiting") or "Awaiting"
            print(f"| #{pr_num} | {title} | {reviewer} | {status} |")
    else:
        print("No PRs in review queue.")
    print()

    # Plan Progress
    print("## Plan Progress")
    print()
    total = plans["total"]
    complete = plans["complete"]
    pct = (complete / total * 100) if total > 0 else 0
    bar_len = 30
    filled = int(bar_len * pct / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    print(f"[{bar}] {pct:.0f}% ({complete}/{total})")
    print()
    print(f"- Complete: {plans['complete']}")
    print(f"- In Progress: {plans['in_progress']}")
    print(f"- Planned: {plans['planned']}")
    print()
    
    # In-progress plans detail
    in_progress = [p for p in plans.get("plans", []) if p["status"] == "in_progress"]
    if in_progress:
        print("**In Progress:**")
        for p in in_progress:
            print(f"  - Plan #{p['number']}: {p['title']}")
        print()
    
    # Worktrees
    print("## Worktrees")
    if worktrees:
        print()
        for wt in worktrees:
            path = wt.get("path", "?")
            branch = wt.get("branch", "detached")
            is_main = path.endswith("/agent_ecology") and "worktrees" not in path
            marker = " (main)" if is_main else ""
            print(f"  - {branch}{marker}")
    print()
    
    # Recent commits
    print("## Recent Commits (main)")
    if commits:
        print()
        for c in commits:
            print(f"  - {c['hash']} {c['message'][:50]} ({c['when']})")
    print()
    
    # Issues
    print("## Needs Attention")
    if issues:
        print()
        for issue in issues:
            print(f"  ⚠️  {issue}")
    else:
        print("No issues detected.")
    print()
    
    print("=" * 60)
    print("Run 'python scripts/meta_status.py --brief' for one-line summary")


def main() -> None:
    parser = argparse.ArgumentParser(description="Meta-process status for CC coordination")
    parser.add_argument("--brief", action="store_true", help="One-line summary")
    args = parser.parse_args()
    
    print_status(brief=args.brief)


if __name__ == "__main__":
    main()
