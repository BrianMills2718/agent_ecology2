def run():
    """Alpha Prime BabyAGI Loop - Plans #273, #298.

    Each iteration:
    1. Read state with task queue
    2. Pop current task
    3. Call LLM to decide action + create new tasks
    4. Execute action
    5. Update state with results and new tasks
    """
    import json

    # Read current state (caller_id is injected by executor)
    state_raw = kernel_state.read_artifact("alpha_prime_state", caller_id)
    try:
        state = json.loads(state_raw) if isinstance(state_raw, str) else state_raw
    except (json.JSONDecodeError, TypeError):
        state = {"iteration": 0, "task_queue": [], "completed_tasks": [], "next_task_id": 1, "insights": {}, "objective": "Earn scrip", "model": "gemini/gemini-2.5-flash"}

    state["iteration"] = state.get("iteration", 0) + 1

    # Get model from state (configurable via initial_state.json)
    model = state.get("model", "gemini/gemini-2.5-flash")

    # Get current task (highest priority)
    task_queue = state.get("task_queue", [])
    if not task_queue:
        # No tasks - add initial task
        task_queue = [{"id": 1, "description": "Query available mint tasks", "priority": 10}]
        state["task_queue"] = task_queue
        state["next_task_id"] = 2

    # Sort by priority (descending) and pop first
    task_queue.sort(key=lambda t: t.get("priority", 5), reverse=True)
    current_task = task_queue[0]

    # Build context for LLM
    recent_completed = state.get("completed_tasks", [])[-5:]  # Last 5 results
    insights = state.get("insights", {})
    objective = state.get("objective", "Earn scrip by completing mint tasks")

    # Plan #275: Include mint tasks data in prompt so LLM can see available tasks
    available_tasks = state.get("last_mint_tasks_query", [])
    action_history = state.get("action_history", [])[-5:]  # Last 5 actions

    # Query scrip balance
    scrip_balance = "unknown"
    try:
        balance_result = kernel_state.query("balances", {"principal_id": caller_id}, caller_id=caller_id)
        if isinstance(balance_result, dict):
            scrip_balance = balance_result.get("scrip", balance_result.get("balance", "unknown"))
    except Exception:
        pass

    prompt = f"""You are Alpha Prime. Execute your current task and plan next steps.

OBJECTIVE: {objective}
STATUS: Iteration {state['iteration']} | Scrip: {scrip_balance} | Artifacts: {len(insights.get('artifacts_created', []))} | Tasks completed: {len(insights.get('completed_tasks', []))}

CURRENT TASK (id={current_task['id']}): {current_task['description']}

AVAILABLE MINT TASKS (from last query):
{json.dumps(available_tasks, indent=2) if available_tasks else "(Query mint_tasks first to see available tasks)"}

RECENT RESULTS:
{json.dumps(recent_completed, indent=2) if recent_completed else "(none yet)"}

RECENT ACTIONS:
{json.dumps(action_history, indent=2) if action_history else "(none yet)"}

INSIGHTS:
- Closed tasks (don't retry): {insights.get('closed_tasks', [])}
- Completed submissions: {insights.get('completed_tasks', [])}
- Artifacts created: {insights.get('artifacts_created', [])}

RESPOND WITH JSON:
{{
  "action": {{"action_type": "...", ...}},
  "task_result": "Brief description of what this action accomplishes",
  "new_tasks": [
    {{"description": "Follow-up task", "priority": 8}}
  ]
}}

ACTIONS:
- Query tasks: {{"action_type": "query_kernel", "query_type": "mint_tasks", "params": {{}}}}
- Query artifacts: {{"action_type": "query_kernel", "query_type": "artifacts", "params": {{"name_pattern": "..."}}}}
- Read artifact: {{"action_type": "read_artifact", "artifact_id": "..."}}
- Write artifact: {{"action_type": "write_artifact", "artifact_id": "alpha_prime_X", "artifact_type": "executable", "executable": true, "code": "def run(...):\\n    ..."}}
- Write artifact (with standing): {{"action_type": "write_artifact", "artifact_id": "my_service", "artifact_type": "executable", "executable": true, "has_standing": true, "code": "def run():\\n    ..."}}
- Invoke artifact: {{"action_type": "invoke_artifact", "artifact_id": "tool_id", "method": "run", "args": [...]}}
- Transfer scrip: {{"action_type": "transfer", "recipient_id": "...", "amount": 50, "memo": "payment for..."}}
- Submit to task: {{"action_type": "submit_to_task", "artifact_id": "alpha_prime_X", "task_id": "task_name"}}

CRITICAL: Use UNIQUE artifact IDs. submit_to_task is an action_type, not invoke_artifact."""

    # Call LLM
    llm_result = _syscall_llm(model, [
        {"role": "user", "content": prompt}
    ])

    if not llm_result.get("success"):
        # LLM call failed - log and return
        state["completed_tasks"].append({
            "id": current_task["id"],
            "description": current_task["description"],
            "result": f"LLM error: {llm_result.get('error', 'unknown')}"
        })
        kernel_actions.write_artifact(caller_id, "alpha_prime_state", json.dumps(state, indent=2))
        return {"success": False, "error": llm_result.get("error")}

    # Parse LLM response
    response_text = llm_result.get("content", "{}")

    # Extract JSON from response (handle markdown code blocks)
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    try:
        response = json.loads(response_text.strip())
    except json.JSONDecodeError:
        response = {"action": {"action_type": "noop"}, "task_result": "Failed to parse response", "new_tasks": []}

    action = response.get("action", {"action_type": "noop"})
    task_result = response.get("task_result", "Completed")
    new_tasks = response.get("new_tasks", [])

    # Remove current task from queue
    state["task_queue"] = [t for t in task_queue if t["id"] != current_task["id"]]

    # Plan #275: Track action in history for observability
    state.setdefault("action_history", []).append({
        "task_id": current_task["id"],
        "action_type": action.get("action_type", "noop"),
        "action": action,
    })
    # Keep only last 5 actions
    state["action_history"] = state["action_history"][-5:]

    # Add to completed tasks - note: actual action_result will be added after execution
    state["completed_tasks"].append({
        "id": current_task["id"],
        "description": current_task["description"],
        "result": task_result,
        "action_type": action.get("action_type", "noop"),
    })
    # Keep only last 10 completed tasks
    state["completed_tasks"] = state["completed_tasks"][-10:]

    # Add new tasks
    for new_task in new_tasks:
        if isinstance(new_task, dict) and "description" in new_task:
            state["task_queue"].append({
                "id": state.get("next_task_id", 1),
                "description": new_task["description"],
                "priority": new_task.get("priority", 5)
            })
            state["next_task_id"] = state.get("next_task_id", 1) + 1

    # Update insights based on action
    if action.get("action_type") == "write_artifact":
        artifact_id = action.get("artifact_id", "")
        if artifact_id and artifact_id not in state["insights"].get("artifacts_created", []):
            state["insights"].setdefault("artifacts_created", []).append(artifact_id)

    # Save state BEFORE executing action (so state is preserved even if action fails)
    kernel_actions.write_artifact(caller_id, "alpha_prime_state", json.dumps(state, indent=2))

    # Execute the action directly (Plan #273 fix: don't return for external execution)
    action_type = action.get("action_type", "noop")
    action_result = {"success": False, "error": "Unknown action"}

    if action_type == "noop":
        action_result = {"success": True, "result": "No action taken"}

    elif action_type == "query_kernel":
        query_type = action.get("query_type", "")
        params = action.get("params", {})
        try:
            # Plan #274: Pass caller_id for logging
            result = kernel_state.query(query_type, params, caller_id=caller_id)
            action_result = {"success": True, "result": result}
            # Plan #275: Store query results in state so LLM can see them
            if query_type == "mint_tasks":
                state["last_mint_tasks_query"] = result.get("tasks", [])
                kernel_actions.write_artifact(caller_id, "alpha_prime_state", json.dumps(state, indent=2))
        except Exception as e:
            action_result = {"success": False, "error": str(e)}

    elif action_type == "read_artifact":
        artifact_id = action.get("artifact_id", "")
        try:
            content = kernel_state.read_artifact(artifact_id, caller_id)
            action_result = {"success": True, "result": content}
        except Exception as e:
            action_result = {"success": False, "error": str(e)}

    elif action_type == "write_artifact":
        artifact_id = action.get("artifact_id", "")
        artifact_type = action.get("artifact_type", "text")
        content = action.get("content", "")
        code = action.get("code", "")
        executable = action.get("executable", False)
        has_standing = action.get("has_standing", False)
        try:
            result = kernel_actions.write_artifact(
                caller_id,
                artifact_id,
                content or code,
                artifact_type=artifact_type,
                executable=executable,
                code=code if executable else None,
                has_standing=has_standing,
            )
            action_result = {"success": True, "result": f"Created artifact {artifact_id}"}
            # Plan #275: Track artifact creation in insights
            if artifact_id not in state["insights"].get("artifacts_created", []):
                state["insights"].setdefault("artifacts_created", []).append(artifact_id)
                kernel_actions.write_artifact(caller_id, "alpha_prime_state", json.dumps(state, indent=2))
        except Exception as e:
            action_result = {"success": False, "error": str(e)}

    elif action_type == "invoke_artifact":
        artifact_id = action.get("artifact_id", "")
        args = action.get("args", [])
        try:
            result = invoke(artifact_id, *args)
            action_result = {"success": True, "result": result}
        except Exception as e:
            action_result = {"success": False, "error": str(e)}

    elif action_type == "transfer":
        recipient_id = action.get("recipient_id", "")
        amount = action.get("amount", 0)
        try:
            success = kernel_actions.transfer_scrip(caller_id, recipient_id, amount)
            if success:
                action_result = {"success": True, "result": f"Transferred {amount} to {recipient_id}"}
            else:
                action_result = {"success": False, "error": "Transfer failed (insufficient funds or invalid recipient)"}
        except Exception as e:
            action_result = {"success": False, "error": str(e)}

    elif action_type == "submit_to_task":
        artifact_id = action.get("artifact_id", "")
        task_id = action.get("task_id", "")
        try:
            result = kernel_actions.submit_to_task(caller_id, artifact_id, task_id)
            action_result = {"success": True, "result": result}
            # Update insights on successful submission
            if result.get("success"):
                state["insights"].setdefault("completed_tasks", []).append(task_id)
            elif "no longer open" in str(result.get("error", "")):
                # Task is closed - add to insights
                if task_id not in state["insights"].get("closed_tasks", []):
                    state["insights"].setdefault("closed_tasks", []).append(task_id)
            # Save updated insights
            kernel_actions.write_artifact(caller_id, "alpha_prime_state", json.dumps(state, indent=2))
        except Exception as e:
            action_result = {"success": False, "error": str(e)}

    return {"success": True, "action_result": action_result, "task_completed": current_task["description"]}
