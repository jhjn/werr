"""Loading of python project config for checking."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

try:
    import tomllib as tomli
except ImportError:
    import tomli  # type: ignore[import]

from . import report
from .cmd import Command

log = logging.getLogger("config")

DEFAULT_TASK = "check"
DEFAULT_REPORTER = "cli"


class _IgnoreMissing(dict):
    """A subclass of dict for use in format_map() that ignores missing keys."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def _command_from_template(command: str, variables: dict[str, str]) -> Command:
    """Create a command from a 'foo {bar}' template."""
    return Command(command.format_map(_IgnoreMissing(variables)))


def load_project(
    pyproject: Path,
    *,
    cli_task: str | None = None,
    cli_reporter: str | None = None,
    cli_parallel: bool = False,
) -> tuple[report.Reporter, list[Command]]:
    """Load the commands from the pyproject.toml file.

    The only forbidden task name is "task" itself.
    """
    if not pyproject.exists():
        raise ValueError(
            f"project directory `{pyproject.parent}` does not contain a "
            "`pyproject.toml`"
        )

    with pyproject.open("rb") as f:
        config = tomli.load(f)

    # validation of [tool.werr] section
    try:
        werr = config["tool"]["werr"]
        default = werr.get("default", {})
    except KeyError:
        raise ValueError(
            f"`{pyproject}` does not contain a [tool.werr] section"
        ) from None

    # select the user's task
    if cli_task:
        task = cli_task  # always prefer the CLI to config
    else:
        task = default.get("task", DEFAULT_TASK)
        log.debug("Using default task %s", task)
    if task == "task":
        raise ValueError("werr tasks cannot be named 'task'")

    # select the user's serial/parallel mode
    if cli_parallel:
        parallel = cli_parallel  # always prefer the CLI to config
    else:
        parallel = default.get(task, {}).get("parallel", False)
        log.debug("Using default parallel %s", parallel)

    # select the user's reporter
    if cli_reporter:
        reporter_name = cli_reporter  # always prefer the CLI to config
    else:
        reporter_name = default.get(task, {}).get("reporter", DEFAULT_REPORTER)
    reporter = report.get_reporter(reporter_name, parallel=parallel)()

    # command selection
    if "task" not in werr or task not in werr["task"]:
        raise ValueError(f"[tool.werr] does not contain a `task.{task}` list")

    # variables: by default just contains {project}
    variables: dict[str, str] = {"project": str(pyproject.parent.resolve())}
    if "variable" in config["tool"]["werr"]:
        assert isinstance(
            config["tool"]["werr"]["variable"], dict
        ), "tool.werr.variable must be a table mapping variable name to value"
        for name, value in config["tool"]["werr"]["variable"].items():
            variables[name] = value.format_map(_IgnoreMissing(variables))
    log.debug("Variables: %s", variables)

    # The very last thing the loader does is emit the first info line.
    project_name = config["project"]["name"]
    reporter.emit_info(f"Project: {project_name} ({task})")
    return reporter, [
        _command_from_template(command, variables)
        for command in config["tool"]["werr"]["task"][task]
    ]
