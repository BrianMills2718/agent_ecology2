"""Tests for check_feature_coverage.py.

Tests acceptance criteria:
- AC-3: Check feature coverage (src files assigned to features)
"""

import tempfile
from pathlib import Path

import pytest
import yaml

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from check_feature_coverage import (
    check_coverage,
    extract_assigned_files,
    find_source_files,
    load_feature_files,
)


class TestLoadFeatureFiles:
    """Tests for loading feature YAML files."""

    def test_load_from_directory(self, tmp_path: Path) -> None:
        """Should load all feature files from directory."""
        # Create feature files
        feature1 = {
            "feature": "test-feature-1",
            "code": ["src/foo.py"],
        }
        feature2 = {
            "feature": "test-feature-2",
            "code": ["src/bar.py"],
        }
        (tmp_path / "feature1.yaml").write_text(yaml.dump(feature1))
        (tmp_path / "feature2.yml").write_text(yaml.dump(feature2))

        features = load_feature_files(tmp_path)

        assert len(features) == 2
        assert "test-feature-1" in features
        assert "test-feature-2" in features

    def test_skip_invalid_yaml(self, tmp_path: Path) -> None:
        """Should skip files with invalid YAML."""
        (tmp_path / "invalid.yaml").write_text("invalid: yaml: [")
        (tmp_path / "valid.yaml").write_text(yaml.dump({"feature": "valid", "code": []}))

        features = load_feature_files(tmp_path)

        assert len(features) == 1
        assert "valid" in features

    def test_empty_directory(self, tmp_path: Path) -> None:
        """Should return empty dict for empty directory."""
        features = load_feature_files(tmp_path)
        assert features == {}

    def test_nonexistent_directory(self, tmp_path: Path) -> None:
        """Should return empty dict for nonexistent directory."""
        features = load_feature_files(tmp_path / "nonexistent")
        assert features == {}


class TestExtractAssignedFiles:
    """Tests for extracting file -> feature mappings."""

    def test_extract_code_files(self) -> None:
        """Should extract files from code sections."""
        features = {
            "feature-1": {"code": ["src/foo.py", "src/bar.py"]},
            "feature-2": {"code": ["scripts/baz.py"]},
        }

        assigned = extract_assigned_files(features)

        assert assigned["src/foo.py"] == "feature-1"
        assert assigned["src/bar.py"] == "feature-1"
        assert assigned["scripts/baz.py"] == "feature-2"

    def test_empty_code_section(self) -> None:
        """Should handle features without code sections."""
        features = {
            "feature-1": {"problem": "something"},
            "feature-2": {"code": []},
        }

        assigned = extract_assigned_files(features)

        assert len(assigned) == 0

    def test_normalize_paths(self) -> None:
        """Should normalize file paths."""
        features = {
            "feature-1": {"code": ["./src/foo.py"]},
        }

        assigned = extract_assigned_files(features)

        # Path normalization should occur
        assert "src/foo.py" in assigned


class TestFindSourceFiles:
    """Tests for finding source files in directories."""

    def test_find_python_files(self, tmp_path: Path) -> None:
        """Should find all .py files."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "foo.py").touch()
        (src / "bar.py").touch()
        (src / "readme.md").touch()

        files = find_source_files([src], [])

        assert len(files) == 2
        assert all(f.suffix == ".py" for f in files)

    def test_exclude_patterns(self, tmp_path: Path) -> None:
        """Should exclude files matching patterns."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "foo.py").touch()
        (src / "__init__.py").touch()
        (src / "conftest.py").touch()

        files = find_source_files([src], ["__init__.py", "conftest.py"])

        assert len(files) == 1
        assert files[0].name == "foo.py"

    def test_skip_pycache(self, tmp_path: Path) -> None:
        """Should skip __pycache__ directories."""
        src = tmp_path / "src"
        pycache = src / "__pycache__"
        src.mkdir()
        pycache.mkdir()
        (src / "foo.py").touch()
        (pycache / "foo.cpython-311.pyc").touch()
        # Also create a .py file in pycache (unusual but possible)
        (pycache / "cached.py").touch()

        files = find_source_files([src], [])

        assert len(files) == 1
        assert files[0].name == "foo.py"

    def test_recursive_search(self, tmp_path: Path) -> None:
        """Should find files in subdirectories."""
        src = tmp_path / "src"
        sub = src / "sub" / "deep"
        src.mkdir()
        sub.mkdir(parents=True)
        (src / "top.py").touch()
        (sub / "deep.py").touch()

        files = find_source_files([src], [])

        assert len(files) == 2

    def test_multiple_directories(self, tmp_path: Path) -> None:
        """Should search multiple directories."""
        src = tmp_path / "src"
        scripts = tmp_path / "scripts"
        src.mkdir()
        scripts.mkdir()
        (src / "a.py").touch()
        (scripts / "b.py").touch()

        files = find_source_files([src, scripts], [])

        assert len(files) == 2


class TestCheckCoverage:
    """Integration tests for coverage checking (AC-3)."""

    def test_all_files_assigned(self, tmp_path: Path) -> None:
        """Should report 100% coverage when all files assigned."""
        # Setup
        src = tmp_path / "src"
        features = tmp_path / "features"
        src.mkdir()
        features.mkdir()

        (src / "foo.py").touch()
        (src / "bar.py").touch()

        # Use absolute paths to match what find_source_files returns
        feature_file = {
            "feature": "test",
            "code": [str(src / "foo.py"), str(src / "bar.py")],
        }
        (features / "test.yaml").write_text(yaml.dump(feature_file))

        # Run
        assigned, unassigned = check_coverage(
            features, [src], ["__init__.py"]
        )

        # Verify
        assert len(unassigned) == 0
        assert len(assigned) == 2

    def test_unassigned_files_detected(self, tmp_path: Path) -> None:
        """Should detect unassigned source files."""
        # Setup
        src = tmp_path / "src"
        features = tmp_path / "features"
        src.mkdir()
        features.mkdir()

        (src / "assigned.py").touch()
        (src / "unassigned.py").touch()

        # Use absolute path to match what find_source_files returns
        feature_file = {
            "feature": "test",
            "code": [str(src / "assigned.py")],
        }
        (features / "test.yaml").write_text(yaml.dump(feature_file))

        # Run
        assigned, unassigned = check_coverage(
            features, [src], ["__init__.py"]
        )

        # Verify
        assert len(assigned) == 1
        assert len(unassigned) == 1
        assert any("unassigned.py" in str(f) for f in unassigned)

    def test_no_source_files(self, tmp_path: Path) -> None:
        """Should handle case with no source files."""
        src = tmp_path / "src"
        features = tmp_path / "features"
        src.mkdir()
        features.mkdir()

        assigned, unassigned = check_coverage(
            features, [src], []
        )

        assert len(assigned) == 0
        assert len(unassigned) == 0

    def test_no_features(self, tmp_path: Path) -> None:
        """Should report all files as unassigned when no features."""
        src = tmp_path / "src"
        features = tmp_path / "features"
        src.mkdir()
        features.mkdir()

        (src / "foo.py").touch()

        assigned, unassigned = check_coverage(
            features, [src], []
        )

        assert len(assigned) == 0
        assert len(unassigned) == 1
