"""Loading of python project config for checking."""

import logging
import tomllib
from collections import Counter
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

from . import report
from .cmd import Command

log = logging.getLogger("config")

# These commands are never descriptive enough _as is_.
# They come with modes like `uv run/sync/tool` or `ruff check/format`.
_ALWAYS_DASHNAME = {"uv", "ruff"}


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


@dataclass(slots=True)
class Task:
    """A configured task."""

    name: str
    reporter: report.Reporter
    commands: list[Command]
    parallel: bool = False
    needs: str | None = None
    dependency: Task | None = None

    def from_start(self) -> Iterator[Task]:
        """Iterate all tasks from start of dependency tree."""
        if self.dependency:
            yield from self.dependency.from_start()
        yield self


@dataclass(frozen=True, slots=True)
class Options:
    """Inline task options from the optional leading dict."""

    parallel: bool = False
    live: bool = False
    shell: bool = False
    needs: str | None = None


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


def _split_options(cfg_commands: list[Any]) -> tuple[Options, list[str]]:
    """Separate the optional leading options dict from command strings."""
    if cfg_commands and isinstance(cfg_commands[0], dict):
        return Options(**cfg_commands[0]), cfg_commands[1:]
    return Options(), cfg_commands


def _deduplicate_names(cmds: list[Command]) -> list[Command]:
    """Use dash-names for commands that share a base name."""
    counts = Counter(c.name for c in cmds)
    return [
        (
            Command.with_dashname(c)
            if counts[c.name] > 1 or c.name in _ALWAYS_DASHNAME
            else c
        )
        for c in cmds
    ]


def _get_tasks(
    taskmap: dict[str, Any] | None, variables: dict[str, str]
) -> Iterator[Task]:
    """Get (Task, raw_needs_name) pairs from the task config map."""
    if not taskmap:
        log.debug("no configured tasks found")
        return

    for name, opts_and_commands in taskmap.items():
        opts, commands = _split_options(opts_and_commands)

        reporter_name: report.ReporterName = "live" if opts.live else "cli"
        reporter = report.get_reporter(reporter_name)

        cmds = [
            _command_from_template(c, variables, shell=opts.shell) for c in commands
        ]
        yield Task(
            name,
            reporter,
            _deduplicate_names(cmds),
            parallel=opts.parallel,
            needs=opts.needs,
        )


def _resolve_needs(tasks: dict[str, Task]) -> list[Task]:
    """Validate needs references, detect cycles, and resolve to Task objects."""

    def _visit(name: str | None, path: set[str]) -> None:
        """Detect cycles depth first."""
        if not name:
            return  # nothing to visit
        if name in path:
            raise ValueError(f"task dependency cycle detected: {name}")
        path.add(name)
        _visit(tasks[name].needs, path)
        path.discard(name)

    for task in tasks.values():
        if not task.needs:
            continue
        if task.needs not in tasks:
            raise ValueError(f"task `{task.name}` needs unknown task `{task.needs}`")
        _visit(task.name, set())
        task.dependency = tasks[task.needs]
    return list(tasks.values())


def _load(pyproject: Path) -> tuple[Config, list[Task]]:
    """Load all configured tasks."""
    config = Config.load(pyproject)

    variables: dict[str, str] = config.werr.get("variable") or {}
    err = "tool.werr.variable must be a table mapping variable name to value"
    assert isinstance(variables, dict), err
    log.debug("Variables: %s", variables)

    return config, _resolve_needs(
        {t.name: t for t in _get_tasks(config.werr.get("task"), variables)}
    )


def load(pyproject: Path) -> list[Task]:
    """Load all configured tasks."""
    return _load(pyproject)[1]


def load_task(
    pyproject: Path,
    *,
    cli_task: str | None = None,
    cli_reporter: report.ReporterName | None = None,
    cli_parallel: bool | None = None,
) -> tuple[str, Task]:
    """Load a single task from a pyproject.toml file.

    CLI reporter overrides apply to all tasks; CLI parallel overrides apply only
    to the selected (leaf) task.
    """
    config, tasks = _load(pyproject)
    if not tasks:
        raise ValueError("[tool.werr] does not contain any `task` lists")

    if cli_task:
        chosen_task = next((task for task in tasks if task.name == cli_task), None)
        if not chosen_task:
            raise ValueError(f"[tool.werr] does not contain a `task.{cli_task}` list")
    else:
        chosen_task = tasks[0]  # select first task if none specified

    if cli_reporter:
        chosen_task.reporter = report.get_reporter(cli_reporter)
    if cli_parallel is not None:
        chosen_task.parallel = cli_parallel

    return config.get("project.name") or "unknown", chosen_task
