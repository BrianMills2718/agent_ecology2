"""Action execution logic extracted from World.

Plan #181: Split large core files.

This module handles all action intent processing and execution,
delegating state access back to World.
"""

from __future__ import annotations

import json
import time
from typing import Any, TYPE_CHECKING

from .actions import (
    ActionIntent, ActionResult, ActionType,
    NoopIntent, ReadArtifactIntent, WriteArtifactIntent,
    EditArtifactIntent, InvokeArtifactIntent, DeleteArtifactIntent,
    QueryKernelIntent, SubscribeArtifactIntent, UnsubscribeArtifactIntent,
    TransferIntent, MintIntent, SubmitToMintIntent, SubmitToTaskIntent,  # Plan #254, #259, #269
    UpdateMetadataIntent,  # Plan #308
    ConfigureContextIntent, ModifySystemPromptIntent,
)
from .artifacts import Artifact
from .executor import (
    get_executor, validate_args_against_interface,
    convert_positional_to_named_args, convert_named_to_positional_args,
    parse_json_args,
)
from .errors import ErrorCode, ErrorCategory
from .invocation_registry import InvocationRecord

from ..config import get as config_get

if TYPE_CHECKING:
    from .world import World


def _artifact_has_handle_request(artifact: Artifact) -> bool:
    """Check if artifact uses handle_request interface (ADR-0024).

    Plan #234: Artifacts with handle_request() handle their own access
    control. The kernel skips permission checking and provides verified
    caller_id instead.

    Detection mirrors validate_code()'s "def run(" check.
    """
    if artifact.genesis_methods is not None:
        return False  # Genesis: existing dispatch in Phase 1
    if not artifact.code:
        return False
    return "def handle_request(" in artifact.code


def get_error_message(error_type: str, **kwargs: Any) -> str:
    """Get a configurable error message with placeholders filled in.

    Args:
        error_type: One of 'access_denied_read', 'access_denied_write',
                   'access_denied_invoke', 'method_not_found', 'escrow_not_owner'
        **kwargs: Placeholder values (artifact_id, method, methods, escrow_id)

    Returns:
        Formatted error message from config (or default if not configured).
    """
    # Defaults (in case config not loaded)
    defaults: dict[str, str] = {
        "access_denied_read": "Access denied: you are not allowed to read {artifact_id}. See handbook_actions for permissions.",
        "access_denied_write": "Access denied: you are not allowed to write to {artifact_id}. See handbook_actions for permissions.",
        "access_denied_invoke": "Access denied: you are not allowed to invoke {artifact_id}. See handbook_actions for permissions.",
        "method_not_found": "Method '{method}' not found on {artifact_id}. Available: {methods}. TIP: Call invoke_artifact('{artifact_id}', 'describe', []) to see method details before invoking.",
        "escrow_not_owner": "Escrow does not own {artifact_id}. See handbook_trading for the 2-step process: 1) edit_artifact to set owner to escrow, 2) deposit.",
    }

    # Get from config (or use default)
    template: str = config_get(f"agent.errors.{error_type}") or defaults.get(error_type, f"Error: {error_type}")

    # Fill in placeholders
    try:
        return template.format(**kwargs)
    except KeyError:
        # Missing placeholder - return template as-is
        return template


class ActionExecutor:
    """Executes action intents on behalf of World.

    Plan #181: Extracted from World to reduce file size.

    All action execution methods are collected here. The executor
    receives a World reference and delegates state access through it.
    """

    def __init__(self, world: "World") -> None:
        self.world = world

    def execute(self, intent: ActionIntent) -> ActionResult:
        """Execute an action intent. Returns the result.

        Actions are free. Real costs come from:
        - LLM tokens (thinking) - costs from compute budget
        - Disk quota (writing) - costs from disk allocation
        - Genesis method costs (configurable per-method)
        - Artifact prices (scrip paid to owner)
        """
        # Execute based on action type
        if isinstance(intent, NoopIntent):
            result = ActionResult(success=True, message="Noop executed")

        elif isinstance(intent, ReadArtifactIntent):
            result = self._execute_read(intent)

        elif isinstance(intent, WriteArtifactIntent):
            result = self._execute_write(intent)

        elif isinstance(intent, EditArtifactIntent):
            result = self._execute_edit(intent)

        elif isinstance(intent, InvokeArtifactIntent):
            result = self._execute_invoke(intent)

        elif isinstance(intent, DeleteArtifactIntent):
            result = self._execute_delete(intent)

        elif isinstance(intent, QueryKernelIntent):
            result = self._execute_query_kernel(intent)

        elif isinstance(intent, SubscribeArtifactIntent):
            result = self._execute_subscribe(intent)

        elif isinstance(intent, UnsubscribeArtifactIntent):
            result = self._execute_unsubscribe(intent)

        elif isinstance(intent, TransferIntent):
            result = self._execute_transfer(intent)

        elif isinstance(intent, MintIntent):
            result = self._execute_mint(intent)

        elif isinstance(intent, SubmitToMintIntent):
            result = self._execute_submit_to_mint(intent)

        elif isinstance(intent, SubmitToTaskIntent):
            result = self._execute_submit_to_task(intent)

        elif isinstance(intent, UpdateMetadataIntent):
            result = self._execute_update_metadata(intent)

        elif isinstance(intent, ConfigureContextIntent):
            result = self._execute_configure_context(intent)

        elif isinstance(intent, ModifySystemPromptIntent):
            result = self._execute_modify_system_prompt(intent)

        else:
            result = ActionResult(success=False, message="Unknown action type")

        self._log_action(intent, result)
        return result

    def _execute_read(self, intent: ReadArtifactIntent) -> ActionResult:
        """Execute a read_artifact action."""
        w = self.world
        # Check regular artifacts first
        artifact = w.artifacts.get(intent.artifact_id)
        if artifact:
            # Check read permission via contracts
            executor = get_executor()
            perm_result = executor._check_permission(intent.principal_id, "read", artifact)
            if not perm_result.allowed:
                return ActionResult(
                    success=False,
                    message=get_error_message("access_denied_read", artifact_id=intent.artifact_id),
                    error_code=ErrorCode.NOT_AUTHORIZED.value,
                    error_category=ErrorCategory.PERMISSION.value,
                    retriable=False,
                )
            # Check if can afford read_price (economic cost -> SCRIP)
            read_price: int = artifact.policy.get("read_price", 0)
            if read_price > 0 and not w.ledger.can_afford_scrip(intent.principal_id, read_price):
                return ActionResult(
                    success=False,
                    message=f"Cannot afford read price: {read_price} scrip (have {w.ledger.get_scrip(intent.principal_id)})",
                    error_code=ErrorCode.INSUFFICIENT_FUNDS.value,
                    error_category=ErrorCategory.RESOURCE.value,
                    retriable=True,
                    error_details={"required": read_price, "available": w.ledger.get_scrip(intent.principal_id)},
                )
            # Pay read_price to scrip_recipient (ADR-0028: contract decides who gets paid)
            recipient = perm_result.scrip_recipient
            if read_price > 0 and recipient:
                w.ledger.deduct_scrip(intent.principal_id, read_price)
                w.ledger.credit_scrip(recipient, read_price)
            return ActionResult(
                success=True,
                message=f"Read artifact {intent.artifact_id}" + (f" (paid {read_price} scrip to {recipient})" if read_price > 0 and recipient else ""),
                data={"artifact": artifact.to_dict(), "read_price_paid": read_price}
            )
        # Plan #254: Genesis artifacts removed - artifact not found
        else:
            # Plan #190: Suggest discovery via query_kernel
            # Plan #211: Clarify query_kernel is an ACTION type, not an artifact
            return ActionResult(
                success=False,
                message=(
                    f"Artifact '{intent.artifact_id}' not found. "
                    f"NOTE: query_kernel is NOT an artifact - do NOT invoke it. "
                    f"It is an action TYPE. Use: "
                    f'{{\"action_type\": \"query_kernel\", \"query_type\": \"artifacts\"}}'
                ),
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

    def _log_action(self, intent: ActionIntent, result: ActionResult) -> None:
        """Log an action execution and emit event for trigger matching."""
        w = self.world
        # Plan #80: Use truncated result to prevent log file bloat
        max_data_size = config_get("logging.truncation.result_data")
        if not isinstance(max_data_size, int):
            max_data_size = 1000  # Default if not configured
        w.logger.log("action", {
            "event_number": w.event_number,
            "intent": intent.to_dict(),
            "result": result.to_dict_truncated(max_data_size),
            "scrip_after": w.ledger.get_scrip(intent.principal_id)
        })

        # Plan #180: Emit event for trigger matching
        if result.success:
            event_type = f"{intent.action_type.value}_success"
            event = {
                "event_type": event_type,
                "event_number": w.event_number,
                "principal_id": intent.principal_id,
                "intent": intent.to_dict(),
                "data": result.data or {},
            }
            w._emit_event(event)

            # Refresh triggers if a trigger artifact was modified
            if isinstance(intent, (WriteArtifactIntent, EditArtifactIntent)):
                artifact = w.artifacts.get(intent.artifact_id)
                if artifact and artifact.type == "trigger":
                    w.refresh_triggers()

    def _execute_write(self, intent: WriteArtifactIntent) -> ActionResult:
        """Execute a write_artifact action.

        Handles:
        - Protection of genesis artifacts
        - Write permission checks (policy-based)
        - Disk quota enforcement (when rights_registry available)
        - Executable code validation
        - Artifact creation/update via ArtifactStore.write_artifact()
        """
        w = self.world
        # Plan #254: Genesis artifacts removed - kernel_ prefixed artifacts are protected in World.delete_artifact

        # Check if artifact exists (for update permission check)
        existing = w.artifacts.get(intent.artifact_id)
        if existing:
            # Plan #235 Phase 1: Block writes to kernel_protected artifacts
            if existing.kernel_protected:
                return ActionResult(
                    success=False,
                    message=f"Artifact '{intent.artifact_id}' is kernel_protected: "
                            "modification only via kernel primitives",
                    error_code=ErrorCode.NOT_AUTHORIZED.value,
                    error_category=ErrorCategory.PERMISSION.value,
                    retriable=False,
                    error_details={"artifact_id": intent.artifact_id},
                )
            # Check write permission via contracts
            executor = get_executor()
            perm_result = executor._check_permission(intent.principal_id, "write", existing)
            if not perm_result.allowed:
                return ActionResult(
                    success=False,
                    message=get_error_message("access_denied_write", artifact_id=intent.artifact_id),
                    error_code=ErrorCode.NOT_AUTHORIZED.value,
                    error_category=ErrorCategory.PERMISSION.value,
                    retriable=False,
                )

        # Require explicit access_contract_id for new artifacts (ADR-0019)
        if existing is None and not intent.access_contract_id:
            from src.world.constants import (
                KERNEL_CONTRACT_FREEWARE,
                KERNEL_CONTRACT_TRANSFERABLE_FREEWARE,
                KERNEL_CONTRACT_SELF_OWNED,
                KERNEL_CONTRACT_PRIVATE,
                KERNEL_CONTRACT_PUBLIC,
            )
            contract_list = [
                f"  {KERNEL_CONTRACT_FREEWARE} — anyone reads/invokes, only creator modifies",
                f"  {KERNEL_CONTRACT_TRANSFERABLE_FREEWARE} — like freeware, signals tradeable",
                f"  {KERNEL_CONTRACT_SELF_OWNED} — only self or principal can access",
                f"  {KERNEL_CONTRACT_PRIVATE} — only principal can access",
                f"  {KERNEL_CONTRACT_PUBLIC} — anyone can do anything",
            ]
            return ActionResult(
                success=False,
                message=(
                    f"New artifact '{intent.artifact_id}' requires access_contract_id. "
                    f"Available contracts:\n" + "\n".join(contract_list)
                ),
                error_code=ErrorCode.INVALID_ARGUMENT.value,
                error_category=ErrorCategory.VALIDATION.value,
                retriable=True,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Disk quota enforcement (Plan #95: Unified resource system)
        # Disk is an allocatable resource - agents have quota, we track usage
        content_size = len(intent.content.encode("utf-8"))
        code_size = len(intent.code.encode("utf-8")) if intent.code else 0
        total_size = content_size + code_size

        # Calculate size delta (if updating, we reclaim old space)
        size_delta = total_size
        if existing:
            old_content_size = len(existing.content.encode("utf-8"))
            old_code_size = len(existing.code.encode("utf-8"))
            size_delta = total_size - old_content_size - old_code_size

        # Check disk quota if size_delta > 0 (writing more than reclaiming)
        # Quota of 0 means unconfigured — skip enforcement (scarcity is opt-in)
        disk_quota = w.resource_manager.get_quota(intent.principal_id, "disk")
        if size_delta > 0 and disk_quota > 0:
            available = w.get_available_capacity(intent.principal_id, "disk")
            if available < size_delta:
                return ActionResult(
                    success=False,
                    message=f"Disk quota exceeded: need {size_delta} bytes, have {available} available",
                    error_code=ErrorCode.QUOTA_EXCEEDED.value,
                    error_category=ErrorCategory.RESOURCE.value,
                    retriable=True,
                    error_details={"required": size_delta, "available": available},
                )

        # Validate executable code if present
        if intent.executable and intent.code:
            executor = get_executor()
            valid, error = executor.validate_code(intent.code)
            if not valid:
                return ActionResult(
                    success=False,
                    message=f"Code validation failed: {error}",
                    error_code=ErrorCode.SYNTAX_ERROR.value,
                    error_category=ErrorCategory.VALIDATION.value,
                    retriable=True,
                    error_details={"validation_error": error},
                )

        # Plan #86: Validate interface schema if provided
        interface = intent.interface
        if interface is not None:
            from ..config import get_validated_config
            validation_mode = get_validated_config().executor.interface_validation
            if validation_mode in ("strict", "warn"):
                # Basic interface structure validation
                if not isinstance(interface, dict):
                    if validation_mode == "strict":
                        return ActionResult(
                            success=False,
                            message="Interface must be a dict",
                            error_code=ErrorCode.INVALID_ARGUMENT.value,
                            error_category=ErrorCategory.VALIDATION.value,
                            retriable=True,
                        )
                elif "tools" in interface:
                    # MCP-style interface - validate tools array
                    tools = interface.get("tools", [])
                    if not isinstance(tools, list):
                        if validation_mode == "strict":
                            return ActionResult(
                                success=False,
                                message="Interface 'tools' must be a list",
                                error_code=ErrorCode.INVALID_ARGUMENT.value,
                                error_category=ErrorCategory.VALIDATION.value,
                                retriable=True,
                            )

        # Write the artifact (Plan #254: include principal creation fields)
        artifact: Artifact = w.artifacts.write(
            artifact_id=intent.artifact_id,
            type=intent.artifact_type,
            content=intent.content,
            created_by=intent.principal_id,
            executable=intent.executable,
            price=intent.price,
            code=intent.code or "",
            policy=intent.policy,
            interface=interface,
            access_contract_id=intent.access_contract_id,
            metadata=intent.metadata,
            has_standing=intent.has_standing,
            has_loop=intent.has_loop,
        )

        # Plan #254: Auto-create principal if has_standing=True on NEW artifacts
        # This enables write_artifact to spawn principals (replacing genesis_ledger.spawn_principal)
        is_new_artifact = existing is None
        has_standing = intent.has_standing
        if is_new_artifact and has_standing:
            # Create principal in ledger (holds scrip and resources)
            if not w.ledger.principal_exists(intent.artifact_id):
                # Get starting resources from config if available
                from ..config import get
                starting_scrip = get("agents.starting_scrip") or 0
                w.ledger.create_principal(intent.artifact_id, starting_scrip)
                w.logger.log("principal_created", {
                    "principal_id": intent.artifact_id,
                    "created_by": intent.principal_id,
                    "has_standing": True,
                    "has_loop": intent.has_loop,
                    "starting_scrip": starting_scrip,
                })

        # Consume disk quota for the size delta (only when quota configured)
        if size_delta > 0 and disk_quota > 0:
            w.consume_quota(intent.principal_id, "disk", float(size_delta))
            w.logger.log_resource_allocated(
                principal_id=intent.principal_id,
                resource="disk",
                amount=float(size_delta),
                used_after=float(w.resource_manager.get_balance(intent.principal_id, "disk")),
                quota=float(w.resource_manager.get_quota(intent.principal_id, "disk")),
            )
        elif size_delta < 0:
            # Reclaim freed disk space (negative consume = return)
            # Note: This doesn't actually give back quota in current impl
            pass

        # Log the write
        w.logger.log("artifact_written", {
            "event_number": w.event_number,
            "artifact_id": intent.artifact_id,
            "created_by": intent.principal_id,
            "type": intent.artifact_type,
            "executable": intent.executable,
            "size_bytes": total_size,
            "was_update": existing is not None,
            "has_standing": has_standing,
            "has_loop": intent.has_loop,
        })

        action = "Updated" if existing else "Created"
        principal_note = " (principal created)" if is_new_artifact and has_standing else ""
        return ActionResult(
            success=True,
            message=f"{action} artifact {intent.artifact_id} ({total_size} bytes){principal_note}",
            data={
                "artifact_id": intent.artifact_id,
                "size_bytes": total_size,
                "was_update": existing is not None,
                "has_standing": has_standing,
                "has_loop": intent.has_loop,
                "principal_created": is_new_artifact and has_standing,
            },
        )

    def _execute_edit(self, intent: EditArtifactIntent) -> ActionResult:
        """Execute an edit_artifact action (Plan #131).

        Applies a surgical string replacement to an artifact's content using
        old_string/new_string (Claude Code-style editing). Delegates to
        ArtifactStore.edit_artifact() for the actual replacement logic.
        """
        w = self.world
        # Check if artifact exists
        artifact = w.artifacts.get(intent.artifact_id)
        if not artifact:
            return ActionResult(
                success=False,
                message=f"Artifact {intent.artifact_id} not found",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Plan #254: Genesis artifacts removed - kernel_ prefixed artifacts protected by kernel_protected flag

        # Plan #235 Phase 1: Block edits to kernel_protected artifacts
        if artifact.kernel_protected:
            return ActionResult(
                success=False,
                message=f"Artifact '{intent.artifact_id}' is kernel_protected: "
                        "modification only via kernel primitives",
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Check write permission via contracts
        executor = get_executor()
        perm_result = executor._check_permission(intent.principal_id, "write", artifact)
        if not perm_result.allowed:
            return ActionResult(
                success=False,
                message=get_error_message("access_denied_write", artifact_id=intent.artifact_id),
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
            )

        # Calculate size delta for quota check
        old_size = len(intent.old_string.encode("utf-8"))
        new_size = len(intent.new_string.encode("utf-8"))
        size_delta = new_size - old_size

        # Check disk quota if content is growing
        if size_delta > 0:
            available = w.get_available_capacity(intent.principal_id, "disk")
            if available < size_delta:
                return ActionResult(
                    success=False,
                    message=f"Disk quota exceeded: need {size_delta} bytes, have {available} available",
                    error_code=ErrorCode.QUOTA_EXCEEDED.value,
                    error_category=ErrorCategory.RESOURCE.value,
                    retriable=True,
                    error_details={"required": size_delta, "available": available},
                )

        # Delegate to ArtifactStore.edit_artifact for the string replacement
        result = w.artifacts.edit_artifact(
            intent.artifact_id, intent.old_string, intent.new_string
        )

        if not result["success"]:
            # Map edit_artifact error codes to ActionResult error codes
            error = (result.get("data") or {}).get("error", "unknown")
            error_code_map = {
                "not_found": ErrorCode.NOT_FOUND,
                "deleted": ErrorCode.NOT_FOUND,
                "not_found_in_content": ErrorCode.INVALID_ARGUMENT,
                "not_unique": ErrorCode.INVALID_ARGUMENT,
                "no_change": ErrorCode.INVALID_ARGUMENT,
            }
            mapped_code = error_code_map.get(error, ErrorCode.INTERNAL_ERROR)
            return ActionResult(
                success=False,
                message=result["message"],
                error_code=mapped_code.value,
                error_category=ErrorCategory.VALIDATION.value,
                retriable=False,
                error_details=result.get("data"),
            )

        # Update disk quota if content grew
        if size_delta > 0:
            w.consume_quota(intent.principal_id, "disk", float(size_delta))

        # Log the edit
        w.logger.log("artifact_edited", {
            "event_number": w.event_number,
            "artifact_id": intent.artifact_id,
            "edited_by": intent.principal_id,
            "size_delta": size_delta,
        })

        return ActionResult(
            success=True,
            message=f"Edited artifact {intent.artifact_id}",
            data={
                "artifact_id": intent.artifact_id,
                "size_delta": size_delta,
            },
        )

    def _execute_invoke(self, intent: InvokeArtifactIntent) -> ActionResult:
        """Execute an invoke_artifact action.

        Handles both:
        - Genesis artifacts (system proxies to ledger, mint, etc.)
        - Executable artifacts (agent-created code)

        Cost model:
        - Genesis method costs: Configurable compute cost per method
        - Artifact prices: Scrip paid to owner on successful invocation

        Invocation tracking (Gap #27):
        - Logs invoke_success/invoke_failure events
        - Records invocations in the registry for observability
        """
        w = self.world
        artifact_id = intent.artifact_id
        method_name = intent.method
        args = intent.args
        start_time = time.perf_counter()

        # Plan #211: Special case for query_kernel - common agent confusion
        if artifact_id == "query_kernel":
            duration_ms = (time.perf_counter() - start_time) * 1000
            error_msg = (
                "STOP: query_kernel is NOT an artifact you can invoke. "
                "It is an ACTION TYPE. Instead of invoke_artifact, use: "
                '{"action_type": "query_kernel", "query_type": "artifacts"}'
            )
            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name or "unknown",
                duration_ms, "not_found", error_msg
            )
            return ActionResult(
                success=False,
                message=error_msg,
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.VALIDATION.value,
                retriable=False,
                error_details={"artifact_id": artifact_id, "hint": "use action_type query_kernel"},
            )

        # Plan #15: Unified invoke path - all artifacts via artifact store
        artifact = w.artifacts.get(artifact_id)
        if artifact:
            if not artifact.executable:
                # Plan #160: Suggest alternative - use read_artifact for data/config artifacts
                duration_ms = (time.perf_counter() - start_time) * 1000
                helpful_msg = (
                    f"Artifact {artifact_id} is not executable (it's a data artifact). "
                    f"Use read_artifact with artifact_id='{artifact_id}' to read its content."
                )
                self._log_invoke_failure(
                    intent.principal_id, artifact_id, method_name,
                    duration_ms, "not_executable", helpful_msg
                )
                return ActionResult(
                    success=False,
                    message=helpful_msg,
                    error_code=ErrorCode.INVALID_TYPE.value,
                    error_category=ErrorCategory.VALIDATION.value,
                    retriable=False,
                    error_details={"artifact_id": artifact_id, "executable": False},
                )

            # Plan #234: Skip kernel permission check for handle_request artifacts.
            # ADR-0024: Artifact handles its own access control in handle_request().
            if not _artifact_has_handle_request(artifact):
                # Legacy path: kernel checks permission (ADR-0019)
                executor = get_executor()
                perm_result = executor._check_permission(
                    intent.principal_id, "invoke", artifact, method=method_name, args=args
                )
                if not perm_result.allowed:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    self._log_invoke_failure(
                        intent.principal_id, artifact_id, method_name,
                        duration_ms, "permission_denied",
                        perm_result.reason
                    )
                    return ActionResult(
                        success=False,
                        message=get_error_message("access_denied_invoke", artifact_id=artifact_id),
                        error_code=ErrorCode.NOT_AUTHORIZED.value,
                        error_category=ErrorCategory.PERMISSION.value,
                        retriable=False,
                    )

            # Plan #161: Auto-describe method
            if method_name == "describe":
                interface = artifact.interface or {}
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._log_invoke_success(
                    intent.principal_id, artifact_id, method_name, duration_ms, "dict"
                )
                return ActionResult(
                    success=True,
                    message=f"Interface for {artifact_id}",
                    data={
                        "artifact_id": artifact_id,
                        "type": artifact.type,
                        "created_by": artifact.created_by,
                        "executable": artifact.executable,
                        "description": interface.get("description", artifact.content),
                        "methods": [
                            {
                                "name": t.get("name"),
                                "description": t.get("description", ""),
                                "parameters": t.get("inputSchema", {}).get("properties", {}),
                            }
                            for t in interface.get("tools", [])
                        ],
                    },
                )

            # Plan #160: Config artifact methods (cognitive self-modification)
            if artifact.type == "config":
                return self._execute_config_invoke(intent, artifact, method_name, args, start_time)

            # Plan #86: Interface validation
            from ..config import get_validated_config
            validation_mode = get_validated_config().executor.interface_validation

            # Plan #160: Parse JSON strings in args BEFORE validation
            parsed_args: list[Any] | dict[str, Any] = intent.args or []
            if isinstance(parsed_args, list):
                parsed_args = parse_json_args(parsed_args)

            # Convert args list to named dict for validation
            args_dict: dict[str, Any] = {}
            if parsed_args:
                if isinstance(parsed_args, dict):
                    args_dict = parsed_args
                elif isinstance(parsed_args, list) and len(parsed_args) > 0:
                    if len(parsed_args) == 1 and isinstance(parsed_args[0], dict):
                        args_dict = parsed_args[0]
                    else:
                        args_dict = convert_positional_to_named_args(
                            interface=artifact.interface,
                            method_name=method_name,
                            args=parsed_args,
                        )

            validation_result = validate_args_against_interface(
                interface=artifact.interface,
                method_name=method_name,
                args=args_dict,
                validation_mode=validation_mode,
            )

            if not validation_result.proceed:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._log_invoke_failure(
                    intent.principal_id, artifact_id, method_name,
                    duration_ms, "interface_validation_failed",
                    validation_result.error_message
                )
                return ActionResult(
                    success=False,
                    message=f"Interface validation failed: {validation_result.error_message}",
                    error_code=ErrorCode.INVALID_ARGUMENT.value,
                    error_category=ErrorCategory.VALIDATION.value,
                    retriable=False,
                    error_details={"validation_error": validation_result.error_message},
                )

            # Plan #160: Use coerced args if available
            effective_args = args
            if validation_result.coerced_args is not None:
                effective_args = convert_named_to_positional_args(
                    interface=artifact.interface,
                    method_name=method_name,
                    args_dict=validation_result.coerced_args,
                )

            # Plan #15: Genesis method dispatch
            if artifact.genesis_methods is not None:
                return self._invoke_genesis_method(intent, artifact, method_name, effective_args, start_time)

            # Plan #234: handle_request dispatch (ADR-0024)
            if _artifact_has_handle_request(artifact):
                return self._invoke_user_artifact(
                    intent, artifact, method_name, effective_args, start_time,
                    entry_point="handle_request",
                )

            # Legacy: run() dispatch
            return self._invoke_user_artifact(intent, artifact, method_name, effective_args, start_time)

        # Artifact not found
        # Plan #211: Clarify query_kernel is an ACTION type, not an artifact
        duration_ms = (time.perf_counter() - start_time) * 1000
        helpful_msg = (
            f"Artifact '{artifact_id}' not found. "
            f"NOTE: query_kernel is NOT an artifact - do NOT invoke it. "
            f"It is an action TYPE. Use: "
            f'{{\"action_type\": \"query_kernel\", \"query_type\": \"artifacts\"}}'
        )
        self._log_invoke_failure(
            intent.principal_id, artifact_id, method_name,
            duration_ms, "not_found", helpful_msg
        )
        return ActionResult(
            success=False,
            message=helpful_msg,
            error_code=ErrorCode.NOT_FOUND.value,
            error_category=ErrorCategory.RESOURCE.value,
            retriable=False,
            error_details={"artifact_id": artifact_id},
        )

    def _execute_config_invoke(
        self,
        intent: InvokeArtifactIntent,
        artifact: Artifact,
        method_name: str,
        args: Any,
        start_time: float,
    ) -> ActionResult:
        """Execute config artifact methods (Plan #160: cognitive self-modification)."""
        w = self.world
        artifact_id = intent.artifact_id

        # Check permission via contract (ADR-0028: no hardcoded created_by checks)
        executor = get_executor()
        perm_result = executor._check_permission(intent.principal_id, "invoke", artifact)
        if not perm_result.allowed:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name,
                duration_ms, "not_authorized",
                perm_result.reason,
            )
            return ActionResult(
                success=False,
                message=f"Permission denied: {perm_result.reason}",
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
            )

        config_data: dict[str, Any] = json.loads(artifact.content) if artifact.content else {}

        if method_name == "get":
            key = args.get("key") if isinstance(args, dict) else (args[0] if args else None)
            if not key:
                return ActionResult(
                    success=False,
                    message="Missing required argument: key",
                    error_code=ErrorCode.INVALID_ARGUMENT.value,
                    error_category=ErrorCategory.VALIDATION.value,
                    retriable=False,
                )
            value = config_data.get(key)
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_success(
                intent.principal_id, artifact_id, method_name, duration_ms, type(value).__name__
            )
            return ActionResult(
                success=True,
                message=f"Config value for '{key}': {value}",
                data={"key": key, "value": value},
            )

        elif method_name == "set":
            key = args.get("key") if isinstance(args, dict) else (args[0] if len(args) > 0 else None)
            value = args.get("value") if isinstance(args, dict) else (args[1] if len(args) > 1 else None)
            if not key:
                return ActionResult(
                    success=False,
                    message="Missing required argument: key",
                    error_code=ErrorCode.INVALID_ARGUMENT.value,
                    error_category=ErrorCategory.VALIDATION.value,
                    retriable=False,
                )
            old_value = config_data.get(key)
            config_data[key] = value
            artifact.content = json.dumps(config_data)
            from datetime import datetime, timezone
            artifact.updated_at = datetime.now(timezone.utc).isoformat()
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_success(
                intent.principal_id, artifact_id, method_name, duration_ms, "bool"
            )
            return ActionResult(
                success=True,
                message=f"Config '{key}' updated: {old_value} -> {value}",
                data={"key": key, "old_value": old_value, "new_value": value},
            )

        elif method_name == "list_keys":
            keys = list(config_data.keys())
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_success(
                intent.principal_id, artifact_id, method_name, duration_ms, "list"
            )
            return ActionResult(
                success=True,
                message=f"Config keys: {keys}",
                data={"keys": keys, "config": config_data},
            )

        else:
            return ActionResult(
                success=False,
                message=f"Unknown config method: {method_name}. Available: get, set, list_keys, describe",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
            )

    def _execute_delete(self, intent: DeleteArtifactIntent) -> ActionResult:
        """Execute a delete_artifact action (Plan #57, #140).

        Soft deletes an artifact, freeing disk quota.
        Permission is checked via the artifact's access contract (Plan #140).
        Genesis artifacts cannot be deleted.
        """
        w = self.world
        # Check if genesis artifact (kernel-level protection, not policy)
        if intent.artifact_id.startswith("genesis_"):
            return ActionResult(
                success=False,
                message="Cannot delete genesis artifacts",
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Check if artifact exists
        artifact = w.artifacts.get(intent.artifact_id)
        if not artifact:
            return ActionResult(
                success=False,
                message=f"Artifact {intent.artifact_id} not found",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Check if already deleted
        if artifact.deleted:
            return ActionResult(
                success=False,
                message=f"Artifact {intent.artifact_id} is already deleted",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Plan #140: Check delete permission via contract
        executor = get_executor()
        perm_result = executor._check_permission(intent.principal_id, "delete", artifact)
        if not perm_result.allowed:
            return ActionResult(
                success=False,
                message=f"Delete not permitted: {perm_result.reason}",
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Calculate freed disk space before deletion
        freed_bytes = len(artifact.content.encode("utf-8")) + len(artifact.code.encode("utf-8"))

        # Perform soft delete
        from datetime import datetime, timezone
        artifact.deleted = True
        artifact.deleted_at = datetime.now(timezone.utc).isoformat()
        artifact.deleted_by = intent.principal_id
        w.artifacts._remove_from_index(artifact)

        # Log the deletion
        w.logger.log("artifact_deleted", {
            "event_number": w.event_number,
            "artifact_id": intent.artifact_id,
            "deleted_by": intent.principal_id,
            "deleted_at": artifact.deleted_at,
        })

        return ActionResult(
            success=True,
            message=f"Deleted artifact {intent.artifact_id}",
            data={"artifact_id": intent.artifact_id, "freed_bytes": freed_bytes},
        )

    def _execute_query_kernel(self, intent: QueryKernelIntent) -> ActionResult:
        """Execute a query_kernel action (Plan #184).

        Provides read-only access to kernel state including artifacts,
        principals, balances, resources, and more.
        """
        w = self.world
        query_result = w.kernel_query_handler.execute(
            intent.query_type,
            intent.params,
        )

        if query_result.get("success"):
            return ActionResult(
                success=True,
                message=f"Query '{intent.query_type}' succeeded",
                data=query_result,
            )
        else:
            return ActionResult(
                success=False,
                message=query_result.get("error", "Query failed"),
                error_code=query_result.get("error_code", "query_error"),
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
            )

    def _execute_subscribe(self, intent: SubscribeArtifactIntent) -> ActionResult:
        """Execute a subscribe_artifact action (Plan #191).

        Adds the artifact to the agent's subscribed_artifacts list.
        The artifact content will be auto-injected into the agent's prompt.
        """
        w = self.world
        agent_id = intent.principal_id
        artifact_id = intent.artifact_id

        # Check if agent artifact exists
        agent_artifact = w.artifacts.get(agent_id)
        if agent_artifact is None:
            return ActionResult(
                success=False,
                message=f"Agent artifact '{agent_id}' not found",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
            )

        # Check if target artifact exists
        # Plan #254: Genesis artifacts removed - only check regular artifacts
        target_artifact = w.artifacts.get(artifact_id)
        if target_artifact is None:
            return ActionResult(
                success=False,
                message=f"Artifact '{artifact_id}' not found. Cannot subscribe to non-existent artifact.",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
            )

        # Parse current agent config
        try:
            config = json.loads(agent_artifact.content) if agent_artifact.content else {}
        except (json.JSONDecodeError, TypeError):
            config = {}

        # Get or initialize subscribed_artifacts list
        subscribed: list[str] = config.get("subscribed_artifacts", [])
        if not isinstance(subscribed, list):
            subscribed = []

        # Check if already subscribed
        if artifact_id in subscribed:
            return ActionResult(
                success=True,
                message=f"Already subscribed to '{artifact_id}'",
                data={"subscribed_artifacts": subscribed},
            )

        # Check max subscriptions limit
        max_count: int = config_get("agent.subscribed_artifacts.max_count") or 5
        if len(subscribed) >= max_count:
            return ActionResult(
                success=False,
                message=f"Maximum subscriptions ({max_count}) reached. Unsubscribe from another artifact first.",
                error_code="subscription_limit_reached",
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
            )

        # Add subscription
        subscribed.append(artifact_id)
        config["subscribed_artifacts"] = subscribed

        # Update agent artifact content
        new_content = json.dumps(config, indent=2)
        w.artifacts.write(
            artifact_id=agent_id,
            type=agent_artifact.type,
            content=new_content,
            created_by=agent_artifact.created_by,
            executable=agent_artifact.executable,
            price=agent_artifact.price,
            code=agent_artifact.code,
            interface=agent_artifact.interface,
            access_contract_id=agent_artifact.access_contract_id,
            metadata=agent_artifact.metadata,
        )

        return ActionResult(
            success=True,
            message=f"Subscribed to '{artifact_id}'. It will be auto-injected into your prompt.",
            data={"subscribed_artifacts": subscribed},
        )

    def _execute_unsubscribe(self, intent: UnsubscribeArtifactIntent) -> ActionResult:
        """Execute an unsubscribe_artifact action (Plan #191).

        Removes the artifact from the agent's subscribed_artifacts list.
        """
        w = self.world
        agent_id = intent.principal_id
        artifact_id = intent.artifact_id

        # Check if agent artifact exists
        agent_artifact = w.artifacts.get(agent_id)
        if agent_artifact is None:
            return ActionResult(
                success=False,
                message=f"Agent artifact '{agent_id}' not found",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
            )

        # Parse current agent config
        try:
            config = json.loads(agent_artifact.content) if agent_artifact.content else {}
        except (json.JSONDecodeError, TypeError):
            config = {}

        # Get subscribed_artifacts list
        subscribed: list[str] = config.get("subscribed_artifacts", [])
        if not isinstance(subscribed, list):
            subscribed = []

        # Check if subscribed
        if artifact_id not in subscribed:
            return ActionResult(
                success=True,
                message=f"Not subscribed to '{artifact_id}'",
                data={"subscribed_artifacts": subscribed},
            )

        # Remove subscription
        subscribed.remove(artifact_id)
        config["subscribed_artifacts"] = subscribed

        # Update agent artifact content
        new_content = json.dumps(config, indent=2)
        w.artifacts.write(
            artifact_id=agent_id,
            type=agent_artifact.type,
            content=new_content,
            created_by=agent_artifact.created_by,
            executable=agent_artifact.executable,
            price=agent_artifact.price,
            code=agent_artifact.code,
            interface=agent_artifact.interface,
            access_contract_id=agent_artifact.access_contract_id,
            metadata=agent_artifact.metadata,
        )

        return ActionResult(
            success=True,
            message=f"Unsubscribed from '{artifact_id}'. It will no longer be auto-injected.",
            data={"subscribed_artifacts": subscribed},
        )

    def _execute_transfer(self, intent: TransferIntent) -> ActionResult:
        """Execute a transfer action (Plan #254).

        Moves scrip from the caller to a recipient principal.
        """
        w = self.world
        sender_id = intent.principal_id
        recipient_id = intent.recipient_id
        amount = intent.amount

        # Validate amount
        if amount <= 0:
            return ActionResult(
                success=False,
                message=f"Transfer amount must be positive, got {amount}",
                error_code=ErrorCode.INVALID_ARGUMENT.value,
                error_category=ErrorCategory.VALIDATION.value,
                retriable=True,
            )

        # Check sender exists and is a principal
        if not w.ledger.principal_exists(sender_id):
            return ActionResult(
                success=False,
                message=f"Sender '{sender_id}' is not a principal",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
            )

        # Check recipient exists and is a principal
        if not w.ledger.principal_exists(recipient_id):
            return ActionResult(
                success=False,
                message=f"Recipient '{recipient_id}' is not a principal",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
            )

        # Check sender has sufficient balance
        sender_balance = w.ledger.get_scrip(sender_id)
        if sender_balance < amount:
            return ActionResult(
                success=False,
                message=f"Insufficient scrip: have {sender_balance}, need {amount}",
                error_code=ErrorCode.INSUFFICIENT_FUNDS.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=True,
            )

        # Execute the transfer
        try:
            w.ledger.transfer_scrip(sender_id, recipient_id, amount)
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Transfer failed: {e}",
                error_code=ErrorCode.RUNTIME_ERROR.value,
                error_category=ErrorCategory.SYSTEM.value,
                retriable=False,
            )

        # Log the transfer
        w.logger.log("transfer", {
            "sender": sender_id,
            "recipient": recipient_id,
            "amount": amount,
            "memo": intent.memo,
            "sender_balance_after": w.ledger.get_scrip(sender_id),
            "recipient_balance_after": w.ledger.get_scrip(recipient_id),
        })

        return ActionResult(
            success=True,
            message=f"Transferred {amount} scrip to '{recipient_id}'",
            data={
                "amount": amount,
                "recipient": recipient_id,
                "sender_balance": w.ledger.get_scrip(sender_id),
            },
        )

    def _execute_mint(self, intent: MintIntent) -> ActionResult:
        """Execute a mint action (Plan #254).

        Creates new scrip. Privileged - requires 'can_mint' capability.
        """
        w = self.world
        minter_id = intent.principal_id
        recipient_id = intent.recipient_id
        amount = intent.amount
        reason = intent.reason

        # Check minter has can_mint capability
        minter_artifact = w.artifacts.get(minter_id)
        if minter_artifact is None:
            return ActionResult(
                success=False,
                message=f"Minter '{minter_id}' not found",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
            )

        # Check capability
        capabilities = minter_artifact.capabilities
        if 'can_mint' not in capabilities:
            return ActionResult(
                success=False,
                message=f"'{minter_id}' lacks 'can_mint' capability. Minting is privileged.",
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
            )

        # Validate amount
        if amount <= 0:
            return ActionResult(
                success=False,
                message=f"Mint amount must be positive, got {amount}",
                error_code=ErrorCode.INVALID_ARGUMENT.value,
                error_category=ErrorCategory.VALIDATION.value,
                retriable=True,
            )

        # Check recipient exists and is a principal
        if not w.ledger.principal_exists(recipient_id):
            return ActionResult(
                success=False,
                message=f"Recipient '{recipient_id}' is not a principal",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
            )

        # Execute the mint
        try:
            w.ledger.credit_scrip(recipient_id, amount)
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Mint failed: {e}",
                error_code=ErrorCode.RUNTIME_ERROR.value,
                error_category=ErrorCategory.SYSTEM.value,
                retriable=False,
            )

        # Log the mint
        w.logger.log("mint", {
            "minter": minter_id,
            "recipient": recipient_id,
            "amount": amount,
            "reason": reason,
            "recipient_balance_after": w.ledger.get_scrip(recipient_id),
        })

        return ActionResult(
            success=True,
            message=f"Minted {amount} scrip to '{recipient_id}' ({reason})",
            data={
                "amount": amount,
                "recipient": recipient_id,
                "reason": reason,
                "recipient_balance": w.ledger.get_scrip(recipient_id),
            },
        )

    def _execute_submit_to_mint(self, intent: SubmitToMintIntent) -> ActionResult:
        """Execute a submit_to_mint action (Plan #259).

        Submits an artifact to the mint auction. The bid amount is escrowed
        from the caller's balance.
        """
        w = self.world
        principal_id = intent.principal_id
        artifact_id = intent.artifact_id
        bid = intent.bid

        # Validate artifact exists
        artifact = w.artifacts.get(artifact_id)
        if artifact is None:
            return ActionResult(
                success=False,
                message=f"Artifact '{artifact_id}' not found",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
            )

        # Validate caller has write permission (ADR-0028: no hardcoded created_by checks)
        executor = get_executor()
        perm_result = executor._check_permission(principal_id, "write", artifact)
        if not perm_result.allowed:
            return ActionResult(
                success=False,
                message=f"Cannot submit '{artifact_id}' to mint: {perm_result.reason}",
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
            )

        # Validate bid amount
        if bid < 0:
            return ActionResult(
                success=False,
                message=f"Bid must be non-negative, got {bid}",
                error_code=ErrorCode.INVALID_ARGUMENT.value,
                error_category=ErrorCategory.VALIDATION.value,
                retriable=True,
            )

        # Submit to mint auction
        try:
            submission_id = w.submit_for_mint(principal_id, artifact_id, bid)
        except Exception as e:
            return ActionResult(
                success=False,
                message=f"Mint submission failed: {e}",
                error_code=ErrorCode.RUNTIME_ERROR.value,
                error_category=ErrorCategory.SYSTEM.value,
                retriable=True,
            )

        # Log the submission
        w.logger.log("mint_submission", {
            "principal": principal_id,
            "artifact_id": artifact_id,
            "bid": bid,
            "submission_id": submission_id,
        })

        return ActionResult(
            success=True,
            message=f"Submitted '{artifact_id}' to mint auction (bid: {bid}, submission: {submission_id})",
            data={
                "artifact_id": artifact_id,
                "bid": bid,
                "submission_id": submission_id,
            },
        )

    def _execute_submit_to_task(self, intent: SubmitToTaskIntent) -> ActionResult:
        """Execute a submit_to_task action (Plan #269).

        Submits an artifact as a solution to a mint task. The artifact is
        tested against public tests (results shown) and hidden tests
        (pass/fail only). If all tests pass, the reward is credited.
        """
        w = self.world
        principal_id = intent.principal_id
        artifact_id = intent.artifact_id
        task_id = intent.task_id

        # Check if task-based mint is enabled
        if not hasattr(w, "mint_task_manager") or w.mint_task_manager is None:
            return ActionResult(
                success=False,
                message="Task-based mint system is not enabled",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.SYSTEM.value,
                retriable=False,
            )

        # Submit solution through the manager
        result = w.mint_task_manager.submit_solution(principal_id, artifact_id, task_id)

        # Convert result to ActionResult
        return ActionResult(
            success=result.success,
            message=result.message,
            data=result.to_dict(),
            error_code=None if result.success else ErrorCode.RUNTIME_ERROR.value,
            error_category=None if result.success else ErrorCategory.VALIDATION.value,
            retriable=not result.success,
        )

    def _execute_update_metadata(self, intent: UpdateMetadataIntent) -> ActionResult:
        """Execute an update_metadata action (Plan #308).

        Updates a single metadata key on an artifact.
        """
        w = self.world

        # Check artifact exists
        artifact = w.artifacts.get(intent.artifact_id)
        if not artifact:
            return ActionResult(
                success=False,
                message=f"Artifact {intent.artifact_id} not found",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Check write permission via contract (ADR-0019)
        executor = get_executor()
        perm_result = executor._check_permission(intent.principal_id, "write", artifact)
        if not perm_result.allowed:
            return ActionResult(
                success=False,
                message=f"Metadata update not permitted: {perm_result.reason}",
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id, "key": intent.key},
            )

        # Update or delete the metadata key
        if intent.value is None:
            artifact.metadata.pop(intent.key, None)
        else:
            artifact.metadata[intent.key] = intent.value

        # Log the update
        w.logger.log("metadata_updated", {
            "event_number": w.event_number,
            "artifact_id": intent.artifact_id,
            "principal_id": intent.principal_id,
            "key": intent.key,
            "value": intent.value,
        })

        return ActionResult(
            success=True,
            message=f"Updated metadata key '{intent.key}' on {intent.artifact_id}",
            data={"artifact_id": intent.artifact_id, "key": intent.key},
        )

    def _execute_configure_context(self, intent: ConfigureContextIntent) -> ActionResult:
        """Execute a configure_context action (Plan #192, #193).

        Updates the agent's context_sections configuration to enable/disable
        specific prompt sections, and optionally sets section priorities.
        """
        w = self.world
        agent_id = intent.principal_id
        sections = intent.sections
        priorities = intent.priorities

        # Validate sections
        valid_sections = {
            "working_memory", "rag_memories", "action_history",
            "failure_history", "recent_events", "resource_metrics",
            "mint_submissions", "quota_info", "metacognitive",
            "subscribed_artifacts",
        }
        invalid_sections = set(sections.keys()) - valid_sections
        if invalid_sections:
            return ActionResult(
                success=False,
                message=f"Unknown sections: {', '.join(invalid_sections)}. Valid sections: {', '.join(sorted(valid_sections))}",
                error_code=ErrorCode.INVALID_ARGUMENT.value,
                error_category=ErrorCategory.VALIDATION.value,
                retriable=True,
            )

        # Plan #193: Validate priorities if provided
        if priorities is not None:
            invalid_priority_sections = set(priorities.keys()) - valid_sections
            if invalid_priority_sections:
                return ActionResult(
                    success=False,
                    message=f"Unknown sections in priorities: {', '.join(invalid_priority_sections)}. Valid sections: {', '.join(sorted(valid_sections))}",
                    error_code=ErrorCode.INVALID_ARGUMENT.value,
                    error_category=ErrorCategory.VALIDATION.value,
                    retriable=True,
                )

        # Check if agent artifact exists
        agent_artifact = w.artifacts.get(agent_id)
        if agent_artifact is None:
            return ActionResult(
                success=False,
                message=f"Agent artifact '{agent_id}' not found",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
            )

        # Parse current agent config
        try:
            config = json.loads(agent_artifact.content) if agent_artifact.content else {}
        except (json.JSONDecodeError, TypeError):
            config = {}

        # Get or initialize context_sections
        current_sections: dict[str, bool] = config.get("context_sections", {})
        if not isinstance(current_sections, dict):
            current_sections = {}

        # Merge new section settings
        for section, enabled in sections.items():
            if isinstance(enabled, bool):
                current_sections[section] = enabled

        config["context_sections"] = current_sections

        # Plan #193: Get or initialize context_section_priorities
        current_priorities: dict[str, int] = config.get("context_section_priorities", {})
        if not isinstance(current_priorities, dict):
            current_priorities = {}

        # Merge new priority settings
        if priorities is not None:
            for section, priority in priorities.items():
                if isinstance(priority, int):
                    current_priorities[section] = priority

            config["context_section_priorities"] = current_priorities

        # Update agent artifact content
        new_content = json.dumps(config, indent=2)
        w.artifacts.write(
            artifact_id=agent_id,
            type=agent_artifact.type,
            content=new_content,
            created_by=agent_artifact.created_by,
            executable=agent_artifact.executable,
            price=agent_artifact.price,
            code=agent_artifact.code,
            interface=agent_artifact.interface,
            access_contract_id=agent_artifact.access_contract_id,
            metadata=agent_artifact.metadata,
        )

        # Build response message
        changes: list[str] = []
        for section, enabled in sections.items():
            changes.append(f"{section}={'on' if enabled else 'off'}")
        if priorities:
            for section, priority in priorities.items():
                changes.append(f"{section} priority={priority}")

        return ActionResult(
            success=True,
            message=f"Context configuration updated: {', '.join(changes)}",
            data={
                "context_sections": current_sections,
                "context_section_priorities": current_priorities,
            },
        )

    def _execute_modify_system_prompt(self, intent: ModifySystemPromptIntent) -> ActionResult:
        """Execute a modify_system_prompt action (Plan #194).

        Updates the agent's custom system prompt modifications.
        """
        w = self.world
        agent_id = intent.principal_id

        # Check if agent artifact exists
        agent_artifact = w.artifacts.get(agent_id)
        if agent_artifact is None:
            return ActionResult(
                success=False,
                message=f"Agent artifact '{agent_id}' not found",
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
            )

        # Parse current agent config
        try:
            config = json.loads(agent_artifact.content) if agent_artifact.content else {}
        except (json.JSONDecodeError, TypeError):
            config = {}

        # Get or initialize system_prompt_modifications
        modifications: dict[str, Any] = config.get("system_prompt_modifications", {})
        if not isinstance(modifications, dict):
            modifications = {}

        # Track what changed
        changes: list[str] = []

        # Handle operation
        if intent.operation == "append":
            # Append content to a section
            section = intent.section_marker or "custom"
            current = modifications.get(section, "")
            if current:
                modifications[section] = f"{current}\n{intent.content}"
            else:
                modifications[section] = intent.content
            changes.append(f"appended to {section}")

        elif intent.operation == "prepend":
            # Prepend content to a section
            section = intent.section_marker or "custom"
            current = modifications.get(section, "")
            if current:
                modifications[section] = f"{intent.content}\n{current}"
            else:
                modifications[section] = intent.content
            changes.append(f"prepended to {section}")

        elif intent.operation == "replace":
            # Replace a section entirely
            section = intent.section_marker or "custom"
            modifications[section] = intent.content
            changes.append(f"replaced {section}")

        elif intent.operation == "remove":
            # Remove a section
            section = intent.section_marker or "custom"
            if section in modifications:
                del modifications[section]
                changes.append(f"removed {section}")
            else:
                return ActionResult(
                    success=False,
                    message=f"Section '{section}' not found in modifications",
                    error_code=ErrorCode.NOT_FOUND.value,
                    error_category=ErrorCategory.RESOURCE.value,
                    retriable=False,
                )

        elif intent.operation == "clear":
            # Clear all modifications
            modifications = {}
            changes.append("cleared all modifications")

        else:
            return ActionResult(
                success=False,
                message=f"Unknown operation: {intent.operation}. Valid: append, prepend, replace, remove, clear",
                error_code=ErrorCode.INVALID_ARGUMENT.value,
                error_category=ErrorCategory.VALIDATION.value,
                retriable=True,
            )

        config["system_prompt_modifications"] = modifications

        # Check size limits
        total_size = sum(len(str(v)) for v in modifications.values())
        max_size: int = config_get("agent.system_prompt.max_modification_size") or 4000
        if total_size > max_size:
            return ActionResult(
                success=False,
                message=f"System prompt modifications too large: {total_size} bytes (max {max_size})",
                error_code=ErrorCode.QUOTA_EXCEEDED.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=True,
                error_details={"current_size": total_size, "max_size": max_size},
            )

        # Update agent artifact content
        new_content = json.dumps(config, indent=2)
        w.artifacts.write(
            artifact_id=agent_id,
            type=agent_artifact.type,
            content=new_content,
            created_by=agent_artifact.created_by,
            executable=agent_artifact.executable,
            price=agent_artifact.price,
            code=agent_artifact.code,
            interface=agent_artifact.interface,
            access_contract_id=agent_artifact.access_contract_id,
            metadata=agent_artifact.metadata,
        )

        return ActionResult(
            success=True,
            message=f"System prompt updated: {', '.join(changes)}",
            data={
                "system_prompt_modifications": modifications,
                "total_size": total_size,
            },
        )

    def _log_invoke_success(
        self,
        invoker_id: str,
        artifact_id: str,
        method: str,
        duration_ms: float,
        result_type: str,
    ) -> None:
        """Log a successful invocation and record in registry."""
        w = self.world
        w.logger.log("invoke_success", {
            "event_number": w.event_number,
            "invoker_id": invoker_id,
            "artifact_id": artifact_id,
            "method": method,
            "duration_ms": duration_ms,
            "result_type": result_type,
        })
        w.invocation_registry.record_invocation(InvocationRecord(
            event_number=w.event_number,
            invoker_id=invoker_id,
            artifact_id=artifact_id,
            method=method,
            success=True,
            duration_ms=duration_ms,
        ))

    def _log_invoke_failure(
        self,
        invoker_id: str,
        artifact_id: str,
        method: str,
        duration_ms: float,
        error_type: str,
        error_message: str,
    ) -> None:
        """Log a failed invocation and record in registry."""
        w = self.world
        w.logger.log("invoke_failure", {
            "event_number": w.event_number,
            "invoker_id": invoker_id,
            "artifact_id": artifact_id,
            "method": method,
            "duration_ms": duration_ms,
            "error_type": error_type,
            "error_message": error_message,
        })
        w.invocation_registry.record_invocation(InvocationRecord(
            event_number=w.event_number,
            invoker_id=invoker_id,
            artifact_id=artifact_id,
            method=method,
            success=False,
            duration_ms=duration_ms,
            error_type=error_type,
        ))

    def _invoke_genesis_method(
        self,
        intent: InvokeArtifactIntent,
        artifact: Artifact,
        method_name: str,
        args: Any,
        start_time: float,
    ) -> ActionResult:
        """Execute a genesis artifact method.

        Plan #125: Extracted from _execute_invoke() for clarity.

        Handles:
        - Method lookup in genesis_methods
        - Compute affordability check
        - Compute cost deduction
        - Method execution with error handling
        """
        w = self.world
        artifact_id = intent.artifact_id

        # genesis_methods is guaranteed non-None here (caller checks)
        assert artifact.genesis_methods is not None
        method = artifact.genesis_methods.get(method_name)
        if not method:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name,
                duration_ms, "method_not_found",
                f"Method {method_name} not found"
            )
            return ActionResult(
                success=False,
                message=get_error_message(
                    "method_not_found",
                    method=method_name,
                    artifact_id=artifact_id,
                    methods=list(artifact.genesis_methods.keys())
                ),
                error_code=ErrorCode.NOT_FOUND.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=False,
                error_details={"method": method_name, "artifact_id": artifact_id},
            )

        # Genesis method costs are in scrip (not LLM tokens)
        if method.cost > 0 and not w.ledger.can_afford_scrip(intent.principal_id, method.cost):
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name,
                duration_ms, "insufficient_scrip",
                f"Cannot afford method cost: {method.cost}"
            )
            return ActionResult(
                success=False,
                message=f"Cannot afford method cost: {method.cost} scrip (have {w.ledger.get_scrip(intent.principal_id)})",
                error_code=ErrorCode.INSUFFICIENT_FUNDS.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=True,
                error_details={"required": method.cost, "available": w.ledger.get_scrip(intent.principal_id)},
            )

        # Deduct scrip cost FIRST
        resources_consumed: dict[str, float] = {}
        if method.cost > 0:
            w.ledger.deduct_scrip(intent.principal_id, method.cost)
            resources_consumed["scrip"] = float(method.cost)

        # Execute the genesis method
        try:
            result_data: dict[str, Any] = method.handler(args, intent.principal_id)
            duration_ms = (time.perf_counter() - start_time) * 1000

            if result_data.get("success"):
                self._log_invoke_success(
                    intent.principal_id, artifact_id, method_name,
                    duration_ms, type(result_data.get("result")).__name__
                )
                # Plan #160: Show brief result preview
                result_value = result_data.get("result")
                result_preview = ""
                if result_value is not None:
                    result_str = str(result_value)[:100]
                    if len(str(result_value)) > 100:
                        result_str += "..."
                    result_preview = f". Result: {result_str}"
                return ActionResult(
                    success=True,
                    message=f"Invoked {artifact_id}.{method_name}{result_preview}",
                    data=result_data,
                    resources_consumed=resources_consumed if resources_consumed else None,
                    charged_to=intent.principal_id,
                )
            else:
                error_code = result_data.get("code", ErrorCode.RUNTIME_ERROR.value)
                error_category = result_data.get("category", ErrorCategory.EXECUTION.value)
                retriable = result_data.get("retriable", False)
                self._log_invoke_failure(
                    intent.principal_id, artifact_id, method_name,
                    duration_ms, "method_failed",
                    result_data.get("error", "Method failed")
                )
                return ActionResult(
                    success=False,
                    message=result_data.get("error", "Method failed"),
                    resources_consumed=resources_consumed if resources_consumed else None,
                    charged_to=intent.principal_id,
                    error_code=error_code,
                    error_category=error_category,
                    retriable=retriable,
                    error_details=result_data.get("details"),
                )
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name,
                duration_ms, "exception",
                str(e)
            )
            return ActionResult(
                success=False,
                message=f"Method execution error: {str(e)}",
                resources_consumed=resources_consumed if resources_consumed else None,
                charged_to=intent.principal_id,
                error_code=ErrorCode.RUNTIME_ERROR.value,
                error_category=ErrorCategory.EXECUTION.value,
                retriable=False,
                error_details={"exception": str(e)},
            )

    def _invoke_user_artifact(
        self,
        intent: InvokeArtifactIntent,
        artifact: Artifact,
        method_name: str,
        args: Any,
        start_time: float,
        entry_point: str = "run",
    ) -> ActionResult:
        """Execute a user-defined artifact method.

        Plan #125: Extracted from _execute_invoke() for clarity.

        Handles:
        - Scrip price affordability check
        - Code execution via executor
        - Resource consumption tracking
        - Price payment to owner
        """
        w = self.world
        artifact_id = intent.artifact_id
        price = artifact.price
        # Plan #311: Payment recipient from artifact state, not metadata or created_by
        recipient = (artifact.state or {}).get("writer") or (artifact.state or {}).get("principal")

        # Plan #236: Resolve payer via charge_to delegation
        # Atomicity note (FM-1): Settlement is safe because execution is
        # single-threaded. If concurrency is added, wrap check→debit→record
        # in a lock.
        from .delegation import DelegationManager

        charge_to = artifact.metadata.get("charge_to", "caller")
        if charge_to == "caller":
            resource_payer = intent.principal_id
        else:
            resource_payer = DelegationManager.resolve_payer(
                charge_to, intent.principal_id, artifact
            )
            if resource_payer != intent.principal_id:
                authorized, reason = w.delegation_manager.authorize_charge(
                    charger_id=intent.principal_id,
                    payer_id=resource_payer,
                    amount=float(price),
                )
                if not authorized:
                    duration_ms = (time.perf_counter() - start_time) * 1000
                    self._log_invoke_failure(
                        intent.principal_id, artifact_id, method_name,
                        duration_ms, "delegation_denied",
                        f"Charge delegation denied: {reason}"
                    )
                    return ActionResult(
                        success=False,
                        message=f"Charge delegation denied: {reason}",
                        error_code=ErrorCode.NOT_AUTHORIZED.value,
                        error_category=ErrorCategory.PERMISSION.value,
                        retriable=False,
                        error_details={
                            "charge_to": charge_to,
                            "payer": resource_payer,
                            "charger": intent.principal_id,
                            "reason": reason,
                        },
                    )

        # Check if payer can afford the price
        if price > 0 and not w.ledger.can_afford_scrip(resource_payer, price):
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name,
                duration_ms, "insufficient_scrip",
                f"Insufficient scrip for price: need {price}"
            )
            return ActionResult(
                success=False,
                message=f"Insufficient scrip for price: need {price}, have {w.ledger.get_scrip(resource_payer)}",
                error_code=ErrorCode.INSUFFICIENT_FUNDS.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=True,
                error_details={"required": price, "available": w.ledger.get_scrip(resource_payer)},
            )

        # Execute the code
        executor = get_executor()
        exec_result = executor.execute_with_invoke(
            code=artifact.code,
            args=args,
            caller_id=intent.principal_id,
            artifact_id=artifact_id,
            ledger=w.ledger,
            artifact_store=w.artifacts,
            world=w,
            entry_point=entry_point,
            method_name=method_name if entry_point == "handle_request" else None,
        )

        # Extract resource consumption
        resources_consumed = exec_result.get("resources_consumed", {})
        duration_ms = exec_result.get("execution_time_ms", (time.perf_counter() - start_time) * 1000)

        rate_limited_resources = {"cpu_seconds"}

        if exec_result.get("success"):
            # Deduct physical resources from caller
            for resource, amount in resources_consumed.items():
                if resource in rate_limited_resources:
                    w.ledger.consume_resource(resource_payer, resource, amount)
                elif not w.ledger.can_spend_resource(resource_payer, resource, amount):
                    self._log_invoke_failure(
                        intent.principal_id, artifact_id, method_name,
                        duration_ms, "insufficient_resource",
                        f"Insufficient {resource}: need {amount}"
                    )
                    return ActionResult(
                        success=False,
                        message=f"Insufficient {resource}: need {amount}",
                        resources_consumed=resources_consumed,
                        charged_to=resource_payer,
                        error_code=ErrorCode.INSUFFICIENT_FUNDS.value,
                        error_category=ErrorCategory.RESOURCE.value,
                        retriable=True,
                        error_details={"resource": resource, "required": amount},
                    )
                else:
                    w.ledger.spend_resource(resource_payer, resource, amount)

            # Pay price to recipient (ADR-0028: contract decides who gets paid)
            if price > 0 and recipient and recipient != resource_payer:
                w.ledger.deduct_scrip(resource_payer, price)
                w.ledger.credit_scrip(recipient, price)
                w.logger.log("scrip_earned", {
                    "event_number": w.event_number,
                    "recipient": recipient,
                    "amount": price,
                    "from": resource_payer,
                    "artifact_id": artifact_id,
                    "method": method_name,
                })
                w.logger.log("scrip_spent", {
                    "event_number": w.event_number,
                    "spender": resource_payer,
                    "amount": price,
                    "to": recipient,
                    "artifact_id": artifact_id,
                    "method": method_name,
                })

                # Plan #236: Record charge for rate window tracking
                if resource_payer != intent.principal_id:
                    w.delegation_manager.record_charge(
                        resource_payer, intent.principal_id, float(price)
                    )

            self._log_invoke_success(
                intent.principal_id, artifact_id, method_name,
                duration_ms, type(exec_result.get("result")).__name__
            )

            # Build message with price info
            if price > 0 and recipient == resource_payer:
                price_msg = " (self-invoke: no scrip transferred, you paid yourself)"
            elif price > 0 and resource_payer != intent.principal_id:
                price_msg = f" (delegated: {resource_payer} paid {price} scrip to {recipient})"
            elif price > 0:
                price_msg = f" (paid {price} scrip to {recipient})"
            else:
                price_msg = ""

            # Plan #160: Show brief result preview
            result_value = exec_result.get("result")
            result_preview = ""
            if result_value is not None:
                result_str = str(result_value)[:100]
                if len(str(result_value)) > 100:
                    result_str += "..."
                result_preview = f". Result: {result_str}"

            return ActionResult(
                success=True,
                message=f"Invoked {artifact_id}{price_msg}{result_preview}",
                data={
                    "result": exec_result.get("result"),
                    "price_paid": price,
                    "recipient": recipient
                },
                resources_consumed=resources_consumed if resources_consumed else None,
                charged_to=resource_payer,
            )
        else:
            # Execution failed - still charge resources
            for resource, amount in resources_consumed.items():
                if resource in rate_limited_resources:
                    w.ledger.consume_resource(resource_payer, resource, amount)
                elif w.ledger.can_spend_resource(resource_payer, resource, amount):
                    w.ledger.spend_resource(resource_payer, resource, amount)

            error_msg = exec_result.get("error", "Unknown error")
            error_type = "execution"
            error_code = ErrorCode.RUNTIME_ERROR.value
            error_category = ErrorCategory.EXECUTION.value
            retriable = False
            if "timed out" in error_msg.lower():
                error_type = "timeout"
                error_code = ErrorCode.TIMEOUT.value
                retriable = True
            elif "syntax" in error_msg.lower():
                error_type = "validation"
                error_code = ErrorCode.SYNTAX_ERROR.value
                error_category = ErrorCategory.VALIDATION.value

            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name,
                duration_ms, error_type, error_msg
            )
            return ActionResult(
                success=False,
                message=f"Execution failed: {error_msg}",
                data={"error": error_msg},
                resources_consumed=resources_consumed if resources_consumed else None,
                charged_to=resource_payer,
                error_code=error_code,
                error_category=error_category,
                retriable=retriable,
                error_details={"artifact_id": artifact_id, "error": error_msg},
            )
