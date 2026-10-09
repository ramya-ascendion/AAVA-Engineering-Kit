"""`bin/check-no-leaks`, red then green, and never green by accident.

The check once failed open: an allowed token containing `/` broke its `sed`
delimiter, `sed` errored, and every line was treated as clean. The cases below
keep a leak beside the kit's own name in view, which is what exposed it. The
kit is called Aurora Kit, so the bare word is allowed and only the product's
own terms and paths are refused.

This file holds the forbidden words on purpose, as test data, so the scan skips
this one file by name.
"""

from __future__ import annotations

import shutil

import pytest

from hook_harness import BARE_PATH, REPO, _run, posix


@pytest.fixture
def tree(tmp_path):
    (tmp_path / "bin").mkdir()
    shutil.copyfile(REPO / "bin" / "check-no-leaks", tmp_path / "bin" / "check-no-leaks")
    (tmp_path / "docs").mkdir()
    return tmp_path


def _check(tree, text):
    (tree / "docs" / "note.md").write_text(text, encoding="utf-8", newline="\n")
    return _run(
        f'bash "{posix(tree)}/bin/check-no-leaks" ',
        cwd=tree,
        env={"PATH": BARE_PATH},
    )


def test_a_clean_tree_passes(tree):
    assert _check(tree, "A plain sentence about a web service.\n").returncode == 0


def test_a_domain_word_is_refused_with_its_line(tree):
    result = _check(tree, "see Verity here\n")

    assert result.returncode == 1
    assert "note.md:1" in result.stdout


def test_a_leak_beside_the_kits_own_name_is_still_refused(tree):
    assert _check(tree, "Aurora Kit and Verity\n").returncode == 1
    assert _check(tree, "use the Verity thing with Aurora Kit\n").returncode == 1


def test_the_kits_own_name_alone_passes(tree):
    assert _check(tree, "Aurora Kit installs into a project\n").returncode == 0


def test_a_path_that_only_exists_in_the_product_is_refused(tree):
    assert _check(tree, "imports from src/aurora/domain\n").returncode == 1
    assert _check(tree, "activate aurora-venv first\n").returncode == 1


def test_a_ticket_key_is_refused(tree):
    assert _check(tree, "tracked in AUR-123\n").returncode == 1
