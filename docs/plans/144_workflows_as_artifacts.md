# Plan 144: Workflows as Tradeable Artifacts

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** Agent self-modification, workflow marketplace

---

## Overview

Currently, agent workflows (the sequence of thinking steps, prompts, and state machines) are defined in `agent.yaml` files and loaded at startup. Agents cannot:
- Modify their own workflow at runtime
- Trade workflows with other agents
- Evolve better reasoning processes

We will extract workflows into first-class **Workflow Artifacts** that agents can create, trade, and swap dynamically. This enables agents to evolve HOW they think, not just WHAT they know.

**Critical Design Principle:** The agent's "brain" becomes part of the simulation economy. Effective thinking patterns become valuable tradeable goods.

---

## Design

### 1. WorkflowArtifact Type

```python
# New artifact type: "workflow"
# Contains the full workflow definition as YAML/JSON

artifact = {
    "id": "alpha_build_workflow_v2",
    "type": "workflow",
    "created_by": "alpha",
    "executable": False,  # Workflows are data, not code
    "content": '''
state_machine:
  states: [observing, planning, executing, reflecting]
  initial_state: observing
  transitions:
    - from: observing
      to: planning
      condition: "has_opportunity"
    - from: planning
      to: executing
    - from: executing
      to: reflecting
    - from: reflecting
      to: observing

steps:
  - name: observe_market
    type: code
    in_state: [observing]
    code: |
      context["opportunities"] = []
      for artifact in context["available_artifacts"]:
        if artifact["price"] < context["balance"] * 0.1:
          context["opportunities"].append(artifact)
      context["has_opportunity"] = len(context["opportunities"]) > 0
    transition_to: planning

  - name: plan_action
    type: llm
    in_state: [planning]
    prompt: |
      You are {agent_id} with {balance} scrip.
      Opportunities: {opportunities}
      Plan your next action.
    transition_to: executing

  - name: execute_plan
    type: llm
    in_state: [executing]
    prompt: |
      Execute your plan. Available actions: {action_schema}
    transition_to: reflecting

  - name: reflect
    type: code
    in_state: [reflecting]
    code: |
      # Update memory with outcome
      context["reflection"] = f"Action result: {context.get('last_result')}"
    transition_to: observing

error_handling:
  default_on_failure: retry
  max_retries: 3
'''
}
```

### 2. Agent Workflow Reference

Agents store a reference to their active workflow artifact:

```yaml
# In agent artifact content
id: alpha
workflow_artifact_id: alpha_build_workflow_v2  # Required
llm_model: gemini/gemini-2.0-flash
# ...
```

### 3. Workflow Loading

```python
# In agent.py
def get_workflow(self) -> WorkflowConfig:
    """Load workflow from artifact."""
    if self._workflow_artifact_id:
        artifact = self._world.artifacts.get(self._workflow_artifact_id)
        if artifact:
            return WorkflowConfig.from_yaml(artifact.content)
    # Fallback to embedded config or default
    return self._default_workflow
```

### 4. Agent Self-Modification

Agents can create and switch workflows:

```python
# Agent creates improved workflow
action = {
    "action_type": "write_artifact",
    "artifact_id": "alpha_workflow_v3",
    "artifact_type": "workflow",
    "content": "<new workflow YAML>"
}

# Agent switches to new workflow
action = {
    "action_type": "invoke_artifact",
    "artifact_id": "genesis_store",
    "method": "update_agent_config",
    "args": [{"workflow_artifact_id": "alpha_workflow_v3"}]
}
```

### 5. Workflow Trading

Workflows are artifacts, enabling:
- **Discovery**: Find workflows via genesis_store
- **Reading**: Inspect other agents' workflows (if contract allows)
- **Copying**: Create derivative workflows
- **Trading**: Sell effective workflows on escrow

### 6. Workflow Evolution via Mint

Agents can use the mint to generate improved workflows:

```python
# Agent submits current workflow for improvement
action = {
    "action_type": "invoke_artifact",
    "artifact_id": "genesis_mint",
    "method": "submit_for_scoring",
    "args": [{
        "artifact_id": "alpha_workflow_v2",
        "improvement_request": "Optimize for faster decision-making"
    }]
}
```

---

## Implementation

### Phase 1: Workflow Artifact Type

1. **Add workflow artifact type** (`artifacts.py`)
   - `artifact_type = "workflow"`
   - Validate workflow structure on creation

2. **Create workflow validator** (`workflow.py`)
   - `validate_workflow_artifact(content: str) -> bool`
   - Check required fields: steps, state_machine (optional)

3. **Update WorkflowConfig** (`workflow.py`)
   - Add `from_yaml(content: str)` class method
   - Add `to_yaml() -> str` method for serialization

### Phase 2: Agent Integration

4. **Update agent config** (`agent.py`)
   - Add `workflow_artifact_id: str | None` field
   - Update `get_workflow()` to load from artifact
   - Add `reload_workflow()` method

5. **Update agent loader** (`loader.py`)
   - For artifact-backed agents, read workflow_artifact_id
   - Create default workflow artifact if not present

6. **Seed genesis workflows** (`genesis.py`)
   - `genesis_default_workflow` - basic observe/think/act cycle
   - `genesis_trading_workflow` - optimized for trading
   - `genesis_builder_workflow` - optimized for artifact creation

### Phase 3: Trading & Discovery

7. **Add workflow discovery** (`genesis/store.py`)
   - `list_workflows()` - list available workflow artifacts
   - `get_workflow_interface()` - describe workflow structure

8. **Enable workflow trading** (existing escrow)
   - Workflows listed/purchased like any artifact

### Phase 4: Agent Self-Modification API

9. **Add config update to genesis_store**
   - `update_agent_config(config_updates: dict)` method
   - Allows setting workflow_artifact_id, reflex_artifact_id, etc.
   - Only allows agent to update own config

---

## Files Affected

| File | Change |
|------|--------|
| `src/world/artifacts.py` | Add "workflow" artifact type |
| `src/agents/agent.py` | Add workflow_artifact_id, load from artifact |
| `src/agents/workflow.py` | Add from_yaml/to_yaml, validation |
| `src/agents/loader.py` | Load workflow from artifact |
| `src/world/genesis.py` | Seed genesis workflows |
| `src/world/genesis/store.py` | Agent config updates |
| `config/schema.yaml` | Workflow artifact config |

---

## Required Tests

| Test | Description |
|------|-------------|
| `test_workflow_artifact_creation` | Can create artifact with type="workflow" |
| `test_workflow_artifact_validation` | Invalid workflows rejected |
| `test_agent_loads_workflow_from_artifact` | Agent uses workflow_artifact_id |
| `test_agent_switch_workflow` | Agent can change workflow at runtime |
| `test_workflow_reload_on_change` | Workflow reloads when artifact updated |
| `test_workflow_discovery` | Can list workflows via genesis_store |
| `test_workflow_trading` | Can trade workflows via escrow |
| `test_genesis_workflows_seeded` | Genesis workflows created at startup |

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Workflows loadable from artifacts | Agent uses artifact content |
| Agents can self-modify | Switch workflow_artifact_id |
| Workflows tradeable | Listed/purchased on escrow |
| Genesis workflows seeded | Default workflows available |
| Graceful degradation | Missing workflow falls back to default |

---

## Migration Path

1. **Phase 1**: Add workflow artifact support, keep YAML fallback
2. **Phase 2**: Migrate existing agents to use workflow artifacts
3. **Phase 3**: Deprecate inline workflow YAML (optional)

Existing agents continue to work unchanged until explicitly migrated.

---

## ADRs Applied

- ADR-0001: Everything is an Artifact (workflows are artifacts)
- ADR-0013: Configurable Agent Workflows (extends to runtime configuration)
- ADR-0014: Continuous Execution Primary (workflows can optimize for speed)

---

## Future Enhancements

- **Workflow versioning**: Track workflow history, rollback on failure
- **Workflow metrics**: Dashboard showing workflow effectiveness
- **Workflow mutation**: LLM-generated workflow improvements
- **Workflow composition**: Combine steps from multiple workflows
