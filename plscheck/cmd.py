"""Wrappers of `subprocess` for custom plscheck functionality."""

from __future__ import annotations

import logging
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

log = logging.getLogger("cmd")


@dataclass(frozen=True, slots=True)
class Result:
    """Information about a *completed* process."""

    task: Task
    returncode: int
    duration: float
    output: str

    @property
    def success(self) -> bool:
        """Return True if the process was successful."""
        return self.returncode == 0


@dataclass(frozen=True, slots=True)
class Task:
    """A task to be run."""

    command: str

    @property
    def name(self) -> str:
        """The name of the task."""
        return self.command.split(" ")[0]

    def run(self, projectdir: Path) -> Result:
        """Run the task using `uv` in isolated mode."""
        command = f"uv run --isolated --project '{projectdir}' {self.command}"
        log.debug("Running command: %s", command)
        start = time.monotonic()
        process = subprocess.run(
            command,
            shell=True,
            check=False,  # the returncode is checked manually
            text=True,
            stderr=subprocess.STDOUT,
            stdout=subprocess.PIPE,
        )
        duration = time.monotonic() - start
        return Result(self, process.returncode, duration, process.stdout)
