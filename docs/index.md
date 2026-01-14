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

`task.<task> = [...]`

`variable.<variable> = "..."`

`default.task = "..."`
`default.<task>.reporter` the options are `cli`, `live`, `xml` and `json`
`default.<task>.parallel = false`

Change the `werr` defaults on a per-task basis to reduce the options required on the CLI.

This is the implicit config:

```toml
[tool.werr]
default.task = "check"
default.check.reporter = "cli"
default.check.parallel = false
```

Note that whatever the config says is overriden by the CLI (e.g. using `--live` or `--execute-parallel` or `fix`).

### CLI

### Examples
