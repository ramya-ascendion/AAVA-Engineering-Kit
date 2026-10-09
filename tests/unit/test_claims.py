"""What `tools/claims.py` counts as a claim, and what it accepts .

Bold in a `src/app` docstring or comment is a guarantee, and the tool fails
on any bold run that is neither listed, owed nor exempt. It is worth no more
than its definition, so most of these cases are about what it must and must not
pick up: a fragment counts, `**kwargs` in a code span does not, a wrapped run is
one claim, and a claim that moved to another file is still the same claim.

**Most cases scan source held in a dictionary**, not files on disk, because the
scan takes `{path: source}` and a case reads better as the source it is about.
The few that need a real repository build one in `tmp_path`.

They start no server and reach no network.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import claims as scanner  # noqa: E402  # pylint: disable=wrong-import-position

SEEDED = "PROJ-495"
THIS = "PROJ-398"


@pytest.fixture(autouse=True)
def _scope_and_tickets(monkeypatch):
    """The tool reads its scope and ticket rules from config; pin them here."""
    monkeypatch.setattr(scanner, "SCOPE", "src/app")
    monkeypatch.setattr(scanner, "SEEDED_TICKET", SEEDED)
    monkeypatch.setattr(scanner, "THIS_TICKET", THIS)


def scanned(source, path="src/app/thing.py"):
    """The claims one module holds, and the faults its scan raised."""
    return scanner.scan_sources({path: textwrap.dedent(source)})


def texts(source):
    """Just the claim texts, for the cases that are only about the definition."""
    claims, _ = scanned(source)
    return [one.text for one in claims]


# ------------------------------------------------------------ what a claim is


def test_a_bold_fragment_is_a_claim():
    """No sentence filter: a fragment can be a guarantee as easily as a sentence."""
    source = '''
    def keep():
        """Recorded and **never acted on**."""
    '''
    assert texts(source) == ["never acted on"]


def test_bold_inside_a_code_span_is_not_a_claim():
    """`**kwargs` is code, not emphasis, so it must never pair with a real run."""
    source = '''
    def keep(**kwargs):
        """Passes `**kwargs` through, and **nothing else is added**."""
    '''
    assert texts(source) == ["nothing else is added"]


def test_a_code_span_inside_the_bold_is_kept_in_the_claim():
    """The span is masked to find the run, never cut out of what the run says.

    Five entries in the list quote bold with a code span inside it; cutting the
    span would make each of them miss its own claim.
    """
    source = '''
    def keep():
        """**Only `tenant_role == "admin"` is an Admin.**"""
    '''
    assert texts(source) == ['Only `tenant_role == "admin"` is an Admin.']


def test_a_doctest_line_and_a_quoted_line_are_not_scanned():
    """`2**31` in an example and bold in a quoted source are not the project's claims."""
    source = '''
    def keep():
        """Sizes.

        >>> 2**31
        2147483648

        > **This is someone else's table.**

        **This one is ours.**
        """
    '''
    assert texts(source) == ["This one is ours."]


def test_a_stray_backtick_hides_nothing_on_the_lines_after_it():
    """A code span is one line long, so a lone backtick cannot mask a paragraph."""
    source = '''
    def keep():
        """A lone ` backtick here.

        **Nothing is ever dropped.**

        Then `a real span`, lines later.
        """
    '''
    assert texts(source) == ["Nothing is ever dropped."]


def test_a_line_starting_with_an_ellipsis_is_still_scanned():
    """Only `>>>` and `>` open an example or a quote; `...` opens a sentence."""
    source = """
    # ... **Every row is kept.**
    """
    assert texts(source) == ["Every row is kept."]


def test_bold_wrapped_across_docstring_lines_is_one_claim():
    """Normalized to one line, so a rewrap never changes what the claim says."""
    source = '''
    def keep():
        """**A stamp of the wrong shape is
        refused, not retried forever.**"""
    '''
    assert texts(source) == [
        "A stamp of the wrong shape is refused, not retried forever."
    ]


def test_bold_wrapped_across_comment_lines_is_one_claim_without_the_hash():
    """Consecutive whole-line comments are one block, and the `#` is not text."""
    source = """
    def keep():
        # **Every secret is read
        # before anything is raised.**
        return 1
    """
    assert texts(source) == ["Every secret is read before anything is raised."]


def test_a_trailing_comment_is_its_own_block():
    """Code between two comments splits them, so they cannot pair across it."""
    source = """
    VALUE = 1  # **one**
    # **two**
    """
    assert texts(source) == ["one", "two"]


def test_an_odd_number_of_markers_is_a_fault_not_a_claim():
    """A stray `**` would pair with the wrong partner and invent a claim."""
    claims, faults = scanned('''
    def keep():
        """**Kept** and ** stray."""
    ''')
    assert not claims
    assert len(faults) == 1
    assert "odd number of `**`" in faults[0]
    assert "src/app/thing.py:3" in faults[0]


# ----------------------------------------------------- where a claim lives


def test_the_symbol_is_the_innermost_definition_or_the_module():
    """The message names where to look: `<module>`, a nested name, a method."""
    source = '''
    """**The module says this.**"""


    class Outer:
        """**The class says this.**"""

        def method(self):
            # **The method's comment says this.**
            def inner():
                """**The nested function says this.**"""
    '''
    claims, _ = scanned(source)
    assert [(one.symbol, one.line) for one in claims] == [
        ("<module>", 2),
        ("Outer", 6),
        ("Outer.method", 9),
        ("Outer.method.inner", 11),
    ]


def test_the_line_is_the_line_the_run_starts_on():
    """Counted in the raw source, so an escape in the docstring cannot shift it."""
    source = '''
    def keep():
        """First line with a \\n escape.

        Plain.

        **Here.**
        """
    '''
    claims, _ = scanned(source)
    assert [one.line for one in claims] == [7]


def test_a_test_module_under_src_app_is_out_of_scope():
    """Tests keep their own style, wherever they sit."""
    claims, _ = scanned('"""**A test says this.**"""', "src/app/x/tests/test_it.py")
    assert not claims


# ------------------------------------------------- what accounts for a claim


LISTED = {"guarantee": "**Uniqueness is guaranteed, not hoped for.**"}


def test_a_listed_claim_is_covered_only_by_its_whole_text():
    """A shorter entry inside a longer claim would cover a claim nobody listed."""
    claims, _ = scanned('''
    def keep():
        """**Uniqueness is guaranteed, not hoped for.** **It sets no timer, ever.**"""
    ''')
    short = {"guarantee": "**It sets no timer**"}
    missing = scanner.unaccounted(claims, [LISTED, short], [])
    assert [one.text for one in missing] == ["It sets no timer, ever."]


def test_a_moved_claim_is_still_covered():
    """Matching ignores location, so moving code re-flags nothing."""
    claims, _ = scanned(
        '"""**Uniqueness is guaranteed, not hoped for.**"""',
        "src/app/moved/elsewhere.py",
    )
    assert scanner.unaccounted(claims, [LISTED], []) == []


def test_an_owed_claim_is_covered_and_a_stale_one_is_reported():
    """An owed line whose text is gone must go, or the list rots by being left."""
    claims, _ = scanned('"""**Nothing is raised here, ever.**"""')
    owed = [
        {"claim": "Nothing is raised here, ever.", "see": "PROJ-1"},
        {"claim": "This text was reworded away.", "see": "PROJ-1"},
    ]
    assert scanner.unaccounted(claims, [], owed) == []
    assert scanner.stale(claims, owed) == [owed[1]]


@pytest.mark.parametrize(
    "entry, fault",
    [
        ({"see": "PROJ-1"}, "claim is missing"),
        ({"claim": "Nothing is raised here."}, "see is missing"),
        (
            {"claim": "Nothing is raised here.", "see": "the backlog"},
            "not a ticket key",
        ),
        ({"claim": "200", "see": "PROJ-1"}, f"under {scanner.SHORTEST} words"),
        ({"claim": "Nothing is raised here.", "see": THIS}, THIS),
    ],
)
def test_a_malformed_owed_entry_is_refused(entry, fault):
    """Each refusal names what is wrong, so the fix is one edit."""
    assert any(fault in one for one in scanner.check_owed(entry))


def test_a_well_formed_owed_entry_is_accepted():
    """The shape the report's snippet teaches is a shape the check accepts."""
    assert (
        scanner.check_owed({"claim": "Nothing is raised here.", "see": "PROJ-7"}) == []
    )


# ------------------------------------------------- the seeded ticket only falls


def owed_under(ticket, *claims):
    """Owed entries citing one ticket, one per claim text."""
    return [{"claim": text, "see": ticket} for text in claims]


def test_nothing_new_joins_the_seeded_ticket():
    """After seeding, a new owed claim cites a ticket of its own."""
    before = owed_under(SEEDED, "One claim here.")
    after = before + owed_under(SEEDED, "A new claim here.")
    faults = scanner.seed_grew(before, after)
    assert faults and "A new claim here." in faults[0]


def test_a_reworded_seeded_entry_is_a_swap_and_passes():
    """Rewording a seeded claim leaves the count where it was."""
    before = owed_under(SEEDED, "One claim here.", "Two claims here.")
    after = owed_under(SEEDED, "One claim here, reworded.", "Two claims here.")
    assert scanner.seed_grew(before, after) == []


def test_proving_a_seeded_entry_passes():
    """The count falling is the whole point."""
    before = owed_under(SEEDED, "One claim here.", "Two claims here.")
    assert scanner.seed_grew(before, before[:1]) == []


def test_a_new_entry_under_its_own_ticket_passes():
    """The seeded ticket is closed to newcomers; the list is not."""
    before = owed_under(SEEDED, "One claim here.")
    after = before + owed_under("PROJ-9", "A new claim here.")
    assert scanner.seed_grew(before, after) == []


def test_with_no_owed_file_before_anything_goes():
    """The commit that writes the file is the seeding commit."""
    assert scanner.seed_grew(None, owed_under(SEEDED, "One claim here.")) == []


# ------------------------------------------------------------ reading a ref


def git(repo, *args):
    """Run git in a scratch repository, with nothing inherited from a hook."""
    subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        env=scanner.git_env(repo),
    )


@pytest.fixture(name="repo")
def a_repo(tmp_path):
    """A scratch repository with one commit that has no owed file."""
    git(tmp_path, "init", "-q")
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    (tmp_path / "README").write_text("x")
    git(tmp_path, "add", "README")
    git(tmp_path, "commit", "-qm", "first")
    return tmp_path


def test_a_ref_with_no_owed_file_reads_as_none(repo):
    """None is the one answer that means seeding."""
    assert scanner.at_ref("HEAD", repo) is None


def test_a_ref_with_an_owed_file_reads_its_entries(repo):
    """The file as committed, not as it sits in the working tree."""
    owed = repo / "tools" / "guarantees-owed.yaml"
    owed.parent.mkdir()
    owed.write_text('- claim: "One claim here."\n  see: PROJ-1\n')
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "owe")
    owed.write_text("")
    assert scanner.at_ref("HEAD", repo) == owed_under("PROJ-1", "One claim here.")


def test_a_ref_that_does_not_resolve_is_refused_not_read_as_seeding(repo):
    """A shallow clone must never pass as the commit where anything goes."""
    with pytest.raises(scanner.CannotRead, match="does not resolve"):
        scanner.at_ref("no-such-ref", repo)


def test_a_directory_that_is_not_a_repository_is_refused(tmp_path):
    """`git archive` trees have no `.git`, and must say so rather than pass."""
    with pytest.raises(scanner.CannotRead, match="not a git repository"):
        scanner.at_ref("HEAD", tmp_path)


def test_a_worktree_is_a_repository(repo, tmp_path):
    """A worktree's `.git` is a file, not a directory, and still counts."""
    other = tmp_path.parent / (tmp_path.name + "-worktree")
    git(repo, "worktree", "add", "-q", str(other))
    assert scanner.at_ref("HEAD", other) is None


# ----------------------------------------------------------- unbolding


def test_a_run_that_lost_its_bold_but_kept_its_text_is_flagged():
    """Unbolding is the one way past the gate; it is shown, never blocked."""
    before, _ = scanned('"""**Nothing is raised here.** **Gone entirely.**"""')
    after = {"src/app/thing.py": '"""Nothing is raised here."""'}
    after_claims, _ = scanner.scan_sources(after)
    flagged = scanner.unbolded(before, after_claims, after)
    assert [one.text for one in flagged] == ["Nothing is raised here."]


def test_a_run_unbolded_across_wrapped_comment_lines_is_flagged():
    """The `#` between wrapped lines must not hide the text it wrapped."""
    before, _ = scanned("# **Every secret is read\n# before anything is raised.**\n")
    after = {
        "src/app/thing.py": "# Every secret is read\n# before anything is raised.\n"
    }
    after_claims, _ = scanner.scan_sources(after)
    assert scanner.unbolded(before, after_claims, after)


# ---------------------------------------------------------------- the report


def test_a_clean_run_reports_nothing():
    """An empty report is how the list test knows it passed."""
    assert scanner.report([], []) == ""


def test_the_report_names_the_claim_and_every_way_out():
    """A newcomer reads this once, so it carries the whole decision."""
    claims, _ = scanned('''
    def keep():
        """**Nothing is raised
        here.**"""
    ''')
    stale = [{"claim": "This text was reworded away.", "see": "PROJ-1"}]
    text = scanner.report(claims, stale)
    assert "src/app/thing.py" in text
    assert '3  keep  "Nothing is raised here."' in text
    assert "tools/guarantees.yaml" in text
    assert "tools/guarantees-owed.yaml" in text
    assert "remove the bold" in text
    assert "one source line" in text
    assert "flagged in CI" in text
    assert "reworded?" in text and "This text was reworded away." in text
    assert "docs/agents/guarantees.md" in text


def test_main_prints_the_owed_count_on_a_pass(tmp_path, capsys, monkeypatch):
    """The debt stays in sight on every run, not only on a red one."""
    (tmp_path / "src" / "app").mkdir(parents=True)
    (tmp_path / "src" / "app" / "thing.py").write_text(
        '"""**Owed here, not proved.**"""\n'
    )
    owed = tmp_path / "owed.yaml"
    owed.write_text('- claim: "Owed here, not proved."\n  see: PROJ-7\n')
    monkeypatch.setattr(scanner, "OWED", owed)
    monkeypatch.setattr(scanner, "SCOPE_ROOT", tmp_path)
    monkeypatch.setattr(scanner.guarantees, "load", lambda: [])

    assert scanner.main([]) == 0
    assert "1 owed" in capsys.readouterr().out


def test_main_fails_naming_an_unaccounted_claim(tmp_path, capsys, monkeypatch):
    """The same report the list test asserts on, from the command CI runs."""
    (tmp_path / "src" / "app").mkdir(parents=True)
    (tmp_path / "src" / "app" / "thing.py").write_text(
        '"""**Nobody listed this one.**"""\n'
    )
    monkeypatch.setattr(scanner, "OWED", tmp_path / "absent.yaml")
    monkeypatch.setattr(scanner, "SCOPE_ROOT", tmp_path)
    monkeypatch.setattr(scanner.guarantees, "load", lambda: [])

    assert scanner.main([]) == 1
    assert "Nobody listed this one." in capsys.readouterr().out


# ------------------------------------------------------ listing what is owed


def _owed_tree(tmp_path, monkeypatch):
    """Two owed claims in two services, one of them bold twice, and one listed."""
    root = tmp_path / "src" / "app" / "services"
    for service in ("intake", "triage"):
        (root / service).mkdir(parents=True)
    (root / "triage" / "later.py").write_text(
        '"""**Owed in triage, not proved.**"""\n\n\n'
        'def again():\n    """**Owed in intake, not proved.**"""\n'
    )
    (root / "intake" / "route.py").write_text(
        '"""**Owed in intake, not proved.**"""\n\n\n'
        'def listed():\n    """**Listed and proved elsewhere.**"""\n'
    )
    owed = tmp_path / "owed.yaml"
    owed.write_text(
        '- claim: "Owed in intake, not proved."\n  see: PROJ-7\n'
        '- claim: "Owed in triage, not proved."\n  see: PROJ-7\n'
    )
    monkeypatch.setattr(scanner, "OWED", owed)
    monkeypatch.setattr(scanner, "SCOPE_ROOT", tmp_path)


def test_the_listing_names_each_owed_place_under_the_path(
    tmp_path, capsys, monkeypatch
):
    """A text bold in two places is listed at both, and a listed claim is not."""
    _owed_tree(tmp_path, monkeypatch)

    assert scanner.main(["--owed-under", "src/app/services/intake"]) == 0
    assert capsys.readouterr().out.splitlines() == [
        "src/app/services/intake/route.py:1  <module>  PROJ-7  "
        '"Owed in intake, not proved."'
    ]


def test_the_listing_is_sorted_by_file_and_line(tmp_path, capsys, monkeypatch):
    _owed_tree(tmp_path, monkeypatch)

    scanner.main(["--owed-under", "src/app/services/"])

    assert [line.split()[0] for line in capsys.readouterr().out.splitlines()] == [
        "src/app/services/intake/route.py:1",
        "src/app/services/triage/later.py:1",
        "src/app/services/triage/later.py:5",
    ]


def test_the_listing_does_not_match_a_folder_by_its_prefix():
    """`services/in` names no folder, so it lists nothing from `intake`."""
    claims = [scanner.Claim("src/app/services/intake/route.py", 1, "f", "Owed.")]

    assert (
        scanner.owed_under(
            claims, [{"claim": "Owed.", "see": "PROJ-7"}], "src/app/services/in"
        )
        == []
    )


def test_the_listing_decides_nothing(tmp_path, capsys, monkeypatch):
    """An unaccounted claim fails the gate, and still leaves the listing at 0."""
    _owed_tree(tmp_path, monkeypatch)
    monkeypatch.setattr(scanner.guarantees, "load", lambda: [])

    assert scanner.main([]) == 1
    capsys.readouterr()

    assert scanner.main(["--owed-under", "src/app"]) == 0
    assert "Listed and proved elsewhere." not in capsys.readouterr().out


def test_a_file_a_dot_slash_and_an_absolute_path_name_the_same_place(
    tmp_path, capsys, monkeypatch
):
    _owed_tree(tmp_path, monkeypatch)
    route = "src/app/services/intake/route.py"

    listings = []
    for spelled in (route, f"./{route}", str(tmp_path / route)):
        assert scanner.main(["--owed-under", spelled]) == 0
        listings.append(capsys.readouterr().out)

    assert listings[0].startswith(f"{route}:1  ")
    assert listings == [listings[0]] * 3


@pytest.mark.parametrize(
    "spelled", ["src/app/servics", "", "   ", "/nowhere/src/app", "..", "/"]
)
def test_a_path_that_names_nothing_is_refused_not_listed_empty(
    spelled, tmp_path, capsys, monkeypatch
):
    """An empty listing reads as nothing owed, so a typo must not produce one."""
    _owed_tree(tmp_path, monkeypatch)

    assert scanner.main(["--owed-under", spelled]) == 2
    assert "is not a file or folder in the repository" in capsys.readouterr().out


def test_the_whole_checkout_lists_every_owed_place(tmp_path, capsys, monkeypatch):
    _owed_tree(tmp_path, monkeypatch)

    assert scanner.main(["--owed-under", "."]) == 0
    assert len(capsys.readouterr().out.splitlines()) == 3


def test_each_place_names_the_ticket_its_claim_is_owed_to():
    """Planning one ticket's batch must not pick up another ticket's debt."""
    claims = [
        scanner.Claim("src/app/b.py", 9, "late", "Owed to the second."),
        scanner.Claim("src/app/a.py", 3, "early", "Owed to the first."),
    ]
    owed = [
        {"claim": "Owed to the first.", "see": "PROJ-1"},
        {"claim": "Owed to the second.", "see": "PROJ-2"},
    ]

    listed = scanner.owed_under(claims, owed, "src/app")

    assert [(one.path, see) for one, see in listed] == [
        ("src/app/a.py", "PROJ-1"),
        ("src/app/b.py", "PROJ-2"),
    ]


def test_a_real_folder_outside_the_checkout_is_refused(tmp_path, capsys, monkeypatch):
    _owed_tree(tmp_path / "checkout", monkeypatch)
    (tmp_path / "elsewhere").mkdir()

    assert scanner.main(["--owed-under", str(tmp_path / "elsewhere")]) == 2
    assert "is not a file or folder in the repository" in capsys.readouterr().out


def test_a_text_owed_to_two_tickets_names_both_once():
    claims = [scanner.Claim("src/app/a.py", 3, "early", "Owed twice over.")]
    owed = [
        {"claim": "Owed twice over.", "see": "PROJ-2"},
        {"claim": "Owed twice over.", "see": "PROJ-1"},
        {"claim": "Owed twice over.", "see": "PROJ-2"},
    ]

    listed = scanner.owed_under(claims, owed, "src/app/")

    assert [see for _, see in listed] == ["PROJ-1, PROJ-2"]
