# Agents package - Plan #299: Legacy agent system removed
#
# The legacy agent system has been removed. Agents are now artifacts:
# - has_loop=True artifacts run autonomously via ArtifactLoopManager
# - has_standing=True artifacts can hold resources
# - Strategy, state, and loop code are separate artifacts
#
# See: config/genesis/agents/alpha_prime/ for the pattern
# See: docs/catalog.yaml for historical agent lineage

__all__: list[str] = []
