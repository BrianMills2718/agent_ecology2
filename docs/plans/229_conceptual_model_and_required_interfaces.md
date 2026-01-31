# Plan 229: Conceptual Model and Required Interfaces

**Status:** Planned
**Priority:** High
**Blocked By:** None
**Blocks:** CC instance comprehension, architecture consistency

## Problem Statement

The codebase has drifted from its intended design:

1. **Interfaces are optional** - `interface: dict | None = None` allows artifacts without interfaces
2. **No conceptual model enforcement** - ADRs describe intent, code doesn't enforce it
3. **CC instances don't understand the system** - They pattern-match on code, miss the conceptual model
4. **Design influences lost** - MCP-inspired patterns, StructGPT terms buried in docs nobody reads

### Evidence

From ADR-0001:
```
interface: dict | None     # Required if has_loop=True
```

From code (artifacts.py):
```python
interface: dict[str, Any] | None = None  # No enforcement
```

Result: Most artifacts have no interface. CC instances see "artifacts are strings with optional stuff."

## Solution

### Phase 1: Define the Canonical Conceptual Model

Create `docs/CONCEPTUAL_MODEL.yaml` - machine-readable, validated, injected:

```yaml
# Canonical conceptual model - source of truth
version: 1

concepts:
  artifact:
    definition: "Unit of existence with interface, content, and contract"
    required_fields:
      - id: "Unique identifier"
      - interface: "MCP-inspired schema (REQUIRED)"
      - content: "Stored data (may be empty string)"
      - access_contract_id: "Contract governing access"
    optional_fields:
      - code: "Python with run() if executable"
      - metadata: "User-defined key-value pairs"
    is_not:
      - "Just a string"
      - "Data without interface"

  interface:
    definition: "MCP-inspired schema describing what artifact is and does"
    required_fields:
      - description: "Human-readable summary"
      - dataType: "Category: data | service | agent | contract"
    optional_fields:
      - methods: "List of callable operations (if executable)"
      - inputSchema: "JSON Schema for inputs"
      - outputSchema: "JSON Schema for outputs"
      - linearization: "Template for text representation (StructGPT)"
      - examples: "Example invocations"
      - cost: "Invocation cost hint"
    influences:
      - "MCP (Model Context Protocol) - tool definitions"
      - "StructGPT - dataType, linearization"

  contract:
    definition: "Access control rules - WHO can do WHAT"
    governs: "read, write, invoke permissions"
    is_not:
      - "Storage backend"
      - "Data format"
      - "Artifact type"
    note: "ANY artifact can have ANY contract - orthogonal"

  principal:
    definition: "Entity that can own things and be party to contracts"
    includes:
      - "Agents (has_standing=True, has_loop=True)"
      - "Non-agent principals (has_standing=True, has_loop=False)"
    has: "Scrip balance, resource quotas"

  kernel:
    definition: "Core that enforces rules and provides primitives"
    provides:
      - "KernelState (read-only): balances, resources, metadata"
      - "KernelActions (write): transfers, spending, creation"
    note: "Genesis artifacts use same primitives as agent-built - no privilege"

relationships:
  - subject: artifact
    predicate: governed_by
    object: contract
    cardinality: "exactly one"

  - subject: artifact
    predicate: owned_by
    object: principal
    cardinality: "exactly one"

  - subject: agent
    predicate: invokes
    object: artifact
    through: kernel

  - subject: contract
    predicate: orthogonal_to
    object: storage
    note: "Contract doesn't determine where data lives"

layers:
  - name: kernel
    description: "Primitives and enforcement"
    contains: ["KernelState", "KernelActions", "Ledger"]

  - name: genesis
    description: "Cold-start conveniences, unprivileged"
    contains: ["genesis_ledger", "genesis_escrow", "genesis_mint"]
    uses: kernel

  - name: agents
    description: "Users of the system"
    contains: ["Agent artifacts"]
    uses: [kernel, genesis]

common_mistakes:
  - wrong: "Artifacts are just strings with content"
    right: "Artifacts have interface (required), content, and contract"

  - wrong: "Genesis artifacts are special/privileged"
    right: "Genesis uses same kernel primitives as any artifact"

  - wrong: "Contract determines storage backend"
    right: "Contract determines access - storage is orthogonal"

  - wrong: "Interfaces are optional nice-to-have"
    right: "Interfaces are required - they define what the artifact IS"
```

### Phase 2: Make Interface Required in Code

Update `src/world/artifacts.py`:

```python
@dataclass
class ArtifactInterface:
    """Required interface for all artifacts (MCP-inspired + StructGPT)."""
    description: str  # Required: what is this
    dataType: str     # Required: data | service | agent | contract
    methods: list[dict] | None = None  # Optional: callable operations
    inputSchema: dict | None = None
    outputSchema: dict | None = None
    linearization: str | None = None  # StructGPT: text template
    examples: list[dict] | None = None
    cost: int | None = None

@dataclass
class Artifact:
    id: str
    type: str
    interface: ArtifactInterface  # REQUIRED, not Optional
    content: str
    # ... rest unchanged
```

Add validation:
```python
def validate_artifact(artifact: Artifact) -> list[str]:
    """Validate artifact meets conceptual model requirements."""
    errors = []
    if not artifact.interface:
        errors.append("interface is required")
    if not artifact.interface.description:
        errors.append("interface.description is required")
    if artifact.interface.dataType not in ["data", "service", "agent", "contract"]:
        errors.append(f"interface.dataType must be one of: data, service, agent, contract")
    if artifact.executable and not artifact.interface.methods:
        errors.append("executable artifacts must have interface.methods")
    return errors
```

### Phase 3: Inject Conceptual Model via Hook

Extend the governance injection hook to also inject conceptual model context:

```bash
# .claude/hooks/inject-conceptual-model.sh
# Inject relevant conceptual model context when reading src/ files
```

When CC reads any `src/` file, inject:
- Relevant concept definitions
- Common mistakes to avoid
- Layer context (which layer is this file in?)

### Phase 4: Migrate Existing Artifacts

Create migration script:
```bash
python scripts/migrate_artifact_interfaces.py --dry-run
python scripts/migrate_artifact_interfaces.py --apply
```

For each artifact without interface:
- Generate minimal interface from type/content
- Require human review for executables

### Phase 5: CI Enforcement

Add to CI:
```bash
python scripts/validate_conceptual_model.py --check
```

Validates:
- All artifacts have required interface fields
- Interface dataType is valid
- Executable artifacts have methods
- Conceptual model YAML is valid

## Test Plan

### Unit Tests
```python
# tests/unit/test_conceptual_model.py

def test_artifact_requires_interface():
    """Creating artifact without interface fails."""

def test_interface_requires_description():
    """Interface without description fails validation."""

def test_interface_requires_datatype():
    """Interface without dataType fails validation."""

def test_executable_requires_methods():
    """Executable artifact without methods fails."""

def test_datatype_must_be_valid():
    """Invalid dataType rejected."""
```

### Integration Tests
```python
def test_conceptual_model_yaml_valid():
    """CONCEPTUAL_MODEL.yaml parses and validates."""

def test_all_genesis_artifacts_have_interfaces():
    """All genesis artifacts meet interface requirements."""

def test_hook_injects_conceptual_context():
    """Reading src/ file injects conceptual model context."""
```

## Acceptance Criteria

- [ ] `docs/CONCEPTUAL_MODEL.yaml` defines all core concepts
- [ ] `interface` field is required (not Optional) in Artifact dataclass
- [ ] `ArtifactInterface` dataclass with required fields
- [ ] Validation rejects artifacts without proper interface
- [ ] All genesis artifacts have valid interfaces
- [ ] Hook injects conceptual model when reading src/ files
- [ ] CI validates conceptual model compliance
- [ ] Migration script for existing artifacts
- [ ] Unit tests pass
- [ ] Integration tests pass

## Files to Create/Modify

### Create
- `docs/CONCEPTUAL_MODEL.yaml` - Canonical conceptual model
- `scripts/validate_conceptual_model.py` - CI validation
- `scripts/migrate_artifact_interfaces.py` - Migration tool
- `.claude/hooks/inject-conceptual-model.sh` - Context injection
- `tests/unit/test_conceptual_model.py` - Unit tests

### Modify
- `src/world/artifacts.py` - Make interface required, add ArtifactInterface
- `src/world/genesis.py` - Add interfaces to all genesis artifacts
- `src/world/genesis/*.py` - Add interfaces to genesis package artifacts
- `.claude/settings.json` - Add conceptual model hook

## Open Questions

1. **Strictness level**: Should we reject artifacts without interface immediately, or have a migration period with warnings?

2. **Interface for data artifacts**: What's the minimal interface for a pure data artifact (no methods)?

3. **Versioning**: How do we handle interface schema evolution?

4. **Performance**: Does validation on every artifact creation add noticeable overhead?

## Why This Matters

Without a enforced conceptual model:
- CC instances pattern-match on code, miss the design
- Documentation describes intent, implementation diverges
- Each CC session rediscovers (or misunderstands) the architecture
- The system becomes what the code says, not what we intended

With enforced conceptual model:
- Code and design stay aligned
- CC instances get the model injected, understand the system
- Validation catches drift early
- The system becomes what we designed
