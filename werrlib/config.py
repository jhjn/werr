"""Loading of python project config for checking."""

import logging
import tomllib
from collections import Counter
from dataclasses import dataclass, replace
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


@dataclass(frozen=True, slots=True)
class Task:
    """A configured task."""

    name: str
    reporter: report.Reporter
    commands: list[Command]
    parallel: bool = False
    project_name: str | None = None
    needs: Task | None = None

    def from_start(self) -> Iterator[Task]:
        """Iterate all tasks from start of dependency tree."""
        if self.needs:
            yield from self.needs.from_start()
        yield self


@dataclass(frozen=True, slots=True)
class Options:
    """Inline task options from the optional leading dict."""

    parallel: bool = False
    live: bool = False
    shell: bool = False
    needs: str = ""


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
) -> Iterator[tuple[Task, str]]:
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
            name, reporter, _deduplicate_names(cmds), parallel=opts.parallel
        ), opts.needs


def _resolve_needs(raw: list[tuple[Task, str]]) -> list[Task]:
    """Validate needs references, detect cycles, and resolve to Task objects."""
    by_name = {t.name: t for t, _ in raw}
    needs_map = {t.name: dep for t, dep in raw}

    for name, dep in needs_map.items():
        if dep and dep not in by_name:
            raise ValueError(f"task `{name}` needs unknown task `{dep}`")

    # Cycle detection via DFS
    def _visit(name: str, path: set[str]) -> None:
        if name in path:
            raise ValueError(f"task dependency cycle detected: {name}")
        path.add(name)
        if needs_map[name]:
            _visit(needs_map[name], path)
        path.discard(name)

    for name in needs_map:
        _visit(name, set())

    # Resolve string references to Task objects
    resolved: dict[str, Task] = {}

    def _resolve(name: str) -> Task:
        if name in resolved:
            return resolved[name]
        dep_name = needs_map[name]
        dep = _resolve(dep_name) if dep_name else None
        resolved[name] = replace(by_name[name], needs=dep)
        return resolved[name]

    return [_resolve(t.name) for t, _ in raw]


def _load(pyproject: Path) -> tuple[Config, list[Task]]:
    """Load all configured tasks."""
    config = Config.load(pyproject)

    variables: dict[str, str] = config.werr.get("variable") or {}
    err = "tool.werr.variable must be a table mapping variable name to value"
    assert isinstance(variables, dict), err
    log.debug("Variables: %s", variables)

    raw = list(_get_tasks(config.werr.get("task"), variables))
    return config, _resolve_needs(raw)


def load(pyproject: Path) -> list[Task]:
    """Load all configured tasks."""
    return _load(pyproject)[1]


def load_task(
    pyproject: Path,
    *,
    cli_task: str | None = None,
    cli_reporter: report.ReporterName | None = None,
    cli_parallel: bool | None = None,
) -> Task:
    """Load a single task from a pyproject.toml file.

    CLI reporter overrides apply to all tasks; CLI parallel overrides apply only
    to the selected (leaf) task.
    """
    config, tasks = _load(pyproject)
    if not tasks:
        raise ValueError("[tool.werr] does not contain any `task` lists")

    if cli_task:
        configured_task = next((task for task in tasks if task.name == cli_task), None)
        if not configured_task:
            raise ValueError(f"[tool.werr] does not contain a `task.{cli_task}` list")
    else:
        configured_task = tasks[0]  # select first task if none specified

    project_name = config.get("project.name")

    # Apply CLI overrides recursively through the needs chain
    overridden: dict[str, Task] = {}

    def _apply(t: Task) -> Task:
        if t.name in overridden:
            return overridden[t.name]
        dep = _apply(t.needs) if t.needs else None
        reporter_name = cli_reporter or t.reporter.name
        parallel = t.parallel
        if t.name == configured_task.name and cli_parallel is not None:
            parallel = cli_parallel
        overridden[t.name] = replace(
            t,
            reporter=report.get_reporter(reporter_name),
            parallel=parallel,
            project_name=project_name,
            needs=dep,
        )
        return overridden[t.name]

    return _apply(configured_task)
