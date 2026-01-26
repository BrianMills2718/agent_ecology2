#!/usr/bin/env python3
"""Extract symbols from Python files for validation (Plan #219).

This module parses Python files using AST to extract class, method, and
function definitions. Used for symbol-level doc-code coupling.

Usage:
    from symbol_extractor import extract_symbols, validate_symbol_exists

    symbols = extract_symbols(Path("src/world/contracts.py"))
    if validate_symbol_exists(Path("src/world/contracts.py"), "ContractInvoker.execute"):
        print("Symbol exists!")
"""

import ast
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Symbol:
    """Represents a symbol (class, method, or function) in source code."""

    name: str
    type: str  # 'class', 'function', 'method'
    line: int
    end_line: int
    file: Path
    parent: str | None = None  # For methods, the class name
    docstring: str | None = None


def extract_symbols(file_path: Path) -> list[Symbol]:
    """Extract all symbols from a Python file.

    Args:
        file_path: Path to the Python file.

    Returns:
        List of Symbol objects for classes, methods, and functions.
    """
    try:
        with open(file_path) as f:
            source = f.read()
    except (OSError, IOError):
        return []

    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []

    symbols: list[Symbol] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            # Extract class
            symbols.append(
                Symbol(
                    name=node.name,
                    type="class",
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    file=file_path,
                    docstring=ast.get_docstring(node),
                )
            )

            # Extract methods within the class
            for item in node.body:
                if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                    symbols.append(
                        Symbol(
                            name=f"{node.name}.{item.name}",
                            type="method",
                            line=item.lineno,
                            end_line=item.end_lineno or item.lineno,
                            file=file_path,
                            parent=node.name,
                            docstring=ast.get_docstring(item),
                        )
                    )

        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            # Check if this is a top-level function (not a method)
            # We identify top-level by checking if lineno is at module level
            # Since ast.walk flattens, we need to check parent
            # Actually, we already extracted methods above, so we can skip
            # functions that are inside classes
            pass

    # Extract top-level functions separately to avoid duplicates
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            symbols.append(
                Symbol(
                    name=node.name,
                    type="function",
                    line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    file=file_path,
                    docstring=ast.get_docstring(node),
                )
            )

    return symbols


def validate_symbol_exists(file_path: Path, symbol_name: str) -> bool:
    """Check if a symbol exists in a file.

    Args:
        file_path: Path to the Python file.
        symbol_name: Symbol name (e.g., "MyClass", "MyClass.my_method", "my_func").

    Returns:
        True if the symbol exists, False otherwise.
    """
    symbols = extract_symbols(file_path)
    return any(s.name == symbol_name for s in symbols)


def get_symbol(file_path: Path, symbol_name: str) -> Symbol | None:
    """Get a specific symbol by name.

    Args:
        file_path: Path to the Python file.
        symbol_name: Symbol name.

    Returns:
        Symbol object if found, None otherwise.
    """
    symbols = extract_symbols(file_path)
    for s in symbols:
        if s.name == symbol_name:
            return s
    return None


def get_symbol_at_line(file_path: Path, line_number: int) -> Symbol | None:
    """Find the symbol containing a specific line number.

    Args:
        file_path: Path to the Python file.
        line_number: Line number to look up.

    Returns:
        Symbol that contains the line, or None if not in any symbol.
    """
    symbols = extract_symbols(file_path)
    # Sort by specificity - methods are more specific than classes
    # So a method at line 50 should be returned over its containing class
    candidates = [
        s for s in symbols if s.line <= line_number <= s.end_line
    ]

    if not candidates:
        return None

    # Prefer methods/functions over classes
    for s in candidates:
        if s.type in ("method", "function"):
            return s

    return candidates[0]


def list_symbols(file_path: Path) -> list[str]:
    """Get a simple list of symbol names in a file.

    Args:
        file_path: Path to the Python file.

    Returns:
        List of symbol names.
    """
    return [s.name for s in extract_symbols(file_path)]


def main() -> None:
    """CLI entry point for symbol extraction."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract symbols from Python files"
    )
    parser.add_argument("file", help="Python file to extract symbols from")
    parser.add_argument(
        "--validate",
        metavar="SYMBOL",
        help="Check if a specific symbol exists",
    )
    parser.add_argument(
        "--line",
        type=int,
        metavar="LINE",
        help="Find symbol at a specific line number",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    args = parser.parse_args()
    file_path = Path(args.file)

    if not file_path.exists():
        print(f"File not found: {file_path}")
        return

    if args.validate:
        exists = validate_symbol_exists(file_path, args.validate)
        print(f"{args.validate}: {'exists' if exists else 'not found'}")
        return

    if args.line:
        symbol = get_symbol_at_line(file_path, args.line)
        if symbol:
            print(f"Line {args.line}: {symbol.name} ({symbol.type})")
        else:
            print(f"Line {args.line}: not in any symbol")
        return

    symbols = extract_symbols(file_path)

    if args.json:
        import json
        data = [
            {
                "name": s.name,
                "type": s.type,
                "line": s.line,
                "end_line": s.end_line,
                "parent": s.parent,
            }
            for s in symbols
        ]
        print(json.dumps(data, indent=2))
    else:
        print(f"Symbols in {file_path}:")
        for s in symbols:
            print(f"  {s.line}-{s.end_line}: {s.name} ({s.type})")


if __name__ == "__main__":
    main()
