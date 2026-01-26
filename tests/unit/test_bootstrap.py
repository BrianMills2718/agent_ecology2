"""Tests for bootstrap_meta_process.py (Plan #220)."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
import sys

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from bootstrap_meta_process import (
    analyze_repo,
    calculate_compliance,
    detect_patterns,
    get_recommendations,
    init_meta_process,
    suggest_adrs,
    suggest_couplings,
)


class TestAnalyzeRepo:
    """Tests for analyze_repo function."""

    def test_analyze_empty_repo(self) -> None:
        """Analyze repo with minimal structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                analysis = analyze_repo()

                assert analysis["has_docs"] is False
                assert analysis["has_tests"] is False
                assert analysis["has_src"] is False
                assert analysis["file_count"] == 0
            finally:
                os.chdir(original_cwd)

    def test_analyze_full_repo(self) -> None:
        """Analyze repo with docs, tests, src."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Create structure
                Path("docs").mkdir()
                Path("tests").mkdir()
                Path("src").mkdir()
                Path("docs/README.md").write_text("# Docs")
                Path("src/main.py").write_text("print('hello')")
                Path("tests/test_main.py").write_text("def test_main(): pass")

                analysis = analyze_repo()

                assert analysis["has_docs"] is True
                assert analysis["has_tests"] is True
                assert analysis["has_src"] is True
                assert analysis["file_count"] >= 1
                assert analysis["test_count"] >= 1
                assert analysis["doc_count"] >= 1
            finally:
                os.chdir(original_cwd)


class TestSuggestCouplings:
    """Tests for suggest_couplings function."""

    def test_suggest_readme_coupling(self) -> None:
        """Coupling suggestions include README.md."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                Path("README.md").write_text("# Project")
                Path("run.py").write_text("print('run')")

                couplings = suggest_couplings()

                # Should suggest README.md -> run.py coupling
                descriptions = [c["description"] for c in couplings]
                assert any("Main entry point" in d for d in descriptions)
            finally:
                os.chdir(original_cwd)

    def test_suggest_module_coupling(self) -> None:
        """Coupling suggestions based on docs/X.md <-> src/X/."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                Path("docs").mkdir()
                Path("src").mkdir()
                Path("src/world").mkdir()
                Path("docs/world.md").write_text("# World docs")
                Path("src/world/main.py").write_text("# world module")

                couplings = suggest_couplings()

                descriptions = [c["description"] for c in couplings]
                assert any("world" in d for d in descriptions)
            finally:
                os.chdir(original_cwd)


class TestSuggestADRs:
    """Tests for suggest_adrs function."""

    def test_suggest_adrs_dockerfile(self) -> None:
        """ADR suggestions based on detected Dockerfile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                Path("Dockerfile").write_text("FROM python:3.12")

                adrs = suggest_adrs()

                titles = [a["title"] for a in adrs]
                assert any("Container" in t for t in titles)
            finally:
                os.chdir(original_cwd)

    def test_suggest_adrs_ci(self) -> None:
        """ADR suggestions based on detected CI."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                Path(".github").mkdir()
                Path(".github/workflows").mkdir()
                Path(".github/workflows/ci.yml").write_text("name: CI")

                adrs = suggest_adrs()

                titles = [a["title"] for a in adrs]
                assert any("CI" in t for t in titles)
            finally:
                os.chdir(original_cwd)


class TestDetectPatterns:
    """Tests for detect_patterns function."""

    def test_detect_src_tests_layout(self) -> None:
        """Detect src-tests layout pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                Path("src").mkdir()
                Path("tests").mkdir()

                patterns = detect_patterns()

                assert "src-tests layout" in patterns
            finally:
                os.chdir(original_cwd)


class TestInitMetaProcess:
    """Tests for init_meta_process function."""

    def test_init_creates_files(self) -> None:
        """Init creates necessary files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                init_meta_process("light")

                assert Path("meta-process.yaml").exists()
                assert Path("scripts/relationships.yaml").exists()
                assert Path("docs/plans").is_dir()
                assert Path("docs/adr").is_dir()
                assert Path("CLAUDE.md").exists()
            finally:
                os.chdir(original_cwd)

    def test_init_respects_weight(self) -> None:
        """Init uses specified weight."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                init_meta_process("medium")

                with open("meta-process.yaml") as f:
                    config = yaml.safe_load(f)

                assert config["weight"] == "medium"
            finally:
                os.chdir(original_cwd)

    def test_init_skips_existing_files(self, capsys) -> None:
        """Init skips files that already exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Create existing file
                Path("CLAUDE.md").write_text("# Existing")

                init_meta_process("light")

                # Check output mentions skipping
                captured = capsys.readouterr()
                assert "Skipped: CLAUDE.md" in captured.out

                # File content should be unchanged
                assert Path("CLAUDE.md").read_text() == "# Existing"
            finally:
                os.chdir(original_cwd)


class TestCalculateCompliance:
    """Tests for calculate_compliance function."""

    def test_compliance_empty_repo(self) -> None:
        """Compliance score for empty repo."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                metrics = calculate_compliance()

                assert metrics["score"] == 0
                assert metrics["has_claude_md"] is False
            finally:
                os.chdir(original_cwd)

    def test_compliance_full_setup(self) -> None:
        """Compliance score for full setup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)

                # Create full structure
                Path("CLAUDE.md").write_text("# Project")
                Path("meta-process.yaml").write_text("weight: medium")
                Path("scripts").mkdir()
                Path("scripts/relationships.yaml").write_text(
                    "couplings:\n" + "".join([
                        f"- sources: ['src{i}/']\n  docs: ['doc{i}.md']\n  description: 'C{i}'\n"
                        for i in range(5)
                    ])
                )
                Path("docs").mkdir()
                Path("docs/adr").mkdir()
                Path("docs/plans").mkdir()
                Path("docs/adr/0001-test.md").write_text("# ADR 1")
                Path("docs/adr/0002-test.md").write_text("# ADR 2")
                Path("docs/adr/0003-test.md").write_text("# ADR 3")
                Path("docs/plans/01_plan.md").write_text("# Plan 1")

                metrics = calculate_compliance()

                assert metrics["has_claude_md"] is True
                assert metrics["has_meta_process"] is True
                assert metrics["has_relationships"] is True
                assert metrics["adr_count"] == 3
                assert metrics["coupling_count"] == 5
                assert metrics["plan_count"] == 1
                assert metrics["score"] >= 80
            finally:
                os.chdir(original_cwd)


class TestGetRecommendations:
    """Tests for get_recommendations function."""

    def test_recommendations_empty(self) -> None:
        """Recommendations for empty repo."""
        metrics = {
            "has_claude_md": False,
            "has_meta_process": False,
            "has_relationships": False,
            "adr_count": 0,
            "coupling_count": 0,
            "weight": "minimal",
            "score": 0,
        }

        recs = get_recommendations(metrics)

        assert any("CLAUDE.md" in r for r in recs)
        assert any("init" in r.lower() for r in recs)

    def test_recommendations_upgrade_weight(self) -> None:
        """Recommendations suggest weight upgrade when appropriate."""
        metrics = {
            "has_claude_md": True,
            "has_meta_process": True,
            "has_relationships": True,
            "adr_count": 3,
            "coupling_count": 5,
            "weight": "light",
            "score": 80,
        }

        recs = get_recommendations(metrics)

        assert any("medium" in r.lower() for r in recs)


class TestRealRepo:
    """Tests on the actual codebase."""

    def test_analyze_on_real_repo(self) -> None:
        """Run analysis on actual codebase."""
        # Only run if in the actual repo
        if not Path("src/world/world.py").exists():
            pytest.skip("Not in agent_ecology2 repo")

        analysis = analyze_repo()

        assert analysis["has_src"] is True
        assert analysis["has_tests"] is True
        assert analysis["file_count"] > 0

    def test_compliance_on_real_repo(self) -> None:
        """Check compliance on actual codebase."""
        if not Path("src/world/world.py").exists():
            pytest.skip("Not in agent_ecology2 repo")

        metrics = calculate_compliance()

        # Our repo should have high compliance
        assert metrics["has_claude_md"] is True
        assert metrics["has_meta_process"] is True
        assert metrics["score"] >= 50
