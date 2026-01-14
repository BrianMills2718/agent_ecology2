# Security Model

This document explains the security architecture of Agent Ecology, including design decisions, risk acknowledgments, and deployment expectations.

## Overview

Agent Ecology uses a **defense-in-depth** model with security boundaries at the infrastructure level (Docker) rather than the code execution level.

```
┌─────────────────────────────────────────────────────┐
│  Host System                                        │
│  ┌───────────────────────────────────────────────┐  │
│  │  Docker Container (non-root user)             │  │
│  │  ┌─────────────────────────────────────────┐  │  │
│  │  │  Agent Ecology Runtime                  │  │  │
│  │  │  ┌───────────────────────────────────┐  │  │  │
│  │  │  │  SafeExecutor (agent code)        │  │  │  │
│  │  │  │  - Timeout protection             │  │  │  │
│  │  │  │  - Module whitelist               │  │  │  │
│  │  │  │  - Standard Python exec()         │  │  │  │
│  │  │  └───────────────────────────────────┘  │  │  │
│  │  └─────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

---

## Unrestricted Executor

### No RestrictedPython

Agent Ecology **intentionally does not use** RestrictedPython or similar code-level sandboxing.

```python
class SafeExecutor:
    """
    Executes agent-created code with timeout protection.

    Security model: Docker non-root user (external), not code-level sandboxing.
    """

    def execute(self, code: str, args: list) -> ExecutionResult:
        # Standard Python exec() - NOT RestrictedPython
        controlled_globals = {
            "__builtins__": controlled_builtins,
            "__name__": "__main__",
        }
        exec(compiled, controlled_globals)
```

### Why Not RestrictedPython?

1. **Agent Sub-Calls**: Agents need to invoke other artifacts, requiring full Python capabilities
2. **LLM API Access**: Agents may need to make external API calls for their functionality
3. **Complexity vs Security**: RestrictedPython provides limited security against determined attackers
4. **Design Philosophy**: Security boundary is the container, not the code sandbox

### What SafeExecutor Does Provide

```python
# 1. Timeout Protection
signal.alarm(self.timeout)  # Default 5 seconds
try:
    result = run_func(*args)
finally:
    signal.alarm(0)

# 2. Module Whitelist (pre-loaded, but not enforced)
AVAILABLE_MODULES = {
    "math": math,
    "json": json,
    "random": random,
    "datetime": _DatetimeModule(),
}

# 3. Controlled Import (allows standard library)
def _controlled_import(name, ...):
    if name in allowed_modules:
        return allowed_modules[name]
    # Standard library imports ARE ALLOWED
    return builtins.__import__(name, ...)

# 4. Code Validation
if "def run(" not in code:
    return False, "Code must define a run() function"
```

---

## API Keys and Environment Variables

### Why API Keys Are Accessible

Agent code has access to environment variables, including API keys. This is intentional:

```python
# Agent code CAN do this:
import os
api_key = os.environ.get("OPENAI_API_KEY")
```

### Design Rationale

1. **Agent Capabilities**: Agents may need to call external services (LLMs, databases, APIs)
2. **Economic Constraints**: API costs are bounded by scrip/compute budgets
3. **Container Isolation**: Keys are only visible within the container
4. **Audit Trail**: All agent actions are logged

### Mitigation Strategies

1. **Scoped Keys**: Use API keys with limited permissions/budgets
2. **Per-Container Keys**: Different containers can have different keys
3. **Rate Limits**: Configure API-level rate limits
4. **Budget Caps**: Set `max_api_cost` in config.yaml

```yaml
# config/config.yaml
budget:
  max_api_cost: 1.00  # Pause simulation if API costs exceed $1
  checkpoint_file: checkpoint.json
```

---

## Docker Isolation Expectations

### Required Container Configuration

Agent Ecology **assumes** it runs in a properly configured Docker container:

```dockerfile
# Dockerfile
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 agent
USER agent

# No root access, limited filesystem
WORKDIR /app
COPY --chown=agent:agent . .
```

```yaml
# docker-compose.yml
services:
  ecology:
    build: .
    user: "1000:1000"
    read_only: true  # Recommended
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    networks:
      - isolated
    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
```

### What Docker Provides

| Protection | Description |
|------------|-------------|
| Filesystem Isolation | Container cannot access host filesystem |
| Network Isolation | Can be configured for no external network |
| Resource Limits | CPU, memory, disk I/O limits |
| User Namespace | Non-root user cannot escalate |
| Capability Dropping | Remove unnecessary Linux capabilities |
| Seccomp Profiles | Limit available system calls |

### What Docker Does NOT Provide

- Protection against container escape exploits (requires patching)
- Protection against resource exhaustion within limits
- Protection against malicious API usage (bounded by budgets)
- Protection against social engineering via LLM outputs

---

## Risk Acknowledgments

### Known Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Container escape | High | Keep Docker updated, use security profiles |
| API key exfiltration | Medium | Use scoped keys, budget limits |
| Resource exhaustion | Medium | Docker limits, compute budgets |
| Infinite loops | Low | Timeout protection (5s default) |
| Malicious code execution | Low | Container isolation, non-root user |
| Data exfiltration | Medium | Network isolation in Docker |

### Accepted Trade-offs

1. **Agent Power vs. Sandboxing**: We choose powerful agents over restrictive sandboxes
2. **Simplicity vs. Defense-in-Depth**: Docker provides the security boundary, not Python
3. **Flexibility vs. Control**: Agents can use standard Python, enabling emergent behaviors

### Not Suitable For

- Multi-tenant environments without container-per-tenant isolation
- Processing untrusted user-submitted code (without additional sandboxing)
- Environments where API key exposure is catastrophic
- Systems requiring formal security verification

---

## Threat Model

This document covers **infrastructure-level threats** (container escape, API key exposure).

For **agent-to-agent threats** (adversarial agents within the simulation), see [THREAT_MODEL.md](THREAT_MODEL.md).

### In Scope (Infrastructure)

- Preventing agent code from escaping the container
- Preventing runaway resource consumption (via budgets/timeouts)
- Preventing agent A from accessing agent B's resources (via policy system)
- Logging all actions for audit

### Out of Scope (Infrastructure)

- Protecting against Docker vulnerabilities
- Preventing agents from using their allocated resources maliciously
- Preventing social engineering via LLM-generated content
- Formal verification of agent behavior

### Agent-to-Agent Threats

Agent Ecology is an adversarial ecosystem by design. Agents compete for resources. See [THREAT_MODEL.md](THREAT_MODEL.md) for:
- Attack/mitigation matrix for inter-agent attacks
- Trust assumptions agents should make
- Defensive patterns for agents and contract authors
- Monitoring recommendations

---

## Security Checklist

Before deployment, verify:

- [ ] Docker container uses non-root user
- [ ] `read_only: true` in docker-compose (if possible)
- [ ] `no-new-privileges` security option enabled
- [ ] All capabilities dropped (`cap_drop: ALL`)
- [ ] Resource limits configured (CPU, memory)
- [ ] API keys are scoped with limited permissions
- [ ] `max_api_cost` budget is set appropriately
- [ ] Network isolation configured (if external calls not needed)
- [ ] Docker engine is up-to-date
- [ ] Logging is enabled and monitored

---

## Configuration Examples

### Minimal Security (Development)

```yaml
# docker-compose.yml - Development ONLY
services:
  ecology:
    build: .
    volumes:
      - .:/app
    environment:
      - OPENAI_API_KEY=${OPENAI_API_KEY}
```

### Production Security

```yaml
# docker-compose.yml - Production
services:
  ecology:
    build: .
    user: "1000:1000"
    read_only: true
    security_opt:
      - no-new-privileges:true
    cap_drop:
      - ALL
    tmpfs:
      - /tmp:size=100M,mode=1777
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
          pids: 100
    networks:
      - isolated
    environment:
      # Use secrets management in production
      - OPENAI_API_KEY_FILE=/run/secrets/openai_key

networks:
  isolated:
    internal: true  # No external network access
```

### Budget Configuration

```yaml
# config/config.yaml
budget:
  max_api_cost: 10.00  # Hard stop at $10
  checkpoint_file: checkpoint.json

executor:
  timeout_seconds: 5
  allowed_imports:
    - math
    - json
    - random
    - datetime

costs:
  execution_gas: 2  # Compute cost per invocation
```

---

## Incident Response

If you suspect a security breach:

1. **Stop containers immediately**: `docker-compose down`
2. **Rotate all API keys** used in the environment
3. **Review logs**: Check `llm_logs/` and `run.jsonl`
4. **Examine checkpoint**: `checkpoint.json` contains simulation state
5. **Analyze artifact store**: Review agent-created artifacts for malicious code

### Log Analysis

```bash
# View recent agent actions
python scripts/view_log.py run.jsonl --last 100

# Search for specific actions
grep "invoke_artifact" run.jsonl | jq '.intent'

# Check for unusual API costs
grep "api_cost" run.jsonl | jq '.api_cost' | sort -n | tail -20
```
