# Docker Deployment

Run agent ecology in containers with enforced resource limits.

## Quick Start

```bash
# Start simulation with Qdrant
docker-compose up -d

# View logs
docker-compose logs -f simulation

# Stop
docker-compose down
```

## Services

| Service | Purpose | Port | Memory | CPU |
|---------|---------|------|--------|-----|
| `simulation` | Agent ecology simulation | - | 4GB | 2 |
| `qdrant` | Vector database for memory | 6333 | 2GB | 1 |
| `dashboard` | Web monitoring UI | 8080 | 512MB | 0.5 |

## Resource Limits

Resource limits enforce real scarcity (physics-first principle). Agents compete for limited compute within the container.

### Default Limits

```yaml
simulation:
  memory: 4G    # Hard limit - OOM killed if exceeded
  cpus: 2       # Throttled if exceeded

qdrant:
  memory: 2G
  cpus: 1
```

### Adjusting Limits

Edit `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 8G    # Increase for more agents
      cpus: '4'     # Increase for faster execution
```

## Environment Variables

Create a `.env` file:

```bash
# Required
GEMINI_API_KEY=your-api-key-here

# Optional (defaults shown)
QDRANT_HOST=qdrant
QDRANT_PORT=6333
```

## Volume Mounts

| Host Path | Container Path | Purpose |
|-----------|----------------|---------|
| `./config` | `/app/config` (ro) | Configuration files |
| `./agents` | `/app/agents` (ro) | Agent definitions |
| `./logs` | `/app/logs` | Simulation logs |
| `./llm_logs` | `/app/llm_logs` | LLM call logs |
| `./data` | `/app/data` | Runtime artifacts |
| `./qdrant_storage` | `/qdrant/storage` | Vector DB persistence |

## Commands

### Run Simulation

```bash
# Basic run
docker-compose up simulation

# With custom arguments
docker-compose run simulation python run.py --ticks 50 --agents 3

# Detached mode
docker-compose up -d simulation
```

### Run Dashboard

```bash
# Start dashboard (requires simulation running)
docker-compose --profile dashboard up -d

# Access at http://localhost:8080
```

### Run Tests

```bash
# Run test suite in container
docker-compose run simulation pytest tests/ -v
```

### Monitoring

```bash
# View resource usage
docker stats agent-ecology agent-qdrant

# View logs
docker-compose logs -f simulation

# Shell into container
docker-compose exec simulation bash
```

## Building

```bash
# Build image
docker-compose build

# Rebuild without cache
docker-compose build --no-cache

# Build and run
docker-compose up --build
```

## Troubleshooting

### Out of Memory

If container is OOM-killed:
1. Check logs: `docker-compose logs simulation`
2. Increase memory limit in `docker-compose.yml`
3. Reduce number of agents in `config/config.yaml`

### Qdrant Connection Failed

```bash
# Check Qdrant is running
docker-compose ps qdrant

# View Qdrant logs
docker-compose logs qdrant

# Restart Qdrant
docker-compose restart qdrant
```

### Permission Denied

Volume mount issues on Linux:
```bash
# Fix permissions
sudo chown -R $USER:$USER ./logs ./llm_logs ./data ./qdrant_storage
```

## Production Deployment

For production, consider:

1. **Use specific image tags** instead of `latest`
2. **Add health checks** to services
3. **Configure logging drivers** for log aggregation
4. **Use secrets management** instead of `.env` files
5. **Add restart policies** for fault tolerance

Example production additions:

```yaml
simulation:
  restart: unless-stopped
  healthcheck:
    test: ["CMD", "python", "-c", "import src"]
    interval: 30s
    timeout: 10s
    retries: 3
  logging:
    driver: json-file
    options:
      max-size: "10m"
      max-file: "3"
```

## Windows Notes

- Requires Docker Desktop with WSL2 backend
- Resource limits work but with slight overhead
- Use PowerShell or WSL2 terminal

```powershell
# Windows quickstart
docker-compose up -d
docker-compose logs -f
```
