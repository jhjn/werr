"""Test reporter classes."""

from __future__ import annotations

import json

import pytest

from werrlib import report
from werrlib.cmd import Command, Result


def _make_result(name: str, *, success: bool = True, output: str = "") -> Result:
    """Create a Result for testing."""
    return Result(
        Command([name]), returncode=0 if success else 1, duration=0.5, output=output
    )


# --- get_reporter tests ---


def test_get_reporter_cli() -> None:
    """Get CLI reporter."""
    r = report.get_reporter("cli")
    assert isinstance(r, report.CliReporter)


def test_get_reporter_json() -> None:
    """Get JSON reporter."""
    r = report.get_reporter("json")
    assert isinstance(r, report.JsonReporter)


def test_get_reporter_xml() -> None:
    """Get XML reporter."""
    r = report.get_reporter("xml")
    assert isinstance(r, report.XmlReporter)


def test_get_reporter_live() -> None:
    """Get live reporter."""
    r = report.get_reporter("live")
    assert isinstance(r, report.LiveReporter)


def test_get_reporter_unknown_raises() -> None:
    """Unknown reporter name raises."""
    with pytest.raises(ValueError, match="Unknown reporter"):
        report.get_reporter(
            "invalid",  # ty: ignore[invalid-argument-type]
        )


# --- Reporter attributes ---


def test_cli_reporter_captures_output() -> None:
    """CLI reporter captures output."""
    assert report.CliReporter.capture_output is True


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
