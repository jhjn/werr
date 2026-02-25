"""Manage the recording and reporting of tasks."""

from __future__ import annotations

import json
import logging
import re
import shlex
import textwrap
import time
from _colorize import ANSIColors as C  # ty: ignore[unresolved-import]
from typing import Literal

from . import cmd, xml

log = logging.getLogger("report")
ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")


_SUITENAME = "werr"
_HEAD_PFX = "      "

ReporterName = Literal["cli", "live", "xml", "json"]


class Reporter:
    """A reporter for reporting the results of a task.

    The base reporter prints nothing for each emission method.
    Subclasses override methods to report each situation.
    """

    name: ReporterName
    capture_output: bool = True

    def emit_task(
        self,
        name: str,
        *,
        parallel: bool,
        reporter_name: ReporterName,
        cmds: list[cmd.Command],
        needs: tuple[str, ...] = (),
    ) -> None:
        """List a task."""

    def emit_info(self, msg: str) -> None:
        """Print a message (for an interactive reader)."""

    def emit_start(self, cmd: cmd.Command) -> None:
        """What is printed before a command begins."""

    def emit_end(self, result: cmd.Result) -> None:
        """What is printed after a command completes."""

    def emit_summary(self, results: list[cmd.Result]) -> None:
        """What is printed after the task has completed."""


class CliReporter(Reporter):
    """A reporter for reporting the results of a task to the console."""

    name: ReporterName = "cli"
    _commands: list[list[str]]
    _start_time: float | None = None

    icon_wait = f"{C.YELLOW}o{C.RESET}"
    icon_pass = f"{C.GREEN}+{C.RESET}"
    icon_fail = f"{C.RED}x{C.RESET}"

    def __init__(self) -> None:
        """Initialise the interactive CLI reporter."""
        self._commands = []

    def _duration(self) -> float:
        assert self._start_time, "must have start set before duration()"
        return time.monotonic() - self._start_time

    def _cursor_up(self, lines: int) -> None:
        print(f"\033[{lines}A", end="", flush=True)

    def _cursor_save(self) -> None:
        print("\0337", end="", flush=True)

    def _cursor_restore(self) -> None:
        print("\0338", end="", flush=True)

    def _clear_line(self) -> None:
        print("\r\033[K", end="", flush=True)

    def emit_task(
        self,
        name: str,
        *,
        parallel: bool,
        reporter_name: ReporterName,
        cmds: list[cmd.Command],
        needs: tuple[str, ...] = (),
    ) -> None:
        """List a task."""
        if parallel:
            suffix = " (parallel)"
        elif reporter_name == "live":
            suffix = " (live)"
        else:
            suffix = ""

        if needs:
            suffix += f" -> {C.GREEN}{', '.join(needs)}{C.RESET}"

        print(
            f"{C.BOLD_GREEN}{name}{C.RESET}{C.CYAN}{suffix}{C.RESET}\n"
            + "\n".join(f"  {C.GREY}{shlex.join(c.command)}{C.RESET}" for c in cmds)
        )

    def emit_info(self, msg: str) -> None:
        """Print to console."""
        print(msg)

    def emit_start(self, cmd: cmd.Command) -> None:
        """Emit the start of a command."""
        if self._start_time is None:
            self._start_time = time.monotonic()

        print(f"  {self.icon_wait} {cmd.name:<20} ", flush=True)
        self._commands.append(cmd.command)

    def emit_end(self, result: cmd.Result) -> None:
        """Emit the end of a command."""
        up_amount = len(self._commands) - self._commands.index(result.cmd.command)
        self._cursor_save()
        self._cursor_up(up_amount)
        self._clear_line()
        print(
            f"  {self.icon_pass if result.success else self.icon_fail} "
            f"{result.cmd.name:<20} {C.CYAN}({result.duration:.2f}s){C.RESET}",
            flush=True,
        )
        self._cursor_restore()

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


class JsonReporter(Reporter):
    """A reporter for reporting the results of a task in lines of JSON."""

    name: ReporterName = "json"

    def emit_task(
        self,
        name: str,
        *,
        parallel: bool,
        reporter_name: ReporterName,
        cmds: list[cmd.Command],
        needs: tuple[str, ...] = (),
    ) -> None:
        """List a task."""
        for c in cmds:
            print(
                json.dumps(
                    {
                        "task": name,
                        "reporter": reporter_name,
                        "parallel": parallel,
                        "command": shlex.join(c.command),
                        "needs": list(needs),
                    }
                )
            )

    def emit_end(self, result: cmd.Result) -> None:
        """Emit the end of a command."""
        print(
            json.dumps(
                {
                    "name": result.cmd.name,
                    "command": shlex.join(result.cmd.command),
                    "duration": result.duration,
                    "output": ansi_escape.sub("", result.output),
                    "success": result.success,
                }
            )
        )


class XmlReporter(Reporter):
    """A reporter for reporting the results of a task as Junit XML."""

    name: ReporterName = "xml"

    def emit_summary(self, results: list[cmd.Result]) -> None:
        """Print Junit XML summary."""
        print(_create_xml(results))


class LiveReporter(Reporter):
    """A reporter for reporting the results of a task to the console."""

    name: ReporterName = "live"
    capture_output: bool = False

    def emit_info(self, msg: str) -> None:
        """Print to console."""
        print(msg)


def get_reporter(name: ReporterName) -> Reporter:
    """Get a reporter instance for the given name."""
    match name:
        case "cli":
            return CliReporter()
        case "json":
            return JsonReporter()
        case "xml":
            return XmlReporter()
        case "live":
            return LiveReporter()
        case _:
            raise ValueError(f"Unknown reporter: {name}")


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
