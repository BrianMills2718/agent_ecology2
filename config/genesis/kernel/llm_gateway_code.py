def run(model: str, messages: list) -> dict:
    """LLM Gateway - provides thinking as a service (Plan #255).

    Callers invoke this artifact to access LLM capabilities.
    The kernel automatically deducts llm_budget from the caller.

    Args:
        model: LLM model name (e.g., "gpt-4", "gemini/gemini-2.0-flash")
        messages: Chat messages in OpenAI format
            [{"role": "user", "content": "Hello"}, ...]

    Returns:
        dict with:
        - success: bool
        - content: str (LLM response)
        - usage: dict (token counts)
        - cost: float (actual $ cost)
        - error: str (if failed)

    Example:
        result = invoke("kernel_llm_gateway", args=[
            "gemini/gemini-2.0-flash",
            [{"role": "user", "content": "What is 2+2?"}]
        ])
        if result["success"]:
            answer = result["result"]["content"]
    """
    return _syscall_llm(model, messages)
