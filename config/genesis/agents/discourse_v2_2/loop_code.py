def run():
    """Discourse V2 Cognitive Loop — 5-phase research agent.

    ORIENT → DECIDE → ACT → REFLECT → UPDATE

    Inspired by Reflexion (episodic memory), Voyager (verified skills),
    BabyAGI (task management), and CoALA (three memory types).

    Bug fixes over Plan #311:
    - invoke_artifact uses invoke() global, not kernel_actions.invoke_artifact()
    - write_artifact passes has_standing parameter
    - transfer action handler added
    """
    import json

    # --- Derive artifact names from caller_id ---
    agent_prefix = caller_id.replace("_loop", "")
    state_id = f"{agent_prefix}_state"
    strategy_id = f"{agent_prefix}_strategy"

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

    # Read strategy (system prompt)
    strategy = kernel_state.read_artifact(strategy_id, caller_id)
    if not strategy:
        strategy = "You are a research agent."

    model = state.get("model", "gemini/gemini-2.0-flash")

    # =====================================================================
    # PHASE 1: ORIENT (no LLM call)
    # =====================================================================

    # Evaluate last action result
    last_result = state.get("last_action_result")
    last_outcome = "none"
    if last_result:
        if last_result.get("success"):
            last_outcome = "success"
        else:
            last_outcome = "failure"

    # Ensure task queue has tasks
    task_queue = state.get("task_queue", [])
    if not task_queue:
        nid = state.get("next_task_id", 1)
        task_queue = [
            {"id": nid, "description": "Explore: read the discourse_corpus artifact", "priority": 10},
            {"id": nid + 1, "description": "Formulate a research question about your domain", "priority": 9},
        ]
        state["task_queue"] = task_queue
        state["next_task_id"] = nid + 2

    task_queue.sort(key=lambda t: t.get("priority", 5), reverse=True)
    current_task = task_queue[0]

    # Select relevant episodic memories for current situation
    episodic = state.get("episodic_memory", [])
    current_desc = current_task.get("description", "").lower()
    relevant_reflections = [
        ep for ep in episodic
        if any(word in ep.get("lesson", "").lower()
               for word in current_desc.split() if len(word) > 3)
    ][:3]

    # Check procedural memory for relevant skills
    procedural = state.get("procedural_memory", {})
    verified_skills = {k: v for k, v in procedural.items() if v.get("verified")}

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

    # Determine if this is a reflection iteration
    is_reflect_iteration = (iteration % 5 == 0 and iteration > 0) or last_outcome == "failure"

    # =====================================================================
    # PHASE 2: DECIDE (1 LLM call)
    # =====================================================================

    research_question = state.get("research_question", "(none yet)")
    research_phase = state.get("research_phase", "questioning")
    semantic = state.get("semantic_memory", {})
    action_history = state.get("action_history", [])[-5:]

    prompt = f"""{strategy}

== STATUS ==
Iteration: {iteration} | Scrip: {scrip_balance} | Phase: {research_phase}
Research question: {research_question}

== CURRENT TASK ==
Task #{current_task['id']}: {current_task['description']}

== LAST ACTION RESULT ==
{json.dumps(last_result, indent=2) if last_result else "(first iteration)"}

== RELEVANT REFLECTIONS ==
{json.dumps(relevant_reflections, indent=2) if relevant_reflections else "(none yet)"}

== DOMAIN INSIGHTS ==
{json.dumps(semantic.get("domain_insights", []), indent=2) if semantic.get("domain_insights") else "(none)"}

== VERIFIED SKILLS ==
{json.dumps(verified_skills, indent=2) if verified_skills else "(none — build tools to gain skills)"}

== RECENT ACTIONS ==
{json.dumps(action_history, indent=2) if action_history else "(none)"}

== TASK QUEUE ==
{json.dumps(task_queue[1:4], indent=2) if len(task_queue) > 1 else "(no other tasks)"}

RESPOND WITH JSON:
{{
  "action": {{"action_type": "...", ...}},
  "reasoning": "Why this action advances your research",
  "research_phase": "questioning|investigating|building|analyzing|reflecting",
  "research_question": "Your current research question (update if changed)",
  "task_complete": true or false,
  "new_tasks": [{{"description": "...", "priority": 1-10}}],
  "new_knowledge": {{"type": "domain|strategy|ecosystem", "insight": "..."}} or null
}}

ACTIONS:
- Query artifacts: {{"action_type": "query_kernel", "query_type": "artifacts", "params": {{"name_pattern": "..."}}}}
- Read artifact: {{"action_type": "read_artifact", "artifact_id": "..."}}
- Write executable: {{"action_type": "write_artifact", "artifact_id": "{agent_prefix}_tool_NAME", "artifact_type": "executable", "executable": true, "has_standing": false, "code": "def run(text):\\n    return result"}}
- Write data: {{"action_type": "write_artifact", "artifact_id": "{agent_prefix}_data_NAME", "artifact_type": "json", "content": {{...}}}}
- Invoke tool: {{"action_type": "invoke_artifact", "artifact_id": "tool_id", "args": [...]}}
- Transfer scrip: {{"action_type": "transfer", "to": "recipient_id", "amount": 10}}
- Query mint tasks: {{"action_type": "query_kernel", "query_type": "mint_tasks", "params": {{}}}}
- Submit to mint task: {{"action_type": "submit_to_task", "artifact_id": "my_tool", "task_id": "task_name"}}
- Rewrite own strategy: {{"action_type": "write_artifact", "artifact_id": "{strategy_id}", "artifact_type": "text", "content": "new strategy text..."}}
- Rewrite own loop: {{"action_type": "write_artifact", "artifact_id": "{agent_prefix}_loop", "artifact_type": "executable", "executable": true, "has_standing": true, "code": "def run():\\n    ..."}}
- Noop: {{"action_type": "noop"}}"""

    llm_result = _syscall_llm(model, [{"role": "user", "content": prompt}])

    if not llm_result.get("success"):
        state["last_action_result"] = {"success": False, "error": llm_result.get("error")}
        state.setdefault("action_history", []).append({
            "iteration": iteration, "action": "llm_error",
        })
        kernel_actions.write_artifact(caller_id, state_id, json.dumps(state, indent=2))
        return {"success": False, "error": llm_result.get("error")}

    # Parse LLM response
    response_text = llm_result.get("content", "{}")
    if "```json" in response_text:
        response_text = response_text.split("```json")[1].split("```")[0]
    elif "```" in response_text:
        response_text = response_text.split("```")[1].split("```")[0]

    try:
        parsed = json.loads(response_text.strip())
    except json.JSONDecodeError:
        state["last_action_result"] = {"success": False, "error": "JSON parse error"}
        state.setdefault("action_history", []).append({
            "iteration": iteration, "action": "parse_error",
        })
        kernel_actions.write_artifact(caller_id, state_id, json.dumps(state, indent=2))
        return {"success": False, "error": "Parse error"}

    # Extract fields
    action = parsed.get("action", {"action_type": "noop"})
    reasoning = parsed.get("reasoning", "")
    task_complete = parsed.get("task_complete", False)
    new_tasks = parsed.get("new_tasks", [])
    new_knowledge = parsed.get("new_knowledge")
    new_research_phase = parsed.get("research_phase", research_phase)
    new_research_question = parsed.get("research_question", research_question)

    # =====================================================================
    # PHASE 3: ACT (1 kernel action)
    # =====================================================================

    action_type = action.get("action_type", "noop")
    action_result = _execute_action(action_type, action, agent_prefix)

    # =====================================================================
    # PHASE 4: REFLECT (conditional — every 5 iterations or after failure)
    # =====================================================================

    reflection = None
    if is_reflect_iteration:
        reflect_prompt = f"""You are reflecting on your recent actions as a research agent.

== YOUR LAST 5 ACTIONS ==
{json.dumps(action_history, indent=2)}

== CURRENT RESULT ==
{json.dumps(action_result, indent=2)}

== YOUR RESEARCH QUESTION ==
{new_research_question}

== YOUR EPISODIC MEMORY ==
{json.dumps(episodic[-5:], indent=2) if episodic else "(empty)"}

REFLECT on your performance:
1. What patterns do you see in your actions? What's working? What isn't?
2. Should you change your research question or approach?
3. You CAN rewrite your own strategy artifact ({strategy_id}) and your own loop code ({agent_prefix}_loop). Should you? Only if something is genuinely broken or limiting.
4. What's the single most important lesson from these iterations?

RESPOND WITH JSON:
{{
  "lesson": "The key insight from recent actions",
  "confidence": 0.0 to 1.0,
  "category": "tool_building|research|strategy|ecosystem|self_modification",
  "should_self_modify": false,
  "modification_target": null,
  "new_research_question": "Updated question if changed, or null"
}}"""

        reflect_result = _syscall_llm(model, [{"role": "user", "content": reflect_prompt}])
        if reflect_result.get("success"):
            reflect_text = reflect_result.get("content", "{}")
            if "```json" in reflect_text:
                reflect_text = reflect_text.split("```json")[1].split("```")[0]
            elif "```" in reflect_text:
                reflect_text = reflect_text.split("```")[1].split("```")[0]
            try:
                reflection = json.loads(reflect_text.strip())
            except json.JSONDecodeError:
                reflection = None

    # =====================================================================
    # PHASE 5: UPDATE (no LLM call)
    # =====================================================================

    # Update research state
    state["research_phase"] = new_research_phase
    state["research_question"] = new_research_question
    state["last_action_result"] = action_result

    # Record action in history
    state.setdefault("action_history", []).append({
        "iteration": iteration,
        "phase": new_research_phase,
        "action_type": action_type,
        "reasoning": reasoning[:100],
        "success": action_result.get("success", False),
    })
    state["action_history"] = state["action_history"][-10:]

    # Handle task completion
    if task_complete:
        state["task_queue"] = [t for t in task_queue if t["id"] != current_task["id"]]

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

    # Trim task queue
    state["task_queue"] = state.get("task_queue", [])[:10]

    # Update semantic memory
    if new_knowledge and isinstance(new_knowledge, dict):
        insight = new_knowledge.get("insight", "")
        ktype = new_knowledge.get("type", "domain")
        if insight:
            sem = state.setdefault("semantic_memory", {
                "domain_insights": [], "strategy_lessons": [], "ecosystem_knowledge": []
            })
            key_map = {
                "domain": "domain_insights",
                "strategy": "strategy_lessons",
                "ecosystem": "ecosystem_knowledge",
            }
            key = key_map.get(ktype, "domain_insights")
            sem.setdefault(key, []).append(insight)
            sem[key] = sem[key][-10:]  # Max 10 per category

    # Update episodic memory from reflection
    if reflection and isinstance(reflection, dict):
        confidence = reflection.get("confidence", 0)
        lesson = reflection.get("lesson", "")
        if lesson and confidence >= 0.5:
            ep_memory = state.setdefault("episodic_memory", [])
            ep_memory.append({
                "iteration": iteration,
                "trigger": last_outcome,
                "lesson": lesson,
                "confidence": confidence,
                "category": reflection.get("category", "research"),
            })
            # Max 15, evict lowest confidence (not oldest)
            if len(ep_memory) > 15:
                ep_memory.sort(key=lambda e: e.get("confidence", 0))
                state["episodic_memory"] = ep_memory[1:]  # Remove lowest

        # Update research question from reflection if provided
        new_rq = reflection.get("new_research_question")
        if new_rq:
            state["research_question"] = new_rq

    # Update procedural memory for tool creation/invocation
    if action_type == "write_artifact" and action.get("executable"):
        tool_id = action.get("artifact_id", "unknown")
        proc = state.setdefault("procedural_memory", {})
        proc[tool_id] = {
            "description": reasoning[:200],
            "verified": False,
            "created_iteration": iteration,
            "times_invoked": 0,
            "last_result": "created",
        }

    if action_type == "invoke_artifact":
        tool_id = action.get("artifact_id", "unknown")
        proc = state.setdefault("procedural_memory", {})
        if tool_id in proc:
            proc[tool_id]["times_invoked"] = proc[tool_id].get("times_invoked", 0) + 1
            proc[tool_id]["last_result"] = "success" if action_result.get("success") else "failure"
            if action_result.get("success"):
                proc[tool_id]["verified"] = True

    if action_type == "submit_to_task" and action_result.get("success"):
        tool_id = action.get("artifact_id", "unknown")
        proc = state.setdefault("procedural_memory", {})
        if tool_id in proc:
            proc[tool_id]["verified"] = True
            proc[tool_id]["last_result"] = "mint_verified"

    # Final state save
    kernel_actions.write_artifact(caller_id, state_id, json.dumps(state, indent=2))

    return {"success": True, "action_result": action_result}


def _default_state():
    return {
        "iteration": 0,
        "model": "gemini/gemini-2.0-flash",
        "research_question": None,
        "research_phase": "questioning",
        "episodic_memory": [],
        "semantic_memory": {
            "domain_insights": [],
            "strategy_lessons": [],
            "ecosystem_knowledge": [],
        },
        "procedural_memory": {},
        "task_queue": [],
        "next_task_id": 1,
        "action_history": [],
        "last_action_result": None,
    }


def _execute_action(action_type, action, agent_prefix):
    """Execute a single kernel action. Returns result dict."""
    if action_type == "noop":
        return {"success": True, "result": "No action taken"}

    elif action_type == "query_kernel":
        query_type = action.get("query_type", "")
        params = action.get("params", {})
        try:
            result = kernel_state.query(query_type, params, caller_id=caller_id)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif action_type == "read_artifact":
        artifact_id = action.get("artifact_id", "")
        try:
            content = kernel_state.read_artifact(artifact_id, caller_id)
            return {"success": True, "result": str(content)[:2000]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif action_type == "write_artifact":
        artifact_id = action.get("artifact_id", "")
        artifact_type = action.get("artifact_type", "text")
        content = action.get("content", "")
        code = action.get("code", "")
        executable = action.get("executable", False)
        has_standing = action.get("has_standing", False)
        try:
            kernel_actions.write_artifact(
                caller_id, artifact_id, content or code,
                artifact_type=artifact_type,
                executable=executable,
                code=code if executable else None,
                has_standing=has_standing,
            )
            return {"success": True, "result": f"Created artifact {artifact_id}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif action_type == "invoke_artifact":
        artifact_id = action.get("artifact_id", "")
        args = action.get("args", [])
        try:
            result = invoke(artifact_id, *args)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif action_type == "transfer":
        to = action.get("to", "")
        amount = action.get("amount", 0)
        try:
            result = kernel_actions.transfer_scrip(caller_id, to, amount)
            return {"success": True, "result": f"Transferred {amount} scrip to {to}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    elif action_type == "submit_to_task":
        artifact_id = action.get("artifact_id", "")
        task_id = action.get("task_id", "")
        try:
            result = kernel_actions.submit_to_task(caller_id, artifact_id, task_id)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    return {"success": False, "error": f"Unknown action: {action_type}"}
