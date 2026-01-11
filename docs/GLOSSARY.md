# Glossary

Canonical terminology for the Agent Ecology. Use these terms consistently across code and documentation.

---

## Entities

| Term | Definition | Notes |
|------|------------|-------|
| **Agent** | An LLM-powered entity that observes state and proposes actions | Has a system prompt, memory, and LLM model |
| **Principal** | Any identity that can hold scrip/resources in the ledger | Includes agents, artifacts, contracts. Broader than "agent" |
| **Artifact** | Data or code stored in the world | Can be executable (has `run()` function) or passive (data only) |
| **Genesis Artifact** | System-provided artifact (ledger, oracle, etc.) | Prefixed with `genesis_` |
| **Contract** | An executable artifact that manages resources/access for others | Uses Gatekeeper pattern |

---

## Resources

### Stock Resources (Finite, Never Refresh)

| Term | What It Is | Unit | Notes |
|------|-----------|------|-------|
| **llm_budget** | Real $ for LLM API calls | dollars | Shared pool, exhaustion stops all agents |
| **disk** | Storage space for artifacts | bytes | Per-principal quota |

### Flow Resources (Per-Tick Quota, Refreshes)

| Term | Config Name | Code Name | What It Is | Unit |
|------|-------------|-----------|-----------|------|
| **compute** | `compute` | `llm_tokens` | Token budget for thinking | token_units |
| **bandwidth** | `bandwidth` | `bandwidth` | Network I/O | bytes (disabled) |

**Note:** Config uses `compute`, code stores as `llm_tokens`. They are the same resource.

---

## Currency

| Term | Definition | Notes |
|------|------------|-------|
| **Scrip** | Economic currency for agent-to-agent trade | NOT a physical resource. Persists across ticks. |

**Key distinction:**
- **Resources** = Physical limits (compute, disk) - always consumed
- **Scrip** = Economic signal (prices, payments) - flows between agents

---

## Time

| Term | Definition | Notes |
|------|------------|-------|
| **Tick** | One simulation step | All agents observe, then act in random order |

**Do NOT use:** "turn", "round", "step"

---

## Actions (Narrow Waist)

Only 4 action types exist:

| Action | Purpose | Costs |
|--------|---------|-------|
| **noop** | Do nothing | None |
| **read_artifact** | Read artifact content | May cost scrip (read_price) |
| **write_artifact** | Create/update artifact | Disk quota |
| **invoke_artifact** | Call method on artifact | May cost scrip (invoke_price) |

**No `transfer` action.** Transfers use: `invoke_artifact("genesis_ledger", "transfer", [...])`

---

## Genesis Artifacts

| Artifact | Purpose | Key Methods |
|----------|---------|-------------|
| **genesis_ledger** | Scrip balances, transfers, ownership | balance, transfer, spawn_principal, transfer_ownership |
| **genesis_oracle** | Auction-based artifact scoring | status, bid, check |
| **genesis_rights_registry** | Resource quota management | check_quota, transfer_quota |
| **genesis_event_log** | Simulation history | read |
| **genesis_escrow** | Trustless artifact trading | deposit, purchase, cancel |
| **genesis_handbook** | Seeded documentation | (read-only) |

---

## Resource Categories

| Category | Meaning | Resources | Behavior |
|----------|---------|-----------|----------|
| **Stock** | Finite pool | llm_budget, disk | Never refreshes. Trade or exhaust. |
| **Flow** | Per-tick quota | compute, bandwidth | Refreshes each tick. Use-or-lose. |

**Use the specific resource name** (`compute`, `disk`) not the category name (`flow`, `stock`).

---

## Policy Terms

| Term | Definition |
|------|------------|
| **read_price** | Scrip cost to read artifact content |
| **invoke_price** | Scrip cost to invoke executable (paid to owner) |
| **allow_read/write/invoke** | Access control list: `["*"]`, `["alice"]`, or `"@contract"` |
| **resource_policy** | Who pays physical resources: `"caller_pays"` or `"owner_pays"` |

---

## Oracle Terms

| Term | Definition |
|------|------------|
| **Vickrey Auction** | Sealed-bid, second-price auction. Winner pays second-highest bid. |
| **UBI** | Universal Basic Income. Winning bid redistributed to all agents. |
| **Minting** | Creating new scrip. Only oracle can mint (for winning submissions). |
| **Scoring** | LLM evaluation of artifact quality (0-100 scale). |

---

## Patterns

| Pattern | Definition |
|---------|------------|
| **Gatekeeper** | Contract holds artifact ownership, manages access for multiple stakeholders |
| **Two-Layer Model** | Scrip (economic) and Resources (physical) are independent layers |
| **Two-Phase Commit** | Observe (frozen state) → Act (randomized execution) |
| **Narrow Waist** | Only 3 verbs (read/write/invoke) - all capabilities derive from these |

---

## Deprecated Terms

| Don't Use | Use Instead | Reason |
|-----------|-------------|--------|
| credits | scrip | Consistency |
| account | principal | Principals include non-agents |
| turn | tick | Consistency |
| flow (as resource name) | compute | Use specific name |
| stock (as resource name) | disk | Use specific name |
| transfer (as action) | invoke_artifact | No direct transfer action |

---

## Code vs Config Mapping

| Config Term | Code Variable | Notes |
|-------------|---------------|-------|
| `resources.flow.compute` | `llm_tokens` | Legacy naming in code |
| `resources.stock.disk` | `disk` | Consistent |
| `scrip.starting_amount` | `scrip[id]` | Ledger field |
| `validation.max_artifact_id_length` | 128 | DoS prevention |
