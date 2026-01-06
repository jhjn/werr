# plscheck

A simple, opinionated, python project task runner.

```toml
[project]
name = "apple"
version = "0.1.0"
dependencies = [
    "pysunlight==24.1",
]

[tool.plscheck]
tasks = [
    "mypy .",
    "black --check .",
    "isort --check .",
    "ruff check .",
]
```

Run `pls` to run each task in sequence, printing which fail and how.

## Structued Output

```bash
pls --cli   # interactive human readable output (default)
pls --json  # lines of JSON representing the result of each task
pls --xml   # junit XML for CI
```
