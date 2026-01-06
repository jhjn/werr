"""Orchestration of task execution."""

from pathlib import Path

from . import config, report

DEFAULT = "check"


def run(
    projectdir: Path,
    task: str = DEFAULT,
    reporter: type[report.Reporter] = report.CliReporter,
) -> bool:
    """
    Run the specified task and return True if all are successful.

    Emit results as we go.
    """
    name, tasks = config.load_project(projectdir / "pyproject.toml", task)
    reporter.emit_info(f"Project: {name} ({task})")

    results = []
    for task in tasks:
        reporter.emit_start(task)
        result = task.run(projectdir)
        results.append(result)
        reporter.emit_end(result)

    reporter.emit_summary(results)

    return all(result.success for result in results)
