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
        config.load_project(pyproject)


def test_task_named_task_forbidden(tmp_path: Path) -> None:
    """Raise error when task is named 'task' (reserved name)."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.task = ["echo hello"]
"""
    )

    with pytest.raises(ValueError, match=r"cannot be named 'task'"):
        config.load_project(pyproject, cli_task="task")


# --- default.* tests ---


def test_default_task(tmp_path: Path) -> None:
    """Use default.task when no CLI task specified."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
default.task = "lint"
task.lint = ["ruff check ."]
task.check = ["pytest"]
"""
    )

    _reporter, commands = config.load_project(pyproject)

    assert commands == [Command("ruff check .")]


def test_default_task_overridden_by_cli(tmp_path: Path) -> None:
    """CLI task overrides default.task."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
default.task = "lint"
task.lint = ["ruff check ."]
task.build = ["make"]
"""
    )

    _reporter, commands = config.load_project(pyproject, cli_task="build")

    assert commands == [Command("make")]


def test_default_reporter(tmp_path: Path) -> None:
    """Use default.<task>.reporter when no CLI reporter specified."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
default.check.reporter = "json"
task.check = ["pytest"]
"""
    )

    reporter, _commands = config.load_project(pyproject)

    assert isinstance(reporter, report.JsonReporter)


def test_default_reporter_overridden_by_cli(tmp_path: Path) -> None:
    """CLI reporter overrides default.<task>.reporter."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
default.check.reporter = "json"
task.check = ["pytest"]
"""
    )

    reporter, _commands = config.load_project(pyproject, cli_reporter="xml")

    assert isinstance(reporter, report.XmlReporter)


def test_default_parallel(tmp_path: Path) -> None:
    """Use default.<task>.parallel when no CLI parallel specified."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
default.check.parallel = true
task.check = ["pytest"]
"""
    )

    reporter, _commands = config.load_project(pyproject)

    assert isinstance(reporter, report.ParallelCliReporter)


def test_default_parallel_overridden_by_cli(tmp_path: Path) -> None:
    """CLI parallel overrides default.<task>.parallel."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
default.check.parallel = false
task.check = ["pytest"]
"""
    )

    reporter, _commands = config.load_project(pyproject, cli_parallel=True)

    assert isinstance(reporter, report.ParallelCliReporter)


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


# --- Combined defaults + CLI override tests ---


def test_combined_defaults_no_cli_override(tmp_path: Path) -> None:
    """Config sets both parallel and reporter; no CLI overrides."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
default.check.parallel = true
default.check.reporter = "json"
task.check = ["pytest"]
"""
    )

    # No CLI args - should get parallel JSON reporter
    reporter, _commands = config.load_project(pyproject)

    # ParallelCliReporter is used even with json because parallel=true
    # but json doesn't have a parallel variant, so it falls back
    assert isinstance(reporter, (report.JsonReporter, report.ParallelCliReporter))


def test_combined_defaults_cli_overrides_both(tmp_path: Path) -> None:
    """Config sets both parallel and reporter; CLI overrides both."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
default.check.parallel = true
default.check.reporter = "json"
task.check = ["pytest"]
"""
    )

    # CLI overrides: parallel=False, reporter=xml
    reporter, _commands = config.load_project(
        pyproject, cli_parallel=False, cli_reporter="xml"
    )

    # Should get serial XML reporter (CLI wins)
    assert isinstance(reporter, report.XmlReporter)
    assert not isinstance(reporter, report.ParallelCliReporter)


def test_combined_defaults_cli_overrides_reporter_only(tmp_path: Path) -> None:
    """Config sets both parallel and reporter; CLI overrides only reporter."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
default.check.parallel = true
default.check.reporter = "json"
task.check = ["pytest"]
"""
    )

    # CLI overrides reporter only; parallel comes from config (true)
    reporter, _commands = config.load_project(pyproject, cli_reporter="cli")

    # Should get parallel CLI reporter
    assert isinstance(reporter, report.ParallelCliReporter)


def test_combined_defaults_cli_overrides_parallel_only(tmp_path: Path) -> None:
    """Config sets both parallel and reporter; CLI overrides only parallel."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
default.check.parallel = false
default.check.reporter = "cli"
task.check = ["pytest"]
"""
    )

    # CLI overrides parallel only; reporter comes from config (cli)
    reporter, _commands = config.load_project(pyproject, cli_parallel=True)

    # Should get parallel CLI reporter
    assert isinstance(reporter, report.ParallelCliReporter)
