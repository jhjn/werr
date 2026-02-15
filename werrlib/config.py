"""Loading of python project config for checking."""

import logging
import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

from . import report
from .cmd import Command

log = logging.getLogger("config")


@dataclass(slots=True)
class Config:
    """Parsed pyproject.toml."""

    path: Path
    _config: dict[str, Any]

    _werr_cache: Config | None = None  # Cache of config starting at tool.werr

    @classmethod
    def load(cls, pyproject: Path) -> Config:
        """Load python project config from file."""
        if not pyproject.exists():
            raise ValueError(
                f"project directory `{pyproject.parent}` does not contain a "
                "`pyproject.toml`"
            )
        return cls(pyproject, tomllib.loads(pyproject.read_text()))

    def get(self, path: str) -> Any | None:  # noqa: ANN401
        """Get nested config item or None if it doesn't exist.

        Path looks like 'key1.key2.key3'.
        """
        item: Any = self._config
        key = "<root>"
        try:
            for key in path.split("."):
                item = item[key]
            log.debug("Found %s=%s in %s", path, item, self.path)
        except (KeyError, TypeError):
            log.debug(
                "Reading path '%s' in %s. Could not find key '%s'", path, self.path, key
            )
            item = None
        return item

    @property
    def werr(self) -> Config:
        """Get the config starting at tool.werr."""
        if self._werr_cache is None:
            werr_config = self.get("tool.werr")
            if werr_config is None:
                raise ValueError(f"[tool.werr] section not found in `{self.path}`")
            self._werr_cache = Config(self.path, werr_config)
        return self._werr_cache


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


def _command_from_template(
    command: str, variables: dict[str, str], *, shell: bool = False
) -> Command:
    """Create a command from a 'foo {bar}' template."""
    resolved = command.format_map(_IgnoreMissing(variables))
    return Command.from_str(resolved, shell=shell)


def _get_tasks(
    taskmap: dict[str, Any] | None, variables: dict[str, str]
) -> Iterator[Task]:
    """Get Task objects from the mapping of task name to list of commands."""
    if not taskmap:
        log.debug("no configured tasks found")
        return

    for name, cfg_commands in taskmap.items():
        if isinstance(cfg_commands[0], dict):
            configdict = cfg_commands[0]
            commands = cfg_commands[1:]  # remove the configdict element
        else:
            configdict = {}
            commands = cfg_commands

        if configdict.get("live", False):
            reporter = "live"
        else:
            reporter = "cli"  # default reporter

        reporter = report.get_reporter(
            reporter_name=reporter,
            parallel=configdict.get("parallel", False),
        )()

        shell = configdict.get("shell", False)
        first_cmds = [
            _command_from_template(command, variables, shell=shell)
            for command in commands
        ]
        final_cmds = []
        # Get set of commands that have more than one common name
        names = [cmd.name for cmd in first_cmds]
        for cmd in first_cmds:
            if names.count(cmd.name) > 1:
                final_cmds.append(Command.with_dashname(cmd))
            else:
                final_cmds.append(cmd)

        yield Task(name, reporter, final_cmds)


def _load(pyproject: Path) -> tuple[Config, list[Task]]:
    """Load all configured tasks."""
    config = Config.load(pyproject)

    variables: dict[str, str] = config.werr.get("variable") or {}
    err = "tool.werr.variable must be a table mapping variable name to value"
    assert isinstance(variables, dict), err
    log.debug("Variables: %s", variables)

    return config, list(_get_tasks(config.werr.get("task"), variables))


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
        configured_task = tasks[0]  # select first task if none specified

    reporter = report.get_reporter(
        reporter_name=cli_reporter or configured_task.reporter.name,
        parallel=cli_parallel or configured_task.reporter.parallel_cmds,
    )()

    # The very last thing the loader does is emit the first info line.
    reporter.emit_info(
        f"Project: {config.get('project.name')} ({configured_task.name})"
    )

    return Task(configured_task.name, reporter, configured_task.commands)
