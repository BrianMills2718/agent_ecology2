# Agent Ecology - Meta Patterns Review Package

Generated: 2026-01-14 06:35

This document concatenates all meta pattern documentation
in recommended reading order for external review.

## Table of Contents

01. [Overview](#01-overview)
02. [CLAUDE.md Authoring](#02-claudemd-authoring)
03. [Testing Strategy](#03-testing-strategy)
04. [Mocking Policy](#04-mocking-policy)
05. [Mock Enforcement](#05-mock-enforcement)
06. [Git Hooks](#06-git-hooks)
07. [ADR](#07-adr)
08. [ADR Governance](#08-adr-governance)
09. [Documentation Graph](#09-documentation-graph)
10. [Doc-Code Coupling](#10-doc-code-coupling)
11. [Terminology](#11-terminology)
12. [Structured Logging](#12-structured-logging)
13. [Feature-Driven Development](#13-feature-driven-development)
14. [Feature Linkage](#14-feature-linkage)
15. [Plan Workflow](#15-plan-workflow)
16. [Plan Blocker Enforcement](#16-plan-blocker-enforcement)
17. [Verification Enforcement](#17-verification-enforcement)
18. [Claim System](#18-claim-system)
19. [Worktree Enforcement](#19-worktree-enforcement)
20. [Rebase Workflow](#20-rebase-workflow)
21. [PR Coordination](#21-pr-coordination)
22. [Human Review Pattern](#22-human-review-pattern)

---


## 01. Overview

*Source: `docs/meta/01_README.md`*


Reusable development process patterns. Each pattern solves a specific coordination or quality problem when working with AI coding assistants (Claude Code, etc.).

## Pattern Index

| Pattern | Problem Solved | Complexity |
|---------|----------------|------------|
| [CLAUDE.md Authoring](02_claude-md-authoring.md) | AI assistants lack project context | Low |
| [Testing Strategy](03_testing-strategy.md) | Inconsistent test approaches | Low |
| [Mocking Policy](04_mocking-policy.md) | When to mock, when not to | Low |
| [Mock Enforcement](05_mock-enforcement.md) | Green CI, broken production | Low |
| [Git Hooks](06_git-hooks.md) | CI failures caught late | Low |
| [ADR](07_adr.md) | Architectural decisions get lost | Medium |
| [ADR Governance](08_adr-governance.md) | ADRs not linked to code | Medium |
| [Documentation Graph](09_documentation-graph.md) | Can't trace decisions → code | Medium |
| [Doc-Code Coupling](10_doc-code-coupling.md) | Docs drift from code | Medium |
| [Terminology](11_terminology.md) | Inconsistent terms | Low |
| [Structured Logging](12_structured-logging.md) | Unreadable logs | Low |
| [Feature-Driven Development](13_feature-driven-development.md) | AI drift, cheating, big bang integration | High |
| [Feature Linkage](14_feature-linkage.md) | Sparse file-to-constraint mappings | Medium |
| [Plan Workflow](15_plan-workflow.md) | Untracked work, scope creep | Medium |
| [Plan Blocker Enforcement](16_plan-blocker-enforcement.md) | Blocked plans started anyway | Medium |
| [Verification Enforcement](17_verification-enforcement.md) | Untested "complete" work | Medium |
| [Claim System](18_claim-system.md) | Parallel work conflicts | Medium |
| [Worktree Enforcement](19_worktree-enforcement.md) | Main directory corruption from parallel edits | Low |
| [Rebase Workflow](20_rebase-workflow.md) | Stale worktrees causing "reverted" changes | Low |
| [PR Coordination](21_pr-coordination.md) | Lost review requests | Low |
| [Human Review Pattern](22_human-review-pattern.md) | Risky changes merged without review | Medium |

### Subsumed Patterns

These patterns are now implementation details of [Documentation Graph](09_documentation-graph.md):

| Pattern | Status |
|---------|--------|
| [ADR Governance](08_adr-governance.md) | `governs` edges in relationships.yaml |
| [Doc-Code Coupling](10_doc-code-coupling.md) | `documented_by` edges in relationships.yaml |

## When to Use

**Start with these (low overhead):**
- CLAUDE.md Authoring - any project using AI coding assistants
- Mock Enforcement - if using pytest with mocks
- Git Hooks - any project with CI
- PR Coordination - if multiple people/instances work in parallel
- Worktree Enforcement - if multiple Claude Code instances share a repo
- Rebase Workflow - when using worktrees for parallel work (prevents "reverted" changes)

**Add these when needed (more setup):**
- Feature-Driven Development - comprehensive meta-process for verified progress, preventing AI drift/cheating
- ADR - when architectural decisions need to be preserved long-term
- Documentation Graph - when you need to trace ADR → target → current → code
- Plan Workflow - for larger features with multiple steps
- Claim System - for explicit parallel work coordination
- Verification Enforcement - when plans need proof of completion

## Pattern Template

When adding new patterns, follow this structure:

```markdown
# Pattern: [Name]

## Problem
What goes wrong without this?

## Solution
How does this pattern solve it?

## Files
| File | Purpose |
|------|---------|
| ... | ... |

## Setup
Steps to add to a new project.

## Usage
Day-to-day commands.

## Customization
What to change for different projects.

## Limitations
What this pattern doesn't solve.
```

## Archive

Deprecated patterns are in `archive/`:
- `handoff-protocol.md` - Superseded by automatic context compaction

## Origin

These patterns emerged from the [agent_ecology](https://github.com/BrianMills2718/agent_ecology2) project while coordinating multiple Claude Code instances on a shared codebase.

---


## 02. CLAUDE.md Authoring

*Source: `docs/meta/02_claude-md-authoring.md`*


## Problem

AI coding assistants (Claude Code, Cursor, etc.) start each session without project context. They:
- Don't know your conventions
- Don't know your architecture
- Don't know what terminology you use
- Make assumptions that conflict with your design

Result: Wasted time correcting the AI, inconsistent code, violated principles.

## Solution

Create a `CLAUDE.md` file at project root that AI assistants automatically read. Include:
1. Project overview (what this is, what it's NOT)
2. Key commands (how to build, test, run)
3. Design principles (fail loud, no magic numbers, etc.)
4. Terminology (canonical names for concepts)
5. Coordination protocol (if multiple AI instances)

## Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Root context file (always loaded) |
| `*/CLAUDE.md` | Directory-specific context (loaded when working in that directory) |

## Setup

### 1. Create root CLAUDE.md

```markdown
# Project Name - Claude Code Context

This file is always loaded. Keep it lean. Reference other docs for details.

## What This Is

[1-2 sentences: what the project does]

## What This Is NOT

[Common misconceptions to prevent]

## Project Structure

```
project/
  src/           # Source code
  tests/         # Test suite
  docs/          # Documentation
  config/        # Configuration
```

## Key Commands

```bash
pip install -e .              # Install
pytest tests/                 # Test
python -m mypy src/           # Type check
```

## Design Principles

### 1. [Principle Name]
[Brief explanation]

### 2. [Principle Name]
[Brief explanation]

## Terminology

| Use | Not | Why |
|-----|-----|-----|
| `term_a` | `term_b` | Consistency |

## References

| Doc | Purpose |
|-----|---------|
| `docs/architecture/` | How things work |
| `docs/GLOSSARY.md` | Full terminology |
```

### 2. Add directory-specific context (optional)

```markdown
# src/CLAUDE.md

## This Directory

Source code for [component].

## Key Files

| File | Purpose |
|------|---------|
| `main.py` | Entry point |
| `utils.py` | Shared utilities |

## Conventions

- All functions must have type hints
- Use `raise RuntimeError()` not `assert` for runtime checks
```

### 3. Keep it lean

The root CLAUDE.md is **always in context**. Every token counts:
- Reference other docs, don't duplicate
- Use tables for dense information
- Omit obvious things

## Usage

### For AI assistants

The file is automatically loaded. No action needed.

### For humans

Review and update when:
- Adding new conventions
- Changing architecture
- Onboarding reveals missing context

### Maintenance

```bash
# Check if CLAUDE.md references exist
grep -r "See \`" CLAUDE.md | while read line; do
  # Verify referenced files exist
done
```

## Content Guidelines

### DO Include

| Content | Example |
|---------|---------|
| Build/test commands | `pytest tests/ -v` |
| Design principles | "Fail loud, no silent fallbacks" |
| Terminology | "Use 'scrip' not 'credits'" |
| File purposes | "config.yaml has runtime values" |
| Anti-patterns | "Never use `except: pass`" |

### DON'T Include

| Content | Why |
|---------|-----|
| Implementation details | Changes frequently, goes stale |
| Full API docs | Too verbose, use references |
| Tutorial content | Not context, it's documentation |
| Aspirational features | Confuses current vs future |

### Size Guidelines

| Section | Target Size |
|---------|-------------|
| Root CLAUDE.md | 200-400 lines |
| Directory CLAUDE.md | 50-100 lines |
| Any single section | <50 lines |

## Customization

### For multi-AI coordination

Add coordination sections:

```markdown
## Active Work

| Instance | Task | Claimed |
|----------|------|---------|
| - | - | - |

## Coordination Protocol

1. Claim before starting
2. Release when done
3. Check claims before starting
```

### For monorepos

```
monorepo/
  CLAUDE.md           # Repo-wide context
  packages/
    api/CLAUDE.md     # API-specific
    web/CLAUDE.md     # Web-specific
```

### For different AI tools

| Tool | File Name | Notes |
|------|-----------|-------|
| Claude Code | `CLAUDE.md` | Auto-loaded |
| Cursor | `.cursorrules` | Different format |
| GitHub Copilot | No equivalent | Use comments |

## Limitations

- **Token cost** - Large files consume context window
- **Staleness** - Must be maintained manually
- **Tool-specific** - Different AI tools use different files
- **Not enforced** - AI may still ignore instructions

## Anti-Patterns

| Anti-Pattern | Problem |
|--------------|---------|
| Duplicating docs | Goes stale, wastes tokens |
| Too verbose | Crowds out actual work context |
| Aspirational content | Confuses AI about current state |
| No structure | Hard to scan, find information |

## Examples

### Minimal (small project)

```markdown
# MyApp - Claude Context

Python CLI tool for X.

## Commands
```bash
pip install -e . && pytest
```

## Principles
- Type hints required
- No silent failures
```

### Full (large project)

See this project's [CLAUDE.md](../../CLAUDE.md) for a complete example.

## See Also

- [Claim system pattern](18_claim-system.md) - Coordination tables in CLAUDE.md
- [Plan workflow pattern](15_plan-workflow.md) - Linking CLAUDE.md to plans
- [Handoff protocol pattern](archive/handoff-protocol.md) - Session continuity (archived)

---


## 03. Testing Strategy

*Source: `docs/meta/03_testing-strategy.md`*


## Philosophy

**Thin slices over big bang.** Every feature must prove it works end-to-end before declaring success. Unit tests passing with integration failing is a false positive.

**TDD as default.** Tests defined before implementation starts. Escape hatches exist for exploratory work.

**Real over mocked.** Prefer real dependencies. Mock only external APIs or when explicitly justified.

## The Thin Slice Principle

### Problem

Without mandatory E2E verification:
- All unit tests pass
- All integration tests pass
- Real system doesn't work
- Issues accumulate until a painful "big bang" integration

### Solution

Every feature (plan) must:
1. Define E2E acceptance criteria
2. Have at least one E2E test that exercises the feature
3. Pass E2E before marking Complete

```
Feature -> E2E Test -> Verified
         (not)
Feature -> Unit Tests Only -> "Complete" -> Broken in production
```

## Test Organization

### Recommended Structure

```
tests/
├── conftest.py              # Global fixtures
├── unit/                    # Single-component tests
│   └── test_ledger.py       # Can be marked with @pytest.mark.plans([1, 11])
├── integration/             # Multi-component tests
│   └── test_escrow.py       # Can be marked with @pytest.mark.plans([6])
├── e2e/                     # Full system tests
│   ├── test_smoke.py        # Generic smoke (mocked LLM)
│   └── test_real_e2e.py     # Real LLM ($$$)
└── plans/                   # Feature-specific E2E tests (NEW)
    ├── conftest.py          # Plan-specific fixtures
    ├── plan_01/
    │   └── test_rate_limiting_e2e.py
    ├── plan_06/
    │   └── test_unified_ontology_e2e.py
    └── ...
```

### Why Hybrid Structure?

| Approach | Pros | Cons |
|----------|------|------|
| Type-first (`unit/`, `integration/`) | Shared fixtures, pytest conventions | Hard to find tests for a plan |
| Plan-first (`plan_01/`, `plan_02/`) | Clear feature mapping | Duplication, deep nesting |
| **Hybrid** (both) | Best of both | Slightly more complex |

The hybrid approach:
- Keeps shared unit/integration tests in their traditional locations
- Adds `tests/plans/` for feature-specific E2E tests
- Uses pytest markers for queryability

### Pytest Markers

Register custom markers in `conftest.py`:

```python
# tests/conftest.py
import pytest

def pytest_configure(config):
    config.addinivalue_line(
        "markers", "plans(nums): mark test as belonging to plan number(s)"
    )
    config.addinivalue_line(
        "markers", "feature_type: mark test as 'feature' or 'enabler'"
    )
```

Use in tests:

```python
# tests/integration/test_escrow.py
import pytest

@pytest.mark.plans([6, 22])
class TestEscrowIntegration:
    """Tests for escrow system (Plans #6, #22)."""
    pass
```

Query with:
```bash
# Run all tests for plan 6
pytest -m "plans and 6" tests/

# Or use the check script
python scripts/check_plan_tests.py --plan 6
```

## TDD Policy

### Default: Tests Before Implementation

1. **Define tests** in plan's `## Required Tests` section
2. **Create test stubs** (they will fail)
3. **Implement** until tests pass
4. **Add E2E test** in `tests/plans/plan_NN/`
5. **Verify with script** before marking complete

### Escape Hatch 1: Exploratory Work

For plans that require exploration before test definition:

1. Start implementation without tests
2. **Before completion**, define and implement tests
3. Document why TDD was skipped in the plan

```markdown
## Notes

TDD skipped: Required exploration to understand the API surface.
Tests added post-implementation: test_foo.py, test_bar.py
```

### Escape Hatch 2: Enabler Plans

Enabler plans (tooling, process, documentation) may not have feature E2E tests:

```bash
# Use --skip-e2e for enabler plans
python scripts/complete_plan.py --plan 32 --skip-e2e
```

Mark in plan:
```markdown
**Type:** Enabler (no feature E2E required)
```

## Plan Types

| Type | Definition | E2E Required? | Example |
|------|------------|---------------|---------|
| **Feature** | Delivers user-visible capability | Yes | Rate limiting, Escrow |
| **Enabler** | Improves dev process | No (validation script instead) | Dev tooling, ADR governance |
| **Refactor** | Changes internals, not behavior | Existing E2E must pass | Terminology cleanup |

## Enforcement Mechanisms

### 1. CI Gates Plan Tests

```yaml
# .github/workflows/ci.yml
plan-tests:
  runs-on: ubuntu-latest
  # NO continue-on-error - this is strict
  steps:
    - run: python scripts/check_plan_tests.py --all
```

### 2. Completion Script Requires Tests

```bash
# This runs E2E tests before allowing completion
python scripts/complete_plan.py --plan N
```

The script:
1. Runs unit tests
2. Runs E2E smoke tests
3. Checks doc-coupling
4. Records evidence in plan file
5. Only then updates status to Complete

### 3. Plan Test Definition Validation

The `check_plan_tests.py` script validates:
- Plans with status "In Progress" or "Complete" have tests defined
- Defined tests exist in the test files
- Defined tests pass

### 4. Pre-Merge Checklist

Before merging a plan PR:

```bash
# All must pass
pytest tests/ -v
python scripts/check_plan_tests.py --plan N
python scripts/complete_plan.py --plan N --dry-run
```

## Writing Good E2E Tests

### Feature E2E Test Template

```python
# tests/plans/plan_NN/test_feature_e2e.py
"""E2E test for Plan #NN: Feature Name.

This test verifies that [feature] works end-to-end with [real/mocked] LLM.
"""

import pytest
from src.simulation.runner import SimulationRunner

class TestFeatureE2E:
    """End-to-end tests for [feature]."""

    def test_feature_basic_flow(self, e2e_config):
        """Verify [feature] works in a real simulation."""
        # Arrange
        runner = SimulationRunner(e2e_config)

        # Act
        world = runner.run_sync()

        # Assert - feature-specific assertions
        assert [feature-specific condition]

    @pytest.mark.external
    def test_feature_with_real_llm(self, real_e2e_config):
        """Verify [feature] with real LLM (costs $$$)."""
        # Only runs with --run-external
        ...
```

### What Makes a Good E2E Test

| Good | Bad |
|------|-----|
| Tests user-visible behavior | Tests internal implementation |
| Minimal mocking | Mocks everything |
| Specific assertions | "Doesn't crash" only |
| Documents the feature | Cryptic test names |
| Fast (< 30s for mocked) | Slow (minutes) |

## Mocking Policy

See [mocking-policy.md](./mocking-policy.md) for details.

**Summary:**
- No mocks by default
- Mock external APIs (LLM, network) when needed for speed/cost
- Require `# mock-ok: <reason>` comment for justified mocks
- CI fails on suspicious mock patterns without justification

## Metrics

Track testing health with:

```bash
# Plan test coverage
python scripts/check_plan_tests.py --list

# Mock usage
python scripts/check_mock_usage.py

# Overall coverage (if using coverage.py)
pytest --cov=src tests/
```

## Migration from Big Bang

If your codebase has accumulated untested "complete" plans:

1. **Audit**: Run `python scripts/plan_progress.py --summary`
2. **Identify gaps**: Plans marked Complete with 0% test progress
3. **Prioritize**: Focus on high-priority plans first
4. **Add tests retroactively**: Create `tests/plans/plan_NN/` for each
5. **Update verification**: Run `complete_plan.py` to record evidence

## Origin

Adopted after discovering multiple "Complete" plans had never been E2E tested. The cost of late integration (debugging across multiple accumulated changes) exceeded the overhead of per-feature E2E verification.

---


## 04. Mocking Policy

*Source: `docs/meta/04_mocking-policy.md`*


## Philosophy

**Real tests, not mock tests.** Mocks can hide real failures. Prefer real dependencies and accept time/cost tradeoffs.

## The Hierarchy

1. **Prefer real** - Use actual dependencies whenever possible
2. **Accept cost** - Real LLM calls cost money; that's acceptable for realistic tests
3. **Mock external only** - When mocking, mock external boundaries (APIs, network)
4. **Never mock internal** - Don't mock your own code; if you need to, the design is wrong
5. **Justify exceptions** - Every mock needs explicit justification

## When Mocking is Acceptable

| Scenario | Mock OK? | Example |
|----------|----------|---------|
| External API in unit test | Yes | Mock HTTP responses |
| LLM in smoke tests | Yes | Speed/cost for CI |
| Time-dependent tests | Yes | Mock `time.time()` |
| Network errors | Yes | Simulate timeout |
| Your own classes | **No** | Never mock `Ledger`, `Agent` |
| Database in unit test | Sometimes | Prefer in-memory DB |

## Enforcement

### The `# mock-ok:` Comment

Any mock of internal code requires justification:

```python
# mock-ok: Testing error handling when LLM unavailable
@patch("src.agents.agent.Agent._call_llm")
def test_handles_llm_failure(self, mock_llm):
    mock_llm.side_effect = ConnectionError()
    ...
```

Without this comment, CI fails:

```bash
python scripts/check_mock_usage.py --strict
# FAILED: Suspicious mock patterns detected
```

### Suspicious Patterns

The script flags these patterns:

```python
# SUSPICIOUS - mocking your own code
@patch("src.world.ledger.Ledger.transfer")  # Why not use real Ledger?

# SUSPICIOUS - MagicMock as internal return
mock_agent.propose_action.return_value = MagicMock()  # Use real ActionIntent

# OK - mocking external API
@patch("requests.get")  # External, fine to mock

# OK - mocking time
@patch("time.sleep")  # Avoids slow tests
```

### CI Integration

```yaml
mock-usage:
  runs-on: ubuntu-latest
  steps:
    - run: python scripts/check_mock_usage.py --strict
```

## Best Practices

### 1. Use Fixtures Over Mocks

```python
# BAD - mock the database
@patch("src.world.artifacts.ArtifactStore.save")
def test_save(self, mock_save):
    ...

# GOOD - use a real in-memory store
def test_save(self, temp_artifact_store):
    # temp_artifact_store is a real ArtifactStore with temp directory
    ...
```

### 2. Test Boundaries, Not Internals

```python
# BAD - testing implementation
@patch("src.agents.agent.Agent._format_prompt")
def test_prompt_formatting(self, mock_format):
    ...

# GOOD - testing behavior
def test_agent_produces_valid_action(self, real_agent):
    action = real_agent.propose_action(world_state)
    assert action.type in ["noop", "read", "write", "invoke"]
```

### 3. Accept Real LLM Costs

```python
# For realistic tests, use real LLM
@pytest.mark.external
def test_agent_with_real_llm(self, real_config):
    """Costs ~$0.01 per run but catches real issues."""
    runner = SimulationRunner(real_config)
    world = runner.run_sync()
    assert world.tick >= 1
```

### 4. Isolate Mocked Tests

Keep mocked tests separate from real tests:

```
tests/
├── e2e/
│   ├── test_smoke.py      # Mocked LLM (CI)
│   └── test_real_e2e.py   # Real LLM (pre-release)
```

## File-Level Justification

For files that legitimately need many mocks (e.g., testing error paths):

```python
# tests/unit/test_error_handling.py
"""Error handling tests.

# mock-ok: These tests verify error handling when external services fail.
# All mocks are for simulating external failures, not avoiding real code.
"""
```

This blanket justification covers all mocks in the first 20 lines.

## Escape Hatches

### Skip Mock Check for Specific File

If a file has unusual needs:

```python
# tests/special/test_weird_case.py
# mock-ok: File-level justification for unusual test pattern.
# Reason: [explain why this file needs to mock internal code]
```

### Run Without Strict Mode

For local development:

```bash
python scripts/check_mock_usage.py  # Report only, don't fail
```

## The Check Script

```bash
# Report all mock usage
python scripts/check_mock_usage.py

# Fail on suspicious patterns (CI mode)
python scripts/check_mock_usage.py --strict

# Just list files with mocks
python scripts/check_mock_usage.py --list
```

## Origin

Adopted after discovering tests that passed but production failed. The tests mocked internal components, hiding real integration issues. The policy ensures tests exercise real code paths.

---


## 05. Mock Enforcement

*Source: `docs/meta/05_mock-enforcement.md`*


## Problem

AI coding assistants (and humans) sometimes mock internal code extensively to make tests pass, then declare success. But the real code is broken - mocks hide the failures. Result: green CI, broken production.

## Solution

1. Detect suspicious mock patterns (mocking internal code instead of external APIs)
2. Require explicit justification for each mock via `# mock-ok: reason` comment
3. Fail CI if unjustified mocks detected
4. Ensure real API keys available in CI for integration tests

## Files

| File | Purpose |
|------|---------|
| `scripts/check_mock_usage.py` | Detect suspicious mock patterns |
| `.github/workflows/ci.yml` | CI job that runs `--strict` mode |
| `CLAUDE.md` | Policy documentation for AI assistants |

## Setup

### 1. Create the detection script

```python
#!/usr/bin/env python3
"""Detect and report mock usage in tests."""

import re
import sys
from pathlib import Path

# Patterns that are suspicious - mocking internal code
SUSPICIOUS_PATTERNS = [
    r"@patch\(['\"]src\.",           # Mocking your own src/ code
    r"@patch.*YourCoreClass",        # Mocking core classes
    r"return_value\s*=\s*MagicMock", # MagicMock for internal code
]

# Patterns that are OK - external dependencies
OK_PATTERNS = [
    r"@patch.*time\.",
    r"@patch.*datetime",
    r"@patch.*requests\.",
    r"@patch.*httpx\.",
]

def find_mock_usage(test_dir: Path) -> dict[str, list[tuple[int, str]]]:
    """Find all mock usage in test files."""
    results = {}
    for test_file in test_dir.glob("test_*.py"):
        content = test_file.read_text()
        lines = content.split("\n")
        mock_lines = []
        for i, line in enumerate(lines, 1):
            if "@patch" in line or "MagicMock" in line:
                if "import" not in line:
                    mock_lines.append((i, line.strip()))
        if mock_lines:
            results[str(test_file)] = mock_lines
    return results

def check_suspicious(mock_usage: dict) -> list[str]:
    """Check for suspicious patterns, respecting # mock-ok: comments."""
    warnings = []
    for file_path, lines in mock_usage.items():
        content = Path(file_path).read_text()
        file_lines = content.split("\n")

        # Check for file-level justification in first 20 lines
        file_justified = any("# mock-ok:" in line for line in file_lines[:20])

        for line_num, line in lines:
            for pattern in SUSPICIOUS_PATTERNS:
                if re.search(pattern, line):
                    if any(re.search(ok, line) for ok in OK_PATTERNS):
                        continue
                    if file_justified:
                        continue
                    if "# mock-ok:" in line:
                        continue
                    # Check previous line for justification
                    if line_num >= 2 and "# mock-ok:" in file_lines[line_num - 2]:
                        continue
                    warnings.append(f"{file_path}:{line_num}: {line}")
    return warnings

def main() -> int:
    test_dir = Path("tests")
    mock_usage = find_mock_usage(test_dir)
    warnings = check_suspicious(mock_usage)

    if warnings and "--strict" in sys.argv:
        print("SUSPICIOUS MOCK PATTERNS:")
        for w in warnings:
            print(f"  {w}")
        print("\nAdd '# mock-ok: <reason>' to justify, or use real implementations.")
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 2. Add CI job

```yaml
# In .github/workflows/ci.yml
mock-usage:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - name: Check for suspicious mock patterns
      run: python scripts/check_mock_usage.py --strict
```

### 3. Add API keys to CI

```yaml
# In your test job
- name: Run pytest
  env:
    YOUR_API_KEY: ${{ secrets.YOUR_API_KEY }}
  run: pytest tests/ -v
```

### 4. Document the policy

Add to your `CLAUDE.md` or contributing guide:

```markdown
### Mock Policy

CI detects suspicious mock patterns. Mocking internal code hides real failures.

**Allowed mocks:** External APIs (requests, httpx), time/datetime

**Not allowed without justification:** `@patch("src.anything")`

**To justify:** Add `# mock-ok: <reason>` comment
```

## Usage

```bash
# Check for suspicious mocks (report only)
python scripts/check_mock_usage.py

# Fail on suspicious mocks (CI mode)
python scripts/check_mock_usage.py --strict

# List files with any mock usage
python scripts/check_mock_usage.py --list
```

### Justifying a Mock

```python
# Line-level justification
# mock-ok: Testing error handling when API unavailable
@patch("src.external.api_client")
def test_handles_api_failure():
    ...

# File-level justification (in docstring, first 20 lines)
"""Tests for runner orchestration.

# mock-ok: Mocking load_agents avoids LLM API calls - tests focus on orchestration
"""
```

## Customization

### Change suspicious patterns

Edit `SUSPICIOUS_PATTERNS` in the script:

```python
SUSPICIOUS_PATTERNS = [
    r"@patch\(['\"]mypackage\.",  # Your package name
    r"@patch.*Database",          # Your core classes
    r"@patch.*Service",
]
```

### Change allowed patterns

Edit `OK_PATTERNS`:

```python
OK_PATTERNS = [
    r"@patch.*time\.",
    r"@patch.*redis\.",     # If Redis is external
    r"@patch.*boto3\.",     # AWS SDK
]
```

### Adjust file-level justification scope

Change the line limit for file-level `# mock-ok:` detection:

```python
file_justified = any("# mock-ok:" in line for line in file_lines[:20])  # First 20 lines
```

## Limitations

- **Pattern-based detection** - May have false positives/negatives. Tune patterns for your codebase.
- **Justification is honor system** - Anyone can add `# mock-ok:` with a bad reason. Code review still needed.
- **Doesn't verify mock correctness** - A justified mock can still be wrong. This only ensures visibility.

## See Also

- [pytest-mock documentation](https://pytest-mock.readthedocs.io/)
- [unittest.mock best practices](https://docs.python.org/3/library/unittest.mock.html)

---


## 06. Git Hooks

*Source: `docs/meta/06_git-hooks.md`*


## Problem

CI catches issues, but feedback is slow. By the time CI fails:
- Developer has context-switched
- Fixes require another commit cycle
- AI assistants may have moved on to other tasks

## Solution

1. Track hooks in repo (not `.git/hooks/` which is ignored)
2. Use `core.hooksPath` to point git at tracked hooks
3. Run fast checks pre-commit (doc-coupling, type checking)
4. Enforce commit message format (plan references)
5. Provide setup script for new clones

## Files

| File | Purpose |
|------|---------|
| `hooks/pre-commit` | Runs before commit is created |
| `hooks/commit-msg` | Validates commit message format |
| `scripts/setup_hooks.sh` | One-time setup after clone |

## Setup

### 1. Create hooks directory

```bash
mkdir hooks
```

### 2. Create pre-commit hook

```bash
#!/bin/bash
# hooks/pre-commit
set -e

echo "Running pre-commit checks..."
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

# Get staged files
STAGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)

# 1. Doc-coupling check
echo "Checking doc-code coupling..."
if ! python scripts/check_doc_coupling.py --strict 2>/dev/null; then
    echo "ERROR: Doc-coupling violation!"
    echo "Run 'python scripts/check_doc_coupling.py --suggest' for help"
    exit 1
fi

# 2. Type checking on changed src/ files
STAGED_SRC=$(echo "$STAGED_PY" | grep '^src/' || true)
if [ -n "$STAGED_SRC" ]; then
    echo "Running mypy..."
    if ! python -m mypy --ignore-missing-imports $STAGED_SRC 2>/dev/null; then
        echo "ERROR: mypy failed!"
        exit 1
    fi
fi

# 3. Lint check (optional)
# if [ -n "$STAGED_PY" ]; then
#     echo "Running ruff..."
#     ruff check $STAGED_PY
# fi

echo "Pre-commit checks passed!"
```

### 3. Create commit-msg hook

```bash
#!/bin/bash
# hooks/commit-msg
COMMIT_MSG_FILE="$1"
FIRST_LINE=$(head -n1 "$COMMIT_MSG_FILE")

# Allow merge commits
if [[ "$FIRST_LINE" =~ ^Merge ]]; then
    exit 0
fi

# Allow fixup/squash commits
if [[ "$FIRST_LINE" =~ ^(fixup!|squash!) ]]; then
    exit 0
fi

# Check for plan reference
if [[ "$FIRST_LINE" =~ ^\[Plan\ \#[0-9]+\] ]]; then
    exit 0
fi

if [[ "$FIRST_LINE" =~ ^\[Unplanned\] ]]; then
    echo "WARNING: Unplanned work. Create a plan before merging."
    exit 0
fi

echo "ERROR: Commit message must include [Plan #N] or [Unplanned]"
echo "  e.g. [Plan #3] Implement feature X"
exit 1
```

### 4. Make hooks executable

```bash
chmod +x hooks/*
```

### 5. Create setup script

```bash
#!/bin/bash
# scripts/setup_hooks.sh
set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$REPO_ROOT/hooks"

if [ ! -d "$HOOKS_DIR" ]; then
    echo "ERROR: hooks/ directory not found"
    exit 1
fi

chmod +x "$HOOKS_DIR"/*
git config core.hooksPath hooks

echo "Git hooks configured!"
echo "  - pre-commit: Runs checks before commit"
echo "  - commit-msg: Validates commit message format"
```

### 6. Document in README

```markdown
## Setup

After cloning:
\`\`\`bash
bash scripts/setup_hooks.sh
\`\`\`
```

## Usage

### Normal workflow

```bash
# Hooks run automatically
git add .
git commit -m "[Plan #3] Implement feature X"
# pre-commit runs → commit-msg validates → commit created
```

### Bypass (emergency only)

```bash
git commit --no-verify -m "Emergency fix"
```

### Re-run setup after clone

```bash
bash scripts/setup_hooks.sh
```

## Customization

### Add more pre-commit checks

```bash
# In hooks/pre-commit

# Run tests on changed files
STAGED_TESTS=$(echo "$STAGED_PY" | grep '^tests/' || true)
if [ -n "$STAGED_TESTS" ]; then
    echo "Running affected tests..."
    pytest $STAGED_TESTS -x
fi

# Check for debug statements
if git diff --cached | grep -E '(pdb|breakpoint|console\.log)'; then
    echo "ERROR: Debug statements found!"
    exit 1
fi

# Check for secrets
if git diff --cached | grep -iE '(api_key|password|secret)\s*=\s*["\047]'; then
    echo "ERROR: Possible secret in commit!"
    exit 1
fi
```

### Change commit message format

```bash
# In hooks/commit-msg

# Require conventional commits format
if [[ "$FIRST_LINE" =~ ^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?:\ .+ ]]; then
    exit 0
fi

echo "ERROR: Use conventional commits format"
echo "  e.g. feat(auth): add login button"
exit 1
```

### Add prepare-commit-msg hook

```bash
#!/bin/bash
# hooks/prepare-commit-msg
# Auto-add branch name to commit message

COMMIT_MSG_FILE="$1"
BRANCH=$(git branch --show-current)

# Extract plan number from branch name
if [[ "$BRANCH" =~ ^plan-([0-9]+) ]]; then
    PLAN_NUM="${BASH_REMATCH[1]}"
    # Prepend plan reference if not present
    if ! grep -q "^\[Plan #" "$COMMIT_MSG_FILE"; then
        sed -i "1s/^/[Plan #$PLAN_NUM] /" "$COMMIT_MSG_FILE"
    fi
fi
```

## Limitations

- **Not enforced on force-push** - Someone can bypass with `--no-verify`.
- **New clones need setup** - Must run `setup_hooks.sh` after every clone.
- **Slow checks hurt velocity** - Keep pre-commit fast (<5 seconds).
- **Platform differences** - Bash hooks may not work on Windows without WSL.

## Best Practices

1. **Keep hooks fast** - Run expensive checks in CI, not hooks
2. **Provide bypass** - `--no-verify` for emergencies
3. **Document setup** - Make it obvious in README
4. **Fail with helpful messages** - Tell users how to fix issues
5. **Test hooks** - Run them manually before committing

## See Also

- [Doc-code coupling pattern](10_doc-code-coupling.md) - Often run as pre-commit check
- [Plan workflow pattern](15_plan-workflow.md) - Commit message format ties to plans

---


## 07. ADR

*Source: `docs/meta/07_adr.md`*


## Problem

Architectural decisions get lost. Months later:
- No one remembers WHY something was built a certain way
- New developers (or AI assistants) repeat old mistakes
- Refactoring breaks things because constraints weren't documented
- Debates recur because the original reasoning wasn't recorded

## Solution

1. Record each significant architectural decision as an ADR
2. ADRs are **immutable** - once accepted, never edited
3. If a decision changes, create a new ADR that supersedes the old one
4. Link ADRs to source files via governance headers
5. CI enforces governance sync

## Files

| File | Purpose |
|------|---------|
| `docs/adr/NNNN-title.md` | Individual decision records |
| `docs/adr/README.md` | Index of all ADRs |
| `docs/adr/TEMPLATE.md` | Template for new ADRs |
| `scripts/governance.yaml` | File-to-ADR mappings |
| `scripts/sync_governance.py` | Sync governance headers to source |

## Setup

### 1. Create ADR directory

```bash
mkdir -p docs/adr
```

### 2. Create README

```markdown
# Architecture Decision Records

| ADR | Title | Status |
|-----|-------|--------|
| [0001](0001-example.md) | Example decision | Accepted |

## Statuses

| Status | Meaning |
|--------|---------|
| Proposed | Under discussion |
| Accepted | Decision made, in effect |
| Deprecated | No longer applies |
| Superseded | Replaced by another ADR |
```

### 3. Create template

```markdown
# ADR-NNNN: Title

**Status:** Proposed
**Date:** YYYY-MM-DD

## Context

What is the issue motivating this decision?

## Decision

What is the change we're making?

## Consequences

### Positive
- Benefit 1

### Negative
- Trade-off 1

## Related
- Gap #N (if applicable)
- Other ADRs
```

### 4. Create governance config (optional)

```yaml
# scripts/governance.yaml
governance:
  - files:
      - "src/core/engine.py"
      - "src/core/runner.py"
    adrs:
      - "0001-example"
    description: "Core engine architecture"
```

### 5. Create governance sync script (optional)

```python
#!/usr/bin/env python3
"""Sync ADR governance headers to source files."""

import yaml
from pathlib import Path

def sync_governance(config_path: str, apply: bool = False):
    config = yaml.safe_load(Path(config_path).read_text())

    for mapping in config.get("governance", []):
        header = build_header(mapping["adrs"])
        for file_path in mapping["files"]:
            if apply:
                update_file(file_path, header)
            else:
                check_file(file_path, header)

def build_header(adrs: list[str]) -> str:
    lines = ["# --- GOVERNANCE START (do not edit) ---"]
    for adr in adrs:
        lines.append(f"# {adr}")
    lines.append("# --- GOVERNANCE END ---")
    return "\n".join(lines)
```

### 6. Add CI check (optional)

```yaml
governance-sync:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - run: python scripts/sync_governance.py --check
```

## Usage

### Creating a new ADR

```bash
# 1. Copy template
cp docs/adr/TEMPLATE.md docs/adr/0004-my-decision.md

# 2. Edit the file
# - Fill in Context, Decision, Consequences
# - Set Status: Proposed

# 3. Submit PR for discussion

# 4. After approval, change Status to Accepted
```

### Superseding an ADR

```markdown
# ADR-0005: New approach to X

**Status:** Accepted
**Date:** 2024-01-15
**Supersedes:** ADR-0002

## Context

ADR-0002 decided X, but we've learned Y...
```

Then update ADR-0002:
```markdown
**Status:** Superseded by ADR-0005
```

### Checking governance

```bash
# Check if headers are in sync
python scripts/sync_governance.py --check

# Apply headers to source files
python scripts/sync_governance.py --apply
```

## ADR Content Guidelines

### What to Record

| Decision Type | Example |
|---------------|---------|
| Technology choices | "Use PostgreSQL over MongoDB" |
| Architectural patterns | "Event sourcing for audit log" |
| API design | "REST over GraphQL" |
| Security decisions | "JWT tokens with 1h expiry" |
| Trade-offs | "Favor consistency over availability" |

### What NOT to Record

| Not an ADR | Why |
|------------|-----|
| Bug fixes | Not architectural |
| Feature specs | Use product docs |
| How-to guides | Use regular docs |
| Temporary decisions | Not significant enough |

### Good ADR Characteristics

- **One decision per ADR** - Don't bundle multiple decisions
- **Context explains WHY** - Future readers need the reasoning
- **Consequences are honest** - Include trade-offs and risks
- **Immutable** - Never edit accepted ADRs, supersede instead

## Customization

### Numbering schemes

```bash
# Sequential (default)
0001, 0002, 0003...

# Date-based
2024-01-001, 2024-01-002...

# Category-based
SEC-001 (security), API-001 (API design)...
```

### Governance header style

```python
# Python style
# --- GOVERNANCE START ---
# ADR-0001
# --- GOVERNANCE END ---

// JavaScript style
// --- GOVERNANCE START ---
// ADR-0001
// --- GOVERNANCE END ---

<!-- Markdown style -->
<!-- GOVERNANCE: ADR-0001, ADR-0002 -->
```

### Linking to plans/gaps

```markdown
## Related

- Implements Gap #3 (Docker isolation)
- See also: ADR-0001 (foundational decision)
```

## Limitations

- **Overhead** - Writing ADRs takes time
- **Discovery** - People must know to look for ADRs
- **Staleness** - Index can drift if not maintained
- **Scope creep** - Risk of recording non-architectural decisions

## Best Practices

1. **Write ADRs during design, not after** - Capture reasoning while fresh
2. **Keep Context brief but complete** - Future readers need enough to understand
3. **Be honest about trade-offs** - Negative consequences are valuable
4. **Link bidirectionally** - ADRs reference code, code references ADRs
5. **Review ADRs in PRs** - Architecture decisions deserve review

## See Also

- [Doc-code coupling pattern](10_doc-code-coupling.md) - Related enforcement mechanism
- [Plan workflow pattern](15_plan-workflow.md) - ADRs can link to implementation plans
- [Original ADR proposal](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) by Michael Nygard

---


## 08. ADR Governance

*Source: `docs/meta/08_adr-governance.md`*


## Problem

AI coding assistants (Claude Code, etc.) lose track of architectural decisions over long sessions. They start ignoring ADRs, drifting from established patterns, and making inconsistent choices. By the time you notice, significant rework may be needed.

The core issue: decisions documented in ADRs are invisible when reading code. Claude must proactively check `docs/adr/` to know what decisions apply - and it often doesn't.

## Solution

Make decisions visible at the point of relevance by embedding governance headers directly in source files:

```python
# --- GOVERNANCE START (do not edit) ---
# ADR-0001: Everything is an artifact
# ADR-0003: Contracts can do anything
#
# Permission checks are the hot path - keep them fast.
# Contracts return decisions; kernel applies state changes.
# --- GOVERNANCE END ---
```

When Claude reads a governed file, it immediately sees which ADRs apply and any context about how they apply to this specific file.

**Key properties:**
- Single source of truth: `governance.yaml` defines file → ADR mappings
- Headers are generated, not manually maintained
- CI enforces sync between config and headers
- Dry-run by default - no accidental modifications

## Files

| File | Purpose |
|------|---------|
| `docs/adr/` | Architecture Decision Records |
| `docs/adr/TEMPLATE.md` | Template for new ADRs |
| `scripts/governance.yaml` | File → ADR mappings (single source of truth) |
| `scripts/sync_governance.py` | Generates headers from config |
| `tests/test_sync_governance.py` | Tests for sync script |

## Setup

1. **Create ADR directory:**
```bash
mkdir -p docs/adr
```

2. **Create template and README:**
```bash
# See docs/adr/TEMPLATE.md and docs/adr/README.md in this project
```

3. **Create governance.yaml:**
```yaml
# scripts/governance.yaml
files:
  src/core/module.py:
    adrs: [1, 3]
    context: |
      Why these ADRs apply to this file.

adrs:
  1:
    title: "Decision title"
    file: "0001-decision-name.md"
```

4. **Copy sync script:**
```bash
# Copy scripts/sync_governance.py from this project
```

5. **Add CI check:**
```yaml
# .github/workflows/ci.yml
governance-sync:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - run: pip install pyyaml
    - run: python scripts/sync_governance.py --check
```

## Usage

**See what needs updating:**
```bash
python scripts/sync_governance.py
```

**Apply changes (requires clean git tree):**
```bash
python scripts/sync_governance.py --apply
```

**Override dirty tree check:**
```bash
python scripts/sync_governance.py --apply --force
```

**Create backups before modifying:**
```bash
python scripts/sync_governance.py --apply --backup
```

**CI check (exit 1 if out of sync):**
```bash
python scripts/sync_governance.py --check
```

**Adding a new ADR:**
1. Copy `docs/adr/TEMPLATE.md` to `docs/adr/NNNN-title.md`
2. Fill in the template
3. Add to `scripts/governance.yaml` under `adrs:`
4. Add file mappings under `files:`
5. Run `--apply` to generate headers

## Customization

**Marker format:** Edit `GOVERNANCE_START` and `GOVERNANCE_END` constants in `sync_governance.py`.

**Header content:** Modify `generate_governance_block()` to change what appears in headers.

**Insertion location:** Modify `update_file_content()` to change where headers are inserted (currently after module docstring).

**File types:** Currently supports Python. Extend `validate_python_syntax()` for other languages or remove validation for non-code files.

## Limitations

- **Python-specific syntax validation:** The script validates Python syntax after modification. For other languages, you'd need to add appropriate validators or disable validation.

- **Doesn't prevent ignoring:** A determined (or confused) Claude can still ignore the headers. This pattern makes decisions visible, not enforced.

- **Manual ADR creation:** ADRs themselves must be written manually. This pattern only handles linking them to code.

- **No reverse lookup:** No easy way to ask "what files does ADR-0001 govern?" without reading the YAML. Could add a `--list-files` command.

- **Header location fixed:** Headers always appear after the module docstring (or at top if no docstring). Some codebases may want different placement.

## Safeguards

The sync script includes multiple safeguards to prevent breaking your codebase:

1. **Dry-run by default** - Must explicitly use `--apply` to modify files
2. **Marker-only modification** - Only changes content between GOVERNANCE markers
3. **Syntax validation** - Validates Python syntax before replacing files
4. **Git dirty check** - Refuses to modify files if working tree is dirty (use `--force` to override)
5. **Atomic writes** - Writes to temp file, validates, then replaces original
6. **Backup option** - Creates `.bak` files before modifying

---


## 09. Documentation Graph

*Source: `docs/meta/09_documentation-graph.md`*


## Problem

Documentation relationships are scattered across multiple config files:
- `governance.yaml` maps ADRs → code
- `doc_coupling.yaml` maps code → docs

This makes it impossible to trace: ADR → target architecture → current architecture → gaps → plans → code. Adding new relationship types requires new config files.

## Solution

Unify all documentation relationships into a single `relationships.yaml` with a nodes/edges schema.

**See:** [ADR-0005: Unified Documentation Graph](../../adr/0005-unified-documentation-graph.md)

## Files

| File | Purpose |
|------|---------|
| `scripts/relationships.yaml` | Single source of truth for all doc relationships |
| `scripts/sync_governance.py` | Reads `governs` edges, embeds headers in code |
| `scripts/check_doc_coupling.py` | Reads `documented_by` edges with `coupling: strict` |
| `scripts/validate_plan.py` | Queries graph before implementation (the "gate") |

## Schema

```yaml
# scripts/relationships.yaml
version: 1

# Node namespaces - glob patterns for doc categories
nodes:
  adr: docs/adr/*.md
  target: docs/architecture/target/*.md
  current: docs/architecture/current/*.md
  plans: docs/plans/*.md
  gaps: docs/architecture/gaps/*.yaml
  source: src/**/*.py

# Edge types
edge_types:
  governs:      # ADR governs code/docs (embeds headers)
  implements:   # Plan implements toward target
  documented_by: # Code documented by architecture doc (CI enforcement)
  vision_for:   # Target doc that current implements toward
  details:      # Plan linked to detailed gap analysis

# Relationships
edges:
  - from: adr/0001-everything-is-artifact
    to: [target/01_README, source/src/world/artifacts.py]
    type: governs

  - from: source/src/world/ledger.py
    to: current/resources
    type: documented_by
    coupling: strict  # CI fails if not updated together
```

## Setup

1. **Create relationships.yaml** from existing configs:
```bash
# Merge governance.yaml + doc_coupling.yaml into relationships.yaml
python scripts/migrate_to_relationships.py  # (if migration script exists)
```

2. **Update scripts** to read new format (or use existing scripts until migrated)

3. **Deprecate old configs** once migration complete

## Usage

```bash
# Governance headers (same as before)
python scripts/sync_governance.py --check
python scripts/sync_governance.py --apply

# Doc coupling (same as before)
python scripts/check_doc_coupling.py --strict

# NEW: Plan validation gate
python scripts/validate_plan.py --plan 28
# Shows: ADRs that govern, docs to update, uncertainties to resolve
```

## Relationship to Other Patterns

| Pattern | Status | Relationship |
|---------|--------|--------------|
| [ADR Governance](08_adr-governance.md) | Subsumed | `governs` edges replace `governance.yaml` |
| [Doc-Code Coupling](10_doc-code-coupling.md) | Subsumed | `documented_by` edges replace `doc_coupling.yaml` |

Both patterns remain valid until migration is complete. After migration, they become implementation details of this unified pattern.

## Limitations

- **Migration required** - Existing scripts need updating to read new format
- **Single large file** - All relationships in one file (could split by namespace if too large)
- **Learning curve** - Contributors must understand edge types

## Complementary: Validation Gate

The graph enables a pre-implementation validation workflow:

```bash
$ python scripts/validate_plan.py --plan 28
Checking Plan #28 against relationship graph...
- ADRs that govern affected files: [0001, 0003]
- Target docs to check consistency: [target/05_contracts.md]
- Current docs that need updating: [current/artifacts_executor.md]
- DESIGN_CLARIFICATIONS <70% items: [#7 Event system]

⚠️  1 uncertainty found - discuss with user before implementing
```

The graph is the map; validation is the gate.

---


## 10. Doc-Code Coupling

*Source: `docs/meta/10_doc-code-coupling.md`*


## Problem

Documentation drifts from code. AI assistants change code but forget to update docs. Humans do the same. Over time, docs become misleading or useless.

## Solution

1. Define explicit mappings: "when file X changes, doc Y must be updated"
2. CI checks if coupled docs were modified together with their sources
3. Two enforcement levels: strict (CI fails) and soft (CI warns)
4. Escape hatch: update "Last verified" date if docs are already accurate

## Files

| File | Purpose |
|------|---------|
| `scripts/check_doc_coupling.py` | Enforcement logic |
| `scripts/doc_coupling.yaml` | Source-to-doc mappings |
| `.github/workflows/ci.yml` | CI job |

## Setup

### 1. Create the coupling config

```yaml
# scripts/doc_coupling.yaml
couplings:
  # STRICT - CI fails if violated
  - sources:
      - "src/core/engine.py"
      - "src/core/runner.py"
    docs:
      - "docs/architecture/engine.md"
    description: "Core engine documentation"

  - sources:
      - "src/api/*.py"
    docs:
      - "docs/api-reference.md"
    description: "API documentation"

  # SOFT - CI warns but doesn't fail
  - sources:
      - "src/**/*.py"
    docs:
      - "docs/CHANGELOG.md"
    description: "Consider updating changelog"
    soft: true
```

### 2. Create the check script

```python
#!/usr/bin/env python3
"""Check doc-code coupling."""

import subprocess
import sys
from pathlib import Path
import yaml
import fnmatch

def get_changed_files(base: str) -> set[str]:
    """Get files changed since base branch."""
    result = subprocess.run(
        ["git", "diff", "--name-only", base],
        capture_output=True, text=True
    )
    return set(result.stdout.strip().split("\n")) if result.stdout.strip() else set()

def matches_pattern(file: str, pattern: str) -> bool:
    """Check if file matches glob pattern."""
    return fnmatch.fnmatch(file, pattern)

def check_coupling(config_path: str, base: str, strict: bool) -> int:
    """Check coupling violations."""
    with open(config_path) as f:
        config = yaml.safe_load(f)

    changed = get_changed_files(base)
    violations = []
    warnings = []

    for coupling in config.get("couplings", []):
        sources = coupling["sources"]
        docs = coupling["docs"]
        is_soft = coupling.get("soft", False)
        desc = coupling.get("description", "")

        # Check if any source pattern matches changed files
        source_changed = any(
            matches_pattern(f, pattern)
            for f in changed
            for pattern in sources
        )

        if source_changed:
            # Check if required docs were also changed
            docs_changed = any(d in changed for d in docs)
            if not docs_changed:
                msg = f"{desc}: {docs[0]} not updated"
                if is_soft:
                    warnings.append(msg)
                else:
                    violations.append(msg)

    if warnings:
        print("WARNINGS (soft couplings):")
        for w in warnings:
            print(f"  {w}")

    if violations:
        print("VIOLATIONS (strict couplings):")
        for v in violations:
            print(f"  {v}")
        if strict:
            return 1

    return 0

if __name__ == "__main__":
    base = "origin/main"
    for i, arg in enumerate(sys.argv):
        if arg == "--base" and i + 1 < len(sys.argv):
            base = sys.argv[i + 1]
    strict = "--strict" in sys.argv
    sys.exit(check_coupling("scripts/doc_coupling.yaml", base, strict))
```

### 3. Add CI job

```yaml
# In .github/workflows/ci.yml
doc-coupling:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
      with:
        fetch-depth: 0  # Need full history for git diff
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - name: Install PyYAML
      run: pip install pyyaml
    - name: Check doc-code coupling
      run: python scripts/check_doc_coupling.py --base origin/main --strict
```

### 4. Add "Last verified" convention

Each doc should have a header:

```markdown
# Engine Architecture

Last verified: 2024-01-15

---

Content here...
```

The escape hatch: if code changed but docs are already accurate, update the date.

## Usage

```bash
# Check for violations (CI mode)
python scripts/check_doc_coupling.py --base origin/main --strict

# See what docs you should update
python scripts/check_doc_coupling.py --suggest

# Validate config file (check all paths exist)
python scripts/check_doc_coupling.py --validate-config

# Check against a different base
python scripts/check_doc_coupling.py --base HEAD~5
```

### Handling Violations

**Option 1: Update the doc** (preferred)
```bash
# Edit the coupled doc
vim docs/architecture/engine.md
# Update "Last verified" date
# Commit both source and doc together
```

**Option 2: Escape hatch** (if doc is already accurate)
```bash
# Just update the "Last verified" date in the doc
# This satisfies the coupling check
```

## Customization

### Coupling types

```yaml
# Strict (default) - CI fails
- sources: ["src/core/*.py"]
  docs: ["docs/core.md"]
  description: "Core module docs"

# Soft - CI warns only
- sources: ["src/**/*.py"]
  docs: ["CHANGELOG.md"]
  description: "Changelog reminder"
  soft: true
```

### Glob patterns

```yaml
sources:
  - "src/api/*.py"           # All .py in api/
  - "src/api/**/*.py"        # All .py in api/ recursively
  - "src/core/engine.py"     # Specific file
  - "config/*.yaml"          # All yaml in config/
```

### Multiple docs per source

```yaml
- sources:
    - "src/public_api.py"
  docs:
    - "docs/api-reference.md"
    - "docs/getting-started.md"
    - "README.md"
  description: "Public API affects multiple docs"
```

### Bidirectional coupling

For docs that should trigger source review:

```yaml
- sources:
    - "docs/api-reference.md"
  docs:
    - "src/public_api.py"
  description: "API doc changes should be reflected in code"
  soft: true  # Usually soft - doc changes don't always need code changes
```

## Limitations

- **Git-based** - Only works with git. Requires `fetch-depth: 0` in CI.
- **File-level granularity** - Can't couple specific functions to specific doc sections.
- **No content validation** - Doesn't check if the doc update is meaningful.
- **Escape hatch can be abused** - Someone can always just update the date without reading.

## See Also

- [Git hooks pattern](06_git-hooks.md) - Can run doc-coupling check pre-commit
- [Plan workflow pattern](15_plan-workflow.md) - Plans are a form of doc-code coupling

---


## 11. Terminology

*Source: `docs/meta/11_terminology.md`*


## Why Terminology Matters

Inconsistent terminology causes:
- Miscommunication between team members
- Documentation that contradicts itself
- Confusion about what's being tracked

This document defines the canonical terms for project organization.

## Core Hierarchy

```
Phase (optional grouping)
└── Feature (the deliverable)
    └── Plan (the implementation document)
        └── Task (atomic work item)
```

### Definitions

| Term | Definition | Identifier | Tests At Level |
|------|------------|------------|----------------|
| **Feature** | A user-visible or system capability that can be verified E2E | Plan number (1:1 with plan) | E2E required |
| **Plan** | Document describing how to implement a feature | `NN_name.md` | References tests |
| **Task** | Atomic work item within a plan | Checklist item | May have unit test |
| **Phase** | Optional grouping of related features | "Phase 1" | No tests (just grouping) |

### Key Insight: Feature = Plan

In this system, each plan implements exactly one feature. The plan number IS the feature ID.

```
Feature: "Rate Limiting"
    └── Plan: 01_rate_allocation.md
        └── Tasks:
            - Create TokenBucket class
            - Update config schema
            - Add tests
```

## Plan Types

Not all plans are features. Distinguish between:

| Type | Definition | E2E Required? | Examples |
|------|------------|---------------|----------|
| **Feature Plan** | Delivers testable capability | Yes | Rate limiting, Escrow, MCP servers |
| **Enabler Plan** | Improves dev process | No | Dev tooling, ADR governance |
| **Refactor Plan** | Changes internals, not behavior | Existing E2E must pass | Terminology cleanup |

Mark in plan header:
```markdown
**Type:** Feature  # or Enabler, Refactor
```

## Status Terms

| Status | Emoji | Meaning |
|--------|-------|---------|
| **Planned** | 📋 | Has implementation design, ready to start |
| **In Progress** | 🚧 | Actively being implemented |
| **Blocked** | ⏸️ | Waiting on dependency |
| **Needs Plan** | ❌ | Gap identified, needs design work |
| **Complete** | ✅ | Implemented, tested, documented |

## Resource Terms

See `docs/GLOSSARY.md` for canonical resource terminology:

| Use | Not | Why |
|-----|-----|-----|
| `scrip` | `credits` | Consistency with economics literature |
| `principal` | `account` | Principals include artifacts, not just agents |
| `tick` | `turn` | Game theory convention |
| `artifact` | `object/entity` | Everything is an artifact |

## Test Organization Terms

| Term | Definition |
|------|------------|
| **Unit test** | Tests single component in isolation |
| **Integration test** | Tests multiple components together |
| **E2E test** | Tests full system end-to-end |
| **Smoke test** | Basic E2E that verifies system runs |
| **Plan test** | Test(s) required for a specific plan |

## Enforcement

Terminology is enforced through:

1. **Code review** - Reviewers flag incorrect terms
2. **Glossary reference** - `docs/GLOSSARY.md` is authoritative
3. **Search and replace** - Periodic terminology audits
4. **CI (future)** - Could add terminology linting

## Usage Examples

### Correct

> "Plan #6 (Unified Ontology) is a feature plan that delivers artifact-backed agents."

> "Task: Create the TokenBucket class (part of Plan #1)"

> "Phase 1 includes Plans #1, #2, and #3"

### Incorrect

> "Feature #6 is blocked" (use "Plan #6")

> "The rate limiting task needs E2E tests" (tasks don't have E2E; plans do)

> "The credits system" (use "scrip")

## Origin

Defined to resolve confusion between "feature", "plan", "gap", and "task" during coordination.

---


## 12. Structured Logging

*Source: `docs/meta/12_structured-logging.md`*


## Philosophy

**Two logs always stored:**
1. **Full log** - Every event, machine-parseable, for debugging and analysis
2. **Tractable log** - Key events only, human-readable, for monitoring

This addresses the common problem: logs are either too verbose to read or too sparse to debug.

## Implementation

### Dual File Strategy

```yaml
# config/config.yaml
logging:
  # Full structured log (JSONL) - every event
  full_log: "run.jsonl"

  # Human-readable log - key events only
  readable_log: "run.log"
  readable_level: INFO  # DEBUG, INFO, WARNING, ERROR

  # Which event types appear in readable log
  readable_events:
    - simulation_start
    - simulation_end
    - tick_start
    - tick_end
    - action_executed
    - auction_resolved
    - budget_exhausted
    - error
    - warning
```

### Python Implementation

```python
import logging
import json
from pathlib import Path
from datetime import datetime

class DualLogger:
    """Logger that writes to both full JSONL and readable text."""

    def __init__(
        self,
        full_log: Path,
        readable_log: Path,
        readable_level: str = "INFO",
        readable_events: list[str] | None = None,
    ):
        self.full_log = full_log
        self.readable_log = readable_log
        self.readable_level = getattr(logging, readable_level.upper())
        self.readable_events = set(readable_events or [])

        # Clear logs on init
        self.full_log.write_text("")
        self.readable_log.write_text("")

        # Setup Python logger for readable output
        self._logger = logging.getLogger("agent_ecology")
        handler = logging.FileHandler(readable_log)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%H:%M:%S"
        ))
        self._logger.addHandler(handler)
        self._logger.setLevel(self.readable_level)

    def log(self, event_type: str, data: dict, level: str = "INFO") -> None:
        """Log an event to both outputs."""
        # Always write to full log
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": event_type,
            **data,
        }
        with open(self.full_log, "a") as f:
            f.write(json.dumps(event) + "\n")

        # Write to readable log if event type matches
        if event_type in self.readable_events or level in ("WARNING", "ERROR"):
            msg = self._format_readable(event_type, data)
            log_level = getattr(logging, level.upper())
            self._logger.log(log_level, msg)

    def _format_readable(self, event_type: str, data: dict) -> str:
        """Format event for human-readable output."""
        # Customize formatting per event type
        formatters = {
            "tick_start": lambda d: f"--- Tick {d.get('tick', '?')} ---",
            "action_executed": lambda d: (
                f"  {d.get('agent_id', '?')}: {d.get('action_type', '?')} -> "
                f"{d.get('status', '?')}"
            ),
            "auction_resolved": lambda d: (
                f"  [AUCTION] Winner: {d.get('winner', '?')}, "
                f"Minted: {d.get('minted', 0)}"
            ),
            "budget_exhausted": lambda d: (
                f"=== BUDGET EXHAUSTED: ${d.get('spent', 0):.4f} ==="
            ),
            "error": lambda d: f"ERROR: {d.get('message', str(d))}",
        }
        formatter = formatters.get(event_type, lambda d: f"{event_type}: {d}")
        return formatter(data)
```

## Event Levels

| Level | Full Log | Readable Log | Use For |
|-------|----------|--------------|---------|
| DEBUG | Yes | If configured | Internal state, debugging |
| INFO | Yes | If event type matches | Normal operations |
| WARNING | Yes | Always | Recoverable issues |
| ERROR | Yes | Always | Failures |

## Example Outputs

### Full Log (run.jsonl)

```json
{"timestamp": "2026-01-12T10:30:00.123Z", "event_type": "tick_start", "tick": 1}
{"timestamp": "2026-01-12T10:30:00.456Z", "event_type": "agent_think_start", "agent_id": "alpha", "input_tokens": 1234}
{"timestamp": "2026-01-12T10:30:01.789Z", "event_type": "agent_think_end", "agent_id": "alpha", "output_tokens": 567}
{"timestamp": "2026-01-12T10:30:01.890Z", "event_type": "action_executed", "agent_id": "alpha", "action_type": "write", "status": "success"}
{"timestamp": "2026-01-12T10:30:02.000Z", "event_type": "tick_end", "tick": 1, "scrip": {"alpha": 95}}
```

### Readable Log (run.log)

```
10:30:00 [INFO] --- Tick 1 ---
10:30:01 [INFO]   alpha: write -> success
10:30:02 [INFO] --- Tick 2 ---
10:30:03 [INFO]   beta: invoke -> success
10:30:04 [WARNING] Agent gamma running low on compute (5 remaining)
10:30:05 [INFO]   [AUCTION] Winner: alpha, Minted: 50
```

## Viewing Logs

### Full Log Analysis

```bash
# View recent events
tail -20 run.jsonl | jq .

# Filter by event type
cat run.jsonl | jq 'select(.event_type == "action_executed")'

# Count events by type
cat run.jsonl | jq -r '.event_type' | sort | uniq -c

# Use view_log.py script
python scripts/view_log.py --type action_executed --last 10
```

### Readable Log

```bash
# Just read it
cat run.log

# Follow live
tail -f run.log

# Search for issues
grep -E "(WARNING|ERROR)" run.log
```

## Migration from Print Statements

Replace print statements with structured logging:

```python
# Before
if self.verbose:
    print(f"    {agent.agent_id}: {input_tokens} in, {output_tokens} out")

# After
self.logger.log("agent_think_end", {
    "agent_id": agent.agent_id,
    "input_tokens": input_tokens,
    "output_tokens": output_tokens,
}, level="DEBUG")
```

## Configuration Options

```yaml
logging:
  # Paths
  full_log: "logs/run.jsonl"       # Full structured log
  readable_log: "logs/run.log"     # Human-readable log

  # Readable log settings
  readable_level: INFO             # Minimum level for readable log
  readable_events:                 # Event types to include
    - simulation_start
    - simulation_end
    - tick_start
    - tick_end
    - action_executed
    - auction_resolved
    - budget_exhausted
    - checkpoint_saved
    - error
    - warning

  # Console output (optional)
  console_level: WARNING           # Only warnings/errors to console

  # Retention (optional)
  max_log_size_mb: 100            # Rotate when exceeded
  keep_last_n_runs: 5             # Keep last N run logs
```

## Benefits

| Concern | Full Log | Readable Log |
|---------|----------|--------------|
| Debugging | All details available | N/A (use full log) |
| Monitoring | Too verbose | Key events only |
| Post-mortems | Parse and analyze | Quick human review |
| Storage | Larger files | Smaller files |
| Machine processing | JSONL format | Text format |

## Trade-offs

- **Storage**: Two files instead of one (but readable is smaller)
- **Performance**: Two writes per event (but async IO mitigates)
- **Complexity**: More configuration (but sane defaults work)

## Origin

Adopted after finding simulation logs too verbose for human monitoring but needing full detail for debugging. The dual-output pattern provides both without compromise.

---


## 13. Feature-Driven Development

*Source: `docs/meta/13_feature-driven-development.md`*


A comprehensive meta-process for AI-assisted software development that ensures verified progress, prevents AI drift, and maintains thin slices.

## Problem

### The "Fingers Crossed" Problem
Without this pattern:
- Work for days on implementation
- Hope everything integrates at the end
- Discover fundamental issues too late
- Painful "big bang" integration failures

### The AI Drift Problem
AI coding assistants (Claude Code, etc.):
- Forget ADRs and architectural constraints mid-implementation
- Make "reasonable assumptions" that diverge from requirements
- When implementation is hard, write weak tests that pass trivially
- Test what they built, not what was needed

### The Linkage Problem
Typical project structure has sparse, disconnected mappings:
- Plans are administrative, not architectural
- No concept linking code + tests + docs + ADRs
- Can't answer: "What ADRs apply to this file?"
- Can't answer: "What tests cover this feature?"

## Solution

### Core Concept: Feature as Central Entity

**Feature** = cohesive capability (e.g., "escrow", "rate_limiting")

A Feature contains:
- Problem statement (WHY)
- Acceptance criteria (WHAT, testable)
- Out of scope (explicit exclusions)
- ADR constraints
- Code files
- Test files
- Documentation

**Tasks** operate ON Features. Plans become administrative tracking, not organizational structure.

### The Lock-Before-Implement Principle

```
Spec written → Spec LOCKED (committed) → Implementation
                    │
                    └── AI cannot modify, so cannot cheat
```

Even if same AI instance, same context - once specs are committed and CI enforces immutability, the AI must pass the specs it wrote.

### Modifying Locked Specs

Locks prevent *sneaky* changes, not *all* changes. Legitimate reasons to modify specs:
- Requirements actually changed (user decision)
- Original spec was wrong or ambiguous
- Scope legitimately changed

**Process to modify:**

```
PR: Remove `locked: true` → Modify spec → Re-add `locked: true`
                │
                └── Human reviews diff, sees explicit unlock/modify/relock
```

**Why this works:**
| Protection | How |
|------------|-----|
| Friction | AI must explicitly unlock (shows intent) |
| Visibility | Spec changes show clearly in PR diff |
| Audit trail | Git history shows unlock → modify → relock |
| Human review | User reviews specs in plain English |

**The key insight:** The lock's value is making spec changes *visible and deliberate*, not *impossible*. If AI explicitly unlocks, modifies, and relocks, that's a deliberate choice visible in git history for human review.

**Stronger enforcement (if needed later):**
- Require `unlock_reason:` field in YAML
- Require separate unlock PR before modification PR
- Require human approval label (e.g., `spec-change-approved`)

Start simple. Add friction only if abuse is detected.

### Human-AI Division of Labor

| Role | Human | AI |
|------|-------|-----|
| Define problem | Reviews/approves | Writes |
| Write specs | Reviews (plain English) | Writes |
| Lock specs | Approves commit | Commits |
| Implement | Not involved | Writes |
| Review code | Not involved | N/A (CI does it) |
| Verify | Sees green CI | N/A |

**Human only touches what human is good at:** requirements and acceptance criteria in plain English.

**AI handles what AI is good at:** writing code and tests.

**CI handles what automation is good at:** verification and enforcement.

## Feature Definition Schema

```yaml
# features/escrow.yaml
feature: escrow
planning_mode: guided  # autonomous | guided | detailed | iterative

# === PRD SECTION (What/Why - Human-readable) ===
problem: |
  Agents need to trade artifacts without trusting each other.
  Currently, if Agent A sends artifact first, Agent B might not pay.

# === DESIGN SECTION (How - Optional, plain English) ===
# Use when: multiple approaches possible, architectural novelty, medium+ features
# Skip when: obvious implementation, bug fix, small feature
design:
  approach: |
    Escrow will be a contract artifact that temporarily holds ownership of
    the traded artifact until payment is received or timeout occurs.
  key_decisions:
    - "Timeout based on tick count, not wall clock (simpler, deterministic)"
    - "One escrow contract per trade (not a shared escrow pool)"
    - "Seller can cancel before buyer commits (flexibility)"
    - "Escrow is an artifact itself (per ADR-0001)"
  risks:
    - "If tick processing is slow, timeout could behave unexpectedly (accepted)"

acceptance_criteria:
  - id: AC-1
    scenario: "Basic escrow lock"
    given:
      - "Agent A owns an artifact"
      - "Agent A has sufficient scrip"
    when: "Agent A locks artifact in escrow with price 50"
    then:
      - "Artifact held by escrow system, not Agent A"
      - "Price recorded as 50 scrip"
      - "Agent A hasn't paid anything yet"
    locked: true  # AI cannot modify after commit

  - id: AC-2
    scenario: "Successful claim"
    given:
      - "Artifact locked in escrow at price 50"
      - "Agent B has 100 scrip"
    when: "Agent B pays 50 scrip to claim"
    then:
      - "Agent B now owns artifact"
      - "Agent A receives 50 scrip"
      - "Escrow cleared"
    locked: true

  - id: AC-3
    scenario: "Cannot claim without payment"
    given:
      - "Artifact locked at price 50"
    when: "Agent B tries to claim with only 30 scrip"
    then:
      - "Claim fails with InsufficientFundsError"
      - "Artifact stays in escrow"
      - "Agent B keeps their 30 scrip"
    locked: true

out_of_scope:
  - "Multi-party escrow (only 2-party supported)"
  - "Partial payments"
  - "Renegotiation after lock"
  - "Escrow fee negotiation"

# === IMPLEMENTATION SECTION ===
adrs: [1, 3]  # ADR-0001, ADR-0003

code:
  - src/world/escrow.py
  - src/world/contracts/escrow_contract.py

tests:
  - tests/unit/test_escrow.py
  - tests/e2e/test_escrow.py

docs:
  - docs/architecture/current/genesis_artifacts.md
```

## Design Section (The "How")

The design section captures architectural decisions BEFORE implementation.

### Why It Exists

Without design section:
```
Spec (WHAT) → Implementation (HOW happens invisibly)
```

CC could satisfy the spec with poor architecture. Tests pass, but code is:
- Hard to maintain
- Wrong patterns
- Doesn't fit existing codebase

Design section surfaces these choices for review.

### When to Use

| Planning Mode | Design Section |
|---------------|----------------|
| `autonomous` | Skip |
| `guided` | Optional (use when multiple approaches possible) |
| `detailed` | Required |
| `iterative` | Per-cycle (can evolve) |

| Feature Type | Design Section |
|--------------|----------------|
| Bug fix | Skip |
| Small utility | Skip |
| Medium feature | Recommended |
| Large feature | Required |
| Architectural change | Required |

### Format Rules

1. **Plain English only** - Human must be able to review without reading code
2. **5-10 lines max** - Not a formal design doc, just a checkpoint
3. **Focus on choices that matter** - Skip obvious decisions
4. **Include rationale** - "X because Y", not just "X"

### What to Include

```yaml
design:
  approach: "1-3 sentence summary of HOW this will be built"
  key_decisions:
    - "Decision 1 and brief rationale"
    - "Decision 2 and brief rationale"
    # 2-5 decisions, focus on non-obvious choices
  risks:  # Optional
    - "Known risk and whether accepted/mitigated"
```

### What NOT to Include

- Pseudocode or code snippets
- Database schemas (unless very simple)
- API signatures
- Implementation details

Keep it reviewable by someone who can't read code.

## Planning Depth Levels

Not all features require the same planning depth.

### Autonomous Mode
```
Human: "Add logging to the simulation"
AI: Writes spec, locks it, implements, done
Human: Sees green CI, trusts result
```
- **Use for:** Low-stakes, well-understood, utilities
- **Risk accepted:** AI might build wrong thing
- **Benefit:** Fast, no bottleneck

### Guided Mode (Default)
```
Human: "I need escrow for trading"
AI: Writes spec in plain English Given/When/Then
Human: "Yes" / "Add timeout case" / "Remove partial payments"
AI: Revises, locks, implements
Human: Sees green CI
```
- **Use for:** Most features
- **Balanced:** Human validates requirements, doesn't read code

### Detailed Mode
```
Human: "Let's design the economic model"
[Days of dialogue]
Human: "What if agents can go into debt?"
AI: "Here are tradeoffs..."
Human: "Let's prohibit debt but allow credit lines"
[More rounds]
AI: Locks spec, implements
```
- **Use for:** Critical features, novel problems, core architecture
- **High investment:** Human deeply involved in spec creation

### Iterative Mode
```
Cycle 1:
  Human: "I want agents to cooperate somehow"
  AI: Writes minimal spec for basic cooperation
  Human: Approves
  AI: Locks v1, implements v1

Cycle 2:
  Human: "Interesting, but they're not forming groups"
  AI: Writes spec v2 based on learnings
  AI: Locks v2, implements v2

Cycle 3:
  [Refined spec based on learnings]
```
- **Use for:** R&D, exploratory, unclear requirements
- **Key:** Each cycle still has lock-before-implement
- **Learning:** Requirements emerge from implementation feedback

## Preventing AI Cheating

### The Problem

When AI writes both spec AND implementation:
- Knows what's easy while writing specs
- Can write weak specs broken code passes
- Skip edge cases that reveal bugs
- Test what it built, not what was needed

### Solution: Temporal Separation + Lock

1. **Spec Phase:** AI writes Given/When/Then specs
2. **Lock Phase:** Specs committed to git, CI enforces immutability
3. **Impl Phase:** AI implements to pass locked specs

AI cannot modify locked specs. If implementation is hard, AI must either:
- Make it work (correct behavior)
- Report failure (honest behavior)

NOT: Weaken the test (cheating)

### Role Framing (Optional Enhancement)

Different prompts for different phases:

**Spec Phase:** "You are QA. Write specs to catch bugs in code someone else will write. Be adversarial. Think about edge cases and failure modes."

**Impl Phase:** "You are a developer. Make these tests pass. You cannot modify the tests."

### Minimum Spec Requirements (CI Enforced)

```yaml
spec_requirements:
  minimum_scenarios: 3
  required_categories:
    - happy_path: "At least one success case"
    - error_case: "At least one failure mode"
    - edge_case: "At least one boundary condition"
  format: "Given/When/Then"
  assertions: "Specific, testable statements in 'then'"
```

## ADR Conformance

### Pre-Implementation Checklist

Before implementing, AI must produce:

```markdown
## Pre-Implementation Checklist

### Feature: escrow
### Task: Add timeout functionality

**Acceptance Criteria Addressed:**
- AC-3: "Escrow times out after N ticks if unclaimed"

**ADR Conformance:**
- ADR-0001 (Everything is artifact): Escrow is already an artifact ✓
- ADR-0003 (Contracts can do anything): Timeout logic in contract ✓

**Out of Scope Verified:**
- NOT adding renegotiation (out of scope) ✓
- NOT adding partial refunds (out of scope) ✓

**Test Plan:**
- Will add test_timeout to test_escrow.py
- Maps to AC-3
```

### Governance Headers

ADR references in source file headers keep constraints visible:

```python
# src/world/escrow.py
# --- GOVERNANCE START (do not edit) ---
# ADR-0001: Everything is an artifact
# ADR-0003: Contracts can do anything
# --- GOVERNANCE END ---
```

## Process Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│ 1. FEATURE DEFINITION (What/Why)                                    │
├─────────────────────────────────────────────────────────────────────┤
│ AI: Writes problem statement, out_of_scope                          │
│ Human: Reviews/approves (if guided/detailed mode)                   │
│ Output: features/<name>.yaml (problem, out_of_scope)                │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 2. SPEC WRITING (What exactly)                                      │
├─────────────────────────────────────────────────────────────────────┤
│ AI: Writes Given/When/Then acceptance criteria                      │
│ Human: Reviews/approves (if guided/detailed mode)                   │
│ CI: Validates spec completeness (minimum requirements)              │
│ Output: acceptance_criteria added to feature file                   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 3. DESIGN (How - Optional based on planning_mode)                   │
├─────────────────────────────────────────────────────────────────────┤
│ AI: Writes approach, key_decisions, risks (plain English)           │
│ Human: Reviews architectural choices                                │
│ Skip if: autonomous mode, small feature, obvious implementation     │
│ Output: design section added to feature file                        │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 4. LOCK                                                             │
├─────────────────────────────────────────────────────────────────────┤
│ Feature file committed to git (specs + design locked)               │
│ CI will reject future modifications to locked sections              │
│ Tests auto-generated from acceptance criteria (also locked)         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 5. PRE-IMPLEMENTATION CHECKLIST                                     │
├─────────────────────────────────────────────────────────────────────┤
│ AI: Documents ADR conformance plan                                  │
│ AI: Acknowledges out_of_scope constraints                           │
│ AI: Confirms design approach (if design section exists)             │
│ AI: Lists acceptance criteria being addressed                       │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 6. IMPLEMENTATION                                                   │
├─────────────────────────────────────────────────────────────────────┤
│ AI: Writes code to pass locked specs                                │
│ AI: Cannot modify specs or generated tests                          │
│ Human: Not involved                                                 │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 7. VERIFICATION                                                     │
├─────────────────────────────────────────────────────────────────────┤
│ CI: All tests pass                                                  │
│ CI: Locked files unchanged                                          │
│ CI: Doc-coupling check passes                                       │
│ CI: ADR conformance documented                                      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ 8. MERGE                                                            │
├─────────────────────────────────────────────────────────────────────┤
│ Human: Sees green CI = done                                         │
│ No code review needed (specs are the contract)                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Task Types

Features contain tasks. Each task has a type with specific verification:

| Type | What It Is | Verification |
|------|------------|--------------|
| `impl` | Code implementation | Feature tests pass, ADR conformance documented |
| `doc` | Documentation | Doc-coupling check passes, terminology correct |
| `arch` | Architecture decision | ADR exists, governance sync passes |

## Thin Slices (Always)

### Principle

Every unit of work must prove it works end-to-end before declaring success.

### Why

- Unit tests passing ≠ system works
- Small increments = verified progress
- Catches integration issues early
- Limits blast radius of mistakes

### Orthogonal to Planning Depth

| Combination | Meaning |
|-------------|---------|
| Autonomous + thin slices | AI makes assumptions, delivers small increments |
| Detailed + thin slices | Extensive planning, still small deliverables |
| Detailed + big slice | **ANTI-PATTERN** (avoid) |

## Files

| File | Purpose |
|------|---------|
| `features/*.yaml` | Feature definitions (single source of truth) |
| `scripts/validate_spec.py` | Validates spec completeness |
| `scripts/check_locked_files.py` | Ensures locked files unchanged |
| `scripts/generate_tests.py` | Generates test stubs from specs |

## Setup (New Project)

1. Create `features/` directory
2. Add spec validation to CI:
   ```yaml
   - name: validate-specs
     run: python scripts/validate_spec.py --all

   - name: check-locked-files
     run: python scripts/check_locked_files.py
   ```
3. Configure minimum spec requirements in `config/spec_requirements.yaml`
4. Add feature definition template

## Usage

### Creating a New Feature

```bash
# 1. Create feature definition
claude "Create feature definition for user authentication"
# AI writes features/authentication.yaml with problem, out_of_scope

# 2. Review and approve (if guided mode)
# Human reviews the definition

# 3. Create specs
claude "Write acceptance criteria for authentication feature"
# AI writes Given/When/Then specs

# 4. Review specs (if guided mode)
# Human reviews acceptance criteria

# 5. Lock specs
git add features/authentication.yaml
git commit -m "Lock authentication feature specs"

# 6. Implement
claude "Implement authentication to pass the locked specs"
# AI implements, cannot modify specs

# 7. Verify
# CI runs, human sees green = done
```

### Iterative Development

```bash
# Cycle 1
claude "Create minimal spec for agent cooperation - we'll iterate"
git commit -m "Lock cooperation v1 specs"
claude "Implement cooperation v1"

# Learn from implementation
# Human: "I see agents aren't forming groups"

# Cycle 2
claude "Update cooperation spec to include group formation based on learnings"
git commit -m "Lock cooperation v2 specs"
claude "Implement cooperation v2"
```

## CI Enforcement

```yaml
# .github/workflows/ci.yml

jobs:
  validate-specs:
    runs-on: ubuntu-latest
    steps:
      - name: Check spec completeness
        run: python scripts/validate_spec.py --all

  check-locks:
    runs-on: ubuntu-latest
    steps:
      - name: Verify locked files unchanged
        run: python scripts/check_locked_files.py --locked "features/*/spec.yaml"

  feature-tests:
    runs-on: ubuntu-latest
    steps:
      - name: Run feature tests
        run: pytest tests/features/ -v
```

## Customization

### Adjusting Minimum Spec Requirements

```yaml
# config/spec_requirements.yaml
minimum_scenarios: 3  # Increase for critical features
required_categories:
  - happy_path
  - error_case
  - edge_case
  - security_case  # Add for security-sensitive features
```

### Planning Mode Defaults

```yaml
# config/defaults.yaml
default_planning_mode: guided
allow_autonomous: true
require_approval_for_lock: true
```

## Limitations

### What This Pattern Solves
- AI drift from ADRs/constraints
- AI cheating by weakening tests
- Big bang integration failures
- Sparse file-to-constraint mapping
- "Fingers crossed" development

### What This Pattern Doesn't Solve
- Knowing the right requirements (requires human judgment)
- Ambiguous natural language in specs (minimize with Given/When/Then)
- AI missing non-obvious edge cases in autonomous mode
- Performance optimization (this is about correctness)

### Accepted Risks

| Risk | Mitigation | Residual |
|------|------------|----------|
| Weak specs in autonomous mode | Spec validation | Non-obvious gaps |
| Wrong requirements | Human reviews (guided/detailed) | None if human reviews |
| Ambiguous spec language | Structured format | Some ambiguity possible |

## Related Patterns

- [Feature Linkage](14_feature-linkage.md) - Companion pattern: optimal linkage structure
- [ADR](07_adr.md) - Architecture Decision Records
- [ADR Governance](08_adr-governance.md) - Linking ADRs to code
- [Doc-Code Coupling](10_doc-code-coupling.md) - Linking docs to code
- [Testing Strategy](03_testing-strategy.md) - Test organization
- [Verification Enforcement](17_verification-enforcement.md) - Proving completion

## Origin

Emerged from coordination problems with multiple Claude Code instances on [agent_ecology](https://github.com/BrianMills2718/agent_ecology2), specifically:
- Repeated "big bang" integration failures
- AI making reasonable but wrong assumptions
- Difficulty tracing requirements to code to tests
- Human unable to validate code but able to validate requirements

## Enterprise Patterns Incorporated

| Pattern | Source | How Used |
|---------|--------|----------|
| PRD structure | Product management | Problem, acceptance criteria, out of scope |
| BDD | Agile testing | Given/When/Then format |
| ATDD | Test-driven development | Tests before implementation |
| Requirements traceability | Systems engineering | Feature → Code → Test chain |
| Definition of Done | Scrum | Per-task-type verification |

---


## 14. Feature Linkage

*Source: `docs/meta/14_feature-linkage.md`*


How to structure relationships between ADRs, features, code, tests, and documentation for full traceability.

## Complete Linkage Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CURRENT STATE (Problematic)                         │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────┐                                           ┌───────────┐
    │   ADRs    │                                           │   Plans   │
    │ (5 exist) │                                           │(34 exist) │
    └─────┬─────┘                                           └─────┬─────┘
          │                                                       │
          │ governance.yaml                                       │ (weak soft
          │ (SPARSE: only 5 files!)                               │  coupling)
          ▼                                                       ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                           SOURCE FILES (src/)                            │
    │                                                                          │
    │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
    │   │ledger.py │ │escrow.py │ │runner.py │ │agent.py  │ │ ??? .py  │     │
    │   │ mapped   │ │ mapped   │ │NOT mapped│ │NOT mapped│ │NOT mapped│     │
    │   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
    └─────────────────────────────────────────────────────────────────────────┘
          │
          │ doc_coupling.yaml (MANUAL, incomplete)
          ▼
    ┌───────────┐         ┌───────────┐
    │   DOCS    │    ?    │   TESTS   │  ← No mapping to features/plans
    └───────────┘         └───────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│                              OPTIMAL STATE (New)                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

                         ┌─────────────────────────────────┐
                         │         features.yaml           │
                         │    (SINGLE SOURCE OF TRUTH)     │
                         └────────────────┬────────────────┘
                                          │
           ┌──────────────────────────────┼──────────────────────────────┐
           │                              │                              │
           ▼                              ▼                              ▼
    ┌─────────────┐               ┌─────────────┐               ┌─────────────┐
    │  FEATURE:   │               │  FEATURE:   │               │  FEATURE:   │
    │   escrow    │               │   ledger    │               │rate_limiting│
    └──────┬──────┘               └──────┬──────┘               └──────┬──────┘
           │                              │                              │
           ▼                              ▼                              ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         FEATURE CONTENTS                                 │
    │                                                                          │
    │   problem         → WHY this feature exists                              │
    │   acceptance_criteria → Given/When/Then specs (LOCKED before impl)       │
    │   out_of_scope    → Explicit exclusions (prevents AI drift)              │
    │   adrs            → [1, 3] constraints from architecture decisions       │
    │   code            → [escrow.py, ...] source files                        │
    │   tests           → [test_escrow.py, ...] verification                   │
    │   docs            → [genesis.md, ...] documentation                      │
    └─────────────────────────────────────────────────────────────────────────┘
                                          │
                    ┌─────────────────────┬┴───────────────────┐
                    │                     │                    │
                    ▼                     ▼                    ▼
           ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
           │   DERIVED:   │      │   DERIVED:   │      │   DERIVED:   │
           │  governance  │      │ doc-coupling │      │ test-mapping │
           │ (file → ADR) │      │ (file → doc) │      │(file → test) │
           └──────────────┘      └──────────────┘      └──────────────┘


                         QUERIES NOW POSSIBLE
    ┌─────────────────────────────────────┬───────────────────────────────┐
    │  QUERY                              │  LOOKUP PATH                  │
    ├─────────────────────────────────────┼───────────────────────────────┤
    │  "What ADRs apply to escrow.py?"    │  file → feature → adrs        │
    │  "What tests cover escrow?"         │  feature → tests              │
    │  "What feature owns runner.py?"     │  file → feature               │
    │  "Is escrow fully tested?"          │  feature.tests all pass?      │
    │  "What docs need update?"           │  file → feature → docs        │
    │  "What does ADR-1 govern?"          │  reverse: adrs → features     │
    └─────────────────────────────────────┴───────────────────────────────┘
```

## Problem

### Sparse, Disconnected Mappings

See "CURRENT STATE" in the diagram above. Key issues:

- `governance.yaml` only maps ~5 files to ADRs
- Most source files have NO ADR mapping
- `doc_coupling.yaml` is manual and incomplete
- Plans are administrative, not linked to code
- No Feature concept linking code + tests + docs + ADRs
- Tests have no mapping to features or plans

### What's Missing

| Query | Can Answer? |
|-------|-------------|
| "What ADRs apply to this file?" | Only if file is in sparse mapping |
| "What tests cover this feature?" | No |
| "Which plan owns this file?" | No |
| "Is this feature fully tested?" | No |
| "What docs need updating if I change X?" | Partial |

## Solution

### Feature as Central Entity

See "OPTIMAL STATE" in the diagram above. **Feature** becomes the single source of truth connecting:

- **ADRs** - Architectural constraints
- **Code** - Source files implementing the feature
- **Tests** - Verification that feature works
- **Docs** - Documentation explaining the feature

All other mappings (governance, doc-coupling, test-mapping) are **derived** from features.yaml.

### Features.yaml Schema

```yaml
features:
  escrow:
    description: "Trustless artifact trading"

    # Constraints
    adrs: [1, 3]  # ADR-0001, ADR-0003

    # Implementation
    code:
      - src/world/escrow.py
      - src/world/contracts/escrow_contract.py

    # Verification
    tests:
      - tests/unit/test_escrow.py
      - tests/e2e/test_escrow.py

    # Documentation
    docs:
      - docs/architecture/current/genesis_artifacts.md

  rate_limiting:
    description: "Token bucket rate limiting for resources"
    adrs: [2]
    code:
      - src/world/rate_tracker.py
    tests:
      - tests/unit/test_rate_tracker.py
    docs:
      - docs/architecture/current/resources.md

  # ... all features
```

## Derived Mappings

From `features.yaml`, derive all other mappings:

### File → ADR (replaces governance.yaml)

```python
def get_adrs_for_file(filepath: str) -> list[int]:
    """Given a file, return which ADRs govern it."""
    for feature in features.values():
        if filepath in feature['code']:
            return feature['adrs']
    return []
```

### File → Doc (replaces doc_coupling.yaml)

```python
def get_docs_for_file(filepath: str) -> list[str]:
    """Given a file, return which docs should be updated."""
    for feature in features.values():
        if filepath in feature['code']:
            return feature['docs']
    return []
```

### Feature → Tests

```python
def get_tests_for_feature(feature_name: str) -> list[str]:
    """Given a feature, return its tests."""
    return features[feature_name]['tests']
```

### File → Feature (reverse lookup)

```python
def get_feature_for_file(filepath: str) -> str | None:
    """Given a file, return which feature owns it."""
    for name, feature in features.items():
        if filepath in feature['code']:
            return name
    return None
```

## Queries Now Possible

| Query | How |
|-------|-----|
| "What ADRs apply to this file?" | `get_adrs_for_file(path)` |
| "What tests cover this feature?" | `get_tests_for_feature(name)` |
| "What feature owns this file?" | `get_feature_for_file(path)` |
| "Is this feature fully tested?" | Check all tests in feature pass |
| "What docs need updating?" | `get_docs_for_file(path)` |
| "What files does ADR-X govern?" | Reverse lookup through features |

## Handling Edge Cases

### Shared Utilities

Files used by multiple features:

```yaml
shared:
  utils:
    description: "Shared utility functions"
    code:
      - src/utils.py
      - src/common/helpers.py
    # No specific ADRs - inherits from all features that use it
    # Tests in unit tests, not feature tests
    tests:
      - tests/unit/test_utils.py
```

### Code Not Yet Assigned

Temporary state during migration:

```yaml
unassigned:
  description: "Code not yet assigned to a feature"
  code:
    - src/legacy/old_module.py
  # Flagged in CI as needing assignment
```

### Multiple Features for One File

If a file legitimately belongs to multiple features (rare):

```yaml
ledger:
  code:
    - src/world/ledger.py  # Primary

escrow:
  code:
    - src/world/ledger.py  # Also uses (secondary)
```

Resolution: Primary feature's ADRs apply. Both features' tests must pass.

## Migration Path

### From Current State

1. **Audit existing code** - List all files in `src/`
2. **Identify features** - Group files by capability
3. **Create features.yaml** - Define features with code mappings
4. **Add ADR mappings** - Which ADRs apply to each feature
5. **Add test mappings** - Which tests verify each feature
6. **Deprecate old configs** - Replace governance.yaml, doc_coupling.yaml

### Validation Script

```bash
# Check all src/ files are assigned to a feature
python scripts/check_feature_coverage.py

# Output:
# ✓ src/world/ledger.py -> feature:ledger
# ✓ src/world/escrow.py -> feature:escrow
# ✗ src/world/orphan.py -> UNASSIGNED
```

## Files

| File | Purpose |
|------|---------|
| `features.yaml` | Single source of truth |
| `scripts/derive_governance.py` | Generate governance.yaml from features |
| `scripts/derive_doc_coupling.py` | Generate doc_coupling.yaml from features |
| `scripts/check_feature_coverage.py` | Ensure all code assigned |

## Benefits

| Before | After |
|--------|-------|
| Sparse ADR mapping | Complete coverage via features |
| Manual doc_coupling.yaml | Derived from features |
| "What owns this file?" - unknown | Feature lookup |
| "Is feature tested?" - unknown | Feature.tests check |
| Plans as organization | Features as organization, plans as tasks |

## Related Patterns

- [Feature-Driven Development](13_feature-driven-development.md) - The complete meta-process
- [ADR Governance](08_adr-governance.md) - Now derived from features
- [Doc-Code Coupling](10_doc-code-coupling.md) - Now derived from features
- [Documentation Graph](09_documentation-graph.md) - Features as nodes

## Origin

Identified during meta-process design when analyzing why ADR conformance checking would fail - the linkage from files to ADRs was too sparse to be useful. Feature-centric organization provides complete coverage.

---


## 15. Plan Workflow

*Source: `docs/meta/15_plan-workflow.md`*


## Problem

Work happens without tracking. AI assistants implement features without:
- Recording what changed
- Linking to requirements
- Following consistent structure
- Ensuring tests exist

Result: orphan code, undocumented features, missed requirements.

## Solution

1. Every significant change has a "plan" document
2. Plans define: gap (current vs target), changes, tests, verification
3. Status tracked in plan file AND index
4. Commit messages link to plans: `[Plan #N]`
5. TDD: define tests in plan before implementing

## Files

| File | Purpose |
|------|---------|
| `docs/plans/CLAUDE.md` | Master index of all plans |
| `docs/plans/NN_name.md` | Individual plan files |
| `scripts/check_plan_tests.py` | Verify plan test requirements |
| `scripts/sync_plan_status.py` | Keep plan/index in sync |

## Setup

### 1. Create the plans directory

```bash
mkdir -p docs/plans
```

### 2. Create the master index

```markdown
<!-- docs/plans/CLAUDE.md -->
# Implementation Plans

| # | Gap | Priority | Status | Blocks |
|---|-----|----------|--------|--------|
| 1 | [Feature A](01_feature_a.md) | High | 📋 Planned | #2 |
| 2 | [Feature B](02_feature_b.md) | Medium | ⏸️ Blocked | - |

## Status Key

| Status | Meaning |
|--------|---------|
| 📋 Planned | Ready to implement |
| 🚧 In Progress | Being worked on |
| ⏸️ Blocked | Waiting on dependency |
| ❌ Needs Plan | Gap identified, no plan yet |
| ✅ Complete | Implemented and verified |
```

### 3. Create a plan template

```markdown
<!-- docs/plans/NN_name.md -->
# Gap N: [Name]

**Status:** 📋 Planned
**Priority:** High | Medium | Low
**Blocked By:** None | #X, #Y
**Blocks:** None | #A, #B

---

## Gap

**Current:** What exists now

**Target:** What we want

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/module.py` | Add new function |
| `config/config.yaml` | New setting |

### Steps

1. Create X
2. Modify Y
3. Add tests
4. Update docs

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_module.py` | `test_basic_function` | Happy path |
| `tests/test_module.py` | `test_error_handling` | Error cases |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/test_related.py` | Integration unchanged |

---

## Verification

- [ ] Required tests pass
- [ ] Full test suite passes
- [ ] Type check passes
- [ ] Docs updated

---

## Notes

[Design decisions, alternatives considered]
```

### 4. Create the plan tests script

```python
#!/usr/bin/env python3
"""Check plan test requirements."""

import re
import sys
import subprocess
from pathlib import Path

def get_plan_tests(plan_path: Path) -> list[tuple[str, str]]:
    """Extract required tests from plan file."""
    content = plan_path.read_text()
    tests = []

    # Find tests in "## Required Tests" section
    in_tests = False
    for line in content.split("\n"):
        if "## Required Tests" in line:
            in_tests = True
        elif line.startswith("## ") and in_tests:
            in_tests = False
        elif in_tests and "|" in line:
            parts = [p.strip() for p in line.split("|")]
            if len(parts) >= 3 and parts[1].startswith("tests/"):
                tests.append((parts[1], parts[2]))

    return tests

def run_tests(tests: list[tuple[str, str]]) -> bool:
    """Run specified tests."""
    all_passed = True
    for test_file, test_func in tests:
        target = f"{test_file}::{test_func}" if test_func else test_file
        result = subprocess.run(
            ["pytest", target, "-v"],
            capture_output=True
        )
        if result.returncode != 0:
            all_passed = False
    return all_passed

def main():
    plans_dir = Path("docs/plans")

    if "--list" in sys.argv:
        for plan in sorted(plans_dir.glob("[0-9]*.md")):
            tests = get_plan_tests(plan)
            print(f"{plan.name}: {len(tests)} required tests")
        return 0

    if "--plan" in sys.argv:
        idx = sys.argv.index("--plan")
        plan_num = sys.argv[idx + 1]
        plan_files = list(plans_dir.glob(f"{plan_num.zfill(2)}*.md"))
        if not plan_files:
            print(f"Plan {plan_num} not found")
            return 1

        tests = get_plan_tests(plan_files[0])
        if "--tdd" in sys.argv:
            print("Tests to write:")
            for test_file, test_func in tests:
                print(f"  {test_file}::{test_func}")
            return 0

        if not run_tests(tests):
            return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

### 5. Add status sync script

```python
#!/usr/bin/env python3
"""Sync plan status between plan files and index."""

import re
import sys
from pathlib import Path

def get_plan_status(plan_path: Path) -> str:
    """Extract status from plan file."""
    content = plan_path.read_text()
    match = re.search(r'\*\*Status:\*\*\s*(.+)', content)
    return match.group(1).strip() if match else "Unknown"

def main():
    plans_dir = Path("docs/plans")
    index_path = plans_dir / "CLAUDE.md"

    mismatches = []
    for plan in sorted(plans_dir.glob("[0-9]*.md")):
        status = get_plan_status(plan)
        # Check against index...
        # (simplified - real script parses index table)

    if "--check" in sys.argv and mismatches:
        print("Status mismatches found:")
        for m in mismatches:
            print(f"  {m}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
```

## Usage

### Creating a new plan

```bash
# 1. Create plan file
cp docs/plans/template.md docs/plans/33_my_feature.md

# 2. Edit with gap description, steps, required tests
vim docs/plans/33_my_feature.md

# 3. Add to index
vim docs/plans/CLAUDE.md
```

### Implementing a plan

```bash
# 1. Check dependencies
cat docs/plans/33_my_feature.md | grep "Blocked By"

# 2. Update status
# In plan file: **Status:** 🚧 In Progress
# In index: same

# 3. TDD - see what tests to write
python scripts/check_plan_tests.py --plan 33 --tdd

# 4. Write tests (they fail initially)
vim tests/test_feature.py

# 5. Implement until tests pass
vim src/feature.py
pytest tests/test_feature.py -v

# 6. Verify all requirements
python scripts/check_plan_tests.py --plan 33
pytest tests/
python -m mypy src/

# 7. Update status to Complete
# In plan file AND index

# 8. Commit with plan reference
git commit -m "[Plan #33] Implement my feature"
```

### Checking plan status

```bash
# List all plans with test counts
python scripts/check_plan_tests.py --list

# Check specific plan's tests
python scripts/check_plan_tests.py --plan 33

# Check status sync
python scripts/sync_plan_status.py --check
```

## Customization

### Plan numbering

```bash
# Option 1: Sequential (01, 02, 03...)
docs/plans/01_auth.md

# Option 2: Categorical (1xx for core, 2xx for UI...)
docs/plans/101_auth.md
docs/plans/201_dashboard.md

# Option 3: Date-based
docs/plans/2024-01-auth.md
```

### Status symbols

```markdown
| Status | Meaning |
|--------|---------|
| ⬜ Backlog | Not yet planned |
| 📋 Planned | Ready to start |
| 🚧 Building | In progress |
| 🔍 Review | PR open |
| ✅ Done | Merged |
| ❌ Won't Do | Cancelled |
```

### Add priority labels

```markdown
**Priority:** 🔴 Critical | 🟠 High | 🟡 Medium | 🟢 Low
```

### Integrate with GitHub Issues

```markdown
# Gap N: [Name]

**Status:** 📋 Planned
**GitHub Issue:** #123
**PR:** (pending)
```

## Trivial Exemption

Not everything needs a plan. Use `[Trivial]` prefix for tiny changes:

```bash
git commit -m "[Trivial] Fix typo in README"
git commit -m "[Trivial] Update copyright year"
git commit -m "[Trivial] Fix formatting in config"
```

**Trivial criteria (all must be true):**
- Less than 20 lines changed
- No changes to `src/` (production code)
- No new files created
- No test changes (except fixing typos)

**CI validates trivial commits** - if a `[Trivial]` commit exceeds limits, CI warns.

**Why this exists:** Plans add value for significant work but create friction for tiny fixes. The 80/20 principle: most value comes from planning significant work, not typo fixes.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Test requirement format | **Plain English + pytest path** | Both: description for humans, path for automation |
| Trivial exemption | **`[Trivial]` prefix** | Reduces friction; CI validates size limits |
| File lists in plans | **Optional** | Impractical to maintain upfront; derived from feature scope |

## Limitations

- **Manual status updates** - Must remember to update both plan file and index.
- **No enforcement** - Plans are advisory unless combined with hooks/CI.
- **Stale plans** - Old plans may reference outdated code/structure.

## Best Practices

1. **Use `[Trivial]` for tiny changes** - Typos, formatting, comments
2. **Use `[Unplanned]` sparingly** - CI blocks these; reserved for emergencies
3. **Keep plans small** - One feature per plan, not epics
4. **Archive completed plans** - Move to `docs/plans/archive/` after a quarter
5. **Link PRs to plans** - PR description should reference plan

## See Also

- [Git hooks pattern](06_git-hooks.md) - Enforces plan references in commits
- [PR coordination pattern](21_pr-coordination.md) - Auto-updates plan status on merge
- [Claim system pattern](18_claim-system.md) - Tracks who's working on which plan

---


## 16. Plan Blocker Enforcement

*Source: `docs/meta/16_plan-blocker-enforcement.md`*


## Problem

Without blocker chain validation:
- Plans remain "Blocked" after their blockers complete
- Dependency graphs become stale and misleading
- Teams don't know which plans are actually ready to start
- Coordination overhead increases as people manually check dependencies

## Solution

A CI check that validates plan dependency chains:
1. Parses all plan files for "Blocked By" field
2. Cross-references against plan statuses
3. Fails if any plan is blocked by a completed plan
4. Suggests the appropriate new status (Needs Plan, Planned, etc.)

**Key principle:** When a blocker completes, all plans it blocks should be updated to their next logical status.

## Files

| File | Purpose |
|------|---------|
| `scripts/check_plan_blockers.py` | Enforcement script |
| `.github/workflows/ci.yml` | CI job `plan-blockers` |
| `docs/plans/*.md` | Plan files with status and blockers |

## Usage

### Check for stale blockers

```bash
# Report only
python scripts/check_plan_blockers.py

# Fail if issues found (CI mode)
python scripts/check_plan_blockers.py --strict

# Show suggested fixes
python scripts/check_plan_blockers.py --fix

# Apply fixes automatically
python scripts/check_plan_blockers.py --apply
```

### Example output

```
STALE BLOCKERS FOUND

These plans are marked 'Blocked' but their blockers are Complete:

  Plan #7: Single ID Namespace
    Status: Blocked
    Blocked by: #6 (Unified Artifact Ontology)
    Blocker status: Complete
    Suggested new status: Needs Plan
```

### What happens when `--apply` runs

1. Updates status from "Blocked" to suggested status
2. Clears the "Blocked By" field (sets to "None")
3. You must then run `python scripts/sync_plan_status.py --sync` to update the index

## Status Transition Logic

When unblocking, the script determines the new status:

| Plan Contains | New Status |
|---------------|------------|
| "Needs design work" | `Needs Plan` |
| Implementation steps defined | `Planned` |
| Default | `Needs Plan` |

## CI Integration

The `plan-blockers` job runs on every PR:

```yaml
plan-blockers:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: "3.11"
    - run: python scripts/check_plan_blockers.py --strict
```

This prevents merging PRs that leave stale blockers in the codebase.

## Workflow Integration

### When completing a plan

1. Mark plan as Complete
2. Run `python scripts/check_plan_blockers.py` to see what it unblocks
3. Update the unblocked plans' statuses
4. Run `python scripts/sync_plan_status.py --sync` to update index

Or automate with:
```bash
python scripts/check_plan_blockers.py --apply
python scripts/sync_plan_status.py --sync
```

### When creating a new plan

Always specify blockers explicitly:
```markdown
**Blocked By:** #6, #11
```

Use `None` if no blockers:
```markdown
**Blocked By:** None
```

## Relationship to Other Patterns

| Pattern | Relationship |
|---------|--------------|
| Plan Status Sync | Blocker check runs after, before sync |
| Doc-Code Coupling | Both enforce documentation accuracy |
| Verification Enforcement | Blocker check is a form of plan verification |
| Claim System | Unblocked plans become claimable |

## Limitations

- Only checks direct blockers (not transitive)
- Doesn't validate that blocker numbers exist
- Doesn't prevent circular dependencies
- Status suggestion is heuristic, not always accurate

## Origin

Created after discovering 5 plans marked "Blocked" by already-completed plans during a codebase audit. The enforcement gap meant teams didn't know which plans were ready to start.

---


## 17. Verification Enforcement

*Source: `docs/meta/17_verification-enforcement.md`*


## Problem

Without mandatory verification:
- Plans get marked "complete" without running tests
- Integration failures accumulate undetected
- "Big bang" testing reveals many issues at once
- No evidence that verification actually happened
- AI assistants may claim completion without proof

## Solution

Require a verification script to mark plans as complete. The script:
1. Runs required tests (unit + E2E smoke)
2. Checks doc-code coupling
3. Records evidence in the plan file
4. Updates status only if all checks pass

**Key principle:** The status update is gated by actual test runs, not promises.

## Files

| File | Purpose |
|------|---------|
| `scripts/complete_plan.py` | Enforcement script |
| `tests/e2e/test_smoke.py` | Basic E2E verification |
| `tests/e2e/conftest.py` | Mocked LLM fixtures |
| `docs/plans/NN_*.md` | Plan files with evidence |

## Setup

1. Create the E2E test directory:
```bash
mkdir -p tests/e2e
```

2. Copy or create the verification script:
```bash
# scripts/complete_plan.py
# See implementation in this project
```

3. Create E2E smoke tests that verify basic functionality:
```python
# tests/e2e/test_smoke.py
def test_basic_functionality(mock_llm):
    """Verify core system works end-to-end."""
    # Your basic smoke test here
    pass
```

4. Update CLAUDE.md to require the script:
```markdown
### Plan Completion (MANDATORY)

> **Never manually set a plan status to Complete.**
> Always use: `python scripts/complete_plan.py --plan N`
```

## Usage

### Completing a plan

```bash
# Standard completion
python scripts/complete_plan.py --plan 35

# Dry run (check without updating)
python scripts/complete_plan.py --plan 35 --dry-run

# Skip E2E for documentation-only plans
python scripts/complete_plan.py --plan 35 --skip-e2e
```

### What the script does

1. **Unit tests** - Runs `pytest tests/ --ignore=tests/e2e/`
2. **E2E smoke** - Runs `pytest tests/e2e/test_smoke.py`
3. **Doc coupling** - Runs `python scripts/check_doc_coupling.py --strict`
4. **Evidence** - Records results in plan file
5. **Status** - Updates to "Complete" only if all pass

### Evidence format

After completion, plan files include:

```markdown
**Status:** ✅ Complete
**Verified:** 2026-01-12T10:30:00Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-12T10:30:00Z
tests:
  unit: 145/145 passed
  e2e_smoke: PASSED (8.2s)
  doc_coupling: passed
commit: a9ba628
```
```

## Customization

### Adding more verification steps

Edit `complete_plan.py` to add checks:

```python
def run_custom_check(project_root: Path) -> tuple[bool, str]:
    """Add your custom verification."""
    result = subprocess.run(["your-command"], ...)
    return result.returncode == 0, "summary"
```

### Plan-specific tests

Plans can define required tests in their `## Required Tests` section. The `check_plan_tests.py` script validates these.

### Skipping E2E for specific plan types

For documentation-only or process plans:
```bash
python scripts/complete_plan.py --plan N --skip-e2e
```

## Limitations

- **Not a substitute for thorough testing** - Smoke tests catch crashes, not subtle bugs
- **Requires test infrastructure** - You need working tests first
- **Can be bypassed** - Determined users can edit files manually (git history shows this)
- **Doesn't verify correctness** - Only verifies that tests pass, not that implementation is right

## Integration with Other Patterns

| Pattern | Integration |
|---------|-------------|
| Plan Workflow | Verification is the final step |
| Claim System | Release claim only after verification |
| Git Hooks | Could add pre-commit check for unverified completions |
| Doc-Code Coupling | Verification includes coupling check |

## Origin

Emerged from agent_ecology after multiple "complete" plans were found to have failing tests. The cost of late integration testing exceeded the overhead of mandatory verification.

---


## 18. Claim System

*Source: `docs/meta/18_claim-system.md`*


## Problem

When multiple AI instances (or developers) work in parallel:
- Two instances start the same work
- Neither knows the other is working
- Merge conflicts, wasted effort, confusion

## Solution: Structured Scope Claims

Claims must specify a **scope** - either a plan number or a feature name:

```bash
# Claim a feature (recommended for most work)
python scripts/check_claims.py --claim --feature ledger --task "Fix transfer bug"

# Claim a plan (for gap implementations)
python scripts/check_claims.py --claim --plan 3 --task "Docker isolation"

# Claim both (for plan work that touches specific features)
python scripts/check_claims.py --claim --feature escrow --plan 8 --task "Agent rights"
```

**Scopes are mutually exclusive** - if CC-2 claims `--feature ledger`, CC-3 cannot claim the same feature until CC-2 releases.

## Scope Types

| Scope | Source | Example |
|-------|--------|---------|
| **Feature** | `features/*.yaml` | `--feature ledger`, `--feature escrow` |
| **Plan** | `docs/plans/*.md` | `--plan 3`, `--plan 21` |

### Feature Scopes

Features are defined in `features/*.yaml`. Each feature lists its code files:

```yaml
# features/ledger.yaml
feature: ledger
code:
  - src/world/ledger.py
  - src/world/rate_tracker.py
```

When you claim `--feature ledger`, you're claiming ownership of those files.

### Plan Scopes

Plans are numbered implementation tasks in `docs/plans/`. Claiming `--plan 3` means you're working on Plan #3.

## Commands

### List available features

```bash
python scripts/check_claims.py --list-features

# Output:
# Available features:
#   - contracts
#   - escrow
#   - ledger
#   - meta-process-tooling
# Files mapped to features: 9
```

### Claim work

```bash
# Feature claim (recommended)
python scripts/check_claims.py --claim --feature ledger --task "Fix transfer bug"

# Plan claim
python scripts/check_claims.py --claim --plan 3 --task "Docker isolation"

# Both
python scripts/check_claims.py --claim --feature escrow --plan 8 --task "Agent rights"
```

### Check for conflicts before claiming

```bash
# List current claims to see what's taken
python scripts/check_claims.py --list
```

### Check if files are covered by claims

```bash
# CI mode - verify files are claimed
python scripts/check_claims.py --check-files src/world/ledger.py src/world/executor.py

# Output if unclaimed:
# ❌ Files not covered by claims:
#   - src/world/ledger.py
# To fix, claim the feature that owns these files:
#   python scripts/check_claims.py --claim --feature ledger --task '...'
```

### Release claim

```bash
python scripts/check_claims.py --release

# With TDD validation
python scripts/check_claims.py --release --validate
```

### CI verification

```bash
# Verify current branch has a claim
python scripts/check_claims.py --verify-claim
```

## Enforcement

### At Claim Time

When you claim, the system blocks if:
- **Same plan** is already claimed by another instance
- **Same feature** is already claimed by another instance

```bash
$ python scripts/check_claims.py --claim --feature ledger --task "My work"

============================================================
❌ SCOPE CONFLICT - CLAIM BLOCKED
============================================================

  Feature 'ledger' already claimed by: other-branch
  Their task: Fix transfer bug

------------------------------------------------------------
Each plan/feature can only be claimed by one instance.
Coordinate with the other instance before proceeding.

Use --force to claim anyway (NOT recommended).
```

### In CI

CI checks that PR branches were claimed. Currently informational, will become strict.

## Files

| File | Purpose |
|------|---------|
| `.claude/active-work.yaml` | Machine-readable claim storage |
| `CLAUDE.md` | Human-readable Active Work table |
| `scripts/check_claims.py` | Claim management script |
| `features/*.yaml` | Feature definitions with code mappings |

## Workflow

1. **Check what's claimed**: `python scripts/check_claims.py --list`
2. **Check available features**: `python scripts/check_claims.py --list-features`
3. **Claim your scope**: `python scripts/check_claims.py --claim --feature NAME --task "..."`
4. **Create worktree**: `make worktree BRANCH=my-feature`
5. **Do work**: Edit files in the claimed feature's scope
6. **Release**: `python scripts/check_claims.py --release`

## Best Practices

1. **Always specify a scope** - Use `--feature` or `--plan` when claiming
2. **Check claims first** - `--list` before starting any work
3. **One scope at a time** - Don't claim more than you need
4. **Release promptly** - Don't hold claims overnight
5. **Use features for code work** - Plans are for gap implementations

## Special Scopes

### Shared Scope

Cross-cutting files that many features use (config, fixtures, types) are in the `shared` scope:

```yaml
# features/shared.yaml
feature: shared
code:
  - src/config.py
  - tests/conftest.py
  - tests/fixtures/
```

**Shared files have no claim conflicts** - any plan can modify them without claiming the shared feature. This prevents false conflicts on common infrastructure.

### Trivial Changes

Changes with `[Trivial]` prefix don't require claims:
- Typo fixes
- Comment updates
- Formatting changes
- Changes < 20 lines not touching `src/`

```bash
git commit -m "[Trivial] Fix typo in README"
# No plan or claim required
```

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Claim granularity | **Feature-level** | File-level is over-restrictive; git handles merges fine. Feature-level prevents duplicate work without blocking valid parallel changes. |
| File lists in plans | **Not required** | Impractical to maintain; files derived from feature's `code:` section instead. |
| Shared scope | **No claim conflicts** | Cross-cutting files shouldn't block anyone; tests are the quality gate. |
| Trivial exemption | **`[Trivial]` prefix** | Reduces friction for tiny fixes; CI validates size limits. |

**Evidence considered:**
- DORA research: deployment frequency > process rigor
- Trunk-based development: small changes + trust git
- Google/Spotify: anyone can modify common code, tests are the gate

## Limitations

- **CI check is informational** - Currently warns but doesn't block (will be strict later)
- **Force override exists** - `--force` can bypass conflicts (for emergencies only)
- **Files outside features** - Files not in any `features/*.yaml` aren't tracked
- **Shared scope honor system** - Anyone can modify shared files; abuse visible in git history

## See Also

- [Worktree Enforcement](19_worktree-enforcement.md) - Worktree + claim workflow
- [PR Coordination](21_pr-coordination.md) - PR workflow with claims
- [Plan Workflow](15_plan-workflow.md) - Plans that claims reference
- [Feature-Driven Development](13_feature-driven-development.md) - Feature definitions

---


## 19. Worktree Enforcement

*Source: `docs/meta/19_worktree-enforcement.md`*


## Problem

Multiple Claude Code instances working in the same directory causes:
- Uncommitted changes from one instance overwritten by another
- Branch switches mid-edit
- Merge conflicts from parallel uncommitted work
- Lost work when instances don't coordinate

Git worktrees solve this by giving each instance its own working directory, but there's no enforcement - instances can still accidentally edit the main directory.

## Solution

Two-part enforcement:

1. **`make worktree` requires claiming** - The worktree creation script prompts for task description and plan number, creating a claim before the worktree. This ensures all instances can see what others are working on.

2. **PreToolUse hook blocks edits in main** - A hook blocks Edit/Write operations when the target file is in the main repository directory (not a worktree).

## Creating a Worktree (with mandatory claim)

```bash
make worktree
```

This runs an interactive script that:
1. Shows existing claims
2. Prompts for task description (required)
3. Prompts for plan number (optional)
4. Suggests branch name based on plan
5. Creates the claim
6. Creates the worktree

See [Claim System](18_claim-system.md) for details on the claim system.

## Hook-Based Enforcement

The PreToolUse hook blocks Edit/Write operations in the main directory.

### Files

| File | Purpose |
|------|---------|
| `.claude/settings.json` | Hook configuration |
| `.claude/hooks/protect-main.sh` | Script that checks file paths and blocks if in main |

## Setup

1. **Create hooks directory:**
   ```bash
   mkdir -p .claude/hooks
   ```

2. **Create the protection script** (`.claude/hooks/protect-main.sh`):
   ```bash
   #!/bin/bash
   MAIN_DIR="/path/to/your/main/repo"

   INPUT=$(cat)
   FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

   if [[ -z "$FILE_PATH" ]]; then
       exit 0
   fi

   if [[ "$FILE_PATH" == "$MAIN_DIR"/* ]]; then
       echo "BLOCKED: Cannot edit files in main directory" >&2
       echo "Create a worktree: git worktree add ../feature -b feature" >&2
       exit 2
   fi

   exit 0
   ```

3. **Make it executable:**
   ```bash
   chmod +x .claude/hooks/protect-main.sh
   ```

4. **Create settings.json** (`.claude/settings.json`):
   ```json
   {
     "hooks": {
       "PreToolUse": [
         {
           "matcher": "Edit|Write",
           "hooks": [
             {
               "type": "command",
               "command": "bash .claude/hooks/protect-main.sh",
               "timeout": 5000
             }
           ]
         }
       ]
     }
   }
   ```

5. **Update .gitignore** to track these files:
   ```
   # Track enforcement hooks
   !.claude/settings.json
   !.claude/hooks/
   ```

## Usage

Once installed, Claude Code instances in the main directory will see:

```
BLOCKED: Cannot edit files in main directory (/path/to/repo)

You're in the main directory. Create a worktree first:
  make worktree BRANCH=plan-NN-description

Or use an existing worktree:
  make worktree-list
```

The Edit/Write operation will be blocked, forcing the instance to use a worktree.

## Coordination Files (Whitelisted)

The hook allows editing **coordination files** even in main directory:

| Pattern | Files | Why Allowed |
|---------|-------|-------------|
| `*/.claude/*` | `.claude/active-work.yaml` | Claims tracking |
| `CLAUDE.md` | All `CLAUDE.md` files | Coordination tables, plan status |

This enables the "Reviews, quick reads, coordination only" workflow in main while blocking implementation work.

## Customization

**Change the main directory path:**
Edit `MAIN_DIR` in `protect-main.sh` to match your repository location.

**Add more exceptions:**
Add patterns to skip enforcement for specific files:
```bash
# Example: Allow a specific config file
if [[ "$BASENAME" == "special-config.yaml" ]]; then
    exit 0
fi
```

**Different branch naming:**
Adjust the error message to match your branch naming convention.

## Limitations

- **Requires jq:** The script uses `jq` to parse JSON input
- **Path-based only:** Detects main vs worktree by path, not git internals
- **Per-project:** Must configure `MAIN_DIR` for each project
- **Read operations allowed:** Only blocks Edit/Write, not Read (intentional - reviewing main is fine)
- **Bash operations allowed:** Doesn't block shell commands (could add if needed)

## Related Patterns

- [Rebase Workflow](20_rebase-workflow.md) - Keeps worktrees up-to-date before creating PRs
- [Claim System](18_claim-system.md) - Coordinates which instance works on what
- [Git Hooks](06_git-hooks.md) - Pre-commit validation before pushing
- [PR Coordination](21_pr-coordination.md) - Tracks review requests across instances

---


## 20. Rebase Workflow

*Source: `docs/meta/20_rebase-workflow.md`*


## Problem

When multiple Claude Code instances work in parallel using worktrees:

1. Worktree A is created from `main` at commit X
2. Worktree B is created, does work, creates PR, merges to `main` (now at commit Y)
3. Worktree A creates PR but:
   - PR is based on outdated commit X
   - May conflict with changes from B
   - Merging may accidentally revert B's work
   - CLAUDE.md or other shared files appear "reverted"

This isn't actually a revert - it's that A's branch never had B's changes.

## Solution

Three-part solution:

1. **Start fresh**: `make worktree` auto-fetches and bases on latest `origin/main`
2. **Before PR**: `make pr-ready` rebases onto current `origin/main` and pushes safely
3. **GitHub enforcement**: Branch protection requires PRs to be up-to-date before merge

### GitHub Branch Protection (Enforcement)

Branch protection on `main` with `strict: true` means GitHub will **block merge** if your branch is behind `origin/main`. This catches cases where developers forget to run `make pr-ready`.

```bash
# Check current protection settings
gh api repos/OWNER/REPO/branches/main/protection --jq '.required_status_checks.strict'
# Should return: true

# Enable if not set (requires admin)
gh api repos/OWNER/REPO/branches/main/protection -X PUT --input - <<'EOF'
{
  "required_status_checks": {"strict": true, "contexts": ["test"]},
  "enforce_admins": false,
  "required_pull_request_reviews": null,
  "restrictions": null
}
EOF
```

When strict mode is enabled, GitHub shows "This branch is out-of-date with the base branch" and the merge button is disabled until you rebase.

## Files

| File | Purpose |
|------|---------|
| `Makefile` | `worktree`, `rebase`, `pr-ready` targets |
| `CLAUDE.md` | Workflow documentation (step 6) |

## Setup

The targets are already in the Makefile:

```makefile
worktree:  ## Create worktree for parallel CC work (usage: make worktree BRANCH=feature-name)
	@if [ -z "$(BRANCH)" ]; then echo "Usage: make worktree BRANCH=feature-name"; exit 1; fi
	git fetch origin
	git worktree add ../ecology-$(BRANCH) -b $(BRANCH) origin/main
	@echo ""
	@echo "Worktree created at ../ecology-$(BRANCH) (based on latest origin/main)"
	@echo "To use: cd ../ecology-$(BRANCH) && claude"
	@echo "To remove when done: git worktree remove ../ecology-$(BRANCH)"

rebase:  ## Rebase current branch onto latest origin/main
	git fetch origin
	git rebase origin/main

pr-ready:  ## Rebase and push (run before creating PR)
	git fetch origin
	git rebase origin/main
	git push --force-with-lease
```

## Usage

### Creating a Worktree (Always Fresh)

```bash
# In main directory
make worktree BRANCH=plan-03-docker

# Automatically:
# 1. Fetches latest from remote
# 2. Creates worktree based on origin/main (not local main)
# 3. Shows path and usage instructions
```

### Before Creating PR

```bash
# In your worktree
make pr-ready

# Automatically:
# 1. Fetches latest from remote
# 2. Rebases your branch onto origin/main
# 3. Pushes with --force-with-lease (safe force push)
```

### Just Rebase (No Push)

```bash
# In your worktree
make rebase

# Rebases but doesn't push - useful for:
# - Checking for conflicts before you're ready
# - Getting latest changes during long-running work
```

## Conflict Resolution

If rebase finds conflicts:

```bash
# 1. Git will stop and show conflicted files
Auto-merging CLAUDE.md
CONFLICT (content): Merge conflict in CLAUDE.md

# 2. Fix conflicts in your editor
# Look for <<<<<<< HEAD, =======, >>>>>>> markers

# 3. Stage resolved files
git add CLAUDE.md

# 4. Continue rebase
git rebase --continue

# 5. If you want to abort and try again later
git rebase --abort
```

### Common Conflict Scenarios

| Scenario | Resolution |
|----------|------------|
| CLAUDE.md Active Work table | Keep remote's table, add your entry |
| Same file modified | Keep both changes if independent, merge if overlapping |
| File deleted vs modified | Usually keep the modification |

## Understanding `--force-with-lease`

Regular `git push --force` overwrites remote unconditionally. This is dangerous if someone else pushed while you were rebasing.

`--force-with-lease` is safer:
- Checks that remote ref hasn't changed since you fetched
- If someone else pushed in between, it fails instead of overwriting
- You then fetch again, rebase, and retry

```bash
# Safe: fails if remote changed
git push --force-with-lease

# Dangerous: overwrites unconditionally (avoid)
git push --force
```

## Workflow Integration

The full workflow from CLAUDE.md:

1. **Claim** - `make claim TASK="..." PLAN=N`
2. **Worktree** - `make worktree BRANCH=plan-NN-description` (auto-fetches)
3. **Update plan status** - Mark "In Progress"
4. **Implement** - Do work, write tests first (TDD)
5. **Verify** - Run all checks
6. **Rebase** - `make pr-ready` (rebase onto latest main, push)
7. **PR** - Create PR from worktree
8. **Review** - Another CC instance reviews
9. **Complete** - Merge PR, remove worktree

Step 6 is critical for preventing "reverted" changes.

## Limitations

- **Requires conflict resolution skills** - Rebasing can produce conflicts that need manual resolution
- **Force push required** - After rebase, history changes, requiring force push
- **Not for shared branches** - Only use for personal feature branches, never for branches others are working on

## Related Patterns

- [Worktree Enforcement](19_worktree-enforcement.md) - Blocks edits in main directory
- [PR Coordination](21_pr-coordination.md) - Tracks PRs and claims
- [Claim System](18_claim-system.md) - Coordinates which instance works on what

---


## 21. PR Coordination

*Source: `docs/meta/21_pr-coordination.md`*


## Problem

When multiple AI instances (or humans) work in parallel, PRs get created but:
- Other instances don't know a PR needs review
- Work tracking tables (Active Work) don't get updated
- After merge, cleanup doesn't happen (stale claims remain)

## Solution

1. GitHub Action triggers on PR events (open, close, merge)
2. Automatically updates coordination files (Active Work table, claims)
3. Extracts plan number from PR title `[Plan #N]` for tracking
4. Surfaces review requests visibly

## Files

| File | Purpose |
|------|---------|
| `.github/workflows/pr-coordination.yml` | GitHub Action workflow |
| `scripts/check_claims.py` | Claim management script |
| `.claude/active-work.yaml` | Machine-readable claim storage |
| `CLAUDE.md` | Active Work table (human-readable) |

## Setup

### 1. Create the workflow

```yaml
# .github/workflows/pr-coordination.yml
name: PR Coordination

on:
  pull_request:
    types: [opened, closed, reopened]

permissions:
  contents: write
  pull-requests: read

jobs:
  update-coordination:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: pip install pyyaml

      - name: Extract plan number from PR title
        id: extract
        run: |
          TITLE="${{ github.event.pull_request.title }}"
          if [[ "$TITLE" =~ \[Plan\ #([0-9]+)\] ]]; then
            echo "plan_number=${BASH_REMATCH[1]}" >> $GITHUB_OUTPUT
            echo "has_plan=true" >> $GITHUB_OUTPUT
          else
            echo "has_plan=false" >> $GITHUB_OUTPUT
          fi

      - name: Handle PR opened
        if: github.event.action == 'opened'
        run: |
          # Claim work for this PR
          python scripts/check_claims.py --claim \
            --task "PR #${{ github.event.pull_request.number }}: ${{ github.event.pull_request.title }}" \
            ${{ steps.extract.outputs.has_plan == 'true' && format('--plan {0}', steps.extract.outputs.plan_number) || '' }}

      - name: Handle PR merged
        if: github.event.action == 'closed' && github.event.pull_request.merged
        run: |
          # Release claim and mark plan complete if applicable
          python scripts/check_claims.py --release
          if [ "${{ steps.extract.outputs.has_plan }}" == "true" ]; then
            # Update plan status to complete
            python scripts/sync_plan_status.py --plan ${{ steps.extract.outputs.plan_number }} --status complete
          fi

      - name: Handle PR closed without merge
        if: github.event.action == 'closed' && !github.event.pull_request.merged
        run: |
          # Just release the claim
          python scripts/check_claims.py --release

      - name: Commit coordination updates
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add -A
          git diff --staged --quiet || git commit -m "[Automated] Update coordination for PR #${{ github.event.pull_request.number }}"
          git push
```

### 2. Create the claims script

```python
#!/usr/bin/env python3
"""Manage work claims."""

import argparse
import yaml
from pathlib import Path
from datetime import datetime

CLAIMS_FILE = Path(".claude/active-work.yaml")

def load_claims() -> dict:
    if CLAIMS_FILE.exists():
        return yaml.safe_load(CLAIMS_FILE.read_text()) or {"claims": []}
    return {"claims": []}

def save_claims(data: dict) -> None:
    CLAIMS_FILE.parent.mkdir(exist_ok=True)
    CLAIMS_FILE.write_text(yaml.dump(data, default_flow_style=False))

def claim(task: str, plan: int | None = None) -> None:
    data = load_claims()
    data["claims"].append({
        "task": task,
        "plan": plan,
        "claimed_at": datetime.now().isoformat(),
        "status": "in_progress"
    })
    save_claims(data)
    print(f"Claimed: {task}")

def release() -> None:
    data = load_claims()
    if data["claims"]:
        released = data["claims"].pop()
        save_claims(data)
        print(f"Released: {released['task']}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--claim", action="store_true")
    parser.add_argument("--release", action="store_true")
    parser.add_argument("--task", type=str)
    parser.add_argument("--plan", type=int)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    if args.claim:
        claim(args.task, args.plan)
    elif args.release:
        release()
    elif args.list:
        data = load_claims()
        for c in data["claims"]:
            print(f"- {c['task']} (claimed {c['claimed_at']})")

if __name__ == "__main__":
    main()
```

### 3. Create the claims file

```yaml
# .claude/active-work.yaml
claims: []
```

### 4. Add Active Work table to CLAUDE.md

```markdown
## Active Work

| Instance | Task | Plan | Claimed | Status |
|----------|------|------|---------|--------|
| - | - | - | - | - |
```

## Usage

### Automatic (via GitHub Actions)

1. **Create PR with plan link**: `[Plan #3] Implement feature X`
2. **On PR open**: Workflow claims work, updates Active Work table
3. **On PR merge**: Workflow releases claim, marks plan complete
4. **On PR close (no merge)**: Workflow releases claim

### Manual (when needed)

```bash
# Claim work
python scripts/check_claims.py --claim --task "Working on feature X" --plan 3

# List active claims
python scripts/check_claims.py --list

# Release claim
python scripts/check_claims.py --release

# Check for stale claims (>4 hours old)
python scripts/check_claims.py

# Clean up old completed entries
python scripts/check_claims.py --cleanup
```

### PR Title Convention

```
[Plan #N] Short description    # Links to plan, enables auto-tracking
[Unplanned] Short description  # No plan link, still tracked
Fix typo in readme             # No tracking (discouraged)
```

## Merging PRs

### Check if approval is required

```bash
# Check branch protection
gh api repos/OWNER/REPO/branches/main/protection 2>&1 | grep -q "not protected" && echo "No approval required"
```

### Merge workflow

| Branch Protection | Review Process | Merge Command |
|-------------------|----------------|---------------|
| None | Comment review, then merge | `gh pr merge N --squash --delete-branch` |
| Requires approval | Need different user to approve | `gh pr review N --approve` (then merge) |
| Requires CI | Wait for checks to pass | `gh pr merge N --auto --squash` |

**Common pattern (no branch protection):**
```bash
# 1. Review with comment (can't approve own PR)
gh pr review 46 --comment --body "LGTM - reviewed changes"

# 2. Merge directly
gh pr merge 46 --squash --delete-branch
```

**Note:** GitHub always blocks self-approval (`--approve` on your own PR), but if branch protection doesn't require approval, you can still merge directly.

## Customization

### Change stale threshold

```python
STALE_HOURS = 4  # Claims older than this are flagged
```

### Add Slack/Discord notification

```yaml
- name: Notify on PR open
  if: github.event.action == 'opened'
  run: |
    curl -X POST ${{ secrets.SLACK_WEBHOOK }} \
      -d '{"text": "PR needs review: ${{ github.event.pull_request.html_url }}"}'
```

### Require plan number

```yaml
- name: Validate PR title
  if: github.event.action == 'opened'
  run: |
    TITLE="${{ github.event.pull_request.title }}"
    if [[ ! "$TITLE" =~ \[Plan\ #[0-9]+\] ]] && [[ ! "$TITLE" =~ \[Unplanned\] ]]; then
      echo "PR title must include [Plan #N] or [Unplanned]"
      exit 1
    fi
```

## Limitations

- **GitHub-specific** - Uses GitHub Actions. Adapt for GitLab CI, etc.
- **Race conditions** - If two PRs merge simultaneously, coordination file may conflict.
- **Token permissions** - Needs `contents: write` to push updates.
- **Branch protection** - May conflict with protected branches requiring reviews.

## See Also

- [Claim system pattern](18_claim-system.md) - More detailed claim management
- [Plan workflow pattern](15_plan-workflow.md) - How plans integrate with PRs

---


## 22. Human Review Pattern

*Source: `docs/meta/22_human-review-pattern.md`*


## Problem

AI agents can run automated tests, but some things require human verification:
- Visual correctness (dashboards, charts, UI)
- User experience quality
- Integration with external systems the agent can't access
- Subjective quality judgments

Without a formal process, agents may declare work "complete" when they can only verify part of it.

## Solution

Plans can specify a `## Human Review Required` section that:
1. Lists specific items a human must verify
2. Provides step-by-step instructions
3. Blocks automated completion until human confirms

## Plan Format

Add this section to any plan requiring human verification:

```markdown
## Human Review Required

Before marking complete, a human must verify:
- [ ] Dashboard loads at http://localhost:8080
- [ ] Charts render correctly with sample data
- [ ] Navigation between tabs works
- [ ] Responsive layout on mobile viewport

**To verify:**
1. Run `python run.py --dashboard`
2. Open http://localhost:8080 in browser
3. Check each item above
4. Confirm with: `python scripts/complete_plan.py --plan NN --human-verified`
```

## How It Works

### During Automated Completion

When `complete_plan.py` runs on a plan with human review:

1. Runs all automated tests first (unit, E2E, doc-coupling)
2. Detects `## Human Review Required` section
3. Prints the checklist and instructions
4. Exits without marking complete
5. Requires `--human-verified` flag to proceed

```bash
$ python scripts/complete_plan.py --plan 40

============================================================
Completing Plan #40
============================================================
...
============================================================
HUMAN REVIEW REQUIRED
============================================================

Plan #40 requires manual verification before completion.

From 40_dashboard.md:
----------------------------------------
Before marking complete, a human must verify:
- [ ] Dashboard loads at http://localhost:8080
- [ ] Charts render correctly with sample data
...
----------------------------------------

After verifying all items above, run:

  python scripts/complete_plan.py --plan 40 --human-verified

This confirms a human has checked things automated tests cannot verify.

❌ Cannot complete: human review required but --human-verified not provided
```

### After Human Verification

Once a human has verified the checklist:

```bash
$ python scripts/complete_plan.py --plan 40 --human-verified

============================================================
Completing Plan #40
============================================================
...
  (--human-verified: human review confirmed)

[1/3] Running unit tests...
    PASSED: ...

✅ Plan #40 marked COMPLETE
```

## When to Use

Add human review when the plan involves:

| Category | Examples |
|----------|----------|
| **Visual** | Dashboards, charts, CSS styling, responsive design |
| **UX** | Navigation flows, form usability, error messages |
| **External** | Third-party API integrations, email delivery |
| **Subjective** | Documentation quality, naming conventions |

## When NOT to Use

Skip human review for:
- Pure backend logic (testable with unit tests)
- API contracts (testable with integration tests)
- Data transformations (testable with property tests)
- CLI tools (testable with E2E tests)

## Best Practices

1. **Be specific** - List exact URLs, commands, and expected outcomes
2. **Keep it short** - 3-5 items max, human attention is limited
3. **Include setup** - Tell the human how to run/access the feature
4. **Chain items** - Order matters for verification steps

## Example: Dashboard Plan

```markdown
# Plan #40: Agent Balance Dashboard

**Status:** 🚧 In Progress

## Problem
Need to visualize agent balances over time.

## Required Tests
- tests/unit/test_dashboard.py::test_data_endpoint
- tests/integration/test_dashboard.py::test_server_starts

## Human Review Required

Before marking complete, a human must verify:
- [ ] Dashboard loads at http://localhost:8080
- [ ] Balance chart shows correct agent data
- [ ] Legend toggles work to show/hide agents
- [ ] Timerange selector updates the chart

**To verify:**
1. Start simulation: `python run.py --agents 3 --ticks 10`
2. Start dashboard: `python -m src.dashboard.server`
3. Open http://localhost:8080
4. Verify each checkbox above
5. Confirm: `python scripts/complete_plan.py --plan 40 --human-verified`

## Solution
...
```

## Related

- [Verification Enforcement](17_verification-enforcement.md) - Overall completion requirements
- [Plan Workflow](15_plan-workflow.md) - Full plan lifecycle
- [Testing Strategy](03_testing-strategy.md) - Test types and when to use each

---

