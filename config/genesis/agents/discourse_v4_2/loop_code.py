def run():
    """Discourse V4 Cognitive Loop — structured tool calling (Plan #323).

    Uses LLM tool calling instead of free-form JSON generation.
    Multi-turn: up to 3 tool call rounds per iteration.
    Memory: strategy (system msg) + notebook (persistent) + conversation (immediate).
    """
    import json

    # --- Derive artifact names from caller_id ---
    agent_prefix = caller_id.replace("_loop", "")
    state_id = f"{agent_prefix}_state"
    strategy_id = f"{agent_prefix}_strategy"
    notebook_id = f"{agent_prefix}_notebook"

    # --- Read current state ---
    state_raw = kernel_state.read_artifact(state_id, caller_id)
    try:
        state = json.loads(state_raw) if isinstance(state_raw, str) else state_raw
    except (json.JSONDecodeError, TypeError):
        state = _default_state()
    if not isinstance(state, dict):
        state = _default_state()

    state["iteration"] = state.get("iteration", 0) + 1
    iteration = state["iteration"]

    # --- Read strategy (becomes system message) ---
    strategy = kernel_state.read_artifact(strategy_id, caller_id)
    if not strategy:
        strategy = "You are a research agent."

    # --- Read notebook (persistent long-term memory) ---
    notebook_raw = kernel_state.read_artifact(notebook_id, caller_id)
    try:
        notebook = json.loads(notebook_raw) if isinstance(notebook_raw, str) else notebook_raw
    except (json.JSONDecodeError, TypeError):
        notebook = {"key_facts": {}, "journal": []}
    if not isinstance(notebook, dict):
        notebook = {"key_facts": {}, "journal": []}
    key_facts = notebook.get("key_facts", {})
    journal = notebook.get("journal", [])

    model = state.get("model", "gemini/gemini-2.0-flash")

    # --- Build context ---
    task_queue = state.get("task_queue", [])
    if not task_queue:
        nid = state.get("next_task_id", 1)
        task_queue = [
            {"id": nid, "description": "Explore: read the discourse_corpus artifact", "priority": 10},
            {"id": nid + 1, "description": "Formulate a research question", "priority": 9},
        ]
        state["task_queue"] = task_queue
        state["next_task_id"] = nid + 2

    task_queue.sort(key=lambda t: t.get("priority", 5), reverse=True)
    current_task = task_queue[0]

    action_history = state.get("action_history", [])[-10:]
    recent_lines = []
    for ah in action_history:
        status = "OK" if ah.get("success") else "FAIL"
        recent_lines.append(
            f"  i{ah.get('iteration', '?')} {ah.get('action', '')} -> {status}: "
            f"{ah.get('result', '')[:100]}"
        )
    recent_text = "\n".join(recent_lines) if recent_lines else "(first iteration)"

    key_facts_text = json.dumps(key_facts, indent=2) if key_facts else "(empty)"
    journal_recent = journal[-20:]
    journal_text = "\n".join(journal_recent) if journal_recent else "(empty)"

    # Query scrip balance
    scrip_balance = "unknown"
    try:
        balance_result = kernel_state.query(
            "balances", {"principal_id": caller_id}, caller_id=caller_id
        )
        if isinstance(balance_result, dict):
            scrip_balance = balance_result.get("scrip", balance_result.get("balance", "unknown"))
    except Exception:
        pass

    # --- Build messages ---
    user_msg = f"""Iteration {iteration} | Scrip: {scrip_balance} | Phase: {state.get('research_phase', 'questioning')}
Research question: {state.get('research_question', '(none yet — formulate one)')}

== CURRENT TASK ==
Task #{current_task['id']}: {current_task['description']}

== NOTEBOOK (persistent memory — survives across iterations) ==
Key facts: {key_facts_text}

Journal (last {len(journal_recent)} entries):
{journal_text}

== RECENT HISTORY (last {len(action_history)} actions) ==
{recent_text}

== TASK QUEUE ==
{json.dumps(task_queue[:5], indent=2)}

Use tools to take actions. Other agents (discourse_v4_2, discourse_v4_3) may have built useful artifacts — use query_artifacts to discover them.
When done acting, call think_and_plan to record your reasoning and manage tasks."""

    messages = [
        {"role": "system", "content": strategy},
        {"role": "user", "content": user_msg},
    ]

    # --- Multi-turn tool calling: up to 3 rounds per iteration ---
    MAX_TOOL_ROUNDS = 3
    all_actions = []

    rounds_used = 0
    for _round in range(MAX_TOOL_ROUNDS):
        # All rounds use tool_choice="required" — Gemini returns empty choices with "auto".
        # The LLM naturally stops by calling think_and_plan as its last action.
        result = _syscall_llm(model, messages, tools=TOOLS, tool_choice="required")
        rounds_used = _round + 1

        if not result.get("success"):
            state["last_action_result"] = {"success": False, "error": result.get("error")}
            state.setdefault("action_history", []).append({
                "iteration": iteration, "action": "llm_error",
                "success": False, "result": result.get("error", "")[:200],
            })
            kernel_actions.write_artifact(caller_id, state_id, json.dumps(state, indent=2))
            return {"success": False, "error": result.get("error")}

        tool_calls = result.get("tool_calls", [])
        content = result.get("content", "")

        if not tool_calls:
            # LLM responded with text only — done with this iteration
            if content:
                journal.append(f"i{iteration} [thinking] {content[:200]}")
            break

        # Append assistant message with tool_calls to conversation
        assistant_msg = {"role": "assistant", "content": content or "", "tool_calls": tool_calls}
        messages.append(assistant_msg)

        # Execute each tool call and append results
        for tc in tool_calls:
            func = tc.get("function", {})
            tool_name = func.get("name", "")
            args_raw = func.get("arguments", "{}")
            try:
                args = json.loads(args_raw) if isinstance(args_raw, str) else args_raw
            except json.JSONDecodeError:
                args = {}

            tool_result = _dispatch_tool(
                tool_name, args, agent_prefix, state, key_facts, journal, iteration
            )
            all_actions.append({"tool": tool_name, "args": args, "result": tool_result})

            # Add tool result to conversation
            result_str = json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)
            messages.append({
                "role": "tool",
                "tool_call_id": tc.get("id", ""),
                "content": result_str,
            })

    # --- Update state ---
    for act in all_actions:
        r = act["result"]
        state.setdefault("action_history", []).append({
            "iteration": iteration,
            "action": act["tool"],
            "success": r.get("success", False) if isinstance(r, dict) else True,
            "result": str(r.get("result", r.get("error", "")))[:200] if isinstance(r, dict) else str(r)[:200],
        })
    state["action_history"] = state["action_history"][-15:]

    # Log rounds and tools used per iteration
    journal.append(f"i{iteration} [meta] rounds={rounds_used} tools={len(all_actions)}")

    # Save notebook
    notebook["key_facts"] = key_facts
    notebook["journal"] = journal[-50:]
    kernel_actions.write_artifact(caller_id, notebook_id, json.dumps(notebook, indent=2))

    # Save state
    kernel_actions.write_artifact(caller_id, state_id, json.dumps(state, indent=2))

    last_result = all_actions[-1]["result"] if all_actions else {"success": True, "result": "No actions taken"}
    return {"success": True, "action_result": last_result, "rounds_used": rounds_used, "tools_used": len(all_actions)}


# --- Tool definitions (OpenAI format) ---

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "query_artifacts",
            "description": "Search for artifacts by name pattern. Use this to discover what other agents have built.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name_pattern": {
                        "type": "string",
                        "description": "Glob pattern, e.g. 'discourse_v4*' or '*corpus*'",
                    }
                },
                "required": ["name_pattern"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_artifact",
            "description": "Read an artifact's content by ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {
                        "type": "string",
                        "description": "The artifact ID to read",
                    }
                },
                "required": ["artifact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_artifact",
            "description": "Create or update an artifact. Content must be a string — use json.dumps() for structured data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {
                        "type": "string",
                        "description": "Artifact ID to create/update",
                    },
                    "content": {
                        "type": "string",
                        "description": "Content as a string (use JSON string for structured data)",
                    },
                    "artifact_type": {
                        "type": "string",
                        "enum": ["text", "json", "executable"],
                        "description": "Type of artifact",
                    },
                    "is_executable": {
                        "type": "boolean",
                        "description": "Whether artifact contains executable code (default false)",
                    },
                    "has_standing": {
                        "type": "boolean",
                        "description": "Whether artifact is a principal (default false)",
                    },
                },
                "required": ["artifact_id", "content", "artifact_type"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "invoke_artifact",
            "description": "Invoke an executable artifact with arguments.",
            "parameters": {
                "type": "object",
                "properties": {
                    "artifact_id": {
                        "type": "string",
                        "description": "ID of executable artifact to invoke",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Arguments to pass (default empty)",
                    },
                },
                "required": ["artifact_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_scrip",
            "description": "Transfer scrip to another agent.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {
                        "type": "string",
                        "description": "Recipient principal ID",
                    },
                    "amount": {
                        "type": "integer",
                        "description": "Amount of scrip to transfer",
                    },
                },
                "required": ["to", "amount"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "think_and_plan",
            "description": "Record your reasoning, update research state, and manage tasks. Call this after your actions to wrap up the iteration.",
            "parameters": {
                "type": "object",
                "properties": {
                    "reasoning": {
                        "type": "string",
                        "description": "Your reasoning about what you did and what to do next",
                    },
                    "research_question": {
                        "type": "string",
                        "description": "Your current research question (update if changed)",
                    },
                    "research_phase": {
                        "type": "string",
                        "enum": ["questioning", "investigating", "building", "analyzing"],
                        "description": "Current phase of research",
                    },
                    "task_complete": {
                        "type": "boolean",
                        "description": "Mark current task as done (default false)",
                    },
                    "new_tasks": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "description": {"type": "string"},
                                "priority": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10,
                                },
                            },
                            "required": ["description"],
                        },
                        "description": "New tasks to add to queue",
                    },
                    "key_facts_update": {
                        "type": "object",
                        "description": "Key-value pairs to add/update in persistent notebook",
                    },
                },
                "required": ["reasoning"],
            },
        },
    },
]


def _dispatch_tool(tool_name, args, agent_prefix, state, key_facts, journal, iteration):
    """Dispatch a tool call to the appropriate handler."""
    if tool_name == "query_artifacts":
        pattern = args.get("name_pattern", "*")
        try:
            result = kernel_state.query("artifacts", {"name_pattern": pattern}, caller_id=caller_id)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool_name == "read_artifact":
        artifact_id = args.get("artifact_id", "")
        try:
            content = kernel_state.read_artifact(artifact_id, caller_id)
            if content is None:
                return {"success": False, "error": f"Cannot read '{artifact_id}': not found or access denied"}
            return {"success": True, "result": str(content)[:2000]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool_name == "write_artifact":
        artifact_id = args.get("artifact_id", "")
        content = args.get("content", "")
        artifact_type = args.get("artifact_type", "text")
        is_executable = args.get("is_executable", False)
        has_standing = args.get("has_standing", False)
        access_contract_id = f"{agent_prefix}_contract"
        try:
            kernel_actions.write_artifact(
                caller_id, artifact_id, content,
                artifact_type=artifact_type,
                executable=is_executable,
                code=content if is_executable else None,
                has_standing=has_standing,
                access_contract_id=access_contract_id,
            )
            return {"success": True, "result": f"Created artifact {artifact_id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool_name == "invoke_artifact":
        artifact_id = args.get("artifact_id", "")
        invoke_args = args.get("args", [])
        try:
            result = invoke(artifact_id, *invoke_args)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool_name == "transfer_scrip":
        to = args.get("to", "")
        amount = args.get("amount", 0)
        try:
            kernel_actions.transfer_scrip(caller_id, to, amount)
            return {"success": True, "result": f"Transferred {amount} scrip to {to}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif tool_name == "think_and_plan":
        reasoning = args.get("reasoning", "")
        journal.append(f"i{iteration} [think] {reasoning[:200]}")

        # Update research state
        if "research_question" in args:
            state["research_question"] = args["research_question"]
        if "research_phase" in args:
            state["research_phase"] = args["research_phase"]

        # Task management
        if args.get("task_complete"):
            tq = state.get("task_queue", [])
            if tq:
                completed = tq[0]
                state["task_queue"] = [t for t in tq if t["id"] != completed["id"]]
                journal.append(f"i{iteration} [task] Completed: {completed.get('description', '')[:100]}")

        existing_descs = {t.get("description", "").lower().strip() for t in state.get("task_queue", [])}
        for nt in args.get("new_tasks", []):
            if isinstance(nt, dict) and "description" in nt:
                desc = nt["description"]
                if desc.lower().strip() in existing_descs:
                    continue
                nid = state.get("next_task_id", 1)
                state.setdefault("task_queue", []).append({
                    "id": nid,
                    "description": desc,
                    "priority": nt.get("priority", 5),
                })
                state["next_task_id"] = nid + 1
                existing_descs.add(desc.lower().strip())

        # Trim task queue
        state["task_queue"] = state.get("task_queue", [])[:10]

        # Notebook key_facts update
        kf_update = args.get("key_facts_update", {})
        if isinstance(kf_update, dict):
            key_facts.update(kf_update)

        return {"success": True, "result": "Updated research state"}

    return {"success": False, "error": f"Unknown tool: {tool_name}"}


def _default_state():
    return {
        "iteration": 0,
        "model": "gemini/gemini-2.0-flash",
        "research_question": None,
        "research_phase": "questioning",
        "task_queue": [],
        "next_task_id": 1,
        "action_history": [],
    }
