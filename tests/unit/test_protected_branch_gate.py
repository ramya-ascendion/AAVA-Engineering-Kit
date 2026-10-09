"""The protected-branch gate, run as the hook runs it.

Red then green: a commit on the protected branch is refused, and the same work
on its own branch is accepted. The gate is off unless the config turns it on,
and it never blocks the first commit of a repository.
"""

from __future__ import annotations

from hook_harness import BARE_PATH, _git, _run, _scratch_repo, posix


def _gate(repo):
    return _run(
        f'"{posix(repo)}/.git-hooks/protected-branch.sh" ',
        cwd=repo,
        env={"PATH": BARE_PATH},
    )


def _on(repo, branch):
    _git("checkout", "-q", "-B", branch, cwd=repo)


class TestProtectedBranch:
    def test_a_commit_on_the_default_branch_is_refused(self, tmp_path):
        repo = _scratch_repo(
            tmp_path, "red", PROTECT_BRANCHES="yes", DEFAULT_BRANCH="master"
        )
        _on(repo, "master")

        result = _gate(repo)

        assert result.returncode == 1
        assert "master" in result.stdout and "own branch" in result.stdout

    def test_the_same_work_on_its_own_branch_passes(self, tmp_path):
        repo = _scratch_repo(
            tmp_path, "green", PROTECT_BRANCHES="yes", DEFAULT_BRANCH="master"
        )
        _on(repo, "worktree-something")

        assert _gate(repo).returncode == 0

    def test_a_listed_branch_is_protected_even_if_it_is_not_the_default(self, tmp_path):
        repo = _scratch_repo(
            tmp_path,
            "listed",
            PROTECT_BRANCHES="yes",
            DEFAULT_BRANCH="main",
            PROTECTED_BRANCHES="main release",
        )
        _on(repo, "release")

        assert _gate(repo).returncode == 1

    def test_it_is_off_unless_the_config_turns_it_on(self, tmp_path):
        repo = _scratch_repo(tmp_path, "off", DEFAULT_BRANCH="master")
        _on(repo, "master")

        assert _gate(repo).returncode == 0

    def test_the_first_commit_of_a_repository_is_never_blocked(self, tmp_path):
        repo = tmp_path / "fresh"
        repo.mkdir()
        _git("init", "--quiet", "-b", "main", cwd=repo)
        (repo / ".kit").mkdir()
        (repo / ".git-hooks").mkdir()
        import shutil
        from hook_harness import HOOKS

        shutil.copytree(HOOKS, repo / ".git-hooks", dirs_exist_ok=True)
        (repo / ".kit" / "config.env").write_text(
            'KIT_PROTECT_BRANCHES="yes"\nKIT_DEFAULT_BRANCH="main"\n', encoding="utf-8"
        )

        assert _gate(repo).returncode == 0
