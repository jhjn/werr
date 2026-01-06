"""Loading of python project config for checking."""

import logging
from pathlib import Path

try:
    import tomllib as tomli
except ImportError:
    import tomli  # type: ignore

from . import cmd


log = logging.getLogger("config")


def load_project(pyproject: Path) -> tuple[str, list[cmd.Task]]:
    """Load the tasks from the pyproject.toml file."""
    with open(pyproject, "rb") as f:
        config = tomli.load(f)

    # validation
    if "tool" not in config or "werr" not in config["tool"]:
        raise ValueError("pyproject.toml does not contain a [tool.werr] section")
    if "tasks" not in config["tool"]["werr"]:
        raise ValueError("[tool.werr] does not contain a `tasks` list")

    return config["project"]["name"], [
        cmd.Task(task) for task in config["tool"]["werr"]["tasks"]
    ]
