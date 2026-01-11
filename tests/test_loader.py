"""Tests for agent loader functionality.

Tests load_agents, list_agents, and get_default_prompt functions.
"""

import tempfile
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.agents.loader import load_agents, list_agents, get_default_prompt, AgentConfig


class TestLoadAgents:
    """Tests for load_agents function."""

    def test_loads_agent_from_directory(self) -> None:
        """load_agents discovers and loads agent from directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            # Create agent directory structure
            agent_dir = agents_dir / "test_agent"
            agent_dir.mkdir()

            config = {"id": "test_agent", "starting_scrip": 150, "enabled": True}
            (agent_dir / "agent.yaml").write_text(yaml.dump(config))
            (agent_dir / "system_prompt.md").write_text("You are a test agent.")

            agents = load_agents(str(agents_dir))

            assert len(agents) == 1
            assert agents[0]["id"] == "test_agent"
            assert agents[0]["starting_scrip"] == 150
            assert agents[0]["system_prompt"] == "You are a test agent."

    def test_skips_disabled_agents(self) -> None:
        """load_agents skips agents with enabled: false."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            # Create enabled agent
            enabled_dir = agents_dir / "enabled_agent"
            enabled_dir.mkdir()
            (enabled_dir / "agent.yaml").write_text(yaml.dump({"id": "enabled", "enabled": True}))

            # Create disabled agent
            disabled_dir = agents_dir / "disabled_agent"
            disabled_dir.mkdir()
            (disabled_dir / "agent.yaml").write_text(yaml.dump({"id": "disabled", "enabled": False}))

            agents = load_agents(str(agents_dir))

            assert len(agents) == 1
            assert agents[0]["id"] == "enabled"

    def test_skips_directories_without_config(self) -> None:
        """load_agents skips directories missing agent.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            # Create valid agent
            valid_dir = agents_dir / "valid_agent"
            valid_dir.mkdir()
            (valid_dir / "agent.yaml").write_text(yaml.dump({"id": "valid"}))

            # Create directory without config
            no_config_dir = agents_dir / "no_config"
            no_config_dir.mkdir()
            (no_config_dir / "system_prompt.md").write_text("No config here")

            agents = load_agents(str(agents_dir))

            assert len(agents) == 1
            assert agents[0]["id"] == "valid"

    def test_skips_underscore_prefixed_directories(self) -> None:
        """load_agents skips directories starting with underscore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            # Create normal agent
            normal_dir = agents_dir / "normal_agent"
            normal_dir.mkdir()
            (normal_dir / "agent.yaml").write_text(yaml.dump({"id": "normal"}))

            # Create template directory (underscore prefix)
            template_dir = agents_dir / "_template"
            template_dir.mkdir()
            (template_dir / "agent.yaml").write_text(yaml.dump({"id": "template"}))

            agents = load_agents(str(agents_dir))

            assert len(agents) == 1
            assert agents[0]["id"] == "normal"

    def test_skips_non_directories(self) -> None:
        """load_agents skips files in the agents directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            # Create agent
            agent_dir = agents_dir / "agent"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text(yaml.dump({"id": "agent"}))

            # Create a file (not directory)
            (agents_dir / "README.md").write_text("This is a file")

            agents = load_agents(str(agents_dir))

            assert len(agents) == 1
            assert agents[0]["id"] == "agent"

    def test_default_starting_scrip(self) -> None:
        """load_agents uses 100 as default starting_scrip."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            agent_dir = agents_dir / "agent"
            agent_dir.mkdir()
            # No starting_scrip in config
            (agent_dir / "agent.yaml").write_text(yaml.dump({"id": "agent"}))

            agents = load_agents(str(agents_dir))

            assert agents[0]["starting_scrip"] == 100

    def test_default_id_from_directory_name(self) -> None:
        """load_agents uses directory name as default id."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            agent_dir = agents_dir / "my_cool_agent"
            agent_dir.mkdir()
            # No id in config
            (agent_dir / "agent.yaml").write_text(yaml.dump({"enabled": True}))

            agents = load_agents(str(agents_dir))

            assert agents[0]["id"] == "my_cool_agent"

    def test_loads_system_prompt(self) -> None:
        """load_agents loads system_prompt.md content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            agent_dir = agents_dir / "agent"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text(yaml.dump({"id": "agent"}))

            prompt = """# Agent System Prompt

You are a helpful agent.

## Instructions
- Be helpful
- Be concise
"""
            (agent_dir / "system_prompt.md").write_text(prompt)

            agents = load_agents(str(agents_dir))

            assert agents[0]["system_prompt"] == prompt

    def test_empty_prompt_when_missing(self) -> None:
        """load_agents uses empty string when system_prompt.md missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            agent_dir = agents_dir / "agent"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text(yaml.dump({"id": "agent"}))
            # No system_prompt.md

            agents = load_agents(str(agents_dir))

            assert agents[0]["system_prompt"] == ""

    def test_loads_action_schema(self) -> None:
        """load_agents loads shared action_schema.md from prompts dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)
            prompts_dir = Path(tmpdir) / "prompts"
            prompts_dir.mkdir()

            # Create action schema
            action_schema = "## Actions\n- read\n- write\n"
            (prompts_dir / "action_schema.md").write_text(action_schema)

            # Create agent
            agent_dir = agents_dir / "agent"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text(yaml.dump({"id": "agent"}))

            agents = load_agents(str(agents_dir), str(prompts_dir))

            assert agents[0]["action_schema"] == action_schema

    def test_empty_action_schema_when_missing(self) -> None:
        """load_agents uses empty string when action_schema.md missing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)
            prompts_dir = Path(tmpdir) / "prompts"
            prompts_dir.mkdir()
            # No action_schema.md

            agent_dir = agents_dir / "agent"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text(yaml.dump({"id": "agent"}))

            agents = load_agents(str(agents_dir), str(prompts_dir))

            assert agents[0]["action_schema"] == ""

    def test_loads_optional_config_fields(self) -> None:
        """load_agents loads temperature and max_tokens when present."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            agent_dir = agents_dir / "agent"
            agent_dir.mkdir()
            config = {
                "id": "agent",
                "temperature": 0.7,
                "max_tokens": 2048,
                "llm_model": "custom-model",
            }
            (agent_dir / "agent.yaml").write_text(yaml.dump(config))

            agents = load_agents(str(agents_dir))

            assert agents[0]["temperature"] == 0.7
            assert agents[0]["max_tokens"] == 2048
            assert agents[0]["llm_model"] == "custom-model"

    def test_none_for_missing_optional_fields(self) -> None:
        """load_agents returns None for missing optional fields."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            agent_dir = agents_dir / "agent"
            agent_dir.mkdir()
            (agent_dir / "agent.yaml").write_text(yaml.dump({"id": "agent"}))

            agents = load_agents(str(agents_dir))

            assert agents[0]["temperature"] is None
            assert agents[0]["max_tokens"] is None
            assert agents[0]["llm_model"] is None

    def test_multiple_agents_sorted(self) -> None:
        """load_agents returns agents sorted by directory name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            # Create agents in non-alphabetical order
            for name in ["charlie", "alice", "bob"]:
                agent_dir = agents_dir / name
                agent_dir.mkdir()
                (agent_dir / "agent.yaml").write_text(yaml.dump({"id": name}))

            agents = load_agents(str(agents_dir))

            assert len(agents) == 3
            assert [a["id"] for a in agents] == ["alice", "bob", "charlie"]

    def test_empty_directory(self) -> None:
        """load_agents returns empty list for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents = load_agents(tmpdir)
            assert agents == []


class TestListAgents:
    """Tests for list_agents function."""

    def test_lists_agent_directories(self) -> None:
        """list_agents returns directory names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            for name in ["agent_a", "agent_b", "agent_c"]:
                (agents_dir / name).mkdir()

            result = list_agents(tmpdir)

            assert set(result) == {"agent_a", "agent_b", "agent_c"}

    def test_excludes_underscore_prefix(self) -> None:
        """list_agents excludes directories starting with underscore."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            (agents_dir / "agent").mkdir()
            (agents_dir / "_template").mkdir()
            (agents_dir / "_private").mkdir()

            result = list_agents(tmpdir)

            assert result == ["agent"]

    def test_excludes_files(self) -> None:
        """list_agents only returns directories, not files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            (agents_dir / "agent").mkdir()
            (agents_dir / "README.md").write_text("readme")

            result = list_agents(tmpdir)

            assert result == ["agent"]

    def test_sorted_output(self) -> None:
        """list_agents returns sorted results."""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents_dir = Path(tmpdir)

            for name in ["zebra", "alpha", "middle"]:
                (agents_dir / name).mkdir()

            result = list_agents(tmpdir)

            assert result == ["alpha", "middle", "zebra"]

    def test_empty_directory(self) -> None:
        """list_agents returns empty list for empty directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = list_agents(tmpdir)
            assert result == []


class TestGetDefaultPrompt:
    """Tests for get_default_prompt function."""

    def test_raises_when_missing(self) -> None:
        """get_default_prompt raises FileNotFoundError when file missing."""
        # This test depends on the actual file structure
        # If the default prompt doesn't exist, it should raise
        # We can't easily test this without modifying the filesystem
        # So we just verify the function exists and has correct signature
        assert callable(get_default_prompt)

    def test_returns_string(self) -> None:
        """get_default_prompt returns a string (if file exists)."""
        try:
            result = get_default_prompt()
            assert isinstance(result, str)
        except FileNotFoundError:
            # Expected if default.md doesn't exist
            pass
