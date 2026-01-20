"""Genesis Debt Contract - Non-privileged lending example

A non-privileged example contract showing how to implement credit/lending.
Agents can build their own competing debt contracts.

Key insight: No magic enforcement. Bad debtors get bad reputation
via the event log, not kernel-level punishment.
"""

from __future__ import annotations

import uuid
from typing import Any

from ...config import get_validated_config
from ...config_schema import GenesisConfig
from ..ledger import Ledger
from .base import GenesisArtifact
from .types import DebtRecord


class GenesisDebtContract(GenesisArtifact):
    """
    Genesis artifact for debt/lending contracts.

    This is a NON-PRIVILEGED example contract showing how to implement
    credit/lending. Agents can build their own competing debt contracts.

    Key insight: No magic enforcement. Bad debtors get bad reputation
    via the event log, not kernel-level punishment.

    Flow:
    1. Debtor calls issue(creditor, principal, interest_rate, due_tick)
    2. Creditor calls accept(debt_id) - debt becomes active
    3. Debtor calls repay(debt_id, amount) to pay back
    4. After due_tick, creditor can call collect(debt_id) to attempt collection
    5. Creditor can call transfer_creditor(debt_id, new_creditor) to sell debt
    """

    ledger: Ledger
    debts: dict[str, DebtRecord]
    current_tick: int

    def __init__(
        self,
        ledger: Ledger,
        genesis_config: GenesisConfig | None = None
    ) -> None:
        """
        Args:
            ledger: The world's Ledger instance (for scrip transfers)
            genesis_config: Optional genesis config (uses global if not provided)
        """
        cfg = genesis_config or get_validated_config().genesis
        debt_cfg = cfg.debt_contract

        super().__init__(
            artifact_id=debt_cfg.id,
            description=debt_cfg.description
        )
        self.ledger = ledger
        self.debts = {}
        self.current_tick = 0

        # Register methods with costs/descriptions from config
        self.register_method(
            name="issue",
            handler=self._issue,
            cost=debt_cfg.methods.issue.cost,
            description=debt_cfg.methods.issue.description
        )
        self.register_method(
            name="accept",
            handler=self._accept,
            cost=debt_cfg.methods.accept.cost,
            description=debt_cfg.methods.accept.description
        )
        self.register_method(
            name="repay",
            handler=self._repay,
            cost=debt_cfg.methods.repay.cost,
            description=debt_cfg.methods.repay.description
        )
        self.register_method(
            name="collect",
            handler=self._collect,
            cost=debt_cfg.methods.collect.cost,
            description=debt_cfg.methods.collect.description
        )
        self.register_method(
            name="transfer_creditor",
            handler=self._transfer_creditor,
            cost=debt_cfg.methods.transfer_creditor.cost,
            description=debt_cfg.methods.transfer_creditor.description
        )
        self.register_method(
            name="check",
            handler=self._check,
            cost=debt_cfg.methods.check.cost,
            description=debt_cfg.methods.check.description
        )
        self.register_method(
            name="list_debts",
            handler=self._list_debts,
            cost=debt_cfg.methods.list_debts.cost,
            description=debt_cfg.methods.list_debts.description
        )
        self.register_method(
            name="list_all",
            handler=self._list_all,
            cost=debt_cfg.methods.list_all.cost,
            description=debt_cfg.methods.list_all.description
        )

    def set_tick(self, tick: int) -> None:
        """Update the current tick (called by World)."""
        self.current_tick = tick

    def _issue(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Issue a debt. Invoker becomes debtor.

        Args: [creditor_id, principal, interest_rate, due_tick]
        - creditor_id: Who will be owed the money
        - principal: Amount borrowed
        - interest_rate: Per-tick interest (e.g., 0.01 = 1% per tick)
        - due_tick: When the debt is due
        """
        if len(args) < 4:
            return {"success": False, "error": "issue requires [creditor_id, principal, interest_rate, due_tick]"}

        creditor_id: str = args[0]
        principal: Any = args[1]
        interest_rate: Any = args[2]
        due_tick: Any = args[3]

        # Validate inputs
        if not isinstance(principal, int) or principal <= 0:
            return {"success": False, "error": "Principal must be a positive integer"}
        if not isinstance(interest_rate, (int, float)) or interest_rate < 0:
            return {"success": False, "error": "Interest rate must be non-negative"}
        if not isinstance(due_tick, int) or due_tick <= self.current_tick:
            return {"success": False, "error": f"Due tick must be greater than current tick ({self.current_tick})"}

        # Cannot issue debt to yourself
        if creditor_id == invoker_id:
            return {"success": False, "error": "Cannot issue debt to yourself"}

        # Create debt record (pending until creditor accepts)
        debt_id = f"debt_{uuid.uuid4().hex[:8]}"
        self.debts[debt_id] = {
            "debt_id": debt_id,
            "debtor_id": invoker_id,
            "creditor_id": creditor_id,
            "principal": principal,
            "interest_rate": float(interest_rate),
            "due_tick": due_tick,
            "amount_owed": principal,  # Will accrue interest when active
            "amount_paid": 0,
            "status": "pending",
            "created_tick": self.current_tick
        }

        return {
            "success": True,
            "debt_id": debt_id,
            "debtor": invoker_id,
            "creditor": creditor_id,
            "principal": principal,
            "interest_rate": interest_rate,
            "due_tick": due_tick,
            "message": f"Debt {debt_id} issued. Creditor {creditor_id} must call accept to activate."
        }

    def _accept(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Accept a pending debt (creditor must call).

        Args: [debt_id]
        """
        if len(args) < 1:
            return {"success": False, "error": "accept requires [debt_id]"}

        debt_id: str = args[0]

        if debt_id not in self.debts:
            return {"success": False, "error": f"Debt {debt_id} not found"}

        debt = self.debts[debt_id]

        # Only creditor can accept
        if debt["creditor_id"] != invoker_id:
            return {"success": False, "error": "Only the creditor can accept a debt"}

        # Must be pending
        if debt["status"] != "pending":
            return {"success": False, "error": f"Debt is not pending (status: {debt['status']})"}

        # Activate the debt
        debt["status"] = "active"

        return {
            "success": True,
            "debt_id": debt_id,
            "debtor": debt["debtor_id"],
            "creditor": invoker_id,
            "principal": debt["principal"],
            "message": f"Debt {debt_id} is now active. Debtor owes {debt['principal']} scrip."
        }

    def _repay(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Repay debt (debtor pays creditor).

        Args: [debt_id, amount]
        """
        if len(args) < 2:
            return {"success": False, "error": "repay requires [debt_id, amount]"}

        debt_id: str = args[0]
        amount: Any = args[1]

        if not isinstance(amount, int) or amount <= 0:
            return {"success": False, "error": "Amount must be a positive integer"}

        if debt_id not in self.debts:
            return {"success": False, "error": f"Debt {debt_id} not found"}

        debt = self.debts[debt_id]

        # Only debtor can repay
        if debt["debtor_id"] != invoker_id:
            return {"success": False, "error": "Only the debtor can repay"}

        # Must be active
        if debt["status"] != "active":
            return {"success": False, "error": f"Debt is not active (status: {debt['status']})"}

        # Calculate current amount owed with interest
        ticks_elapsed = max(0, self.current_tick - debt["created_tick"])
        interest = int(debt["principal"] * debt["interest_rate"] * ticks_elapsed)
        current_owed = debt["principal"] + interest - debt["amount_paid"]

        # Cap payment at amount owed
        actual_payment = min(amount, current_owed)

        # Transfer scrip from debtor to creditor
        transfer_success = self.ledger.transfer_scrip(
            invoker_id,
            debt["creditor_id"],
            actual_payment
        )
        if not transfer_success:
            return {"success": False, "error": "Transfer failed: insufficient funds"}

        # Update debt record
        debt["amount_paid"] += actual_payment
        debt["amount_owed"] = current_owed - actual_payment

        # Check if fully paid
        if debt["amount_owed"] <= 0:
            debt["status"] = "paid"
            return {
                "success": True,
                "debt_id": debt_id,
                "amount_paid": actual_payment,
                "total_paid": debt["amount_paid"],
                "remaining": 0,
                "status": "paid",
                "message": f"Debt {debt_id} fully paid!"
            }

        return {
            "success": True,
            "debt_id": debt_id,
            "amount_paid": actual_payment,
            "total_paid": debt["amount_paid"],
            "remaining": debt["amount_owed"],
            "message": f"Paid {actual_payment} scrip. {debt['amount_owed']} remaining."
        }

    def _collect(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Collect overdue debt (creditor only, after due_tick).

        This attempts to collect. No magic enforcement - if debtor has no
        scrip, collection fails but debt is marked defaulted for reputation.

        Args: [debt_id]
        """
        if len(args) < 1:
            return {"success": False, "error": "collect requires [debt_id]"}

        debt_id: str = args[0]

        if debt_id not in self.debts:
            return {"success": False, "error": f"Debt {debt_id} not found"}

        debt = self.debts[debt_id]

        # Only creditor can collect
        if debt["creditor_id"] != invoker_id:
            return {"success": False, "error": "Only the creditor can collect"}

        # Must be active
        if debt["status"] != "active":
            return {"success": False, "error": f"Debt is not active (status: {debt['status']})"}

        # Must be past due
        if self.current_tick < debt["due_tick"]:
            return {
                "success": False,
                "error": f"Debt not yet due (due at tick {debt['due_tick']}, current tick {self.current_tick})"
            }

        # Calculate amount owed
        ticks_elapsed = max(0, self.current_tick - debt["created_tick"])
        interest = int(debt["principal"] * debt["interest_rate"] * ticks_elapsed)
        amount_owed = debt["principal"] + interest - debt["amount_paid"]

        # Try to collect
        debtor_balance = self.ledger.get_scrip(debt["debtor_id"])

        if debtor_balance >= amount_owed:
            # Full collection
            transfer_success = self.ledger.transfer_scrip(
                debt["debtor_id"],
                invoker_id,
                amount_owed
            )
            if transfer_success:
                debt["amount_paid"] += amount_owed
                debt["amount_owed"] = 0
                debt["status"] = "paid"
                return {
                    "success": True,
                    "debt_id": debt_id,
                    "collected": amount_owed,
                    "status": "paid",
                    "message": f"Collected {amount_owed} scrip. Debt fully paid."
                }

        elif debtor_balance > 0:
            # Partial collection
            transfer_success = self.ledger.transfer_scrip(
                debt["debtor_id"],
                invoker_id,
                debtor_balance
            )
            if transfer_success:
                debt["amount_paid"] += debtor_balance
                debt["amount_owed"] = amount_owed - debtor_balance
                return {
                    "success": True,
                    "debt_id": debt_id,
                    "collected": debtor_balance,
                    "remaining": debt["amount_owed"],
                    "status": "active",
                    "message": f"Partial collection: {debtor_balance} scrip. {debt['amount_owed']} still owed."
                }

        # Debtor has no scrip - mark as defaulted for reputation
        debt["status"] = "defaulted"
        return {
            "success": False,
            "debt_id": debt_id,
            "collected": 0,
            "remaining": amount_owed,
            "status": "defaulted",
            "error": f"Debtor {debt['debtor_id']} has no scrip. Debt marked as defaulted."
        }

    def _transfer_creditor(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Transfer creditor rights to another principal (sell the debt).

        Args: [debt_id, new_creditor_id]
        """
        if len(args) < 2:
            return {"success": False, "error": "transfer_creditor requires [debt_id, new_creditor_id]"}

        debt_id: str = args[0]
        new_creditor_id: str = args[1]

        if debt_id not in self.debts:
            return {"success": False, "error": f"Debt {debt_id} not found"}

        debt = self.debts[debt_id]

        # Only current creditor can transfer
        if debt["creditor_id"] != invoker_id:
            return {"success": False, "error": "Only the creditor can transfer creditor rights"}

        # Cannot be paid or pending
        if debt["status"] not in ("active", "defaulted"):
            return {"success": False, "error": f"Cannot transfer debt with status: {debt['status']}"}

        old_creditor = debt["creditor_id"]
        debt["creditor_id"] = new_creditor_id

        return {
            "success": True,
            "debt_id": debt_id,
            "old_creditor": old_creditor,
            "new_creditor": new_creditor_id,
            "message": f"Creditor rights transferred from {old_creditor} to {new_creditor_id}"
        }

    def _check(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """Check status of a debt.

        Args: [debt_id]
        """
        if len(args) < 1:
            return {"success": False, "error": "check requires [debt_id]"}

        debt_id: str = args[0]

        if debt_id not in self.debts:
            return {"success": False, "error": f"Debt {debt_id} not found"}

        debt = self.debts[debt_id]

        # Calculate current amount owed
        if debt["status"] == "active":
            ticks_elapsed = max(0, self.current_tick - debt["created_tick"])
            interest = int(debt["principal"] * debt["interest_rate"] * ticks_elapsed)
            current_owed = debt["principal"] + interest - debt["amount_paid"]
        else:
            current_owed = debt["amount_owed"]

        return {
            "success": True,
            "debt": {
                **debt,
                "current_owed": current_owed,
                "current_tick": self.current_tick
            }
        }

    def _list_debts(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List debts for a principal.

        Args: [principal_id]
        """
        if len(args) < 1:
            return {"success": False, "error": "list_debts requires [principal_id]"}

        principal_id: str = args[0]

        # Find debts where principal is debtor or creditor
        debts = [
            debt for debt in self.debts.values()
            if debt["debtor_id"] == principal_id or debt["creditor_id"] == principal_id
        ]

        return {
            "success": True,
            "principal_id": principal_id,
            "debts": debts,
            "count": len(debts)
        }

    def _list_all(self, args: list[Any], invoker_id: str) -> dict[str, Any]:
        """List all debts.

        Args: []
        """
        return {
            "success": True,
            "debts": list(self.debts.values()),
            "count": len(self.debts)
        }

    def get_interface(self) -> dict[str, Any]:
        """Get detailed interface schema for the debt contract (Plan #114)."""
        return {
            "description": self.description,
            "dataType": "service",
            "tools": [
                {
                    "name": "issue",
                    "description": "Issue a new debt. Invoker becomes the debtor. Creditor must call accept to activate.",
                    "cost": self.methods["issue"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "creditor_id": {
                                "type": "string",
                                "description": "ID of the creditor (who will be owed money)"
                            },
                            "principal": {
                                "type": "integer",
                                "description": "Amount to borrow",
                                "minimum": 1
                            },
                            "interest_rate": {
                                "type": "number",
                                "description": "Per-tick interest rate (e.g., 0.01 = 1% per tick)",
                                "minimum": 0
                            },
                            "due_tick": {
                                "type": "integer",
                                "description": "Tick when debt is due"
                            }
                        },
                        "required": ["creditor_id", "principal", "interest_rate", "due_tick"]
                    }
                },
                {
                    "name": "accept",
                    "description": "Accept a pending debt (creditor must call). Activates the debt.",
                    "cost": self.methods["accept"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "debt_id": {
                                "type": "string",
                                "description": "ID of the pending debt to accept"
                            }
                        },
                        "required": ["debt_id"]
                    }
                },
                {
                    "name": "repay",
                    "description": "Repay debt (debtor pays creditor). Transfers scrip automatically.",
                    "cost": self.methods["repay"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "debt_id": {
                                "type": "string",
                                "description": "ID of the debt to repay"
                            },
                            "amount": {
                                "type": "integer",
                                "description": "Amount to repay",
                                "minimum": 1
                            }
                        },
                        "required": ["debt_id", "amount"]
                    }
                },
                {
                    "name": "collect",
                    "description": "Collect overdue debt (creditor can seize assets if debt is past due)",
                    "cost": self.methods["collect"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "debt_id": {
                                "type": "string",
                                "description": "ID of the overdue debt to collect"
                            }
                        },
                        "required": ["debt_id"]
                    }
                },
                {
                    "name": "transfer_creditor",
                    "description": "Transfer creditor rights to another principal (sell your debt receivable)",
                    "cost": self.methods["transfer_creditor"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "debt_id": {
                                "type": "string",
                                "description": "ID of the debt to transfer"
                            },
                            "new_creditor_id": {
                                "type": "string",
                                "description": "ID of the new creditor"
                            }
                        },
                        "required": ["debt_id", "new_creditor_id"]
                    }
                },
                {
                    "name": "check",
                    "description": "Check status of a specific debt including current amount owed",
                    "cost": self.methods["check"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "debt_id": {
                                "type": "string",
                                "description": "ID of the debt to check"
                            }
                        },
                        "required": ["debt_id"]
                    }
                },
                {
                    "name": "list_debts",
                    "description": "List all debts for a specific principal (as debtor or creditor)",
                    "cost": self.methods["list_debts"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "principal_id": {
                                "type": "string",
                                "description": "ID of the principal to list debts for"
                            }
                        },
                        "required": ["principal_id"]
                    }
                },
                {
                    "name": "list_all",
                    "description": "List all debts in the system",
                    "cost": self.methods["list_all"].cost,
                    "inputSchema": {
                        "type": "object",
                        "properties": {}
                    }
                }
            ]
        }
