"""
Agent Loader - Discovers and loads agents from directory structure

Each agent lives in src/agents/<name>/ with:
  - agent.yaml: config (id, model, scrip, enabled)
  - system_prompt.md: the agent's system prompt

Artifact-Backed Agents (INT-004):
Agents can be created directly in the artifact store using create_agent_artifacts().
This enables:
- Persistent agent state across simulation restarts
- Agents as tradeable principals
- Memory artifacts linked to agents
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, TypedDict, TYPE_CHECKING

if TYPE_CHECKING:
    from ..world.artifacts import ArtifactStore, Artifact
    from .agent import Agent

# Resolve paths relative to project root
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent


class RAGConfigDict(TypedDict, total=False):
    """RAG configuration from agent.yaml."""
    enabled: bool
    limit: int
    query_template: str


class VisibilityConfigDict(TypedDict, total=False):
    """Resource visibility configuration from agent.yaml (Plan #93)."""
    resources: list[str]  # Which resources to show (None = use system default)
    detail_level: str  # "minimal", "standard", or "verbose"
    see_others: bool  # Whether to see other agents' resources


class AgentConfig(TypedDict, total=False):
    """Configuration for an agent."""
    id: str
    llm_model: str | None
    starting_scrip: int
    system_prompt: str
    action_schema: str
    temperature: float | None
    max_tokens: int | None
    rag: RAGConfigDict | None
    visibility: VisibilityConfigDict | None  # Plan #93: Resource visibility config


class AgentYamlConfig(TypedDict, total=False):
    """Configuration loaded from agent.yaml file."""
    id: str
    llm_model: str
    starting_scrip: int
    enabled: bool
    temperature: float
    max_tokens: int
    rag: RAGConfigDict
    visibility: VisibilityConfigDict  # Plan #93: Resource visibility config


def load_agents(agents_dir: str | None = None, prompts_dir: str | None = None) -> list[AgentConfig]:
    """
    Load all enabled agents from the agents directory.
    Returns list of agent configs with prompts loaded.
    """
    agents_path: Path = Path(agents_dir) if agents_dir else Path(__file__).parent
    prompts_path: Path = Path(prompts_dir) if prompts_dir else PROJECT_ROOT / "config" / "prompts"

    # Load shared action schema
    action_schema_path: Path = prompts_path / "action_schema.md"
    action_schema: str = ""
    if action_schema_path.exists():
        action_schema = action_schema_path.read_text()

    agents: list[AgentConfig] = []

    # Iterate through agent directories
    for agent_dir in sorted(agents_path.iterdir()):
        # Skip non-directories and template
        if not agent_dir.is_dir():
            continue
        if agent_dir.name.startswith("_"):
            continue

        config_path: Path = agent_dir / "agent.yaml"
        prompt_path: Path = agent_dir / "system_prompt.md"

        # Skip if missing required files
        if not config_path.exists():
            print(f"Warning: {agent_dir.name} missing agent.yaml, skipping")
            continue

        # Load config
        with open(config_path) as f:
            config: dict[str, Any] = yaml.safe_load(f)

        # Skip disabled agents
        if not config.get("enabled", True):
            continue

        # Load prompt
        system_prompt: str = ""
        if prompt_path.exists():
            system_prompt = prompt_path.read_text()

        # Build full agent config
        agent: AgentConfig = {
            "id": config.get("id", agent_dir.name),
            "llm_model": config.get("llm_model"),
            "starting_scrip": config.get("starting_scrip", 100),
            "system_prompt": system_prompt,
            "action_schema": action_schema,
            # Optional overrides
            "temperature": config.get("temperature"),
            "max_tokens": config.get("max_tokens"),
            # Per-agent RAG config (None = use global defaults)
            "rag": config.get("rag"),
            # Per-agent visibility config (Plan #93: None = use global defaults)
            "visibility": config.get("visibility"),
            # Workflow configuration (Plan #70)
            "workflow": config.get("workflow"),
            # Prompt components (Plan #150)
            "components": config.get("components"),
        }

        agents.append(agent)

    return agents


def list_agents(agents_dir: str = "agents") -> list[str]:
    """List all agent directory names (excluding template)"""
    agents_path: Path = Path(agents_dir)
    return [
        d.name for d in sorted(agents_path.iterdir())
        if d.is_dir() and not d.name.startswith("_")
    ]


def get_default_prompt() -> str:
    """
    Load the default system prompt for spawned agents.
    Returns the contents of prompts/default.md.
    """
    default_prompt_path: Path = Path(__file__).parent / "prompts" / "default.md"
    if not default_prompt_path.exists():
        raise FileNotFoundError(
            f"Default prompt not found at {default_prompt_path}"
        )
    return default_prompt_path.read_text()


def create_agent_artifacts(
    store: ArtifactStore,
    agent_configs: list[AgentConfig] | None = None,
    create_memory: bool = True,
) -> list[Artifact]:
    """Create agent artifacts in the artifact store.

    This function loads agent configs (or uses provided ones) and creates
    artifact representations for each agent in the store. This enables
    persistent agent state and artifact-backed agents.

    Args:
        store: Artifact store to create agents in
        agent_configs: Optional list of agent configs. If None, loads from disk.
        create_memory: Whether to create memory artifacts for each agent (default True)

    Returns:
        List of created agent artifacts

    Example:
        >>> store = ArtifactStore()
        >>> artifacts = create_agent_artifacts(store)
        >>> artifacts[0].is_agent
        True
    """
    from ..world.artifacts import create_agent_artifact, create_memory_artifact

    # Load configs if not provided
    if agent_configs is None:
        agent_configs = load_agents()

    created_artifacts: list[Artifact] = []

    for config in agent_configs:
        agent_id = config["id"]

        # Create memory artifact first if requested
        memory_artifact_id: str | None = None
        if create_memory:
            memory_id = f"{agent_id}_memory"
            memory_artifact = create_memory_artifact(
                memory_id=memory_id,
                created_by=agent_id,  # Agent owns its memory
            )
            store.artifacts[memory_id] = memory_artifact
            memory_artifact_id = memory_id

        # Build agent config dict for artifact content
        agent_config_dict: dict[str, Any] = {
            "llm_model": config.get("llm_model"),
            "system_prompt": config.get("system_prompt", ""),
            "action_schema": config.get("action_schema", ""),
        }
        if config.get("rag"):
            agent_config_dict["rag"] = config["rag"]
        if config.get("workflow"):
            agent_config_dict["workflow"] = config["workflow"]
        if config.get("components"):
            agent_config_dict["components"] = config["components"]

        # Create agent artifact (self-owned)
        agent_artifact = create_agent_artifact(
            agent_id=agent_id,
            created_by=agent_id,  # Self-owned
            agent_config=agent_config_dict,
            memory_artifact_id=memory_artifact_id,
        )
        store.artifacts[agent_id] = agent_artifact
        created_artifacts.append(agent_artifact)

    return created_artifacts


def load_agents_from_store(
    store: ArtifactStore,
    log_dir: str | None = None,
    run_id: str | None = None,
) -> list["Agent"]:
    """Load agents from artifact store.

    Creates Agent instances from all artifacts with is_agent=True in the store.

    Args:
        store: Artifact store containing agent artifacts
        log_dir: Directory for LLM logs
        run_id: Run ID for log organization

    Returns:
        List of Agent instances

    Example:
        >>> store = ArtifactStore()
        >>> create_agent_artifacts(store)
        >>> agents = load_agents_from_store(store)
        >>> agents[0].is_artifact_backed
        True
    """
    from .agent import Agent

    agents: list[Agent] = []

    for artifact in store.artifacts.values():
        if artifact.is_agent:
            agent = Agent.from_artifact(
                artifact,
                store=store,
                log_dir=log_dir,
                run_id=run_id,
            )
            agents.append(agent)

    return agents


if __name__ == "__main__":
    # Quick test
    agents: list[AgentConfig] = load_agents()
    print(f"Found {len(agents)} agents:")
    for a in agents:
        print(f"  - {a['id']}: {a['starting_scrip']} scrip")
        print(f"    prompt: {len(a['system_prompt'])} chars")
