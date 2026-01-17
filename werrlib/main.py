"""Entrypoint for the werr CLI tool."""

__all__ = ("console_entry",)

import logging
import subprocess
import sys
import traceback

from . import cli

log = logging.getLogger("saturn")


def console_entry() -> None:
    """Entrypoint for CLI usage."""
    try:
        cli.run(sys.argv[1:])
    # TODO: Better process failure error reporting
    except subprocess.CalledProcessError as e:
        log.debug(traceback.format_exc())
        log.error(str(e.stdout).strip())  # noqa: TRY400
        log.error(str(e.stderr).strip())  # noqa: TRY400
        sys.exit(e.returncode)
    except ValueError as e:
        log.debug(traceback.format_exc())
        log.error(e)  # noqa: TRY400
        sys.exit(1)
    except KeyboardInterrupt:
        log.error("Interrupted by user.")  # noqa: TRY400
        sys.exit(130)


if __name__ == "__main__":
    console_entry()
