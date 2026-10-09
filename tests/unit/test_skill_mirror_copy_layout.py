"""The skill-mirror gate in the copy layout, red then green.

`KIT_SKILL_LAYOUT="copy"` keeps every skill as real files in `.agents/skills` and
`.claude/skills`, and the gate proves the copies are byte-identical to their
source. Each refusal below breaks exactly one thing in a tree that was otherwise
correct, and the green case comes first so the refusals mean something.
"""

from __future__ import annotations

import shutil

from hook_harness import (
    BASH,
    HOOKS,
    _git,
    _run_gate,
    _scratch_repo,
    _stage_link,
    posix,
    write_lf,
)

GATE = HOOKS / "skill-mirror.sh"

SKILL = "---\nname: {name}\ndescription: A skill.\n---\n\n# {name}\n\n{body}"


def _gate(cwd):
    return _run_gate([BASH, posix(GATE)], cwd)


def _repo(tmp_path, label):
    return _scratch_repo(tmp_path, label, SKILL_LAYOUT="copy")


def _own(repo, name="aes-thing", body="Do the thing.\n", extra=()):
    """Our skill, and its byte-identical copy for Claude Code."""
    for root in (".agents/skills", ".claude/skills"):
        directory = repo / root / name
        directory.mkdir(parents=True)
        write_lf(directory / "SKILL.md", SKILL.format(name=name, body=body))
        for basename, contents in extra:
            write_lf(directory / basename, contents)
    _git("add", "-A", cwd=repo)


def _borrowed(repo, name="borrowed", source="upstream"):
    """A pristine vendored skill, with identical copies in both skills trees."""
    for root in (f"vendor/{source}", ".agents/skills", ".claude/skills"):
        directory = repo / root / name
        directory.mkdir(parents=True)
        write_lf(directory / "SKILL.md", SKILL.format(name=name, body="Borrowed.\n"))
    _git("add", "-A", cwd=repo)


class TestTheGreenCase:
    def test_a_tree_of_identical_copies_passes_and_says_it_is_the_copy_layout(
        self, tmp_path
    ):
        repo = _repo(tmp_path, "green")
        _own(repo)
        _borrowed(repo)

        result = _gate(repo)

        assert result.returncode == 0, result.stdout
        assert "layout: copy" in result.stdout
        assert "2 skill(s)" in result.stdout


class TestWhatItRefuses:
    def test_a_claude_copy_that_differs_from_its_source(self, tmp_path):
        repo = _repo(tmp_path, "drift")
        _own(repo)
        write_lf(
            repo / ".claude/skills/aes-thing/SKILL.md",
            SKILL.format(name="aes-thing", body="Quietly different.\n"),
        )
        _git("add", "-A", cwd=repo)

        result = _gate(repo)

        assert result.returncode == 1
        assert ".claude/skills/aes-thing is not byte-identical" in result.stdout

    def test_a_skill_with_no_claude_copy(self, tmp_path):
        repo = _repo(tmp_path, "nocopy")
        _own(repo)
        _git("rm", "-r", "-q", "--cached", ".claude/skills/aes-thing", cwd=repo)
        shutil.rmtree(repo / ".claude/skills/aes-thing")

        result = _gate(repo)

        assert result.returncode == 1
        assert "has no copy in .claude/skills" in result.stdout

    def test_a_claude_copy_with_an_extra_file(self, tmp_path):
        repo = _repo(tmp_path, "extra")
        _own(repo)
        write_lf(repo / ".claude/skills/aes-thing/notes.md", "stray\n")
        _git("add", "-A", cwd=repo)

        assert _gate(repo).returncode == 1

    def test_a_vendored_copy_edited_away_from_the_pristine_source(self, tmp_path):
        repo = _repo(tmp_path, "edited")
        _borrowed(repo)
        for root in (".agents/skills", ".claude/skills"):
            write_lf(
                repo / root / "borrowed" / "SKILL.md",
                SKILL.format(name="borrowed", body="Edited locally.\n"),
            )
        _git("add", "-A", cwd=repo)

        result = _gate(repo)

        assert result.returncode == 1
        assert "differs from its pristine source" in result.stdout

    def test_any_link_in_the_skills_trees(self, tmp_path):
        repo = _repo(tmp_path, "link")
        _own(repo)
        _git("rm", "-r", "-q", "--cached", ".claude/skills/aes-thing", cwd=repo)
        shutil.rmtree(repo / ".claude/skills/aes-thing")
        _stage_link(repo, ".claude/skills/aes-thing", "../../.agents/skills/aes-thing")

        result = _gate(repo)

        assert result.returncode == 1
        assert "these are links" in result.stdout

    def test_a_claude_entry_with_no_source(self, tmp_path):
        repo = _repo(tmp_path, "orphan")
        _own(repo)
        shutil.copytree(repo / ".claude/skills/aes-thing", repo / ".claude/skills/aes-ghost")
        write_lf(
            repo / ".claude/skills/aes-ghost/SKILL.md",
            SKILL.format(name="aes-ghost", body="No source.\n"),
        )
        _git("add", "-A", cwd=repo)

        result = _gate(repo)

        assert result.returncode == 1
        assert "has no source in .agents/skills" in result.stdout

    def test_a_name_that_does_not_match_its_directory(self, tmp_path):
        repo = _repo(tmp_path, "rename")
        _own(repo)
        for root in (".agents/skills", ".claude/skills"):
            write_lf(
                repo / root / "aes-thing" / "SKILL.md",
                SKILL.format(name="aes-other", body="x\n"),
            )
        _git("add", "-A", cwd=repo)

        result = _gate(repo)

        assert result.returncode == 1
        assert "declares 'name: aes-other'" in result.stdout

    def test_a_companion_nothing_points_at(self, tmp_path):
        repo = _repo(tmp_path, "companion")
        _own(repo, extra=[("steps.md", "Step detail.\n")])

        result = _gate(repo)

        assert result.returncode == 1
        assert "is not named in backticks" in result.stdout


def test_the_default_layout_is_still_the_link_layout(tmp_path):
    """Nothing in a project's config means links, so every existing install and
    every link-layout test keeps its meaning."""
    repo = _scratch_repo(tmp_path, "default")
    _own(repo)

    result = _gate(repo)

    assert "layout: copy" not in result.stdout
