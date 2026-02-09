"""Wrappers of `subprocess` for custom werr functionality."""

from __future__ import annotations

import logging
import os
import shlex
import subprocess
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

log = logging.getLogger("cmd")


@dataclass(frozen=True, slots=True)
class Result:
    """Information about a *completed* process."""

    cmd: Command
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

    command: list[str]
    use_dashname: bool = False

    @property
    def name(self) -> str:
        """The name of the task."""
        if self.use_dashname and len(self.command) > 1:
            return "-".join(self.command[0:2])
        return self.command[0]

    def run(self, *, cwd: Path | None = None, live: bool = False) -> Result:
        """Run the task using `uv` in isolated mode."""
        command = ["uv", "run", *self.command]
        log.debug("Running command: %s", shlex.join(command))
        start = time.monotonic()
        process = subprocess.run(
            command,
            check=False,  # returncode is checked manually
            text=True,
            stderr=None if live else subprocess.STDOUT,
            stdout=None if live else subprocess.PIPE,
            cwd=cwd,
            # env is a copy but without the `VIRTUAL_ENV` variable.
            env=os.environ.copy() | {"VIRTUAL_ENV": ""},
        )
        duration = time.monotonic() - start
        return Result(self, process.returncode, duration, process.stdout)
