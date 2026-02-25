"""Test task dependency (needs) execution."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from werrlib import config, report, task
from werrlib.cmd import Command

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path
    from unittest.mock import MagicMock


@pytest.fixture
def mock_run() -> Iterator[MagicMock]:
    """Patch task.run via patch.object, yielding the mock."""
    with patch.object(task, "run") as m:
        yield m


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
        dependency=needs,
    )


# --- Dependency ordering ---


def test_deps_run_before_leaf(tmp_path: Path, mock_run: MagicMock) -> None:
    """Dependencies run before the leaf task, sharing the target reporter."""
    build = _make_task("build", reporter=report.CliReporter())
    test = _make_task("test", needs=build, reporter=report.JsonReporter())

    order: list[str] = []
    reporters: list[report.Reporter] = []

    def _side_effect(
        _proj: Path, reporter: report.Reporter, cmds: list[Command],
        _nf: str | None, *, _parallel: bool = False,
    ) -> bool:
        order.append(cmds[0].name)
        reporters.append(reporter)
        return True

    mock_run.side_effect = _side_effect
    result = task.run_tree(tmp_path, test)

    assert result is True
    assert order == ["build", "test"]
    # run_tree uses target.reporter for all deps
    assert all(isinstance(r, report.JsonReporter) for r in reporters)


def test_dep_failure_skips_leaf(tmp_path: Path, mock_run: MagicMock) -> None:
    """When a dependency fails, the leaf task is not run."""
    build = _make_task("build")
    test = _make_task("test", needs=build)

    names: list[str] = []

    def _side_effect(
        _proj: Path, _reporter: report.Reporter, cmds: list[Command],
        _nf: str | None, *, _parallel: bool = False,
    ) -> bool:
        names.append(cmds[0].name)
        return False  # build fails

    mock_run.side_effect = _side_effect
    result = task.run_tree(tmp_path, test)

    assert result is False
    assert names == ["build"]  # only build was attempted


def test_transitive_deps(tmp_path: Path, mock_run: MagicMock) -> None:
    """Transitive chain: C needs B needs A."""
    a = _make_task("a")
    b = _make_task("b", needs=a)
    c = _make_task("c", needs=b)

    order: list[str] = []

    def _side_effect(
        _proj: Path, _reporter: report.Reporter, cmds: list[Command],
        _nf: str | None, *, _parallel: bool = False,
    ) -> bool:
        order.append(cmds[0].name)
        return True

    mock_run.side_effect = _side_effect
    result = task.run_tree(tmp_path, c)

    assert result is True
    assert order == ["a", "b", "c"]


def test_cli_reporter_override_on_target(tmp_path: Path) -> None:
    """CLI reporter override is set on the target task."""
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

    _, t = config.load_task(pyproject, cli_task="test", cli_reporter="json")

    # run_tree uses target.reporter for all deps, so only the target matters
    assert isinstance(t.reporter, report.JsonReporter)


def test_cli_parallel_override_applies_to_leaf_only(tmp_path: Path) -> None:
    """CLI parallel override applies only to the leaf task.

    run_tree uses dep.parallel for each task, so verifying the data model
    ensures the right runtime behaviour.
    """
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

    _, t = config.load_task(pyproject, cli_task="test", cli_parallel=True)

    assert t.parallel is True
    assert t.dependency is not None
    assert t.dependency.parallel is False


def test_name_filter_applies_to_all(tmp_path: Path, mock_run: MagicMock) -> None:
    """name_filter is passed through to all tasks via run_tree."""
    build = _make_task(
        "build", commands=[Command(["make"]), Command(["make", "install"])]
    )
    test_t = _make_task("test", needs=build)

    calls: list[tuple[str, str | None]] = []

    def _side_effect(
        _proj: Path, _reporter: report.Reporter, cmds: list[Command],
        nf: str | None, *, _parallel: bool = False,
    ) -> bool:
        calls.append((cmds[0].name, nf))
        return True

    mock_run.side_effect = _side_effect
    task.run_tree(tmp_path, test_t, "make")

    assert calls[0] == ("make", "make")
    assert calls[1] == ("test", "make")


def test_no_deps_works(tmp_path: Path, mock_run: MagicMock) -> None:
    """Tasks with no needs still work through run_tree."""
    check = _make_task("check")

    mock_run.return_value = True
    result = task.run_tree(tmp_path, check)

    assert result is True
