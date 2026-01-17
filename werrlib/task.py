"""Orchestration of task execution."""

import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

    from . import report
    from .cmd import Command, Process


def _filter_name(cmds: list[Command], name_filter: str | None) -> list[Command]:
    """Filter commands if a name filter is set."""
    if name_filter is None:
        return cmds

    # first, attempt to match the exact name
    selected = [cmd for cmd in cmds if cmd.name.startswith(name_filter)]
    if not selected:
        # if no matches, attempt to match as a prefix
        selected = [cmd for cmd in cmds if cmd.name.startswith(name_filter)]
    if not selected:
        raise ValueError(
            f"No commands match name: {name_filter}, available: "
            + ", ".join(cmd.name for cmd in cmds)
        )
    return selected


def run(
    project: Path,
    reporter: report.Reporter,
    cmds: list[Command],
    name_filter: str | None = None,
) -> bool:
    """Run the specified task and return True if all are successful.

    Emit results as we go.
    """
    cmds = _filter_name(cmds, name_filter)

    if reporter.parallel_cmds:
        return run_parallel(project, reporter, cmds)

    results = []
    for cmd in cmds:
        reporter.emit_start(cmd)
        result = cmd.run(cwd=project, live=not reporter.capture_output)
        results.append(result)
        reporter.emit_end(result)

    reporter.emit_summary(results)

    return all(result.success for result in results)


def run_parallel(project: Path, reporter: report.Reporter, cmds: list[Command]) -> bool:
    """Run the specified task in parallel and return True if all are successful.

    Live display reports results as each process completes.
    """
    # kick off all commands
    running: list[Process] = []
    for cmd in cmds:
        reporter.emit_start(cmd)
        running.append(cmd.start(cwd=project, live=not reporter.capture_output))

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
