# Pattern: Coordination Table Automation

## Problem

Multiple Claude Code instances updating coordination tables (Active Work, Awaiting Review) in CLAUDE.md causes:

- **Merge conflicts**: Every PR that updates status touches the same file section
- **Stale data**: Tables become outdated when manual updates are forgotten
- **Conflict cascades**: PRs created in parallel all conflict with each other
- **Wasted effort**: PRs created solely to update tables (meta-work)

In the agent_ecology project, we observed 6+ PRs all conflicting because they each tried to update the same coordination tables.

## Solution

**Auto-generate coordination tables** from source-of-truth data:

1. **Active Work** table generated from `.claude/active-work.yaml`
2. **Awaiting Review** table generated from `gh pr list`

Tables become read-only output. No manual edits needed → no conflicts.

**Enforcement:**
- CI blocks PRs that manually edit tables (diff against generated output)
- Post-merge workflow auto-updates tables on main

## Files

| File | Purpose |
|------|---------|
| `scripts/generate_coordination_tables.py` | Generates tables from source data |
| `.github/workflows/ci.yml` | CI job that blocks manual edits |
| `.github/workflows/sync-coordination-tables.yml` | Auto-updates after merges |

## Setup

### 1. Add the generation script

```bash
# Copy scripts/generate_coordination_tables.py to your project
chmod +x scripts/generate_coordination_tables.py
```

### 2. Add CI enforcement

Add to `.github/workflows/ci.yml`:

```yaml
coordination-tables:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - run: pip install pyyaml
    - name: Check coordination tables
      env:
        GH_TOKEN: ${{ github.token }}
      run: python scripts/generate_coordination_tables.py --check
```

### 3. Add post-merge auto-sync

Create `.github/workflows/sync-coordination-tables.yml`:

```yaml
name: Sync Coordination Tables

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  sync:
    runs-on: ubuntu-latest
    if: "!contains(github.event.head_commit.message, '[Auto] Sync coordination tables')"
    steps:
      - uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install pyyaml
      - name: Generate tables
        env:
          GH_TOKEN: ${{ github.token }}
        run: python scripts/generate_coordination_tables.py --apply
      - name: Commit if changed
        run: |
          git diff --quiet CLAUDE.md || (
            git config user.name "github-actions[bot]"
            git config user.email "github-actions[bot]@users.noreply.github.com"
            git add CLAUDE.md
            git commit -m "[Auto] Sync coordination tables"
            git push
          )
```

### 4. Mark tables as auto-generated

The script adds comments to tables:

```markdown
**Active Work:**
<!-- AUTO-GENERATED from .claude/active-work.yaml - Do not edit manually -->
```

## Usage

```bash
# See what tables would be generated
python scripts/generate_coordination_tables.py

# Check if tables are in sync (CI mode)
python scripts/generate_coordination_tables.py --check

# Update tables locally (rarely needed - auto-sync handles this)
python scripts/generate_coordination_tables.py --apply
```

## Customization

### Table format

Edit `generate_coordination_tables.py` functions:
- `generate_active_work_table()` - Active Work format
- `generate_awaiting_review_table()` - Awaiting Review format

### Additional data sources

The script can be extended to pull from:
- GitHub Issues (`gh issue list`)
- Project boards
- External tracking systems

## Limitations

- **Requires `gh` CLI**: Script uses GitHub CLI for PR data
- **GitHub Actions permissions**: Post-merge workflow needs write access
- **Network dependency**: CI check needs GitHub API access
- **Eventual consistency**: Tables update after merge, not immediately

## Related Patterns

| Pattern | Relationship |
|---------|--------------|
| [Claim System](claim-system.md) | Source of Active Work data |
| [PR Coordination](pr-coordination.md) | Supersedes manual Awaiting Review updates |
| [Worktree Enforcement](worktree-enforcement.md) | Prevents conflicts but doesn't solve table conflicts |
