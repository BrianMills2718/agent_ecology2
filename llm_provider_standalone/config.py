"""
LLM Configuration

Edit these values to customize LLM behavior across the application.
"""

import os


# ============================================================================
# LLM Provider Settings
# ============================================================================

LLM_CONFIG = {
    # Model configuration
    "model": "gpt-5-mini-2025-08-07",

    # Retry and timeout
    "max_retries": 3,
    "timeout": 300.0,  # seconds (5 minutes)

    # Logging
    "log_dir": "llm_logs",
    "log_retention_days": 10,  # Auto-delete logs older than this (None = keep forever)

    # API key (leave as None to use OPENAI_API_KEY from .env)
    "api_key": os.getenv("OPENAI_API_KEY"),
}


# ============================================================================
# Advanced Settings (optional)
# ============================================================================

# Batch processing concurrency
MAX_CONCURRENT_REQUESTS = 5

# Default system prompt (if needed)
DEFAULT_SYSTEM_PROMPT = None
