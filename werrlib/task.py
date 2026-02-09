"""Orchestration of task execution."""

from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from .cmd import Command

if TYPE_CHECKING:
    from pathlib import Path

    from . import report
    from .cmd import Command


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
    # @@@ run a uv sync first?
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
    for cmd in cmds:
        reporter.emit_start(cmd)

    results = []
    with ThreadPoolExecutor(max_workers=min(len(cmds), 8)) as executor:
        for result in executor.map(
            lambda cmd: cmd.run(cwd=project, live=not reporter.capture_output), cmds
        ):
            results.append(result)
            reporter.emit_end(result)

    reporter.emit_summary(results)

    return all(result.success for result in results)
