# Simulation Learnings

Observations and insights from running agent simulations. Focus on what we learn about emergent behavior, architectural weaknesses, and directions for improvement.

---

## 2026-01-25: Model Comparison (gemini-2.0-flash vs gemini-3-flash-preview)

### Experiment
Ran identical 120-second simulations with 3 agents (alpha_3, beta_3, delta_3) using different models.

### Results

| Metric | gemini-2.0-flash | gemini-3-flash-preview |
|--------|------------------|------------------------|
| Events | 917 | 972 |
| alpha_3 lessons stored | **0** | **35** |
| alpha_3 hit error limit | Yes (7x consecutive) | No |
| Economic activity | Only beta_3 active | All 3 agents active |
| Meta-learning observed | None | Yes ("stop storing generic actions") |

### Key Observation
The `semantic_memory` trait is injected into prompts for all agents. gemini-3-flash-preview follows it; gemini-2.0-flash ignores it.

### Wrong Lesson (Avoided)
Initial instinct: "Force learning behavior through hard-coded rules" - e.g., block retries until lessons stored, require reflection after failures.

**Why this is wrong:**
- Prescribing every failure case doesn't scale
- Doesn't improve innate intelligence/adaptability
- Creates brittle systems dependent on anticipating all scenarios
- Stronger models would just work around architectural issues

### Right Lesson
The architecture needs to create **conditions for emergence**, not script behaviors.

**Directions to explore:**

1. **Metacognitive capabilities** - Agents that think about their own thinking, evaluate their own strategies, notice their own patterns (gemini-3-flash-preview did this spontaneously: "Repeatedly storing generic action descriptions is not helpful")

2. **Self-modification** - Agents that can modify their own cognitive architectures, experiment with different approaches, evolve their workflows

3. **Long-term strategic behavior** - Not just reactive error handling, but genuine planning toward goals that span many actions

4. **Evolutionary pressure** - Selection mechanisms that favor agents with better learning/adaptation capabilities

### Design Principle
**Use weak models to stress-test architecture.** If gemini-2.0-flash can't bootstrap with our architecture, we're relying on model intelligence to paper over weaknesses. A stronger model might "work around" issues, masking problems that prevent genuine emergent collective capability.

The goal is an architecture robust enough that even weak models can bootstrap, because the structure itself facilitates learning - not because we've anticipated and hard-coded every scenario.

---

## 2026-01-25: Simplified Metacognitive Prompt (gemini-2.5-flash)

### Experiment
Simplified the `semantic_memory` trait from verbose instructions to a metacognitive question:

**Before (verbose):**
```
ACTION REQUIRED: If you learned something useful, STORE IT NOW...
WHEN TO STORE (do this!):
- After ANY failure: "LESSON: [action] failed because [reason]"
- After success: "STRATEGY: [approach] worked for [goal]"
...
```

**After (metacognitive):**
```
ASK YOURSELF: What did I just learn that my future self should know?

If the answer is something specific (not generic), store it...
Good: "LESSON: escrow deposit requires setting authorized_writer first"
Bad: "ACTION: I queried the kernel" (too generic, don't store)
```

### Results

| Metric | 2.0-flash (verbose) | 3-flash-preview (verbose) | 2.5-flash (metacognitive) |
|--------|---------------------|---------------------------|---------------------------|
| alpha_3 lessons | 0 | 35 | 2 |
| beta_3 lessons | 13 | 6 | 1 |
| delta_3 lessons | 15 | 9 | 4 |
| Lesson quality | N/A | Mixed (some generic spam) | **High (all specific)** |
| Hit error limit | Yes | No | No |
| Errors (recovered) | 7+ consecutive | 11 | 66/33/41 |

### Sample Lessons (2.5-flash with metacognitive prompt)
- "LESSON: escrow deposit requires setting authorized_writer first"
- "LESSON: Repeatedly writing and bidding on simple_fetch leads to MCP server errors"
- "LESSON: Failed to use query_kernel because I tried to invoke it directly"
- "LESSON: Check existing artifacts before building to avoid duplication"

### Key Finding
**Fewer but higher-quality lessons.** The metacognitive framing ("What did I learn that my future self should know?") filters out generic action logging. Quality over quantity.

### Insight
The metacognitive prompt works because it:
1. Shifts from "follow these instructions" to "reflect on your experience"
2. Provides a quality filter (specific vs generic)
3. Frames learning as self-beneficial ("your future self")

This aligns with the goal of **creating conditions for emergence** rather than prescribing behaviors.

---

## 2026-01-25: Metacognitive Prompt with Weak Model (gemini-2.0-flash)

### Experiment
Applied the simplified metacognitive prompt (from previous experiment) to gemini-2.0-flash to see if the approach helps weak models learn.

### Results

| Metric | 2.0-flash (verbose) | 2.0-flash (metacognitive) |
|--------|---------------------|---------------------------|
| alpha_3 lessons | 0 | 0 |
| beta_3 lessons | 13 | 0 |
| delta_3 lessons | 15 | **4** |
| Hit error limit | Yes (7x consecutive) | **No** |
| Lesson quality | N/A | High (all specific) |

### Sample Lessons (delta_3)
- "LESSON: escrow deposit requires setting authorized_writer first"
- "LESSON: Repeatedly writing and bidding on simple_fetch leads to MCP server errors"
- "LESSON: Failed to use query_kernel because I tried to invoke it directly"
- "LESSON: Check existing artifacts before building to avoid duplication"

### Key Findings

1. **Error loops reduced**: No agent hit the 7-consecutive-error limit. The metacognitive framing seems to encourage more varied behavior even when agents don't explicitly store lessons.

2. **Mixed learning outcomes**: delta_3 stored high-quality lessons while alpha_3 and beta_3 stored none. This suggests agent-specific factors (workflow, goals, or just randomness) affect learning behavior.

3. **Quality over quantity**: beta_3 went from 13 lessons (verbose) to 0 (metacognitive), but this may be correct - the verbose prompt was producing low-quality spam.

### Full Model Comparison (Metacognitive Prompt)

| Metric | 2.0-flash | 2.5-flash | 3-flash-preview (verbose*) |
|--------|-----------|-----------|---------------------------|
| Total lessons | 4 | 7 | 50 |
| alpha_3 | 0 | 2 | 35 |
| beta_3 | 0 | 1 | 6 |
| delta_3 | 4 | 4 | 9 |
| Error limit hits | 0 | 0 | 0 |
| Quality | High | High | Mixed |

*gemini-3-flash-preview was tested with verbose prompt only

### Insight

The metacognitive prompt provides two separate benefits:
1. **Reduces error loops** - Works across all model strengths
2. **Improves lesson quality** - Works when models do store lessons

However, **lesson quantity** still correlates with model capability. Weak models (2.0-flash) may understand the metacognitive question but lack the capability to consistently act on it.

### Architectural Implication

The metacognitive approach is a step toward "conditions for emergence" but doesn't fully solve weak model bootstrapping. Next directions:

- **Structural forcing** - Can we design workflows where learning is more naturally embedded (not just prompted)?
- **Peer observation** - Can agents learn from watching others succeed/fail?
- **Accumulated pressure** - Does performance improve over longer simulations as lessons compound?

---

## Future Experiments

- [x] ~~Evaluate metacognitive prompt strategies~~ (done: simplified prompt improves quality)
- [x] ~~Test metacognitive prompt with weak model (gemini-2.0-flash)~~ (done: reduces error loops, mixed learning)
- [ ] Test cognitive architecture variations (different workflow structures)
- [ ] Measure cross-session learning persistence
- [ ] Compare prescriptive vs emergent learning approaches
- [ ] Longer simulations to observe learning accumulation
- [ ] Peer observation mechanisms (agents learning from each other)

---

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

---

## Archived Observations

### 2026-01-19: Dashboard Test Run

**Duration:** 180 seconds (3 minutes)
**Agents:** alpha_3, beta_3, delta_3, epsilon_3, gamma_3
**LLM Budget:** $100.00
**Starting Scrip:** 100 each (500 total)
**Final Artifacts:** 64

#### Summary

This was a dashboard validation run after fixing the timestamp parsing bug. The simulation ran successfully with the dashboard at localhost:9000.

#### Final Balances

| Agent | Starting | Final | Change |
|-------|----------|-------|--------|
| alpha_3 | 100 | 106 | +6 |
| beta_3 | 100 | 106 | +6 |
| delta_3 | 100 | 64 | -36 |
| epsilon_3 | 100 | 85 | -15 |
| gamma_3 | 100 | 99 | -1 |

**Total:** 500 → 460 (40 scrip burned to system via auctions)

#### Auction Economics Analysis

**Delta_3's Auction Activity:**

| Auction | Bid | Paid | Score | Scrip Minted |
|---------|-----|------|-------|--------------|
| 1 | (unknown) | 10 | 78 | 7 |
| 2 | (unknown) | 11 | 82 | 8 |

**Total paid:** 21 scrip | **Total minted:** 15 scrip | **Net cost:** 6 scrip from auctions alone

**The Missing 30 Scrip:** Delta_3's total loss was 36 scrip, but auctions only cost net 6. The remaining 30 scrip was likely spent on LLM thinking costs, artifact creation, and invocation fees.

**UBI Distribution:** When auctions resolve, the paid scrip is distributed as Universal Basic Income. alpha_3 and beta_3 each gained +6 without winning any auctions.

#### Behavioral Observations

- **Delta_3 (Aggressive Bidder):** Won both auctions, ended with lowest balance (64), high scores suggest quality artifact creation
- **Alpha_3 & Beta_3 (UBI Beneficiaries):** Gained scrip without auction participation - passive strategy can be viable
- **Epsilon_3 (Moderate Activity):** Lost 15 scrip, neither won auctions nor gained from UBI
- **Gamma_3 (Conservative):** Only lost 1 scrip, minimal activity, preserved capital but created no value

---

### 2026-01-16: Agent Paralysis Analysis

**Status:** open
**Simulation:** runs/test_long_run.jsonl
**Related:** Plan #59 (Agent Intelligence Patterns)

#### What Happened

Ran 10-tick simulation with 3 agents (alpha, beta, gamma). Results:
- 765 invoke_artifact actions
- 717 read_artifact actions
- 0 write_artifact actions

No agent created anything. They spent all 10 ticks searching and invoking genesis artifacts.

#### Bug Found: Duplicate Artifact Count

Agents saw "45 artifacts (15 genesis, 15 executable, 15 data)" but only 30 actually exist.

**Root cause:** `src/world/world.py` lines 1281-1286. The `get_state_summary()` method:
1. Gets artifacts from store (30 total, includes genesis)
2. Then loops over `genesis_artifacts.values()` and adds them again (+15)
3. Result: 45 with 15 duplicates

Agents noticed the discrepancy but instead of accepting uncertainty and building something, they kept searching for the phantom executables.

#### Deeper Problem: Trivial Confusion Breaks Everything

The duplicate count is a bug, but the more concerning issue: such a trivial piece of confusing information broke all 3 agents for 10 ticks. This points to a **general intelligence problem**, not just a data bug. Band-aid fixes won't scale.

#### Cold-Start Deadlock in Prompts

Examined agent prompts and found a structural problem:

**Alpha's prompt:** "Before building anything, you check what already exists"
**Beta's prompt:** "When others build primitives, you wire them together"

This creates a waiting cycle where everyone waits and nobody creates.

**The problem:** These prompts are **rule-sets** (prescriptive instructions) rather than **goal + context** (what you're trying to achieve).

#### Architecture Limitations Identified

| Limitation | Current State | What SOTA agents have |
|------------|---------------|----------------------|
| Actions per tick | 1 (forced choice) | Agentic loop until goal met |
| Planning | None | TodoWrite, goals, sub-tasks |
| Memory control | Automatic | Explicit store/retrieve |
| Reflection | None | Self-critique, plan revision |
| Sub-agents | None | Task delegation |

#### Questions / Uncertainties

1. How much of the paralysis was the bug (fixable) vs architecture (needs redesign)?
2. Can prompt restructuring (goal+context vs rules) help within current architecture?
3. What's the minimal architecture change that would enable agentic behavior?
4. Should thinking mode be per-agent or global?

#### Next Steps

- [ ] Fix duplicate artifact bug in `get_state_summary()`
- [ ] Re-run simulation to isolate bug impact vs structural issues
- [ ] Draft YAML-ized prompt structure (goal/personality/metacognition sections)
- [ ] Prototype planning action (even if just writing to a `{agent}_plan` artifact)
- [ ] Investigate architecture options for multi-action or agentic loop
