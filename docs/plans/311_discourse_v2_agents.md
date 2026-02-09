# Plan #311: V2 Discourse Agents

**Status:** In Progress

## Problem

V1 discourse analysts (Plan #299) get stuck in "investigating" phase — they endlessly
query for artifacts that don't exist and never transition to building tools. They lack:
- Goal-driven task management
- Memory of what worked/failed
- Auto-progression when stuck in a phase
- Concrete initial tasks that push creation

## Solution

Create v2 discourse agents that hybridize alpha_prime's task queue pattern with the
discourse analyst's research cycle:

1. **Task queue drives action** — concrete, prioritized tasks from alpha_prime
2. **Auto-progression** — if stuck in a phase for 3+ iterations, advance automatically
3. **Knowledge accumulation** — persistent knowledge base across iterations
4. **Failed-attempt tracking** — never repeat what didn't work
5. **Build-first** — initial tasks push agents to create artifacts immediately
6. **Action result feedback** — each iteration sees what the last action returned

## Agents

| Agent | Domain | Replaces |
|-------|--------|----------|
| discourse_v2 | Argument & Logic | discourse_analyst |
| discourse_v2_2 | Narrative & Sequence | discourse_analyst_2 |
| discourse_v2_3 | Rhetoric & Persuasion | discourse_analyst_3 |

All share the same hybrid loop_code.py, parameterized via caller_id.

## Changes

- New: `config/genesis/agents/discourse_v2{,_2,_3}/` (agent.yaml, strategy.md, initial_state.json, loop_code.py, CLAUDE.md)
- Disable v1: `discourse_analyst{,_2,_3}/agent.yaml` set `enabled: false`
- Enable alpha_prime and mint_tasks in `config/config.yaml`

## Verification

Run simulation with v2 agents + alpha_prime, observe:
- Agents make LLM calls and create artifacts (vs v1 stuck in investigating)
- Task queues progress (tasks completed, new tasks generated)
- Knowledge bases accumulate
- Tools get built
