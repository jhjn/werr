"""Test werr configuration parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from werrlib import config, report
from werrlib.cmd import Command

if TYPE_CHECKING:
    from pathlib import Path


# --- Config class tests ---


def test_config_load(tmp_path: Path) -> None:
    """Config.load() parses a pyproject.toml file."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"')

    cfg = config.Config.load(pyproject)

    assert cfg.path == pyproject
    assert cfg.get("project.name") == "test"


def test_config_load_missing_file(tmp_path: Path) -> None:
    """Config.load() raises for missing file."""
    pyproject = tmp_path / "pyproject.toml"

    with pytest.raises(ValueError, match=r"does not contain a `pyproject.toml`"):
        config.Config.load(pyproject)


def test_config_get_nested(tmp_path: Path) -> None:
    """Config.get() accesses nested keys with dot notation."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.werr]\ntask.check = ["pytest"]')

    cfg = config.Config.load(pyproject)

    assert cfg.get("tool.werr.task.check") == ["pytest"]


def test_config_get_missing_returns_none(tmp_path: Path) -> None:
    """Config.get() returns None for missing keys."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"')

    cfg = config.Config.load(pyproject)

    assert cfg.get("nonexistent.key") is None


def test_config_werr_property(tmp_path: Path) -> None:
    """Config.werr returns a Config scoped to [tool.werr]."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[tool.werr]\ntask.check = ["pytest"]')

    cfg = config.Config.load(pyproject)

    assert cfg.werr.get("task.check") == ["pytest"]


def test_config_werr_missing_raises(tmp_path: Path) -> None:
    """Config.werr raises when [tool.werr] is missing."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"')

    cfg = config.Config.load(pyproject)

    with pytest.raises(ValueError, match=r"\[tool.werr\] section not found"):
        _ = cfg.werr


# --- load() tests ---


def test_load_returns_all_tasks(tmp_path: Path) -> None:
    """load() returns a list of all configured tasks."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = ["pytest"]
task.lint = ["ruff check ."]
"""
    )

    tasks = config.load(pyproject)

    assert [t.name for t in tasks] == ["check", "lint"]


def test_load_dashname_for_duplicate_command_names(tmp_path: Path) -> None:
    """Commands sharing a base name get dash-style names; unique ones don't."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = ["ruff check .", "ruff format --check .", "pytest"]
"""
    )

    tasks = config.load(pyproject)

    cmds = tasks[0].commands
    assert cmds[0] == Command(["ruff", "check", "."], use_dashname=True)
    assert cmds[0].name == "ruff-check"
    assert cmds[1] == Command(["ruff", "format", "--check", "."], use_dashname=True)
    assert cmds[1].name == "ruff-format"
    assert cmds[2] == Command(["pytest"], use_dashname=False)
    assert cmds[2].name == "pytest"


def test_load_config_names(tmp_path: Path) -> None:
    """Commands sharing a base name get dash-style names; unique ones don't."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.foo = [
    "ruff check",
    "ruff",
    "ruff format --check .",
]
task.bar = [
    {shell = true},
    "echo hi",
    "echo bye | grep y",
]
"""
    )

    foo, bar = config.load(pyproject)

    assert foo.commands[0].name == "ruff-check"
    assert foo.commands[1].name == "ruff"
    assert foo.commands[2].name == "ruff-format"
    assert bar.commands[0].name == "echo-hi"
    assert bar.commands[1].name == "echo-bye"


def test_load_empty_tasks(tmp_path: Path) -> None:
    """load() returns empty list when no tasks defined."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.werr]")

    tasks = config.load(pyproject)

    assert tasks == []


# --- load_task() basic tests ---


def test_load_task_success(tmp_path: Path) -> None:
    """load_task() returns a Task with commands."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.check = ["ruff check .", "pytest"]
"""
    )

    task = config.load_task(pyproject)

    assert task.name == "check"
    assert isinstance(task.reporter, report.CliReporter)
    assert task.commands == [Command(["ruff", "check", "."]), Command(["pytest"])]


def test_load_task_missing_werr_section(tmp_path: Path) -> None:
    """load_task() raises when [tool.werr] section is missing."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text('[project]\nname = "test"')

    with pytest.raises(ValueError, match=r"\[tool.werr\] section not found"):
        config.load_task(pyproject)


def test_load_task_missing_task(tmp_path: Path) -> None:
    """load_task() raises when requested task doesn't exist."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.build = ["make"]
"""
    )

    with pytest.raises(ValueError, match=r"does not contain a `task.check` list"):
        config.load_task(pyproject, cli_task="check")


def test_load_task_no_tasks(tmp_path: Path) -> None:
    """load_task() raises when no tasks defined."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text("[tool.werr]")

    with pytest.raises(ValueError, match=r"does not contain any `task` lists"):
        config.load_task(pyproject)


# --- Default task (first in dict) tests ---


def test_first_task_is_default(tmp_path: Path) -> None:
    """First task in config is used when no CLI task specified."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.lint = ["ruff check ."]
task.test = ["pytest"]
"""
    )

    task = config.load_task(pyproject)

    assert task.name == "lint"
    assert task.commands == [Command(["ruff", "check", "."])]


def test_cli_task_overrides_default(tmp_path: Path) -> None:
    """CLI task overrides the default first task."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.lint = ["ruff check ."]
task.build = ["make"]
"""
    )

    task = config.load_task(pyproject, cli_task="build")

    assert task.name == "build"
    assert task.commands == [Command(["make"])]


# --- Inline config dict tests ---


def test_task_config_parallel(tmp_path: Path) -> None:
    """Task config dict sets parallel mode."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = [
    {parallel = true},
    "pytest",
]
"""
    )

    task = config.load_task(pyproject)

    assert isinstance(task.reporter, report.CliReporter)
    assert task.parallel is True
    assert task.commands == [Command(["pytest"])]


def test_task_config_live(tmp_path: Path) -> None:
    """Task config dict sets live mode."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = [
    {live = true},
    "pytest",
]
"""
    )

    task = config.load_task(pyproject)

    assert isinstance(task.reporter, report.LiveReporter)
    assert task.commands == [Command(["pytest"])]


def test_task_config_both_options(tmp_path: Path) -> None:
    """Task config dict can set both parallel and live."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = [
    {parallel = true},
    "pytest",
]
"""
    )

    task = config.load_task(pyproject)

    assert isinstance(task.reporter, report.CliReporter)
    assert task.parallel is True
    assert task.commands == [Command(["pytest"])]


def test_task_without_config_dict(tmp_path: Path) -> None:
    """Task without config dict uses defaults."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = ["pytest", "ruff check ."]
"""
    )

    task = config.load_task(pyproject)

    assert isinstance(task.reporter, report.CliReporter)
    assert task.parallel is False
    assert task.commands == [Command(["pytest"]), Command(["ruff", "check", "."])]


# --- shell config dict tests ---


def test_task_config_shell(tmp_path: Path) -> None:
    """shell=true wraps commands in bash -c."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = [
    {shell = true},
    "pytest | tee output.txt",
]
"""
    )

    task = config.load_task(pyproject)

    assert [c.command for c in task.commands] == [
        ["uv", "run", "bash", "-c", "pytest | tee output.txt"]
    ]


def test_task_without_shell(tmp_path: Path) -> None:
    """Default (no shell) splits commands into arg lists."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = ["ruff check ."]
"""
    )

    task = config.load_task(pyproject)

    assert task.commands == [Command(["ruff", "check", "."])]


# --- CLI overrides config dict tests ---


def test_cli_parallel_overrides_config(tmp_path: Path) -> None:
    """CLI parallel flag overrides task config."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = [
    {parallel = false},
    "pytest",
]
"""
    )

    task = config.load_task(pyproject, cli_parallel=True)

    assert isinstance(task.reporter, report.CliReporter)
    assert task.parallel is True


def test_cli_reporter_overrides_default(tmp_path: Path) -> None:
    """CLI reporter flag overrides the default reporter."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = ["pytest"]
"""
    )

    task = config.load_task(pyproject, cli_reporter="xml")

    assert isinstance(task.reporter, report.XmlReporter)


def test_cli_overrides_both_options(tmp_path: Path) -> None:
    """CLI flags override both parallel and reporter."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = ["pytest"]
"""
    )

    task = config.load_task(pyproject, cli_parallel=True, cli_reporter="xml")

    assert isinstance(task.reporter, report.XmlReporter)
    assert task.parallel is True


# --- variable.* tests ---


def test_variable_substitution(tmp_path: Path) -> None:
    """Custom variables are substituted in commands."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
variable.src = "src/app"
task.check = ["ruff check {src}"]
"""
    )

    task = config.load_task(pyproject)

    assert task.commands == [Command(["ruff", "check", "src/app"])]


def test_multiple_variables(tmp_path: Path) -> None:
    """Multiple variables can be used in commands."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
variable.src = "src"
variable.tests = "tests"
task.check = ["ruff check {src} {tests}"]
"""
    )

    task = config.load_task(pyproject)

    assert task.commands == [Command(["ruff", "check", "src", "tests"])]


def test_unknown_variable_preserved(tmp_path: Path) -> None:
    """Unknown variables are left as-is (not substituted)."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = ["echo {unknown}"]
"""
    )

    task = config.load_task(pyproject)

    assert task.commands == [Command(["echo", "{unknown}"])]


# --- Combined config + CLI tests ---


def test_config_with_partial_cli_override(tmp_path: Path) -> None:
    """CLI overrides reporter while config provides parallel."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = [
    {parallel = true},
    "pytest",
]
"""
    )

    task = config.load_task(pyproject, cli_reporter="xml")

    assert isinstance(task.reporter, report.XmlReporter)
    assert task.parallel is True


def test_multiple_tasks_different_configs(tmp_path: Path) -> None:
    """Different tasks can have different configs."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = [
    {parallel = true},
    "pytest",
]
task.ci = [
    {live = true},
    "pytest",
]
"""
    )

    task1 = config.load_task(pyproject)
    assert isinstance(task1.reporter, report.CliReporter)
    assert task1.parallel is True

    task2 = config.load_task(pyproject, cli_task="ci")
    assert isinstance(task2.reporter, report.LiveReporter)


# --- needs tests ---


def test_task_config_needs_string(tmp_path: Path) -> None:
    """{needs = "build"} resolves task.needs to the build Task."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.build = ["make"]
task.test = [
    {needs = "build"},
    "pytest",
]
"""
    )

    tasks = config.load(pyproject)
    test_task = next(t for t in tasks if t.name == "test")

    assert test_task.dependency is not None
    assert test_task.dependency.name == "build"


def test_task_without_needs(tmp_path: Path) -> None:
    """Tasks without needs have None."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.check = ["pytest"]
"""
    )

    tasks = config.load(pyproject)

    assert tasks[0].dependency is None


def test_needs_unknown_task_raises(tmp_path: Path) -> None:
    """Referencing a non-existent task in needs raises."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.test = [
    {needs = "nonexistent"},
    "pytest",
]
"""
    )

    with pytest.raises(ValueError, match=r"needs unknown task `nonexistent`"):
        config.load(pyproject)


def test_needs_cycle_raises(tmp_path: Path) -> None:
    """A needs B, B needs A raises."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.a = [
    {needs = "b"},
    "echo a",
]
task.b = [
    {needs = "a"},
    "echo b",
]
"""
    )

    with pytest.raises(ValueError, match=r"cycle"):
        config.load(pyproject)


def test_needs_self_cycle_raises(tmp_path: Path) -> None:
    """A needs A raises."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[tool.werr]
task.a = [
    {needs = "a"},
    "echo a",
]
"""
    )

    with pytest.raises(ValueError, match=r"cycle"):
        config.load(pyproject)


def test_load_task_preserves_needs(tmp_path: Path) -> None:
    """load_task() propagates needs on the selected task."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.build = ["make"]
task.test = [
    {needs = "build"},
    "pytest",
]
"""
    )

    task = config.load_task(pyproject, cli_task="test")

    assert task.dependency is not None
    assert task.dependency.name == "build"
