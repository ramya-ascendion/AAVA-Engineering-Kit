"""The document-structure gate, and the tree it exists to hold.

`tools/doc_structure.py` asks four questions about the agent documentation:
is every `docs/agents/*.md` reachable from `AGENTS.md`, does every Markdown
link between them land, does every path the two registries name exist, and
does every entry claiming `deterministic` name the gate that decides it.
The rule is `docs/agents/writing-a-rule.md`, and the reason it is a script
rather than a paragraph is that none of the four needs judgment.

Two different questions here, and they fail in different ways. The first group
asks whether the gate can tell a broken tree from an intact one — a gate that
refuses everything gets switched off, and a gate that refuses nothing is not a
gate. The last asks whether this repo's own tree is actually clean, which is
the kind of check that stays true rather than being true once.

**One test guards a false positive rather than a miss.** The first draft of the
gate treated any backticked `*.md` as a pointer, and `docs/agents/design-handoff.md`
calls `docs/design/design-project-github.md` "github.md" throughout. A
nickname in prose is not a broken link, and a gate that says it is trains
people to ignore it.

The gate runs as a subprocess with a working directory, the way the commit
hook calls it, rather than by importing it — the paths it reads are relative
to where it runs, and a test that imported it would prove something else.

They start no server and reach no network.
"""

from __future__ import annotations

import sys
import textwrap

from hook_harness import REPO, _run_gate

GATE = REPO / "tools" / "doc_structure.py"


def _gate(cwd):
    """Run the gate against a tree and hand back the completed process."""
    return _run_gate(["python", str(GATE)], cwd)


def _tree(root, agents_md, docs, registries=None):
    """Write a minimal repo-shaped tree the gate can read.

    `docs` maps a file name under `docs/agents/` to its contents. `registries`
    maps a file name under `tools/` to its contents, defaulting to one empty
    registry of each name so the third check has something to find.
    """
    root.mkdir(parents=True)
    (root / "AGENTS.md").write_text(textwrap.dedent(agents_md), encoding="utf-8")
    agent_docs = root / "docs" / "agents"
    agent_docs.mkdir(parents=True)
    for name, contents in docs.items():
        (agent_docs / name).write_text(textwrap.dedent(contents), encoding="utf-8")
    tools = root / "tools"
    tools.mkdir()
    for name, contents in (
        registries
        or {"document_types.yaml": "types: []\n", "issue_types.yaml": "types: []\n"}
    ).items():
        (tools / name).write_text(textwrap.dedent(contents), encoding="utf-8")
    return root


class TestTheGateAcceptsAnIntactTree:
    """A gate that refuses a correct tree is a gate somebody turns off."""

    def test_a_doc_named_in_backticks_counts_as_a_pointer(self, tmp_path):
        tree = _tree(
            tmp_path / "backticks",
            "# Repo\n\nThe rule is `docs/agents/only.md`.\n",
            {"only.md": "# Only\n\nA rule.\n"},
        )
        result = _gate(tree)
        assert result.returncode == 0, (
            "a doc named in backticks is how most of AGENTS.md points at its "
            f"leaves, and it was read as unreachable: {result.stdout!r}"
        )

    def test_a_doc_reached_through_another_doc_counts(self, tmp_path):
        tree = _tree(
            tmp_path / "transitive",
            "# Repo\n\nThe tracker is `docs/agents/index.md`.\n",
            {
                "index.md": "# Index\n\nThe states are [states.md](states.md).\n",
                "states.md": "# States\n\nA rule.\n",
            },
        )
        result = _gate(tree)
        assert result.returncode == 0, (
            "an index file is the whole point of the split, so reachability "
            f"has to follow pointers through one: {result.stdout!r}"
        )

    def test_a_backticked_nickname_is_not_a_broken_link(self, tmp_path):
        tree = _tree(
            tmp_path / "nickname",
            "# Repo\n\nThe rule is `docs/agents/only.md`.\n",
            {"only.md": "# Only\n\nIt is generated to `github.md`, which is prose.\n"},
        )
        result = _gate(tree)
        assert result.returncode == 0, (
            "a backticked name in prose is a nickname, not a link, and calling "
            f"it broken trains people to ignore the gate: {result.stdout!r}"
        )


class TestTheGateRefusesABrokenTree:
    """Each question fails on its own, and says which file is wrong."""

    def test_a_doc_nothing_points_at_is_refused(self, tmp_path):
        tree = _tree(
            tmp_path / "orphan",
            "# Repo\n\nThe rule is `docs/agents/only.md`.\n",
            {"only.md": "# Only\n\nA rule.\n", "stranded.md": "# Stranded\n"},
        )
        result = _gate(tree)
        assert result.returncode == 1
        assert "stranded.md" in result.stdout
        assert "only.md" not in result.stdout.split("FAILED")[1].split("ok")[0]

    def test_a_link_that_lands_nowhere_is_refused(self, tmp_path):
        tree = _tree(
            tmp_path / "broken-link",
            "# Repo\n\nThe rule is `docs/agents/only.md`.\n",
            {"only.md": "# Only\n\nSee [the gone one](gone.md).\n"},
        )
        result = _gate(tree)
        assert result.returncode == 1
        assert "gone.md" in result.stdout

    def test_a_registry_naming_a_missing_file_is_refused(self, tmp_path):
        tree = _tree(
            tmp_path / "bad-registry",
            "# Repo\n\nThe rule is `docs/agents/only.md`.\n",
            {"only.md": "# Only\n\nA rule.\n"},
            registries={
                "document_types.yaml": """\
                    types:
                      - type: invented
                        rule: docs/agents/never-written.md
                    """,
                "issue_types.yaml": "types: []\n",
            },
        )
        result = _gate(tree)
        assert result.returncode == 1
        assert "never-written.md" in result.stdout

    def test_a_template_that_was_never_written_is_refused(self, tmp_path):
        """The failure the templates exist to prevent, made impossible.

        `document-types.md` promised `docs/agents/document-templates/` for two
        commits before the directory existed. Prose naming a directory is not
        something this gate reads, so the registry has to name each template.
        """
        tree = _tree(
            tmp_path / "missing-template",
            "# Repo\n\nThe rule is `docs/agents/only.md`.\n",
            {"only.md": "# Only\n\nA rule.\n"},
            registries={
                "document_types.yaml": """\
                    types:
                      - type: invented
                        template: docs/agents/document-templates/never-written.md
                    """,
                "issue_types.yaml": "types: []\n",
            },
        )
        result = _gate(tree)
        assert result.returncode == 1
        assert "never-written.md" in result.stdout

    def test_a_deterministic_entry_with_no_gate_is_refused(self, tmp_path):
        """An enforcement claim that nothing runs.

        `requirements` shipped as `deterministic` with no `gate:`, so the
        registry said a script decided it and no script did. Naming a gate
        that does not exist was already caught; claiming one and naming
        nothing was the hole next to it.
        """
        tree = _tree(
            tmp_path / "ungated-deterministic",
            "# Repo\n\nThe rule is `docs/agents/only.md`.\n",
            {"only.md": "# Only\n\nA rule.\n"},
            registries={
                "document_types.yaml": """\
                    types:
                      - type: invented
                        enforcement: deterministic
                    """,
                "issue_types.yaml": "types: []\n",
            },
        )
        result = _gate(tree)
        assert result.returncode == 1
        assert "names no gate" in result.stdout

    def test_a_hybrid_entry_with_no_gate_is_accepted(self, tmp_path):
        """The false alarm next door.

        `hybrid` and `inferred` both end in a person's judgment, which is why
        they are not scripts. Demanding a gate from them would refuse most of
        the registry.
        """
        tree = _tree(
            tmp_path / "ungated-hybrid",
            "# Repo\n\nThe rule is `docs/agents/only.md`.\n",
            {"only.md": "# Only\n\nA rule.\n"},
            registries={
                "document_types.yaml": """\
                    types:
                      - type: invented
                        enforcement: hybrid
                    """,
                "issue_types.yaml": "types: []\n",
            },
        )
        result = _gate(tree)
        assert result.returncode == 0, (
            "hybrid ends in a person's judgment and needs no gate, and "
            f"refusing it would refuse most of the registry: {result.stdout!r}"
        )

    def test_a_missing_registry_is_refused(self, tmp_path):
        tree = _tree(
            tmp_path / "no-registry",
            "# Repo\n\nThe rule is `docs/agents/only.md`.\n",
            {"only.md": "# Only\n\nA rule.\n"},
            registries={"issue_types.yaml": "types: []\n"},
        )
        result = _gate(tree)
        assert result.returncode == 1
        assert "document_types.yaml" in result.stdout


class TestThisRepoIsClean:
    """The acceptance criterion, written as something that stays true.

    The tests above prove the gate works on a tree built to be wrong. This one
    asks the question the gate exists for, of the tree it protects — and it is
    the half that catches a document somebody adds next month and forgets to
    point at.
    """

    def test_every_agent_doc_is_reachable_and_every_pointer_lands(self):
        result = _gate(REPO)
        assert result.returncode == 0, (
            "this repo's own agent documentation does not hang together:\n"
            f"{result.stdout}"
        )


def _typed_tree(root, doc, registry, local=None):
    """A tree with one doc under `docs/` and a registry that may or may not claim it."""
    tree = _tree(
        root,
        "# Repo\n",
        {},
        registries={"document_types.yaml": registry, "issue_types.yaml": "types: []\n"},
    )
    target = tree / doc
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# A doc\n", encoding="utf-8")
    if local is not None:
        (tree / "tools" / "document_types.local.yaml").write_text(
            textwrap.dedent(local), encoding="utf-8"
        )
    return tree


def _typed_gate(tree):
    return _run_gate([sys.executable, str(GATE)], tree)


CLAIMS_SPECS = """    types:
      - type: specification
        paths: [docs/superpowers/specs/**/*.md]
    forbidden_paths:
      - path: docs/*.md
        because: The root of docs/ is a drawer.
    """


class TestEveryDocBelongsToAType:
    """`paths:` in the registry used to be read by nobody."""

    def test_a_doc_in_a_claimed_folder_passes(self, tmp_path):
        tree = _typed_tree(
            tmp_path / "ok", "docs/superpowers/specs/phases/x.md", CLAIMS_SPECS
        )
        assert _typed_gate(tree).returncode == 0

    def test_a_doc_in_a_folder_no_type_claims_is_refused(self, tmp_path):
        tree = _typed_tree(tmp_path / "untyped", "docs/notes/x.md", CLAIMS_SPECS)
        result = _typed_gate(tree)
        assert result.returncode == 1
        assert "docs/notes/x.md" in result.stdout
        assert "matches no document type" in result.stdout

    def test_a_forbidden_path_is_refused_and_says_why(self, tmp_path):
        tree = _typed_tree(tmp_path / "forbidden", "docs/TRACKER.md", CLAIMS_SPECS)
        result = _typed_gate(tree)
        assert result.returncode == 1
        assert "docs/TRACKER.md" in result.stdout
        assert "drawer" in result.stdout

    def test_a_forbidden_path_can_be_allowed_by_name(self, tmp_path):
        tree = _typed_tree(
            tmp_path / "allowed",
            "docs/TRACKER.md",
            CLAIMS_SPECS,
            local="allowed_paths: [docs/TRACKER.md]\n",
        )
        assert _typed_gate(tree).returncode == 0

    def test_a_project_type_in_the_local_registry_claims_a_folder(self, tmp_path):
        tree = _typed_tree(
            tmp_path / "local",
            "docs/compliance/x.md",
            CLAIMS_SPECS,
            local="types:\n  - type: compliance\n    paths: [docs/compliance/*.md]\n",
        )
        assert _typed_gate(tree).returncode == 0

    def test_a_single_star_does_not_cross_a_folder(self, tmp_path):
        tree = _typed_tree(
            tmp_path / "shallow",
            "docs/research/deep/x.md",
            "types:\n  - type: r\n    paths: [docs/research/*.md]\n",
        )
        assert _typed_gate(tree).returncode == 1
