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
        "escrow_not_owner": "Escrow does not own {artifact_id}. See handbook_trading for the 2-step process: 1) genesis_ledger.transfer_ownership([artifact_id, '{escrow_id}']), 2) deposit.",
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
            allowed, reason = executor._check_permission(intent.principal_id, "read", artifact)
            if not allowed:
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
            # Pay read_price to owner (economic transfer -> SCRIP)
            if read_price > 0:
                w.ledger.deduct_scrip(intent.principal_id, read_price)
                w.ledger.credit_scrip(artifact.created_by, read_price)
            return ActionResult(
                success=True,
                message=f"Read artifact {intent.artifact_id}" + (f" (paid {read_price} scrip to {artifact.created_by})" if read_price > 0 else ""),
                data={"artifact": artifact.to_dict(), "read_price_paid": read_price}
            )
        # Check genesis artifacts (always public, free)
        elif intent.artifact_id in w.genesis_artifacts:
            genesis = w.genesis_artifacts[intent.artifact_id]
            return ActionResult(
                success=True,
                message=f"Read genesis artifact {intent.artifact_id}",
                data={"artifact": genesis.to_dict()}
            )
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
        # Protect genesis artifacts from modification
        if intent.artifact_id in w.genesis_artifacts:
            return ActionResult(
                success=False,
                message=f"Cannot modify system artifact {intent.artifact_id}",
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Check if artifact exists (for update permission check)
        existing = w.artifacts.get(intent.artifact_id)
        if existing:
            # Check write permission via contracts
            executor = get_executor()
            allowed, reason = executor._check_permission(intent.principal_id, "write", existing)
            if not allowed:
                return ActionResult(
                    success=False,
                    message=get_error_message("access_denied_write", artifact_id=intent.artifact_id),
                    error_code=ErrorCode.NOT_AUTHORIZED.value,
                    error_category=ErrorCategory.PERMISSION.value,
                    retriable=False,
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

        # Write the artifact
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
        )

        # Consume disk quota for the size delta
        if size_delta > 0:
            w.consume_quota(intent.principal_id, "disk", float(size_delta))
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
        })

        action = "Updated" if existing else "Created"
        return ActionResult(
            success=True,
            message=f"{action} artifact {intent.artifact_id} ({total_size} bytes)",
            data={
                "artifact_id": intent.artifact_id,
                "size_bytes": total_size,
                "was_update": existing is not None,
            },
        )

    def _execute_edit(self, intent: EditArtifactIntent) -> ActionResult:
        """Execute an edit_artifact action (Plan #131).

        Applies a partial edit to an existing artifact. Only the specified
        fields are updated; others are preserved.
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

        # Protect genesis artifacts from modification
        if intent.artifact_id in w.genesis_artifacts:
            return ActionResult(
                success=False,
                message=f"Cannot edit genesis artifact {intent.artifact_id}",
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
                error_details={"artifact_id": intent.artifact_id},
            )

        # Check write permission via contracts
        executor = get_executor()
        allowed, reason = executor._check_permission(intent.principal_id, "write", artifact)
        if not allowed:
            return ActionResult(
                success=False,
                message=get_error_message("access_denied_write", artifact_id=intent.artifact_id),
                error_code=ErrorCode.NOT_AUTHORIZED.value,
                error_category=ErrorCategory.PERMISSION.value,
                retriable=False,
            )

        # Calculate size changes for quota
        old_content_size = len(artifact.content.encode("utf-8"))
        old_code_size = len(artifact.code.encode("utf-8"))

        new_content = intent.content if intent.content is not None else artifact.content
        new_code = intent.code if intent.code is not None else artifact.code

        new_content_size = len(new_content.encode("utf-8"))
        new_code_size = len(new_code.encode("utf-8"))
        size_delta = (new_content_size + new_code_size) - (old_content_size + old_code_size)

        # Check disk quota if growing
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

        # Validate code if being updated and artifact is/becomes executable
        new_executable = intent.executable if intent.executable is not None else artifact.executable
        if new_executable and intent.code is not None:
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

        # Build update dict with only specified fields
        updates: dict[str, Any] = {}
        if intent.content is not None:
            updates["content"] = intent.content
        if intent.code is not None:
            updates["code"] = intent.code
        if intent.executable is not None:
            updates["executable"] = intent.executable
        if intent.price is not None:
            updates["price"] = intent.price
        if intent.interface is not None:
            updates["interface"] = intent.interface
        if intent.access_contract_id is not None:
            # Plan #235 Phase 0 (FM-7): Only creator can change access_contract_id
            if (intent.access_contract_id != artifact.access_contract_id
                    and intent.principal_id != artifact.created_by):
                return ActionResult(
                    success=False,
                    message=f"Only creator '{artifact.created_by}' can change access_contract_id",
                    error_code=ErrorCode.NOT_AUTHORIZED.value,
                    error_category=ErrorCategory.PERMISSION.value,
                    retriable=False,
                )
            updates["access_contract_id"] = intent.access_contract_id
        if intent.metadata is not None:
            # Merge metadata rather than replace
            new_metadata = dict(artifact.metadata or {})
            new_metadata.update(intent.metadata)
            updates["metadata"] = new_metadata

        # Apply updates
        w.artifacts.update(intent.artifact_id, updates)

        # Update disk quota
        if size_delta > 0:
            w.consume_quota(intent.principal_id, "disk", float(size_delta))

        # Log the edit
        w.logger.log("artifact_edited", {
            "event_number": w.event_number,
            "artifact_id": intent.artifact_id,
            "edited_by": intent.principal_id,
            "fields_updated": list(updates.keys()),
            "size_delta": size_delta,
        })

        return ActionResult(
            success=True,
            message=f"Edited artifact {intent.artifact_id} (updated: {', '.join(updates.keys())})",
            data={
                "artifact_id": intent.artifact_id,
                "fields_updated": list(updates.keys()),
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

            # Check invoke permission via contracts (ADR-0019: pass method/args in context)
            executor = get_executor()
            allowed, reason = executor._check_permission(
                intent.principal_id, "invoke", artifact, method=method_name, args=args
            )
            if not allowed:
                duration_ms = (time.perf_counter() - start_time) * 1000
                self._log_invoke_failure(
                    intent.principal_id, artifact_id, method_name,
                    duration_ms, "permission_denied",
                    reason
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

            # Regular artifact code execution path
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

        # Only the owner can access their config
        if artifact.created_by != intent.principal_id:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name,
                duration_ms, "not_authorized",
                "Only the config owner can access it"
            )
            return ActionResult(
                success=False,
                message=f"Permission denied: only {artifact.created_by} can access this config",
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
        allowed, reason = executor._check_permission(intent.principal_id, "delete", artifact)
        if not allowed:
            return ActionResult(
                success=False,
                message=f"Delete not permitted: {reason}",
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
        target_artifact = w.artifacts.get(artifact_id)
        target_is_genesis = artifact_id in w.genesis_artifacts
        if target_artifact is None and not target_is_genesis:
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
            type=agent_artifact.artifact_type,
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
            type=agent_artifact.artifact_type,
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
            type=agent_artifact.artifact_type,
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
            section = intent.section or "custom"
            current = modifications.get(section, "")
            if current:
                modifications[section] = f"{current}\n{intent.content}"
            else:
                modifications[section] = intent.content
            changes.append(f"appended to {section}")

        elif intent.operation == "prepend":
            # Prepend content to a section
            section = intent.section or "custom"
            current = modifications.get(section, "")
            if current:
                modifications[section] = f"{intent.content}\n{current}"
            else:
                modifications[section] = intent.content
            changes.append(f"prepended to {section}")

        elif intent.operation == "replace":
            # Replace a section entirely
            section = intent.section or "custom"
            modifications[section] = intent.content
            changes.append(f"replaced {section}")

        elif intent.operation == "remove":
            # Remove a section
            section = intent.section or "custom"
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
            type=agent_artifact.artifact_type,
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
        created_by = artifact.created_by
        resource_payer = intent.principal_id

        # Check if caller can afford the price
        if price > 0 and not w.ledger.can_afford_scrip(intent.principal_id, price):
            duration_ms = (time.perf_counter() - start_time) * 1000
            self._log_invoke_failure(
                intent.principal_id, artifact_id, method_name,
                duration_ms, "insufficient_scrip",
                f"Insufficient scrip for price: need {price}"
            )
            return ActionResult(
                success=False,
                message=f"Insufficient scrip for price: need {price}, have {w.ledger.get_scrip(intent.principal_id)}",
                error_code=ErrorCode.INSUFFICIENT_FUNDS.value,
                error_category=ErrorCategory.RESOURCE.value,
                retriable=True,
                error_details={"required": price, "available": w.ledger.get_scrip(intent.principal_id)},
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

            # Pay price to owner
            if price > 0 and created_by != intent.principal_id:
                w.ledger.deduct_scrip(intent.principal_id, price)
                w.ledger.credit_scrip(created_by, price)
                w.logger.log("scrip_earned", {
                    "event_number": w.event_number,
                    "recipient": created_by,
                    "amount": price,
                    "from": intent.principal_id,
                    "artifact_id": artifact_id,
                    "method": method_name,
                })
                w.logger.log("scrip_spent", {
                    "event_number": w.event_number,
                    "spender": intent.principal_id,
                    "amount": price,
                    "to": created_by,
                    "artifact_id": artifact_id,
                    "method": method_name,
                })

            self._log_invoke_success(
                intent.principal_id, artifact_id, method_name,
                duration_ms, type(exec_result.get("result")).__name__
            )

            # Build message with price info
            if price > 0 and created_by == intent.principal_id:
                price_msg = f" (self-invoke: no scrip transferred, you paid yourself)"
            elif price > 0:
                price_msg = f" (paid {price} scrip to {created_by})"
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
                    "owner": created_by
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
