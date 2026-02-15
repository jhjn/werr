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

    _argv: list[str] | str  # str for shell commands
    use_dashname: bool = False
    shell: bool = False

    @classmethod
    def from_str(
        cls, command: str, *, use_dashname: bool = False, shell: bool = False
    ) -> Command:
        """Split a command string to construct a `Command`."""
        if shell:
            argv = command
        else:
            argv = shlex.split(command)
        return cls(_argv=argv, use_dashname=use_dashname, shell=shell)

    @classmethod
    def with_dashname(cls, cmd: Command) -> Command:
        """Create a new command with the same command but with dashname enabled."""
        return cls(_argv=cmd._argv, use_dashname=True, shell=cmd.shell)

    @property
    def name(self) -> str:
        """The name of the task."""
        if isinstance(self._argv, str):
            argv = shlex.split(self._argv)
        else:
            argv = self._argv

        if self.use_dashname and len(argv) > 1:
            return "-".join(argv[0:2])
        return argv[0]

    @property
    def command(self) -> list[str]:
        """The constructed command to run."""
        if self.shell:
            assert isinstance(self._argv, str)
            return ["uv", "run", "bash", "-c", self._argv]
        assert isinstance(self._argv, list)
        return ["uv", "run", *self._argv]

    def run(self, *, cwd: Path | None = None, live: bool = False) -> Result:
        """Run the task using `uv` in isolated mode."""
        command = self.command
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
