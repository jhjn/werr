"""Orchestration of task execution."""

from pathlib import Path

from . import config, report


def default(
    projectdir: Path, reporter: type[report.Reporter] = report.CliReporter
) -> bool:
    """
    Run the default check tasks and return True if successful.

    Emit results as we go.
    """
    name, tasks = config.load_project(projectdir / "pyproject.toml")
    reporter.emit_info(f"Project: {name}")

    results = []
    for task in tasks:
        reporter.emit_start(task)
        result = task.run(projectdir)
        results.append(result)
        reporter.emit_end(result)

    reporter.emit_summary(results)

    return all(result.success for result in results)
