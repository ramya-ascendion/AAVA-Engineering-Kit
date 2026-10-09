"""The spelling gate and the secret-scan wrapper, run as the hooks run them.

Red then green for each: a tree with one thing wrong exits non-zero, and the same
tree with it fixed exits zero. Gitleaks itself is stubbed here (its job is not
under test); a separate manual proof runs the real one.
"""

from __future__ import annotations

import pytest

from hook_harness import (
    BARE_PATH,
    BASH,
    HOOKS,
    _git,
    _run,
    _scratch_repo,
    _stub_on_path,
    posix,
    write_lf,
)

BRITISH = "The colour" + " of the behaviour"  # spelling-ok


def _spell(repo, *files, **env):
    return _run(
        f'"{posix(repo)}/.git-hooks/american-spelling.sh" ' + " ".join(files),
        cwd=repo,
        env={"PATH": BARE_PATH, **env},
    )


class TestSpelling:
    def test_a_british_word_is_refused_with_its_line(self, tmp_path):
        repo = _scratch_repo(tmp_path, "red")
        write_lf(repo / "note.md", f"fine\n{BRITISH}\n")

        result = _spell(repo, "note.md")

        assert result.returncode == 1
        assert "note.md" in result.stdout and "2:" in result.stdout

    def test_the_same_file_corrected_passes(self, tmp_path):
        repo = _scratch_repo(tmp_path, "green")
        write_lf(repo / "note.md", "The color of the behavior\n")

        assert _spell(repo, "note.md").returncode == 0

    def test_a_snake_case_identifier_is_seen(self, tmp_path):
        """`\\b` counts `_` as a word character, so a snake_case spelling slipped
        past it; the letter-test boundary does not."""
        repo = _scratch_repo(tmp_path, "snake")
        write_lf(repo / "m.py", "sends_no_authorisation = 1\n")  # spelling-ok

        assert _spell(repo, "m.py").returncode == 1

    def test_an_american_word_that_contains_a_stem_is_not_flagged(self, tmp_path):
        repo = _scratch_repo(tmp_path, "stem")
        write_lf(repo / "m.md", "A realistic fulfillment of the area.\n")

        assert _spell(repo, "m.md").returncode == 0

    def test_the_line_marker_exempts_one_line(self, tmp_path):
        repo = _scratch_repo(tmp_path, "marker")
        write_lf(repo / "q.md", f"{BRITISH}  spelling-ok\n")

        assert _spell(repo, "q.md").returncode == 0

    def test_the_exempt_list_exempts_a_file_and_a_directory(self, tmp_path):
        repo = _scratch_repo(tmp_path, "exempt")
        (repo / "vendor" / "x").mkdir(parents=True)
        write_lf(repo / "vendor" / "x" / "a.md", BRITISH + "\n")
        write_lf(repo / "quoted.md", BRITISH + "\n")
        write_lf(repo / ".git-hooks" / "spelling-exempt", "# why\nquoted.md\nvendor/\n")

        assert _spell(repo, "vendor/x/a.md", "quoted.md").returncode == 0

    def test_the_gate_is_exempt_from_its_own_word_list(self, tmp_path):
        repo = _scratch_repo(tmp_path, "self")

        assert _spell(repo, ".git-hooks/american-spelling.sh").returncode == 0

    def test_locale_none_skips_and_says_so(self, tmp_path):
        repo = _scratch_repo(tmp_path, "none", SPELLING_LOCALE="none")
        write_lf(repo / "note.md", BRITISH + "\n")

        result = _spell(repo, "note.md")

        assert result.returncode == 0
        assert "KIT_SPELLING_LOCALE is none" in result.stdout

    def test_an_unknown_locale_is_a_failure_not_a_pass(self, tmp_path):
        repo = _scratch_repo(tmp_path, "weird", SPELLING_LOCALE="klingon")
        write_lf(repo / "note.md", "fine\n")

        assert _spell(repo, "note.md").returncode == 1


def _scan(repo, path, *args, **env):
    return _run(
        f'"{posix(repo)}/.git-hooks/secret-scan.sh" ' + " ".join(args),
        cwd=repo,
        env={"PATH": path, **env},
    )


class TestSecretScan:
    def _home(self, tmp_path):
        home = tmp_path / "home"
        home.mkdir(exist_ok=True)
        return {"HOME": posix(home), "LOCALAPPDATA": posix(home)}

    def test_no_scanner_fails_with_the_install_hint(self, tmp_path):
        repo = _scratch_repo(tmp_path, "none")

        result = _scan(repo, BARE_PATH, **self._home(tmp_path))

        assert result.returncode == 1
        assert "winget install Gitleaks.Gitleaks" in result.stdout

    def test_a_clean_scan_exits_zero_quietly(self, tmp_path):
        stubs = _stub_on_path(tmp_path / "s", "gitleaks", "exit 0").parent
        repo = _scratch_repo(tmp_path, "clean")

        result = _scan(repo, f"{posix(stubs)}:{BARE_PATH}", **self._home(tmp_path))

        assert result.returncode == 0 and result.stdout == ""

    def test_a_finding_exits_one_and_shows_the_scanners_report(self, tmp_path):
        stubs = _stub_on_path(tmp_path / "s", "gitleaks", "echo RULE-HIT; exit 1").parent
        repo = _scratch_repo(tmp_path, "hit")

        result = _scan(repo, f"{posix(stubs)}:{BARE_PATH}", **self._home(tmp_path))

        assert result.returncode == 1
        assert "RULE-HIT" in result.stdout and "looks like a secret" in result.stdout

    def test_a_scanner_that_did_not_run_is_failed_not_clean(self, tmp_path):
        stubs = _stub_on_path(tmp_path / "s", "gitleaks", "exit 126").parent
        repo = _scratch_repo(tmp_path, "broken")

        result = _scan(repo, f"{posix(stubs)}:{BARE_PATH}", **self._home(tmp_path))

        assert result.returncode == 1
        assert "did not happen" in result.stdout

    def test_an_old_scanner_without_protect_falls_back_to_git(self, tmp_path):
        body = (
            'case "$1" in protect) echo "unknown command protect" >&2; exit 1;; '
            'git) echo "ran git $*" >> "' + posix(tmp_path / "led") + '"; exit 0;; esac'
        )
        stubs = _stub_on_path(tmp_path / "s", "gitleaks", body).parent
        repo = _scratch_repo(tmp_path, "old")

        result = _scan(repo, f"{posix(stubs)}:{BARE_PATH}", **self._home(tmp_path))

        assert result.returncode == 0, result.stdout
        assert "git --staged" in (tmp_path / "led").read_text()

    def test_tree_mode_scans_the_working_tree_without_history(self, tmp_path):
        body = 'echo "$*" >> "' + posix(tmp_path / "led") + '"; exit 0'
        stubs = _stub_on_path(tmp_path / "s", "gitleaks", body).parent
        repo = _scratch_repo(tmp_path, "tree")

        _scan(repo, f"{posix(stubs)}:{BARE_PATH}", "--tree", **self._home(tmp_path))

        assert "detect --no-git" in (tmp_path / "led").read_text()

    def test_a_repo_config_is_passed_through(self, tmp_path):
        body = 'echo "$*" >> "' + posix(tmp_path / "led") + '"; exit 0'
        stubs = _stub_on_path(tmp_path / "s", "gitleaks", body).parent
        repo = _scratch_repo(tmp_path, "cfg")
        write_lf(repo / ".gitleaks.toml", "title = 'x'\n")

        _scan(repo, f"{posix(stubs)}:{BARE_PATH}", **self._home(tmp_path))

        assert "--config .gitleaks.toml" in (tmp_path / "led").read_text()


def test_every_shell_script_parses():
    import subprocess

    scripts = [p for p in HOOKS.iterdir() if p.suffix == ".sh" or p.name.startswith("pre-")]
    assert len(scripts) >= 6
    for script in scripts:
        done = subprocess.run([BASH, "-n", posix(script)], capture_output=True, text=True)
        assert done.returncode == 0, (script.name, done.stderr)
    assert _git and pytest  # imported for the other tests in this module
