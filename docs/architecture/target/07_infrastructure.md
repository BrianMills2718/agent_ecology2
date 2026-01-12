# Target Infrastructure

What we're building toward.

**Last verified:** 2026-01-11

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

## Calibration Process

Token bucket rates must be calibrated to your container's capacity.

### Step 1: Baseline Container

Start with conservative limits:

```bash
docker run --memory=4g --cpus=2 agent-ecology
```

### Step 2: Run Stress Test

```bash
# Start 5 agents in continuous mode
# Monitor container stats in another terminal
docker stats agent-ecology
```

Watch for:
- CPU usage (target: 70-80% sustained)
- Memory usage (target: <90% of limit)
- Throttling indicators

### Step 3: Adjust Token Bucket Rate

**Calibration algorithm:**

```
1. Start with rate = 10 tokens/sec per agent
2. Run 5 agents at full continuous loop for 5 minutes
3. If CPU > 85%: reduce rate by 20% (rate = 8)
4. If CPU < 50%: increase rate by 25% (rate = 12.5)
5. Repeat until CPU stabilizes at 70-80%
```

### Step 4: Document Configuration

```yaml
# Example: Calibrated for 4GB/2CPU container
resources:
  flow:
    llm_rate:           # Token bucket for LLM API access
      rate: 10          # tokens/sec per agent
      capacity: 100     # max tokens storable
```

### Hardware Variability

Different hardware will need different calibration:

| Hardware Class | Suggested Starting Rate |
|----------------|------------------------|
| Laptop (4 cores) | 5-10 tokens/sec |
| Desktop (8 cores) | 10-20 tokens/sec |
| Server (16+ cores) | 20-50 tokens/sec |

These are starting points only. Always calibrate with stress testing.

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
