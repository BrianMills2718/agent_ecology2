# External Tools

Extending your capabilities with external libraries.

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
