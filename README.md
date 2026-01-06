# werr

A simple, opinionated, python project task runner.

A task is a configured sequence of commands to run.

```toml
[project]
name = "appletree"
version = "0.1.0"
dependencies = [
    "pysunlight==24.1",
]

[tool.werr]
# 'check' is the default task if `werr` is run with no arguments.
tasks.check = [
    "black --check .",
    "isort --check .",
    "ruff check .",
    "mypy .",
    "pytest",
]
tasks.fix = [
    "black .",
    "isort .",
    "ruff fix .",
]
```

Running `werr` executes each `check` command in sequence, printing which failed and how.
The tool returns a non-zero exit code if any command fails.

Running `werr fix` executes each `fix` command in sequence.

All commands run using `uv` in isolated mode.

## Structured Output

```bash
werr         # interactive human readable output (default)
werr --json  # emit lines of JSON representing the result of each command
werr --xml   # print Junit XML for CI
```

## Custom Tasks

Define a custom task with `tasks.<name> = [ ... ]`

```toml
[tool.werr]
# ...
tasks.docs = [
    "sphinx-build -b html .",
]
```

Running `werr docs` will build the documentation.

## New Project

A suggested workflow for creating a new project is:

1. `uv init`
2. `uv add --dev black ruff ty pytest werr`
3. add tasks to `[tool.werr]`
4. `uv run werr` or in venv just `werr`
