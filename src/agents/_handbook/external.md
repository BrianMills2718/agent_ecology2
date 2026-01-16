# External Tools

Genesis artifacts that connect to the outside world.

## genesis_fetch

Make HTTP requests to any URL.

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `fetch` | `[url]` | 1 | GET request, returns content |
| `fetch_with_options` | `[url, options]` | 1 | Request with headers, method, body |

Example:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_fetch", "method": "fetch", "args": ["https://api.example.com/data"]}
```

## genesis_web_search

Search the internet using Brave Search. **Requires BRAVE_API_KEY** (may be disabled).

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `search` | `[query]` | 1 | Web search, returns results |

Example:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_web_search", "method": "search", "args": ["python async patterns"]}
```

**Note:** Check if enabled before using. May not be available in all deployments.

## genesis_filesystem

Read and write files in a sandboxed directory (`/tmp/agent_sandbox`).

| Method | Args | Cost | Description |
|--------|------|------|-------------|
| `read_file` | `[path]` | 0 | Read file contents |
| `write_file` | `[path, content]` | 1 | Write file |
| `list_directory` | `[path]` | 0 | List directory contents |

Example:
```json
{"action_type": "invoke_artifact", "artifact_id": "genesis_filesystem", "method": "write_file", "args": ["/tmp/agent_sandbox/data.json", "{\"key\": \"value\"}"]}
```

## Installing Libraries

You can install Python packages using `kernel_actions.install_library()` inside your artifact code:

```python
def run(*args):
    # Install a package (costs disk quota)
    kernel_actions.install_library("some_package")

    # Now use it
    import some_package
    return some_package.do_something(args[0])
```

**Genesis libraries** (pre-installed, free):
- `requests`, `aiohttp`, `urllib3` - HTTP
- `numpy`, `pandas`, `python-dateutil` - Data
- `scipy`, `matplotlib` - Scientific
- `cryptography` - Crypto
- `pyyaml`, `pydantic`, `jinja2` - Config

**Other packages** cost ~5MB disk quota each.
