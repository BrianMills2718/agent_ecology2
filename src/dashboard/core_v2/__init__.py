"""Dashboard core business logic.

Structured into:
- event_parser.py: Parse JSONL → typed events
- state_tracker.py: Events → current state
- metrics_engine.py: State → computed metrics
"""

from .event_parser import EventParser
from .state_tracker import StateTracker
from .metrics_engine import MetricsEngine

__all__ = [
    "EventParser",
    "StateTracker",
    "MetricsEngine",
]
