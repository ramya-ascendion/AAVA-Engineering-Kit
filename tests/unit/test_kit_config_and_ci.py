"""The shared config, the live gate, the CI workflow, and the no-leak guard.

Small things that hold the rest together: every gate reads `.kit/config.env`
through one parser, CI and the kit's copy of the workflow must not drift, and no
gate machinery may name a project.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "tests"))

import kit_config  # noqa: E402  pylint: disable=wrong-import-position
import live_gate  # noqa: E402  pylint: disable=wrong-import-position


class TestKitConfig:
    def test_a_missing_file_gives_the_defaults(self, tmp_path):
        assert kit_config.load(tmp_path) == kit_config.DEFAULTS

    def test_values_override_in_any_quoting(self, tmp_path):
        (tmp_path / ".kit").mkdir()
        (tmp_path / ".kit" / "config.env").write_text(
            'KIT_STACK="node"\nKIT_TEST_CMD=\'node --test\'\n'
            "KIT_COVERAGE_BAR=60  # trailing comment\n# KIT_CRAP_BAR=99\n"
        )
        loaded = kit_config.load(tmp_path)
        assert loaded["KIT_STACK"] == "node"
        assert loaded["KIT_TEST_CMD"] == "node --test"
        assert loaded["KIT_COVERAGE_BAR"] == "60"
        assert loaded["KIT_CRAP_BAR"] == kit_config.DEFAULTS["KIT_CRAP_BAR"]

    def test_every_key_in_the_example_is_a_known_default(self):
        example = (REPO / ".kit" / "config.env.example").read_text()
        keys = set(re.findall(r"^(KIT_[A-Z_]+)=", example, re.M))
        assert keys == set(kit_config.DEFAULTS)

    @pytest.mark.parametrize(
        "stack, cmd, expected",
        [
            ("none", "", ""),
            ("node", "", ""),
            ("node", "node --test", "node --test"),
            ("python", "", "python -m pytest tests/unit -q"),
            ("python", "make test", "make test"),
        ],
    )
    def test_the_effective_test_command(self, stack, cmd, expected):
        settings = {**kit_config.DEFAULTS, "KIT_STACK": stack, "KIT_TEST_CMD": cmd}
        assert kit_config.test_command(settings) == expected

    def test_the_source_root_is_the_packages_parent(self, tmp_path):
        settings = {**kit_config.DEFAULTS, "KIT_PACKAGE_DIR": "src/thing"}
        assert kit_config.source_root(settings, tmp_path) == tmp_path / "src"

    def test_the_bash_defaults_match_the_python_ones(self):
        """Two readers of one file must agree about what a missing key means."""
        shell = (REPO / ".git-hooks" / "common.sh").read_text()
        for key, value in kit_config.DEFAULTS.items():
            match = re.search(rf': "\$\{{{key}:=([^}}]*)\}}"', shell)
            assert match, f"common.sh gives {key} no default"
            assert match.group(1) == value, key


class TestLiveGate:
    def test_a_file_under_integration_is_live(self):
        assert live_gate.is_live(live_gate.LIVE_SUITE / "test_x.py")

    def test_a_unit_test_is_not(self):
        assert not live_gate.is_live(live_gate.TESTS / "unit" / "test_x.py")

    def test_the_skip_reason_says_what_to_run(self):
        assert "--live" in live_gate.NOT_ASKED


class TestTheWorkflow:
    def test_the_kits_copy_and_the_installed_copy_are_identical(self):
        kit = (REPO / "ci" / "gates.yml").read_bytes()
        installed = (REPO / ".github" / "workflows" / "gates.yml").read_bytes()
        assert kit == installed

    def test_every_action_is_pinned_to_a_commit(self):
        for workflow in (REPO / ".github" / "workflows").glob("*.yml"):
            for use in re.findall(r"uses: (\S+)", workflow.read_text()):
                assert re.search(r"@[0-9a-f]{40}$", use), f"{workflow.name}: {use}"

    def test_an_unusable_base_falls_back_and_never_skips(self):
        text = (REPO / "ci" / "gates.yml").read_text()
        assert "falling back to the merge base" in text
        assert "git merge-base origin/main HEAD" in text

    def test_the_commit_hook_and_ci_read_the_same_file_types(self):
        hook = (REPO / ".git-hooks" / "pre-commit").read_text()
        ci = (REPO / "ci" / "gates.yml").read_text()
        extensions = set(re.findall(r"'(\*\.[a-z.]+)'", ci.split("diff-filter")[1]))
        for extension in extensions:
            assert extension in hook, f"CI reads {extension}, the hook does not"

    def test_it_says_why_a_hook_alone_is_not_a_gate(self):
        assert "--no-verify" in (REPO / "ci" / "gates.yml").read_text()


class TestNoProjectNamesInTheGateMachinery:
    """The kit is for projects that are not the one it was copied from."""

    # Built from pieces so this file does not contain what it forbids.
    WORDS = [
        "src/au" + "rora",
        "au" + "rora-venv",
        "AU" + "R-[0-9]",
        "atlas" + "sian",
        "so" + "nic",
        "ver" + "ity",
        "tempo" + "ral",
        "test" + "bed",
        "font" + "awesome",
    ]

    def test_no_gate_file_names_one(self):
        pattern = re.compile("|".join(self.WORDS), re.I)
        roots = [".git-hooks", "tools", "tests", "ci", ".github", "offline", ".claude"]
        files = [REPO / "setup-dev-env.sh", REPO / "pyproject.toml", REPO / ".gitignore"]
        for root in roots:
            files += [p for p in (REPO / root).rglob("*") if p.is_file()]
        hits = []
        for path in files:
            # The leak check's own test holds the forbidden words as data, on purpose.
            if "__pycache__" in path.parts or path.suffix == ".txt" or path.name == "test_leak_check.py":
                continue
            # Skill trees hold borrowed third-party skills; bin/check-no-leaks governs them.
            if "skills" in path.parts:
                continue
            for number, line in enumerate(
                path.read_text(encoding="utf-8", errors="replace").splitlines(), 1
            ):
                if pattern.search(line) and "document_types" not in path.name:
                    hits.append(f"{path.relative_to(REPO)}:{number}")
        assert not hits, hits[:10]
