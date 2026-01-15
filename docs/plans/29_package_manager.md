# Gap 29: Library Installation

**Status:** ✅ Complete

**Verified:** 2026-01-15T00:35:03Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-15T00:35:03Z
tests:
  unit: 1347 passed, 7 skipped in 16.60s
  e2e_smoke: PASSED (2.59s)
  e2e_real: PASSED (4.48s)
  doc_coupling: passed
commit: aaaa5d7
```
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Only pre-installed libraries available to agents.

**Target:** Genesis libraries (free) + quota-based installation for additional packages.

---

## Design

### Genesis Libraries (Pre-installed, Free)

Baked into Docker image, don't count against quota:

| Category | Libraries |
|----------|-----------|
| **Stdlib** | All standard library modules |
| **HTTP** | `requests`, `aiohttp`, `urllib3` |
| **Data** | `numpy`, `pandas`, `python-dateutil` |
| **Config** | `pyyaml`, `pydantic` |
| **Scientific** | `scipy`, `matplotlib` |
| **Crypto** | `cryptography` |

These are cold-start conveniences, like genesis artifacts.

### New Libraries = Quota Cost

`pip install X` counts installed size against disk quota.

```python
kernel_actions.install_library("scikit-learn")  # Deducts from disk quota
```

### Security Blocklist (Minimal)

Block only sandbox-escape risks:

| Package | Risk |
|---------|------|
| `docker` | Docker daemon access |
| `debugpy` | Debugger attachment |

Everything else is safe within Docker isolation.

---

## Plan

### Phase 1: Genesis Libraries

1. Update Dockerfile with pre-installed packages
2. Document in agent handbook

### Phase 2: Runtime Installation

1. Add `install_library(name)` to kernel actions
2. Check disk quota before install
3. Deduct installed size from quota

### Phase 3: Blocklist

1. Maintain blocklist in config
2. Reject blocked packages with clear error

---

## Required Tests

- `tests/unit/test_library_install.py::test_install_deducts_quota`
- `tests/unit/test_library_install.py::test_blocked_package_rejected`
- `tests/unit/test_library_install.py::test_insufficient_quota_fails`

---

## Verification

- [x] Genesis libraries available without quota cost
- [x] New installs deduct from disk quota
- [x] Blocked packages rejected
- [x] Tests pass
- [x] Handbook documents available libraries
