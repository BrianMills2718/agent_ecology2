"""Tests for health_check.py and meta_config.py scripts."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestHealthCheck:
    """Test HealthCheck class."""

    def test_init_default(self) -> None:
        """Test HealthCheck initialization with defaults."""
        from health_check import HealthCheck

        checker = HealthCheck()
        assert checker.fix is False
        assert checker.quiet is False
        assert checker.issues == []
        assert checker.warnings == []
        assert checker.fixed == []

    def test_init_with_options(self) -> None:
        """Test HealthCheck initialization with options."""
        from health_check import HealthCheck

        checker = HealthCheck(fix=True, quiet=True)
        assert checker.fix is True
        assert checker.quiet is True

    def test_issue_adds_to_list(self) -> None:
        """Test issue method adds to issues list."""
        from health_check import HealthCheck

        checker = HealthCheck(quiet=True)
        checker.issue("test issue")
        assert "test issue" in checker.issues

    def test_warning_adds_to_list(self) -> None:
        """Test warning method adds to warnings list."""
        from health_check import HealthCheck

        checker = HealthCheck(quiet=True)
        checker.warning("test warning")
        assert "test warning" in checker.warnings


class TestHealthCheckCLI:
    """Test health_check.py CLI."""

    def test_help_flag(self) -> None:
        """Test --help flag works."""
        result = subprocess.run(
            [sys.executable, "scripts/health_check.py", "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "health" in result.stdout.lower() or "usage" in result.stdout.lower()


class TestMetaConfig:
    """Test meta_config.py helper."""

    def test_get_config_missing_file(self, tmp_path: Path) -> None:
        """Test getting config when file doesn't exist."""
        from meta_config import get_config

        with patch("meta_config.get_repo_root", return_value=tmp_path):
            config = get_config()
            assert config == {}

    def test_get_value_default(self, tmp_path: Path) -> None:
        """Test getting value with default."""
        from meta_config import get_value

        with patch("meta_config.get_repo_root", return_value=tmp_path):
            value = get_value("hooks.protect_main", True)
            assert value is True

    def test_is_hook_enabled_default(self, tmp_path: Path) -> None:
        """Test hook enabled check defaults to True."""
        from meta_config import is_hook_enabled

        with patch("meta_config.get_repo_root", return_value=tmp_path):
            enabled = is_hook_enabled("protect_main")
            assert enabled is True

    def test_get_config_with_file(self, tmp_path: Path) -> None:
        """Test getting config from actual file."""
        from meta_config import get_config

        config_file = tmp_path / "meta-process.yaml"
        config_file.write_text("hooks:\n  protect_main: false\n")

        with patch("meta_config.get_repo_root", return_value=tmp_path):
            config = get_config()
            assert config.get("hooks", {}).get("protect_main") is False

    def test_is_hook_disabled_in_config(self, tmp_path: Path) -> None:
        """Test hook can be disabled via config."""
        from meta_config import is_hook_enabled

        config_file = tmp_path / "meta-process.yaml"
        config_file.write_text("hooks:\n  protect_main: false\n")

        with patch("meta_config.get_repo_root", return_value=tmp_path):
            enabled = is_hook_enabled("protect_main")
            assert enabled is False

    def test_get_value_nested(self, tmp_path: Path) -> None:
        """Test getting nested config value."""
        from meta_config import get_value

        config_file = tmp_path / "meta-process.yaml"
        config_file.write_text("workflow:\n  stale_claim_hours: 12\n")

        with patch("meta_config.get_repo_root", return_value=tmp_path):
            value = get_value("workflow.stale_claim_hours", 8)
            assert value == 12


class TestMetaConfigCLI:
    """Test meta_config.py CLI."""

    def test_help_flag(self) -> None:
        """Test --help flag works."""
        script_path = Path(__file__).parent.parent / "scripts" / "meta_config.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--help"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "hook" in result.stdout.lower()

    def test_dump_flag(self) -> None:
        """Test --dump flag works."""
        script_path = Path(__file__).parent.parent / "scripts" / "meta_config.py"
        result = subprocess.run(
            [sys.executable, str(script_path), "--dump"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
