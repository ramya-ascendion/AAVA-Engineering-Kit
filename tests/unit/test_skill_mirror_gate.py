"""The skill-mirror gate: one shape for the skills tree, read from the index.

`.git-hooks/skill-mirror.sh` asks eight questions about the skills tree in a commit.
Its header says what each one is and why. Most of the tests below build a small
skills tree and break exactly one thing in it, because a gate that refuses
everything gets switched off and a gate that refuses nothing is not a gate.

**Links are three things on Windows**, and the second half of this module holds
the gate to saying which it found: a symlink (mode 120000), a plain file holding
the relative target (what `core.symlinks=false` produces, accepted only there),
and a junction (which git cannot store, and stages as a copy).

The gate reads the index rather than the working tree, so every test stages its
tree and none of them commits.
"""

from __future__ import annotations

import subprocess

import pytest

from hook_harness import (
    BASH,
    HOOKS,
    IS_WINDOWS,
    REPO,
    _git,
    _run_gate,
    _scratch_repo,
    _stage_link,
    posix,
    write_lf,
)

GATE = HOOKS / "skill-mirror.sh"


def _gate(cwd):
    """Run the gate against whatever is staged in `cwd`.

    It takes no arguments: the staged file list every other gate receives answers
    "what changed", and this one asks "what shape is the skills tree".
    """
    return _run_gate([BASH, posix(GATE)], cwd)


def _skill(repo, name="aes-thing", body="Do the thing.\n", companions=(), link=True):
    """Stage a well-formed skill, plus whatever companions a test asks for.

    The `.claude/skills` link and the matching `name:` field are questions 1 to
    6, and the companion tests are about 7 and 8 — so they are built correct, and
    a test that broke one of them would be failing for a reason it does not claim
    to be about.

    `companions` is (basename, contents) pairs, written verbatim, because the
    frontmatter question is about the exact first bytes of a file.
    """
    skill_dir = repo / ".agents" / "skills" / name
    skill_dir.mkdir(parents=True)
    write_lf(
        skill_dir / "SKILL.md",
        f"---\nname: {name}\ndescription: A skill.\n---\n\n# Thing\n\n{body}",
    )
    for basename, contents in companions:
        write_lf(skill_dir / basename, contents)

    _git("add", "-A", cwd=repo)
    if link:
        _stage_link(repo, f".claude/skills/{name}", f"../../.agents/skills/{name}")
    return skill_dir


def _vendored(repo, name="borrowed", source="some-upstream", link=True):
    """Stage a pristine vendored skill and the link that borrows it."""
    vendor_dir = repo / "vendor" / source / name
    vendor_dir.mkdir(parents=True)
    write_lf(
        vendor_dir / "SKILL.md",
        f"---\nname: {name}\ndescription: Borrowed.\n---\n\n# Borrowed\n",
    )
    _git("add", "-A", cwd=repo)
    if link:
        _stage_link(repo, f".agents/skills/{name}", f"../../vendor/{source}/{name}")
        _stage_link(repo, f".claude/skills/{name}", f"../../.agents/skills/{name}")


class TestTheShapeItRequires:
    def test_a_well_formed_tree_passes_and_says_which_links_it_found(self, tmp_path):
        """The green case, so the refusals below mean something. Without it every
        other test would pass against a gate that refused every tree it was
        handed."""
        repo = _scratch_repo(tmp_path, "green")
        _skill(repo)

        result = _gate(repo)

        assert result.returncode == 0, result.stdout
        assert "links in the index: symlink x1" in result.stdout

    def test_a_tree_with_no_skills_has_nothing_to_check_and_says_so(self, tmp_path):
        repo = _scratch_repo(tmp_path, "empty")

        result = _gate(repo)

        assert result.returncode == 0, result.stdout
        assert "no skills tree to check" in result.stdout

    def test_a_committed_copy_in_claude_skills_is_refused(self, tmp_path):
        """Question 1. The copy happens to be identical today, and editing either
        one leaves the other stale while each harness reads a different one."""
        repo = _scratch_repo(tmp_path, "copy")
        _skill(repo, link=False)
        copy = repo / ".claude" / "skills" / "aes-thing"
        copy.mkdir(parents=True)
        write_lf(copy / "SKILL.md", "---\nname: aes-thing\n---\n")
        _git("add", "-A", cwd=repo)

        result = _gate(repo)

        assert result.returncode == 1
        assert "is a committed copy, not a link" in result.stdout

    def test_a_link_to_the_wrong_name_is_refused(self, tmp_path):
        """Question 2. The same name on both sides means a reader never has to
        work out which skill a link serves."""
        repo = _scratch_repo(tmp_path, "wrong-name")
        _skill(repo, link=False)
        _stage_link(repo, ".claude/skills/aes-thing", "../../.agents/skills/other")

        result = _gate(repo)

        assert result.returncode == 1
        assert "must point at '../../.agents/skills/aes-thing'" in result.stdout

    def test_a_dangling_link_is_refused(self, tmp_path):
        """Question 3."""
        repo = _scratch_repo(tmp_path, "dangling")
        _stage_link(repo, ".claude/skills/ghost", "../../.agents/skills/ghost")

        result = _gate(repo)

        assert result.returncode == 1
        assert "which has no" in result.stdout and "dangling" in result.stdout

    def test_a_skill_with_no_link_back_is_refused(self, tmp_path):
        """Question 4. A skill with no link is invisible to Claude Code, which is
        quieter than a broken link and just as wrong."""
        repo = _scratch_repo(tmp_path, "unlinked")
        _skill(repo, link=False)

        result = _gate(repo)

        assert result.returncode == 1
        assert "has no link in .claude/skills" in result.stdout

    def test_a_skill_whose_name_field_disagrees_with_its_directory_is_refused(
        self, tmp_path
    ):
        """Question 6. A half-finished rename lists the skill under one name and
        files it under the other."""
        repo = _scratch_repo(tmp_path, "renamed")
        skill_dir = _skill(repo)
        write_lf(skill_dir / "SKILL.md", "---\nname: something-else\n---\n")
        _git("add", "-A", cwd=repo)

        result = _gate(repo)

        assert result.returncode == 1
        assert "declares 'name: something-else'" in result.stdout

    def test_a_skill_directory_with_no_skill_md_is_refused(self, tmp_path):
        repo = _scratch_repo(tmp_path, "no-skill-md")
        notes = repo / ".agents" / "skills" / "aes-thing"
        notes.mkdir(parents=True)
        write_lf(notes / "notes.txt", "x\n")
        _git("add", "-A", cwd=repo)
        _stage_link(repo, ".claude/skills/aes-thing", "../../.agents/skills/aes-thing")

        result = _gate(repo)

        assert result.returncode == 1
        assert "has no SKILL.md" in result.stdout


class TestVendoredSkillsOfAnySource:
    """The vendor path is read generically: any directory under `vendor/`."""

    @pytest.mark.parametrize("source", ["mattpocock-skills", "another-upstream"])
    def test_a_borrowed_skill_linked_into_agents_passes(self, tmp_path, source):
        repo = _scratch_repo(tmp_path, f"vendor-{source}")
        _vendored(repo, source=source)

        result = _gate(repo)

        assert result.returncode == 0, result.stdout

    def test_a_link_into_a_vendor_copy_that_does_not_exist_is_refused(self, tmp_path):
        repo = _scratch_repo(tmp_path, "vendor-missing")
        _vendored(repo, link=False)
        _stage_link(repo, ".agents/skills/borrowed", "../../vendor/elsewhere/borrowed")
        _stage_link(repo, ".claude/skills/borrowed", "../../.agents/skills/borrowed")

        result = _gate(repo)

        assert result.returncode == 1
        assert "no committed" in result.stdout

    def test_a_link_into_agents_may_only_point_into_vendor(self, tmp_path):
        repo = _scratch_repo(tmp_path, "vendor-elsewhere")
        _vendored(repo, link=False)
        _stage_link(repo, ".agents/skills/borrowed", "../../somewhere/borrowed")
        _stage_link(repo, ".claude/skills/borrowed", "../../.agents/skills/borrowed")

        result = _gate(repo)

        assert result.returncode == 1
        assert "may only point at '../../vendor/<source>/borrowed'" in result.stdout

    def test_two_copies_of_one_skill_are_refused(self, tmp_path):
        """Question 5. After an upstream update replaces each link with a
        directory of fresh files, every other check still passes."""
        repo = _scratch_repo(tmp_path, "two-copies")
        _vendored(repo, link=False)
        _skill(repo, name="borrowed")

        result = _gate(repo)

        assert result.returncode == 1
        assert "two copies of one skill" in result.stdout

    def test_a_vendored_skills_own_tree_is_not_policed(self, tmp_path):
        """A vendored skill's shape is upstream's, and policing it here would be
        the fork the vendor rule exists to prevent."""
        repo = _scratch_repo(tmp_path, "vendor-companion")
        _vendored(repo)
        write_lf(repo / "vendor" / "some-upstream" / "borrowed" / "loose.md", "# loose\n")
        _git("add", "vendor", cwd=repo)

        result = _gate(repo)

        assert result.returncode == 0, result.stdout


class TestWindowsLinks:
    """A symlink, a plain-file link, or a junction — and which one was found."""

    def test_a_plain_file_link_is_accepted_only_with_symlinks_off(self, tmp_path):
        repo = _scratch_repo(tmp_path, "plain-on")
        _skill(repo, link=False)
        _git("config", "core.symlinks", "false", cwd=repo)
        (repo / ".claude" / "skills").mkdir(parents=True)
        write_lf(
            repo / ".claude" / "skills" / "aes-thing",
            "../../.agents/skills/aes-thing",
        )
        _git("add", "-f", ".claude/skills/aes-thing", cwd=repo)

        result = _gate(repo)

        assert result.returncode == 0, result.stdout
        assert "links in the index: plain-file x1" in result.stdout

    def test_the_same_plain_file_is_refused_where_symlinks_work(self, tmp_path):
        repo = _scratch_repo(tmp_path, "plain-off")
        _skill(repo, link=False)
        _git("config", "core.symlinks", "true", cwd=repo)
        (repo / ".claude" / "skills").mkdir(parents=True)
        write_lf(
            repo / ".claude" / "skills" / "aes-thing",
            "../../.agents/skills/aes-thing",
        )
        _git("add", "-f", ".claude/skills/aes-thing", cwd=repo)

        result = _gate(repo)

        assert result.returncode == 1
        assert "committed as a plain file" in result.stdout
        assert "only where core.symlinks=false" in result.stdout

    def test_a_plain_file_with_the_wrong_target_is_still_refused(self, tmp_path):
        repo = _scratch_repo(tmp_path, "plain-wrong")
        _skill(repo, link=False)
        _git("config", "core.symlinks", "false", cwd=repo)
        (repo / ".claude" / "skills").mkdir(parents=True)
        write_lf(repo / ".claude" / "skills" / "aes-thing", "../../.agents/skills/nope")
        _git("add", "-f", ".claude/skills/aes-thing", cwd=repo)

        result = _gate(repo)

        assert result.returncode == 1
        assert "points at '../../.agents/skills/nope'" in result.stdout

    @pytest.mark.skipif(not IS_WINDOWS, reason="junctions are an NTFS thing")
    def test_a_staged_junction_is_named_as_one(self, tmp_path):
        """Git cannot store a junction: it stages the directory behind it, file by
        file. The gate must say that it found a junction, and how to undo it,
        rather than leaving a reader with an unexplained 'committed copy'."""
        repo = _scratch_repo(tmp_path, "junction")
        _skill(repo, link=False)
        (repo / ".claude" / "skills").mkdir(parents=True)
        made = subprocess.run(
            [
                "cmd",
                "/c",
                "mklink",
                "/J",
                str(repo / ".claude" / "skills" / "aes-thing"),
                str(repo / ".agents" / "skills" / "aes-thing"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if made.returncode != 0:
            pytest.skip(f"this machine will not make a junction: {made.stderr}")
        _git("add", "-A", cwd=repo)

        result = _gate(repo)

        assert result.returncode == 1
        assert "is a committed copy, not a link" in result.stdout
        assert "a junction in the working tree" in result.stdout
        assert "git rm -r --cached .claude/skills/aes-thing" in result.stdout

    @pytest.mark.skipif(not IS_WINDOWS, reason="junctions are an NTFS thing")
    def test_a_junction_in_the_working_tree_is_reported_and_accepted(self, tmp_path):
        """With the committed link in the index and a junction on disk, the
        working tree resolves, and the gate says which kind it is using."""
        repo = _scratch_repo(tmp_path, "junction-ok")
        _skill(repo)
        link = repo / ".claude" / "skills" / "aes-thing"
        if link.exists() or link.is_symlink():
            link.unlink() if link.is_file() or link.is_symlink() else link.rmdir()
        link.parent.mkdir(parents=True, exist_ok=True)
        made = subprocess.run(
            [
                "cmd",
                "/c",
                "mklink",
                "/J",
                str(link),
                str(repo / ".agents" / "skills" / "aes-thing"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if made.returncode != 0:
            pytest.skip(f"this machine will not make a junction: {made.stderr}")

        result = _gate(repo)

        assert result.returncode == 0, result.stdout
        assert "links in the working tree: junction x1" in result.stdout


class TestTheCompanionFileRules:
    """Questions 7 and 8: every companion is named from its SKILL.md in
    backticks, and none carries YAML frontmatter."""

    def test_a_skill_pointing_at_its_companion_passes(self, tmp_path):
        repo = _scratch_repo(tmp_path, "companion-green")
        _skill(
            repo,
            body="Read `quality-bars.md` beside this file before the gate.\n",
            companions=[("quality-bars.md", "# Bars\n\nRun them.\n")],
        )

        result = _gate(repo)

        assert result.returncode == 0, result.stdout

    def test_a_pointer_early_in_a_long_skill_passes(self, tmp_path):
        """Piping the skill into `grep -q` under `pipefail` can fail a search that
        matched: `grep -q` stops at the first match, the writer dies on a broken
        pipe, and `pipefail` turns that into a failed search. A pointer on line one
        followed by a long body loses that race every time."""
        repo = _scratch_repo(tmp_path, "long-skill")
        _skill(
            repo,
            body="Read `quality-bars.md` first.\n" + "More steps.\n" * 200_000,
            companions=[("quality-bars.md", "# Bars\n\nRun them.\n")],
        )

        result = _gate(repo)

        assert result.returncode == 0, result.stdout

    def test_a_companion_nothing_points_at_is_refused(self, tmp_path):
        repo = _scratch_repo(tmp_path, "orphan")
        _skill(repo, companions=[("quality-bars.md", "# Bars\n\nRun them.\n")])

        result = _gate(repo)

        assert result.returncode == 1
        assert "quality-bars.md" in result.stdout
        assert "not named in backticks" in result.stdout

    def test_a_name_contained_in_a_longer_one_is_not_a_pointer(self, tmp_path):
        """`ranking.md` is inside `frontier-ranking.md`, so a gate matching on the
        bare basename would report a pointer that is not there."""
        repo = _scratch_repo(tmp_path, "substring")
        _skill(
            repo,
            body="Rank it with `frontier-ranking.md` beside this file.\n",
            companions=[
                ("frontier-ranking.md", "# Ranking\n\nRank it.\n"),
                ("ranking.md", "# Also ranking\n\nRank it again.\n"),
            ],
        )

        result = _gate(repo)

        assert result.returncode == 1
        assert "ranking.md is not named in backticks" in result.stdout
        assert "frontier-ranking.md is not named" not in result.stdout

    @pytest.mark.parametrize(
        "contents",
        [
            "---\nname: bars\n---\n\n# Bars\n",
            "\n---\nname: bars\n---\n\n# Bars\n",
            "--- \nname: bars\n---\n\n# Bars\n",
        ],
        ids=["plain", "after-a-blank-line", "trailing-space"],
    )
    def test_a_companion_carrying_frontmatter_is_refused(self, tmp_path, contents):
        """Read from the first line with anything on it: a `head -1` equality test
        passes the blank-line and trailing-space forms, and every YAML parser
        reads the frontmatter anyway."""
        repo = _scratch_repo(tmp_path, "frontmatter")
        _skill(
            repo,
            body="Read `quality-bars.md` beside this file.\n",
            companions=[("quality-bars.md", contents)],
        )

        result = _gate(repo)

        assert result.returncode == 1
        assert "opens with YAML frontmatter" in result.stdout

    def test_a_non_markdown_file_beside_a_skill_is_not_a_companion(self, tmp_path):
        """Question 7 stops at Markdown, depth one. A skill may commit a diagram
        or a script beside its `SKILL.md`, and neither is a step of the skill."""
        repo = _scratch_repo(tmp_path, "not-a-companion")
        skill_dir = _skill(repo)
        write_lf(skill_dir / "shape.mmd", "flowchart LR\n  A --> B\n")
        write_lf(skill_dir / "run.sh", "#!/bin/bash\nexit 0\n")
        _git("add", ".agents", cwd=repo)

        result = _gate(repo)

        assert result.returncode == 0, result.stdout


class TestTheSkillPrefix:
    def test_an_own_skill_without_the_configured_prefix_is_noted_not_refused(
        self, tmp_path
    ):
        repo = _scratch_repo(tmp_path, "prefix", SKILL_PREFIX="act")
        _skill(repo, name="aes-thing")

        result = _gate(repo)

        assert result.returncode == 0, result.stdout
        assert "do not start with 'act-'" in result.stdout

    def test_a_prefixed_skill_draws_no_note(self, tmp_path):
        repo = _scratch_repo(tmp_path, "prefixed", SKILL_PREFIX="act")
        _skill(repo, name="act-thing")

        result = _gate(repo)

        assert result.returncode == 0, result.stdout
        assert "do not start with" not in result.stdout


def test_this_repository_passes_its_own_gate():
    """The tree as committed, which is the rule stated as something that holds.
    It goes red when somebody adds a skill layer and breaks the shape."""
    result = _gate(REPO)

    assert result.returncode == 0, result.stdout
