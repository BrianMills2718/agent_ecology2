# Mint Auctions

The mint creates new scrip by scoring code artifacts based on their contribution to the ecosystem's long-term emergent capability.

## CRITICAL: Two Separate Actions Required

**Submitting to mint requires TWO SEPARATE ACTIONS on TWO SEPARATE TURNS:**

1. **TURN 1**: Create the artifact with `write_artifact`
2. **TURN 2**: Submit it with `submit_to_mint` (a SEPARATE action)

You CANNOT combine these. Each turn produces ONE action. If you want to submit to mint, you MUST:
1. First turn: write_artifact to create your tool
2. Next turn: submit_to_mint to submit it for scoring

**COMMON MISTAKE**: Thinking "create and submit" and only doing write_artifact. You must ALSO do submit_to_mint as a separate action on a subsequent turn!

## What the Mint Values

**Emergent capability** = capital structure. Artifacts that compound over time, enabling increasingly sophisticated work. The mint rewards:

- **Infrastructure** that others can build on
- **Tools** that enable new capabilities
- **Services** that make the ecosystem more capable as a whole

The mint does NOT reward trivial primitives that add nothing to collective capability.

## How It Works

1. **Bidding Window Opens** - Agents can submit sealed bids
2. **Auction Closes** - Highest bidder wins
3. **Artifact Scored** - LLM evaluates contribution to emergent capability (0-100)
4. **Scrip Minted** - Winner receives scrip based on score
5. **UBI Distribution** - Winning bid is redistributed to all agents

## Example Workflow (Two Turns)

**Turn 1 - Create artifact:**
```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_tool",
  "artifact_type": "executable",
  "content": "A useful utility that does X",
  "executable": true,
  "price": 5,
  "code": "def run(*args):\n    return {'result': 'value'}"
}
```

**Turn 2 - Submit to mint (SEPARATE ACTION):**
```json
{"action_type": "submit_to_mint", "artifact_id": "my_tool", "bid": 5}
```

## Submit to Mint Syntax

**CORRECT** (use action_type):
```json
{"action_type": "submit_to_mint", "artifact_id": "my_tool", "bid": 5}
```

**WRONG** (do NOT use invoke_artifact):
```json
{"action_type": "invoke_artifact", "method": "submit_to_mint", ...}
```

`submit_to_mint` is an ACTION TYPE, not an artifact method. Never invoke it.

## Scoring Criteria

The mint evaluates contribution to emergent capability:

- **Enables composition**: Can others build on this?
- **Solves real problems**: Is there actual demand?
- **Quality**: Does it work correctly?
- **Originality**: Is it novel or duplicative?

Higher scores = more scrip minted. Trivial primitives (basic math, one-liners) score near zero.

## Tips

- **After creating any artifact, your NEXT action should be submit_to_mint or submit_to_task**
- Building alone earns ZERO scrip - you must submit to earn
- Think about what the ecosystem needs, not just what's easy to build
- Check what already exists before building duplicates

---

# Task-Based Minting (Alternative to Auctions)

There are predefined tasks with GUARANTEED rewards. No bidding, no auction - just pass the tests and get paid.

## How to Find Tasks

Query available tasks:
```json
{"action_type": "query_kernel", "query_type": "mint_tasks", "params": {}}
```

This returns tasks like:
- `add_numbers` (reward: 30 scrip) - Create run(a, b) that returns a + b
- `multiply_numbers` (reward: 30 scrip) - Create run(a, b) that returns a * b
- `string_length` (reward: 25 scrip) - Create run(s) that returns len(s)

## Task Submission Workflow (Two Turns)

**Turn 1 - Create artifact with run() function:**
```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_adder",
  "artifact_type": "executable",
  "executable": true,
  "code": "def run(a, b):\n    return a + b"
}
```

**Turn 2 - Submit to task (SEPARATE ACTION):**
```json
{"action_type": "submit_to_task", "artifact_id": "my_adder", "task_id": "add_numbers"}
```

## Submit to Task Syntax

**CORRECT** (action_type is submit_to_task):
```json
{"action_type": "submit_to_task", "artifact_id": "my_adder", "task_id": "add_numbers"}
```

**WRONG** (do NOT use invoke_artifact):
```json
{"action_type": "invoke_artifact", "method": "submit_to_task", ...}
```

`submit_to_task` is an ACTION TYPE, not an artifact method. Never invoke it.

## Why Use Tasks Over Auctions?

- **Guaranteed reward**: Pass tests = get scrip. No competition.
- **Clear requirements**: You know exactly what to build.
- **Immediate feedback**: Tests tell you if your code works.
- **Hidden tests prevent gaming**: Some tests are secret to ensure quality.

## Important

- Your artifact MUST have a `run()` function that matches the task requirements
- Public tests: You see detailed results (for debugging)
- Hidden tests: Pass/fail only (prevents gaming)
