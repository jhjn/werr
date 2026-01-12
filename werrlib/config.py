"""Loading of python project config for checking."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

try:
    import tomllib as tomli
except ImportError:
    import tomli  # type: ignore[import]

from .cmd import Command

log = logging.getLogger("config")


class _IgnoreMissing(dict):
    def __missing__(self, key: str) -> str:
        return "{key}"


def _command_from_template(command: str, variables: dict[str, str]) -> Command:
    """Create a command from a 'foo {bar}' template."""
    return Command(command.format_map(_IgnoreMissing(variables)))


def load_project(pyproject: Path, task: str) -> tuple[str, list[Command]]:
    """Load the commands from the pyproject.toml file."""
    if not pyproject.exists():
        raise ValueError(
            f"project directory `{pyproject.parent}` does not contain a "
            "`pyproject.toml`"
        )

    with pyproject.open("rb") as f:
        config = tomli.load(f)

    # validation of [tool.werr] section
    if "tool" not in config or "werr" not in config["tool"]:
        raise ValueError(f"`{pyproject}` does not contain a [tool.werr] section")

    if (
        "task" not in config["tool"]["werr"]
        or task not in config["tool"]["werr"]["task"]
    ):
        raise ValueError(f"[tool.werr] does not contain a `task.{task}` list")

    # by default just contains {project}
    variables: dict[str, str] = {"project": str(pyproject.parent.resolve())}
    if "variable" in config["tool"]["werr"]:
        assert isinstance(
            config["tool"]["werr"]["variable"], dict
        ), "tool.werr.variable must be a table mapping variable name to value"
        for name, value in config["tool"]["werr"]["variable"].items():
            variables[name] = value.format_map(_IgnoreMissing(variables))
    log.debug("Variables: %s", variables)

    return config["project"]["name"], [
        _command_from_template(command, variables)
        for command in config["tool"]["werr"]["task"][task]
    ]
