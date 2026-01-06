"""Manage the recording and reporting of tasks."""

from __future__ import annotations

import json
import logging
import re
import textwrap
from _colorize import ANSIColors as C
from abc import ABC, abstractmethod

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

    task_index = 0

    @staticmethod
    def emit_info(msg: str) -> None:
        """Print to console."""
        print(msg)

    @staticmethod
    def emit_start(cmd: cmd.Command) -> None:
        """Emit the start of a command."""
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
        duration = sum(result.duration for result in results)

        msg = (
            f"Ran {len(results)} check{_plural(len(results))} in "
            f"{duration:>2.2f} secs, "
            f"{len(successes)} Passed, {len(failures)} Failed"
        )
        print(f"{C.RED if failures else C.GREEN}{msg}{C.RESET}")

        if failures:
            print("\nFailures:\n---------")
            for result in failures:
                CliReporter.emit_start(result.task)
                print()
                print(textwrap.indent(result.output, _HEAD_PFX))


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
                    "task": result.task.name,
                    "command": result.task.command,
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
        name=result.task.name,
        time=result.duration,
        classname=_SUITENAME,
    )
    if not result.success:
        node.add_child(xml.Node("failure", ansi_escape.sub("", result.output)))
    return node
