"""Test task dependency (needs) execution."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, call, patch

from werrlib import cli, config, report
from werrlib.cmd import Command

if TYPE_CHECKING:
    from pathlib import Path


def _make_task(
    name: str,
    *,
    needs: tuple[str, ...] = (),
    parallel: bool = False,
    reporter: report.Reporter | None = None,
    commands: list[Command] | None = None,
) -> config.Task:
    """Create a Task for testing."""
    return config.Task(
        name=name,
        reporter=reporter or report.CliReporter(),
        commands=commands if commands is not None else [Command([name])],
        parallel=parallel,
        project_name="test",
        needs=needs,
    )


# --- Dependency ordering ---


def test_deps_run_before_leaf(tmp_path: Path) -> None:
    """Dependencies run before the leaf task."""
    build = _make_task("build")
    test = _make_task("test", needs=("build",))
    all_tasks = {"build": build, "test": test}

    order: list[str] = []

    def mock_run(_proj, _reporter, cmds, _nf, *, parallel=False):  # noqa: ARG001
        order.append(cmds[0].name)
        return True

    with patch("werrlib.cli.task.run", side_effect=mock_run):
        result = cli._run_with_needs(tmp_path, test, all_tasks, None)

    assert result is True
    assert order == ["build", "test"]


def test_dep_failure_skips_leaf(tmp_path: Path) -> None:
    """When a dependency fails, the leaf task is not run."""
    build = _make_task("build")
    test = _make_task("test", needs=("build",))
    all_tasks = {"build": build, "test": test}

    call_count = 0

    def mock_run(_proj, _reporter, cmds, _nf, *, parallel=False):  # noqa: ARG001
        nonlocal call_count
        call_count += 1
        return False  # build fails

    with patch("werrlib.cli.task.run", side_effect=mock_run):
        result = cli._run_with_needs(tmp_path, test, all_tasks, None)

    assert result is False
    assert call_count == 1  # only build was attempted


def test_diamond_deps_run_once(tmp_path: Path) -> None:
    """Diamond dependency: shared dep runs exactly once."""
    #   check
    #   /   \
    # build  lint
    #   \   /
    #   compile
    compile_t = _make_task("compile")
    build = _make_task("build", needs=("compile",))
    lint = _make_task("lint", needs=("compile",))
    check = _make_task("check", needs=("build", "lint"))
    all_tasks = {
        "compile": compile_t,
        "build": build,
        "lint": lint,
        "check": check,
    }

    order: list[str] = []

    def mock_run(_proj, _reporter, cmds, _nf, *, parallel=False):  # noqa: ARG001
        order.append(cmds[0].name)
        return True

    with patch("werrlib.cli.task.run", side_effect=mock_run):
        result = cli._run_with_needs(tmp_path, check, all_tasks, None)

    assert result is True
    assert order.count("compile") == 1
    assert "check" in order
    assert order[-1] == "check"


def test_aggregation_task(tmp_path: Path) -> None:
    """Task with needs but no commands succeeds after deps pass."""
    build = _make_task("build")
    lint = _make_task("lint")
    check = _make_task("check", needs=("build", "lint"), commands=[])
    all_tasks = {"build": build, "lint": lint, "check": check}

    def mock_run(_proj, _reporter, cmds, _nf, *, parallel=False):  # noqa: ARG001
        return True

    with patch("werrlib.cli.task.run", side_effect=mock_run):
        result = cli._run_with_needs(tmp_path, check, all_tasks, None)

    assert result is True


def test_cli_reporter_override_applies_to_all(tmp_path: Path) -> None:
    """CLI reporter override applies to all tasks in the chain."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.build = ["make"]
task.test = [
    {needs = "build"},
    "pytest",
]
"""
    )

    task, all_tasks = config.load_task(pyproject, cli_task="test", cli_reporter="json")

    assert isinstance(task.reporter, report.JsonReporter)
    assert isinstance(all_tasks["build"].reporter, report.JsonReporter)


def test_cli_parallel_override_applies_to_leaf_only(tmp_path: Path) -> None:
    """CLI parallel override applies only to the leaf task."""
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        """
[project]
name = "testproject"

[tool.werr]
task.build = ["make"]
task.test = [
    {needs = "build"},
    "pytest",
]
"""
    )

    task, all_tasks = config.load_task(pyproject, cli_task="test", cli_parallel=True)

    assert task.parallel is True
    assert all_tasks["build"].parallel is False


def test_name_filter_only_applies_to_leaf(tmp_path: Path) -> None:
    """name_filter is only passed to the leaf task, not deps."""
    build = _make_task("build", commands=[Command(["make"]), Command(["make", "install"])])
    test = _make_task("test")
    test_with_needs = _make_task("test", needs=("build",))
    all_tasks = {"build": build, "test": test_with_needs}

    calls: list[tuple[str, str | None]] = []

    def mock_run(_proj, _reporter, cmds, nf, *, parallel=False):  # noqa: ARG001
        calls.append((cmds[0].name, nf))
        return True

    with patch("werrlib.cli.task.run", side_effect=mock_run):
        cli._run_with_needs(tmp_path, test_with_needs, all_tasks, "test")

    # build should get nf=None, test should get nf="test"
    assert calls[0] == ("make", None)
    assert calls[1] == ("test", "test")


def test_no_deps_works(tmp_path: Path) -> None:
    """Tasks with no needs still work through _run_with_needs."""
    check = _make_task("check")
    all_tasks = {"check": check}

    def mock_run(_proj, _reporter, cmds, _nf, *, parallel=False):  # noqa: ARG001
        return True

    with patch("werrlib.cli.task.run", side_effect=mock_run):
        result = cli._run_with_needs(tmp_path, check, all_tasks, None)

    assert result is True
