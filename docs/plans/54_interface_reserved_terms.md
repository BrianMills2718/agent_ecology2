# Gap 54: Interface Reserved Terms

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** #14 (Artifact Interface Schema - Complete)
**Blocks:** None

---

## Gap

**Current:** Artifacts have an optional `interface` field (Plan #14), but no guidance on structure. Dashboard doesn't display interface information.

**Target:** Define reserved terms for artifact interfaces that enable discoverability. Dashboard renders recognized fields nicely. No mandates - conventions only.

**Why Medium:** Improves agent-to-agent discoverability and dashboard observability without constraining emergence.

---

## Background

This plan synthesizes insights from:

1. **MCP (Model Context Protocol)** - Tool schemas with `inputSchema`/`outputSchema`
2. **StructGPT paper** - Linearization, data type categories, progressive narrowing
3. **Project philosophy** - Reserved terms, not mandates; peer-to-peer benefit framing

### Key Design Decisions

1. **Reserved terms, not mandates** - Agents choose what to include
2. **Peer-to-peer framing** - Benefits are for other agents, not "the system"
3. **Dashboard opportunistically renders** - Shows what's available, gracefully degrades

---

## Reserved Terms

These field names have conventional meanings. Agents may use them for discoverability.

### Core Terms (MCP-aligned)

| Term | Type | Description |
|------|------|-------------|
| `description` | `string` | Human-readable summary of artifact |
| `methods` | `array` | List of callable operations |
| `inputSchema` | `object` | JSON Schema for method inputs |
| `outputSchema` | `object` | JSON Schema for method outputs |

### StructGPT-inspired Terms

| Term | Type | Description |
|------|------|-------------|
| `dataType` | `string` | Category hint: `table`, `knowledge_graph`, `service`, `document` |
| `linearization` | `string` | Template for converting output to readable text |

### Learning Aids

| Term | Type | Description |
|------|------|-------------|
| `examples` | `array` | Example invocations with input/output pairs |

### Economic Terms

| Term | Type | Description |
|------|------|-------------|
| `cost` | `number` | Per-method cost hint (supplements artifact `invoke_price`) |
| `errors` | `array` | Possible error codes this method returns |

---

## Interface Structure Examples

### Minimal (description only)

```json
{
  "description": "Stores and retrieves notes"
}
```

### With Methods

```json
{
  "description": "Calculator service",
  "dataType": "service",
  "methods": [
    {
      "name": "add",
      "description": "Add two numbers",
      "inputSchema": {
        "type": "object",
        "properties": {
          "a": {"type": "number"},
          "b": {"type": "number"}
        },
        "required": ["a", "b"]
      },
      "outputSchema": {"type": "number"},
      "cost": 0
    }
  ]
}
```

### Full StructGPT-style

```json
{
  "description": "Movie knowledge graph",
  "dataType": "knowledge_graph",
  "methods": [
    {
      "name": "get_relations",
      "description": "Get all relations for an entity",
      "inputSchema": {
        "type": "object",
        "properties": {
          "entity": {"type": "string"}
        },
        "required": ["entity"]
      },
      "outputSchema": {
        "type": "array",
        "items": {"type": "string"}
      },
      "linearization": "Relations: {result.join(', ')}",
      "cost": 1,
      "errors": ["ENTITY_NOT_FOUND"],
      "examples": [
        {
          "input": {"entity": "Spielberg"},
          "output": ["directed", "produced", "wrote"]
        }
      ]
    }
  ]
}
```

---

## Plan

### Phase 1: Documentation

Document reserved terms for agents:

1. Update `docs/architecture/current/artifacts_executor.md` with reserved terms section
2. Add interface examples to genesis artifacts (GenesisLedger, GenesisMint, etc.)
3. Update agent handbook with interface conventions

### Phase 2: Dashboard Display

Extend dashboard to render interfaces:

1. Add `interface` field to `ArtifactDetail` model
2. Create interface rendering in artifact detail view:
   - Show `description` prominently
   - Render `methods` as expandable list
   - Show `inputSchema`/`outputSchema` as formatted JSON
   - Display `examples` as copyable snippets
   - Show `dataType` as a badge/tag
3. Graceful degradation - show raw JSON if structure not recognized

### Phase 3: Genesis Artifact Interfaces

Update genesis artifacts to demonstrate patterns:

```python
# genesis_ledger interface
{
    "description": "Scrip balances and transfers",
    "dataType": "service",
    "methods": [
        {
            "name": "balance",
            "description": "Get balance for principal",
            "inputSchema": {"principal_id": "string"},
            "outputSchema": {"balance": "number"},
            "linearization": "{principal_id} has {balance} scrip",
            "cost": 0,
            "errors": ["PRINCIPAL_NOT_FOUND"],
            "examples": [
                {"input": {"principal_id": "alice"}, "output": {"balance": 100}}
            ]
        },
        {
            "name": "transfer",
            "description": "Transfer scrip to another principal",
            "inputSchema": {
                "from": "string (caller)",
                "to": "string",
                "amount": "integer, minimum 1"
            },
            "outputSchema": {"success": "boolean", "new_balance": "number"},
            "cost": 0,
            "errors": ["INSUFFICIENT_BALANCE", "INVALID_RECIPIENT"]
        }
    ]
}
```

---

## Changes Required

| File | Change |
|------|--------|
| `docs/architecture/current/artifacts_executor.md` | Add Interface Reserved Terms section |
| `src/dashboard/models.py` | Add `interface` to `ArtifactDetail` |
| `src/dashboard/parser.py` | Parse interface from artifact data |
| `src/dashboard/static/` | Render interface in artifact detail view |
| `src/world/genesis.py` | Add full interfaces to genesis artifacts |
| `docs/AGENT_HANDBOOK.md` | Document interface conventions for agents |

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_interface_terms.py` | `test_interface_description_only` | Minimal interface works |
| `tests/unit/test_interface_terms.py` | `test_interface_with_methods` | Methods array recognized |
| `tests/unit/test_interface_terms.py` | `test_interface_full_example` | All reserved terms work |
| `tests/unit/test_dashboard_models.py` | `test_artifact_detail_has_interface` | Model includes interface |
| `tests/integration/test_genesis_interface.py` | `test_genesis_ledger_interface` | Genesis has interface |
| `tests/integration/test_genesis_interface.py` | `test_genesis_mint_interface` | Genesis has interface |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_artifact_interface.py` | Plan #14 interface tests |
| `tests/integration/test_genesis_*` | Genesis artifacts unchanged |
| `tests/unit/test_dashboard_*` | Dashboard still works |

---

## Dashboard Display Specification

### Artifact Detail View

When viewing an artifact, if `interface` exists:

```
┌─────────────────────────────────────────────────────────┐
│ artifact_id: calculator_v1                              │
│ type: executable    owner: alice    [service]          │
│                                     ↑ dataType badge    │
├─────────────────────────────────────────────────────────┤
│ Calculator service for basic arithmetic                 │
│ ↑ description                                           │
├─────────────────────────────────────────────────────────┤
│ Methods:                                                │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ▼ add - Add two numbers                    cost: 0  │ │
│ │   Input: { a: number, b: number }                   │ │
│ │   Output: number                                    │ │
│ │   Example: add({a: 1, b: 2}) → 3                   │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─────────────────────────────────────────────────────┐ │
│ │ ▶ subtract - Subtract two numbers          cost: 0  │ │
│ └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

### Graceful Degradation

| Interface Content | Display |
|-------------------|---------|
| Full structure | Rich rendering as above |
| `description` only | Show description, note "No method definitions" |
| Unknown structure | Show raw JSON with "Custom interface format" label |
| `interface: null` | Show "No interface defined" |

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 53`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] `docs/architecture/current/artifacts_executor.md` updated with reserved terms
- [ ] `docs/AGENT_HANDBOOK.md` updated with interface conventions
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes

### Philosophy Alignment

This plan follows project principles:

1. **Minimal kernel, maximum flexibility** - Reserved terms, not mandates
2. **Observe, don't prevent** - No enforcement, just conventions
3. **Selection pressure** - Well-documented artifacts get used more
4. **Genesis as examples** - Genesis artifacts demonstrate patterns

### Framing for Agents

Documentation should NOT say "the system rewards this" but rather:

> "Reserved terms for artifact interfaces. Other agents may use these for discovery. Convention, not requirement."

The peer-to-peer benefit framing maintains immersion - agents don't know there's an observer benefiting from structure.

### References

- **StructGPT paper**: `docs/references/structgpt.txt`
- **MCP Protocol**: https://modelcontextprotocol.io/
- **Plan #14**: `docs/plans/14_mcp_interface.md` (interface field added)
- **Architecture decision**: `docs/ARCHITECTURE_DECISIONS_2026_01.md` (Don't Mandate MCP)
