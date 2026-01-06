import argparse
import logging
import sys
from pathlib import Path

from rich_argparse import RichHelpFormatter

from . import check, report

log = logging.getLogger("cli")


def _get_parser() -> argparse.ArgumentParser:
    """Create a parser for the saturn CLI."""
    RichHelpFormatter.styles["argparse.args"] = "cyan"
    RichHelpFormatter.styles["argparse.prog"] = "bold cyan"
    RichHelpFormatter.styles["argparse.groups"] = "bold green"
    RichHelpFormatter.styles["argparse.syntax"] = "magenta"

    parser = argparse.ArgumentParser(
        prog="pls",
        description="🪐 the simple python project task runner",
        formatter_class=RichHelpFormatter,
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")

    parser.add_argument(
        "-p",
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Python project directory (defaults to cwd)",
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
    """Main entrypoint of the plscheck tool."""
    args = _get_parser().parse_args(argv)

    logging.basicConfig(
        format="[%(levelname)s] %(message)s",
        level=logging.DEBUG if args.verbose else logging.INFO,
    )
    log.debug("Called with arguments: %s", argv)

    success = check.default(args.project, args.reporter)
    if not success:
        sys.exit(1)
