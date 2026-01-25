# Plan #161: Agent Error Learning

**Status:** ✅ Complete
**Priority:** High
**Goal:** Help agents learn from errors by improving discoverability and error messages

---

## Context

Agents are making two types of errors repeatedly without learning:

1. **Wrong attribute name:** Using `artifact.artifact_type` instead of `artifact.type`
2. **Wrong method name:** Calling `run()` on artifacts that have custom method names

Root causes:
- Agents can't easily discover what attributes/methods exist BEFORE using them
- Error messages tell WHAT failed but not HOW to avoid it next time
- Handbook examples imply `run` is the standard method name

---

## Implementation

### 1. Artifact serves its own interface

**Current:** Must call `genesis_store.get_interface("my_artifact")`
**New:** Can call `my_artifact.describe()` directly

Every executable artifact automatically gets a `describe` method that returns its interface.

**Files:** `src/world/executor.py`

### 2. Better attribute error messages

When agent code accesses a non-existent attribute on an Artifact, provide a helpful suggestion.

**Current:** `AttributeError: 'Artifact' object has no attribute 'artifact_type'`
**New:** `AttributeError: 'Artifact' has no attribute 'artifact_type'. Did you mean 'type'? Available: id, type, content, created_by, executable, interface`

**Files:** `src/world/artifacts.py`

### 3. Better method-not-found error messages

**Current:** `Method 'run' not found. Available methods: ['list', 'search', 'describe']`
**New:** `Method 'run' not found. This artifact has custom methods: ['list', 'search', 'describe']. Call artifact_id.describe() to see method details before invoking.`

**Files:** `src/world/executor.py`

### 4. Update handbook

Add section on discovering artifact interfaces before invoking.

**Files:** `src/agents/_handbook/actions.md`

---

## Implementation Order

1. Artifact `describe()` method (enables discovery)
2. Better method-not-found errors (references describe)
3. Better attribute errors (helpful suggestions)
4. Handbook update (documents the pattern)

---

## Success Criteria

- [x] Agents can call `any_artifact.describe()` to get interface
- [x] Wrong attribute access shows suggestion with correct name
- [x] Method-not-found error explains how to discover methods
- [x] Handbook explains interface discovery pattern

---

## Files Affected

- `src/world/executor.py` (modify) - Add auto-describe method, improve error messages
- `src/world/world.py` (modify) - Improve method_not_found error message
- `src/world/artifacts.py` (modify) - Add `__getattr__` for helpful attribute errors
- `src/agents/_handbook/actions.md` (modify) - Add interface discovery guidance
- `tests/unit/test_error_learning.py` (create) - Tests for improved error messages

---

## Verification Evidence

- PR #641 merged: https://github.com/BrianMills2718/agent_ecology2/pull/641
- Tests: `tests/unit/test_error_learning.py` (6 tests pass)
- Implementation locations:
  - `describe()` method in `src/world/world.py:868-895`
  - `__getattr__` in `src/world/artifacts.py:270-297`
  - Handbook section in `src/agents/_handbook/actions.md:91-107`
  - Error message in `src/world/world.py:70`
