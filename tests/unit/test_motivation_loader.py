"""Tests for motivation_loader (Plan #277)."""

import pytest
from pathlib import Path
import tempfile
import yaml

from src.agents.motivation_loader import (
    load_motivation_profile,
    assemble_motivation_prompt,
    get_motivation_prompt,
    get_motivation_for_agent,
)
from src.agents.agent_schema import MotivationSchema, TelosSchema, NatureSchema, DriveSchema


class TestMotivationSchema:
    """Test MotivationSchema validation."""

    def test_empty_motivation_is_valid(self) -> None:
        """Empty motivation schema should be valid (all fields optional)."""
        motivation = MotivationSchema()
        assert motivation.telos is None
        assert motivation.nature is None
        assert motivation.drives == {}

    def test_telos_schema(self) -> None:
        """Test TelosSchema validation."""
        telos = TelosSchema(name="Test Goal", prompt="Your goal is to test things.")
        assert telos.name == "Test Goal"
        assert "test things" in telos.prompt

    def test_nature_schema(self) -> None:
        """Test NatureSchema validation."""
        nature = NatureSchema(expertise="testing", prompt="You are a test expert.")
        assert nature.expertise == "testing"
        assert "test expert" in nature.prompt

    def test_drive_schema(self) -> None:
        """Test DriveSchema validation."""
        drive = DriveSchema(prompt="You want to test everything.")
        assert "test everything" in drive.prompt

    def test_full_motivation_schema(self) -> None:
        """Test complete MotivationSchema with all fields."""
        motivation = MotivationSchema(
            telos=TelosSchema(name="Test Telos", prompt="Test telos prompt"),
            nature=NatureSchema(expertise="testing", prompt="Test nature prompt"),
            drives={"curiosity": DriveSchema(prompt="Test curiosity drive")},
        )
        assert motivation.telos is not None
        assert motivation.telos.name == "Test Telos"
        assert motivation.nature is not None
        assert motivation.nature.expertise == "testing"
        assert "curiosity" in motivation.drives


class TestLoadMotivationProfile:
    """Test load_motivation_profile function."""

    def test_load_missing_profile_raises(self) -> None:
        """Loading a non-existent profile should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError, match="not found"):
            load_motivation_profile("nonexistent_profile")

    def test_load_empty_profile_raises(self) -> None:
        """Loading an empty profile should raise ValueError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_path = Path(tmpdir) / "empty.yaml"
            profile_path.write_text("")

            with pytest.raises(ValueError, match="is empty"):
                load_motivation_profile("empty", profiles_dir=Path(tmpdir))

    def test_load_valid_profile(self) -> None:
        """Test loading a valid profile."""
        with tempfile.TemporaryDirectory() as tmpdir:
            profile_data = {
                "motivation": {
                    "telos": {
                        "name": "Test Goal",
                        "prompt": "Test telos prompt",
                    },
                    "nature": {
                        "expertise": "testing",
                        "prompt": "Test nature prompt",
                    },
                    "drives": {
                        "curiosity": {"prompt": "Test curiosity drive"},
                    },
                }
            }
            profile_path = Path(tmpdir) / "test_profile.yaml"
            profile_path.write_text(yaml.dump(profile_data))

            motivation = load_motivation_profile("test_profile", profiles_dir=Path(tmpdir))
            assert motivation.telos is not None
            assert motivation.telos.name == "Test Goal"
            assert motivation.nature is not None
            assert motivation.nature.expertise == "testing"
            assert "curiosity" in motivation.drives


class TestAssembleMotivationPrompt:
    """Test assemble_motivation_prompt function."""

    def test_empty_motivation_returns_empty(self) -> None:
        """Empty motivation should return empty string."""
        motivation = MotivationSchema()
        prompt = assemble_motivation_prompt(motivation)
        assert prompt == ""

    def test_telos_only(self) -> None:
        """Test prompt with only telos."""
        motivation = MotivationSchema(
            telos=TelosSchema(name="Test Goal", prompt="Your goal is testing.")
        )
        prompt = assemble_motivation_prompt(motivation)
        assert "## Your Telos: Test Goal" in prompt
        assert "Your goal is testing." in prompt

    def test_full_motivation_prompt_order(self) -> None:
        """Test that full prompt has correct section order."""
        motivation = MotivationSchema(
            telos=TelosSchema(name="Test Telos", prompt="Telos content"),
            nature=NatureSchema(expertise="testing", prompt="Nature content"),
            drives={"drive1": DriveSchema(prompt="Drive1 content")},
        )
        prompt = assemble_motivation_prompt(motivation)

        # Check sections exist
        assert "## Your Telos: Test Telos" in prompt
        assert "## Your Nature (testing)" in prompt
        assert "## Your Drives" in prompt
        assert "### Drive1" in prompt

        # Check order (telos before nature before drives)
        telos_pos = prompt.find("Your Telos")
        nature_pos = prompt.find("Your Nature")
        drives_pos = prompt.find("Your Drives")

        assert telos_pos < nature_pos < drives_pos


class TestGetMotivationForAgent:
    """Test get_motivation_for_agent function."""

    def test_no_motivation_returns_none(self) -> None:
        """Agent config without motivation returns None."""
        config: dict = {"id": "test_agent"}
        result = get_motivation_for_agent(config)
        assert result is None

    def test_inline_motivation(self) -> None:
        """Test agent with inline motivation config."""
        config: dict = {
            "id": "test_agent",
            "motivation": {
                "telos": {"name": "Inline Goal", "prompt": "Inline telos"},
            },
        }
        result = get_motivation_for_agent(config)
        assert result is not None
        assert "Inline Goal" in result
        assert "Inline telos" in result

    def test_profile_reference(self) -> None:
        """Test agent with motivation_profile reference."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a profile
            profile_data = {
                "motivation": {
                    "telos": {"name": "Profile Goal", "prompt": "Profile telos"},
                }
            }
            profile_path = Path(tmpdir) / "test_profile.yaml"
            profile_path.write_text(yaml.dump(profile_data))

            config: dict = {
                "id": "test_agent",
                "motivation_profile": "test_profile",
            }
            result = get_motivation_for_agent(config, profiles_dir=Path(tmpdir))
            assert result is not None
            assert "Profile Goal" in result
            assert "Profile telos" in result
