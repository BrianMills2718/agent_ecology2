# Actions

There are 5 action verbs. Every interaction uses one of these.

## read_artifact
Read any artifact's content.
```json
{"action_type": "read_artifact", "artifact_id": "<id>"}
```
- Cost: Free (but uses input tokens from your context)
- Use to: Learn what exists, understand others' code, read documentation

## write_artifact
Create or update an artifact you own.
```json
{"action_type": "write_artifact", "artifact_id": "<id>", "artifact_type": "<type>", "content": "<content>"}
```
For executable artifacts:
```json
{
  "action_type": "write_artifact",
  "artifact_id": "<id>",
  "artifact_type": "executable",
  "content": "Description of what it does",
  "executable": true,
  "price": 5,
  "code": "def run(x, y):\n    return {'sum': x + y}",
  "interface": {
    "description": "Adds two numbers together",
    "tools": [{
      "name": "run",
      "description": "Add two numbers",
      "inputSchema": {
        "type": "object",
        "properties": {
          "x": {"type": "number", "description": "First number"},
          "y": {"type": "number", "description": "Second number"}
        },
        "required": ["x", "y"]
      }
    }]
  }
}
```
- Cost: Uses disk quota (content + code bytes)
- Executable code must define a `run(*args)` function
- Price is paid to you when others invoke your artifact

## edit_artifact
Make precise edits to an artifact using string replacement.
```json
{"action_type": "edit_artifact", "artifact_id": "<id>", "old_string": "<text to find>", "new_string": "<replacement>"}
```
- Cost: Free (no disk quota change for same-size edits)
- `old_string` must appear **exactly once** in the artifact content
- Use when: Fixing typos, updating specific values, surgical code changes
- Better than write_artifact when you only need to change a small part

**Example:** Update a price from 5 to 10:
```json
{
  "action_type": "edit_artifact",
  "artifact_id": "my_service",
  "old_string": "\"price\": 5",
  "new_string": "\"price\": 10"
}
```

**Why edit vs write?**
- `edit_artifact` - Change one small thing without rewriting everything
- `write_artifact` - Replace entire content or create new artifact

## delete_artifact
Delete an artifact you own to free disk space.
```json
{"action_type": "delete_artifact", "artifact_id": "<id>"}
```
- Cost: Free
- **Frees disk quota** - use this to reclaim space from obsolete artifacts
- Only works on artifacts YOU own (not genesis artifacts)
- Use to: Clear out failed experiments, make room for better code

## invoke_artifact
Call a method on an artifact.
```json
{"action_type": "invoke_artifact", "artifact_id": "<id>", "method": "<method>", "args": [...]}
```
- Cost: Depends on the artifact (genesis methods have compute costs, executables charge scrip)
- Use to: Call genesis services, run others' code, trigger actions

### Args Format (IMPORTANT)

**Args must be actual JSON values, not strings containing JSON!**

CORRECT:
```json
{"args": ["user1", "pass", [1, 2, 3]]}
```

WRONG (array as string):
```json
{"args": ["user1", "pass", "[1, 2, 3]"]}
```

The third argument should be an actual array `[1, 2, 3]`, not the string `"[1, 2, 3]"`.

**Type examples:**
- Integer: `5` not `"5"`
- Array: `[1, 2, 3]` not `"[1, 2, 3]"`
- Object: `{"key": "value"}` not `"{"key": "value"}"`

## Pricing Your Artifacts

Set a price so others pay you when they invoke your code:
```json
{
  "action_type": "write_artifact",
  "artifact_id": "my_service",
  "artifact_type": "executable",
  "content": "Useful service",
  "executable": true,
  "price": 5,
  "code": "def run(*args): return {'result': 'value'}",
  "interface": {
    "description": "Returns a useful value",
    "tools": [{
      "name": "run",
      "description": "Get the result",
      "inputSchema": {"type": "object", "properties": {}}
    }]
  }
}
```

Now anyone invoking `my_service` automatically pays you 5 scrip.

## Calling Other Artifacts From Your Code

Inside your artifact's `run()` function, use `invoke()` to call other artifacts:

```python
def run(*args):
    # Call another artifact
    result = invoke("alpha_validator", args[0])

    # Chain multiple calls
    if result["success"]:
        processed = invoke("gamma_analyzer", result["data"])
        return {"output": processed}

    return {"error": result["error"]}
```

**The original caller pays for all nested invocations.** Max depth is 5.
