"""Pydantic schemas for genesis config files (Plan #298).

These models validate the YAML config files in config/genesis/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class ArtifactSpec(BaseModel):
    """Specification for a single artifact to create."""

    id: str = Field(..., description="Unique artifact ID")
    type: str = Field(..., description="Artifact type (text, json, executable, etc.)")

    # Content sources (mutually exclusive)
    content: str | dict[str, Any] | None = Field(
        None, description="Inline content (string or dict)"
    )
    content_file: str | None = Field(
        None, description="Path to content file (relative to manifest)"
    )
    code_file: str | None = Field(
        None, description="Path to Python code file (for executables)"
    )

    # Artifact properties
    executable: bool = Field(False, description="Whether artifact is executable")
    capabilities: list[str] = Field(
        default_factory=list, description="Capabilities (e.g., can_call_llm)"
    )
    has_standing: bool = Field(False, description="Can hold resources")
    has_loop: bool = Field(False, description="Runs autonomously")

    # Access control
    access_contract_id: str | None = Field(
        None, description="Access contract for this artifact"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )
    state: dict[str, Any] = Field(
        default_factory=dict, description="Initial contract-managed state (Plan #311)"
    )


class PrincipalSpec(BaseModel):
    """Specification for a principal (ledger entry) to create."""

    id: str = Field(..., description="Principal ID (usually matches an artifact ID)")

    # Resource keys (read from main config)
    starting_scrip_key: str | None = Field(
        None, description="Config key for starting scrip (e.g., 'alpha_prime.starting_scrip')"
    )
    starting_llm_budget_key: str | None = Field(
        None, description="Config key for LLM budget"
    )
    disk_quota_key: str | None = Field(
        None, description="Config key for disk quota"
    )

    # Direct values (fallbacks)
    starting_scrip: int = Field(100, description="Default starting scrip")
    starting_llm_budget: float = Field(0.0, description="Default LLM budget")
    disk_quota: float = Field(10000.0, description="Default disk quota")


class AgentManifest(BaseModel):
    """Manifest for a genesis agent (multi-artifact cluster)."""

    id: str = Field(..., description="Agent identifier")
    enabled_key: str | None = Field(
        None, description="Config key to check if enabled (e.g., 'alpha_prime.enabled')"
    )
    enabled: bool = Field(True, description="Default enabled state")

    artifacts: list[ArtifactSpec] = Field(
        default_factory=list, description="Artifacts to create"
    )
    principal: PrincipalSpec | None = Field(
        None, description="Principal to register in ledger"
    )


class ArtifactManifest(BaseModel):
    """Manifest for standalone artifacts (e.g., handbook)."""

    id: str = Field(..., description="Manifest identifier")
    enabled: bool = Field(True, description="Whether to create these artifacts")

    # For file-based artifacts (like handbook)
    source_dir: str | None = Field(
        None, description="Directory containing source files"
    )
    file_pattern: str = Field("*.md", description="Glob pattern for source files")
    artifact_type: str = Field("documentation", description="Type for created artifacts")
    id_prefix: str = Field("", description="Prefix for artifact IDs")
    id_mapping: dict[str, str] = Field(
        default_factory=dict, description="filename -> artifact_id mapping"
    )

    # For explicit artifacts
    artifacts: list[ArtifactSpec] = Field(
        default_factory=list, description="Explicit artifact definitions"
    )


class KernelManifest(BaseModel):
    """Manifest for kernel infrastructure artifacts."""

    id: str = Field(..., description="Identifier")
    kernel: Literal[True] = Field(
        True, description="Marker that this is kernel infrastructure"
    )

    artifacts: list[ArtifactSpec] = Field(
        default_factory=list, description="Artifacts to create"
    )
    principal: PrincipalSpec | None = Field(
        None, description="Principal to register"
    )
