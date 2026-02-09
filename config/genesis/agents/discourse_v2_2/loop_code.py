def run():
    """Discourse V2 Hybrid Loop — Task-driven research agent.

    Combines alpha_prime's task queue with discourse analyst's research cycle.
    Key improvements over v1:
    - Task queue drives action (concrete, prioritized goals)
    - Auto-progression when stuck in a phase too long
    - Knowledge accumulation with failed-attempt tracking
    - Action results feed back into next iteration's context
    - Build-first: agents create artifacts early, not just investigate
    """
    import json

    # Derive artifact names from caller_id (e.g. discourse_v2_loop -> discourse_v2)
    agent_prefix = caller_id.replace("_loop", "")
    state_id = f"{agent_prefix}_state"
    strategy_id = f"{agent_prefix}_strategy"

    # Read current state
    state_raw = kernel_state.read_artifact(state_id, caller_id)
    try:
        state = json.loads(state_raw) if isinstance(state_raw, str) else state_raw
    except (json.JSONDecodeError, TypeError):
        state = {
            "iteration": 0,
            "model": "gemini/gemini-2.0-flash",
            "phase": "building",
            "phase_iterations": 0,
            "task_queue": [],
            "completed_tasks": [],
            "next_task_id": 1,
            "knowledge": [],
            "tools_built": [],
            "failed_attempts": [],
            "action_history": [],
            "last_action_result": None,
        }

    state["iteration"] = state.get("iteration", 0) + 1

    # Read strategy (system prompt)
    strategy = kernel_state.read_artifact(strategy_id, caller_id)
    if not strategy:
        strategy = "You are a research agent."

    model = state.get("model", "gemini/gemini-2.0-flash")

    # --- Task Queue Management (alpha_prime pattern) ---
    task_queue = state.get("task_queue", [])
    if not task_queue:
        task_queue = [
            {"id": state.get("next_task_id", 1),
             "description": "Build an analysis tool relevant to your research domain",
             "priority": 10},
            {"id": state.get("next_task_id", 1) + 1,
             "description": "Query artifact store to discover what exists",
             "priority": 8},
        ]
        state["task_queue"] = task_queue
        state["next_task_id"] = state.get("next_task_id", 1) + 2

    task_queue.sort(key=lambda t: t.get("priority", 5), reverse=True)
    current_task = task_queue[0]

    # --- Phase Management with Auto-Progression ---
    phase = state.get("phase", "building")
    phase_iterations = state.get("phase_iterations", 0) + 1

    if phase_iterations > 3:
        progression = {
            "investigating": "building",
            "building": "analyzing",
            "analyzing": "reflecting",
            "reflecting": "questioning",
            "questioning": "building",
        }
        old_phase = phase
        phase = progression.get(phase, "building")
        phase_iterations = 1
        if old_phase != phase:
            nid = state.get("next_task_id", 1)
            task_queue.append({
                "id": nid,
                "description": f"Auto-advanced to {phase} phase — act accordingly",
                "priority": 9,
            })
            state["next_task_id"] = nid + 1

    state["phase"] = phase
    state["phase_iterations"] = phase_iterations

    # --- Query scrip balance for context ---
    scrip_balance = "unknown"
    try:
        balance_result = kernel_state.query("ledger", {"method": "balance", "args": [caller_id]}, caller_id=caller_id)
        if isinstance(balance_result, dict):
            scrip_balance = balance_result.get("scrip", balance_result.get("balance", "unknown"))
    except Exception:
        pass

    # --- Periodic reflection (every 10 iterations) ---
    if state["iteration"] % 10 == 0 and state["iteration"] > 0:
        completed_count = len(state.get("completed_tasks", []))
        tools_count = len(state.get("tools_built", []))
        fails = len(state.get("failed_attempts", []))
        nid = state.get("next_task_id", 1)
        state.setdefault("task_queue", []).append({
            "id": nid,
            "description": f"REFLECT: {completed_count} tasks done, {tools_count} tools built, {fails} failures. What strategy is working? What should change?",
            "priority": 10,
        })
        state["next_task_id"] = nid + 1

    # --- Gather Memory Context ---
    knowledge = state.get("knowledge", [])[-10:]
    tools_built = state.get("tools_built", [])
    failed_attempts = state.get("failed_attempts", [])[-5:]
    action_history = state.get("action_history", [])[-5:]
    last_result = state.get("last_action_result")
    completed = state.get("completed_tasks", [])[-5:]

    phase_guidance = {
        "questioning": "Identify a specific research question. What gap matters most?",
        "investigating": "Gather info: query artifacts, read others' work. Don't investigate forever — if nothing exists, BUILD it.",
        "building": "CREATE something tangible. Write an executable artifact. This is where value comes from.",
        "analyzing": "Apply your tools. Invoke artifacts, test hypotheses, generate results.",
        "reflecting": "Synthesize what you learned. Record knowledge. Plan what's next.",
    }

    prompt = f"""{strategy}

== STATUS ==
Iteration: {state['iteration']} | Scrip: {scrip_balance} | Tools built: {len(tools_built)} | Tasks completed: {len(state.get('completed_tasks', []))}

== CURRENT TASK ==
Task #{current_task['id']}: {current_task['description']}

== PHASE: {phase.upper()} ==
{phase_guidance.get(phase, "Take action.")}

== LAST ACTION RESULT ==
{json.dumps(last_result, indent=2) if last_result else "(first iteration)"}

== KNOWLEDGE BASE ==
{json.dumps(knowledge, indent=2) if knowledge else "(empty)"}

== TOOLS YOU'VE BUILT ==
{json.dumps(tools_built, indent=2) if tools_built else "(none — building tools is how you gain capability)"}

== FAILED ATTEMPTS (don't repeat these) ==
{json.dumps(failed_attempts, indent=2) if failed_attempts else "(none)"}

== RECENT ACTIONS ==
{json.dumps(action_history, indent=2) if action_history else "(none)"}

== TASK QUEUE ==
{json.dumps(task_queue[1:4], indent=2) if len(task_queue) > 1 else "(empty — generate new tasks)"}

== COMPLETED TASKS ==
{json.dumps(completed, indent=2) if completed else "(none yet)"}

== MINT TASKS ALREADY DONE (by you or others — don't retry) ==
{json.dumps(state.get('completed_mint_tasks', []), indent=2) if state.get('completed_mint_tasks') else "(none — earn scrip by completing mint tasks!)"}

RESPOND WITH JSON:
{{
  "action": {{"action_type": "...", ...}},
  "reasoning": "Why this action advances your current task",
  "task_result": "What this accomplishes",
  "task_complete": true or false,
  "new_tasks": [{{"description": "...", "priority": 1-10}}],
  "new_knowledge": "Fact or insight to remember (or null)",
  "next_phase": "questioning|investigating|building|analyzing|reflecting"
}}

ACTIONS:
- Query artifacts: {{"action_type": "query_kernel", "query_type": "artifacts", "params": {{"name_pattern": "..."}}}}
- Read artifact: {{"action_type": "read_artifact", "artifact_id": "..."}}
- Write executable: {{"action_type": "write_artifact", "artifact_id": "{agent_prefix}_tool_NAME", "artifact_type": "executable", "executable": true, "code": "def run(text):\\n    return result"}}
- Write data: {{"action_type": "write_artifact", "artifact_id": "{agent_prefix}_data_NAME", "artifact_type": "json", "content": {{...}}}}
- Invoke tool: {{"action_type": "invoke_artifact", "artifact_id": "tool_id", "method": "run", "args": [...]}}
- Query mint tasks: {{"action_type": "query_kernel", "query_type": "mint_tasks", "params": {{}}}}
- Submit to mint task: {{"action_type": "submit_to_task", "artifact_id": "my_tool", "task_id": "task_name"}}
- Noop: {{"action_type": "noop"}}

RULES:
1. NEVER repeat a failed action. Check failed_attempts first.
2. Prefer BUILDING over investigating. Creating artifacts = capability.
3. Each response MUST include at least 1 new_task.
4. Use UNIQUE artifact IDs with your prefix: {agent_prefix}_
5. If you've queried 3+ times without results, BUILD instead."""

    # --- Call LLM ---
    llm_result = _syscall_llm(model, [{"role": "user", "content": prompt}])

    if not llm_result.get("success"):
        state.setdefault("action_history", []).append({
            "iteration": state["iteration"],
            "action": "llm_error",
            "error": llm_result.get("error", "unknown"),
        })
        state["last_action_result"] = {"success": False, "error": llm_result.get("error")}
        kernel_actions.write_artifact(caller_id, state_id, json.dumps(state, indent=2))
        return {"success": False, "error": llm_result.get("error")}

    # --- Parse Response ---
    response_text = llm_result.get("content", "{}")
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    try:
        parsed = json.loads(response_text.strip())
    except json.JSONDecodeError:
        state.setdefault("action_history", []).append({
            "iteration": state["iteration"],
            "action": "parse_error",
            "raw": response_text[:200],
        })
        state.setdefault("failed_attempts", []).append({
            "iteration": state["iteration"],
            "type": "parse_error",
        })
        state["last_action_result"] = {"success": False, "error": "JSON parse error"}
        kernel_actions.write_artifact(caller_id, state_id, json.dumps(state, indent=2))
        return {"success": False, "error": "Parse error"}

    # --- Extract Fields ---
    action = parsed.get("action", {"action_type": "noop"})
    reasoning = parsed.get("reasoning", "")
    task_result = parsed.get("task_result", "")
    task_complete = parsed.get("task_complete", False)
    new_tasks = parsed.get("new_tasks", [])
    new_knowledge = parsed.get("new_knowledge")
    next_phase = parsed.get("next_phase", phase)

    # Update phase
    if next_phase != phase:
        state["phase"] = next_phase
        state["phase_iterations"] = 0

    # Record knowledge
    if new_knowledge:
        state.setdefault("knowledge", []).append(new_knowledge)
        state["knowledge"] = state["knowledge"][-20:]

    # Handle task completion
    if task_complete:
        state["task_queue"] = [t for t in task_queue if t["id"] != current_task["id"]]
        state.setdefault("completed_tasks", []).append({
            "id": current_task["id"],
            "description": current_task["description"],
            "result": task_result,
        })
        state["completed_tasks"] = state["completed_tasks"][-10:]

    # Add new tasks
    for nt in new_tasks:
        if isinstance(nt, dict) and "description" in nt:
            nid = state.get("next_task_id", 1)
            state.setdefault("task_queue", []).append({
                "id": nid,
                "description": nt["description"],
                "priority": nt.get("priority", 5),
            })
            state["next_task_id"] = nid + 1

    # Track tool creation
    if action.get("action_type") == "write_artifact" and action.get("executable"):
        tool_id = action.get("artifact_id", "unknown")
        if tool_id not in state.get("tools_built", []):
            state.setdefault("tools_built", []).append(tool_id)

    # Record action in history
    state.setdefault("action_history", []).append({
        "iteration": state["iteration"],
        "phase": phase,
        "action_type": action.get("action_type"),
        "reasoning": reasoning[:100],
    })
    state["action_history"] = state["action_history"][-10:]

    # Save state BEFORE executing action
    kernel_actions.write_artifact(caller_id, state_id, json.dumps(state, indent=2))

    # --- Execute Action ---
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
        except Exception as e:
            action_result = {"success": False, "error": str(e)}
            state.setdefault("failed_attempts", []).append({
                "iteration": state["iteration"],
                "type": f"query_{query_type}",
                "error": str(e)[:100],
            })

    elif action_type == "read_artifact":
        artifact_id = action.get("artifact_id", "")
        try:
            content = kernel_state.read_artifact(artifact_id, caller_id)
            action_result = {"success": True, "result": str(content)[:500]}
        except Exception as e:
            action_result = {"success": False, "error": str(e)}
            state.setdefault("failed_attempts", []).append({
                "iteration": state["iteration"],
                "type": f"read_{artifact_id}",
                "error": str(e)[:100],
            })

    elif action_type == "write_artifact":
        artifact_id = action.get("artifact_id", "")
        artifact_type = action.get("artifact_type", "text")
        content = action.get("content", "")
        code = action.get("code", "")
        executable = action.get("executable", False)
        try:
            kernel_actions.write_artifact(
                caller_id, artifact_id, content or code,
                artifact_type=artifact_type,
                executable=executable,
                code=code if executable else None,
            )
            action_result = {"success": True, "result": f"Created artifact {artifact_id}"}
        except Exception as e:
            action_result = {"success": False, "error": str(e)}
            state.setdefault("failed_attempts", []).append({
                "iteration": state["iteration"],
                "type": f"write_{artifact_id}",
                "error": str(e)[:100],
            })

    elif action_type == "invoke_artifact":
        artifact_id = action.get("artifact_id", "")
        method = action.get("method", "run")
        args = action.get("args", [])
        kwargs = action.get("kwargs", {})
        try:
            result = kernel_actions.invoke_artifact(
                caller_id, artifact_id, method, args, kwargs
            )
            action_result = {"success": True, "result": result}
        except Exception as e:
            action_result = {"success": False, "error": str(e)}
            state.setdefault("failed_attempts", []).append({
                "iteration": state["iteration"],
                "type": f"invoke_{artifact_id}",
                "error": str(e)[:100],
            })

    elif action_type == "submit_to_task":
        artifact_id = action.get("artifact_id", "")
        task_id = action.get("task_id", "")
        try:
            result = kernel_actions.submit_to_task(caller_id, artifact_id, task_id)
            if result.get("success"):
                action_result = {"success": True, "result": result}
                # Track completed mint tasks so we don't retry them
                state.setdefault("completed_mint_tasks", []).append(task_id)
            else:
                # Submission failed — include test details for learning
                action_result = {"success": False, "result": result}
                state.setdefault("failed_attempts", []).append({
                    "iteration": state["iteration"],
                    "type": f"submit_{task_id}",
                    "artifact": artifact_id,
                    "error": result.get("message", "unknown"),
                    "tests": result.get("public_tests", {}),
                })
        except Exception as e:
            action_result = {"success": False, "error": str(e)}

    # Store action result for next iteration
    state["last_action_result"] = action_result

    # Keep failed_attempts bounded
    state["failed_attempts"] = state.get("failed_attempts", [])[-10:]

    # Final state save
    kernel_actions.write_artifact(caller_id, state_id, json.dumps(state, indent=2))

    return {"success": True, "action_result": action_result}
