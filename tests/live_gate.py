"""The live suite's gate: which tests need a real environment, and why they skip.

Not a test file. A "live" test is one that reaches something real — a running
service, a real model, a real database — and is quick when that thing is there
and close to unbounded when it is not. The defect is never the duration. It is
that committing would depend on state that has nothing to do with the commit,
with no signal saying which world you are in. So live tests are kept out of the
commit gate and run on purpose.

This module is used from the places that must agree, so they read one answer:

* `tests/conftest.py`, which adds `--live` and marks the suite. pytest reads
  `pytest_addoption` only from the root conftest of the test tree, which is why
  the gate lives up here rather than beside the tests it gates.
* Any hook or script that wants to ask the same question first.

## Two rules, and the reason each is written this way

**Membership is a directory, never a list.** A test is live because of where it
sits: under `tests/integration/`. A list of filenames here would be the thing
that stops being true the first time somebody adds a test, and the symptom
would be a commit that quietly costs a quarter of an hour again.

**A skip says what to do.** These are the only tests that touch the real thing.
A suite that skips without saying why is a suite nobody runs.

## Making it yours

Nothing here knows what "standing" means for a project. A project that wants a
probe (is the service up, does the model answer) adds it where it fits and
reports through `PROBE_EXIT`; the three answers a probe may give are named below
so a script and a test read the same words.
"""

from __future__ import annotations

from pathlib import Path

TESTS = Path(__file__).resolve().parent
LIVE_SUITE = TESTS / "integration"
REPO = TESTS.parent

# What a skipped live test says. One sentence, ending in what to run.
NOT_ASKED = (
    "live test: it needs a real environment, so it is skipped unless asked "
    "for. Run it deliberately with: pytest tests/integration --live -ra"
)

# What a probe of the environment may answer, written once. A probe that exits
# with one of these lets a caller tell "switched off" from "never set up" from
# "set up wrong" from "the probe itself broke".
PROBE_EXIT = {
    "standing": 0,
    "absent": 1,
    "unconfigured": 2,
    "broken": 3,
    "misconfigured": 4,
}


def is_live(path: Path) -> bool:
    """True when a test file sits under the live suite's directory."""
    try:
        Path(path).resolve().relative_to(LIVE_SUITE)
    except ValueError:
        return False
    return True
