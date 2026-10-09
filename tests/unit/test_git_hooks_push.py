"""The pre-push hook: which refs it reads, which checks it runs, and what it says.

A push is looked at through the refs git names on stdin, and what the hook
decides from them is the part worth testing: a push that sends nothing runs
nothing, a push of prose runs nothing that needs an environment, and a push of
code runs the duplicate-code gate and, when the project keeps a guarantee list,
the guarantee check.

The rule most of these hold the hook to: **an optional check the project has not
set up is NOT RUN and the push goes ahead; a required tool that is missing, or a
check that ran and failed, refuses it.**
"""

import pytest

from hook_harness import (
    _git,
    _push_line,
    _run_pre_push,
    _scratch_repo,
    _stub_on_path,
    _stub_pylint,
    _stub_tools,
    _stub_venv,
    posix,
    write_lf,
)

ZERO = "0" * 40


def _head(repo):
    return _git("rev-parse", "HEAD", cwd=repo).stdout.strip()


class TestARefThatSendsNothing:
    def test_a_ref_the_remote_already_has_runs_nothing(self, tmp_path):
        repo = _scratch_repo(tmp_path, "already", STACK="python")
        sha = _head(repo)

        result, said = _run_pre_push(repo, f"refs/heads/main {sha} refs/heads/main {sha}\n")

        assert result.returncode == 0, said
        assert "already on the remote or being deleted" in said
        assert "Pre-push checks passed." in said

    def test_a_deletion_runs_nothing(self, tmp_path):
        repo = _scratch_repo(tmp_path, "deleted", STACK="python")
        sha = _head(repo)

        result, said = _run_pre_push(repo, f"(delete) {ZERO} refs/heads/old {sha}\n")

        assert result.returncode == 0, said
        assert "already on the remote or being deleted" in said


class TestAPushOnAnotherStack:
    def test_every_python_check_says_the_stack_is_not_python(self, tmp_path):
        repo = _scratch_repo(tmp_path, "node", STACK="node")
        refs = _push_line(repo, "src/app.js", "x\n")

        result, said = _run_pre_push(repo, refs)

        assert result.returncode == 0, said
        assert "duplicate-code gate (stack is node" in said
        assert "guarantee check (stack is node" in said


class TestAPushOfProse:
    def test_it_needs_no_environment(self, tmp_path):
        repo = _scratch_repo(tmp_path, "prose", STACK="python")
        refs = _push_line(repo, "NOTES.md", "A note.\n")

        result, said = _run_pre_push(repo, refs)

        assert result.returncode == 0, said
        assert "NOT RUN — the duplicate-code gate and the guarantee check." in said
        assert "Nothing in this push can change what a test does" in said


class TestAPushOfCode:
    def _setup(self, tmp_path, name, **pylint):
        repo = _scratch_repo(tmp_path, name, STACK="python")
        venv = _stub_venv(repo)
        ledger = tmp_path / f"{name}-ledger"
        _stub_tools(venv, ledger, "python")
        _stub_pylint(venv, ledger, **pylint)
        return repo, ledger

    def test_no_environment_refuses_the_push_with_the_fix(self, tmp_path):
        repo = _scratch_repo(tmp_path, "noenv", STACK="python")
        refs = _push_line(repo, "thing.py", "VALUE = 1\n")

        result, said = _run_pre_push(repo, refs)

        assert result.returncode == 1, said
        assert "no project environment" in said
        assert "git push --no-verify" in said

    def test_a_clean_tree_passes_and_pylint_runs_duplicate_code_only(self, tmp_path):
        repo, ledger = self._setup(tmp_path, "clean")
        refs = _push_line(repo, "thing.py", "VALUE = 1\n")

        result, said = _run_pre_push(repo, refs)

        assert result.returncode == 0, said
        call = [one for one in ledger.read_text().splitlines() if one.startswith("pylint")][0]
        assert "--disable=all" in call and "--enable=duplicate-code" in call
        assert "thing.py" in call
        assert "NOT RUN — the guarantee check: this project has no tools/guarantees.yaml." in said

    def test_a_reported_pair_refuses_the_push(self, tmp_path):
        repo, _ = self._setup(tmp_path, "dup", reporting=[("alpha", "beta")])
        refs = _push_line(repo, "thing.py", "VALUE = 1\n")

        result, said = _run_pre_push(repo, refs)

        assert result.returncode == 1, said
        assert "duplicate-code finding" in said

    def test_a_listed_pair_is_let_through_in_either_order(self, tmp_path):
        repo, _ = self._setup(tmp_path, "exempt", reporting=[("alpha", "beta")])
        write_lf(
            repo / ".git-hooks" / "duplicate-code-exempt", "beta alpha  # same fixture\n"
        )
        refs = _push_line(repo, "thing.py", "VALUE = 1\n")

        result, said = _run_pre_push(repo, refs)

        assert result.returncode == 0, said
        assert "1 pair(s) let through" in said

    def test_a_pylint_that_did_not_run_is_failed_not_clean(self, tmp_path):
        """A broken run prints no `R0801` and reports nothing, which is the shape
        a gate reading only its own filter mistakes for a clean tree."""
        repo, _ = self._setup(tmp_path, "broken", broken_with=32)
        refs = _push_line(repo, "thing.py", "VALUE = 1\n")

        result, said = _run_pre_push(repo, refs)

        assert result.returncode == 1, said
        assert "pylint exited 32, so nothing was compared" in said


class TestTheGuaranteeCheck:
    """Optional: it runs only for a project that keeps `tools/guarantees.yaml`."""

    def _repo_with_list(self, tmp_path, name, exit_code):
        repo = _scratch_repo(tmp_path, name, STACK="python")
        venv = _stub_venv(repo)
        ledger = tmp_path / f"{name}-ledger"
        _stub_tools(venv, ledger, "pylint")
        # A `python` that answers for the guarantee tool with the given exit.
        _stub_on_path(
            venv / "bin",
            "python",
            f'echo "python $*" >> "{posix(ledger)}"; exit {exit_code}',
        )
        (repo / "tools").mkdir(exist_ok=True)
        write_lf(repo / "tools" / "guarantees.yaml", "- guarantee: x\n")
        for tool_file in ("guarantees.py", "guarantee_proofs.py", "guarantee_results.py"):
            write_lf(repo / "tools" / tool_file, "# stand-in; never run\n")
        return repo, ledger

    def test_a_missing_tool_file_refuses_the_push(self, tmp_path):
        repo, _ = self._repo_with_list(tmp_path, "nofile", 0)
        (repo / "tools" / "guarantee_results.py").unlink()
        refs = _push_line(repo, "thing.py", "VALUE = 1\n")

        result, said = _run_pre_push(repo, refs)

        assert result.returncode == 1, said
        assert "tools/guarantee_results.py is missing" in said

    @pytest.mark.parametrize(
        "exit_code, passes, phrase",
        [
            (0, True, "ok"),
            (3, True, "PASSED WITH UNMEASURED GUARANTEES"),
            (1, False, "the guarantee check did not pass"),
            (2, False, "the guarantee check did not pass"),
            (9, False, "the guarantee check did not pass"),
        ],
    )
    def test_each_exit_ranks_as_the_results_module_orders_them(
        self, tmp_path, exit_code, passes, phrase
    ):
        """`unmeasured` (3) is a fact about the machine and ranks below
        `unproved` (1) though its exit is larger; an exit nobody named ranks
        worst of all."""
        repo, ledger = self._repo_with_list(tmp_path, f"exit{exit_code}", exit_code)
        # pylint must pass (a clean duplicate-code run) before the guarantee.
        refs = _push_line(repo, "thing.py", "VALUE = 1\n")

        result, said = _run_pre_push(repo, refs)

        assert (result.returncode == 0) is passes, said
        assert phrase in said
        assert "guarantees.py --ref" in ledger.read_text()


def test_the_rank_function_matches_the_results_module():
    """The hook's `case` and `tools/guarantee_results.py` own the same table, and
    a change to one that the other did not follow would push a guarantee nothing
    defends."""
    import re
    import sys
    from hook_harness import HOOKS, REPO

    sys.path.insert(0, str(REPO / "tools"))
    import guarantee_results as results  # pylint: disable=import-outside-toplevel

    hook = (HOOKS / "pre-push").read_text()
    body = re.search(r"guarantee_rank\(\) \{\n    case \"\$1\" in\n(.*?)\n    esac", hook, re.S)
    assert body, "pre-push no longer defines guarantee_rank"
    ranks = {
        int(code): int(rank)
        for code, rank in re.findall(r"^\s+(\d+)\) echo (\d+) ;;$", body.group(1), re.M)
    }
    for name, exit_code in results.EXIT.items():
        assert ranks[exit_code] == results.RANK[name], name
