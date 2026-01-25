# Simulation Learnings - CC Instructions

This directory captures observations from simulation runs. See README.md for file format.

## Post-Simulation Analysis Guide

Best practices and heuristics for diagnosing, critiquing, and improving agent behavior after simulation runs.

### Quick Start

```bash
make analyze                    # Run metrics analysis on latest run
make analyze RUN=logs/run_XXX   # Analyze specific run
```

### Analysis Workflow

#### 1. Run Metrics First

```bash
make analyze
```

Check these key indicators:
- **LLM Success Rate** - Should be >95%. Lower indicates schema/API issues.
- **Thought Capture Rate** - Should be 100%. Lower indicates logging issues.
- **Invoke Success Rate** - <80% suggests agent confusion or missing capabilities.

#### 2. Identify Failure Patterns

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

#### 3. Deep Dive: LLM Logs

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

#### 4. Categorize the Problem

| Category | Symptoms | Fix Location |
|----------|----------|--------------|
| **Missing Information** | Agent doesn't see relevant data | Prompt construction, memory |
| **Unclear Information** | Agent sees data but misinterprets | Error messages, documentation |
| **Wrong Reasoning** | Agent has info but draws wrong conclusion | Prompt engineering, examples |
| **Capability Gap** | Agent can't do what's needed | New genesis methods, tools |

### Common Failure Patterns & Solutions

#### Pattern: Repeated Transfer After Escrow Deposit

**Symptoms:**
```
transfer_ownership(X, escrow) -> SUCCESS
transfer_ownership(X, escrow) -> FAIL (not owner)
transfer_ownership(X, escrow) -> FAIL (not owner)
```

**Root Cause:** Agent doesn't understand that successful transfer+deposit means artifact is listed.

**Solution:**
1. Prescriptive error: "You already transferred X to escrow. To cancel: `genesis_escrow.cancel([X])`"
2. Ensure agent memory shows the successful deposit, not just the transfer

#### Pattern: Deposit Before Transfer

**Symptoms:**
```
deposit(X, price) -> FAIL (escrow does not own X)
```

**Root Cause:** Agent doesn't understand 2-step escrow process.

**Solution:**
1. Error message already includes 2-step instructions
2. Ensure handbook_trading is clear

#### Pattern: Wrong Method Name

**Symptoms:**
```
invoke(artifact, "run", args) -> FAIL (method not found)
```

**Root Cause:** Agent assumes all executables use `run()` but artifact has different interface.

**Solution:**
1. Better error: "Method 'run' not found. Available: [analyze, process]."
2. Encourage agents to read artifacts before invoking

### Heuristics for Improvement Decisions

#### When to Improve Error Messages

**Do improve if:**
- Error says what's wrong but not what to do next
- Agent's reasoning shows misinterpretation of error
- Same error causes repeated failures across multiple agents

**Don't improve if:**
- Agent has the information but reasons incorrectly (prompt engineering issue)
- Error is rare/edge case

#### When to Add Memory/Context

**Do add if:**
- Agent needs information from >3 actions ago
- Pattern requires tracking state across steps (like escrow workflow)

**Don't add if:**
- Information is already in prompt but agent ignores it
- Agent should learn this through experience (emergence)

#### When to Modify Genesis Artifacts

**Do modify if:**
- Current design creates unavoidable confusion
- Missing capability blocks useful emergent behavior

**Don't modify if:**
- Agents could build the capability themselves
- Change prescribes behavior rather than enabling it

### Emergence vs. Prescription

From project philosophy (README.md):

> "Emergence is the goal... Selection pressure over protection... Observe, don't prevent"

**But also:**
> "We need to get the agents as intelligent as possible to bootstrap the system."

#### The Bootstrap Principle

- Fix obvious issues that block basic competence
- Don't wait for emergence to solve problems we understand
- Emergence finds solutions we CAN'T design
- Goal: Get agents smart enough that interesting emergence can occur

### Diagnostic Commands Reference

```bash
# Basic metrics
make analyze

# JSON output for scripting
python scripts/analyze_run.py --json

# Find specific agent's actions
grep "gamma_3" logs/latest/events.jsonl | head -20

# Find all ownership transfers
grep "transfer_ownership" logs/latest/events.jsonl | python -m json.tool

# Find LLM logs with specific error
grep -l "error text" llm_logs/YYYYMMDD/*.json
```

## Creating New Learnings

When you discover something notable during simulation analysis:

1. Create `YYYY-MM-DD_short_description.md`
2. Use the template in README.md
3. Set status: `open`, `resolved`, or `wontfix`
4. Link to related plans if applicable
