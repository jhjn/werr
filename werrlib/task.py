"""Orchestration of task execution."""

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from . import report
    from .cmd import Command, Result
    from .config import Task


def _filter_name(cmds: list[Command], name_filter: str) -> list[Command]:
    """Filter commands if a name filter is set."""
    exact = [c for c in cmds if c.name == name_filter]
    if exact:
        return exact
    prefix = [c for c in cmds if c.name.startswith(name_filter)]
    if prefix:
        return prefix
    raise ValueError(
        f"No commands match name: {name_filter}, available: "
        + ", ".join(cmd.name for cmd in cmds)
    )


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
        futures = (
            pool.submit(cmd.run, cwd=project, live=not reporter.capture_output)
            for cmd in cmds
        )
        for future in as_completed(futures):
            yield future.result()


def run(
    project: Path,
    reporter: report.Reporter,
    cmds: list[Command],
    name_filter: str | None = None,
    *,
    parallel: bool = False,
) -> bool:
    """Run the specified task and return True if all are successful.

    Emit results as we go.
    """
    if name_filter:
        cmds = _filter_name(cmds, name_filter)

    executor = _parallel if parallel else _serial

    results = []
    for result in executor(project, reporter, cmds):
        results.append(result)
        reporter.emit_end(result)
    reporter.emit_summary(results)

    return all(result.success for result in results)


def run_tree(
    project: Path,
    target: Task,
    name_filter: str | None = None,
) -> bool:
    """Run a task and its dependencies recursively.

    Dependencies share the reporter but keep their own parallelism.
    """
    for dep in target.from_start():
        success = run(
            project, target.reporter, dep.commands, name_filter, parallel=dep.parallel
        )
        if not success:
            return False
    return True
