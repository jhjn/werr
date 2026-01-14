"""Wrappers of `subprocess` for custom werr functionality."""

from __future__ import annotations

import logging
import os
import shlex
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

    def run(self, *, cwd: Path | None = None, live: bool = False) -> Result:
        """Run the task using `uv` in isolated mode."""
        return self.start(cwd=cwd, live=live).poll(block=True)

    def start(self, *, cwd: Path | None = None, live: bool = False) -> Process:
        """Start the task using `uv` in isolated mode."""
        command = ["uv", "run", "bash", "-c", self.command]
        log.debug("Running command: %s", shlex.join(command))
        start = time.monotonic()
        process = subprocess.Popen(
            command,
            text=True,
            stderr=None if live else subprocess.STDOUT,
            stdout=None if live else subprocess.PIPE,
            cwd=cwd,
            # env is a copy but without the `VIRTUAL_ENV` variable.
            env=os.environ.copy() | {"VIRTUAL_ENV": ""},
        )
        return Process(self, process, start)
