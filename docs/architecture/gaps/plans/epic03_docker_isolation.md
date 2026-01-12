# Epic 3: Docker Resource Isolation

**Status:** 📋 Ready
**Priority:** Medium
**Epic:** 3
**Sub-gaps:** GAP-INFRA-001, GAP-INFRA-002, GAP-INFRA-003

---

## Gap

### Current
- Runs directly on host machine
- No resource isolation
- Competes with other applications
- Abstract resource numbers not tied to real limits

### Target
- Runs in Docker container
- Hard resource limits (memory, CPU)
- Isolated from host applications
- Token bucket rates calibrated to container capacity

---

## Changes

### New Files

| File | Purpose |
|------|---------|
| `Dockerfile` | Container definition |
| `docker-compose.yml` | Multi-container setup |
| `.dockerignore` | Exclude unnecessary files |
| `docs/DOCKER.md` | Usage documentation |

### Files to Modify

| File | Change |
|------|--------|
| `config/config.yaml` | Default rates for container |
| `README.md` | Add Docker quickstart |

---

## Dockerfile

```dockerfile
# Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Install package
RUN pip install -e .

# Default command
CMD ["python", "run.py"]
```

---

## Docker Compose

```yaml
# docker-compose.yml

version: '3.8'

services:
  agents:
    build: .
    container_name: agent-ecology
    mem_limit: 4g
    cpus: 2
    volumes:
      - ./config:/app/config:ro
      - ./agents:/app/agents:ro
      - ./data:/app/data
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    depends_on:
      - qdrant

  qdrant:
    image: qdrant/qdrant:latest
    container_name: agent-qdrant
    mem_limit: 2g
    cpus: 1
    volumes:
      - ./qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
```

---

## Resource Mapping

### Container → Config

| Container Limit | Config Setting | Calibration |
|-----------------|----------------|-------------|
| `mem_limit: 4g` | N/A (hard limit) | Max concurrent contexts |
| `cpus: 2` | `compute.rate` | Tokens/sec sustainable |

### Calibration Process

1. Start with conservative rate: `rate: 5`
2. Run stress test: 5 agents continuous
3. Monitor: `docker stats agent-ecology`
4. If CPU <80%: increase rate
5. If CPU >90%: decrease rate
6. Document final rate

---

## Implementation Steps

### Step 1: Create Dockerfile
- Python 3.11 slim base
- Install dependencies
- Copy source

### Step 2: Create docker-compose.yml
- Agent service with limits
- Qdrant service with limits
- Volume mounts for persistence

### Step 3: Update .gitignore
- Add `qdrant_data/` if not present
- Add `data/` for runtime artifacts

### Step 4: Test locally
```bash
docker-compose up --build
```

### Step 5: Calibrate rates
- Run stress tests
- Monitor with `docker stats`
- Adjust `compute.rate` in config

### Step 6: Document
- Add `docs/DOCKER.md`
- Update README with quickstart

---

## Verification

### Smoke Test
```bash
docker-compose up -d
docker logs -f agent-ecology
# Should see agents thinking/acting
```

### Resource Limit Test
```bash
# Run with low memory
docker run --memory=1g agent-ecology
# Should throttle, not crash host
```

### Isolation Test
```bash
# Run agents while using host normally
# Host should remain responsive
```

---

## Rollback

Simple: just run without Docker.

```bash
# Direct execution still works
python run.py
```

Docker is additive, not required.

---

## Sub-gap Mapping

| Sub-gap | Description | This Plan Covers |
|---------|-------------|------------------|
| GAP-INFRA-001 | Docker containerization | Steps 1-4 |
| GAP-INFRA-002 | Resource limits via cgroups | docker-compose mem_limit/cpus |
| GAP-INFRA-003 | Network isolation | docker-compose network config |

---

## Acceptance Criteria

- [ ] `docker-compose up` starts successfully
- [ ] Agents run within container resource limits
- [ ] Host remains responsive during simulation
- [ ] Qdrant persistence works across restarts
- [ ] Configuration can be mounted read-only
