"""What `tools/crap.py` does when its inputs cannot be trusted .

**The gate is the thing that says whether a branch is ready**, so the way it
fails matters as much as the way it passes. It shipped scoring a function its
coverage data did not mention as zero-covered, which turned an old measurement
into a red gate on code nobody had touched — and a gate that goes green on a
re-run teaches a reader that red means "run it again".

Each test builds a throwaway package under `tmp_path`, takes a real coverage
measurement over it, and runs the real `tools/crap.py` in a subprocess. Nothing
is reimplemented here: a Python copy of the tool would only prove the copy
works.

Two classes are not about the tool: `TestWhereItLooksForItsTools` covers where
this module finds `coverage` and `radon` , and
`TestWhatTheMeasurementTraces` covers which code the measurement can see at
all.

Telling the exit codes apart is most of what is asserted here.
`docs/agents/coverage-and-crap.md` says what each one means.

They start no server and reach no network.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
CRAP = REPO / "tools" / "crap.py"
# `coverage` and `radon` sit beside the interpreter running this suite, in a
# worktree as well as in the main checkout.
TOOL_BIN = Path(sys.executable).parent


def _ignored_dirs_in_crap():
    """`IGNORED_DIRS` read out of the tool's source, so importing it is not needed."""
    found = re.search(r'^IGNORED_DIRS = "([^"]+)"', CRAP.read_text(), re.M)
    assert found, "tools/crap.py no longer defines IGNORED_DIRS"
    return found.group(1)


IGNORED_DIRS_IN_CRAP = _ignored_dirs_in_crap()

# One simple function and one branchy one, so a run has something to score and
# the branchy one can be pushed over a bar on purpose.
A_MODULE = """
def simple(value):
    return value + 1


def branchy(a, b, c, d):
    if a:
        return 1
    if b:
        return 2
    if c:
        return 3
    if d:
        return 4
    return 5
"""

A_TEST = """
from pkg import thing


def test_simple():
    assert thing.simple(1) == 2
"""


def _environment(**settings: str) -> dict:
    """The caller's environment for a subprocess, without its coverage settings.

    `coverage` reads `COVERAGE_FILE` and the rest of `COVERAGE_*` from the
    environment, so a caller's value would decide where the measurement goes
    and which file the tool reads. Dropped wholesale, the way
    `tools/guarantees.py` scrubs them for a proof.
    """
    kept = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith("COVERAGE_")
    }
    return {**kept, **settings}


@pytest.fixture(name="measured")
def _measured(tmp_path):
    """A tiny package with a real coverage measurement taken over it."""
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("")
    (package / "thing.py").write_text(A_MODULE)

    tests = tmp_path / "tests"
    tests.mkdir()
    (tests / "test_thing.py").write_text(A_TEST)

    subprocess.run(
        [
            str(TOOL_BIN / "coverage"),
            "run",
            "--source=src/pkg",
            "-m",
            "pytest",
            "-q",
            "tests",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
        env=_environment(PYTHONPATH=str(tmp_path / "src")),
    )
    return tmp_path


def crap(where: Path, *arguments: str, path: str | None = None):
    """The real tool, run the way a person runs it."""
    environment = _environment(PATH=f"{TOOL_BIN}{os.pathsep}{os.environ['PATH']}")
    if path is not None:
        environment["PATH"] = path
    return subprocess.run(
        [sys.executable, str(CRAP), "--source=src/pkg", *arguments],
        cwd=where,
        capture_output=True,
        text=True,
        check=False,
        env=environment,
    )


class TestWhereItLooksForItsTools:
    """Where this module finds `coverage` and `radon` .

    The first test reads the `TOOL_BIN` assignment out of this file's own
    source, the way `test_gate_coverage.py` reads the hook's pathspec. In the
    main checkout the interpreter's directory and `REPO / ".venv" / "bin"`
    are the same path, so a runtime comparison cannot tell them apart.
    """

    def test_the_tool_path_comes_from_the_interpreter(self):
        assignment = next(
            (
                line
                for line in Path(__file__).read_text(encoding="utf-8").splitlines()
                if line.startswith("TOOL_BIN")
            ),
            "",
        )

        assert assignment, (
            "no `TOOL_BIN` assignment was found in this file. This test reads it "
            "out of the module's own source, so it has stopped measuring "
            "anything. Renaming the constant means renaming it here too."
        )
        assert "sys.executable" in assignment, assignment


class TestAMeasurementItCanTrust:
    def test_fresh_data_scores_every_function_and_passes(self, measured):
        done = crap(measured, "--coverage-bar", "0")

        assert done.returncode == 0, done.stdout + done.stderr
        assert "Functions scored: 2" in done.stdout
        assert "ok — both bars passed" in done.stdout

    def test_a_failed_bar_exits_one_not_two(self, measured):
        """The distinction the exit codes exist for. `branchy` is complexity 5
        and never called, so a bar of 4 fails it on a measurement that ran."""
        done = crap(measured, "--bar", "4", "--coverage-bar", "0")

        assert done.returncode == 1, done.stdout + done.stderr
        assert "FAILED" in done.stdout
        assert "NOT RUN" not in done.stdout

    def test_coverage_under_the_bar_exits_one_and_says_to_write_tests(self, measured):
        """The other bar. `branchy` is never called, so this package sits well
        under 75% — measured, and failing, which is not the same as not run."""
        done = crap(measured)

        assert done.returncode == 1, done.stdout + done.stderr
        assert "under the 75% bar" in done.stdout
        assert "Write unit tests" in done.stdout
        assert "NOT RUN" not in done.stdout

    def test_python_under_node_modules_is_neither_watched_nor_scored(self, measured):
        """The Web client workspace sits inside `src/app`, and npm's
        `flatted` package ships a `.py` file. `npm ci` writes it after any
        measurement, and coverage never measures it, so either half reading it
        would refuse every run."""
        stray = measured / "src" / "pkg" / "node_modules" / "flatted" / "python"
        stray.mkdir(parents=True)
        (stray / "flatted.py").write_text("def parse(value):\n    return value\n")

        done = crap(measured, "--coverage-bar", "0")

        assert done.returncode == 0, done.stdout + done.stderr
        assert "Functions scored: 2" in done.stdout


@pytest.fixture(name="coverage_file_elsewhere")
def _coverage_file_elsewhere(tmp_path_factory, monkeypatch):
    """`COVERAGE_FILE` pointed outside the measured tree, as a caller may have it.

    A fixture rather than a line in the test, so the variable is set before
    `measured` takes its measurement.
    """
    elsewhere = tmp_path_factory.mktemp("elsewhere") / "data"
    monkeypatch.setenv("COVERAGE_FILE", str(elsewhere))
    return elsewhere


class TestACallersCoverageFileIsIgnored:
    """The measurement and the tool both use the tree's own `.coverage`.

    Both subprocesses here inherit the caller's environment, and `coverage`
    honors `COVERAGE_FILE`. Left in, a caller's variable moves the measurement
    out of the tree and points the tool at whatever file it names, so a test
    here could score the wrong data and pass.
    """

    def test_the_measurement_stays_in_the_tree(self, coverage_file_elsewhere, measured):
        assert (measured / ".coverage").exists()
        assert not coverage_file_elsewhere.exists()

    @pytest.mark.usefixtures("coverage_file_elsewhere")
    def test_the_tool_reads_the_trees_own_data(self, measured):
        (measured / ".coverage").unlink()

        done = crap(measured)

        assert done.returncode == 2, done.stdout + done.stderr


class TestItRefusesRatherThanGuessing:
    def test_data_older_than_the_code_is_refused_and_says_which_files(self, measured):
        """The guard PROJ-1 asked for.

        **Not a reproduction of the original bug.** That one needed data whose
        function list disagreed with the source, which could not be provoked
        afterwards; `touch` changes no content, so the old tool scored this
        happily. What is pinned here is the new behavior: a measurement older
        than what it measured is not scored at all. A refusal a reader cannot
        act on is a traceback with better manners, so both files and the
        command are pinned too.
        """
        (measured / "src" / "pkg" / "thing.py").touch()

        done = crap(measured)

        assert done.returncode == 2, done.stdout + done.stderr
        assert "NOT RUN" in done.stdout
        assert "older than the code" in done.stdout
        assert ".coverage collected" in done.stdout
        assert "thing.py" in done.stdout
        assert "coverage run --source=src/pkg" in done.stdout

    def test_editing_a_test_makes_the_data_stale_too(self, measured):
        """A measurement taken before a test existed describes a suite nobody
        ran — and it is wrong in the flattering direction when the new test is
        the one that covers the gap."""
        (measured / "tests" / "test_thing.py").touch()

        done = crap(measured)

        assert done.returncode == 2, done.stdout + done.stderr
        assert "older than the code" in done.stdout
        assert "test_thing.py" in done.stdout

    def test_no_coverage_data_at_all_is_refused(self, measured):
        (measured / ".coverage").unlink()

        done = crap(measured)

        assert done.returncode == 2, done.stdout + done.stderr
        assert "no coverage data" in done.stdout
        assert "coverage run --source=src/pkg" in done.stdout

    def test_a_missing_tool_names_the_environment_not_a_traceback(self, measured):
        """Without this the tool dies on `FileNotFoundError: 'coverage'`, which
        reads as a bug in the gate rather than an environment nobody activated."""
        done = crap(measured, path="/usr/bin:/bin")

        assert done.returncode == 2, done.stdout + done.stderr
        assert "not on PATH" in done.stdout
        assert ".venv/bin/activate" in done.stdout
        assert "setup-dev-env.sh" in done.stdout
        assert "Traceback" not in done.stderr

    def test_pointing_at_directories_with_no_python_is_refused(self, measured):
        """Both watched directories empty, because `tests/` on its own holds
        Python and would take a different refusal — an earlier version of this
        test pointed there and passed for the wrong reason.
        """
        (measured / "nothing").mkdir()

        done = crap(measured, "--source=nothing", "--tests", "nothing")

        assert done.returncode == 2, done.stdout + done.stderr
        assert "holds any Python" in done.stdout
        assert "--source and --tests" in done.stdout


class TestWhatItStillScores:
    def test_a_module_in_no_coverage_report_is_refused_not_scored_at_zero(
        self, measured
    ):
        """This is the shape PROJ-1 actually saw: a whole file absent from the
        report, every function in it scored at zero, and the gate red on code
        nobody had touched.

        Zero is the honest number for a module nothing imports — and it is also
        what a half-finished measurement looks like. The two cannot be told
        apart from here, so neither is scored.
        """
        lonely = measured / "src" / "pkg" / "lonely.py"
        lonely.write_text("def never_called(a):\n    return a\n")
        os.utime(lonely, (0, 0))

        done = crap(measured, "--coverage-bar", "0")

        assert done.returncode == 2, done.stdout + done.stderr
        assert "in no coverage report" in done.stdout
        assert "lonely.py" in done.stdout
        assert "neither is a score" in done.stdout


class TestWhatTheMeasurementTraces:
    """Coverage's own configuration decides which code it can see at all."""

    def test_coverage_omits_the_same_directories_crap_ignores(self):
        """`[tool.coverage.run] omit` in pyproject.toml and `IGNORED_DIRS` in
        tools/crap.py are one decision spread across two files. Omitting a
        directory in one and not the other makes crap.py refuse, because radon
        then reports files coverage never mentioned."""
        text = (REPO / "pyproject.toml").read_text()
        block = re.search(r"^\[tool\.coverage\.run\]\n(.*?)(?=^\[|\Z)", text, re.M | re.S)
        assert block, "pyproject.toml has no [tool.coverage.run] table."
        omitted = re.search(r"^omit\s*=\s*\[([^\]]*)\]", block.group(1), re.M)
        assert omitted, "[tool.coverage.run] names no `omit`."
        assert f"*/{IGNORED_DIRS_IN_CRAP}/*" in omitted.group(1)
