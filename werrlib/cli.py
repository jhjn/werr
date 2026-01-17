"""The command line interface for the werr tool."""

import _colorize  # ty: ignore[unresolved-import]
import argparse
import logging
import sys
from pathlib import Path

from . import config, task

log = logging.getLogger("cli")

_colorize.set_theme(
    _colorize.Theme(
        argparse=_colorize.Argparse(
            usage=_colorize.ANSIColors.BOLD_GREEN,
            prog=_colorize.ANSIColors.BOLD_CYAN,
            heading=_colorize.ANSIColors.BOLD_GREEN,
            summary_long_option=_colorize.ANSIColors.CYAN,
            summary_short_option=_colorize.ANSIColors.CYAN,
            summary_label=_colorize.ANSIColors.CYAN,
            summary_action=_colorize.ANSIColors.CYAN,
            long_option=_colorize.ANSIColors.BOLD_CYAN,
            short_option=_colorize.ANSIColors.BOLD_CYAN,
            label=_colorize.ANSIColors.CYAN,
            action=_colorize.ANSIColors.BOLD_CYAN,
        )
    )
)


class LogFormatter(logging.Formatter):
    """Custom stdlib log formatter for the werr tool."""

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record with a colorized level name."""
        match record.levelno:
            case logging.DEBUG:
                name = _colorize.ANSIColors.MAGENTA + "debug"
            case logging.INFO:
                name = _colorize.ANSIColors.GREEN + "info"
            case logging.WARNING:
                name = _colorize.ANSIColors.YELLOW + "warning"
            case logging.ERROR:
                name = _colorize.ANSIColors.RED + "error"
            case logging.CRITICAL:
                name = _colorize.ANSIColors.BOLD_RED + "critical"
            case _:
                name = _colorize.ANSIColors.RESET + "unknown"

        name += _colorize.ANSIColors.RESET

        self._style._fmt = f"{name}: %(message)s"  # noqa: SLF001
        return super().format(record)


def _get_parser() -> argparse.ArgumentParser:
    """Create a parser for the saturn CLI."""
    parser = argparse.ArgumentParser(
        prog="werr",
        description="A simple python project task runner",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )

    parser.add_argument(
        "-x",
        "--execute-parallel",
        action="store_true",
        help="Run task commands in parallel",
    )

    parser.add_argument(
        "-p",
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Python project directory (defaults to cwd)",
    )

    parser.add_argument(
        "-n",
        "--name",
        help="Name of command to filter by (runs single tool)",
    )

    parser.add_argument(
        "task",
        nargs="?",
        help="Task to run (defined in pyproject.toml, defaults to first task in config",
    )

    # Output format selection - all options write to 'reporter' dest
    # CLI is the default via set_defaults
    output_fmt = parser.add_mutually_exclusive_group()
    output_fmt.add_argument(
        "--cli",
        action="store_const",
        const="cli",
        dest="reporter",
        help="Print results to the console (default)",
    )
    output_fmt.add_argument(
        "--live",
        action="store_const",
        const="live",
        dest="reporter",
        help="Print command output to the console (no results)",
    )
    output_fmt.add_argument(
        "--xml",
        action="store_const",
        const="xml",
        dest="reporter",
        help="Print results as Junit XML",
    )
    output_fmt.add_argument(
        "--json",
        action="store_const",
        const="json",
        dest="reporter",
        help="Print results as lines of JSON",
    )
    parser.set_defaults(reporter=None)  # i.e. let the config decide

    return parser


def run(argv: list[str]) -> None:
    """Main entrypoint of the werr tool."""
    args = _get_parser().parse_args(argv)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG if args.verbose else logging.INFO)
    root_logger.addHandler(logging.StreamHandler(sys.stdout))
    root_logger.handlers[0].setFormatter(LogFormatter())
    log.debug("Called with arguments: %s", argv)

    reporter, commands = config.load_project(
        args.project / "pyproject.toml",
        cli_task=args.task,
        cli_reporter=args.reporter,
        cli_parallel=args.execute_parallel,
    )

    success = task.run(args.project, reporter, commands, args.name)

    if not success:
        sys.exit(1)
