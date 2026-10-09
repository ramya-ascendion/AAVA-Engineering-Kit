"""The layering gate, and every way it can go red.

`tools/layering.py` decides which area of the package may import which. These
prove each refusal it makes, because a gate nobody has seen fail is a comment.
The shipped tables are empty, so every test sets the ones it needs.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import layering  # noqa: E402  pylint: disable=wrong-import-position


def _tree(root: pathlib.Path, files: dict[str, str]) -> pathlib.Path:
    """A miniature package `app` holding exactly what a test needs."""
    package = root / "app"
    for where, body in files.items():
        path = package / where
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")
        for parent in path.parents:
            if parent == package.parent:
                break
            (parent / "__init__.py").touch()
    return package


@pytest.fixture(autouse=True)
def _own_package(monkeypatch):
    monkeypatch.setattr(layering, "IMPORT_NAME", "app")


def _faults(monkeypatch, tmp_path, files, **tables):
    monkeypatch.setattr(layering, "PACKAGE", _tree(tmp_path, files))
    for name, value in tables.items():
        monkeypatch.setattr(layering, name, value)
    return layering.faults()


def test_the_shipped_tables_are_empty_and_example_free():
    assert layering.CROSSINGS == {}
    assert layering.LEAVES == set()
    assert layering.TESTS_ONLY == set()
    assert layering.NO_IMPORT_AREAS == set()


def test_being_handed_nothing_fails_rather_than_passes(tmp_path, monkeypatch):
    monkeypatch.setattr(layering, "PACKAGE", tmp_path / "nowhere")
    assert any("nothing was checked" in one for one in layering.faults())


def test_a_tree_with_no_crossings_is_clean(tmp_path, monkeypatch):
    assert _faults(monkeypatch, tmp_path, {"a/x.py": "", "a/y.py": "from . import x\n"}) == []


def test_an_unnamed_crossing_is_reported(tmp_path, monkeypatch):
    bad = _faults(
        monkeypatch,
        tmp_path,
        {"billing/pay.py": "from app.users import account\n", "users/account.py": ""},
    )
    assert any("billing -> users is not a named crossing" in one for one in bad)


def test_a_named_crossing_passes_and_an_unlisted_module_does_not(tmp_path, monkeypatch):
    files = {
        "billing/pay.py": "from app.users import account\nfrom app.users import secret\n",
        "users/account.py": "",
        "users/secret.py": "",
    }
    table = {("billing", "users"): ("billing reads accounts", {"users.account"})}
    bad = _faults(monkeypatch, tmp_path, files, CROSSINGS=table)
    assert len(bad) == 1 and "users.secret" in bad[0] and "only for" in bad[0]


def test_the_plain_import_form_is_read_too(tmp_path, monkeypatch):
    """`import app.x.y` is the same edge as `from app.x import y`, and reading
    only the second made the gate blind to the first."""
    bad = _faults(
        monkeypatch,
        tmp_path,
        {"billing/pay.py": "import app.users.account\n", "users/account.py": ""},
    )
    assert any("is not a named crossing" in one for one in bad)


def test_a_leaf_may_be_imported_from_anywhere(tmp_path, monkeypatch):
    files = {"billing/pay.py": "from app.common import util\n", "common/util.py": ""}
    assert _faults(monkeypatch, tmp_path, files, LEAVES={"common"}) == []


def test_a_leaf_may_not_reach_a_non_leaf_area(tmp_path, monkeypatch):
    files = {"common/util.py": "from app.billing import pay\n", "billing/pay.py": ""}
    bad = _faults(monkeypatch, tmp_path, files, LEAVES={"common"})
    assert any("is a leaf" in one for one in bad)


def test_a_leaf_that_reaches_out_two_hops_is_caught(tmp_path, monkeypatch):
    """Checking one hop let a leaf reach another area through a named edge."""
    files = {
        "common/util.py": "from app.mid import hop\n",
        "mid/hop.py": "from app.billing import pay\n",
        "billing/pay.py": "",
    }
    table = {
        ("common", "mid"): ("named", None),
        ("mid", "billing"): ("named", None),
    }
    bad = _faults(monkeypatch, tmp_path, files, LEAVES={"common"}, CROSSINGS=table)
    assert any("it reaches" in one for one in bad)


def test_an_area_that_may_import_nothing_is_held_to_it(tmp_path, monkeypatch):
    files = {"domain/shape.py": "from app.billing import pay\n", "billing/pay.py": ""}
    bad = _faults(monkeypatch, tmp_path, files, NO_IMPORT_AREAS={"domain"})
    assert any("NO_IMPORT_AREAS" in one for one in bad)


def test_an_edge_kept_for_tests_refuses_the_areas_own_code(tmp_path, monkeypatch):
    files = {
        "db/prod.py": "from app.svc import thing\n",
        "db/tests/test_it.py": "from app.svc import thing\n",
        "svc/thing.py": "",
    }
    table = {("db", "svc"): ("tests exercise the service", None)}
    bad = _faults(
        monkeypatch, tmp_path, files, CROSSINGS=table, TESTS_ONLY={("db", "svc")}
    )
    assert len(bad) == 1 and "db/prod" in bad[0].replace(".", "/")


def test_an_import_cycle_between_modules_is_reported(tmp_path, monkeypatch):
    files = {"a/one.py": "from . import two\n", "a/two.py": "from . import one\n"}
    bad = _faults(monkeypatch, tmp_path, files)
    assert any("import cycle" in one for one in bad)


def test_an_import_of_a_module_that_does_not_exist_is_reported(tmp_path, monkeypatch):
    bad = _faults(monkeypatch, tmp_path, {"a/x.py": "from app.ghost import thing\n"})
    assert any("is no module here" in one for one in bad)


def test_a_file_that_cannot_be_parsed_is_a_fault(tmp_path, monkeypatch):
    bad = _faults(monkeypatch, tmp_path, {"a/x.py": "def broken(:\n"})
    assert any("cannot be read" in one for one in bad)


def test_the_command_exits_one_on_a_fault_and_zero_when_clean(tmp_path):
    """The gate as the hook runs it: a process with a real exit code."""
    root = tmp_path / "proj"
    (root / ".kit").mkdir(parents=True)
    (root / "tools").mkdir()
    for name in ("layering.py", "kit_config.py", "repo.py"):
        (root / "tools" / name).write_bytes((REPO / "tools" / name).read_bytes())
    (root / ".kit" / "config.env").write_text(
        'KIT_PACKAGE_DIR="src/app"\nKIT_PYTHON_PACKAGE="app"\n'
    )
    _tree(root / "src", {"a/x.py": "", "b/y.py": "from app.a import x\n"})

    def run():
        return subprocess.run(
            [sys.executable, "tools/layering.py"],
            cwd=root,
            capture_output=True,
            text=True,
            check=False,
        )

    red = run()
    assert red.returncode == 1, red.stdout
    assert "b -> a is not a named crossing" in red.stdout

    (root / "src" / "app" / "b" / "y.py").write_text("")
    green = run()
    assert green.returncode == 0, green.stdout
