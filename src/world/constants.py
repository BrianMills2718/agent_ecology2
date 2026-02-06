"""Centralized constants for the world module.

Kernel contract IDs and system-level constants live here to avoid
string literals scattered across modules (TD-008).
"""

# System principal ID for kernel-created artifacts
SYSTEM_OWNER = "SYSTEM"

# Genesis artifact ID prefix
GENESIS_PREFIX = "genesis_"

# Kernel contract IDs — match the contract_id fields in kernel_contracts.py
KERNEL_CONTRACT_FREEWARE = "kernel_contract_freeware"
KERNEL_CONTRACT_TRANSFERABLE_FREEWARE = "kernel_contract_transferable_freeware"
KERNEL_CONTRACT_SELF_OWNED = "kernel_contract_self_owned"
KERNEL_CONTRACT_PRIVATE = "kernel_contract_private"
KERNEL_CONTRACT_PUBLIC = "kernel_contract_public"
