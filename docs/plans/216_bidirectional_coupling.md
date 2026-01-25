# Plan 216: Bidirectional Coupling Checks

**Status:** Planned
**Phase:** 1 of 5 (Meta-Process Improvements)
**Depends on:** Plan #215 (Unified Documentation Graph) - Complete
**Blocked by:** None

## Problem

Currently our doc-coupling checks are unidirectional: when code changes, we prompt about docs. But we don't check the reverse: when docs change, we should prompt about related code. Similarly for ADRs.

This means:
- Docs can drift from code without any warning
- ADRs can become stale without surfacing affected code
- The coupling enforcement is incomplete

## Solution

Extend existing scripts to check bidirectionally using `relationships.yaml`:

```
Code changes  →  Surface related docs + ADRs
Doc changes   →  Surface related code + ADRs
ADR changes   →  Surface governed code + related docs
```

## Implementation

### 1. Extend `check_doc_coupling.py`

Add `--reverse` or `--bidirectional` mode:
- Given a list of changed files (from git diff)
- For each changed file, find all related nodes in the graph
- Report: "You changed X, consider updating: Y, Z"

```python
def get_related_nodes(changed_file: Path, relationships: dict) -> list[str]:
    """Find all nodes related to changed_file in any direction."""
    related = []

    # Check couplings (source → doc)
    for coupling in relationships.get("couplings", []):
        sources = coupling.get("sources", [])
        docs = coupling.get("docs", [])
        if str(changed_file) in sources:
            related.extend(docs)
        if str(changed_file) in docs:
            related.extend(sources)

    # Check governance (source → ADR)
    for entry in relationships.get("governance", []):
        if entry.get("source") == str(changed_file):
            for adr in entry.get("adrs", []):
                related.append(f"docs/adr/{adr:04d}_*.md")

    # Check if changed file is an ADR
    if "docs/adr/" in str(changed_file):
        adr_num = extract_adr_number(changed_file)
        for entry in relationships.get("governance", []):
            if adr_num in entry.get("adrs", []):
                related.append(entry.get("source"))

    return related
```

### 2. Create pre-commit hook integration

Update pre-commit to run bidirectional check on staged files:
```bash
# In pre-commit hook
python scripts/check_doc_coupling.py --bidirectional --files $(git diff --cached --name-only)
```

### 3. Add `--suggest-all` mode

Given any file, show the full relationship graph for that file:
```bash
$ python scripts/check_doc_coupling.py --suggest-all src/world/contracts.py

Related to src/world/contracts.py:
  ADRs:
    - docs/adr/0001_scrip_system.md (governs)
    - docs/adr/0003_permission_model.md (governs)
  Docs:
    - docs/architecture/current/contract_system.md (coupled)
  Context:
    "Permission checks are the hot path. Changes here affect all
     contract invocations. See ADR-0003 for permission model."
```

## Test Plan

### Unit Tests
```python
# tests/unit/test_bidirectional_coupling.py

def test_code_change_surfaces_related_docs():
    """Changing runner.py should surface execution_model.md"""

def test_doc_change_surfaces_related_code():
    """Changing execution_model.md should surface runner.py, world.py"""

def test_adr_change_surfaces_governed_code():
    """Changing ADR-0003 should surface contracts.py, escrow.py"""

def test_symmetric_relationship():
    """If A relates to B, then B relates to A"""

def test_suggest_all_shows_full_graph():
    """--suggest-all shows ADRs, docs, and context"""
```

### Integration Tests
```python
def test_bidirectional_on_real_repo():
    """Run bidirectional check on actual staged changes"""

def test_pre_commit_integration():
    """Pre-commit hook runs bidirectional check"""
```

## Acceptance Criteria

- [ ] `check_doc_coupling.py --bidirectional` works
- [ ] Code→Doc, Doc→Code, ADR→Code, Code→ADR all checked
- [ ] `--suggest-all` shows full relationship graph for any file
- [ ] Pre-commit hook integration documented
- [ ] Unit tests pass
- [ ] Integration tests pass

## Files to Modify

- `scripts/check_doc_coupling.py` - Add bidirectional logic
- `scripts/setup_hooks.sh` - Update pre-commit hook
- `tests/unit/test_bidirectional_coupling.py` - New test file
- `scripts/CLAUDE.md` - Document new options

## Ambiguities

None - this is a straightforward extension of existing functionality.
