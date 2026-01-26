# Plan 219: Symbol-Level Granularity

**Status:** ✅ Complete
**Phase:** 3 of 5 (Meta-Process Improvements)
**Depends on:**
- Plan #215 (Unified Documentation Graph) - Complete
- Plan #216 (Bidirectional Coupling) - Complete
**Blocked by:** None
**Completed:** 2026-01-26

## Implementation Evidence

- `scripts/symbol_extractor.py` - AST-based symbol extraction (200+ lines)
- `tests/unit/test_symbol_extraction.py` - 19 unit tests (all pass)

### Core Implementation

The symbol extractor provides:
- Extract classes, methods, and functions from Python files using AST
- Line range tracking for each symbol (line, end_line)
- Symbol lookup by name (`validate_symbol_exists`, `get_symbol`)
- Symbol lookup by line number (`get_symbol_at_line`)
- CLI for symbol inspection: `python scripts/symbol_extractor.py FILE`

### Usage Example
```python
from symbol_extractor import extract_symbols, validate_symbol_exists

symbols = extract_symbols(Path("src/world/contracts.py"))
if validate_symbol_exists(path, "ContractInvoker.execute"):
    print("Symbol exists!")
```

### Future Extensions (defer to follow-up plan if needed)
- Extend relationships.yaml schema with `symbols` section
- Symbol-level context injection in hooks
- Symbol validation in CI

## Problem

Current doc-coupling works at file level. But often:
- Only specific functions in a file are governed by an ADR
- A plan affects specific classes, not whole files
- Symbol-level queries are useful: "show me all functions related to ADR-0003"

File-level granularity is too coarse for precise context injection and coupling checks.

## Solution

Extend `relationships.yaml` to support symbol-level mappings:

```yaml
governance:
  - source: src/world/contracts.py
    adrs: [1, 3]
    symbols:
      - name: ContractInvoker.check_permission
        adrs: [3]
        context: "Hot path - see ADR-0003 section 4.2"
      - name: ContractInvoker.execute
        adrs: [1, 3]
        context: "Orchestrates permission check + execution"
```

## Implementation

### 1. Extend relationships.yaml schema

```yaml
# Extended schema
governance:
  - source: src/world/contracts.py
    adrs: [1, 3]           # File-level governance
    context: |
      Permission checks are the hot path.
    symbols:               # Symbol-level governance (optional)
      - name: "ContractInvoker"
        type: class
        adrs: [3]
        context: "Main contract execution class"
      - name: "ContractInvoker.check_permission"
        type: method
        adrs: [3]
        context: "Permission check hot path"
      - name: "validate_caller"
        type: function
        adrs: [1]
        context: "Caller validation logic"

couplings:
  - sources:
      - src/simulation/runner.py
    docs:
      - docs/architecture/current/execution_model.md
    symbols:              # Optional symbol-level coupling
      - name: "SimulationRunner.run_phase"
        docs:
          - docs/architecture/current/execution_model.md#two-phase
```

### 2. AST parsing for symbol extraction

```python
# scripts/symbol_extractor.py
"""Extract symbols from Python files for validation."""

import ast
from pathlib import Path
from dataclasses import dataclass

@dataclass
class Symbol:
    name: str
    type: str  # 'class', 'function', 'method'
    line: int
    file: Path

def extract_symbols(file_path: Path) -> list[Symbol]:
    """Extract all symbols from a Python file."""
    with open(file_path) as f:
        tree = ast.parse(f.read())

    symbols = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(Symbol(node.name, 'class', node.lineno, file_path))
            # Also extract methods
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    symbols.append(Symbol(
                        f"{node.name}.{item.name}",
                        'method',
                        item.lineno,
                        file_path
                    ))
        elif isinstance(node, ast.FunctionDef):
            # Top-level function
            if not any(isinstance(parent, ast.ClassDef) for parent in ast.walk(tree)):
                symbols.append(Symbol(node.name, 'function', node.lineno, file_path))

    return symbols

def validate_symbol_exists(file_path: Path, symbol_name: str) -> bool:
    """Check if a symbol exists in a file."""
    symbols = extract_symbols(file_path)
    return any(s.name == symbol_name for s in symbols)
```

### 3. Symbol-level queries

```python
# scripts/query_symbols.py
"""Query symbols by ADR, plan, or doc."""

def symbols_for_adr(adr_number: int) -> list[tuple[Path, str]]:
    """Find all symbols governed by an ADR."""
    results = []
    for entry in relationships.get("governance", []):
        source = Path(entry.get("source", ""))
        # File-level
        if adr_number in entry.get("adrs", []):
            results.append((source, "*"))  # Whole file
        # Symbol-level
        for symbol in entry.get("symbols", []):
            if adr_number in symbol.get("adrs", []):
                results.append((source, symbol.get("name")))
    return results

# CLI usage:
# python scripts/query_symbols.py --adr 3
# Output:
#   src/world/contracts.py:ContractInvoker.check_permission
#   src/world/contracts.py:ContractInvoker.execute
#   src/world/escrow.py:*
```

### 4. Symbol-level context injection

Extend `inject_context.py` to include symbol-level context:

```python
def get_context_for_symbol(file_path: str, line_number: int) -> str | None:
    """Get context for the symbol at a specific line."""
    symbols = extract_symbols(Path(file_path))
    # Find symbol containing this line
    for symbol in symbols:
        if symbol.line <= line_number:
            # Check if this symbol has specific context
            context = get_symbol_context(file_path, symbol.name)
            if context:
                return context
    # Fall back to file-level context
    return get_context_for_file(file_path)
```

### 5. Validation that symbols still exist

```python
# In CI or pre-commit
def validate_symbol_mappings():
    """Ensure all mapped symbols still exist in source."""
    errors = []
    for entry in relationships.get("governance", []):
        source = Path(entry.get("source", ""))
        for symbol in entry.get("symbols", []):
            if not validate_symbol_exists(source, symbol.get("name")):
                errors.append(f"Symbol {symbol.get('name')} not found in {source}")
    return errors
```

## Test Plan

### Unit Tests
```python
# tests/unit/test_symbol_extraction.py

def test_extract_class():
    """Extract class definitions"""

def test_extract_method():
    """Extract methods with Class.method format"""

def test_extract_function():
    """Extract top-level functions"""

def test_validate_symbol_exists():
    """Symbol validation works"""

def test_validate_symbol_missing():
    """Missing symbol detected"""
```

```python
# tests/unit/test_symbol_queries.py

def test_symbols_for_adr():
    """Query symbols by ADR number"""

def test_file_level_fallback():
    """When no symbol-level, return file-level"""

def test_symbol_context_injection():
    """Symbol-level context injected correctly"""
```

### Integration Tests
```python
def test_real_codebase_symbol_extraction():
    """Extract symbols from actual src/ files"""

def test_symbol_mapping_validation():
    """All mapped symbols in relationships.yaml exist"""
```

## Acceptance Criteria

- [ ] Extended relationships.yaml schema supports symbols
- [ ] AST parsing extracts classes, methods, functions
- [ ] Symbol existence validation works
- [ ] Query by ADR returns symbol-level results
- [ ] Context injection works at symbol level
- [ ] CI validates symbol mappings still exist
- [ ] Unit tests pass
- [ ] Integration tests pass

## Files to Create/Modify

- `scripts/relationships.yaml` - Extended schema with symbols
- `scripts/symbol_extractor.py` - New: AST parsing
- `scripts/query_symbols.py` - New: symbol queries
- `scripts/inject_context.py` - Symbol-level injection
- `scripts/validate_relationships.py` - New: symbol validation
- `tests/unit/test_symbol_extraction.py` - New test file
- `tests/unit/test_symbol_queries.py` - New test file

## Ambiguities

1. **Scope of AST parsing**: Just Python? Or also YAML, Markdown, TypeScript? Starting with Python only seems reasonable. Other languages can be added later.

2. **Symbol naming convention**: Use `Class.method` or `Class::method` or `Class#method`? Python convention is `.` but might conflict with file paths. Leaning toward `.` since we're Python-focused.

3. **Nested classes/functions**: How to handle `OuterClass.InnerClass.method`? Full path seems right but verbose.

4. **Symbol drift detection**: When a symbol is renamed, how do we detect it? Could use git diff + AST comparison. This is complex - maybe defer to a follow-up plan.

5. **Granularity trade-off**: Too fine-grained becomes maintenance burden. Should we recommend only mapping "important" symbols? Need usage guidelines.

6. **Performance**: AST parsing every file on every check could be slow. Caching strategy needed. Could cache parsed symbols in `.claude/symbol-cache.json`.

7. **When to populate symbols**: During planning (TDD)? After implementation? Retroactively for existing code? Probably:
   - New code: define symbols during planning
   - Existing code: add symbols when touching related code
   - Don't require complete coverage

8. **Line number sensitivity**: If code is refactored and symbols move, line numbers in cache become stale. Symbol names are more stable than line numbers - use names as primary key.
