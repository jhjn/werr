"""Manage the recording and reporting of tasks."""

from __future__ import annotations

import json
import logging
import re
import sys
import textwrap
import time
from _colorize import ANSIColors as C  # ty: ignore[unresolved-import]
from abc import ABC, abstractmethod
from typing import ClassVar

from . import cmd, xml

log = logging.getLogger("report")
ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


_SUITENAME = "werr"
_TOTAL_HEAD_LEN = 25
_HEAD_PFX = "      "


class Reporter(ABC):
    """A reporter for reporting the results of a task."""

    @staticmethod
    @abstractmethod
    def emit_info(msg: str) -> None:
        """Print a message for an interactive reader."""

    @staticmethod
    @abstractmethod
    def emit_start(cmd: cmd.Command) -> None:
        """What is printed before a command begins."""

    @staticmethod
    @abstractmethod
    def emit_end(result: cmd.Result) -> None:
        """What is printed after a command completes."""

    @staticmethod
    @abstractmethod
    def emit_summary(results: list[cmd.Result]) -> None:
        """What is printed after the task has completed."""


class CliReporter(Reporter):
    """A reporter for reporting the results of a task to the console."""

    start_time: float | None = None
    task_index = 0

    @staticmethod
    def _duration() -> float:
        assert CliReporter.start_time, "must have start set before duration()"
        return time.monotonic() - CliReporter.start_time

    @staticmethod
    def emit_info(msg: str) -> None:
        """Print to console."""
        print(msg)

    @staticmethod
    def emit_start(cmd: cmd.Command) -> None:
        """Emit the start of a command."""
        if CliReporter.start_time is None:
            CliReporter.start_time = time.monotonic()

        prefix = f"[{CliReporter.task_index+1}]"
        print(f"{prefix:<5} {cmd.name:<20} ", end="", flush=True)
        CliReporter.task_index += 1

    @staticmethod
    def emit_end(result: cmd.Result) -> None:
        """Emit the end of a command."""
        if result.success:
            status = f"{C.GREEN}PASSED{C.RESET}"
        else:
            status = f"{C.RED}FAILED{C.RESET}"

        print(f"({result.duration:>2.2f} secs) {status:>18}", flush=True)

    @staticmethod
    def emit_summary(results: list[cmd.Result]) -> None:
        """Print the summary line explaining what the net result was."""
        successes = [result for result in results if result.success]
        failures = [result for result in results if not result.success]

        msg = (
            f"Ran {len(results)} check{_plural(len(results))} in "
            f"{CliReporter._duration():>2.2f} secs, "
            f"{len(successes)} Passed, {len(failures)} Failed"
        )
        print(f"{C.RED if failures else C.GREEN}{msg}{C.RESET}")

        if failures:
            print("\nFailures:\n---------")
            for result in failures:
                CliReporter.emit_start(result.cmd)
                print()
                print(textwrap.indent(result.output, _HEAD_PFX))


class ParallelCliReporter(CliReporter):
    """An interactive reporter with live display updating in place."""

    _process_lines: ClassVar[dict[str, int]] = {}  # cmd -> line index from bottom
    _total_lines: ClassVar[int] = 0

    @staticmethod
    def emit_start(cmd: cmd.Command) -> None:
        """Print the command with running status."""
        if CliReporter.start_time is None:
            CliReporter.start_time = time.monotonic()

        CliReporter.task_index += 1
        print(f"  {C.YELLOW}o{C.RESET} {cmd.name}", flush=True)
        ParallelCliReporter._total_lines += 1
        # Store line position (1 = last line printed, 2 = second to last, etc.)
        ParallelCliReporter._process_lines[cmd.command] = 1
        # Shift all previous entries up by one
        for key in ParallelCliReporter._process_lines:
            if key != cmd.command:
                ParallelCliReporter._process_lines[key] += 1

    @staticmethod
    def emit_end(result: cmd.Result) -> None:
        """Move cursor back and update the command's status."""
        line_offset = ParallelCliReporter._process_lines.get(result.cmd.command, 0)

        if line_offset and sys.stdout.isatty():
            # Move cursor up to the correct line
            print(f"\033[{line_offset}A", end="")
            # Move to start of line and clear it
            print("\r\033[K", end="")

        # Print updated status
        if result.success:
            icon, color = "+", C.GREEN
        else:
            icon, color = "x", C.RED
        dur = f"{C.CYAN}({result.duration:.2f}s){C.RESET}"
        status = f"  {color}{icon}{C.RESET} {result.cmd.name:<20} {dur}"

        if line_offset and sys.stdout.isatty():
            print(status, end="")
            # Move cursor back down to the bottom
            print(f"\033[{line_offset}B", end="")
            print("\r", end="", flush=True)
        else:
            print(status, flush=True)


class JsonReporter(Reporter):
    """A reporter for reporting the results of a task in lines of JSON."""

    @staticmethod
    def emit_info(msg: str) -> None:
        """Print nothing."""

    @staticmethod
    def emit_start(cmd: cmd.Command) -> None:
        """Print nothing."""

    @staticmethod
    def emit_end(result: cmd.Result) -> None:
        """Emit the end of a command."""
        print(
            json.dumps(
                {
                    "task": result.cmd.name,
                    "command": result.cmd.command,
                    "duration": result.duration,
                    "output": ansi_escape.sub("", result.output),
                    "success": result.success,
                }
            )
        )

    @staticmethod
    def emit_summary(results: list[cmd.Result]) -> None:
        """Print nothing."""


class XmlReporter(Reporter):
    """A reporter for reporting the results of a task as Junit XML."""

    @staticmethod
    def emit_info(msg: str) -> None:
        """Print nothing."""

    @staticmethod
    def emit_start(cmd: cmd.Command) -> None:
        """Print nothing."""

    @staticmethod
    def emit_end(result: cmd.Result) -> None:
        """Print nothing."""

    @staticmethod
    def emit_summary(results: list[cmd.Result]) -> None:
        """Print Junit XML summary."""
        print(_create_xml(results))


def _plural(size: int) -> str:
    """Return 's' if the size is not a single element."""
    if size == 1:
        return ""
    return "s"


def _create_xml(results: list[cmd.Result]) -> str:
    """Create a string representing the results as Junit XML."""
    failures = [result for result in results if not result.success]
    duration = sum(result.duration for result in results)

    root = xml.Node(
        "testsuites",
        tests=len(results),
        failures=len(failures),
        errors=0,
        skipped=0,
        time=duration,
    )
    sa = xml.Node(
        "testsuite",
        name=_SUITENAME,
        time=duration,
        tests=len(results),
        failures=len(failures),
        errors=0,
        skipped=0,
    )
    root.add_child(sa)

    for result in results:
        sa.add_child(_result_xml(result))

    return root.to_document()


def _result_xml(result: cmd.Result) -> xml.Node:
    """Create a single Junit XML testcase."""
    node = xml.Node(
        "testcase",
        name=result.cmd.name,
        time=result.duration,
        classname=_SUITENAME,
    )
    if not result.success:
        node.add_child(xml.Node("failure", ansi_escape.sub("", result.output)))
    return node
