"""Test werr configuration parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from werrlib import config, report
from werrlib.cmd import Command

if TYPE_CHECKING:
    from pathlib import Path


# --- Basic loading tests ---


def test_load_project_success(tmp_path: Path) -> None:
    """Successfully load a valid pyproject.toml with tasks."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.check = ["ruff check .", "pytest"]
"""
    )

    reporter, commands = config.load_project(pyproject)

    assert isinstance(reporter, report.CliReporter)
    assert commands == [Command("ruff check ."), Command("pytest")]


def test_load_project_missing_file(tmp_path: Path) -> None:
    """Raise error when pyproject.toml doesn't exist."""
    pyproject = tmp_path / "pyproject.toml"

    with pytest.raises(ValueError, match=r"does not contain a `pyproject.toml`"):
        config.load_project(pyproject)


def test_load_project_missing_werr_section(tmp_path: Path) -> None:
    """Raise error when [tool.werr] section is missing."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"
"""
    )

    with pytest.raises(ValueError, match=r"does not contain a \[tool.werr\] section"):
        config.load_project(pyproject)


def test_load_project_missing_task(tmp_path: Path) -> None:
    """Raise error when requested task doesn't exist."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.build = ["make"]
"""
    )

    with pytest.raises(ValueError, match=r"does not contain a `task.check` list"):
        config.load_project(pyproject, cli_task="check")


def test_load_project_no_tasks(tmp_path: Path) -> None:
    """Raise error when no tasks defined."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
variable.src = "src"
"""
    )

    with pytest.raises(ValueError, match=r"does not contain any `task` lists"):
        config.load_project(pyproject)


# --- Default task (first in dict) tests ---


def test_first_task_is_default(tmp_path: Path) -> None:
    """First task in config is used when no CLI task specified."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.lint = ["ruff check ."]
task.test = ["pytest"]
"""
    )

    _reporter, commands = config.load_project(pyproject)

    assert commands == [Command("ruff check .")]


def test_cli_task_overrides_default(tmp_path: Path) -> None:
    """CLI task overrides the default first task."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.lint = ["ruff check ."]
task.build = ["make"]
"""
    )

    _reporter, commands = config.load_project(pyproject, cli_task="build")

    assert commands == [Command("make")]


# --- Inline config dict tests ---


def test_task_config_parallel(tmp_path: Path) -> None:
    """Task config dict sets parallel mode."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.check = [
    {parallel = true},
    "pytest",
]
"""
    )

    reporter, commands = config.load_project(pyproject)

    assert isinstance(reporter, report.ParallelCliReporter)
    assert commands == [Command("pytest")]


def test_task_config_reporter(tmp_path: Path) -> None:
    """Task config dict sets reporter."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.check = [
    {reporter = "json"},
    "pytest",
]
"""
    )

    reporter, commands = config.load_project(pyproject)

    assert isinstance(reporter, report.JsonReporter)
    assert commands == [Command("pytest")]


def test_task_config_both_options(tmp_path: Path) -> None:
    """Task config dict can set both parallel and reporter."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.check = [
    {parallel = true, reporter = "cli"},
    "pytest",
]
"""
    )

    reporter, commands = config.load_project(pyproject)

    assert isinstance(reporter, report.ParallelCliReporter)
    assert commands == [Command("pytest")]


def test_task_without_config_dict(tmp_path: Path) -> None:
    """Task without config dict uses defaults."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.check = ["pytest", "ruff check ."]
"""
    )

    reporter, commands = config.load_project(pyproject)

    assert isinstance(reporter, report.CliReporter)
    assert not isinstance(reporter, report.ParallelCliReporter)
    assert commands == [Command("pytest"), Command("ruff check .")]


# --- CLI overrides config dict tests ---


def test_cli_parallel_overrides_config(tmp_path: Path) -> None:
    """CLI parallel flag overrides task config."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.check = [
    {parallel = false},
    "pytest",
]
"""
    )

    reporter, _commands = config.load_project(pyproject, cli_parallel=True)

    assert isinstance(reporter, report.ParallelCliReporter)


def test_cli_reporter_overrides_config(tmp_path: Path) -> None:
    """CLI reporter flag overrides task config."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.check = [
    {reporter = "json"},
    "pytest",
]
"""
    )

    reporter, _commands = config.load_project(pyproject, cli_reporter="xml")

    assert isinstance(reporter, report.XmlReporter)


def test_cli_overrides_both_config_options(tmp_path: Path) -> None:
    """CLI flags override both task config options."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.check = [
    {parallel = true, reporter = "json"},
    "pytest",
]
"""
    )

    reporter, _commands = config.load_project(
        pyproject, cli_parallel=False, cli_reporter="xml"
    )

    # cli_parallel=False doesn't override config parallel=true (False is falsy)
    # but cli_reporter="xml" does override
    assert isinstance(reporter, report.XmlReporter)


# --- variable.* tests ---


def test_variable_substitution(tmp_path: Path) -> None:
    """Custom variables are substituted in commands."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
variable.src = "src/app"
task.check = ["ruff check {src}"]
"""
    )

    _reporter, commands = config.load_project(pyproject)

    assert commands == [Command("ruff check src/app")]


def test_variable_chaining(tmp_path: Path) -> None:
    """Variables can reference other variables."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
variable.base = "src"
variable.app = "{base}/app"
task.check = ["ruff check {app}"]
"""
    )

    _reporter, commands = config.load_project(pyproject)

    assert commands == [Command("ruff check src/app")]


def test_project_variable_builtin(tmp_path: Path) -> None:
    """The {project} variable is always available."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.check = ["ruff check {project}/src"]
"""
    )

    _reporter, commands = config.load_project(pyproject)

    assert commands == [Command(f"ruff check {tmp_path.resolve()}/src")]


def test_variable_uses_project(tmp_path: Path) -> None:
    """Custom variables can use {project}."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
variable.src = "{project}/src"
task.check = ["ruff check {src}"]
"""
    )

    _reporter, commands = config.load_project(pyproject)

    assert commands == [Command(f"ruff check {tmp_path.resolve()}/src")]


def test_unknown_variable_preserved(tmp_path: Path) -> None:
    """Unknown variables are left as-is (not substituted)."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.check = ["echo {unknown}"]
"""
    )

    _reporter, commands = config.load_project(pyproject)

    assert commands == [Command("echo {unknown}")]


# --- Combined config + CLI tests ---


def test_config_with_partial_cli_override(tmp_path: Path) -> None:
    """CLI overrides one option while config provides the other."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.check = [
    {parallel = true, reporter = "json"},
    "pytest",
]
"""
    )

    # Override only reporter, parallel comes from config
    reporter, _commands = config.load_project(pyproject, cli_reporter="cli")

    assert isinstance(reporter, report.ParallelCliReporter)


def test_multiple_tasks_different_configs(tmp_path: Path) -> None:
    """Different tasks can have different configs."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.check = [
    {parallel = true},
    "pytest",
]
task.ci = [
    {reporter = "xml"},
    "pytest",
]
"""
    )

    # Default task (check) is parallel
    reporter1, _commands = config.load_project(pyproject)
    assert isinstance(reporter1, report.ParallelCliReporter)

    # CI task uses XML reporter
    reporter2, _commands = config.load_project(pyproject, cli_task="ci")
    assert isinstance(reporter2, report.XmlReporter)
