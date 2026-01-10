"""Orchestration of task execution."""

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from .cmd import Process

from . import config, report

DEFAULT = "check"


def run(
    projectdir: Path,
    task: str = DEFAULT,
    reporter: report.Reporter | None = None,
) -> bool:
    """Run the specified task and return True if all are successful.

    Emit results as we go.
    """
    if reporter is None:
        reporter = report.CliReporter()

    name, cmds = config.load_project(projectdir / "pyproject.toml", task)
    reporter.emit_info(f"Project: {name} ({task})")

    results = []
    for cmd in cmds:
        reporter.emit_start(cmd)
        result = cmd.run(projectdir)
        results.append(result)
        reporter.emit_end(result)

    reporter.emit_summary(results)

    return all(result.success for result in results)


def run_parallel(
    projectdir: Path,
    task: str = DEFAULT,
    reporter: report.Reporter | None = None,
) -> bool:
    """Run the specified task in parallel and return True if all are successful.

    Live display reports results as each process completes.
    """
    if reporter is None:
        reporter = report.ParallelCliReporter()

    name, cmds = config.load_project(projectdir / "pyproject.toml", task)
    reporter.emit_info(f"Project: {name} ({task})")

    # kick off all commands
    running: list[Process] = []
    for cmd in cmds:
        reporter.emit_start(cmd)
        running.append(cmd.start(projectdir))

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
