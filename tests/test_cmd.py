"""Test command execution classes."""

from __future__ import annotations

from werrlib.cmd import Command, Result

# --- Command tests ---


def test_command_name_simple() -> None:
    """Command name is first word."""
    assert Command("pytest").name == "pytest"


def test_command_name_with_args() -> None:
    """Command name extracts first word from command with args."""
    assert Command("ruff check src/").name == "ruff"


def test_command_name_with_path() -> None:
    """Command name handles paths."""
    assert Command("python -m pytest tests/").name == "python"


# --- Result tests ---


def test_result_success_zero_returncode() -> None:
    """Result is successful with returncode 0."""
    result = Result(Command("test"), returncode=0, duration=1.0, output="")
    assert result.success is True


def test_result_failure_nonzero_returncode() -> None:
    """Result is failure with non-zero returncode."""
    result = Result(Command("test"), returncode=1, duration=1.0, output="error")
    assert result.success is False


def test_result_failure_negative_returncode() -> None:
    """Result is failure with negative returncode (signal)."""
    result = Result(Command("test"), returncode=-9, duration=0.5, output="")
    assert result.success is False
