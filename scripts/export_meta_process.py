#!/usr/bin/env python3
"""
Export meta-process to the standalone template repository.

This script copies the portable meta-process framework from agent_ecology to
the standalone template repo, stripping project-specific content.

Usage:
    python scripts/export_meta_process.py --target /path/to/claude_code_meta_process
    python scripts/export_meta_process.py --target ~/projects/claude_code_meta_process --dry-run
    python scripts/export_meta_process.py --target /path/to/repo --version 1.0.0

What gets exported:
    - meta-process/patterns/     -> patterns/
    - meta-process/hooks/        -> hooks/
    - meta-process/ci/           -> ci/
    - meta-process/*.md          -> *.md
    - meta-process.yaml          -> meta-process.yaml.example
    - docs/plans/TEMPLATE.md     -> templates/PLAN_TEMPLATE.md
    - Portable scripts           -> scripts/

What gets stripped:
    - Agent ecology specific references in paths
    - Project-specific acceptance gates
    - Non-portable scripts
"""

import argparse
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


# Files/directories to export from meta-process/
EXPORT_FROM_META = [
    "patterns",
    "hooks",
    "ci",
    "GETTING_STARTED.md",
]

# Portable scripts to export
PORTABLE_SCRIPTS = [
    "check_planning_patterns.py",
    "check_claims.py",
    "check_doc_coupling.py",
    "generate_plan_index.py",
    "safe_worktree_remove.py",
    "finish_pr.py",
    "merge_pr.py",
    "sync_plan_status.py",
]

# Template files to generate
TEMPLATE_README = '''# Claude Code Meta-Process

A collection of patterns for coordinating AI coding assistants (Claude Code, Cursor, etc.) on shared codebases.

## What This Solves

- **Parallel work conflicts** - Multiple instances editing the same files
- **Context loss** - AI forgetting project conventions mid-session
- **Documentation drift** - Docs diverging from code over time
- **AI drift** - AI guessing instead of investigating

## Quick Start

```bash
# Clone this repo
git clone https://github.com/BrianMills2718/claude_code_meta_process.git

# Copy to your project
cp -r claude_code_meta_process/* your-project/meta-process/
cp claude_code_meta_process/meta-process.yaml.example your-project/meta-process.yaml

# Or use the install script
./install.sh /path/to/your-project
```

## Documentation

- [Getting Started](GETTING_STARTED.md) - Step-by-step adoption guide
- [Patterns](patterns/01_README.md) - All {pattern_count} patterns
- [Hooks](hooks/README.md) - Git and Claude Code hooks

## Patterns Overview

| Category | Patterns |
|----------|----------|
| **Core Workflow** | Worktrees, Claims, Plans |
| **Quality** | Testing, Mocking, Doc-Code Coupling |
| **Planning** | Question-Driven, Uncertainty Tracking, Conceptual Modeling |
| **Coordination** | PR Review, Ownership Respect |

## Configuration

Edit `meta-process.yaml` to control enforcement:

```yaml
weight: medium  # minimal | light | medium | heavy

planning:
  question_driven_planning: advisory  # disabled | advisory | required
  uncertainty_tracking: advisory
  warn_on_unverified_claims: true

project:
  type: existing  # new | existing | prototype
  complexity: moderate  # simple | moderate | complex
```

## Origin

Developed and stress-tested in [agent_ecology](https://github.com/BrianMills2718/agent_ecology2).

## Version

{version}

Generated: {date}
'''

TEMPLATE_CHANGELOG = '''# Changelog

## [{version}] - {date}

### Added
- Initial export from agent_ecology2
- {pattern_count} patterns for AI-assisted development
- Planning patterns: Question-Driven, Uncertainty Tracking, Conceptual Modeling
- Configurable enforcement levels (disabled/advisory/required)
- CI workflow templates for GitHub Actions
- Hook templates for Git and Claude Code
- Plan template with Open Questions and Uncertainties sections

### Configuration
- Weight levels: minimal, light, medium, heavy
- Per-pattern configuration
- Project type guidance (new/existing/prototype)

### Notes
- Patterns have been stress-tested in agent_ecology2 development
- See GETTING_STARTED.md for adoption guidance
'''


def count_patterns(source_dir: Path) -> int:
    """Count the number of patterns."""
    patterns_dir = source_dir / "meta-process" / "patterns"
    if not patterns_dir.exists():
        return 0
    return sum(1 for f in patterns_dir.glob("*.md") if f.name[0].isdigit())


def copy_directory(src: Path, dst: Path, dry_run: bool = False) -> None:
    """Copy directory, overwriting if exists."""
    if dry_run:
        print(f"  Would copy: {src} -> {dst}")
        return

    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    print(f"  Copied: {src.name}/")


def copy_file(src: Path, dst: Path, dry_run: bool = False) -> None:
    """Copy single file."""
    if dry_run:
        print(f"  Would copy: {src} -> {dst}")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  Copied: {src.name}")


def create_example_config(source_dir: Path, target_dir: Path, dry_run: bool = False) -> None:
    """Create meta-process.yaml.example from source config."""
    src = source_dir / "meta-process.yaml"
    dst = target_dir / "meta-process.yaml.example"

    if not src.exists():
        print(f"  WARNING: {src} not found, skipping config")
        return

    if dry_run:
        print(f"  Would create: {dst}")
        return

    content = src.read_text()

    header = """# Meta-Process Configuration Example
# ==================================
#
# Copy this file to meta-process.yaml in your project root.
# See GETTING_STARTED.md for guidance on settings.
#

"""
    dst.write_text(header + content)
    print(f"  Created: meta-process.yaml.example")


def create_generated_files(
    target_dir: Path, version: str, pattern_count: int, dry_run: bool = False
) -> None:
    """Create README.md and CHANGELOG.md."""
    date = datetime.now().strftime("%Y-%m-%d")

    readme_content = TEMPLATE_README.format(
        version=version, date=date, pattern_count=pattern_count
    )
    changelog_content = TEMPLATE_CHANGELOG.format(
        version=version, date=date, pattern_count=pattern_count
    )

    if dry_run:
        print(f"  Would create: README.md")
        print(f"  Would create: CHANGELOG.md")
        print(f"  Would create: VERSION")
        return

    (target_dir / "README.md").write_text(readme_content)
    (target_dir / "CHANGELOG.md").write_text(changelog_content)
    (target_dir / "VERSION").write_text(f"{version}\n")
    print(f"  Created: README.md, CHANGELOG.md, VERSION")


def copy_plan_template(source_dir: Path, target_dir: Path, dry_run: bool = False) -> None:
    """Copy plan template."""
    src = source_dir / "docs" / "plans" / "TEMPLATE.md"
    dst = target_dir / "templates" / "PLAN_TEMPLATE.md"

    if not src.exists():
        print(f"  WARNING: {src} not found")
        return

    if dry_run:
        print(f"  Would copy: {src} -> {dst}")
        return

    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    print(f"  Copied: templates/PLAN_TEMPLATE.md")


def copy_portable_scripts(source_dir: Path, target_dir: Path, dry_run: bool = False) -> None:
    """Copy portable scripts."""
    scripts_src = source_dir / "scripts"
    scripts_dst = target_dir / "scripts"

    copied = 0
    for script_name in PORTABLE_SCRIPTS:
        src = scripts_src / script_name
        if not src.exists():
            continue

        dst = scripts_dst / script_name
        if dry_run:
            print(f"  Would copy: {script_name}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1

    if not dry_run:
        print(f"  Copied: {copied} scripts")


def get_version(source_dir: Path, explicit_version: str | None) -> str:
    """Get version string."""
    if explicit_version:
        return explicit_version

    # Try git describe
    try:
        result = subprocess.run(
            ["git", "describe", "--tags", "--always"],
            cwd=source_dir,
            capture_output=True,
            text=True,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass

    # Fallback to date-based
    return datetime.now().strftime("0.1.0-%Y%m%d")


def main():
    parser = argparse.ArgumentParser(
        description="Export meta-process to standalone template repo"
    )
    parser.add_argument(
        "--target", "-t",
        type=Path,
        required=True,
        help="Target directory (the template repo)",
    )
    parser.add_argument(
        "--source", "-s",
        type=Path,
        default=Path.cwd(),
        help="Source directory (default: current directory)",
    )
    parser.add_argument(
        "--version", "-v",
        type=str,
        help="Version string (default: from git or date)",
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be done",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        help="Clean target before export (preserves .git)",
    )

    args = parser.parse_args()

    source_dir = args.source.resolve()
    target_dir = args.target.resolve()

    # Validate
    if not (source_dir / "meta-process").exists():
        print(f"ERROR: {source_dir}/meta-process not found")
        sys.exit(1)

    version = get_version(source_dir, args.version)
    pattern_count = count_patterns(source_dir)

    print(f"Export Meta-Process")
    print(f"  Source: {source_dir}")
    print(f"  Target: {target_dir}")
    print(f"  Version: {version}")
    print(f"  Patterns: {pattern_count}")
    print()

    # Clean if requested
    if args.clean and target_dir.exists() and not args.dry_run:
        print("Cleaning target (preserving .git)...")
        for item in target_dir.iterdir():
            if item.name == ".git":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()

    # Ensure target exists
    if not args.dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)

    # Export meta-process directories
    print("Exporting meta-process/...")
    meta_src = source_dir / "meta-process"
    for item_name in EXPORT_FROM_META:
        src = meta_src / item_name
        if src.exists():
            dst = target_dir / item_name
            if src.is_dir():
                copy_directory(src, dst, args.dry_run)
            else:
                copy_file(src, dst, args.dry_run)

    # Create config example
    print("Creating config example...")
    create_example_config(source_dir, target_dir, args.dry_run)

    # Copy plan template
    print("Copying plan template...")
    copy_plan_template(source_dir, target_dir, args.dry_run)

    # Copy portable scripts
    print("Copying portable scripts...")
    copy_portable_scripts(source_dir, target_dir, args.dry_run)

    # Generate files
    print("Generating files...")
    create_generated_files(target_dir, version, pattern_count, args.dry_run)

    print()
    if args.dry_run:
        print("Dry run complete. Remove --dry-run to apply.")
    else:
        print("Export complete!")
        print()
        print("Next steps:")
        print(f"  cd {target_dir}")
        print("  git add -A")
        print(f'  git commit -m "Update to {version}"')
        print(f"  git tag v{version}")
        print("  git push origin main --tags")


if __name__ == "__main__":
    main()
