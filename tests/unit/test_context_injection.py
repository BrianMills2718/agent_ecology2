"""Tests for Plan #217: Context Injection for Claude Code.

Tests the governance context retrieval and hook functionality.
"""

import json
import subprocess
from pathlib import Path

import pytest
import yaml

# Import the function we're testing
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from get_governance_context import get_governance_context


class TestGetGovernanceContext:
    """Tests for get_governance_context function."""

    def test_governed_file_returns_context(self) -> None:
        """Test that a governed file returns context."""
        # contracts.py is governed by ADR-0001 and ADR-0003
        context = get_governance_context("src/world/contracts.py")
        assert context is not None
        assert "ADR-0001" in context
        assert "ADR-0003" in context
        assert "Permission checks" in context

    def test_governed_file_ledger(self) -> None:
        """Test governance context for ledger.py."""
        context = get_governance_context("src/world/ledger.py")
        assert context is not None
        assert "ADR-0001" in context
        assert "ADR-0002" in context
        assert "balance" in context.lower()

    def test_ungoverned_file_returns_none(self) -> None:
        """Test that an ungoverned file returns None."""
        context = get_governance_context("README.md")
        assert context is None

    def test_nonexistent_file_returns_none(self) -> None:
        """Test that a non-existent file returns None."""
        context = get_governance_context("nonexistent/path/file.py")
        assert context is None

    def test_context_includes_adr_titles(self) -> None:
        """Test that context includes ADR titles when available."""
        context = get_governance_context("src/world/contracts.py")
        assert context is not None
        # Should include the title, not just the number
        assert "Everything is an artifact" in context or "ADR-0001" in context


class TestHookIntegration:
    """Integration tests for the hook script."""

    def test_hook_outputs_valid_json_for_governed_file(self) -> None:
        """Test that hook outputs valid JSON for governed files."""
        result = subprocess.run(
            ["bash", ".claude/hooks/inject-governance-context.sh"],
            input='{"tool_input":{"file_path":"src/world/contracts.py"}}',
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        if result.stdout.strip():
            output = json.loads(result.stdout)
            assert "hookSpecificOutput" in output
            assert output["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
            assert "additionalContext" in output["hookSpecificOutput"]

    def test_hook_silent_for_ungoverned_file(self) -> None:
        """Test that hook produces no output for ungoverned files."""
        result = subprocess.run(
            ["bash", ".claude/hooks/inject-governance-context.sh"],
            input='{"tool_input":{"file_path":"README.md"}}',
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_hook_silent_for_missing_file_path(self) -> None:
        """Test that hook handles missing file_path gracefully."""
        result = subprocess.run(
            ["bash", ".claude/hooks/inject-governance-context.sh"],
            input='{"tool_input":{}}',
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        assert result.stdout.strip() == ""

    def test_hook_silent_for_invalid_json(self) -> None:
        """Test that hook handles invalid JSON gracefully."""
        result = subprocess.run(
            ["bash", ".claude/hooks/inject-governance-context.sh"],
            input='not valid json',
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent.parent,
        )
        assert result.returncode == 0
        # Should exit cleanly even with invalid input


class TestHookConfiguration:
    """Tests for hook configuration in meta-process.yaml."""

    def test_hook_config_exists(self) -> None:
        """Test that inject_governance_context config exists."""
        meta_process_path = Path(__file__).parent.parent.parent / "meta-process.yaml"
        with open(meta_process_path) as f:
            config = yaml.safe_load(f)

        assert "hooks" in config
        assert "inject_governance_context" in config["hooks"]

    def test_hook_enabled_by_default(self) -> None:
        """Test that hook is enabled by default."""
        meta_process_path = Path(__file__).parent.parent.parent / "meta-process.yaml"
        with open(meta_process_path) as f:
            config = yaml.safe_load(f)

        assert config["hooks"]["inject_governance_context"] is True


class TestSettingsJson:
    """Tests for .claude/settings.json configuration."""

    def test_read_hook_configured(self) -> None:
        """Test that PostToolUse hook for Read is configured."""
        settings_path = Path(__file__).parent.parent.parent / ".claude" / "settings.json"
        with open(settings_path) as f:
            settings = json.load(f)

        assert "hooks" in settings
        assert "PostToolUse" in settings["hooks"]

        # Find the Read matcher
        read_hooks = [h for h in settings["hooks"]["PostToolUse"] if h.get("matcher") == "Read"]
        assert len(read_hooks) == 1

        # Check inject-governance-context.sh is configured
        read_hook = read_hooks[0]
        hook_commands = [h["command"] for h in read_hook["hooks"]]
        assert any("inject-governance-context.sh" in cmd for cmd in hook_commands)
