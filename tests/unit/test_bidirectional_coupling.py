"""Tests for bidirectional coupling checks (Plan #216).

These tests verify that the doc-coupling script can check relationships
in both directions: code→doc AND doc→code.
"""

import pytest
from pathlib import Path
from unittest.mock import patch

# Import the module under test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))


class TestGetRelatedNodes:
    """Test get_related_nodes() finds all relationships."""

    @pytest.fixture
    def sample_relationships(self) -> dict:
        """Sample relationships.yaml data for testing."""
        return {
            "adrs": {
                1: {"title": "Everything is an artifact", "file": "0001-everything-is-artifact.md"},
                3: {"title": "Contracts can do anything", "file": "0003-contracts-can-do-anything.md"},
            },
            "governance": [
                {
                    "source": "src/world/contracts.py",
                    "adrs": [1, 3],
                    "context": "Permission checks are the hot path.",
                },
                {
                    "source": "src/world/ledger.py",
                    "adrs": [1],
                    "context": "Balance mutations.",
                },
            ],
            "couplings": [
                {
                    "sources": ["src/simulation/runner.py", "src/world/world.py"],
                    "docs": ["docs/architecture/current/execution_model.md"],
                    "description": "Tick loop and two-phase execution",
                },
                {
                    "sources": ["src/world/ledger.py"],
                    "docs": ["docs/architecture/current/resources.md"],
                    "description": "Flow/stock resources",
                },
            ],
        }

    def test_code_change_surfaces_related_docs(self, sample_relationships: dict) -> None:
        """Changing runner.py should surface execution_model.md."""
        from check_doc_coupling import get_related_nodes

        related = get_related_nodes(
            Path("src/simulation/runner.py"),
            sample_relationships
        )

        assert "docs/architecture/current/execution_model.md" in related

    def test_doc_change_surfaces_related_code(self, sample_relationships: dict) -> None:
        """Changing execution_model.md should surface runner.py, world.py."""
        from check_doc_coupling import get_related_nodes

        related = get_related_nodes(
            Path("docs/architecture/current/execution_model.md"),
            sample_relationships
        )

        assert "src/simulation/runner.py" in related
        assert "src/world/world.py" in related

    def test_code_change_surfaces_related_adrs(self, sample_relationships: dict) -> None:
        """Changing contracts.py should surface ADR-0001, ADR-0003."""
        from check_doc_coupling import get_related_nodes

        related = get_related_nodes(
            Path("src/world/contracts.py"),
            sample_relationships
        )

        # Should include ADR paths
        adr_related = [r for r in related if "docs/adr/" in r]
        assert len(adr_related) == 2
        assert any("0001" in r for r in adr_related)
        assert any("0003" in r for r in adr_related)

    def test_adr_change_surfaces_governed_code(self, sample_relationships: dict) -> None:
        """Changing ADR-0003 should surface contracts.py."""
        from check_doc_coupling import get_related_nodes

        related = get_related_nodes(
            Path("docs/adr/0003-contracts-can-do-anything.md"),
            sample_relationships
        )

        assert "src/world/contracts.py" in related

    def test_symmetric_relationship_couplings(self, sample_relationships: dict) -> None:
        """If A relates to B via coupling, then B relates to A."""
        from check_doc_coupling import get_related_nodes

        # runner.py -> execution_model.md
        related_from_code = get_related_nodes(
            Path("src/simulation/runner.py"),
            sample_relationships
        )
        assert "docs/architecture/current/execution_model.md" in related_from_code

        # execution_model.md -> runner.py
        related_from_doc = get_related_nodes(
            Path("docs/architecture/current/execution_model.md"),
            sample_relationships
        )
        assert "src/simulation/runner.py" in related_from_doc

    def test_file_with_no_relationships(self, sample_relationships: dict) -> None:
        """File with no relationships returns empty list."""
        from check_doc_coupling import get_related_nodes

        related = get_related_nodes(
            Path("src/unrelated/file.py"),
            sample_relationships
        )

        assert related == []

    def test_returns_context_for_governance(self, sample_relationships: dict) -> None:
        """Related nodes include context from governance entries."""
        from check_doc_coupling import get_related_nodes_with_context

        related = get_related_nodes_with_context(
            Path("src/world/contracts.py"),
            sample_relationships
        )

        # Should have context
        assert "context" in related
        assert "Permission checks are the hot path" in related["context"]


class TestExtractAdrNumber:
    """Test ADR number extraction from file paths."""

    def test_extract_from_standard_path(self) -> None:
        """Extract ADR number from standard path format."""
        from check_doc_coupling import extract_adr_number

        assert extract_adr_number(Path("docs/adr/0001-everything-is-artifact.md")) == 1
        assert extract_adr_number(Path("docs/adr/0003-contracts-can-do-anything.md")) == 3
        assert extract_adr_number(Path("docs/adr/0019-something.md")) == 19

    def test_extract_from_non_adr_returns_none(self) -> None:
        """Non-ADR paths return None."""
        from check_doc_coupling import extract_adr_number

        assert extract_adr_number(Path("src/world/contracts.py")) is None
        assert extract_adr_number(Path("docs/plans/01_rate_allocation.md")) is None


class TestBidirectionalCheck:
    """Test the bidirectional check mode."""

    @pytest.fixture
    def sample_relationships(self) -> dict:
        """Sample relationships for testing."""
        return {
            "adrs": {
                1: {"title": "Everything is an artifact", "file": "0001-everything-is-artifact.md"},
            },
            "governance": [
                {
                    "source": "src/world/contracts.py",
                    "adrs": [1],
                    "context": "Test context",
                },
            ],
            "couplings": [
                {
                    "sources": ["src/simulation/runner.py"],
                    "docs": ["docs/architecture/current/execution_model.md"],
                    "description": "Execution model",
                },
            ],
        }

    def test_bidirectional_detects_doc_without_code(
        self, sample_relationships: dict
    ) -> None:
        """Bidirectional mode detects when doc changed but code wasn't."""
        from check_doc_coupling import check_bidirectional

        # Only doc changed, not code
        changed_files = {"docs/architecture/current/execution_model.md"}

        warnings = check_bidirectional(changed_files, sample_relationships)

        # Should warn that runner.py might need checking
        assert len(warnings) > 0
        assert any("src/simulation/runner.py" in str(w) for w in warnings)

    def test_bidirectional_passes_when_both_changed(
        self, sample_relationships: dict
    ) -> None:
        """Bidirectional mode passes when both sides of coupling changed."""
        from check_doc_coupling import check_bidirectional

        # Both doc and code changed
        changed_files = {
            "docs/architecture/current/execution_model.md",
            "src/simulation/runner.py",
        }

        warnings = check_bidirectional(changed_files, sample_relationships)

        # Should have no warnings for this coupling
        assert not any("execution_model.md" in str(w) for w in warnings)


class TestSuggestAll:
    """Test --suggest-all mode showing full relationship graph."""

    @pytest.fixture
    def sample_relationships(self) -> dict:
        """Sample relationships for testing."""
        return {
            "adrs": {
                1: {"title": "Everything is an artifact", "file": "0001-everything-is-artifact.md"},
                3: {"title": "Contracts can do anything", "file": "0003-contracts-can-do-anything.md"},
            },
            "governance": [
                {
                    "source": "src/world/contracts.py",
                    "adrs": [1, 3],
                    "context": "Permission checks are the hot path.",
                },
            ],
            "couplings": [
                {
                    "sources": ["src/world/contracts.py"],
                    "docs": ["docs/architecture/current/contract_system.md"],
                    "description": "Contract system",
                },
            ],
        }

    def test_suggest_all_shows_adrs(self, sample_relationships: dict) -> None:
        """--suggest-all shows related ADRs."""
        from check_doc_coupling import get_suggest_all_output

        output = get_suggest_all_output(
            Path("src/world/contracts.py"),
            sample_relationships
        )

        assert "ADRs:" in output
        assert "0001" in output
        assert "0003" in output

    def test_suggest_all_shows_docs(self, sample_relationships: dict) -> None:
        """--suggest-all shows related docs."""
        from check_doc_coupling import get_suggest_all_output

        output = get_suggest_all_output(
            Path("src/world/contracts.py"),
            sample_relationships
        )

        assert "Docs:" in output
        assert "contract_system.md" in output

    def test_suggest_all_shows_context(self, sample_relationships: dict) -> None:
        """--suggest-all shows governance context."""
        from check_doc_coupling import get_suggest_all_output

        output = get_suggest_all_output(
            Path("src/world/contracts.py"),
            sample_relationships
        )

        assert "Context:" in output
        assert "Permission checks are the hot path" in output


class TestLoadRelationships:
    """Test loading relationships from YAML."""

    def test_load_from_relationships_yaml(self, tmp_path: Path) -> None:
        """Load relationships from relationships.yaml."""
        import yaml
        from check_doc_coupling import load_relationships

        # Create test file
        relationships = {
            "adrs": {1: {"title": "Test", "file": "0001-test.md"}},
            "governance": [],
            "couplings": [],
        }
        rel_file = tmp_path / "relationships.yaml"
        with open(rel_file, "w") as f:
            yaml.dump(relationships, f)

        loaded = load_relationships(rel_file)

        assert "adrs" in loaded
        assert "governance" in loaded
        assert "couplings" in loaded
