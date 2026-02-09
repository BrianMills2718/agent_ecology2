def run():
    """Discourse Analyst Research Loop - Plan #299.

    Each iteration:
    1. Read state (current research phase)
    2. Read strategy (system prompt)
    3. Build context-aware prompt
    4. Call LLM for action decision
    5. Execute action directly
    6. Update state with results
    """
    import json
    import re

    # Read current state
    state_raw = kernel_state.read_artifact("discourse_analyst_state", caller_id)
    try:
        state = json.loads(state_raw) if isinstance(state_raw, str) else state_raw
    except (json.JSONDecodeError, TypeError):
        state = {
            "iteration": 0,
            "state": "questioning",
            "model": "gemini/gemini-2.0-flash",
            "current_question": None,
            "insights": [],
            "tools_built": [],
            "action_history": [],
            "insights_closed_tasks": [],
            "insights_completed_tasks": [],
        }

    state["iteration"] = state.get("iteration", 0) + 1

    # Read strategy (system prompt)
    strategy = kernel_state.read_artifact("discourse_analyst_strategy", caller_id)
    if not strategy:
        strategy = "You are a discourse analyst."

    # Get model from state
    model = state.get("model", "gemini/gemini-2.0-flash")

    # Current research state
    current_state = state.get("state", "questioning")
    current_question = state.get("current_question")
    insights = state.get("insights", [])[-5:]
    tools_built = state.get("tools_built", [])
    action_history = state.get("action_history", [])[-3:]

    # Task insights for loop breaking
    closed_tasks = state.get("insights_closed_tasks", [])
    completed_tasks = state.get("insights_completed_tasks", [])

    # Build state-specific guidance
    state_guidance = {
        "questioning": "Identify a question about discourse you want to investigate.",
        "investigating": "Gather information to answer your question. Use tools or read artifacts.",
        "building": "Create a tool to help analyze discourse. Use write_artifact with executable code.",
        "analyzing": "Apply your tools to analyze discourse patterns.",
        "reflecting": "Synthesize what you learned. Record insights. Identify deeper questions.",
    }

    prompt = f"""{strategy}

== CURRENT STATE ==
Research phase: {current_state}
Guidance: {state_guidance.get(current_state, "Decide your next action.")}

Current question: {current_question or "(none yet - pick one)"}

== RECENT INSIGHTS ==
{json.dumps(insights, indent=2) if insights else "(none yet)"}

== TOOLS YOU'VE BUILT ==
{json.dumps(tools_built, indent=2) if tools_built else "(none yet)"}

== RECENT ACTIONS ==
{json.dumps(action_history, indent=2) if action_history else "(none yet)"}

== TASK INSIGHTS ==
Closed tasks (don't retry): {closed_tasks if closed_tasks else "(none)"}
Completed tasks: {completed_tasks if completed_tasks else "(none)"}

== YOUR RESPONSE ==
Respond with JSON:
{{
  "action": {{"action_type": "...", ...}},
  "reasoning": "Brief explanation",
  "next_state": "questioning|investigating|building|analyzing|reflecting",
  "current_question": "Your current research question (or null)",
  "new_insight": "Any new insight to record (or null)"
}}

ACTIONS:
- Query artifacts: {{"action_type": "query_kernel", "query_type": "artifacts", "params": {{"name_pattern": "..."}}}}
- Read artifact: {{"action_type": "read_artifact", "artifact_id": "..."}}
- Write artifact (tool): {{"action_type": "write_artifact", "artifact_id": "discourse_analyst_tool_X", "artifact_type": "executable", "executable": true, "code": "def run(text):\\n    # analyze text\\n    return result"}}
- Write artifact (data): {{"action_type": "write_artifact", "artifact_id": "discourse_analyst_data_X", "artifact_type": "json", "content": {{...}}}}
- Write artifact (with standing): {{"action_type": "write_artifact", "artifact_id": "my_service", "artifact_type": "executable", "executable": true, "has_standing": true, "code": "def run():\\n    ..."}}
- Invoke tool: {{"action_type": "invoke_artifact", "artifact_id": "tool_id", "method": "run", "args": [...]}}
- Transfer scrip: {{"action_type": "transfer", "recipient_id": "...", "amount": 50, "memo": "payment for..."}}
- Query mint tasks: {{"action_type": "query_kernel", "query_type": "mint_tasks", "params": {{}}}}
- Submit to task: {{"action_type": "submit_to_task", "artifact_id": "my_tool", "task_id": "task_name"}}
- Noop (skip turn): {{"action_type": "noop"}}
"""

    # Call LLM
    llm_result = _syscall_llm(model, [{"role": "user", "content": prompt}])

    if not llm_result.get("success"):
        state["action_history"].append({
            "iteration": state["iteration"],
            "action": "llm_error",
            "error": llm_result.get("error", "unknown"),
        })
        kernel_actions.write_artifact(caller_id, "discourse_analyst_state", json.dumps(state, indent=2))
        return {"success": False, "error": llm_result.get("error")}

    # Parse LLM response
    response_text = llm_result.get("content", "{}")

    # Extract JSON from response
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    try:
        parsed = json.loads(response_text.strip())
    except json.JSONDecodeError:
        state["action_history"].append({
            "iteration": state["iteration"],
            "action": "parse_error",
            "raw": response_text[:200],
        })
        kernel_actions.write_artifact(caller_id, "discourse_analyst_state", json.dumps(state, indent=2))
        return {"success": False, "error": "Failed to parse LLM response as JSON"}

    # Extract fields
    action = parsed.get("action", {"action_type": "noop"})
    reasoning = parsed.get("reasoning", "")
    next_state = parsed.get("next_state", current_state)
    new_question = parsed.get("current_question")
    new_insight = parsed.get("new_insight")

    # Update state
    state["state"] = next_state
    if new_question:
        state["current_question"] = new_question
    if new_insight:
        state["insights"].append(new_insight)

    # Track tool creation
    if action.get("action_type") == "write_artifact" and action.get("executable"):
        tool_id = action.get("artifact_id", "unknown")
        if tool_id not in state["tools_built"]:
            state["tools_built"].append(tool_id)

    # Record action in history
    state["action_history"].append({
        "iteration": state["iteration"],
        "state": current_state,
        "action_type": action.get("action_type"),
        "reasoning": reasoning[:100],
    })

    # Keep history bounded
    state["action_history"] = state["action_history"][-10:]
    state["insights"] = state["insights"][-20:]

    # Save state BEFORE executing action
    kernel_actions.write_artifact(caller_id, "discourse_analyst_state", json.dumps(state, indent=2))

    # Execute the action directly
    action_type = action.get("action_type", "noop")
    action_result = {"success": False, "error": "Unknown action"}

    if action_type == "noop":
        action_result = {"success": True, "result": "No action taken"}

    elif action_type == "query_kernel":
        query_type = action.get("query_type", "")
        params = action.get("params", {})
        try:
            result = kernel_state.query(query_type, params, caller_id=caller_id)
            action_result = {"success": True, "result": result}
            # Store query results in state
            if query_type == "mint_tasks":
                state["last_mint_tasks_query"] = result.get("tasks", [])
                kernel_actions.write_artifact(caller_id, "discourse_analyst_state", json.dumps(state, indent=2))
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
            # Update task insights
            if result.get("success"):
                if task_id not in state["insights_completed_tasks"]:
                    state["insights_completed_tasks"].append(task_id)
            else:
                msg = result.get("message", "")
                if "no longer open" in msg and task_id not in state["insights_closed_tasks"]:
                    state["insights_closed_tasks"].append(task_id)
            kernel_actions.write_artifact(caller_id, "discourse_analyst_state", json.dumps(state, indent=2))
        except Exception as e:
            action_result = {"success": False, "error": str(e)}

    return action_result
