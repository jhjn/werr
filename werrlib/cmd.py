"""Wrappers of `subprocess` for custom werr functionality."""

from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("cmd")


@dataclass(frozen=True, slots=True)
class Result:
    """Information about a *completed* process."""

    task: Command
    returncode: int
    duration: float
    output: str

    @property
    def success(self) -> bool:
        """Return True if the process was successful."""
        return self.returncode == 0


@dataclass(frozen=True, slots=True)
class Command:
    """A command to be run as part of a task."""

    command: str

    @property
    def name(self) -> str:
        """The name of the task."""
        return self.command.split(" ")[0]

    def resolved_command(self, projectdir: Path) -> str:
        """Return the command with the {...} variables substituted."""
        return self.command.replace("{project}", str(projectdir.resolve()))

    def run(self, projectdir: Path) -> Result:
        """Run the task using `uv` in isolated mode."""
        command = f"uv run --project '{projectdir}' {self.resolved_command(projectdir)}"
        log.debug("Running command: %s", command)
        start = time.monotonic()
        process = subprocess.run(
            command,
            shell=True,
            check=False,  # the returncode is checked manually
            text=True,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            # env is a copy but without the `VIRTUAL_ENV` variable.
            env=os.environ.copy() | {"VIRTUAL_ENV": ""},
        )
        duration = time.monotonic() - start
        return Result(self, process.returncode, duration, process.stdout)
