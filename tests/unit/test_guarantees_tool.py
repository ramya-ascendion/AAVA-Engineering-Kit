"""What `tools/guarantees.py` does, and what it refuses to conclude .

The tool exists because a docstring can claim more than the code delivers. It
is worth no more than its own correctness: a check that cannot fail is the
thing it was built to find, so the cases here are mostly about the ways it
could report `proved` without having measured anything.

**`tools/` is outside the coverage and CRAP bars** — `--source=src/app` does
not reach it — so this file is the only thing standing between the tool and
rot. `docs/agents/guarantees.md` says so in as many words.

**Most cases never start pytest.** `_judge` takes two runs and returns a
result, so the verdict logic is driven with runs built by hand; only the
handful about the subprocess itself pay for a real one. Sixteen cases each
forking two pytest runs would put thirty-two interpreter starts in the suite
every commit runs, which is the cost this design was shaped to avoid.

They start no server and reach no network.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
import threading
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import guarantee_proofs  # noqa: E402  # pylint: disable=wrong-import-position
import guarantee_results  # noqa: E402  # pylint: disable=wrong-import-position
import guarantees  # noqa: E402  # pylint: disable=wrong-import-position


def a_run(code, **outcomes):
    """One pytest run's report, without running pytest.

    `outcomes` maps a node id to an `element:message` pair, so a case reads as
    the thing it is testing rather than as a dictionary literal.
    """
    return guarantees.Ran(
        code,
        {
            nodeid.replace("__", "::"): tuple(spelled.split(":", 1))
            for nodeid, spelled in outcomes.items()
        },
    )


AN_ENTRY = {
    "guarantee": "**It holds.**",
    "file": "src/tiny/thing.py",
    "symbol": "keep",
    "guard": "if guarded:",
    "replaced_by": "if True:",
    "removes": "the guard",
    "fails_with": "AssertionError",
    "tests": ["tests/test_thing.py::test_it_holds"],
}

A_PACKAGE = '''"""A tiny module with one guarantee in it."""


def keep(guarded):
    """**It holds.**"""
    if guarded:
        return "kept"
    return "not kept"
'''

A_SUITE = """
from tiny.thing import keep


def test_it_holds():
    assert keep(False) == "not kept"
"""


@pytest.fixture(name="tree")
def _tree(tmp_path):
    """A whole little project: a package, a suite, and a pytest to find them.

    Built once per test rather than once per module, because half the cases
    mutate it. It is four files, so the cost is the pytest runs and not this.
    """
    (tmp_path / "src" / "tiny").mkdir(parents=True)
    (tmp_path / "src" / "tiny" / "__init__.py").write_text("")
    (tmp_path / "src" / "tiny" / "thing.py").write_text(A_PACKAGE)
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_thing.py").write_text(A_SUITE)
    (tmp_path / "pytest.ini").write_text("[pytest]\ntestpaths = tests\n")
    return tmp_path


class TestFindingTheCodeAnEntryNames:
    """A span, because everything else is measured inside one."""

    def test_a_span_starts_at_the_first_decorator(self):
        """`@dataclass(frozen=True)` is the guard of the ticket's own first
        criterion, and `ClassDef.lineno` does not include it."""
        source = textwrap.dedent("""
            @decorated
            @twice
            class Thing:
                pass
            """).strip()

        assert guarantees.span_of(source, "Thing") == (1, 4)

    def test_an_async_def_is_found(self):
        """`Investigation.run` is one, and `ast.FunctionDef` does not match it."""
        assert guarantees.span_of("async def run():\n    pass\n", "run") == (1, 2)

    def test_a_dotted_symbol_is_matched_on_its_last_part(self):
        source = "class Holder:\n    def run(self):\n        pass\n"

        assert guarantees.span_of(source, "Holder.run") == (2, 3)

    def test_a_symbol_that_is_gone_is_not_guessed_at(self):
        assert guarantees.span_of("x = 1\n", "vanished") is None

    def test_a_borrowed_literal_is_read_from_its_own_symbol(self, tmp_path):
        """Two functions, the same keyword, different values: the entry gets the
        one inside the symbol it named, not the first in the file."""
        module = tmp_path / "bounds.py"
        module.write_text(
            "def elsewhere():\n"
            "    wait(timeout=5)\n"
            "\n"
            "def here():\n"
            "    wait(timeout=30)\n"
        )

        assert guarantees.literal_in_span(module, "here", "timeout") == 30


class TestRemovingTheGuard:
    """The mutation, which has to remove one thing and nothing else."""

    def test_only_the_named_symbols_copy_is_replaced(self):
        """`@dataclass(frozen=True)` appears three times in `evidence.py`. A
        whole-file replace would unfreeze two other classes, and the entry would
        be measuring them too."""
        source = textwrap.dedent("""
            @dataclass(frozen=True)
            class Other:
                pass


            @dataclass(frozen=True)
            class Wanted:
                pass
            """).strip()
        entry = {
            "symbol": "Wanted",
            "guard": "@dataclass(frozen=True)",
            "replaced_by": "@dataclass()",
        }

        mutated = guarantees._mutated(source, entry)

        assert mutated.count("@dataclass(frozen=True)") == 1
        assert "@dataclass()\nclass Wanted:" in mutated

    def test_a_guard_that_is_not_there_removes_nothing(self):
        """A zero-substitution no-op would read as `unproved` — a guarantee
        accused of being decoration by a run that never touched it."""
        entry = {"symbol": "Thing", "guard": "if gone:", "replaced_by": "if True:"}

        assert guarantees._mutated("class Thing:\n    pass\n", entry) is None

    def test_a_mutation_that_will_not_parse_is_refused(self):
        entry = {"symbol": "keep", "guard": "return 1", "replaced_by": "return return"}

        assert guarantees._mutated("def keep():\n    return 1\n", entry) is None


class TestTheVerdict:
    """Every way a run can come back, and what the tool is allowed to conclude.

    This is where the tool is most dangerous, because every mistake here is a
    `proved` it did not earn.
    """

    def test_red_on_the_named_test_is_proved(self):
        before = a_run(0, tests__a_py__test_it="passed:")
        after = a_run(1, tests__a_py__test_it="failure:AssertionError: nope")
        entry = {**AN_ENTRY, "tests": ["tests::a_py::test_it"]}

        assert guarantees._judge(entry, before, after)[0] == guarantees.PROVED

    def test_green_under_the_mutation_is_unproved(self):
        before = a_run(0, tests__a_py__test_it="passed:")
        after = a_run(0, tests__a_py__test_it="passed:")
        entry = {**AN_ENTRY, "tests": ["tests::a_py::test_it"]}

        assert guarantees._judge(entry, before, after)[0] == guarantees.UNPROVED

    @pytest.mark.parametrize("code", [2, 3, 4, 5])
    def test_a_non_zero_exit_that_is_not_a_failure_is_broken(self, code):
        """**The defect this tool exists to find, rebuilt inside it.** pytest
        exits 2 on a collection error, 4 on a bad node id and 5 on nothing
        collected. Reading a bare non-zero as success would report every
        guarantee in a file as proved the moment a mutation stopped it
        importing."""
        before = a_run(0, tests__a_py__test_it="passed:")
        entry = {**AN_ENTRY, "tests": ["tests::a_py::test_it"]}

        assert guarantees._judge(entry, before, a_run(code))[0] == guarantees.BROKEN

    def test_an_error_rather_than_a_failure_is_broken(self):
        """A fixture blowing up is reported as ERROR and still exits 1."""
        before = a_run(0, tests__a_py__test_it="passed:")
        after = a_run(1, tests__a_py__test_it="error:fixture 'thing' not found")
        entry = {**AN_ENTRY, "tests": ["tests::a_py::test_it"]}

        assert guarantees._judge(entry, before, after)[0] == guarantees.BROKEN

    def test_a_skipped_proof_is_broken_rather_than_passed(self):
        """A skip that reads as a pass is the shape this ticket is about, and
        `tests/conftest.py` skips on the `live` marker."""
        before = a_run(0, tests__a_py__test_it="skipped:needs a service")
        entry = {**AN_ENTRY, "tests": ["tests::a_py::test_it"]}

        assert guarantees._judge(entry, before, a_run(1))[0] == guarantees.BROKEN

    def test_a_failure_the_entry_did_not_predict_is_broken(self):
        """Red for the wrong reason. The tool cannot tell a guarantee from a
        timeout unless the entry says which it expects."""
        before = a_run(0, tests__a_py__test_it="passed:")
        after = a_run(1, tests__a_py__test_it="failure:TimeoutError")
        entry = {**AN_ENTRY, "tests": ["tests::a_py::test_it"]}

        result, why = guarantees._judge(entry, before, after)

        assert result == guarantees.BROKEN
        assert "TimeoutError" in why

    def test_any_listed_spelling_of_the_failure_matches(self):
        """`asyncio.TimeoutError` became an alias of the builtin in 3.11 and
        `pyproject.toml` declares a 3.10 floor, so one failure has two
        spellings and only one can ever match on a given interpreter."""
        before = a_run(0, tests__a_py__test_it="passed:")
        after = a_run(1, tests__a_py__test_it="failure:asyncio.exceptions.TimeoutError")
        entry = {
            **AN_ENTRY,
            "tests": ["tests::a_py::test_it"],
            "fails_with": ["TimeoutError", "asyncio.exceptions.TimeoutError"],
        }

        assert guarantees._judge(entry, before, after)[0] == guarantees.PROVED

    def test_a_proof_that_never_ran_is_broken(self):
        before = a_run(0)
        entry = {**AN_ENTRY, "tests": ["tests::a_py::test_it"]}

        assert guarantees._judge(entry, before, a_run(1))[0] == guarantees.BROKEN

    def test_a_killed_run_is_broken_and_never_a_satisfied_timeout(self):
        """A subprocess killed by its own timeout writes no XML at all. A
        guarantee proved by missing evidence is not proved."""
        before = a_run(0, tests__a_py__test_it="passed:")
        entry = {
            **AN_ENTRY,
            "tests": ["tests::a_py::test_it"],
            "fails_with": "TimeoutError",
        }

        assert guarantees._judge(entry, before, None)[0] == guarantees.BROKEN

    def test_every_parameter_of_a_parametrized_proof_has_to_fail(self):
        """The entry names the function; pytest expands it. One parameter going
        red is not the test going red."""
        before = a_run(
            0,
            tests__a_py__test_it_0="passed:",
            tests__a_py__test_it_1="passed:",
        )
        after = a_run(
            1,
            tests__a_py__test_it_0="failure:AssertionError: nope",
            tests__a_py__test_it_1="passed:",
        )
        for run in (before, after):
            run.outcomes["tests::a_py::test_it[one]"] = run.outcomes.pop(
                "tests::a_py::test_it_0"
            )
            run.outcomes["tests::a_py::test_it[two]"] = run.outcomes.pop(
                "tests::a_py::test_it_1"
            )
        entry = {**AN_ENTRY, "tests": ["tests::a_py::test_it"]}

        assert guarantees._judge(entry, before, after)[0] == guarantees.BROKEN


class TestRebuildingANodeId:
    """The join between what the list says and what pytest reported."""

    def test_a_module_level_test_rebuilds_without_an_empty_segment(self, tmp_path):
        """`classname` is just the dotted module for a test outside a class, so
        joining it whole gives `test_x.py::::test_y` and matches nothing. There
        are twenty-one such tests in `test_client_gate.py` alone."""
        report = tmp_path / "j.xml"
        report.write_text(
            "<testsuites><testsuite><testcase "
            'classname="tests.unit.test_thing" name="test_it" '
            'file="tests/unit/test_thing.py" /></testsuite></testsuites>'
        )

        assert list(guarantee_proofs._node_ids(report)) == [
            "tests/unit/test_thing.py::test_it"
        ]

    def test_an_enclosing_class_is_kept(self, tmp_path):
        report = tmp_path / "j.xml"
        report.write_text(
            "<testsuites><testsuite><testcase "
            'classname="tests.unit.test_thing.TestIt" name="test_it" '
            'file="tests/unit/test_thing.py" /></testsuite></testsuites>'
        )

        assert list(guarantee_proofs._node_ids(report)) == [
            "tests/unit/test_thing.py::TestIt::test_it"
        ]


class TestTheEnvironmentAProofRunsIn:
    """The one failure mode of measuring a copy, and it looks like success."""

    def test_pythonpath_is_replaced_and_not_extended(self, tmp_path):
        """`activate_venv` exports the main checkout's `src` before any gate
        runs. Inherited, it would let pytest import the unmutated `app` while
        the tool edits a copy nobody reads, and every entry would read
        `unproved` with nothing wrong."""
        kept = guarantees.os.environ.get("PYTHONPATH")
        guarantees.os.environ["PYTHONPATH"] = "/somewhere/else/src"
        try:
            built = guarantee_proofs._clean_env(tmp_path)
        finally:
            if kept is None:
                del guarantees.os.environ["PYTHONPATH"]
            else:
                guarantees.os.environ["PYTHONPATH"] = kept

        assert built["PYTHONPATH"] == str(tmp_path / "src")

    def test_coverage_is_scrubbed_wholesale(self, tmp_path):
        """`a1_coverage.pth` arms subprocess coverage on `COVERAGE_PROCESS_START`
        *or* `COVERAGE_PROCESS_CONFIG`, so naming two variables leaves a third
        arming it."""
        guarantees.os.environ["COVERAGE_PROCESS_CONFIG"] = "somewhere"
        try:
            built = guarantee_proofs._clean_env(tmp_path)
        finally:
            del guarantees.os.environ["COVERAGE_PROCESS_CONFIG"]

        assert not [name for name in built if name.startswith("COVERAGE_")]

    def test_git_is_scrubbed_wholesale(self, tmp_path, monkeypatch):
        """`pre-push` exports `GIT_DIR`, and a proof that runs git in a scratch
        repository under it would act on the real one — the damage this change
        once did to its own checkout, one layer down."""
        monkeypatch.setenv("GIT_DIR", str(tmp_path / "somewhere" / ".git"))
        monkeypatch.setenv("GIT_INDEX_FILE", str(tmp_path / "index"))

        built = guarantee_proofs._clean_env(tmp_path)

        assert not [name for name in built if name.startswith("GIT_")]


class TestAWholeEntry:
    """The tool end to end, against a project small enough to reason about."""

    def test_a_guarantee_with_a_real_proof_is_proved(self, tree):
        """**The positive control.** Every other case here asserts red, and a
        tool that always reported `broken` would satisfy all of them."""
        result, why = guarantees.measure(tree, [AN_ENTRY])[0][1:]

        assert result == guarantees.PROVED, why

    def test_a_guarantee_nothing_defends_is_unproved(self, tree):
        """The defect the tool is for: the claim is real, the test does not
        reach it, and removing the guard changes nothing."""
        (tree / "tests" / "test_thing.py").write_text(
            "\nfrom tiny.thing import keep\n\n\n"
            "def test_it_holds():\n    assert keep(True) == 'kept'\n"
        )

        result, _ = guarantees.measure(tree, [AN_ENTRY])[0][1:]

        assert result == guarantees.UNPROVED

    def test_a_mutation_that_breaks_the_import_is_broken_not_proved(self, tree):
        """pytest exits 2 on a collection error, and every test in the file
        errors at once. This is the case that would turn a whole module's
        guarantees green."""
        entry = {**AN_ENTRY, "replaced_by": "if guarded and:"}

        result, _ = guarantees.measure(tree, [entry])[0][1:]

        assert result == guarantees.BROKEN

    def test_no_mutation_reaches_another_entry(self, tree, monkeypatch):
        """Without a tree each, one entry's mutation is on disk when another
        reads its file, and the other measures both.

        The two entries are held in the one order that shows it: the first
        stays inside its mutated run until the second has read its own file.
        pytest is stubbed, so the order is forced rather than hoped for.
        """
        original = (tree / "src" / "tiny" / "thing.py").read_text()
        mutated = threading.Event()
        read = threading.Event()
        started = []
        seen = []
        lock = threading.Lock()
        runs = threading.local()

        def stub(own, ids, _timeout):
            runs.count = getattr(runs, "count", 0) + 1
            if runs.count == 1:
                with lock:
                    started.append(own)
                    second = len(started) == 2
                if second:
                    assert mutated.wait(10)
                    seen.append((own / "src" / "tiny" / "thing.py").read_text())
                    read.set()
                return guarantees.Ran(0, {ids[0]: ("passed", "")})
            if not mutated.is_set():
                mutated.set()
                assert read.wait(10)
            return guarantees.Ran(1, {ids[0]: ("failure", "AssertionError")})

        monkeypatch.setattr(guarantees, "run_tests", stub)

        results = guarantees.measure(tree, [AN_ENTRY] * 2, workers=2)

        assert seen == [original]
        assert [result for _, result, _ in results] == [guarantees.PROVED] * 2
        assert (tree / "src" / "tiny" / "thing.py").read_text() == original

    def test_an_excused_entry_is_not_measured(self, tree):
        excused = {
            "guarantee": "**It cannot be tested.**",
            "file": "src/tiny/thing.py",
            "symbol": "keep",
            "reason": "the thing it describes has not been built",
        }

        result, why = guarantees.measure(tree, [excused])[0][1:]

        assert result == guarantees.EXEMPT
        assert why == excused["reason"]


class TestWhatTheTempTreeNeedsThatGitCannotCarry:
    """Two things the archive cannot hold, and what happens without them."""

    def test_the_cases_are_counted_and_not_the_argument_names(self, tmp_path):
        """`parametrize` takes the argnames first, and a two-name marker spells
        them as a tuple. Counting that would measure the names."""
        module = tmp_path / "test_named.py"
        module.write_text(
            "import pytest\n\n\n"
            '@pytest.mark.parametrize(("first", "second"), [(1, 2), (3, 4), (5, 6)])\n'
            "def test_it(first, second):\n    pass\n"
        )

        assert guarantees.parameters_of(module, "test_it") == 3

    def test_stacked_markers_multiply(self, tmp_path):
        module = tmp_path / "test_stacked.py"
        module.write_text(
            "import pytest\n\n\n"
            '@pytest.mark.parametrize("a", [1, 2])\n'
            '@pytest.mark.parametrize("b", [1, 2, 3])\n'
            "def test_it(a, b):\n    pass\n"
        )

        assert guarantees.parameters_of(module, "test_it") == 6

    def test_the_import_guard_holds_under_a_symlinked_root(self, tmp_path):
        """macOS hands out `/var/folders/...`, a symlink to `/private/var/...`.
        Comparing one spelling against the other would make every entry `broken`
        on this platform and nowhere else.

        Reproduced rather than asserted about: the guard is reached through a
        symlink while `app` sits under the real path, which is the shape
        `mkdtemp` hands the tool on every run here."""
        real = tmp_path / "real"
        (real / "src" / "app").mkdir(parents=True)
        (real / "src" / "app" / "__init__.py").write_text("")
        (real / "conftest.py").write_text(guarantees._GUARD_CONFTEST.replace("__PACKAGE__", "app"))
        through = tmp_path / "through"
        try:
            through.symlink_to(real)
        except OSError as refused:
            pytest.skip(f"this machine will not make a symlink: {refused}")

        finished = guarantees.subprocess.run(
            [sys.executable, str(through / "conftest.py")],
            cwd=through,
            env={**guarantees.os.environ, "PYTHONPATH": str(through / "src")},
            capture_output=True,
            text=True,
            check=False,
        )

        assert finished.returncode == 0, finished.stderr

    def test_the_import_guard_refuses_a_package_from_elsewhere(self, tmp_path):
        """The guard is the whole defense against the one failure that looks
        like success, so it is run rather than read."""
        # The other checkout has to be genuinely outside the tree. Nested under
        # it, the guard is right to accept it and this case would prove nothing.
        tree = tmp_path / "tree"
        tree.mkdir()
        guard = tree / "conftest.py"
        guard.write_text(guarantees._GUARD_CONFTEST.replace("__PACKAGE__", "app"))
        elsewhere = tmp_path / "elsewhere"
        (elsewhere / "app").mkdir(parents=True)
        (elsewhere / "app" / "__init__.py").write_text("")

        finished = guarantees.subprocess.run(
            [sys.executable, str(guard)],
            cwd=tree,
            env={**guarantees.os.environ, "PYTHONPATH": str(elsewhere)},
            capture_output=True,
            text=True,
            check=False,
        )

        assert finished.returncode != 0
        assert "outside" in finished.stderr

    def test_the_import_guard_admits_a_package_from_inside_the_tree(self, tmp_path):
        """The positive control for the guard itself. Without it the guard could
        refuse everything and every case above would still pass."""
        guard = tmp_path / "conftest.py"
        guard.write_text(guarantees._GUARD_CONFTEST.replace("__PACKAGE__", "app"))
        (tmp_path / "src" / "app").mkdir(parents=True)
        (tmp_path / "src" / "app" / "__init__.py").write_text("")

        finished = guarantees.subprocess.run(
            [sys.executable, str(guard)],
            cwd=tmp_path,
            env={**guarantees.os.environ, "PYTHONPATH": str(tmp_path / "src")},
            capture_output=True,
            text=True,
            check=False,
        )

        assert finished.returncode == 0, finished.stderr


class TestTheJunitContractTheParserDependsOn:
    """pytest's junit shape is not a documented contract, and this reads it.

    `pyproject.toml` declares `pytest>=7.0.0` — a floor rather than a pin, so
    any later pytest satisfies it. An upgrade that changed any of these would not
    fail loudly anywhere else; it would turn entries green or broken with nothing
    on screen to say why.
    """

    def test_a_testcase_carries_the_file_it_came_from(self, tmp_path):
        """`xunit1` is not optional: the default family writes only `classname`,
        which a path cannot be recovered from."""
        report = tmp_path / "j.xml"
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_records.py").write_text(
            "class TestChain:\n    def test_it(self):\n        pass\n"
        )
        guarantees.subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_records.py::TestChain",
                "-q",
                "--color=no",
                "-p",
                "no:cacheprovider",
                "-o",
                "junit_family=xunit1",
                f"--junit-xml={report}",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        rebuilt = guarantee_proofs._node_ids(report)

        assert rebuilt, "no testcase carried a `file` attribute"
        assert all(
            one.startswith(
                "tests/test_records.py::TestChain::"
            )
            for one in rebuilt
        )

    def test_a_bare_assert_reports_without_the_exception_name(self, tmp_path):
        """pytest strips `AssertionError: ` from a rewritten bare assert — but
        only when the repr happens to use single quotes. Both spellings reach
        `fails_with`, so a change here moves what an entry has to declare."""
        suite = tmp_path / "test_bare.py"
        suite.write_text("def test_it():\n    assert 1 == 2\n")
        report = tmp_path / "j.xml"
        guarantees.subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                str(suite),
                "-q",
                "--color=no",
                "-p",
                "no:cacheprovider",
                "-o",
                "junit_family=xunit1",
                f"--junit-xml={report}",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )

        reported = list(guarantee_proofs._node_ids(report).values())

        assert len(reported) == 1, f"expected one testcase, got {reported}"
        assert reported[0][1].startswith("assert ")


class TestAGuardHasToBeCode:
    """A guard matched in prose would be mutated as prose.

    The tool finds the guard by text. Text appears in comments and docstrings
    too — and `evidence.py`'s frozen guarantee is a sentence *about*
    `frozen=True`, so this is one rewording away from mattering. Matched there,
    the edit would rewrite a sentence, the tests would not move, and the entry
    would report `unproved`: a guarantee accused of being decoration because the
    tool changed a description of it.
    """

    A_MODULE = '''
def keep(guarded):
    """Guarded, and this sentence does not repeat the line that does it."""
    if guarded:
        return "kept"
    return "not kept"
'''

    def test_a_guard_matched_only_in_a_docstring_is_refused(self, tmp_path):
        (tmp_path / "src" / "tiny").mkdir(parents=True)
        (tmp_path / "src" / "tiny" / "thing.py").write_text(
            "\ndef keep(guarded):\n"
            '    """The sentence says if guarded: and the code does not."""\n'
            '    return "kept"\n'
        )
        entry = {**AN_ENTRY, "guarantee": "The sentence says"}

        problems = guarantees.check(entry, tmp_path)

        assert any("comment or a string" in one for one in problems), problems

    def test_a_guard_that_is_real_code_is_allowed(self, tmp_path):
        """The positive control. Without it the check could refuse every guard
        and the case above would still pass."""
        (tmp_path / "src" / "tiny").mkdir(parents=True)
        (tmp_path / "src" / "tiny" / "thing.py").write_text(self.A_MODULE)
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_thing.py").write_text(A_SUITE)
        entry = {**AN_ENTRY, "guarantee": "Guarded, and this sentence"}

        problems = guarantees.check(entry, tmp_path)

        assert not [one for one in problems if "comment or a string" in one], problems

    def test_a_guard_sharing_a_line_with_a_string_is_still_code(self, tmp_path):
        """The check must not refuse a guard just because its line holds a
        literal — `raise MalformedBatch("...")` is a guard like any other."""
        (tmp_path / "src" / "tiny").mkdir(parents=True)
        (tmp_path / "src" / "tiny" / "thing.py").write_text(
            "\ndef keep(guarded):\n"
            '    """Nothing here repeats the guard."""\n'
            "    if guarded:\n"
            '        raise ValueError("refused")\n'
            '    return "kept"\n'
        )
        entry = {
            **AN_ENTRY,
            "guarantee": "Nothing here repeats the guard.",
            "guard": 'raise ValueError("refused")',
        }

        problems = guarantees.check(entry, tmp_path)

        assert not [one for one in problems if "comment or a string" in one], problems


class TestOneCaseOfAParametrizedTestAsTheProof:
    """A proof is the narrowest node id that can fail, and one case of a
    parametrized test is narrower than the whole test. The run already reports
    each case under its own id, so what has to agree with it is the check that
    the proof exists and the count of how often it runs."""

    A_PARAMETRIZED_SUITE = (
        "import pytest\n\n\n"
        "class TestIt:\n"
        '    @pytest.mark.parametrize("case", [1, 2, 3])\n'
        "    def test_it_holds(self, case):\n"
        "        pass\n"
    )

    def a_tree(self, tmp_path, suite):
        (tmp_path / "src" / "tiny").mkdir(parents=True)
        (tmp_path / "src" / "tiny" / "thing.py").write_text(A_PACKAGE)
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_thing.py").write_text(suite)
        return tmp_path

    def test_a_single_case_is_a_proof_that_exists(self, tmp_path):
        tree = self.a_tree(tmp_path, self.A_PARAMETRIZED_SUITE)
        entry = {**AN_ENTRY, "tests": ["tests/test_thing.py::TestIt::test_it_holds[2]"]}

        assert guarantees.check(entry, tree) == []

    def test_a_case_of_a_test_that_is_gone_is_still_refused(self, tmp_path):
        """Stripping the case must not make every bracketed name pass."""
        tree = self.a_tree(tmp_path, self.A_PARAMETRIZED_SUITE)
        entry = {**AN_ENTRY, "tests": ["tests/test_thing.py::TestIt::test_gone[2]"]}

        problems = guarantees.check(entry, tree)

        assert any("no such test" in one for one in problems), problems

    def test_a_case_id_holding_a_double_colon_is_one_test(self, tmp_path):
        """pytest spells a case from its value, and a value can hold `::`."""
        tree = self.a_tree(tmp_path, self.A_PARAMETRIZED_SUITE)
        entry = {
            **AN_ENTRY,
            "tests": ["tests/test_thing.py::TestIt::test_it_holds[a::b]"],
        }

        assert guarantees.check(entry, tree) == []

    def test_a_case_pytest_cannot_find_is_named_as_a_bad_id(self):
        """The existence check reads the source and cannot see a case. pytest
        exits 4 on an id it cannot find, and on a usage error too. The reason
        names both rather than reporting a test that failed."""
        verdict, reason = guarantees._judge(AN_ENTRY, a_run(4), a_run(4))

        assert verdict == guarantees.BROKEN
        assert "unknown node id" in reason

    def test_an_xfail_on_the_test_is_seen_through_its_case(self, tmp_path):
        suite = self.A_PARAMETRIZED_SUITE.replace(
            "    @pytest.mark.parametrize",
            "    @pytest.mark.xfail(strict=True)\n    @pytest.mark.parametrize",
        )
        tree = self.a_tree(tmp_path, suite)
        entry = {**AN_ENTRY, "tests": ["tests/test_thing.py::TestIt::test_it_holds[2]"]}

        problems = guarantees.check(entry, tree)

        assert any("xfail" in one for one in problems), problems

    def test_a_single_case_runs_once(self, tmp_path):
        """A bound sized for every case would be charged to a proof that runs
        one of them."""
        tree = self.a_tree(tmp_path, self.A_PARAMETRIZED_SUITE)
        module = tree / "tests" / "test_thing.py"

        assert guarantees.parameters_of(module, "test_it_holds") == 3
        assert guarantees.parameters_of(module, "test_it_holds[2]") == 1

    def test_a_single_case_is_matched_to_that_case_alone(self):
        ran = a_run(
            1,
            **{
                "t.py__test_it[1]": "failure:AssertionError",
                "t.py__test_it[2]": "passed:",
            },
        )

        assert ran.matching("t.py::test_it[1]") == ["t.py::test_it[1]"]


class TestTheWaysAnEntryCouldEarnAVerdictItDidNot:
    """Two gaps a review found: a check that matches everything, and a mutation
    that could reach outside the symbol it names.

    Both are the shape this tool exists to refuse — a `proved` nobody earned —
    so both are refused rather than made unlikely.
    """

    @pytest.mark.parametrize("spelling", ["", "a", "asser"])
    def test_a_fails_with_too_short_to_discriminate_is_refused(self, spelling):
        """`fails_with` is a prefix. An empty one matches every failure, so the
        entry would report `proved` for a red run it never looked at."""
        entry = {**AN_ENTRY, "fails_with": spelling}

        problems = guarantees._check_shape(entry)

        assert any("too short" in one for one in problems), problems

    def test_every_spelling_in_a_list_is_checked(self):
        """One good member must not excuse a vacuous one beside it."""
        entry = {**AN_ENTRY, "fails_with": ["AssertionError", ""]}

        problems = guarantees._check_shape(entry)

        assert any("too short" in one for one in problems), problems

    def test_a_real_fails_with_is_allowed(self):
        """The positive control: without it the rule could refuse everything."""
        assert not [
            one for one in guarantees._check_shape(AN_ENTRY) if "too short" in one
        ]

    def test_nothing_outside_the_symbol_moves(self):
        """The guard text may legally appear in another function too.

        Exactly-once is scoped to the symbol's span, not the file, so a guard
        that also reads `if guarded:` somewhere else is allowed — and a
        whole-file replace would mutate both, producing a verdict about code
        the entry never named. That is `proved` for the wrong reason.

        The guard appears three times here and only the named copy may move.
        """
        source = textwrap.dedent("""
            def before(guarded):
                if guarded:
                    return "before"
                return "no"


            def keep(guarded):
                if guarded:
                    return "kept"
                return "not kept"


            def after(guarded):
                if guarded:
                    return "after"
                return "no"
            """).strip()
        entry = {"symbol": "keep", "guard": "if guarded:", "replaced_by": "if True:"}

        mutated = guarantees._mutated(source, entry)

        assert mutated.count("if guarded:") == 2, mutated
        assert mutated.count("if True:") == 1, mutated
        assert 'if True:\n        return "kept"' in mutated, mutated


class TestWhatARunExitsWith:
    """The exit a hook reads, which is not the same order as the results.

    `unmeasured` has an exit of its own so a caller can tell it apart, but it
    ranks below `unproved`. A run holding both must exit as `unproved`, or a
    missing server would hide a guarantee nothing defends.
    """

    @staticmethod
    def results(*names):
        return [({"guarantee": name}, name, "") for name in names]

    @pytest.mark.parametrize(
        ("names", "code"),
        [
            ((), 0),
            (("proved", "exempt"), 0),
            (("proved", "unmeasured"), 3),
            (("unmeasured", "unproved"), 1),
            (("unproved", "unmeasured"), 1),
            (("unmeasured", "unproved", "broken"), 2),
            (("broken", "proved"), 2),
        ],
    )
    def test_the_worst_result_by_rank_decides_the_exit(self, names, code):
        assert guarantees.exit_for(self.results(*names)) == code


class TestARunThatCouldNotMeasure:
    """`main` itself, with the archive and the measuring stubbed out."""

    def test_a_commit_with_no_list_refuses_as_broken(self, monkeypatch, capsys):
        """An old branch, or one that deletes the list. `load` would raise
        `FileNotFoundError`, and Python's exit for an uncaught error is the same
        code as `unproved`'s."""
        monkeypatch.setattr(guarantees, "_prepared", lambda _ref, _tree: None)

        with pytest.raises(SystemExit) as stopped:
            guarantees.main(["--ref", "HEAD"])

        assert stopped.value.code == guarantee_results.EXIT[guarantee_results.BROKEN]
        assert "FAILED" in capsys.readouterr().out

    def test_a_crash_exits_as_broken_and_says_failed(self, monkeypatch, capsys):
        """Python's exit for an uncaught error is `unproved`'s code, so any
        exception would otherwise read as a guarantee nothing defends."""

        def lays_out_a_list(_ref, tree):
            (tree / "tools").mkdir()
            (tree / "tools" / "guarantees.yaml").write_text("- guarantee: one\n")

        def crashes(_tree, _entries):
            raise RuntimeError("the tool itself broke")

        monkeypatch.setattr(guarantees, "_prepared", lays_out_a_list)
        monkeypatch.setattr(guarantees, "measure", crashes)

        assert (
            guarantees.main(["--ref", "HEAD"])
            == guarantee_results.EXIT[guarantee_results.BROKEN]
        )
        said = capsys.readouterr().out
        assert "FAILED" in said and "the tool itself broke" in said
        assert "NOT RUN" not in said, (
            "NOT RUN means a check was not needed ; this one was "
            "needed and could not run"
        )

    def test_a_result_nobody_named_exits_as_broken_rather_than_ranking(
        self, monkeypatch
    ):
        """`exit_for` refuses to rank a string it does not know. Inside `main`
        that is a crash, and a crash exits as `broken` — never as `unproved`,
        and never as a pass."""

        def lays_out_a_list(_ref, tree):
            (tree / "tools").mkdir()
            (tree / "tools" / "guarantees.yaml").write_text("- guarantee: one\n")

        monkeypatch.setattr(guarantees, "_prepared", lays_out_a_list)
        monkeypatch.setattr(
            guarantees, "measure", lambda _tree, _entries: [({}, "bogus", "")]
        )

        assert (
            guarantees.main(["--ref", "HEAD"])
            == guarantee_results.EXIT[guarantee_results.BROKEN]
        )


class TestEntriesRunInParallel:
    """`measure` runs entries at once, each in its own tree, and hands back the
    same shape a one-at-a-time run did (#299)."""

    def test_one_worker_and_several_give_the_same_verdicts(self, tree):
        unproved = {**AN_ENTRY, "tests": ["tests/test_thing.py::test_it_stays"]}
        (tree / "tests" / "test_thing.py").write_text(
            A_SUITE + "\n\ndef test_it_stays():\n    assert keep(True) == 'kept'\n"
        )
        entries = [AN_ENTRY, unproved, AN_ENTRY, unproved]

        alone = guarantees.measure(tree, entries, workers=1)
        together = guarantees.measure(tree, entries, workers=3)

        assert [result for _, result, _ in together] == [
            result for _, result, _ in alone
        ]
        assert [result for _, result, _ in alone] == [
            guarantees.PROVED,
            guarantees.UNPROVED,
        ] * 2


class TestEachResultIsPrintedAsItIsKnown:
    """The runtime entry takes ninety seconds, so a run that printed only at
    the end would look hung under a hook."""

    def test_measure_prints_each_result(self, tree, capsys):
        excused = {
            "guarantee": "**It cannot be tested.**",
            "file": "src/tiny/thing.py",
            "symbol": "keep",
            "reason": "the thing it describes has not been built",
        }

        guarantees.measure(tree, [excused])

        said = capsys.readouterr().out
        assert "exempt" in said and "**It cannot be tested.**" in said

    def test_an_entry_with_no_quotation_is_still_named(self, capsys):
        guarantees.report({}, guarantees.BROKEN, "no guarantee field")

        assert "<an entry with no guarantee>" in capsys.readouterr().out

    def test_an_empty_list_refuses_as_broken(self, monkeypatch, capsys):
        """A list emptied by a commit measures nothing, and nothing measured
        must not exit as a pass."""

        def lays_out_an_empty_list(_ref, tree):
            (tree / "tools").mkdir()
            (tree / "tools" / "guarantees.yaml").write_text("[]\n")

        monkeypatch.setattr(guarantees, "_prepared", lays_out_an_empty_list)

        with pytest.raises(SystemExit) as stopped:
            guarantees.main(["--ref", "HEAD"])

        assert stopped.value.code == guarantee_results.EXIT[guarantee_results.BROKEN]
        assert "is empty" in capsys.readouterr().out
