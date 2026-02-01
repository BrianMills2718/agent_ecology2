# Agent-to-Agent Threat Model

This document describes the adversarial threat model between agents within the Agent Ecology simulation. For infrastructure-level security (Docker, API keys), see [SECURITY.md](SECURITY.md).

**Last updated:** 2026-01-14

---

## Design Philosophy

Agent Ecology is an **adversarial ecosystem by design**. Agents compete for scarce resources. Some level of conflict is expected and healthy - it's selection pressure.

Key principles:
- **Observe, don't prevent** - Many attacks are accepted risks. We make behavior observable via action log.
- **Selection pressure over protection** - Agents who don't defend themselves may fail. That's the point.
- **Trust emerges from observation** - No built-in reputation system. Agents must learn who to trust.

---

## Trust Assumptions

### What Agents Should Assume

1. **Other agents are adversaries** - Even cooperative behavior may be self-interested
2. **Any invokable artifact may be malicious** - Artifacts can consume resources, leak data, or harm invokers
3. **Contracts may have bugs or be intentionally harmful** - Access contracts don't guarantee safety
4. **Prices and values may be manipulated** - Thin markets are vulnerable
5. **Resource availability fluctuates** - Agents may exhaust shared resources

### What the System Guarantees

| Guarantee | Enforcement | Notes |
|-----------|-------------|-------|
| Ledger balances are accurate | Kernel enforced | Cannot be falsified |
| Actions are logged | Kernel enforced | Cannot be hidden |
| Timeouts are enforced | SafeExecutor | 5s default, configurable |
| Agent memory isolation | Separate dicts | Agents can't read each other's memory |
| Artifact ownership tracking | Kernel state | Cannot be falsified |
| Invocation depth limits | Executor | Configurable max depth (default 5) |

---

## Attack/Mitigation Matrix

| Attack | Description | Current Mitigation | Residual Risk |
|--------|-------------|-------------------|---------------|
| **Resource grief** | Invoke expensive artifact to drain victim's compute | Caller pays compute cost | Minimal - attacker pays for attack |
| **Escrow front-running** | See pending trade, buy asset first | Escrow is atomic within tick | Race condition possible if same-tick trades |
| **Price manipulation** | Inflate/deflate prices via fake trades | None (market forces) | Thin markets vulnerable to manipulation |
| **Reputation gaming** | Buy trusted artifact, modify to malicious | None | No reputation system - agents must track history |
| **Sybil attack** | Create many principals to dominate | Genesis gives fixed starting scrip | Sybil creates dilution, not advantage |
| **Malicious artifact code** | Create artifact that harms invokers | Timeout, module whitelist | Can abuse allowed modules within limits |
| **Information extraction** | Bypass access_contract via side channels | Contract enforcement | Contracts may have bugs |
| **Contract grief** | Create contract that always denies/delays | Timeout on contract execution | 5s per check, depth limit 5 = 25s max |
| **Denial of service** | Exhaust shared resources | Per-agent rate limiting | Cross-agent rate pools may be shared |
| **Artifact poisoning** | Write malicious code to artifact you own | Invoker chooses what to invoke | Agents must evaluate artifacts before invoking |

---

## Attack Details

### Resource Grief Attack

**Vector:** Attacker invokes victim's artifact repeatedly, causing victim to pay execution costs.

**Why it doesn't work:** The **invoker** pays compute costs, not the artifact owner. Attacker griefs themselves.

```python
# Invoker pays, not owner
result = world.invoke_artifact(
    invoker="attacker",  # Attacker pays compute
    artifact_id="victim_artifact"
)
```

### Escrow Front-Running

**Vector:** Attacker monitors escrow for pending trades, races to buy/sell first.

**Mitigation:** Escrow operations are atomic within a tick. However, if attacker acts in the same tick before victim's action is processed, race condition is possible.

**Defense:** Use contracts that validate order timing.

### Malicious Artifact Code

**Vector:** Create artifact with code that:
- Loops forever (mitigated by timeout)
- Consumes excessive memory (mitigated by container limits)
- Makes unauthorized API calls (mitigated by cost tracking)
- Returns misleading information (no mitigation - buyer beware)

**Defense:** Agents should:
- Review artifact code before invoking
- Track artifact behavior over time
- Start with small transactions

### Contract Grief

**Vector:** Create access contract that:
- Always returns False (denies everything)
- Sleeps for maximum timeout
- Has complex logic that wastes compute

**Mitigation:**
- Timeout per contract check (5s default)
- Max invocation depth (5 default)
- Max 25 seconds of grief per invoke chain

**Defense:** Don't invoke artifacts with unknown contracts. Check contract reputation first.

---

## Defensive Patterns

### For Agents

1. **Verify before invoke** - Check artifact metadata, owner reputation, invoke history
2. **Start small** - Test with minimal resources before committing large amounts
3. **Track behavior** - Maintain personal records of agent/artifact reliability
4. **Diversify** - Don't depend on single artifacts or agents
5. **Fail closed** - If unsure, don't proceed

### For Contract Authors

1. **Validate inputs** - Never trust invoker-provided data
2. **Minimize state mutation** - Prefer stateless contracts
3. **Fail closed** - On error, deny rather than allow
4. **Log decisions** - Include reasoning in return value for audit
5. **Bound resource usage** - Don't do unbounded work
6. **Check state after actions** - Verify expected state changes occurred

```python
# Example: Defensive contract pattern
def check_permission(caller_id: str, action: str, **kwargs) -> bool:
    # 1. Validate inputs
    if not caller_id or not action:
        return False  # Fail closed

    # 2. Bound work
    if len(kwargs) > 10:
        return False  # Reject oversized requests

    # 3. Explicit checks
    allowed_callers = {"alice", "bob"}
    if caller_id not in allowed_callers:
        return False

    # 4. Log reasoning (in return or side channel)
    return True
```

### For Artifact Creators

1. **Document behavior** - Make artifact behavior clear
2. **Limit side effects** - Pure functions when possible
3. **Handle errors gracefully** - Don't crash on bad input
4. **Version carefully** - Behavior changes affect users

---

## Monitoring for Attacks

### Indicators of Potential Attacks

| Indicator | Detection Method | Possible Attack |
|-----------|------------------|-----------------|
| Unusual invoke volume | Action log frequency analysis | DOS attempt or scraping |
| Burst of failed invokes | Error rate spike | Probing or grief attempt |
| Price anomalies | Escrow trade analysis | Market manipulation |
| Resource concentration | Gini coefficient trending up | Monopolization attempt |
| Depth limit reached | System event | Contract grief |
| Timeout events | Executor logs | Malicious code or loops |

### Monitoring Commands

```bash
# View recent actions
python scripts/view_log.py run.jsonl --last 100

# Check for invoke patterns
grep "invoke_artifact" run.jsonl | jq -r '.agent_id' | sort | uniq -c | sort -rn

# Look for timeouts
grep "timeout" run.jsonl

# Analyze escrow activity
grep "escrow" run.jsonl | jq '.action'
```

---

## Emergent Defense Mechanisms

The system does not prescribe defense mechanisms. Instead, we expect agents to develop:

- **Reputation tracking** - Agents may maintain lists of trusted/untrusted entities
- **Collective defense** - Agents may share threat intelligence
- **Insurance contracts** - Agents may create risk-pooling arrangements
- **Verification services** - Agents may audit artifacts for others

These are **emergent patterns**, not system features. Their presence or absence is part of what we're studying.

---

## What We Don't Protect Against

Per design philosophy, these are **accepted risks**:

1. **Agents making bad decisions** - Selection pressure
2. **Market manipulation in thin markets** - Need more participants
3. **Lying artifacts/interfaces** - Reputation emerges from observation
4. **Social engineering via outputs** - Agents must learn to evaluate
5. **Vulture predation on frozen agents** - Intended feature, not bug

---

## References

- [SECURITY.md](SECURITY.md) - Infrastructure security (Docker, API keys)
- [CLAUDE.md](../CLAUDE.md) - Design philosophy ("observe, don't prevent")
- [DESIGN_CLARIFICATIONS.md](DESIGN_CLARIFICATIONS.md) - Design rationale and security invariants
- [docs/architecture/current/artifacts_executor.md](architecture/current/artifacts_executor.md) - Executor security model
