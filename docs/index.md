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
# 'check' is the default task if `werr` is run with no arguments.
task.check = [
    "black --check {project}",
    "isort --check {project}",
    "ruff check {project}",
    "mypy {project}",
    "pytest",
]
task.fix = [
    "black {project}",
    "isort {project}",
    "ruff fix {project}",
]
```

Running `werr` executes each `check` command in sequence, printing which failed and how.
The tool returns a non-zero exit code if any command fails.

Running `werr fix` executes each `fix` command in sequence.

NOTE: All commands are run using `uv` (the only dependency of this project).

## Guide
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

Define a named task as a list of commands to run in sequence. The task name `task` is reserved and cannot be used.

```toml
[tool.werr]
task.check = ["ruff check {project}", "pytest"]
task.fix = ["ruff check --fix {project}"]
```

#### Variables

```toml
variable.<name> = "value"
```

Define custom variables for use in commands with `{name}` syntax. Variables can reference other variables and the built-in `{project}` variable (the absolute path to the project directory).

```toml
[tool.werr]
variable.src = "{project}/src"
variable.tests = "{project}/tests"
task.check = ["ruff check {src}", "pytest {tests}"]
```

Variables are resolved in order, so later variables can reference earlier ones:

```toml
[tool.werr]
variable.base = "src"
variable.app = "{base}/myapp"
task.check = ["ruff check {app}"]  # resolves to "ruff check src/myapp"
```

Unknown variables are preserved as-is (not substituted).

#### Defaults

```toml
default.task = "<task-name>"
default.<task>.reporter = "cli" | "json" | "xml"
default.<task>.parallel = true | false
```

Configure default behavior to reduce CLI arguments needed.

- `default.task` - the task to run when no task is specified (default: `"check"`)
- `default.<task>.reporter` - output format for a specific task (default: `"cli"`)
- `default.<task>.parallel` - whether to run commands in parallel (default: `false`)

```toml
[tool.werr]
default.task = "check"
default.check.reporter = "cli"
default.check.parallel = true
default.ci.reporter = "xml"
```

CLI arguments always override config defaults (e.g. `--json`, `--xml`, `-x`).

### CLI

### Examples
