"""
Motivation Profile Loader - Loads and assembles motivation prompts (Plan #277).

Motivation profiles define an agent's intrinsic drives and goals. They're
assembled from four layers:
1. Telos - the unreachable goal that orients everything
2. Nature - what the agent IS (expertise, identity)
3. Drives - what the agent WANTS (intrinsic motivations)
4. Personality - HOW the agent pursues its drives

Profiles can be:
- Referenced by name from config/motivation_profiles/
- Defined inline in agent.yaml

Usage:
    from src.agents.motivation_loader import load_motivation_profile, assemble_motivation_prompt

    # Load a profile by name
    profile = load_motivation_profile("discourse_analyst")

    # Assemble the prompt
    prompt_section = assemble_motivation_prompt(profile)

    # Or in one step:
    prompt_section = get_motivation_prompt("discourse_analyst")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from .agent_schema import MotivationSchema

logger = logging.getLogger(__name__)

# Default profiles directory
PROFILES_DIR = Path(__file__).parent.parent.parent / "config" / "motivation_profiles"


def load_motivation_profile(
    profile_name: str,
    profiles_dir: Path | None = None,
) -> MotivationSchema:
    """Load a motivation profile by name.

    Args:
        profile_name: Name of the profile (without .yaml extension)
        profiles_dir: Directory containing profile files. Defaults to
                     config/motivation_profiles/

    Returns:
        Validated MotivationSchema

    Raises:
        FileNotFoundError: If profile doesn't exist
        ValueError: If profile is invalid
    """
    dir_path = profiles_dir or PROFILES_DIR
    profile_path = dir_path / f"{profile_name}.yaml"

    if not profile_path.exists():
        raise FileNotFoundError(
            f"Motivation profile '{profile_name}' not found at {profile_path}"
        )

    logger.info(f"Loading motivation profile: {profile_name} from {profile_path}")

    with open(profile_path) as f:
        data = yaml.safe_load(f)

    if not data:
        raise ValueError(f"Motivation profile '{profile_name}' is empty")

    # Profile can have motivation at root or nested
    motivation_data = data.get("motivation", data)

    motivation = MotivationSchema.model_validate(motivation_data)

    # Log loaded motivation details
    if motivation.telos:
        logger.info(f"  Telos: {motivation.telos.name}")
    if motivation.nature:
        logger.info(f"  Nature: {motivation.nature.expertise}")
    if motivation.drives:
        logger.info(f"  Drives: {list(motivation.drives.keys())}")
    if motivation.personality:
        logger.info(f"  Personality: {motivation.personality.social_orientation}")

    return motivation


def assemble_motivation_prompt(motivation: MotivationSchema) -> str:
    """Assemble the motivation prompt from a MotivationSchema.

    The prompt is assembled in order:
    1. Telos prompt (if present)
    2. Nature prompt (if present)
    3. Drive prompts (concatenated)
    4. Personality prompt (if present)

    Args:
        motivation: The motivation schema to assemble

    Returns:
        Assembled prompt string with section headers
    """
    sections: list[str] = []

    # Telos - the unreachable goal
    if motivation.telos:
        sections.append(f"## Your Telos: {motivation.telos.name}")
        sections.append(motivation.telos.prompt.strip())

    # Nature - what you are
    if motivation.nature:
        sections.append(f"## Your Nature ({motivation.nature.expertise})")
        sections.append(motivation.nature.prompt.strip())

    # Drives - what you want
    if motivation.drives:
        sections.append("## Your Drives")
        for drive_name, drive in motivation.drives.items():
            sections.append(f"### {drive_name.title()}")
            sections.append(drive.prompt.strip())

    # Personality - how you pursue
    if motivation.personality and motivation.personality.prompt:
        sections.append("## Your Personality")
        sections.append(motivation.personality.prompt.strip())

    return "\n\n".join(sections)


def get_motivation_prompt(
    profile_name: str | None = None,
    motivation: MotivationSchema | None = None,
    profiles_dir: Path | None = None,
) -> str | None:
    """Get the assembled motivation prompt.

    Either loads a profile by name or uses an inline MotivationSchema.

    Args:
        profile_name: Name of profile to load from config/motivation_profiles/
        motivation: Inline MotivationSchema (takes precedence over profile_name)
        profiles_dir: Custom profiles directory

    Returns:
        Assembled prompt string, or None if no motivation configured
    """
    if motivation:
        # Inline motivation takes precedence
        return assemble_motivation_prompt(motivation)

    if profile_name:
        profile = load_motivation_profile(profile_name, profiles_dir)
        return assemble_motivation_prompt(profile)

    return None


def get_motivation_for_agent(
    agent_config: dict[str, Any],
    profiles_dir: Path | None = None,
) -> str | None:
    """Get the motivation prompt for an agent config.

    Checks for motivation_profile reference first, then inline motivation.

    Args:
        agent_config: The agent configuration dictionary
        profiles_dir: Custom profiles directory

    Returns:
        Assembled prompt string, or None if no motivation configured
    """
    # Check for profile reference
    profile_name = agent_config.get("motivation_profile")
    if profile_name:
        logger.debug(f"Loading motivation profile: {profile_name}")
        return get_motivation_prompt(profile_name=profile_name, profiles_dir=profiles_dir)

    # Check for inline motivation
    motivation_data = agent_config.get("motivation")
    if motivation_data:
        logger.debug("Using inline motivation config")
        motivation = MotivationSchema.model_validate(motivation_data)
        return get_motivation_prompt(motivation=motivation)

    return None


__all__ = [
    "load_motivation_profile",
    "assemble_motivation_prompt",
    "get_motivation_prompt",
    "get_motivation_for_agent",
    "PROFILES_DIR",
]
