# Gap 19: Agent-to-Agent Threat Model

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** No documented agent-vs-agent attack surface

**Target:** Documented threat model with mitigations

---

## Problem Statement

SECURITY.md focuses on Docker isolation (system vs external threats). However, in a competitive agent ecosystem, agents themselves are adversaries. There is no documentation of:

- What attacks are possible between agents?
- What mitigations exist?
- What trust assumptions should agents make?
- How should contract authors protect against attacks?

This is especially important because:
1. Adversarial agents are **expected** (competitive ecosystem)
2. Without explicit threat model, mitigations are ad-hoc
3. Contract authors need guidance to write defensive code
4. System auditors need to know what to watch for

---

## Plan

### Phase 1: Document Known Attack Vectors

Create `docs/THREAT_MODEL.md` documenting agent-to-agent attacks.

**Attack/Mitigation Matrix:**

| Attack | Description | Current Mitigation | Residual Risk |
|--------|-------------|-------------------|---------------|
| **Grief via contract** | Invoke expensive contract to drain victim | Max depth 5, 5s timeout | 25 seconds x depth can still be extracted |
| **Front-running escrow** | See pending trade, buy asset first | Escrow is atomic | Race condition if same tick |
| **Price manipulation** | Artificially inflate/deflate prices | None (market forces) | Thin markets vulnerable |
| **Reputation gaming** | Buy trusted artifact, modify to malicious | None | No reputation system yet |
| **Resource exhaustion** | Exhaust shared resource (rate limits) | Token bucket per agent | Cross-agent rate is shared |
| **Malicious artifact code** | Create artifact that harms invokers | Timeout, module whitelist | Can still abuse allowed modules |
| **Information extraction** | Bypass access_contract via side channels | Contract enforcement | Contracts may have bugs |
| **Sybil attack** | Create many agents to dominate | None | Genesis mint gives everyone scrip |

### Phase 2: Document Trust Assumptions

**What Agents Should Assume:**
1. Other agents are adversaries
2. Any invokable artifact may be malicious
3. Contracts may have bugs or be intentionally harmful
4. Prices/values may be manipulated
5. Resource availability may fluctuate

**What the System Guarantees:**
1. Ledger balances are accurate (kernel enforced)
2. Actions are logged (cannot be hidden)
3. Timeouts are enforced (bounded compute per invoke)
4. Agent isolation (separate memory spaces)
5. Artifact ownership (tracked correctly)

### Phase 3: Guidance for Contract Authors

Add section to SECURITY.md or new doc:

```markdown
## Defensive Contract Writing

1. **Validate inputs** - Never trust invoker-provided data
2. **Minimize state mutation** - Prefer stateless contracts
3. **Fail closed** - On error, deny rather than allow
4. **Log decisions** - Include reasoning in return value
5. **Bound resource usage** - Don't do unbounded work
6. **Avoid reentrancy** - Check state before and after
```

### Phase 4: Monitoring Recommendations

Document what to watch for:

| Indicator | Detection | Response |
|-----------|-----------|----------|
| Unusual invoke volume | Action log analysis | Rate limit, investigate |
| Failed invoke bursts | Error rate monitoring | May indicate attack |
| Price anomalies | Escrow trade analysis | Market manipulation check |
| Resource concentration | Gini coefficient | Inequality may indicate gaming |
| Contract depth exceeded | System event | Potential grief attack |

---

## Changes Required

| File | Change |
|------|--------|
| `docs/THREAT_MODEL.md` | **NEW** - Main threat model document |
| `docs/SECURITY.md` | Add reference to THREAT_MODEL.md |
| `docs/architecture/current/` | Update to reference threat model |

### Implementation Steps

1. **Create THREAT_MODEL.md** - Main document with attack matrix
2. **Add trust assumptions** - What agents should/shouldn't assume
3. **Add contract guidance** - How to write defensive contracts
4. **Add monitoring section** - What to watch for
5. **Update SECURITY.md** - Link to new document
6. **Review existing docs** - Ensure consistency

---

## Required Tests

**Note:** This is primarily a documentation task. No code changes expected.

### Verification
- Manual review of THREAT_MODEL.md for completeness
- Cross-reference with SECURITY.md for consistency
- Verify attack matrix matches known mitigations in code

---

## E2E Verification

Documentation-only plan - verify by:

1. **Read through THREAT_MODEL.md** - Is it comprehensive?
2. **Try example attacks** - Do documented mitigations work?
3. **Contract author review** - Is guidance actionable?

```bash
# Verify documentation exists and is linked
cat docs/THREAT_MODEL.md
grep -r "THREAT_MODEL" docs/
```

---

## Out of Scope

- **Implementing new mitigations** - Document existing, don't add new
- **Formal verification** - Informal analysis only
- **Automated attack detection** - Manual monitoring guidance
- **Reputation system** - Separate gap (#27 partially)

---

## Verification

- [ ] THREAT_MODEL.md created
- [ ] Attack/mitigation matrix complete
- [ ] Trust assumptions documented
- [ ] Contract guidance added
- [ ] Monitoring recommendations included
- [ ] SECURITY.md updated

---

## Notes

This is a **documentation task**, not implementation. The goal is to make explicit what is currently implicit - the adversarial nature of the agent ecosystem and the trust boundaries.

Key principle from CLAUDE.md: "Observe, don't prevent. Many risks are accepted. Make behavior observable via action log."

The threat model should reflect this - we document attacks and mitigations, but many attacks are **accepted risks** that we observe rather than prevent.

Reference: docs/DESIGN_CLARIFICATIONS.md Section 17 "Edge Case Decisions"
