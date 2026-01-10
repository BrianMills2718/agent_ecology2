# Physics-First Model

The Agent Ecology uses a "physics-first" design philosophy where agents interact through a narrow API of primitive operations, and all behaviors emerge from these fundamental primitives rather than being hardcoded.

## Overview

### Core Principles

1. **Narrow Waist Architecture**: Only 3 primitive operations (read, write, invoke) plus noop
2. **Everything is an Artifact**: Data, code, and even system functions are artifacts
3. **Explicit Costs**: Every action has a visible cost in compute or scrip
4. **Emergent Behavior**: Complex functionality emerges from simple primitives

### The Three Verbs

```python
class ActionType(str, Enum):
    NOOP = "noop"
    READ_ARTIFACT = "read_artifact"
    WRITE_ARTIFACT = "write_artifact"
    INVOKE_ARTIFACT = "invoke_artifact"
```

All agent capabilities derive from these three operations. There is no special `transfer` action - transfers happen via `invoke_artifact("genesis_ledger", "transfer", [...])`.

---

## spawn_principal API

Agents can spawn new principals (sub-agents) dynamically using the genesis ledger.

### Usage

```json
{
  "action_type": "invoke_artifact",
  "artifact_id": "genesis_ledger",
  "method": "spawn_principal",
  "args": []
}
```

### Behavior

- Generates a unique principal ID (e.g., `agent_a1b2c3d4`)
- Creates ledger entry with **0 scrip** and **0 compute**
- Returns `{"success": true, "principal_id": "agent_..."}`
- Costs 1 scrip processing fee

### Design Rationale

New principals start with nothing. The parent agent must explicitly transfer resources to keep them alive:

```json
// After spawning, transfer resources to the new principal
{
  "action_type": "invoke_artifact",
  "artifact_id": "genesis_ledger",
  "method": "transfer",
  "args": ["parent_agent", "agent_a1b2c3d4", 50]
}
```

This prevents resource inflation and creates economic accountability for spawned agents.

### Agent Creation Flow

When `spawn_principal` creates a new entry in the ledger, the simulation loop detects it:

```python
def check_for_new_principals(world, agents, config, verbose):
    # Get all principal IDs from the ledger
    ledger_principals = set(world.ledger.scrip.keys())
    existing_agent_ids = {agent.agent_id for agent in agents}

    # Find principals without Agent instances
    new_principal_ids = ledger_principals - existing_agent_ids

    # Create default Agent instances for new principals
    for principal_id in new_principal_ids:
        new_agent = Agent(
            agent_id=principal_id,
            llm_model=default_model,
            system_prompt="You are a new agent. Survive and thrive.",
            ...
        )
```

---

## Policy System

Artifacts support fine-grained access control through policies.

### Policy Fields

```python
class PolicyDict(TypedDict, total=False):
    read_price: int        # Scrip cost to read content
    invoke_price: int      # Scrip cost to invoke (paid to owner)
    allow_read: list[str] | str   # Who can read
    allow_write: list[str] | str  # Who can modify
    allow_invoke: list[str] | str # Who can invoke
```

### Access Control Lists

**Static Lists (V1 - implemented)**:
- `["*"]` - Everyone can access
- `["alice", "bob"]` - Only specified agents
- `[]` - No one (owner only for write)

**Contract References (V2 - planned)**:
- `"@dao_contract"` - Defers decision to executable artifact
- Enables DAOs, voting, time-based access, etc.

### Example: Creating a Private Artifact

```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_secret_data",
  "artifact_type": "data",
  "content": "sensitive information",
  "policy": {
    "allow_read": ["trusted_agent"],
    "allow_write": [],
    "read_price": 10
  }
}
```

### Example: Creating a Paid Service

```json
{
  "action_type": "write_artifact",
  "artifact_id": "premium_calculator",
  "artifact_type": "executable",
  "content": "Advanced math service",
  "executable": true,
  "code": "def run(x, y): return x ** y",
  "policy": {
    "allow_invoke": ["*"],
    "invoke_price": 5
  }
}
```

### Permission Resolution

```python
def can_read(self, agent_id: str) -> bool:
    allow = self.policy.get("allow_read", ["*"])

    # V1: Static list (fast path)
    if isinstance(allow, list):
        return "*" in allow or agent_id in allow or agent_id == self.owner_id

    # Owner always has read access
    return agent_id == self.owner_id
```

---

## Cooldown Mechanism

Agents that generate verbose output enter a cooldown period, preventing rapid-fire actions.

### How It Works

```python
# After LLM call, calculate cooldown based on output tokens
tokens_per_tick_capacity = 500  # configurable
agent.cooldown_ticks = output_tokens // tokens_per_tick_capacity

# At start of each tick, check and decrement cooldown
if agent.cooldown_ticks > 0:
    print(f"{agent.agent_id} cooling down... ({agent.cooldown_ticks} ticks remaining)")
    agent.cooldown_ticks -= 1
    continue  # Skip this agent's turn
```

### Configuration

```yaml
# config/config.yaml
cooldown:
  tokens_per_tick_capacity: 500  # tokens before 1 tick cooldown
```

### Design Rationale

- Prevents agents from dominating with verbose outputs
- Creates natural pacing in multi-agent interactions
- Incentivizes concise communication
- Mirrors "speaking time" in real-world discussions

---

## Two-Phase Commit Execution

Each tick uses a two-phase commit model to ensure fair ordering.

### Phase 1: Observe (Proposal Collection)

All agents see the **same frozen snapshot** of world state:

```python
# Capture frozen state ONCE at start of tick
tick_state = world.get_state_summary()

# All agents propose actions seeing the same state
proposals = []
for agent in agents:
    # Skip agents in cooldown
    if agent.cooldown_ticks > 0:
        continue

    # Agent sees frozen tick_state, not live state
    proposal = agent.propose_action(tick_state)
    proposals.append({"agent": agent, "proposal": proposal, ...})
```

### Phase 2: Act (Randomized Execution)

Actions execute in random order:

```python
# Randomize execution order for fairness
random.shuffle(proposals)

for action_proposal in proposals:
    agent = action_proposal["agent"]
    intent = parse_intent_from_json(agent.agent_id, json.dumps(proposal["action"]))

    # Execute against LIVE state (may fail due to race conditions)
    result = world.execute_action(intent)
```

### Why Two-Phase Commit?

1. **Fairness**: No agent gets informational advantage from action order
2. **Atomicity**: Thinking costs are paid regardless of execution success
3. **Race Handling**: Actions may fail if state changed (explicit failure handling)
4. **Determinism**: Given same random seed, execution order is reproducible

### Cost Model

| Phase | Cost Type | When Paid |
|-------|-----------|-----------|
| Observe | Compute (thinking) | Always (even if proposal rejected) |
| Act | Compute (action) | Only on success |
| Act | Scrip (fees/prices) | Only on success |

---

## Originality Oracle

The oracle scores artifacts for external value and mints scrip based on quality.

### How It Works

```python
class OracleScorer:
    _seen_hashes: set[str] = set()

    def score_artifact(self, artifact_id, artifact_type, content):
        # Check for duplicates
        content_hash = hashlib.md5(content.strip().lower().encode()).hexdigest()
        if content_hash in self._seen_hashes:
            return {
                "success": True,
                "score": 0,
                "reason": "Duplicate content - no originality reward"
            }

        # Mark as seen
        self._seen_hashes.add(content_hash)

        # LLM evaluation for quality (0-100)
        score = self._llm_evaluate(content)
        return {"success": True, "score": score, "reason": "..."}
```

### Oracle API

```json
// Submit artifact for scoring (5 scrip fee)
{
  "action_type": "invoke_artifact",
  "artifact_id": "genesis_oracle",
  "method": "submit",
  "args": ["my_artifact_id"]
}

// Process pending submissions (free)
{
  "action_type": "invoke_artifact",
  "artifact_id": "genesis_oracle",
  "method": "process",
  "args": []
}

// Check submission status (free)
{
  "action_type": "invoke_artifact",
  "artifact_id": "genesis_oracle",
  "method": "check",
  "args": ["my_artifact_id"]
}
```

### Important Constraints

1. **Code Only**: Oracle only accepts executable artifacts (`executable: true`)
2. **Originality Check**: Duplicate content scores 0
3. **Minting Formula**: `credits_minted = score // 10` (configurable via `mint_ratio`)

### Scoring Criteria

The LLM evaluates artifacts on:
- Usefulness and practical value
- Clarity and quality of implementation
- Originality and creativity
- Potential for engagement/reuse

Score ranges:
- 0-10: Low quality, spam
- 11-30: Mediocre
- 31-50: Decent value
- 51-70: Good quality
- 71-90: Excellent
- 91-100: Exceptional

---

## Genesis Artifacts Reference

System artifacts that provide core infrastructure:

### genesis_ledger
- `balance([agent_id])` - Get flow/scrip balance [FREE]
- `all_balances([])` - Get all balances [FREE]
- `transfer([from, to, amount])` - Transfer scrip [1 scrip fee]
- `spawn_principal([])` - Create new principal [1 scrip fee]

### genesis_rights_registry
- `check_quota([agent_id])` - Get compute/disk quotas [FREE]
- `all_quotas([])` - Get all quotas [FREE]
- `transfer_quota([from, to, type, amount])` - Transfer quota [1 scrip fee]

### genesis_oracle
- `status([])` - Oracle status [FREE]
- `submit([artifact_id])` - Submit for scoring [5 scrip fee]
- `check([artifact_id])` - Check submission [FREE]
- `process([])` - Score pending submission [FREE]

### genesis_event_log
- `read([offset, limit])` - Read events [FREE in scrip, costs input tokens]
