<img align="left" width="80" height="80" src="https://openmoji.org/data/color/svg/2699.svg" alt="gear">

# werr <!-- replace with svg -->

<div align="center">

[![werr](https://img.shields.io/badge/src-werr-purple?logo=github)](https://github.com/jhjn/werr)
[![version](https://img.shields.io/pypi/v/werr.svg)](https://pypi.python.org/pypi/werr)
[![license](https://img.shields.io/pypi/l/werr.svg)](https://pypi.python.org/pypi/werr)
[![python](https://img.shields.io/pypi/pyversions/werr.svg)](https://pypi.python.org/pypi/werr)

<!--
[![testing](https://github.com/jhjn/werr/actions/workflows/ci.yml/badge.svg)](https://github.com/jhjn/werr/actions)
[![downloads](https://img.shields.io/pypi/dm/werr.svg)](https://pypistats.org/packages/werr)
-->

</div>

**A simple, opinionated, python project task runner.**

<!--add image of werr in action here (with pytest too) -->

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

## Command Variables

The following `{...}` variables are provided by `werr` to be used in task commands:

- `{project}` - the absolute path to the directory containing the `pyproject.toml` file

## Structured Output

```bash
werr         # interactive human readable output (default)
werr --json  # emit lines of JSON representing the result of each command
werr --xml   # print Junit XML for CI
```

## Custom Tasks

Define a custom task with `task.<name> = [ ... ]`

```toml
[tool.werr]
# ...
task.docs = [
    "sphinx-build -b html {project}",
]
```

Running `werr docs` will build the documentation.

## New Project

A suggested workflow for creating a new project is:

1. `uv init`
2. `uv add --dev black ruff ty pytest`
3. add tasks to `[tool.werr]`
4. `uvx werr` or add to `dev` group and in venv just `werr`
