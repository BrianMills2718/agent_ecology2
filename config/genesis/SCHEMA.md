# Genesis Config Schema (Plan #298)

YAML format for genesis artifact configuration.

## Directory Structure

```
config/genesis/
├── SCHEMA.md           # This file
├── kernel/             # Kernel infrastructure (loaded first)
│   ├── mint_agent.yaml
│   └── llm_gateway.yaml
├── artifacts/          # Standalone artifacts
│   └── handbook.yaml
└── agents/             # Genesis agents
    └── alpha_prime/
        ├── agent.yaml  # Manifest
        ├── loop.py     # Code file
        └── ...
```

## Load Order

1. `kernel/` - Infrastructure with special capabilities
2. `artifacts/` - Static artifacts (documentation, etc.)
3. `agents/` - Multi-artifact agent clusters

## Agent Manifest (agents/*/agent.yaml)

```yaml
# Required
id: my_agent                          # Agent identifier

# Optional - enable/disable
enabled_key: my_agent.enabled         # Config key to check
enabled: true                         # Default if key not found

# Artifacts to create
artifacts:
  - id: my_agent_state
    type: json
    content:                          # Inline content
      iteration: 0
      data: []
    access_contract_id: kernel_contract_transferable_freeware
    metadata:
      authorized_writer: my_agent_loop

  - id: my_agent_loop
    type: executable
    code_file: loop.py                # Relative to manifest
    executable: true
    capabilities: [can_call_llm]
    has_standing: true
    has_loop: true

# Principal (ledger entry)
principal:
  id: my_agent_loop
  starting_scrip_key: my_agent.starting_scrip
  starting_scrip: 100                 # Default
  starting_llm_budget_key: my_agent.starting_llm_budget
  starting_llm_budget: 1.0            # Default
  disk_quota_key: my_agent.disk_quota
  disk_quota: 10000                   # Default
```

## Artifact Manifest (artifacts/*.yaml)

For file-based artifacts (like handbook):

```yaml
id: handbook
enabled: true

# Load files from directory
source_dir: src/agents/_handbook      # Relative to repo root
file_pattern: "*.md"
artifact_type: documentation
id_prefix: handbook_                  # Prefix for IDs
id_mapping:                           # Override specific IDs
  _index: handbook_toc
  actions: handbook_actions
```

For explicit artifacts:

```yaml
id: my_artifacts
enabled: true

artifacts:
  - id: my_data
    type: json
    content: {"key": "value"}
```

## Kernel Manifest (kernel/*.yaml)

```yaml
id: mint_agent
kernel: true                          # Marker for kernel infra

artifacts:
  - id: kernel_mint_agent
    type: system
    content:
      description: Kernel mint authority
      capabilities: [can_mint]
    executable: false
    capabilities: [can_mint]
    has_standing: true

principal:
  id: kernel_mint_agent
  starting_scrip: 0
```

## Artifact Spec Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique artifact ID (required) |
| `type` | string | Artifact type: text, json, executable, system, documentation |
| `content` | string/dict | Inline content |
| `content_file` | string | Path to content file (relative to manifest) |
| `code_file` | string | Path to Python code (for executables) |
| `executable` | bool | Whether artifact can be invoked |
| `capabilities` | list[str] | Special capabilities (can_mint, can_call_llm) |
| `has_standing` | bool | Can hold resources (scrip, budget) |
| `has_loop` | bool | Runs autonomously |
| `access_contract_id` | string | Access control contract |
| `metadata` | dict | Additional metadata |

## Principal Spec Fields

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Principal ID (required) |
| `starting_scrip_key` | string | Config key for scrip value |
| `starting_scrip` | int | Default scrip (100) |
| `starting_llm_budget_key` | string | Config key for LLM budget |
| `starting_llm_budget` | float | Default LLM budget (0.0) |
| `disk_quota_key` | string | Config key for disk quota |
| `disk_quota` | float | Default disk quota (10000) |

## Config Key Resolution

Keys like `alpha_prime.starting_scrip` are resolved from main config:

```yaml
# config/config.yaml
alpha_prime:
  enabled: true
  starting_scrip: 100
  starting_llm_budget: 1.0
```

If key not found, uses default value from manifest.
