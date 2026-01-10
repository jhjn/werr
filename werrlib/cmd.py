"""Wrappers of `subprocess` for custom werr functionality."""

from __future__ import annotations

import logging
import os
import subprocess
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, overload

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
class Process:
    """A started command."""

    cmd: Command
    process: subprocess.Popen[str]
    start_time: float

    @overload
    def poll(self, *, block: Literal[True]) -> Result: ...

    @overload
    def poll(self, *, block: Literal[False]) -> Result | None: ...

    def poll(self, *, block: bool = False) -> Result | None:
        """Check if process finished. Return Result if done, None if still running."""
        if block:
            self.process.wait()
        elif self.process.poll() is None:
            return None
        duration = time.monotonic() - self.start_time
        stdout = self.process.stdout.read() if self.process.stdout else ""
        return Result(self.cmd, self.process.returncode, duration, stdout)


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
        return self.start(projectdir).poll(block=True)

    def start(self, projectdir: Path) -> Process:
        """Start the task using `uv` in isolated mode."""
        command = f"uv run --project '{projectdir}' {self.resolved_command(projectdir)}"
        log.debug("Running command: %s", command)
        start = time.monotonic()
        process = subprocess.Popen(
            command,
            shell=True,
            text=True,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
            # env is a copy but without the `VIRTUAL_ENV` variable.
            env=os.environ.copy() | {"VIRTUAL_ENV": ""},
        )
        return Process(self, process, start)
