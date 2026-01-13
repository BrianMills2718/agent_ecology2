# Pattern: Claim System

## Problem

When multiple AI instances (or developers) work in parallel:
- Two instances start the same work
- Neither knows the other is working
- Merge conflicts, wasted effort, confusion

## Solution

1. Before starting work, "claim" it in a shared file
2. Other instances see the claim and work on something else
3. When done, "release" the claim
4. Stale claims (>4 hours) flagged for cleanup
5. Plan dependencies checked before claiming

## Enforcement

**Claims are mandatory when creating worktrees.** The `make worktree` command runs an interactive script that:
1. Shows existing claims
2. Prompts for task description and plan number
3. Creates the claim in `.claude/active-work.yaml`
4. Only then creates the worktree

This prevents the common failure mode where developers forget to claim work.

```bash
make worktree  # Interactive - prompts for claim info
```

See [worktree-enforcement.md](worktree-enforcement.md) for the full worktree workflow.

## Files

| File | Purpose |
|------|---------|
| `.claude/active-work.yaml` | Machine-readable claim storage |
| `CLAUDE.md` | Human-readable Active Work table |
| `scripts/check_claims.py` | Claim management script |

## Setup

### 1. Create the claims file

```yaml
# .claude/active-work.yaml
claims: []
completed: []
```

### 2. Create the claims script

```python
#!/usr/bin/env python3
"""Manage work claims."""

import argparse
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import yaml

YAML_PATH = Path(".claude/active-work.yaml")
STALE_HOURS = 4

def get_current_branch() -> str:
    """Get current git branch as instance ID."""
    result = subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True
    )
    return result.stdout.strip() or "unknown"

def load_claims() -> dict:
    """Load claims from YAML file."""
    if YAML_PATH.exists():
        return yaml.safe_load(YAML_PATH.read_text()) or {"claims": [], "completed": []}
    return {"claims": [], "completed": []}

def save_claims(data: dict) -> None:
    """Save claims to YAML file."""
    YAML_PATH.parent.mkdir(exist_ok=True)
    YAML_PATH.write_text(yaml.dump(data, default_flow_style=False))

def claim(instance_id: str, task: str, plan: int | None = None) -> bool:
    """Claim work for an instance."""
    data = load_claims()

    # Check if already claimed
    for c in data["claims"]:
        if c.get("instance_id") == instance_id:
            print(f"Already have claim: {c['task']}")
            return False

    data["claims"].append({
        "instance_id": instance_id,
        "task": task,
        "plan": plan,
        "claimed_at": datetime.now(timezone.utc).isoformat(),
        "status": "in_progress"
    })
    save_claims(data)
    print(f"Claimed: {task}")
    return True

def release(instance_id: str) -> bool:
    """Release claim for an instance."""
    data = load_claims()

    for i, c in enumerate(data["claims"]):
        if c.get("instance_id") == instance_id:
            released = data["claims"].pop(i)
            released["released_at"] = datetime.now(timezone.utc).isoformat()
            data["completed"].append(released)
            save_claims(data)
            print(f"Released: {released['task']}")
            return True

    print("No active claim to release")
    return False

def list_claims(data: dict) -> None:
    """List all active claims."""
    if not data["claims"]:
        print("No active claims")
        return

    print("Active claims:")
    for c in data["claims"]:
        age = get_claim_age(c)
        stale = " (STALE)" if age > timedelta(hours=STALE_HOURS) else ""
        plan_info = f" [Plan #{c['plan']}]" if c.get("plan") else ""
        print(f"  {c['instance_id']}: {c['task']}{plan_info} ({age_str(age)}{stale})")

def check_stale(data: dict) -> list[dict]:
    """Find stale claims."""
    stale = []
    threshold = timedelta(hours=STALE_HOURS)
    for c in data["claims"]:
        if get_claim_age(c) > threshold:
            stale.append(c)
    return stale

def get_claim_age(claim: dict) -> timedelta:
    """Get age of claim."""
    claimed = datetime.fromisoformat(claim["claimed_at"])
    if claimed.tzinfo is None:
        claimed = claimed.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - claimed

def age_str(td: timedelta) -> str:
    """Format timedelta as string."""
    hours = td.total_seconds() / 3600
    if hours < 1:
        return f"{int(td.total_seconds() / 60)}m"
    return f"{hours:.1f}h"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--claim", action="store_true", help="Claim work")
    parser.add_argument("--release", action="store_true", help="Release claim")
    parser.add_argument("--list", action="store_true", help="List claims")
    parser.add_argument("--cleanup", action="store_true", help="Clean old completed")
    parser.add_argument("--task", type=str, help="Task description")
    parser.add_argument("--plan", type=int, help="Plan number")
    parser.add_argument("--id", type=str, help="Instance ID (default: branch)")
    args = parser.parse_args()

    instance_id = args.id or get_current_branch()
    data = load_claims()

    if args.list:
        list_claims(data)
        return 0

    if args.claim:
        if not args.task:
            print("ERROR: --task required")
            return 1
        claim(instance_id, args.task, args.plan)
        return 0

    if args.release:
        release(instance_id)
        return 0

    if args.cleanup:
        # Remove completed entries older than 24h
        threshold = datetime.now(timezone.utc) - timedelta(hours=24)
        data["completed"] = [
            c for c in data["completed"]
            if datetime.fromisoformat(c["released_at"]).replace(tzinfo=timezone.utc) > threshold
        ]
        save_claims(data)
        return 0

    # Default: check for stale claims
    stale = check_stale(data)
    if stale:
        print("WARNING: Stale claims detected:")
        for c in stale:
            print(f"  {c['instance_id']}: {c['task']} ({age_str(get_claim_age(c))})")
        return 1
    else:
        print("No stale claims")
        return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 3. Add Active Work table to CLAUDE.md

```markdown
## Active Work

<!-- Updated automatically by check_claims.py --sync -->
| Instance | Plan | Task | Claimed | Status |
|----------|------|------|---------|--------|
| - | - | - | - | - |
```

### 4. Add sync functionality

Add to `check_claims.py`:

```python
def sync_to_markdown(data: dict) -> None:
    """Sync YAML claims to CLAUDE.md Active Work table."""
    claude_md = Path("CLAUDE.md")
    content = claude_md.read_text()

    # Build new table
    rows = []
    for c in data["claims"]:
        plan = f"#{c['plan']}" if c.get("plan") else "-"
        rows.append(f"| {c['instance_id']} | {plan} | {c['task']} | {c['claimed_at'][:16]} | {c['status']} |")

    if not rows:
        rows = ["| - | - | - | - | - |"]

    table = "| Instance | Plan | Task | Claimed | Status |\n"
    table += "|----------|------|------|---------|--------|\n"
    table += "\n".join(rows)

    # Replace table in CLAUDE.md
    pattern = r"\| Instance \| Plan \|.*?(?=\n\n|\n###|\Z)"
    content = re.sub(pattern, table, content, flags=re.DOTALL)
    claude_md.write_text(content)
```

## Usage

### Claiming work

```bash
# Claim with auto-detected branch ID
python scripts/check_claims.py --claim --task "Implement feature X"

# Claim with plan reference
python scripts/check_claims.py --claim --plan 3 --task "Docker isolation"

# Claim with explicit instance ID
python scripts/check_claims.py --claim --id cc-instance-1 --task "Feature Y"
```

### Checking claims

```bash
# List all active claims
python scripts/check_claims.py --list

# Check for stale claims (default action)
python scripts/check_claims.py

# Check plan dependencies before claiming
python scripts/check_claims.py --check-deps 7
```

### Releasing claims

```bash
# Release current branch's claim
python scripts/check_claims.py --release

# Release with TDD validation
python scripts/check_claims.py --release --validate
```

### Maintenance

```bash
# Sync YAML to CLAUDE.md table
python scripts/check_claims.py --sync

# Clean up old completed entries (>24h)
python scripts/check_claims.py --cleanup
```

## Customization

### Change stale threshold

```python
STALE_HOURS = 4  # Default
STALE_HOURS = 8  # More relaxed
STALE_HOURS = 1  # More aggressive
```

### Add plan dependency checking

```python
def check_dependencies(plan_number: int) -> bool:
    """Check if blocking plans are complete."""
    # Parse plan file for "Blocked By: #X, #Y"
    # Check status of each blocker
    # Return False if any incomplete
    pass

# In claim():
if plan and not check_dependencies(plan):
    print("ERROR: Dependencies not complete")
    return False
```

### Add Slack notification for stale claims

```python
def notify_stale(stale_claims: list) -> None:
    import requests
    webhook = os.environ.get("SLACK_WEBHOOK")
    if webhook and stale_claims:
        msg = "Stale claims:\n" + "\n".join(
            f"- {c['instance_id']}: {c['task']}"
            for c in stale_claims
        )
        requests.post(webhook, json={"text": msg})
```

### Instance ID strategies

```python
# Option 1: Git branch (default)
def get_instance_id():
    return subprocess.run(
        ["git", "branch", "--show-current"],
        capture_output=True, text=True
    ).stdout.strip()

# Option 2: Hostname
def get_instance_id():
    import socket
    return socket.gethostname()

# Option 3: Environment variable
def get_instance_id():
    return os.environ.get("CC_INSTANCE_ID", "unknown")

# Option 4: Random ID per session
def get_instance_id():
    return f"cc-{uuid.uuid4().hex[:8]}"
```

## Limitations

- **Honor system** - Nothing stops someone from ignoring claims.
- **Git conflicts** - If two instances claim simultaneously, YAML may conflict.
- **Stale detection is passive** - Only flagged when script runs, not proactively.
- **No lock** - Claim is advisory, not a mutex.

## Best Practices

1. **Claim before starting** - Even for "quick" work
2. **Release promptly** - Don't hold claims overnight
3. **Check claims first** - `--list` before starting any work
4. **Use plan references** - Links claim to documentation
5. **Clean up regularly** - Run `--cleanup` periodically

## See Also

- [PR coordination pattern](pr-coordination.md) - Auto-claims on PR open
- [Plan workflow pattern](plan-workflow.md) - Plans that claims reference
- [Git hooks pattern](git-hooks.md) - Can check for claim before commit
