"""Tests for VSM-aligned agents (Plan #82).

Verifies that alpha_2 and beta_2 agents have the expected
workflow configurations for self-audit and goal hierarchies.
"""

import pytest
import yaml
from pathlib import Path

from src.config import get_validated_config


@pytest.mark.plans([82])
class TestVSMAgents:
    """Tests for VSM-aligned agent configurations."""

    def test_alpha_2_exists(self) -> None:
        """alpha_2 agent directory exists with required files."""
        agent_dir = Path("src/agents/alpha_2")
        assert agent_dir.exists(), "alpha_2 agent directory should exist"
        assert (agent_dir / "agent.yaml").exists(), "alpha_2 should have agent.yaml"
        assert (agent_dir / "system_prompt.md").exists(), "alpha_2 should have system_prompt.md"

    def test_beta_2_exists(self) -> None:
        """beta_2 agent directory exists with required files."""
        agent_dir = Path("src/agents/beta_2")
        assert agent_dir.exists(), "beta_2 agent directory should exist"
        assert (agent_dir / "agent.yaml").exists(), "beta_2 should have agent.yaml"
        assert (agent_dir / "system_prompt.md").exists(), "beta_2 should have system_prompt.md"

    def test_alpha_2_workflow_has_self_audit(self) -> None:
        """alpha_2 workflow includes self_audit step for VSM S3*."""
        agent_yaml = Path("src/agents/alpha_2/agent.yaml")
        with open(agent_yaml) as f:
            config = yaml.safe_load(f)

        assert "workflow" in config, "alpha_2 should have workflow config"
        steps = config["workflow"].get("steps", [])
        step_names = [s.get("name") for s in steps]

        assert "self_audit" in step_names, "alpha_2 workflow should include self_audit step"
        assert "compute_metrics" in step_names, "alpha_2 workflow should include compute_metrics step"

    def test_alpha_2_has_adaptation_trigger(self) -> None:
        """alpha_2 workflow computes should_pivot adaptation trigger."""
        agent_yaml = Path("src/agents/alpha_2/agent.yaml")
        with open(agent_yaml) as f:
            config = yaml.safe_load(f)

        # Find compute_metrics step
        steps = config["workflow"].get("steps", [])
        compute_step = next((s for s in steps if s.get("name") == "compute_metrics"), None)
        assert compute_step is not None, "compute_metrics step should exist"

        code = compute_step.get("code", "")
        assert "should_pivot" in code, "compute_metrics should calculate should_pivot"
        assert "success_rate" in code, "compute_metrics should calculate success_rate"

    def test_beta_2_has_goal_hierarchy(self) -> None:
        """beta_2 workflow includes goal hierarchy tracking."""
        agent_yaml = Path("src/agents/beta_2/agent.yaml")
        with open(agent_yaml) as f:
            config = yaml.safe_load(f)

        assert "workflow" in config, "beta_2 should have workflow config"
        steps = config["workflow"].get("steps", [])
        step_names = [s.get("name") for s in steps]

        assert "load_goals" in step_names, "beta_2 should have load_goals step"
        assert "strategic_review" in step_names, "beta_2 should have strategic_review step"

    def test_beta_2_tracks_subgoal_progress(self) -> None:
        """beta_2 workflow tracks subgoal progress."""
        agent_yaml = Path("src/agents/beta_2/agent.yaml")
        with open(agent_yaml) as f:
            config = yaml.safe_load(f)

        steps = config["workflow"].get("steps", [])
        load_goals_step = next((s for s in steps if s.get("name") == "load_goals"), None)
        assert load_goals_step is not None, "load_goals step should exist"

        code = load_goals_step.get("code", "")
        assert "strategic_goal" in code, "load_goals should extract strategic_goal"
        assert "current_subgoal" in code, "load_goals should extract current_subgoal"
        assert "subgoal_progress" in code, "load_goals should track subgoal_progress"

    def test_working_memory_recommended(self) -> None:
        """Working memory configuration exists and can be enabled.

        Note: Working memory defaults to disabled (per project philosophy
        of 'avoid defaults'). For best results with VSM-aligned agents,
        set working_memory.enabled=true in config.
        """
        config = get_validated_config()
        # Verify working memory config exists and is configurable
        assert hasattr(config.agent, "working_memory"), \
            "Working memory config should exist"
        assert hasattr(config.agent.working_memory, "enabled"), \
            "Working memory should have enabled flag"
        # Note: we don't require it to be enabled by default


@pytest.mark.plans([82])
class TestVSMAgentGenotypes:
    """Tests for VSM agent genotype differentiation."""

    def test_alpha_2_is_build_focused(self) -> None:
        """alpha_2 genotype traits favor building."""
        agent_yaml = Path("src/agents/alpha_2/agent.yaml")
        with open(agent_yaml) as f:
            content = f.read()

        # Check genotype comments
        assert "WRITE-HEAVY" in content or "Build" in content.lower(), \
            "alpha_2 should have build-focused traits"

    def test_beta_2_is_integration_focused(self) -> None:
        """beta_2 genotype traits favor integration."""
        agent_yaml = Path("src/agents/beta_2/agent.yaml")
        with open(agent_yaml) as f:
            content = f.read()

        # Check genotype comments
        assert "READ-HEAVY" in content or "integrat" in content.lower(), \
            "beta_2 should have integration-focused traits"

    def test_agents_have_different_rag_templates(self) -> None:
        """alpha_2 and beta_2 have differentiated RAG query templates."""
        alpha_yaml = Path("src/agents/alpha_2/agent.yaml")
        beta_yaml = Path("src/agents/beta_2/agent.yaml")

        with open(alpha_yaml) as f:
            alpha_config = yaml.safe_load(f)
        with open(beta_yaml) as f:
            beta_config = yaml.safe_load(f)

        alpha_template = alpha_config.get("rag", {}).get("query_template", "")
        beta_template = beta_config.get("rag", {}).get("query_template", "")

        assert alpha_template != beta_template, \
            "Agents should have different RAG templates reflecting their focus"
