"""Genesis artifact loader (Plan #298).

Loads genesis artifacts from config/genesis/ YAML files and creates them
in the world. This separates genesis data (sample agents, documentation)
from kernel code.

Usage:
    load_genesis(world, Path("config/genesis"))

Directory structure:
    config/genesis/
    ├── kernel/          # Kernel infrastructure (mint_agent, llm_gateway)
    ├── artifacts/       # Standalone artifacts (handbook)
    └── agents/          # Genesis agents (alpha_prime)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

from src.config import get as config_get

from .schema import AgentManifest, ArtifactManifest, ArtifactSpec, KernelManifest

if TYPE_CHECKING:
    from src.world.world import World

logger = logging.getLogger(__name__)


def load_genesis(
    world: "World",
    genesis_dir: Path | None = None,
    config: dict[str, Any] | None = None,
) -> None:
    """Load all genesis artifacts from config directory.

    Called by World.__init__ during bootstrap.

    Order:
    1. kernel/ - infrastructure (mint_agent, llm_gateway)
    2. artifacts/ - static artifacts (handbook)
    3. agents/ - genesis agents (alpha_prime)

    Args:
        world: The World instance to populate
        genesis_dir: Path to genesis config directory (default: config/genesis)
        config: Config dict (uses global config if not provided)
    """
    if genesis_dir is None:
        genesis_dir = Path("config/genesis")

    if not genesis_dir.exists():
        logger.warning(f"Genesis directory not found: {genesis_dir}")
        return

    # 1. Load kernel infrastructure first
    kernel_dir = genesis_dir / "kernel"
    if kernel_dir.exists():
        for manifest_file in sorted(kernel_dir.glob("*.yaml")):
            _load_kernel_manifest(world, manifest_file, config)

    # 2. Load standalone artifacts
    artifacts_dir = genesis_dir / "artifacts"
    if artifacts_dir.exists():
        for manifest_file in sorted(artifacts_dir.glob("*.yaml")):
            _load_artifact_manifest(world, manifest_file)

    # 3. Load agents
    agents_dir = genesis_dir / "agents"
    if agents_dir.exists():
        for agent_dir in sorted(agents_dir.iterdir()):
            if agent_dir.is_dir():
                manifest_file = agent_dir / "agent.yaml"
                if manifest_file.exists():
                    _load_agent_manifest(world, manifest_file, config)


def _get_config_value(config: dict[str, Any] | None, key: str, default: Any = None) -> Any:
    """Get a value from config dict by dotted key path.

    If config dict is provided, ONLY look in that dict (don't fall back to global).
    This allows tests to override the global config by passing a dict.

    If no config dict is provided, fall back to global config.
    """
    if config is not None:
        # Try to get from config dict using dotted key path
        parts = key.split(".")
        value = config
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                # Key not found in config dict - return default (don't use global)
                return default
        return value
    # No config dict provided, use global config
    return config_get(key, default)


def _load_kernel_manifest(
    world: "World", manifest_file: Path, config: dict[str, Any] | None = None
) -> None:
    """Load and create kernel infrastructure artifacts."""
    with open(manifest_file) as f:
        raw = yaml.safe_load(f)

    manifest = KernelManifest(**raw)
    logger.info(f"Loading kernel manifest: {manifest.id}")

    for artifact_spec in manifest.artifacts:
        _create_artifact(world, artifact_spec, manifest_file.parent)

    if manifest.principal:
        _create_principal(world, manifest.principal, config)


def _load_artifact_manifest(world: "World", manifest_file: Path) -> None:
    """Load and create standalone artifacts (e.g., handbook)."""
    with open(manifest_file) as f:
        raw = yaml.safe_load(f)

    manifest = ArtifactManifest(**raw)

    if not manifest.enabled:
        logger.debug(f"Skipping disabled manifest: {manifest.id}")
        return

    logger.info(f"Loading artifact manifest: {manifest.id}")

    # Handle file-based artifacts (like handbook)
    if manifest.source_dir:
        source_path = Path(manifest.source_dir)
        if not source_path.is_absolute():
            # Relative to repo root
            source_path = Path.cwd() / source_path

        if source_path.exists():
            for source_file in sorted(source_path.glob(manifest.file_pattern)):
                # Determine artifact ID
                stem = source_file.stem
                artifact_id = manifest.id_mapping.get(
                    stem, f"{manifest.id_prefix}{stem}"
                )

                content = source_file.read_text()
                world.artifacts.write(
                    artifact_id=artifact_id,
                    type=manifest.artifact_type,
                    content=content,
                    created_by="SYSTEM",
                    executable=False,
                )
                logger.debug(f"Created artifact: {artifact_id}")

    # Handle explicit artifacts
    for artifact_spec in manifest.artifacts:
        _create_artifact(world, artifact_spec, manifest_file.parent)


def _load_agent_manifest(
    world: "World", manifest_file: Path, config: dict[str, Any] | None = None
) -> None:
    """Load and create a genesis agent (multi-artifact cluster)."""
    with open(manifest_file) as f:
        raw = yaml.safe_load(f)

    manifest = AgentManifest(**raw)

    # Check if enabled via config key
    if manifest.enabled_key:
        enabled = _get_config_value(config, manifest.enabled_key, manifest.enabled)
    else:
        enabled = manifest.enabled

    if not enabled:
        logger.debug(f"Skipping disabled agent: {manifest.id}")
        return

    logger.info(f"Loading agent manifest: {manifest.id}")

    # Create all artifacts
    for artifact_spec in manifest.artifacts:
        _create_artifact(world, artifact_spec, manifest_file.parent)

    # Create principal if specified
    if manifest.principal:
        _create_principal(world, manifest.principal, config)


def _create_artifact(
    world: "World", spec: ArtifactSpec, base_dir: Path
) -> None:
    """Create a single artifact from spec."""
    # Resolve content
    content: str | dict[str, Any]
    code: str | None = None

    if spec.content is not None:
        # Inline content
        if isinstance(spec.content, dict):
            content = json.dumps(spec.content, indent=2)
        else:
            content = spec.content
    elif spec.content_file:
        # Content from file
        content_path = base_dir / spec.content_file
        content = content_path.read_text()
    else:
        content = ""

    # Resolve code for executables
    if spec.code_file:
        code_path = base_dir / spec.code_file
        code = code_path.read_text()

    # Create the artifact
    world.artifacts.write(
        artifact_id=spec.id,
        type=spec.type,
        content=content,
        created_by="SYSTEM",
        executable=spec.executable,
        code=code,
        capabilities=spec.capabilities if spec.capabilities else None,
        has_standing=spec.has_standing,
        has_loop=spec.has_loop,
        access_contract_id=spec.access_contract_id,
        metadata=spec.metadata if spec.metadata else None,
    )
    logger.debug(f"Created artifact: {spec.id}")


def _create_principal(
    world: "World", spec: "PrincipalSpec", config: dict[str, Any] | None = None
) -> None:
    """Create a principal in the ledger."""
    from decimal import Decimal

    # Resolve values from config or use defaults
    starting_scrip = spec.starting_scrip
    if spec.starting_scrip_key:
        starting_scrip = _get_config_value(config, spec.starting_scrip_key, starting_scrip)

    starting_llm_budget = spec.starting_llm_budget
    if spec.starting_llm_budget_key:
        starting_llm_budget = float(
            _get_config_value(config, spec.starting_llm_budget_key, starting_llm_budget)
        )

    disk_quota = spec.disk_quota
    if spec.disk_quota_key:
        disk_quota = float(_get_config_value(config, spec.disk_quota_key, disk_quota))

    # Create principal if not exists
    if not world.ledger.principal_exists(spec.id):
        world.ledger.create_principal(spec.id, starting_scrip=int(starting_scrip))

        # Set LLM budget if specified
        if starting_llm_budget > 0:
            world.ledger.set_resource(
                spec.id, "llm_budget", float(starting_llm_budget)
            )

    # Set up ResourceManager entry
    if hasattr(world, "resource_manager"):
        if not world.resource_manager.principal_exists(spec.id):
            world.resource_manager.create_principal(spec.id)
        world.resource_manager.set_quota(spec.id, "disk", disk_quota)

    logger.debug(f"Created principal: {spec.id}")
