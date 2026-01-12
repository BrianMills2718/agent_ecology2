# Target Infrastructure

What we're building toward.

**Last verified:** 2026-01-12

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

### Scaling to Multiple Containers

When a single container can't support enough agents (100+ agents, high-throughput scenarios), scale horizontally with multiple agent containers sharing state services.

#### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         Shared Services                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │   PostgreSQL    │  │     Redis       │  │     Qdrant      │  │
│  │   (Ledger)      │  │   (Events)      │  │   (Memory)      │  │
│  │   2GB, 1 CPU    │  │   1GB, 1 CPU    │  │   4GB, 2 CPU    │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
           │                    │                    │
           └────────────────────┼────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
┌───────▼───────┐       ┌───────▼───────┐       ┌───────▼───────┐
│  Agent Node 1 │       │  Agent Node 2 │       │  Agent Node N │
│  Agents 1-50  │       │  Agents 51-100│       │  Agents ...   │
│  4GB, 2 CPU   │       │  4GB, 2 CPU   │       │  4GB, 2 CPU   │
└───────────────┘       └───────────────┘       └───────────────┘
```

#### Shared State Services

**PostgreSQL (Ledger):**
- All ledger operations go through shared database
- SQLite not suitable for multi-container (file locking issues)
- Transactions ensure atomicity across containers
- Connection pooling per agent node

```python
# Each agent node connects to shared PostgreSQL
class DistributedLedger:
    def __init__(self, pg_url: str):
        self.pool = asyncpg.create_pool(pg_url, min_size=5, max_size=20)

    async def transfer(self, from_id, to_id, amount, resource) -> bool:
        async with self.pool.acquire() as conn:
            async with conn.transaction():
                # Same atomic transfer logic, but PostgreSQL handles locking
                ...
```

**Redis (Event Bus):**
- Pub/sub for cross-container events
- Agents in any container can wake agents in any other container
- No event queuing (fire-and-forget, agents poll on restart)

```python
class DistributedEventBus:
    def __init__(self, redis_url: str):
        self.redis = aioredis.from_url(redis_url)
        self.pubsub = self.redis.pubsub()

    async def publish(self, event: Event) -> None:
        await self.redis.publish(f"events:{event.type}", event.json())

    async def subscribe(self, agent_id: str, event_type: str) -> None:
        await self.pubsub.subscribe(f"events:{event_type}")
```

**Qdrant (Memory):**
- Already designed as separate service
- All agent nodes connect to same Qdrant instance
- Memory artifacts reference collections in shared Qdrant

#### Agent Assignment

Agents are statically assigned to containers at startup:

```yaml
# docker-compose.yml
services:
  agent-node-1:
    environment:
      AGENT_RANGE: "1-50"
      POSTGRES_URL: postgres://ledger:5432/ecology
      REDIS_URL: redis://events:6379
      QDRANT_URL: http://qdrant:6333

  agent-node-2:
    environment:
      AGENT_RANGE: "51-100"
      # Same shared service URLs
```

**Why static assignment:**
- Simpler - no agent migration logic
- Predictable - know where each agent runs
- Sufficient - agents don't need to move between containers

**Dynamic assignment (future):**
- Would require agent state serialization
- Coordination service (etcd/consul) for assignment
- Not needed for initial scaling

#### Cross-Container Agent Interaction

Agents in different containers interact normally via shared services:

| Operation | Mechanism | Container Boundary |
|-----------|-----------|-------------------|
| Transfer scrip | PostgreSQL transaction | Transparent |
| Read artifact | PostgreSQL query | Transparent |
| Wake sleeping agent | Redis pub/sub | Transparent |
| Access memory | Qdrant query | Transparent |

**Latency consideration:** Cross-container operations add ~1-5ms network latency. Acceptable for LLM-driven agents (thinking takes seconds).

#### docker-compose Example

```yaml
version: '3.8'

services:
  # Shared services
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: ecology
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1'

  redis:
    image: redis:7
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '1'

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2'

  # Agent nodes (scale as needed)
  agent-node:
    image: agent-ecology:latest
    environment:
      POSTGRES_URL: postgres://postgres:${POSTGRES_PASSWORD}@postgres:5432/ecology
      REDIS_URL: redis://redis:6379
      QDRANT_URL: http://qdrant:6333
    deploy:
      replicas: 3
      resources:
        limits:
          memory: 4G
          cpus: '2'

volumes:
  postgres_data:
  qdrant_data:
```

#### When to Scale

| Scenario | Recommendation |
|----------|----------------|
| < 50 agents | Single container, SQLite ledger |
| 50-200 agents | Single container, consider PostgreSQL |
| 200+ agents | Multiple containers, PostgreSQL + Redis |
| High availability | Kubernetes with PostgreSQL HA |

#### Kubernetes (Future)

For production at scale, Kubernetes provides:
- Automatic container restart on failure
- Horizontal pod autoscaling
- Service discovery
- Rolling updates

```yaml
# Simplified k8s example
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-nodes
spec:
  replicas: 5
  template:
    spec:
      containers:
      - name: agent-ecology
        resources:
          limits:
            memory: "4Gi"
            cpu: "2"
```

This is beyond MVP scope but the architecture supports it.

### Local LLM Support

Two patterns depending on hardware:

| Setup | Pattern | Resource Tracking |
|-------|---------|-------------------|
| CPU-only (llama.cpp) | Run in worker pool | `resource.getrusage()` captures automatically |
| GPU-based (vLLM, TGI) | Separate model server | GPU metrics via server API |

Details TBD based on deployment requirements.

### Git-Backed Artifact Store

The artifact store uses Git as its backend:

```
┌─────────────────────────────────────────────────────────┐
│                    Docker Container                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │           Current Commit (HEAD)                  │   │
│  │  • Physical reality agents can see/modify       │   │
│  │  • Constrained by disk quotas                   │   │
│  │  • write_artifact() creates new commit          │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                          │
                          │ (boundary)
                          ▼
┌─────────────────────────────────────────────────────────┐
│                   Git History                            │
│  • Observer-only (human admin, not agents)              │
│  • Immutable audit trail of all changes                 │
│  • Enables safe rollback without agent "time travel"    │
│  • Prevents "history as free storage" exploit           │
└─────────────────────────────────────────────────────────┘
```

**Why observer-only history:**

| Concern | Solution |
|---------|----------|
| Free storage exploit | Agents can't read history, so can't use it as unbounded storage |
| Debugging | Admin can rewind to see what caused failures |
| Recovery | Admin can rollback bad states; agents see it as "system reset" |
| Audit | Complete provenance of every artifact change |

**The "free storage" exploit (prevented):**
1. Agent commits 1GB of data
2. Agent overwrites with new data
3. Agent tries to retrieve old data from history
4. **Blocked** - agents can only access current commit

**Future consideration:** Could expose limited history access as premium feature (expensive retrieval cost scaling with age), but not needed for V1.

### Monitoring

- Container stats (CPU, memory, network)
- Agent metrics (actions/sec, blocked status)
- LLM costs ($)

### Restart Policy

```bash
docker run --restart=unless-stopped agent-ecology
```

Recover from crashes automatically.
