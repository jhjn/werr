"""Test werr configuration parsing."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from werrlib import cmd, config


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

    name, commands = config.load_project(pyproject, "check")

    assert name == "testproject"
    assert commands == [cmd.Command("ruff check ."), cmd.Command("pytest")]


def test_load_project_single_command(tmp_path: Path) -> None:
    """Load a task with a single command."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "myapp"

[tool.werr]
task.lint = ["black --check ."]
"""
    )

    name, commands = config.load_project(pyproject, "lint")

    assert name == "myapp"
    assert len(commands) == 1
    assert commands[0].command == "black --check ."
    assert commands[0].name == "black"


def test_load_project_missing_file(tmp_path: Path) -> None:
    """Raise error when pyproject.toml doesn't exist."""
    pyproject = tmp_path / "pyproject.toml"

    with pytest.raises(ValueError, match=r"does not contain a `pyproject.toml`"):
        config.load_project(pyproject, "check")


def test_load_project_missing_tool_section(tmp_path: Path) -> None:
    """Raise error when [tool.werr] section is missing."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"
"""
    )

    with pytest.raises(ValueError, match=r"does not contain a \[tool.werr\] section"):
        config.load_project(pyproject, "check")


def test_load_project_missing_werr_section(tmp_path: Path) -> None:
    """Raise error when [tool.werr] is missing but [tool] exists."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.other]
something = true
"""
    )

    with pytest.raises(ValueError, match=r"does not contain a \[tool.werr\] section"):
        config.load_project(pyproject, "check")


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
        config.load_project(pyproject, "check")


def test_load_project_empty_task_section(tmp_path: Path) -> None:
    """Raise error when task section exists but requested task is missing."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.lint = ["ruff"]
task.test = ["pytest"]
"""
    )

    with pytest.raises(ValueError, match=r"does not contain a `task.deploy` list"):
        config.load_project(pyproject, "deploy")
