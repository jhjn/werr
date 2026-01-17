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

DEFAULT_REPORTER: report.ReporterName = "cli"


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
    cli_reporter: report.ReporterName | None = None,
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
    except KeyError:
        raise ValueError(
            f"`{pyproject}` does not contain a [tool.werr] section"
        ) from None

    # select the user's task
    if cli_task:
        task = cli_task
        try:
            task_list = werr["task"][cli_task]
        except KeyError:
            raise ValueError(
                f"[tool.werr] does not contain a `task.{cli_task}` list"
            ) from None
    else:
        try:
            # get first task list in dict
            task, task_list = next(iter(werr["task"].items()))
        except KeyError:
            raise ValueError("[tool.werr] does not contain any `task` lists") from None
        log.debug("Using default task %s", task)

    # look for config in task list (optional dict as first element)
    config_parallel = False
    config_reporter: report.ReporterName = DEFAULT_REPORTER
    if task_list and isinstance(task_list[0], dict):
        config_parallel = task_list[0].get("parallel", False)
        config_reporter = task_list[0].get("reporter", DEFAULT_REPORTER)
        task_list = task_list[1:]

    # select the CLI over the config
    reporter = report.get_reporter(
        reporter_name=cli_reporter or config_reporter,
        parallel=cli_parallel or config_parallel,
    )()

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
        _command_from_template(command, variables) for command in task_list
    ]
