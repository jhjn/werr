## Getting Started
<!-- From no idea to installed and first example -->

![werr passing](https://github.com/user-attachments/assets/b7b46341-6751-49d2-b00f-05885cce2973){width="50%"}

A task is a configured sequence of commands to run.

```toml
[project]
name = "appletree"
version = "0.1.0"
dependencies = [
    "pysunlight==24.1",
]

[tool.werr]
variable.src = "src tests"

# The first task is the default when `werr` is run with no arguments.
task.check = [
    {parallel = true},  # optional config: run commands in parallel
    "ruff check {src}",
    "ruff format --check {src}",
    "mypy {src}",
    "pytest",
]
task.fix = [
    "ruff check --fix {src}",
    "ruff format {src}",
]
```

Running `werr` executes each `check` command in sequence (or parallel if configured), printing which failed and how.
The tool returns a non-zero exit code if any command fails.

Running `werr fix` executes each `fix` command in sequence.

NOTE: All commands are run using `uv` (the only dependency of this project).

## Guides
<!-- Guide for common user patterns -->

### Setting up a new project

### Linting a project

### Fixing linting issues

## Reference
<!-- Complete documentation of all config/CLIs -->

### Config

All werr configuration lives in your `pyproject.toml` under `[tool.werr]`.

#### Tasks

```toml
task.<name> = ["command1", "command2", ...]
```

Define a named task as a list of commands to run. The **first task** defined is the default when running `werr` without arguments.

Each command string is split into an argument list (using shell-style tokenization) and executed directly. For example, `"ruff check src"` becomes `["ruff", "check", "src"]`.

```toml
[tool.werr]
task.check = ["ruff check src", "pytest"]  # default task (first)
task.fix = ["ruff check --fix src"]
```

#### Task Options

Each task can have an optional config dict as its **first element** to set task-specific options:

```toml
task.<name> = [
    {parallel = true},  # optional config dict as first list element
    "command1",
    "command2",
]
```

Available options:

| Option | Values | Default | Description |
|--------|--------|---------|-------------|
| `parallel` | `true` / `false` | `false` | Run commands in parallel |
| `live` | `true` / `false` | `false` | Stream command output directly to the console (no results summary) |
| `shell` | `true` / `false` | `false` | Wrap commands in `bash -c` for shell features (pipes, globbing, etc.) |

Example with different configs per task:

```toml
[tool.werr]
task.check = [
    {parallel = true},
    "ruff check src",
    "pytest",
]
task.ci = [
    {live = true},
    "pytest -v",
]
task.report = [
    {shell = true},
    "pytest | tee results.txt",
]
task.fix = [
    "ruff check --fix src",
]
```

CLI arguments always override task config (e.g. `--json`, `--xml`, `-x`).

#### Variables

```toml
variable.<name> = "value"
```

Define custom variables for use in commands with `{name}` syntax.

```toml
[tool.werr]
variable.src = "src"
variable.tests = "tests"
task.check = ["ruff check {src}", "pytest {tests}"]
```

Unknown variables are preserved as-is (not substituted).

### CLI

```
werr [options] [task]
```

| Option | Description |
|--------|-------------|
| `task` | Task to run (defaults to first task in config) |
| `-v`, `--verbose` | Enable verbose logging |
| `-l`, `--list` | List available tasks and exit (combines with `--json`) |
| `-x`, `--execute-parallel` | Run task commands in parallel |
| `-p`, `--project PATH` | Python project directory (defaults to cwd) |
| `-n`, `--name NAME` | Name of command to filter by (runs single tool) |
| `--cli` | Print results to the console (default) |
| `--live` | Print command output to the console (no results) |
| `--xml` | Print results as Junit XML |
| `--json` | Print results as lines of JSON |

### Examples
