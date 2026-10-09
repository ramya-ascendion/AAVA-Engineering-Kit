"""Reads `.kit/config.env`, the one place per-project settings live.

The file is shell-sourceable, so hooks `source` it and Python tools call
`load()`. Both read the same keys. A missing key falls back to the default
below, and a missing file is not an error: the kit then runs on defaults.
"""
from __future__ import annotations

import re
from pathlib import Path

from repo import REPO

DEFAULTS = {
    "KIT_PROJECT_NAME": "project",
    "KIT_PACKAGE_DIR": "src/app",
    "KIT_PYTHON_PACKAGE": "app",
    "KIT_VENV_DIR": ".venv",
    "KIT_TICKET_PREFIX": "PROJ",
    "KIT_SKILL_PREFIX": "aes",
    "KIT_SPELLING_LOCALE": "american",
    "KIT_TRACKER": "github",
    "KIT_DEFAULT_BRANCH": "main",
    "KIT_SKILL_LAYOUT": "link",
    "KIT_PROTECT_BRANCHES": "no",
    "KIT_PROTECTED_BRANCHES": "",
    "KIT_COVERAGE_BAR": "75",
    "KIT_CRAP_BAR": "30",
    "KIT_TEST_DIRS": "tests/unit",
    # node | python | none. Decides which language gates run; secrets,
    # document-structure, skill-mirror and spelling run for every stack.
    "KIT_STACK": "none",
    # Shell command a commit runs when the staged change could affect a test.
    # Empty means: python -> `python -m pytest <KIT_TEST_DIRS> -q`, else NOT RUN.
    "KIT_TEST_CMD": "",
    # Optional extra lint command, whole tree, any stack. Empty means none.
    "KIT_LINT_CMD": "",
}

_LINE = re.compile(r'^\s*([A-Z][A-Z0-9_]*)=(?:"([^"]*)"|\'([^\']*)\'|(\S*))\s*(?:#.*)?$')


def load(root: Path = REPO) -> dict[str, str]:
    """Return the settings, defaults filled in for anything the file omits."""
    settings = dict(DEFAULTS)
    path = root / ".kit" / "config.env"
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            match = _LINE.match(line)
            if match:
                key = match.group(1)
                settings[key] = next(g for g in match.groups()[1:] if g is not None)
    return settings


def test_command(settings: dict[str, str]) -> str:
    """The command a commit runs for tests, or "" when none is configured."""
    if settings["KIT_TEST_CMD"].strip():
        return settings["KIT_TEST_CMD"].strip()
    if settings["KIT_STACK"] == "python":
        return f"python -m pytest {settings['KIT_TEST_DIRS']} -q"
    return ""


def package_dir(settings: dict[str, str], root: Path = REPO) -> Path:
    """Absolute path of the package the Python gates measure."""
    return root / settings["KIT_PACKAGE_DIR"]


def source_root(settings: dict[str, str], root: Path = REPO) -> Path:
    """The directory that must be on `sys.path` for the package to import.

    `src/my_project` is imported from `src`; a package at the repo root is
    imported from the root itself.
    """
    return package_dir(settings, root).parent


if __name__ == "__main__":
    # `python tools/kit_config.py KEY` prints one value, for shell callers.
    # `--test-cmd` prints the effective test command, defaults applied.
    import sys

    loaded = load()
    for wanted in sys.argv[1:]:
        if wanted == "--test-cmd":
            print(test_command(loaded))
        else:
            print(loaded.get(wanted, ""))
