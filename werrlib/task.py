"""Orchestration of task execution."""

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from .cmd import Command, Process

from . import config, report

DEFAULT = "check"


def _filter_name(cmds: list[Command], name_filter: str | None) -> list[Command]:
    """Filter commands if a name filter is set."""
    if name_filter is None:
        return cmds

    # first, attempt to match the exact name
    cmds = [cmd for cmd in cmds if cmd.name.startswith(name_filter)]
    if not cmds:
        # if no matches, attempt to match as a prefix
        cmds = [cmd for cmd in cmds if cmd.name.startswith(name_filter)]
    if not cmds:
        raise ValueError(
            f"No commands match name: {name_filter}, available: "
            + ", ".join(cmd.name for cmd in cmds)
        )
    return cmds


def run(
    projectdir: Path,
    task: str = DEFAULT,
    reporter: report.Reporter | None = None,
    name_filter: str | None = None,
) -> bool:
    """Run the specified task and return True if all are successful.

    Emit results as we go.
    """
    if reporter is None:
        reporter = report.CliReporter()

    name, cmds = config.load_project(projectdir / "pyproject.toml", task)
    cmds = _filter_name(cmds, name_filter)
    reporter.emit_info(f"Project: {name} ({task})")

    results = []
    for cmd in cmds:
        reporter.emit_start(cmd)
        result = cmd.run(cwd=projectdir)
        results.append(result)
        reporter.emit_end(result)

    reporter.emit_summary(results)

    return all(result.success for result in results)


def run_parallel(
    projectdir: Path,
    task: str = DEFAULT,
    reporter: report.Reporter | None = None,
    name_filter: str | None = None,
) -> bool:
    """Run the specified task in parallel and return True if all are successful.

    Live display reports results as each process completes.
    """
    if reporter is None:
        reporter = report.ParallelCliReporter()

    name, cmds = config.load_project(projectdir / "pyproject.toml", task)
    cmds = _filter_name(cmds, name_filter)
    reporter.emit_info(f"Project: {name} ({task})")

    # kick off all commands
    running: list[Process] = []
    for cmd in cmds:
        reporter.emit_start(cmd)
        running.append(cmd.start(cwd=projectdir))

    results = []
    while running:
        for process in running[:]:  # use copy avoiding mid-loop mutation
            if (result := process.poll()) is not None:
                running.remove(process)
                results.append(result)
                reporter.emit_end(result)
        if running:
            time.sleep(0.03)

    reporter.emit_summary(results)

    return all(result.success for result in results)
