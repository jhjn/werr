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
# 'check' is the default task
tasks.check = [
    "mypy .",
    "black --check .",
    "isort --check .",
    "ruff check .",
]
```

Run `werr` to run each of the `check` commands in sequence, printing which failed and how.
The tool returns a non-zero exit code if any command fails.

All commands run using `uv` in isolated mode.

## Structured Output

```bash
werr         # interactive human readable output (default)
werr --json  # emit lines of JSON representing the result of each command
werr --xml   # print Junit XML for CI
```

## Custom Tasks

Define a custom task like `tasks.<name> = [ ... ]`

```toml
[tool.werr]
tasks.check = [
    "mypy .",
    "black --check .",
    "isort --check .",
    "ruff check .",
]
tasks.fix = [
    "black .",
    "isort .",
    "ruff fix .",
]
tasks.docs = [
    "sphinx-build -b html .",
]
```

Running `werr fix` will run the linter fixes.
Running `werr docs` will build the documentation.
