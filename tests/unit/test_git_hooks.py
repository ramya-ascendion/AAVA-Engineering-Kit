"""`common.sh` and the pre-commit hook, run for real against scratch checkouts.

Each test builds a small git repository holding the kit's real hooks, stages one
thing, runs the hook the way git does and reads what it said and how it exited.
Tools the hooks call (black, pytest, gitleaks) are stubs that log their
arguments, so a name in a ledger proves the hook reached it and what it asked.

The rule most of these hold the hook to is the one the hook is built on: **a
check that did not run is not a check that passed.** So a missing tool says
FAILED, a gate that does not apply to the stack says NOT RUN with the reason,
and neither reads as ok.
"""

from __future__ import annotations

import os
import shutil

import pytest

from hook_harness import (
    BARE_PATH,
    HOOKS,
    IS_WINDOWS,
    _ask_activate_venv,
    _ask_skip_sentence,
    _git,
    _python_dir,
    _run,
    _run_pre_commit,
    _scratch_repo,
    _stage_link,
    _stub_on_path,
    _stub_tools,
    _stub_venv,
    posix,
    write_config,
    write_lf,
)


def _path(*directories):
    """A PATH of the given directories, then the bare one."""
    return ":".join([*(posix(one) for one in directories), BARE_PATH])


def _stage(repo, name, text="x\n"):
    """Write and stage one file."""
    (repo / name).parent.mkdir(parents=True, exist_ok=True)
    write_lf((repo / name), text)
    _git("add", name, cwd=repo)


def _clean_gitleaks(tmp_path):
    """A `gitleaks` that finds nothing, in a directory of its own."""
    return _stub_on_path(tmp_path / "stubs", "gitleaks", "exit 0").parent


# ---------------------------------------------------------------------------
# common.sh
# ---------------------------------------------------------------------------


class TestWhichChangesNeedTheTests:
    """`path_affects_tests` is deliberately wide and read from the config."""

    def _asks(self, repo, path):
        result = _run(
            f'source "{posix(repo)}/.git-hooks/common.sh"; '
            f'path_affects_tests "{path}" && echo YES || echo NO',
            cwd=repo,
            env={"PATH": BARE_PATH},
        )
        return result.stdout.strip()

    @pytest.mark.parametrize(
        "path",
        [
            "a.py",
            "web/app.js",
            "tests/data/fixture.json",
            ".git-hooks/pre-commit",
            "tools/crap-exempt",
            "pyproject.toml",
            "package.json",
            ".kit/config.env",
            "tools/requirements-ci.txt",
        ],
    )
    def test_the_fixed_part_of_the_rule(self, tmp_path, path):
        repo = _scratch_repo(tmp_path, "fixed")
        assert self._asks(repo, path) == "YES"

    @pytest.mark.parametrize("path", ["README.md", "docs/agents/x.md", "LICENSE"])
    def test_prose_does_not_need_the_tests(self, tmp_path, path):
        repo = _scratch_repo(tmp_path, "prose", PACKAGE_DIR="lib/thing")
        assert self._asks(repo, path) == "NO"

    def test_the_package_directory_comes_from_the_config(self, tmp_path):
        repo = _scratch_repo(tmp_path, "pkg", PACKAGE_DIR="lib/thing")
        assert self._asks(repo, "lib/thing/data.txt") == "YES"

    def test_the_test_directories_come_from_the_config(self, tmp_path):
        repo = _scratch_repo(tmp_path, "dirs", TEST_DIRS="spec/unit")
        assert self._asks(repo, "spec/unit/case.txt") == "YES"
        # The first path segment, because a fixture beside the tests counts.
        assert self._asks(repo, "spec/fixtures/case.txt") == "YES"

    def test_the_sentence_recites_the_configured_rule(self, tmp_path):
        sentence = _ask_skip_sentence()
        for word in ("source code", "pytest.ini", "package.json", ".kit/config.env"):
            assert word in sentence


class TestActivatingTheEnvironment:
    """`activate_venv` finds the project's environment by `KIT_VENV_DIR`."""

    @pytest.mark.parametrize("layout", ["bin", "Scripts"])
    def test_both_layouts_are_found(self, tmp_path, layout):
        repo = _scratch_repo(tmp_path, f"venv-{layout}")
        venv = _stub_venv(repo, layout=layout)

        result = _ask_activate_venv(repo)

        assert result.returncode == 0, result.stdout + result.stderr
        assert f"VENV={posix(venv)}" in result.stdout

    def test_the_directory_name_is_the_configured_one(self, tmp_path):
        repo = _scratch_repo(tmp_path, "named", VENV_DIR="env-for-this")
        venv = _stub_venv(repo, name="env-for-this")

        result = _ask_activate_venv(repo)

        assert f"VENV={posix(venv)}" in result.stdout

    def test_the_default_name_is_not_found_when_another_is_configured(self, tmp_path):
        repo = _scratch_repo(tmp_path, "other", VENV_DIR="env-for-this")
        _stub_venv(repo, name=".venv")

        result = _ask_activate_venv(repo)

        assert result.returncode == 1
        assert "VENV=none" in result.stdout
        assert "no env-for-this found" in result.stdout

    def test_finding_nothing_says_so_and_how_to_fix_it(self, tmp_path):
        repo = _scratch_repo(tmp_path, "none")

        result = _ask_activate_venv(repo)

        assert result.returncode == 1
        assert "./setup-dev-env.sh" in result.stdout

    def test_this_checkouts_source_is_put_first_on_the_path(self, tmp_path):
        """`src/pkg` is imported from `src`, so the checkout being committed wins
        over an editable install that points at the main checkout."""
        repo = _scratch_repo(tmp_path, "pythonpath", PACKAGE_DIR="src/thing")
        (repo / "src").mkdir()
        _stub_venv(repo)

        result = _ask_activate_venv(repo)

        pythonpath = [
            line for line in result.stdout.splitlines() if line.startswith("PP=")
        ][0]
        assert pythonpath.endswith("/src") or "/src" in pythonpath


class TestTheHookIsTheOneTheRepoDefines:
    """`refuse_if_stale`: a copy that has drifted must not run a weaker gate."""

    def _ask(self, repo, running, extra_env=None):
        return _run(
            f'source "{posix(repo)}/.git-hooks/common.sh"; '
            f'refuse_if_stale pre-commit "{posix(running)}"; echo "RC=$?"',
            cwd=repo,
            env={"PATH": BARE_PATH, **(extra_env or {})},
        )

    def test_the_tracked_copy_itself_is_fine(self, tmp_path):
        repo = _scratch_repo(tmp_path, "same")

        result = self._ask(repo, repo / ".git-hooks" / "pre-commit")

        assert "RC=0" in result.stdout

    def test_a_drifted_copy_is_refused_and_told_how_to_reinstall(self, tmp_path):
        repo = _scratch_repo(tmp_path, "drift")
        stale = tmp_path / "stale-pre-commit"
        write_lf(stale, "#!/bin/bash\necho an older gate\n")

        result = self._ask(repo, stale)

        assert "RC=1" in result.stdout
        assert "FAILED" in result.stdout
        assert "git config core.hooksPath .git-hooks" in result.stdout

    def test_a_worktree_pointed_elsewhere_hands_off_once(self, tmp_path):
        """The override is honored by running this branch's own hook with
        `exec`, and `KIT_HOOK_REEXEC` stops it happening twice."""
        repo = _scratch_repo(tmp_path, "handoff")
        _git("config", "extensions.worktreeConfig", "true", cwd=repo)
        _git("config", "--worktree", "core.hooksPath", "/somewhere/else", cwd=repo)
        # The tracked hook becomes a stub that reports what it was handed.
        tracked = repo / ".git-hooks" / "pre-commit"
        write_lf(tracked, '#!/bin/bash\necho "HANDED_OFF reexec=$KIT_HOOK_REEXEC"\n')
        tracked.chmod(0o755)
        stale = tmp_path / "stale-pre-commit"
        write_lf(stale, "#!/bin/bash\necho an older gate\n")

        result = self._ask(repo, stale)

        assert "HANDED_OFF reexec=1" in result.stdout

    def test_a_second_hand_off_is_refused_not_looped(self, tmp_path):
        repo = _scratch_repo(tmp_path, "loop")
        _git("config", "extensions.worktreeConfig", "true", cwd=repo)
        _git("config", "--worktree", "core.hooksPath", "/somewhere/else", cwd=repo)
        stale = tmp_path / "stale-pre-commit"
        write_lf(stale, "#!/bin/bash\necho an older gate\n")

        result = self._ask(repo, stale, {"KIT_HOOK_REEXEC": "1"})

        assert "RC=1" in result.stdout
        assert "Handing off to this branch's copy did not help" in result.stdout


class TestExemptLists:
    """`gate_is_exempt`: the one format every `*-exempt` file shares."""

    def _exempt(self, repo, listed, path):
        write_lf((repo / "ex"), listed)
        result = _run(
            f'source "{posix(repo)}/.git-hooks/common.sh"; '
            f'gate_is_exempt ex "{path}" && echo EXEMPT || echo CHECKED',
            cwd=repo,
            env={"PATH": BARE_PATH},
        )
        return result.stdout.strip()

    def test_an_exact_path_is_exempt(self, tmp_path):
        repo = _scratch_repo(tmp_path, "exact")
        assert self._exempt(repo, "docs/a.md\n", "docs/a.md") == "EXEMPT"

    def test_a_leading_dot_slash_does_not_matter(self, tmp_path):
        repo = _scratch_repo(tmp_path, "dotslash")
        assert self._exempt(repo, "docs/a.md\n", "./docs/a.md") == "EXEMPT"

    def test_a_trailing_slash_exempts_the_whole_directory(self, tmp_path):
        repo = _scratch_repo(tmp_path, "dir")
        assert self._exempt(repo, "vendor/\n", "vendor/x/y.md") == "EXEMPT"

    def test_a_directory_line_does_not_prefix_match_a_sibling(self, tmp_path):
        repo = _scratch_repo(tmp_path, "sibling")
        assert self._exempt(repo, "vendor/\n", "vendored/y.md") == "CHECKED"

    def test_comments_and_blank_lines_are_ignored(self, tmp_path):
        repo = _scratch_repo(tmp_path, "comments")
        listed = "# docs/a.md\n\n   \n"
        assert self._exempt(repo, listed, "docs/a.md") == "CHECKED"

    def test_a_short_entry_does_not_match_a_longer_path(self, tmp_path):
        repo = _scratch_repo(tmp_path, "short")
        assert self._exempt(repo, "docs/my\n", "docs/my-file.md") == "CHECKED"

    def test_the_shipped_lists_name_their_format_and_exempt_only_vendor(self):
        spelling = (HOOKS / "spelling-exempt").read_text()
        duplicates = (HOOKS / "duplicate-code-exempt").read_text()
        assert "Format" in spelling and "Format" in duplicates
        entries = [
            line
            for line in spelling.splitlines()
            if line.strip() and not line.startswith("#")
        ]
        assert entries == ["vendor/"]
        assert not [
            line
            for line in duplicates.splitlines()
            if line.strip() and not line.startswith("#")
        ]


# ---------------------------------------------------------------------------
# pre-commit, end to end
# ---------------------------------------------------------------------------


class TestAProseCommitOnAnyStack:
    """Secrets, spelling, document structure and the skill mirror are for every
    stack, and a repository with no Python at all can still commit."""

    def test_it_passes_with_no_python_on_the_machine(self, tmp_path):
        repo = _scratch_repo(tmp_path, "prose")
        _stage(repo, "NOTES.md", "A plain note.\n")

        result, said = _run_pre_commit(
            repo, path=_path(_clean_gitleaks(tmp_path))
        )

        assert result.returncode == 0, said
        assert "Pre-commit checks passed." in said
        assert "NOT RUN — the tests." in said

    def test_every_python_gate_says_the_stack_is_not_python(self, tmp_path):
        repo = _scratch_repo(tmp_path, "nopython", STACK="none")
        _stage(repo, "tools/helper.py", "x = 1\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 0, said
        for gate in ("black, flake8, pylint", "mypy", "imports resolve", "layering"):
            assert gate in said
        assert said.count("stack is none") >= 4

    def test_a_node_stack_is_not_asked_for_a_python_environment(self, tmp_path):
        repo = _scratch_repo(tmp_path, "node", STACK="node")
        _stage(repo, "src/app.js", "export const x = 1;\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 0, said
        assert "stack is node" in said
        assert "no .venv found" not in said


class TestTheTestCommand:
    def test_no_command_is_not_run_and_says_why(self, tmp_path):
        repo = _scratch_repo(tmp_path, "nocmd", STACK="none")
        _stage(repo, "src/app.js", "x\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 0, said
        assert "NOT RUN — the tests: no test command configured." in said

    def test_a_failing_command_refuses_the_commit(self, tmp_path):
        repo = _scratch_repo(tmp_path, "failing", STACK="node", TEST_CMD="exit 3")
        _stage(repo, "src/app.js", "x\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 1, said
        assert "Pre-commit checks FAILED" in said
        assert "tests (exit 3)" in said

    def test_a_passing_command_is_run_from_the_repo_root(self, tmp_path):
        ledger = tmp_path / "ledger"
        repo = _scratch_repo(
            tmp_path,
            "passing",
            STACK="node",
            TEST_CMD=f"echo ran-in $(basename $PWD) >> {posix(ledger)}",
        )
        _stage(repo, "src/app.js", "x\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 0, said
        assert "ran-in passing" in ledger.read_text()

    def test_a_prose_only_commit_does_not_run_it(self, tmp_path):
        ledger = tmp_path / "ledger"
        repo = _scratch_repo(
            tmp_path, "skipped", STACK="node", TEST_CMD=f"echo ran >> {posix(ledger)}"
        )
        _stage(repo, "NOTES.md", "prose\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 0, said
        assert not ledger.exists()
        assert "NOT RUN — the tests." in said

    def test_a_python_project_defaults_to_pytest_over_its_test_dirs(self, tmp_path):
        ledger = tmp_path / "ledger"
        repo = _scratch_repo(tmp_path, "pydefault", STACK="python", TEST_DIRS="tests/unit")
        venv = _stub_venv(repo)
        _stub_tools(venv, ledger, "pytest", "python", "black", "flake8", "pylint", "mypy")
        _stage(repo, "tests/unit/test_a.py", "def test_a():\n    pass\n")

        result, said = _run_pre_commit(
            repo, path=_path(_clean_gitleaks(tmp_path))
        )

        assert result.returncode == 0, said
        assert "python -m pytest tests/unit -q" in ledger.read_text()


class TestPythonGates:
    def test_a_missing_tool_is_failed_not_not_run(self, tmp_path):
        ledger = tmp_path / "ledger"
        repo = _scratch_repo(tmp_path, "missing", STACK="python")
        venv = _stub_venv(repo)
        # Everything but black.
        _stub_tools(venv, ledger, "flake8", "pylint", "mypy", "pytest", "python")
        _stage(repo, "tools/helper.py", "x = 1\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 1, said
        assert "FAILED — black is not installed" in said
        assert "NOT RUN — black" not in said

    @pytest.mark.parametrize("layout", ["bin", "Scripts"])
    def test_the_environment_is_used_on_either_layout(self, tmp_path, layout):
        ledger = tmp_path / "ledger"
        repo = _scratch_repo(tmp_path, f"layout-{layout}", STACK="python")
        venv = _stub_venv(repo, layout=layout)
        _stub_tools(
            venv, ledger, "black", "flake8", "pylint", "mypy", "pytest", "python",
            layout=layout,
        )
        _stage(repo, "tools/helper.py", "x = 1\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 0, said
        used = ledger.read_text()
        assert "black --check" in used and "flake8" in used

    def test_no_environment_refuses_a_python_commit_with_the_fix(self, tmp_path):
        repo = _scratch_repo(tmp_path, "noenv", STACK="python")
        _stage(repo, "tools/helper.py", "x = 1\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 1, said
        assert "no .venv found" in said
        assert "./setup-dev-env.sh" in said

    def test_mypy_not_configured_is_not_run_and_says_so(self, tmp_path):
        ledger = tmp_path / "ledger"
        repo = _scratch_repo(tmp_path, "nomypy", STACK="python")
        venv = _stub_venv(repo)
        _stub_tools(venv, ledger, "black", "flake8", "pylint", "mypy", "pytest", "python")
        _stage(repo, "tools/helper.py", "x = 1\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 0, said
        assert "no [tool.mypy] in pyproject.toml and no mypy.ini" in said
        assert "mypy\n" not in ledger.read_text()

    def test_mypy_runs_when_configured(self, tmp_path):
        ledger = tmp_path / "ledger"
        repo = _scratch_repo(tmp_path, "mypy", STACK="python")
        write_lf((repo / "pyproject.toml"), "[tool.mypy]\nfiles = ['tools']\n")
        venv = _stub_venv(repo)
        _stub_tools(venv, ledger, "black", "flake8", "pylint", "mypy", "pytest", "python")
        _stage(repo, "tools/helper.py", "x = 1\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 0, said
        assert "types (mypy)" in said
        assert "mypy \n" in ledger.read_text() or "mypy" in ledger.read_text()

    def test_layering_is_skipped_when_the_package_directory_is_absent(self, tmp_path):
        ledger = tmp_path / "ledger"
        repo = _scratch_repo(tmp_path, "nopkg", STACK="python", PACKAGE_DIR="src/absent")
        venv = _stub_venv(repo)
        _stub_tools(venv, ledger, "black", "flake8", "pylint", "mypy", "pytest", "python")
        _stage(repo, "tools/helper.py", "x = 1\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 0, said
        assert "NOT RUN — layering: src/absent does not exist." in said


class TestTheProjectLintCommand:
    def test_it_runs_for_any_stack(self, tmp_path):
        ledger = tmp_path / "ledger"
        repo = _scratch_repo(
            tmp_path,
            "lint",
            STACK="node",
            LINT_CMD=f"echo linted >> {posix(ledger)}",
        )
        _stage(repo, "src/app.js", "x\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 0, said
        assert "linted" in ledger.read_text()

    def test_a_failing_one_refuses_the_commit(self, tmp_path):
        repo = _scratch_repo(tmp_path, "badlint", STACK="node", LINT_CMD="exit 1")
        _stage(repo, "src/app.js", "x\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 1, said

    def test_none_configured_is_not_run(self, tmp_path):
        repo = _scratch_repo(tmp_path, "nolint", STACK="node")
        _stage(repo, "src/app.js", "x\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert "NOT RUN — project lint: no KIT_LINT_CMD configured." in said


class TestTheSpellingGateInTheHook:
    def test_a_british_spelling_refuses_the_commit(self, tmp_path):
        repo = _scratch_repo(tmp_path, "british")
        _stage(repo, "NOTES.md", "The behaviour was unclear.\n")  # spelling-ok

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 1, said
        assert "NOTES.md" in said and "behaviour" in said  # spelling-ok

    def test_the_locale_none_turns_it_off_and_says_so(self, tmp_path):
        repo = _scratch_repo(tmp_path, "nolocale", SPELLING_LOCALE="none")
        _stage(repo, "NOTES.md", "The behaviour was unclear.\n")  # spelling-ok

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 0, said
        assert "KIT_SPELLING_LOCALE is none" in said

    def test_the_hooks_directory_is_read_too(self, tmp_path):
        """The hooks have no suffix, so a directory pattern is what lets this
        gate see the densest prose in the repository."""
        repo = _scratch_repo(tmp_path, "hookprose")
        _stage(repo, ".git-hooks/extra-note", "# the colour of the gate\n")  # spelling-ok

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 1, said
        assert "extra-note" in said


class TestSecretsInTheHook:
    def test_a_missing_scanner_refuses_with_the_install_hint(self, tmp_path):
        repo = _scratch_repo(tmp_path, "noscanner")
        _stage(repo, "NOTES.md", "note\n")
        empty_home = tmp_path / "home"
        empty_home.mkdir()

        result, said = _run_pre_commit(
            repo,
            path=BARE_PATH,
            env={
                "HOME": posix(empty_home),
                "LOCALAPPDATA": posix(empty_home),
            },
        )

        assert result.returncode == 1, said
        assert "gitleaks is not installed" in said
        assert "winget install Gitleaks.Gitleaks" in said

    def test_a_scanner_that_finds_something_refuses(self, tmp_path):
        stubs = _stub_on_path(tmp_path / "stubs", "gitleaks", "echo leak >&2; exit 1").parent
        repo = _scratch_repo(tmp_path, "leak")
        _stage(repo, "NOTES.md", "note\n")

        result, said = _run_pre_commit(repo, path=_path(stubs))

        assert result.returncode == 1, said
        assert "looks like a secret" in said

    @pytest.mark.skipif(not IS_WINDOWS, reason="a winget layout is a Windows thing")
    def test_a_winget_install_off_the_path_is_found(self, tmp_path):
        """On Windows a winget install does not reach Git Bash's PATH, so the
        gate looks under `%LOCALAPPDATA%/Microsoft/WinGet/Packages`."""
        local = tmp_path / "local"
        _stub_on_path(
            local / "Microsoft" / "WinGet" / "Packages" / "Gitleaks.Gitleaks_x",
            "gitleaks.exe",
            "exit 0",
        )
        repo = _scratch_repo(tmp_path, "winget")
        _stage(repo, "NOTES.md", "note\n")
        empty_home = tmp_path / "home"
        empty_home.mkdir()

        result, said = _run_pre_commit(
            repo,
            path=BARE_PATH,
            env={"HOME": posix(empty_home), "LOCALAPPDATA": posix(local)},
        )

        assert result.returncode == 0, said


class TestDocumentStructureInTheHook:
    def _agents_docs(self, repo, orphan=False):
        (repo / "docs" / "agents").mkdir(parents=True)
        write_lf((repo / "AGENTS.md"), "# Agents\n\nSee `docs/agents/one.md`.\n")
        write_lf((repo / "docs" / "agents" / "one.md"), "# One\n")
        if orphan:
            write_lf((repo / "docs" / "agents" / "orphan.md"), "# Orphan\n")

    def test_no_agent_docs_is_not_run_not_failed(self, tmp_path):
        repo = _scratch_repo(tmp_path, "nodocs")
        _stage(repo, "NOTES.md", "note\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 0, said
        assert "NOT RUN — no AGENTS.md or docs/agents" in said

    def test_an_unreachable_doc_refuses_the_commit(self, tmp_path):
        repo = _scratch_repo(tmp_path, "orphan")
        self._agents_docs(repo, orphan=True)
        _stage(repo, "NOTES.md", "note\n")

        result, said = _run_pre_commit(
            repo, path=_path(_clean_gitleaks(tmp_path), _python_dir())
        )

        assert result.returncode == 1, said
        assert "orphan.md" in said and "nothing reaches it" in said

    def test_a_reachable_tree_passes(self, tmp_path):
        repo = _scratch_repo(tmp_path, "reachable")
        self._agents_docs(repo)
        # The registry is required once agent docs exist.
        shutil.copyfile(
            HOOKS.parent / "tools" / "document_types.yaml",
            repo / "tools" / "document_types.yaml",
        )
        write_lf((repo / "tools" / "document_types.yaml"), "types: []\n")
        # The shipped issue registry names rules this scratch tree does not hold.
        (repo / "tools" / "issue_types.yaml").unlink()
        _stage(repo, "NOTES.md", "note\n")

        result, said = _run_pre_commit(
            repo, path=_path(_clean_gitleaks(tmp_path), _python_dir())
        )

        assert result.returncode == 0, said

    def test_agent_docs_with_no_interpreter_is_failed_not_skipped(self, tmp_path):
        repo = _scratch_repo(tmp_path, "nointerp")
        self._agents_docs(repo)
        _stage(repo, "NOTES.md", "note\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 1, said
        assert "no working python" in said


class TestTheSkillMirrorInTheHook:
    def test_a_skill_with_no_link_refuses_the_commit(self, tmp_path):
        repo = _scratch_repo(tmp_path, "nolink")
        _stage(repo, ".agents/skills/aes-thing/SKILL.md", "---\nname: aes-thing\n---\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 1, said
        assert "has no link in .claude/skills" in said

    def test_a_correct_skill_passes(self, tmp_path):
        repo = _scratch_repo(tmp_path, "linked")
        _stage(repo, ".agents/skills/aes-thing/SKILL.md", "---\nname: aes-thing\n---\n")
        _stage_link(repo, ".claude/skills/aes-thing", "../../.agents/skills/aes-thing")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert result.returncode == 0, said

    def test_no_skills_staged_is_skipped_and_says_so(self, tmp_path):
        repo = _scratch_repo(tmp_path, "noskills")
        _stage(repo, "NOTES.md", "note\n")

        result, said = _run_pre_commit(repo, path=_path(_clean_gitleaks(tmp_path)))

        assert "no skills staged — skipping the skill mirror gate" in said


def test_the_hooks_run_with_the_os_independent_path_helpers():
    """A guard on the harness itself: the paths handed to bash are POSIX-style."""
    assert "\\" not in posix(HOOKS)
    assert os.path.isdir(HOOKS)


class TestCommitMessageTrailer:
    """A trailer with a placeholder instead of an address credits nobody."""

    @staticmethod
    def _run(tmp_path, message):
        import subprocess

        msg = tmp_path / "MSG"
        msg.write_text(message, encoding="utf-8")
        hook = HOOKS / "commit-msg.sh"
        return subprocess.run(
            ["bash", hook.as_posix(), msg.as_posix()],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_a_real_address_passes(self, tmp_path):
        done = self._run(tmp_path, "feat: x\n\nCo-Authored-By: A B <ab@example.com>\n")
        assert done.returncode == 0

    def test_a_placeholder_is_refused(self, tmp_path):
        done = self._run(tmp_path, "feat: x\n\nCo-Authored-By: A B <[REDACTED_EMAIL]>\n")
        assert done.returncode == 1
        assert "no real address" in done.stdout

    def test_a_trailer_with_no_brackets_is_refused(self, tmp_path):
        done = self._run(tmp_path, "feat: x\n\nCo-Authored-By: A B\n")
        assert done.returncode == 1

    def test_a_message_with_no_trailer_passes(self, tmp_path):
        assert self._run(tmp_path, "feat: x\n").returncode == 0
