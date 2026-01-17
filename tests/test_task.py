"""Test task orchestration."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest

from werrlib import task
from werrlib.cmd import Command, Result

if TYPE_CHECKING:
    from pathlib import Path


def _mock_reporter(*, parallel: bool = False) -> MagicMock:
    """Create a mock reporter."""
    reporter = MagicMock(spec=["emit_info", "emit_start", "emit_end", "emit_summary"])
    reporter.parallel_cmds = parallel
    reporter.capture_output = True
    return reporter


def _make_result(cmd: Command, *, success: bool = True) -> Result:
    """Create a Result for testing."""
    return Result(cmd, returncode=0 if success else 1, duration=0.1, output="")


# --- Serial run tests ---


def test_run_serial_all_pass(tmp_path: Path) -> None:
    """Serial run returns True when all commands pass."""
    cmds = [Command("cmd1"), Command("cmd2")]
    reporter = _mock_reporter()

    with patch.object(Command, "run") as mock_run:
        mock_run.side_effect = [_make_result(c) for c in cmds]
        result = task.run(tmp_path, reporter, cmds)

    assert result is True
    assert reporter.emit_start.call_count == len(cmds)
    assert reporter.emit_end.call_count == len(cmds)
    reporter.emit_summary.assert_called_once()


def test_run_serial_one_fails(tmp_path: Path) -> None:
    """Serial run returns False when any command fails."""
    cmds = [Command("cmd1"), Command("cmd2")]
    reporter = _mock_reporter()

    with patch.object(Command, "run") as mock_run:
        mock_run.side_effect = [
            _make_result(cmds[0], success=True),
            _make_result(cmds[1], success=False),
        ]
        result = task.run(tmp_path, reporter, cmds)

    assert result is False


def test_run_serial_continues_after_failure(tmp_path: Path) -> None:
    """Serial run continues executing after a failure."""
    cmds = [Command("cmd1"), Command("cmd2"), Command("cmd3")]
    reporter = _mock_reporter()

    with patch.object(Command, "run") as mock_run:
        mock_run.side_effect = [
            _make_result(cmds[0], success=False),
            _make_result(cmds[1], success=True),
            _make_result(cmds[2], success=True),
        ]
        task.run(tmp_path, reporter, cmds)

    assert mock_run.call_count == len(cmds)


# --- Parallel run tests ---


def test_run_parallel_dispatches_to_parallel(tmp_path: Path) -> None:
    """Run dispatches to run_parallel when reporter.parallel_cmds is True."""
    cmds = [Command("cmd1")]
    reporter = _mock_reporter(parallel=True)

    with patch.object(task, "run_parallel", return_value=True) as mock_parallel:
        task.run(tmp_path, reporter, cmds)

    mock_parallel.assert_called_once_with(tmp_path, reporter, cmds)


# --- Name filter tests ---


def test_filter_by_name_prefix(tmp_path: Path) -> None:
    """Name filter selects commands matching prefix."""
    cmds = [Command("pytest tests/"), Command("ruff check")]
    reporter = _mock_reporter()

    with patch.object(Command, "run") as mock_run:
        mock_run.return_value = _make_result(cmds[0])
        task.run(tmp_path, reporter, cmds, name_filter="py")

    assert mock_run.call_count == 1


def test_filter_no_match_raises(tmp_path: Path) -> None:
    """Name filter raises when no commands match."""
    cmds = [Command("pytest"), Command("ruff check")]
    reporter = _mock_reporter()

    with pytest.raises(ValueError, match="No commands match"):
        task.run(tmp_path, reporter, cmds, name_filter="black")
