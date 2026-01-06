"""Loading of python project config for checking."""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

try:
    import tomllib as tomli
except ImportError:
    import tomli  # type: ignore[import]

from . import cmd

log = logging.getLogger("config")


def load_project(pyproject: Path, task: str) -> tuple[str, list[cmd.Command]]:
    """Load the commands from the pyproject.toml file."""
    with pyproject.open("rb") as f:
        config = tomli.load(f)

    # validation of [tool.werr] section
    if "tool" not in config or "werr" not in config["tool"]:
        raise ValueError("pyproject.toml does not contain a [tool.werr] section")
    if (
        "task" not in config["tool"]["werr"]
        or task not in config["tool"]["werr"]["task"]
    ):
        raise ValueError(f"[tool.werr] does not contain a `task.{task}` list")

    return config["project"]["name"], [
        cmd.Command(task) for task in config["tool"]["werr"]["task"][task]
    ]
