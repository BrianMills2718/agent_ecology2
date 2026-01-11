"""
Agent Loader - Discovers and loads agents from directory structure

Each agent lives in src/agents/<name>/ with:
  - agent.yaml: config (id, model, scrip, enabled)
  - system_prompt.md: the agent's system prompt
"""

import yaml
from pathlib import Path
from typing import Any, TypedDict


# Resolve paths relative to project root
PROJECT_ROOT: Path = Path(__file__).parent.parent.parent


class RAGConfigDict(TypedDict, total=False):
    """RAG configuration from agent.yaml."""
    enabled: bool
    limit: int
    query_template: str


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


class AgentYamlConfig(TypedDict, total=False):
    """Configuration loaded from agent.yaml file."""
    id: str
    llm_model: str
    starting_scrip: int
    enabled: bool
    temperature: float
    max_tokens: int
    rag: RAGConfigDict


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


if __name__ == "__main__":
    # Quick test
    agents: list[AgentConfig] = load_agents()
    print(f"Found {len(agents)} agents:")
    for a in agents:
        print(f"  - {a['id']}: {a['starting_scrip']} scrip")
        print(f"    prompt: {len(a['system_prompt'])} chars")
