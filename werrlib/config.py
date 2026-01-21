"""Loading of python project config for checking."""

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

try:
    import tomllib as tomli
except ImportError:
    import tomli  # type: ignore[import]

from . import report
from .cmd import Command

log = logging.getLogger("config")

DEFAULT_REPORTER: report.ReporterName = "cli"


@dataclass(frozen=True, slots=True)
class Task:
    """A configured task."""

    name: str
    reporter: report.Reporter
    commands: list[Command]
    """Commands with variables resolved."""


class _IgnoreMissing(dict):
    """A subclass of dict for use in format_map() that ignores missing keys."""

    def __missing__(self, key: str) -> str:
        return f"{{{key}}}"


def _command_from_template(command: str, variables: dict[str, str]) -> Command:
    """Create a command from a 'foo {bar}' template."""
    return Command(command.format_map(_IgnoreMissing(variables)))


def _get_tasks(taskmap: dict[str, Any], variables: dict[str, str]) -> Iterator[Task]:
    """Get Task objects from the mapping of task name to list of commands."""
    for name, commands_ in taskmap.items():
        if isinstance(commands_[0], dict):
            configdict = commands_[0]
            commands = commands_[1:]  # remove the configdict element
        else:
            configdict = {}
            commands = commands_

        reporter = report.get_reporter(
            reporter_name=configdict.get("reporter", DEFAULT_REPORTER),
            parallel=configdict.get("parallel", False),
        )()

        yield Task(
            name,
            reporter,
            [_command_from_template(command, variables) for command in commands],
        )


def _load(pyproject: Path) -> tuple[dict[str, Any], list[Task]]:
    """Load all configured tasks."""
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

    # variables: by default just contains {project}
    variables: dict[str, str] = {"project": str(pyproject.parent.resolve())}
    if "variable" in config["tool"]["werr"]:
        assert isinstance(
            config["tool"]["werr"]["variable"], dict
        ), "tool.werr.variable must be a table mapping variable name to value"
        for name, value in config["tool"]["werr"]["variable"].items():
            variables[name] = value.format_map(_IgnoreMissing(variables))
    log.debug("Variables: %s", variables)

    return config, list(_get_tasks(werr["task"], variables))


def load(pyproject: Path) -> list[Task]:
    """Load all configured tasks."""
    return _load(pyproject)[1]


def load_task(
    pyproject: Path,
    *,
    cli_task: str | None = None,
    cli_reporter: report.ReporterName | None = None,
    cli_parallel: bool = False,
) -> Task:
    """Load a single task from a pyproject.toml file."""
    config, tasks = _load(pyproject)
    if not tasks:
        raise ValueError("[tool.werr] does not contain any `task` lists")

    if cli_task:
        configured_task = next((task for task in tasks if task.name == cli_task), None)
        if not configured_task:
            raise ValueError(
                f"[tool.werr] does not contain a `task.{cli_task}` list"
            ) from None
    else:
        configured_task = tasks[0]

    reporter = report.get_reporter(
        reporter_name=cli_reporter or configured_task.reporter.name,
        parallel=cli_parallel or configured_task.reporter.parallel_cmds,
    )()

    # The very last thing the loader does is emit the first info line.
    project_name = config["project"]["name"]
    reporter.emit_info(f"Project: {project_name} ({configured_task.name})")

    return Task(configured_task.name, reporter, configured_task.commands)
