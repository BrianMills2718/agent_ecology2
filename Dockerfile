# Agent Ecology Dockerfile
# Containerized simulation with resource limits

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (better layer caching)
COPY requirements.txt pyproject.toml ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY config/ ./config/
COPY llm_provider_standalone/ ./llm_provider_standalone/
COPY run.py ./
COPY scripts/ ./scripts/
COPY tests/ ./tests/

# Install package in editable mode
RUN pip install -e .

# Create data directory for runtime artifacts
RUN mkdir -p /app/data

# Environment defaults
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Default command
CMD ["python", "run.py"]
