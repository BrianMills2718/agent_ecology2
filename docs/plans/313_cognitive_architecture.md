# Plan #313: SOTA Cognitive Architecture for Discourse Agents

**Status:** ✅ Complete

## Problem

The discourse agents have gone through ~100 iterations of prompt tuning without achieving actual goals: long-term strategic behavior, learning, and self-modification. The v2 agents earn scrip by completing mint tasks but have no intrinsic motivation, no real memory, no self-modification capability, and no discourse-relevant behavior.

## Solution

Redesign the cognitive architecture while staying entirely within the artifact cluster pattern:

1. **Fix Plan #312 bugs** — invoke uses `invoke()` global, add `has_standing` param, add `transfer` action
2. **Restore five drives** — Will to Understanding/Power/Novelty/Social Clout/Self-Evolution
3. **5-phase cognitive loop** — ORIENT → DECIDE → ACT → REFLECT → UPDATE
4. **Structured memory** — Episodic (reflections), Semantic (domain/strategy/ecosystem), Procedural (verified skills)
5. **Discourse corpus** — Sample texts across argument, narrative, and rhetoric domains

## Research Basis

- **Reflexion** — Structured self-reflection with episodic memory
- **Voyager** — Verified skill library with semantic retrieval
- **BabyAGI** — Task creation/prioritization as separate reasoning steps
- **CoALA** — Three memory types with quality-gated storage

## Files Changed

| File | Change |
|------|--------|
| `config/genesis/agents/discourse_v2/loop_code.py` | 5-phase cognitive loop with bug fixes |
| `config/genesis/agents/discourse_v2_2/loop_code.py` | Same (copy) |
| `config/genesis/agents/discourse_v2_3/loop_code.py` | Same (copy) |
| `config/genesis/agents/discourse_v2/strategy.md` | Five drives, argument & logic domain |
| `config/genesis/agents/discourse_v2_2/strategy.md` | Five drives, narrative & sequence domain |
| `config/genesis/agents/discourse_v2_3/strategy.md` | Five drives, rhetoric & persuasion domain |
| `config/genesis/agents/discourse_v2/initial_state.json` | Structured memory + research tasks |
| `config/genesis/agents/discourse_v2_2/initial_state.json` | Same pattern |
| `config/genesis/agents/discourse_v2_3/initial_state.json` | Same pattern |
| `config/genesis/artifacts/discourse_corpus.yaml` | New: corpus manifest |
| `config/genesis/artifacts/discourse_corpus.json` | New: 10 sample texts |

## No src/ Changes

All changes are to config/genesis files (agent artifacts). No kernel modifications.
