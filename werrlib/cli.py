import _colorize
import argparse
import logging
import sys
from pathlib import Path

from . import report, task

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


def _get_parser() -> argparse.ArgumentParser:
    """Create a parser for the saturn CLI."""
    parser = argparse.ArgumentParser(
        prog="werr",
        description="A simple python project task runner",
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    parser.add_argument(
        "-p",
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Python project directory (defaults to cwd)",
    )

    parser.add_argument(
        "task",
        nargs="?",
        default=task.DEFAULT,
        help=f"Task to run (defined in pyproject.toml, defaults to '{task.DEFAULT}')",
    )

    # Output format selection - all options write to 'reporter' dest
    # CLI is the default via set_defaults
    output_fmt = parser.add_mutually_exclusive_group()
    output_fmt.add_argument(
        "--cli",
        action="store_const",
        const=report.CliReporter,
        dest="reporter",
        help="Print results to the console (default)",
    )
    output_fmt.add_argument(
        "--xml",
        action="store_const",
        const=report.XmlReporter,
        dest="reporter",
        help="Print results as Junit XML",
    )
    output_fmt.add_argument(
        "--json",
        action="store_const",
        const=report.JsonReporter,
        dest="reporter",
        help="Print results as lines of JSON",
    )
    parser.set_defaults(reporter=report.CliReporter)

    return parser


def run(argv: list[str]) -> None:
    """Main entrypoint of the werr tool."""
    args = _get_parser().parse_args(argv)

    logging.basicConfig(
        format="[%(levelname)s] %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )
    log.debug("Called with arguments: %s", argv)

    success = task.run(args.project, args.task, args.reporter)
    if not success:
        sys.exit(1)
