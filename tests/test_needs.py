"""Test task dependency (needs) execution."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

from werrlib import config, report, task
from werrlib.cmd import Command

if TYPE_CHECKING:
    from pathlib import Path


def _make_task(
    name: str,
    *,
    needs: config.Task | None = None,
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
    test = _make_task("test", needs=build)

    order: list[str] = []

    def mock_run(_proj, _reporter, cmds, _nf, *, parallel=False):  # noqa: ARG001
        order.append(cmds[0].name)
        return True

    with patch("werrlib.task.run", side_effect=mock_run):
        result = task.run_tree(tmp_path, test)

    assert result is True
    assert order == ["build", "test"]


def test_dep_failure_skips_leaf(tmp_path: Path) -> None:
    """When a dependency fails, the leaf task is not run."""
    build = _make_task("build")
    test = _make_task("test", needs=build)

    call_count = 0

    def mock_run(_proj, _reporter, cmds, _nf, *, parallel=False):  # noqa: ARG001
        nonlocal call_count
        call_count += 1
        return False  # build fails

    with patch("werrlib.task.run", side_effect=mock_run):
        result = task.run_tree(tmp_path, test)

    assert result is False
    assert call_count == 1  # only build was attempted


def test_transitive_deps(tmp_path: Path) -> None:
    """Transitive chain: C needs B needs A."""
    a = _make_task("a")
    b = _make_task("b", needs=a)
    c = _make_task("c", needs=b)

    order: list[str] = []

    def mock_run(_proj, _reporter, cmds, _nf, *, parallel=False):  # noqa: ARG001
        order.append(cmds[0].name)
        return True

    with patch("werrlib.task.run", side_effect=mock_run):
        result = task.run_tree(tmp_path, c)

    assert result is True
    assert order == ["a", "b", "c"]


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

    t = config.load_task(pyproject, cli_task="test", cli_reporter="json")

    assert isinstance(t.reporter, report.JsonReporter)
    assert t.needs is not None
    assert isinstance(t.needs.reporter, report.JsonReporter)


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

    t = config.load_task(pyproject, cli_task="test", cli_parallel=True)

    assert t.parallel is True
    assert t.needs is not None
    assert t.needs.parallel is False


def test_name_filter_applies_to_all(tmp_path: Path) -> None:
    """name_filter is passed through to all tasks via run_tree."""
    build = _make_task(
        "build", commands=[Command(["make"]), Command(["make", "install"])]
    )
    test_t = _make_task("test", needs=build)

    calls: list[tuple[str, str | None]] = []

    def mock_run(_proj, _reporter, cmds, nf, *, parallel=False):  # noqa: ARG001
        calls.append((cmds[0].name, nf))
        return True

    with patch("werrlib.task.run", side_effect=mock_run):
        task.run_tree(tmp_path, test_t, "make")

    assert calls[0] == ("make", "make")
    assert calls[1] == ("test", "make")


def test_no_deps_works(tmp_path: Path) -> None:
    """Tasks with no needs still work through run_tree."""
    check = _make_task("check")

    def mock_run(_proj, _reporter, cmds, _nf, *, parallel=False):  # noqa: ARG001
        return True

    with patch("werrlib.task.run", side_effect=mock_run):
        result = task.run_tree(tmp_path, check)

    assert result is True
