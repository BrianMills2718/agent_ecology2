# Post-Simulation Analysis Guide

Best practices and heuristics for diagnosing, critiquing, and improving agent behavior after simulation runs.

## Quick Start

```bash
make analyze                    # Run metrics analysis on latest run
make analyze RUN=logs/run_XXX   # Analyze specific run
```

## Analysis Workflow

### 1. Run Metrics First

```bash
make analyze
```

Check these key indicators:
- **LLM Success Rate** - Should be >95%. Lower indicates schema/API issues.
- **Thought Capture Rate** - Should be 100%. Lower indicates logging issues.
- **Invoke Success Rate** - <80% suggests agent confusion or missing capabilities.

### 2. Identify Failure Patterns

Look for repeated failures in the output:
```bash
# Check top failure reasons
python scripts/analyze_run.py --json | jq '.invokes.failure_reasons'
```

Common patterns:
| Pattern | Likely Cause | Investigation |
|---------|--------------|---------------|
| Same action fails 5+ times | Agent not learning from errors | Check LLM logs for reasoning |
| "not the owner" errors | Ownership confusion | Check escrow workflow |
| "method not found" | Wrong interface assumptions | Check if agent reads interfaces |
| ModuleNotFoundError | Missing library | Check if library is installed |

### 3. Deep Dive: LLM Logs

When agents make wrong decisions despite clear errors:

```bash
# Find logs where agent saw specific error
grep -l "specific error text" llm_logs/YYYYMMDD/*.json

# Read the full prompt to see what agent saw
cat llm_logs/YYYYMMDD/<file>.json | jq '.prompt.raw'

# Check agent's reasoning
cat llm_logs/YYYYMMDD/<file>.json | jq '.response.parsed_model.reasoning'
```

**Key questions:**
1. Did the agent see the error message? (Check `## Last Action Result`)
2. Did the agent see relevant history? (Check `## Recent Failures`)
3. Was the error message actionable? (Does it say what to DO next?)
4. Is the reasoning correct given the information?

### 4. Categorize the Problem

| Category | Symptoms | Fix Location |
|----------|----------|--------------|
| **Missing Information** | Agent doesn't see relevant data | Prompt construction, memory |
| **Unclear Information** | Agent sees data but misinterprets | Error messages, documentation |
| **Wrong Reasoning** | Agent has info but draws wrong conclusion | Prompt engineering, examples |
| **Capability Gap** | Agent can't do what's needed | New genesis methods, tools |

## Common Failure Patterns & Solutions

### Pattern: Repeated Transfer After Escrow Deposit

**Symptoms:**
```
transfer_ownership(X, escrow) → SUCCESS
transfer_ownership(X, escrow) → FAIL (not owner)
transfer_ownership(X, escrow) → FAIL (not owner)
transfer_ownership(X, self) → FAIL (not owner)
```

**Root Cause:** Agent doesn't understand that successful transfer+deposit means artifact is listed. Tries to re-transfer or "reclaim" ownership.

**Solution:**
1. Prescriptive error: "You already transferred X to escrow. It's listed for sale. To cancel: `genesis_escrow.cancel([X])`"
2. Ensure agent memory shows the successful deposit, not just the transfer

### Pattern: Deposit Before Transfer

**Symptoms:**
```
deposit(X, price) → FAIL (escrow does not own X)
deposit(X, price) → FAIL (escrow does not own X)
```

**Root Cause:** Agent doesn't understand 2-step escrow process.

**Solution:**
1. Error message already includes 2-step instructions
2. Ensure handbook_trading is clear
3. Consider: Add example in action schema

### Pattern: Wrong Method Name

**Symptoms:**
```
invoke(artifact, "run", args) → FAIL (method not found)
```

**Root Cause:** Agent assumes all executables use `run()` but artifact has different interface.

**Solution:**
1. Better error: "Method 'run' not found. Available: [analyze, process]. Read artifact to see interface."
2. Encourage agents to read artifacts before invoking

### Pattern: Repeated Identical Failures

**Symptoms:** Same exact action fails 5+ times in a row.

**Root Cause:** Agent not adapting to failure feedback.

**Solution:**
1. Check if `## Recent Failures` section is truncated
2. Check if error message is actionable
3. Consider: Add "you've tried this X times" warning

## Heuristics for Improvement Decisions

### When to Improve Error Messages

**Do improve if:**
- Error says what's wrong but not what to do next
- Agent's reasoning shows misinterpretation of error
- Same error causes repeated failures across multiple agents

**Don't improve if:**
- Agent has the information but reasons incorrectly (prompt engineering issue)
- Error is rare/edge case
- Fix would add complexity without clear benefit

### When to Add Memory/Context

**Do add if:**
- Agent needs information from >3 actions ago
- Pattern requires tracking state across steps (like escrow workflow)
- Multiple agents exhibit same memory gap

**Don't add if:**
- Information is already in prompt but agent ignores it
- Memory would make prompts too long
- Agent should learn this through experience (emergence)

### When to Modify Genesis Artifacts

**Do modify if:**
- Current design creates unavoidable confusion
- Missing capability blocks useful emergent behavior
- Change aligns with design philosophy (observability, not control)

**Don't modify if:**
- Agents could build the capability themselves
- Change prescribes behavior rather than enabling it
- Simpler prompt fix would work

## Emergence vs. Prescription

From project philosophy (README.md):

> "Emergence is the goal... Selection pressure over protection... Observe, don't prevent"

**But also:**
> "We need to get the agents as intelligent as possible to bootstrap the system. If they are not smart enough, emergence will never occur."

### The Bootstrap Principle

- Fix obvious issues that block basic competence
- Don't wait for emergence to solve problems we understand
- Emergence finds solutions we CAN'T design - don't use it for problems we CAN solve
- Goal: Get agents smart enough that interesting emergence can occur

### Decision Framework

```
Is this a problem we understand how to solve?
  YES → Fix it (better errors, clearer docs, improved prompts)
  NO  → Let emergence find the solution

Would fixing this prescribe specific behavior?
  YES → Consider if it's necessary for bootstrap vs. premature optimization
  NO  → Safe to fix (improving observability, clarity, capabilities)

Could agents solve this themselves?
  YES → Only fix if blocking bootstrap intelligence
  NO  → Fix it (missing capability, unclear interface)
```

## Diagnostic Commands Reference

```bash
# Basic metrics
make analyze

# JSON output for scripting
python scripts/analyze_run.py --json

# Find specific agent's actions
grep "gamma_3" logs/latest/events.jsonl | head -20

# Find all ownership transfers
grep "transfer_ownership" logs/latest/events.jsonl | python -m json.tool

# Count action types by agent
python3 -c "
import json
from collections import Counter
c = Counter()
for line in open('logs/latest/events.jsonl'):
    e = json.loads(line)
    if e.get('event_type') == 'action':
        agent = e.get('intent', {}).get('principal_id', 'unknown')
        action = e.get('intent', {}).get('action_type', 'unknown')
        c[(agent, action)] += 1
for k, v in sorted(c.items()):
    print(f'{k[0]:15} {k[1]:20} {v}')
"

# Find LLM logs with specific error
grep -l "error text" llm_logs/YYYYMMDD/*.json

# Check agent reasoning after failure
cat llm_logs/YYYYMMDD/<file>.json | jq '{reasoning: .response.parsed_model.reasoning, last_action: .prompt.raw | split("## Last Action Result")[1] | split("##")[0]}'
```

## Contributing to This Guide

When you discover a new failure pattern or diagnostic technique:

1. Add it to the appropriate section above
2. Include: symptoms, root cause, solution
3. Update the diagnostic commands if new tools are useful
4. Consider if the pattern suggests a code fix (create a plan)
