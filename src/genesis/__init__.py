"""Genesis artifact loading from config files (Plan #298).

Provides config-driven genesis: YAML files define what artifacts to create
at world initialization. This separates genesis data from kernel code.

Usage:
    from src.genesis import load_genesis
    load_genesis(world, Path("config/genesis"))
"""

from .loader import load_genesis

__all__ = ["load_genesis"]
