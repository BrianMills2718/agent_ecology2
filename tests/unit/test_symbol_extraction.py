"""Tests for symbol extraction (Plan #219)."""

import tempfile
from pathlib import Path

import pytest
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from symbol_extractor import (
    Symbol,
    extract_symbols,
    get_symbol,
    get_symbol_at_line,
    list_symbols,
    validate_symbol_exists,
)


class TestExtractSymbols:
    """Tests for extract_symbols function."""

    def test_extract_class(self) -> None:
        """Extract class definitions."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
class MyClass:
    """A test class."""
    pass
''')
            f.flush()
            path = Path(f.name)

        try:
            symbols = extract_symbols(path)
            assert len(symbols) == 1
            assert symbols[0].name == "MyClass"
            assert symbols[0].type == "class"
            assert symbols[0].docstring == "A test class."
        finally:
            path.unlink()

    def test_extract_method(self) -> None:
        """Extract methods with Class.method format."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
class MyClass:
    def my_method(self):
        """A test method."""
        pass
''')
            f.flush()
            path = Path(f.name)

        try:
            symbols = extract_symbols(path)
            # Should have class and method
            names = [s.name for s in symbols]
            assert "MyClass" in names
            assert "MyClass.my_method" in names

            method = next(s for s in symbols if s.name == "MyClass.my_method")
            assert method.type == "method"
            assert method.parent == "MyClass"
            assert method.docstring == "A test method."
        finally:
            path.unlink()

    def test_extract_function(self) -> None:
        """Extract top-level functions."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
def my_function():
    """A test function."""
    pass
''')
            f.flush()
            path = Path(f.name)

        try:
            symbols = extract_symbols(path)
            assert len(symbols) == 1
            assert symbols[0].name == "my_function"
            assert symbols[0].type == "function"
            assert symbols[0].docstring == "A test function."
        finally:
            path.unlink()

    def test_extract_async_function(self) -> None:
        """Extract async functions."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
async def async_func():
    pass
''')
            f.flush()
            path = Path(f.name)

        try:
            symbols = extract_symbols(path)
            assert len(symbols) == 1
            assert symbols[0].name == "async_func"
            assert symbols[0].type == "function"
        finally:
            path.unlink()

    def test_extract_async_method(self) -> None:
        """Extract async methods."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
class MyClass:
    async def async_method(self):
        pass
''')
            f.flush()
            path = Path(f.name)

        try:
            symbols = extract_symbols(path)
            names = [s.name for s in symbols]
            assert "MyClass" in names
            assert "MyClass.async_method" in names
        finally:
            path.unlink()

    def test_extract_multiple_classes(self) -> None:
        """Extract multiple classes and their methods."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
class FirstClass:
    def first_method(self):
        pass

class SecondClass:
    def second_method(self):
        pass
''')
            f.flush()
            path = Path(f.name)

        try:
            symbols = extract_symbols(path)
            names = [s.name for s in symbols]
            assert "FirstClass" in names
            assert "FirstClass.first_method" in names
            assert "SecondClass" in names
            assert "SecondClass.second_method" in names
        finally:
            path.unlink()

    def test_extract_empty_file(self) -> None:
        """Handle empty files gracefully."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("")
            f.flush()
            path = Path(f.name)

        try:
            symbols = extract_symbols(path)
            assert symbols == []
        finally:
            path.unlink()

    def test_extract_syntax_error(self) -> None:
        """Handle files with syntax errors gracefully."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write("def broken(:\n    pass")
            f.flush()
            path = Path(f.name)

        try:
            symbols = extract_symbols(path)
            assert symbols == []
        finally:
            path.unlink()

    def test_extract_nonexistent_file(self) -> None:
        """Handle nonexistent files gracefully."""
        path = Path("/nonexistent/file.py")
        symbols = extract_symbols(path)
        assert symbols == []


class TestValidateSymbolExists:
    """Tests for validate_symbol_exists function."""

    def test_validate_symbol_exists(self) -> None:
        """Symbol validation works for existing symbol."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
class MyClass:
    def my_method(self):
        pass
''')
            f.flush()
            path = Path(f.name)

        try:
            assert validate_symbol_exists(path, "MyClass") is True
            assert validate_symbol_exists(path, "MyClass.my_method") is True
        finally:
            path.unlink()

    def test_validate_symbol_missing(self) -> None:
        """Missing symbol detected."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
class MyClass:
    pass
''')
            f.flush()
            path = Path(f.name)

        try:
            assert validate_symbol_exists(path, "MyClass") is True
            assert validate_symbol_exists(path, "NonexistentClass") is False
            assert validate_symbol_exists(path, "MyClass.nonexistent_method") is False
        finally:
            path.unlink()


class TestGetSymbol:
    """Tests for get_symbol function."""

    def test_get_symbol_found(self) -> None:
        """Get symbol by name when it exists."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
def my_func():
    pass
''')
            f.flush()
            path = Path(f.name)

        try:
            symbol = get_symbol(path, "my_func")
            assert symbol is not None
            assert symbol.name == "my_func"
            assert symbol.type == "function"
        finally:
            path.unlink()

    def test_get_symbol_not_found(self) -> None:
        """Get symbol returns None when not found."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
def my_func():
    pass
''')
            f.flush()
            path = Path(f.name)

        try:
            symbol = get_symbol(path, "other_func")
            assert symbol is None
        finally:
            path.unlink()


class TestGetSymbolAtLine:
    """Tests for get_symbol_at_line function."""

    def test_get_symbol_at_line_function(self) -> None:
        """Find function containing a line."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
def my_func():
    x = 1
    y = 2
    return x + y
''')
            f.flush()
            path = Path(f.name)

        try:
            # Line 3 is inside my_func
            symbol = get_symbol_at_line(path, 3)
            assert symbol is not None
            assert symbol.name == "my_func"
        finally:
            path.unlink()

    def test_get_symbol_at_line_method(self) -> None:
        """Find method containing a line."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
class MyClass:
    def my_method(self):
        x = 1
        return x
''')
            f.flush()
            path = Path(f.name)

        try:
            # Line 4 is inside my_method
            symbol = get_symbol_at_line(path, 4)
            assert symbol is not None
            assert symbol.name == "MyClass.my_method"
            assert symbol.type == "method"
        finally:
            path.unlink()

    def test_get_symbol_at_line_outside(self) -> None:
        """Return None for lines outside any symbol."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
# Just a comment

def my_func():
    pass
''')
            f.flush()
            path = Path(f.name)

        try:
            # Line 2 is outside any symbol
            symbol = get_symbol_at_line(path, 2)
            assert symbol is None
        finally:
            path.unlink()


class TestListSymbols:
    """Tests for list_symbols function."""

    def test_list_symbols(self) -> None:
        """List all symbol names in a file."""
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w") as f:
            f.write('''
class MyClass:
    def method1(self):
        pass
    def method2(self):
        pass

def standalone():
    pass
''')
            f.flush()
            path = Path(f.name)

        try:
            names = list_symbols(path)
            assert "MyClass" in names
            assert "MyClass.method1" in names
            assert "MyClass.method2" in names
            assert "standalone" in names
        finally:
            path.unlink()


class TestRealFiles:
    """Tests using real source files from the codebase."""

    def test_real_codebase_symbol_extraction(self) -> None:
        """Extract symbols from actual src/ files."""
        # Test on a known file
        path = Path("src/world/world.py")
        if not path.exists():
            pytest.skip("src/world/world.py not found")

        symbols = extract_symbols(path)

        # Should find the World class
        names = [s.name for s in symbols]
        assert "World" in names

        # Should find methods
        method_names = [s.name for s in symbols if s.type == "method"]
        assert len(method_names) > 0

    def test_real_file_line_lookup(self) -> None:
        """Test line lookup on real files."""
        path = Path("src/world/world.py")
        if not path.exists():
            pytest.skip("src/world/world.py not found")

        # Line 1 might be imports or comments
        # Find a line inside a class
        symbols = extract_symbols(path)
        if not symbols:
            pytest.skip("No symbols found")

        # Use the first symbol's line
        first_symbol = symbols[0]
        found = get_symbol_at_line(path, first_symbol.line)
        assert found is not None
        assert found.name == first_symbol.name
