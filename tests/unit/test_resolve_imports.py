"""Whether `tools/resolve_imports.py` still catches a broken app import.

The gate it feeds is only worth having if it fails on a tree that cannot run.
This proves both halves: the real tree resolves, and a planted bad import is
reported rather than passed over.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO / "tools"))

import resolve_imports  # noqa: E402  pylint: disable=wrong-import-position


class TestTheTreeHangsTogether:
    """The check over the repository as it stands."""

    def test_every_import_in_the_repository_resolves(self) -> None:
        """A failure here names the file and line, so it is actionable as printed."""
        fails = resolve_imports.check(REPO)
        assert fails == [], "unresolved app imports:\n  " + "\n  ".join(fails)

    def test_a_script_run_finds_the_helpers_pytest_ini_names(self) -> None:
        """The pre-commit gate runs the tool as a script, so pytest's path is unset.

        A test module imports `exam_harness` from a directory `pytest.ini` names.
        Dropping those entries first is what the script's process looks like.
        """
        extra = [
            str(REPO / part)
            for part in ("tests", "tests/unit")
            if (REPO / part).is_dir()
        ]
        held = [entry for entry in sys.path if entry in extra]
        sys.path[:] = [entry for entry in sys.path if entry not in extra]
        try:
            assert resolve_imports.check(REPO) == []
        finally:
            sys.path[0:0] = held


class TestABrokenImportIsReported:
    """The half that makes the green run mean something."""

    @pytest.fixture
    def tree(self, tmp_path: pathlib.Path):
        """A tree holding one file, so the planted break is the only find.

        The tiny `app` package here is what the checked imports resolve against.
        """
        package = tmp_path / "src" / "app"
        (package / "lookups").mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "lookups" / "__init__.py").write_text("", encoding="utf-8")
        (package / "lookups" / "named.py").write_text("class Found:\n    pass\n")
        yield tmp_path
        for name in [one for one in sys.modules if one == "app" or one.startswith("app.")]:
            del sys.modules[name]

    def test_a_module_that_does_not_exist_is_named(self, tree: pathlib.Path) -> None:
        """The shape a rename leaves behind when a caller is missed."""
        (tree / "caller.py").write_text(
            "from app.nowhere.at_all import Thing\n", encoding="utf-8"
        )
        fails = resolve_imports.check(tree)
        assert len(fails) == 1
        assert "caller.py:1" in fails[0]
        assert "app.nowhere.at_all" in fails[0]

    def test_another_sessions_worktree_is_not_walked(self, tree: pathlib.Path) -> None:
        """A worktree under `.claude` is another branch's checkout, not this tree."""
        worktree = tree / ".claude" / "worktrees" / "stale"
        worktree.mkdir(parents=True)
        (worktree / "caller.py").write_text(
            "from app.nowhere.at_all import Thing\n", encoding="utf-8"
        )
        assert not resolve_imports.check(tree)

    def test_a_name_missing_from_a_real_module_is_named(
        self, tree: pathlib.Path
    ) -> None:
        """The shape that a module-only check passes and this one does not.

        `app.lookups` is a package, so it resolves. `Found` lives in the
        `app.lookups.named` module inside it, so importing `Found` from
        the package is the mistake a module-level check cannot see.
        """
        (tree / "caller.py").write_text(
            "from app.lookups import Found\n", encoding="utf-8"
        )
        fails = resolve_imports.check(tree)
        assert len(fails) == 1
        assert "'Found'" in fails[0]


class TestTheCommandLine:
    """What the pre-commit gate actually calls."""

    def test_a_clean_tree_exits_zero_and_says_so(self, capsys) -> None:
        """The gate reads the exit code; a person reads the line."""
        assert resolve_imports.main() == 0
        assert "every import of the project package resolves" in capsys.readouterr().out

    def test_the_path_entry_does_not_accumulate(self) -> None:
        """Two calls in one process must not leave two entries behind.

        This proves path hygiene and nothing more. Resolution itself is decided
        by `sys.modules`, which `check` does not clear, so the leak was never
        what made a second call see the first call's modules.
        """
        before = list(sys.path)
        resolve_imports.check(REPO)
        resolve_imports.check(REPO)
        assert sys.path == before
