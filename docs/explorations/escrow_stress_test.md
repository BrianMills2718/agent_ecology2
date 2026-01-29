# Exploration: Escrow Stress Test Insights

**Status:** Insights captured
**Date:** 2026-01-28

Insights from walking through a complex escrow artifact example to stress-test the conceptual model.

## Contracts Are Just Artifacts

**Status:** ESTABLISHED (85% confidence)

Contracts are NOT a special kernel type. They are just artifacts that implement the `check_permission` interface. The kernel calls `check_permission()` on whatever artifact `access_contract_id` points to.

**Implications:**
- No special "contract" type in kernel - just artifacts with an interface
- Any artifact can be a contract if it implements `check_permission`
- Kernel doesn't know or care if something is "a contract" - just calls the interface

---

## Self-Referential Access (Constitution Pattern)

**Status:** ESTABLISHED (80% confidence)

`access_contract_id` can point to SELF. This is the "constitution" pattern - an artifact that governs its own access.

**Key distinction:** Self-reference does NOT mean "same rules for everyone."

A self-referential artifact has TWO COMPLETE ACCESS CONTROL RULESETS:
1. **Governance rules:** For artifacts that use me as their contract
2. **Self-access rules:** For access to ME (the contract artifact itself)

Both are FULL access control. The `check_permission` function distinguishes by checking if `target_artifact_id == self.id`.

```python
def check_permission(caller, operation, context):
    if context.target_artifact_id == self.id:
        # Accessing ME - apply my self-access rules
        return self.self_access_rules.check(caller, operation, context)
    else:
        # Accessing another artifact that uses me - apply governance rules
        return self.governance_rules.check(caller, operation, context)
```

Self-reference terminates the access chain. No infinite regress. No need for a special kernel "root contract."

---

## Contract Scope Is Self-Defined

**Status:** ESTABLISHED (75% confidence)

Contracts define their own scope - what state they query, what operations they govern. Like a constitution defining its own limits, not just the limits of what it governs.

**Mechanism:** Kernel passes target artifact state as part of context to `check_permission`. Contract decides what to examine and what rules to apply.

---

## Artifacts Can Have Standing

**Status:** ESTABLISHED (80% confidence)

Artifacts CAN have standing (hold scrip). `has_standing` is an independent property. This is necessary for value-holding use cases like escrow.

**Mechanism:**
```
escrow_service artifact:
  - has_standing: true (so it has a ledger entry)
  - Holds scrip on behalf of parties
  - Tracks internally which funds belong to which escrow

Ledger sees: escrow_service: 1500 scrip
Artifact tracks: { ESC-001: 500, ESC-002: 1000 }
```

**Deletion invariant (85% confidence):** Artifacts with non-zero balance cannot be deleted. Prevents accidental fund loss.

---

## MCP and StructGPT Integration

**Status:** ESTABLISHED (75% confidence)

**MCP influence:** Defines how tools/resources are discovered and invoked.
- Tools: name, title, description, inputSchema (required), outputSchema, annotations
- Resources: name, title, uri, description, mimeType, annotations, size
- Annotations: readOnlyHint, destructiveHint, idempotentHint, openWorldHint

**StructGPT influence:** Defines how structured data is presented to LLMs (linearization).
- Raw data (JSON, tables, graphs) converted to LLM-readable text
- Linearization strategy depends on the task/question
- Reduces token usage, improves reasoning

**How they combine:**
- MCP answers: "What can I invoke and how?" (interface/tools)
- StructGPT answers: "How is content formatted for LLM consumption?" (linearization)

---

## Tool Result Format

**Status:** TENTATIVE (75% confidence)

**Recommendation:** MCP-style content blocks

```yaml
result:
  - type: "text"
    text: "Human-readable response for LLM"
  - type: "structured"  # Optional extension
    data: { ... }  # For programmatic access
```

---

## Content/State Relationship

**Status:** TENTATIVE (60% confidence)

**Recommendation:** Artifact provides `linearize()` function

- Artifact has internal state (structured)
- Artifact provides `linearize()` that produces content
- Kernel calls `linearize()` when content is needed
- Default `linearize()` = JSON dump of state

---

## Semantic Methods vs Raw Operations

**Status:** INSIGHT (70% confidence)

Instead of controlling raw edit operations, well-designed artifacts expose semantic methods that can be individually permissioned.

**Example:**
Instead of:
```
edit(allowed_readers, old="[alice]", new="[alice, bob]")
```

Expose:
```
add_reader(user)    # Contract can allow
remove_reader(user) # Contract can deny
```

**Implication:** Raw edit is a low-level primitive. Higher-level artifacts should expose semantic operations. Contracts control methods via invoke permissions.
