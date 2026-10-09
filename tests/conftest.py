"""Fixtures and shared constants for the whole suite.

Reach everything here through a fixture, never `from conftest import ...`.
"""

from __future__ import annotations

import pytest

import live_gate  # pylint: disable=wrong-import-order

# ---------------------------------------------------------------------------
# The live gate.
#
# Here rather than in `tests/integration/conftest.py`, where it belongs, because
# pytest reads `pytest_addoption` only from the root conftest of the test tree.
# The decisions themselves are in `tests/live_gate.py`.
# ---------------------------------------------------------------------------


def pytest_addoption(parser):
    """`--live` runs the suite that needs a real environment."""
    parser.addoption(
        "--live",
        action="store_true",
        default=False,
        help=(
            "run the live suite in tests/integration, which reaches real "
            "services. Without this they skip."
        ),
    )


def pytest_collection_modifyitems(config, items):
    """Mark the live suite, and skip it unless it was asked for.

    **Marked by where a test sits, not by a list of files.** A list is the thing
    that stops being true the first time somebody adds a test, and the symptom
    would be the commit gate quietly costing a quarter of an hour again.

    The skip is added here rather than left to a fixture so that it applies to
    every live test including ones that ask for no fixtures at all, and so the
    reason is visible at collection rather than discovered per test.
    """
    asked = config.getoption("--live")
    not_asked = pytest.mark.skip(reason=live_gate.NOT_ASKED)

    for item in items:
        if not live_gate.is_live(item.path):
            continue
        item.add_marker(pytest.mark.live)
        if not asked:
            item.add_marker(not_asked)
