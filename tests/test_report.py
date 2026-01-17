"""Test reporter classes."""

from __future__ import annotations

import json

import pytest

from werrlib import report
from werrlib.cmd import Command, Result


def _make_result(name: str, *, success: bool = True, output: str = "") -> Result:
    """Create a Result for testing."""
    return Result(
        Command(name), returncode=0 if success else 1, duration=0.5, output=output
    )


# --- get_reporter tests ---


def test_get_reporter_cli_serial() -> None:
    """Get CLI reporter in serial mode."""
    cls = report.get_reporter("cli", parallel=False)
    assert cls is report.CliReporter


def test_get_reporter_cli_parallel() -> None:
    """Get CLI reporter in parallel mode."""
    cls = report.get_reporter("cli", parallel=True)
    assert cls is report.ParallelCliReporter


def test_get_reporter_json_serial() -> None:
    """Get JSON reporter in serial mode."""
    cls = report.get_reporter("json", parallel=False)
    assert cls is report.JsonReporter


def test_get_reporter_json_parallel() -> None:
    """Get JSON reporter in parallel mode."""
    cls = report.get_reporter("json", parallel=True)
    assert cls is report.ParallelJsonReporter


def test_get_reporter_xml_serial() -> None:
    """Get XML reporter in serial mode."""
    cls = report.get_reporter("xml", parallel=False)
    assert cls is report.XmlReporter


def test_get_reporter_live_serial() -> None:
    """Get live reporter in serial mode."""
    cls = report.get_reporter("live", parallel=False)
    assert cls is report.LiveReporter


def test_get_reporter_live_parallel_raises() -> None:
    """Live reporter cannot be used in parallel mode."""
    with pytest.raises(ValueError, match="cannot be used in parallel"):
        report.get_reporter("live", parallel=True)


def test_get_reporter_unknown_raises() -> None:
    """Unknown reporter name raises."""
    with pytest.raises(ValueError, match="Unknown reporter"):
        report.get_reporter("invalid", parallel=False)


# --- Reporter attributes ---


def test_cli_reporter_captures_output() -> None:
    """CLI reporter captures output."""
    assert report.CliReporter.capture_output is True
    assert report.CliReporter.parallel_cmds is False


def test_parallel_cli_reporter_parallel_flag() -> None:
    """Parallel CLI reporter has parallel_cmds=True."""
    assert report.ParallelCliReporter.parallel_cmds is True


def test_live_reporter_no_capture() -> None:
    """Live reporter does not capture output."""
    assert report.LiveReporter.capture_output is False


# --- JSON reporter output ---


def test_json_reporter_emit_end(capsys: pytest.CaptureFixture[str]) -> None:
    """JSON reporter emits valid JSON on emit_end."""
    reporter = report.JsonReporter()
    result = _make_result("pytest", success=True, output="test output")

    reporter.emit_end(result)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["name"] == "pytest"
    assert data["success"] is True
    assert data["output"] == "test output"
    assert "duration" in data


def test_json_reporter_strips_ansi(capsys: pytest.CaptureFixture[str]) -> None:
    """JSON reporter strips ANSI codes from output."""
    reporter = report.JsonReporter()
    result = _make_result("test", output="\033[31mred\033[0m")

    reporter.emit_end(result)

    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["output"] == "red"


# --- XML reporter output ---


def test_xml_reporter_emit_summary(capsys: pytest.CaptureFixture[str]) -> None:
    """XML reporter emits valid XML summary."""
    reporter = report.XmlReporter()
    results = [_make_result("pytest", success=True)]

    reporter.emit_summary(results)

    captured = capsys.readouterr()
    assert "<?xml version=" in captured.out
    assert "<testsuites" in captured.out
    assert "<testsuite" in captured.out
    assert 'name="pytest"' in captured.out


def test_xml_reporter_includes_failures(capsys: pytest.CaptureFixture[str]) -> None:
    """XML reporter includes failure elements for failed tests."""
    reporter = report.XmlReporter()
    results = [_make_result("ruff", success=False, output="error message")]

    reporter.emit_summary(results)

    captured = capsys.readouterr()
    assert "<failure" in captured.out
    assert "error message" in captured.out
