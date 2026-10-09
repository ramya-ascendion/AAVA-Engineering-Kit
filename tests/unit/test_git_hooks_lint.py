"""What the commit gate asks of black, flake8 and pylint, and of which files.

Its own module because `test_git_hooks.py` is already long; the harness and the
shape of a test are that file's, unchanged.

The commit gate turns `duplicate-code` off and `pre-push` runs it over a fixed
file set instead, because that is the one pylint check whose answer depends on
which files are in the run, and a commit's file set is whatever it happened to
stage.

**Asserted through the arguments, not the ledger.** A stub that logs only its
own name cannot tell `--disable=duplicate-code` from a bare call. The stubs here
record `"$@"`, and that is what these read.
"""

from hook_harness import (
    _git,
    _run_pre_commit,
    _scratch_repo,
    _stub_on_path,
    _stub_pylint,
    _stub_tools,
    _stub_venv,
    posix,
    write_lf,
)

TOOLS = ("python", "pytest", "black", "flake8", "mypy")


def _python_repo(tmp_path, name, layout="bin"):
    """A Python-stack scratch checkout with a stub environment and a ledger."""
    scratch = _scratch_repo(tmp_path, name, STACK="python")
    venv = _stub_venv(scratch, layout=layout)
    ledger = tmp_path / f"{name}-ledger"
    _stub_tools(venv, ledger, *TOOLS, layout=layout)
    _stub_pylint(venv, ledger, layout=layout)
    gitleaks = _stub_on_path(tmp_path / f"{name}-stubs", "gitleaks", "exit 0").parent
    return scratch, ledger, f"{posix(gitleaks)}:/usr/bin:/bin:/mingw64/bin"


def _calls(ledger, tool):
    return [
        line
        for line in ledger.read_text().splitlines()
        if line.startswith(f"{tool} ")
    ]


def test_both_pylint_passes_turn_duplicate_code_off(tmp_path):
    """Both passes, not one.

    The gate splits staged Python into test files and everything else so the two
    can carry different module-length caps. A similar pair lands in whichever
    pass matches, so turning the check off in only one of them would still refuse
    half the commits this is meant to let through.
    """
    scratch, ledger, path = _python_repo(tmp_path, "commit-gate")

    # One file on each side of the split. With only one, the other pass never
    # fires and its arguments never reach the ledger to be checked.
    write_lf(scratch / "thing.py", "VALUE = 1\n")
    (scratch / "tests").mkdir()
    write_lf(scratch / "tests" / "test_thing.py", "def test_it():\n    pass\n")
    _git("add", "thing.py", "tests/test_thing.py", cwd=scratch)

    result, output = _run_pre_commit(scratch, path=path)
    calls = _calls(ledger, "pylint")

    assert result.returncode == 0, output
    assert len(calls) == 2, (
        "expected one pylint call per side of the test/non-test split, so that"
        f" both can be checked: {calls!r}\n{output}"
    )
    for call in calls:
        assert "--disable=duplicate-code" in call, (
            "a pylint pass still runs duplicate-code, so whether this commit"
            f" passes depends on what else it staged: {call!r}"
        )

    # The caps are what the two passes exist for, and a change that dropped one
    # while adding the disable would satisfy every assertion above.
    assert (
        sum("--max-module-lines=1250" in call for call in calls) == 1
    ), f"exactly one pass takes the looser cap, for test modules: {calls!r}"


def test_only_the_staged_files_reach_the_linters(tmp_path):
    """The commit gate looks at what is being committed, so one broken file
    elsewhere cannot block a change over here."""
    scratch, ledger, path = _python_repo(tmp_path, "staged-only")
    write_lf(scratch / "elsewhere.py", "BROKEN = (\n")
    write_lf(scratch / "thing.py", "VALUE = 1\n")
    _git("add", "thing.py", cwd=scratch)

    result, output = _run_pre_commit(scratch, path=path)

    assert result.returncode == 0, output
    for tool in ("black", "flake8", "pylint"):
        calls = _calls(ledger, tool)
        assert calls, f"{tool} never ran on a commit staging Python: {output!r}"
        assert all("thing.py" in call for call in calls), calls
        assert not any("elsewhere.py" in call for call in calls), calls


def test_the_staged_files_still_reach_pylint(tmp_path):
    """The disable must not be the only thing the hook passes.

    `--disable=duplicate-code` sits next to the file list in the same command, and
    a quoting slip there would send pylint a flag and no files. Pylint called with
    nothing to lint exits 0, so the gate would go quiet and pass everything.
    """
    scratch, ledger, path = _python_repo(tmp_path, "files-still-sent")
    write_lf(scratch / "thing.py", "VALUE = 1\n")
    _git("add", "thing.py", cwd=scratch)

    result, output = _run_pre_commit(scratch, path=path)
    calls = _calls(ledger, "pylint")

    assert result.returncode == 0, output
    assert any("thing.py" in call for call in calls), calls


def test_black_is_checked_never_applied(tmp_path):
    """A hook that rewrites the file being committed changes what is about to be
    committed after the author has read it, which is worse than refusing."""
    scratch, ledger, path = _python_repo(tmp_path, "black-check")
    write_lf(scratch / "thing.py", "VALUE = 1\n")
    _git("add", "thing.py", cwd=scratch)

    _run_pre_commit(scratch, path=path)

    assert all("--check" in call for call in _calls(ledger, "black"))


def test_a_failing_linter_refuses_the_commit(tmp_path):
    scratch, ledger, path = _python_repo(tmp_path, "flake-fails")
    _stub_tools(scratch / ".venv", ledger, "flake8", code=1)
    write_lf(scratch / "thing.py", "VALUE = 1\n")
    _git("add", "thing.py", cwd=scratch)

    result, output = _run_pre_commit(scratch, path=path)

    assert result.returncode == 1, output
    assert "style (flake8)" in output and "FAILED" in output


def test_a_prose_only_commit_runs_none_of_them(tmp_path):
    scratch, ledger, path = _python_repo(tmp_path, "prose-only")
    write_lf(scratch / "NOTES.md", "A note.\n")
    _git("add", "NOTES.md", cwd=scratch)

    result, output = _run_pre_commit(scratch, path=path)

    assert result.returncode == 0, output
    assert "no Python files staged" in output
    assert not ledger.exists() or not _calls(ledger, "flake8")
