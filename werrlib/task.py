"""Orchestration of task execution."""

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from . import report
    from .cmd import Command, Result


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


def _serial(
    project: Path, reporter: report.Reporter, cmds: list[Command]
) -> Iterator[Result]:
    """Iterate commands yielding results."""
    for cmd in cmds:
        reporter.emit_start(cmd)
        yield cmd.run(cwd=project, live=not reporter.capture_output)


def _parallel(
    project: Path, reporter: report.Reporter, cmds: list[Command]
) -> Iterator[Result]:
    """Execute commands in parallel yielding results when they complete."""
    for cmd in cmds:
        reporter.emit_start(cmd)  # print all start messages at once
    with ThreadPoolExecutor(max_workers=min(len(cmds), 8)) as pool:
        yield from pool.map(
            lambda cmd: cmd.run(cwd=project, live=not reporter.capture_output), cmds
        )


def run(
    project: Path,
    reporter: report.Reporter,
    cmds: list[Command],
    name_filter: str | None = None,
) -> bool:
    """Run the specified task and return True if all are successful.

    Emit results as we go.
    """
    # @@@ run a uv sync first?
    cmds = _filter_name(cmds, name_filter)

    executor = _parallel if reporter.parallel_cmds else _serial

    results = []
    for result in executor(project, reporter, cmds):
        results.append(result)
        reporter.emit_end(result)
    reporter.emit_summary(results)

    return all(result.success for result in results)
