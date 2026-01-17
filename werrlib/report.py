"""Manage the recording and reporting of tasks."""

from __future__ import annotations

import json
import logging
import re
import textwrap
import time
from _colorize import ANSIColors as C  # ty: ignore[unresolved-import]
from abc import ABC, abstractmethod
from typing import Literal

from . import cmd, xml

log = logging.getLogger("report")
ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


_SUITENAME = "werr"
_TOTAL_HEAD_LEN = 25
_HEAD_PFX = "      "

ReporterName = Literal["cli", "live", "xml", "json"]


class Reporter(ABC):
    """A reporter for reporting the results of a task."""

    capture_output: bool = True
    parallel_cmds: bool = False

    @abstractmethod
    def emit_info(self, msg: str) -> None:
        """Print a message (for an interactive reader)."""

    @abstractmethod
    def emit_start(self, cmd: cmd.Command) -> None:
        """What is printed before a command begins."""

    @abstractmethod
    def emit_end(self, result: cmd.Result) -> None:
        """What is printed after a command completes."""

    @abstractmethod
    def emit_summary(self, results: list[cmd.Result]) -> None:
        """What is printed after the task has completed."""


class CliReporter(Reporter):
    """A reporter for reporting the results of a task to the console."""

    start_time: float | None = None

    icon_wait = f"{C.YELLOW}o{C.RESET}"
    icon_pass = f"{C.GREEN}+{C.RESET}"
    icon_fail = f"{C.RED}x{C.RESET}"

    def _duration(self) -> float:
        assert self.start_time, "must have start set before duration()"
        return time.monotonic() - self.start_time

    def _clear_line(self) -> None:
        print("\r\033[K", end="", flush=True)

    def emit_info(self, msg: str) -> None:
        """Print to console."""
        print(msg)

    def emit_start(self, cmd: cmd.Command) -> None:
        """Emit the start of a command."""
        if self.start_time is None:
            self.start_time = time.monotonic()

        print(f"  {self.icon_wait} {cmd.name:<20} ", end="", flush=True)

    def emit_end(self, result: cmd.Result) -> None:
        """Emit the end of a command."""
        self._clear_line()
        print(
            f"  {self.icon_pass if result.success else self.icon_fail} "
            f"{result.cmd.name:<20} {C.CYAN}({result.duration:.2f}s){C.RESET}",
            flush=True,
        )

    def emit_summary(self, results: list[cmd.Result]) -> None:
        """Print the summary line explaining what the net result was."""
        successes = [result for result in results if result.success]
        failures = [result for result in results if not result.success]

        msg = (
            f"Ran {len(results)} check{_plural(len(results))} in "
            f"{self._duration():>2.2f} secs, "
            f"{len(successes)} Passed, {len(failures)} Failed"
        )
        print(f"{C.RED if failures else C.GREEN}{msg}{C.RESET}")

        if failures:
            print("\nFailures:\n---------")
            for result in failures:
                self.emit_start(result.cmd)
                print()
                print(textwrap.indent(result.output, _HEAD_PFX))


class ParallelCliReporter(CliReporter):
    """An interactive reporter with live display updating in place."""

    parallel_cmds: bool = True

    _commands: list[str]

    def __init__(self) -> None:
        """Initialise the parallel CLI reporter."""
        self._commands = []

    def _cursor_up(self, lines: int) -> None:
        print(f"\033[{lines}A", end="", flush=True)

    def _cursor_save(self) -> None:
        print("\0337", end="", flush=True)

    def _cursor_restore(self) -> None:
        print("\0338", end="", flush=True)

    def emit_start(self, cmd: cmd.Command) -> None:
        """Print the command with running status."""
        if self.start_time is None:
            self.start_time = time.monotonic()

        print(f"  {C.YELLOW}o{C.RESET} {cmd.name}", flush=True)
        self._commands.append(cmd.command)

    def emit_end(self, result: cmd.Result) -> None:
        """Move cursor back and update the command's status."""
        up_amount = len(self._commands) - self._commands.index(result.cmd.command)
        self._cursor_save()
        self._cursor_up(up_amount)
        super().emit_end(result)
        self._cursor_restore()


class JsonReporter(Reporter):
    """A reporter for reporting the results of a task in lines of JSON."""

    def emit_info(self, msg: str) -> None:
        """Print nothing."""

    def emit_start(self, cmd: cmd.Command) -> None:
        """Print nothing."""

    def emit_end(self, result: cmd.Result) -> None:
        """Emit the end of a command."""
        print(
            json.dumps(
                {
                    "name": result.cmd.name,
                    "command": result.cmd.command,
                    "duration": result.duration,
                    "output": ansi_escape.sub("", result.output),
                    "success": result.success,
                }
            )
        )

    def emit_summary(self, results: list[cmd.Result]) -> None:
        """Print nothing."""


class ParallelJsonReporter(JsonReporter):
    """A reporter for reporting the results of a task in lines of JSON."""

    parallel_cmds: bool = True


class XmlReporter(Reporter):
    """A reporter for reporting the results of a task as Junit XML."""

    def emit_info(self, msg: str) -> None:
        """Print nothing."""

    def emit_start(self, cmd: cmd.Command) -> None:
        """Print nothing."""

    def emit_end(self, result: cmd.Result) -> None:
        """Print nothing."""

    def emit_summary(self, results: list[cmd.Result]) -> None:
        """Print Junit XML summary."""
        print(_create_xml(results))


class ParallelXmlReporter(XmlReporter):
    """A reporter for reporting the results of a task as Junit XML."""

    parallel_cmds: bool = True


class LiveReporter(Reporter):
    """A reporter for reporting the results of a task to the console."""

    capture_output: bool = False

    def emit_info(self, msg: str) -> None:
        """Print to console."""
        print(msg)

    def emit_start(self, cmd: cmd.Command) -> None:
        """Do not emit the start of a command."""

    def emit_end(self, result: cmd.Result) -> None:
        """Do not emit the result at the end of a command."""

    def emit_summary(self, results: list[cmd.Result]) -> None:
        """Do not emit the summary."""


_SERIAL_REPORTERS = {
    "cli": CliReporter,
    "live": LiveReporter,
    "xml": XmlReporter,
    "json": JsonReporter,
}
_PARALLEL_REPORTERS = {
    "cli": ParallelCliReporter,
    "live": None,  # cannot set live _and_ parallel.
    "xml": ParallelXmlReporter,
    "json": ParallelJsonReporter,
}


def get_reporter(reporter_name: str, *, parallel: bool) -> type[Reporter]:
    """Get a reporter class for the given reporter name and mode."""
    if parallel:
        d = _PARALLEL_REPORTERS
    else:
        d = _SERIAL_REPORTERS
    try:
        reporter = d[reporter_name]
    except KeyError:
        raise ValueError(f"Unknown reporter: {reporter_name}") from None
    if reporter is None:
        raise ValueError(
            f"Reporter '{reporter_name}' cannot be used in "
            f"{'parallel' if parallel else 'serial'} mode"
        )
    return reporter


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
