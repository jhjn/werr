# werr

A simple, opinionated, python project task runner.

```toml
[project]
name = "apple"
version = "0.1.0"
dependencies = [
    "pysunlight==24.1",
]

[tool.werr]
tasks = [
    "mypy .",
    "black --check .",
    "isort --check .",
    "ruff check .",
]
```

Run `werr` to run each task in sequence, printing which tasks failed and how.

All tasks run using `uv` in isolated mode.

## Structured Output

```bash
werr         # interactive human readable output (default)
werr --json  # emit lines of JSON representing the result of each task
werr --xml   # print Junit XML for CI
```

## Custom Modes

Define a custom mode like `custom.<name> = [ ... ]`

```toml
[tool.werr]
tasks = [
    "mypy .",
    "black --check .",
    "isort --check .",
    "ruff check .",
]
custom.fix = [
    "black .",
    "isort .",
    "ruff fix .",
]
custom.docs = [
    "sphinx-build -b html .",
]
```

Running `werr fix` will run the linter fixes.
Running `werr docs` will build the documentation.
