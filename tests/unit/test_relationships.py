"""Tests for unified documentation graph (relationships.yaml).

Plan #215: Verify that all scripts correctly read from relationships.yaml.
"""

import pytest
from pathlib import Path

import yaml


SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"


class TestRelationshipsSchema:
    """Test relationships.yaml schema and structure."""

    def test_relationships_yaml_exists(self) -> None:
        """relationships.yaml should exist."""
        path = SCRIPTS_DIR / "relationships.yaml"
        assert path.exists(), "relationships.yaml not found"

    def test_relationships_yaml_valid(self) -> None:
        """relationships.yaml should be valid YAML."""
        path = SCRIPTS_DIR / "relationships.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        assert data is not None
        assert isinstance(data, dict)

    def test_has_adrs_section(self) -> None:
        """Should have adrs metadata section."""
        path = SCRIPTS_DIR / "relationships.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "adrs" in data
        assert isinstance(data["adrs"], dict)
        # Should have at least ADR 1, 2, 3
        assert 1 in data["adrs"]
        assert 2 in data["adrs"]
        assert 3 in data["adrs"]

    def test_has_governance_section(self) -> None:
        """Should have governance section."""
        path = SCRIPTS_DIR / "relationships.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "governance" in data
        assert isinstance(data["governance"], list)
        assert len(data["governance"]) > 0

    def test_has_couplings_section(self) -> None:
        """Should have couplings section."""
        path = SCRIPTS_DIR / "relationships.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        assert "couplings" in data
        assert isinstance(data["couplings"], list)
        assert len(data["couplings"]) > 0

    def test_governance_entry_structure(self) -> None:
        """Each governance entry should have source and adrs."""
        path = SCRIPTS_DIR / "relationships.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        for entry in data["governance"]:
            assert "source" in entry, f"Missing 'source' in governance entry: {entry}"
            assert "adrs" in entry, f"Missing 'adrs' in governance entry: {entry}"
            assert isinstance(entry["adrs"], list)

    def test_coupling_entry_structure(self) -> None:
        """Each coupling entry should have sources, docs, and description."""
        path = SCRIPTS_DIR / "relationships.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        for entry in data["couplings"]:
            assert "sources" in entry, f"Missing 'sources' in coupling: {entry}"
            assert "docs" in entry, f"Missing 'docs' in coupling: {entry}"
            assert "description" in entry, f"Missing 'description' in coupling: {entry}"
            assert isinstance(entry["sources"], list)
            assert isinstance(entry["docs"], list)


class TestCheckDocCouplingIntegration:
    """Test check_doc_coupling.py reads from relationships.yaml."""

    def test_load_couplings_returns_list(self) -> None:
        """load_couplings should return coupling list."""
        import sys
        sys.path.insert(0, str(SCRIPTS_DIR))
        from check_doc_coupling import load_couplings

        couplings = load_couplings(SCRIPTS_DIR / "relationships.yaml")
        assert isinstance(couplings, list)
        assert len(couplings) > 0

    def test_couplings_have_required_fields(self) -> None:
        """Each coupling should have sources and docs."""
        import sys
        sys.path.insert(0, str(SCRIPTS_DIR))
        from check_doc_coupling import load_couplings

        couplings = load_couplings(SCRIPTS_DIR / "relationships.yaml")
        for coupling in couplings:
            assert "sources" in coupling
            assert "docs" in coupling


class TestSyncGovernanceIntegration:
    """Test sync_governance.py reads from relationships.yaml."""

    def test_governance_config_loads(self) -> None:
        """GovernanceConfig.load should work with relationships.yaml."""
        import sys
        sys.path.insert(0, str(SCRIPTS_DIR))
        from sync_governance import GovernanceConfig

        config = GovernanceConfig.load(SCRIPTS_DIR / "relationships.yaml")
        assert isinstance(config.files, dict)
        assert isinstance(config.adrs, dict)
        assert len(config.files) > 0
        assert len(config.adrs) > 0

    def test_governance_has_expected_files(self) -> None:
        """Should have governance for key files."""
        import sys
        sys.path.insert(0, str(SCRIPTS_DIR))
        from sync_governance import GovernanceConfig

        config = GovernanceConfig.load(SCRIPTS_DIR / "relationships.yaml")
        expected = ["src/world/contracts.py", "src/world/ledger.py", "src/world/artifacts.py"]
        for path in expected:
            assert path in config.files, f"Missing governance for {path}"
