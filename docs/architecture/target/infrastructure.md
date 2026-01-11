# Target Infrastructure

What we're building toward.

---

## Docker Resource Isolation

### Why Docker

- Hard resource limits enforced by container runtime
- Isolates agent ecology from host system
- Host stays responsive even if agents misbehave
- Easy to test different resource scenarios

### Container Limits = Real Constraints

Docker limits ARE the resource constraints:

```bash
docker run --memory=4g --cpus=2 agent-ecology
```

| Flag | Effect |
|------|--------|
| `--memory=4g` | Hard cap at 4GB RAM |
| `--cpus=2` | Limit to 2 CPU cores |
| `--storage-opt` | Disk limits (driver-dependent) |

These are not abstract numbers. They're actual limits.

---

## Architecture Options

### Single Container

```
┌─────────────────────────────────────┐
│  Container (4GB, 2 CPU)             │
│  ┌─────────────────────────────┐    │
│  │  Agent Ecology + Qdrant     │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

Simpler. All resources shared.

### Separate Containers

```
┌─────────────────────────────────────┐
│  Container 1: Agents (4GB, 2 CPU)   │
│  ┌─────────────────────────────┐    │
│  │  Agent Ecology              │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│  Container 2: Qdrant (2GB, 1 CPU)   │
│  ┌─────────────────────────────┐    │
│  │  Vector Database            │    │
│  └─────────────────────────────┘    │
└─────────────────────────────────────┘
```

Better isolation. Agents can't starve Qdrant.

---

## Mapping Resources to Limits

### Compute Flow → CPU Limit

Token bucket rate calibrated to container CPU:

```
Container: 2 CPUs
Token bucket rate: X tokens/sec
Calibrate X so max concurrent agents don't exceed 2 CPUs
```

### Memory → RAM Limit

```
Container: 4GB
Per-agent memory: ~200-500MB
Max concurrent thinking agents: ~8-20
```

### Disk → Storage Limit

```yaml
resources:
  stock:
    disk:
      total: 500000  # 500KB per agent
```

Or use Docker storage limits if available.

---

## Windows Considerations

### Docker Desktop

- Uses WSL2 or Hyper-V
- Slight overhead vs native Linux
- Works fine for this use case

### Resource Visibility

```bash
# Check container resource usage
docker stats agent-ecology
```

---

## Development Environment

Reference specs for calibration:

| Component | Spec |
|-----------|------|
| Machine | Surface Laptop 4 |
| CPU | Intel i7-1185G7 (4 cores, 8 threads) |
| RAM | 32GB (often ~17GB available) |
| OS | Windows 11 |

Note: Developer often runs many other programs (Claude Code instances, browsers, etc.). Docker isolation prevents agent ecology from competing with these.

---

## Calibration Process

### Step 1: Baseline Container

```bash
docker run --memory=4g --cpus=2 agent-ecology
```

### Step 2: Run Stress Test

- Start 5 agents
- Full continuous loops
- Monitor container stats

### Step 3: Adjust Token Bucket Rate

If container maxes out:
- Reduce rate (fewer tokens/sec)
- Or increase container resources

If container underutilized:
- Increase rate
- More throughput possible

### Step 4: Document Sweet Spot

```yaml
# Calibrated for 4GB/2CPU container
resources:
  flow:
    compute:
      rate: 10          # tokens/sec per agent
      capacity: 100     # max tokens
```

---

## Production Considerations

### Scaling

Multiple containers, each with agent subset:

```
Container 1: Agents 1-10 (4GB, 2 CPU)
Container 2: Agents 11-20 (4GB, 2 CPU)
Shared: Qdrant container (4GB, 2 CPU)
```

### Monitoring

- Container stats (CPU, memory, network)
- Agent metrics (actions/sec, debt levels)
- LLM costs ($)

### Restart Policy

```bash
docker run --restart=unless-stopped agent-ecology
```

Recover from crashes automatically.
