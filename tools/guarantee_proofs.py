"""Running one proof: a pytest subprocess in the temp tree, read from its junit file.

Its own module because `tools/guarantees.py` reached its line cap. `run_tests` is the
only thing that starts a pytest subprocess, which is what lets the tool's own
tests stub it.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from xml.etree import ElementTree

from kit_config import load


class Ran:
    """What one pytest run reported, read from its junit file.

    Junit rather than the text summary because the summary's shape is a
    presentation detail: `-rA` and `-rf` print headings, `--durations` prints a
    thresholded selection, and both have been reworded across releases. The XML
    carries `<failure>` and `<skipped>` as distinct elements and the message
    `fails_with` matches on.
    """

    def __init__(self, code: int, outcomes: Dict[str, Tuple[str, str]]) -> None:
        self.code = code
        # node id -> (element name, message)
        self.outcomes = outcomes

    def matching(self, listed: str) -> List[str]:
        """Every node id this run reported for one listed id.

        A parametrized proof expands: `…_hangs` becomes `…_hangs[None]` and two
        more. Both spellings count, so an entry may name the function without
        naming each parameter.
        """
        return [
            found
            for found in self.outcomes
            if found == listed or found.startswith(f"{listed}[")
        ]


def _node_ids(report: Path) -> Dict[str, Tuple[str, str]]:
    """Rebuild each test's node id from a junit `xunit1` testcase.

    **`xunit1` is not optional.** The default family writes only `classname` and
    `name`, and `classname` is a dotted string a path cannot be recovered from,
    so a listed node id would have nothing to match against. `xunit1` keeps
    `file`.

    The classname is split on `.` rather than sliced: a module-level test has an
    empty tail, and joining it whole yields `test_x.py::::test_y`, which matches
    nothing. A nested class needs the same split.
    """
    outcomes: Dict[str, Tuple[str, str]] = {}
    # The report is the one `run_tests` just had pytest write into a temp file,
    # so nothing untrusted reaches this parser.
    # nosemgrep: python.lang.security.use-defused-xml-parse.use-defused-xml-parse
    for case in ElementTree.parse(report).getroot().iter("testcase"):
        filename = case.get("file")
        if filename is None:
            continue
        # pytest writes the path in the platform's own separators, and a node id
        # is spelled with forward slashes everywhere.
        filename = filename.replace("\\", "/")
        module = Path(filename).with_suffix("").as_posix().split("/")
        named = [part for part in (case.get("classname") or "").split(".") if part]
        # `classname` is the dotted module path with any enclosing classes after
        # it, so the module is a *prefix* to drop — not a suffix to match. A
        # module-level test leaves nothing behind, which is the case that makes
        # the difference between `test_x.py::test_y` and `test_x.py::::test_y`.
        tail = named[len(module) :] if named[: len(module)] == module else named
        nodeid = "::".join([filename, *tail, case.get("name") or ""])

        element, message = "passed", ""
        for kind in ("failure", "error", "skipped"):
            found = case.find(kind)
            if found is not None:
                element, message = kind, found.get("message") or ""
                break
        outcomes[nodeid] = (element, message)
    return outcomes


def _clean_env(tree: Path) -> Dict[str, str]:
    """The environment a proof runs in.

    `PYTHONPATH` is **replaced**, not extended: `activate_venv` exports the main
    checkout's package root before any gate runs, and an inherited copy of it
    would let pytest import the unmutated package while this tool edits a copy
    nobody reads. Every `COVERAGE_*` variable goes, because the venv's
    `a1_coverage.pth` arms subprocess coverage on two of them and the data would
    describe a tree about to be deleted. Every `GIT_*` variable goes too: a hook
    exports `GIT_DIR`, and a proof that shells out to git in a scratch repository
    would otherwise act on the real one.
    """
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("COVERAGE_", "GIT_"))
    }
    # The directory the package imports from: `src` for `src/pkg`, the tree
    # itself for a package at the root.
    package_dir = Path(load()["KIT_PACKAGE_DIR"])
    environment["PYTHONPATH"] = str(tree / package_dir.parent)
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    return environment


def run_tests(tree: Path, ids: Sequence[str], timeout: int) -> Optional[Ran]:
    """Run the named tests inside the temp tree. None when nothing came back.

    The only thing in this module that starts a subprocess, which is what lets
    the tool's own tests stub it and pay for pytest a handful of times rather
    than thirty-two.

    `sys.executable -m pytest` rather than a bare `pytest`, so the interpreter is
    the one running this tool and not whatever the PATH happens to hold.
    """
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as handle:
        report = Path(handle.name)

    try:
        finished = subprocess.run(
            [
                sys.executable,
                "-m",
                "pytest",
                *ids,
                "--quiet",
                "--color=no",
                "-p",
                "no:cacheprovider",
                "-o",
                "junit_family=xunit1",
                f"--junit-xml={report}",
            ],
            cwd=tree,
            env=_clean_env(tree),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return None
    finally:
        try:
            outcomes = _node_ids(report) if report.stat().st_size else {}
        except ElementTree.ParseError:
            # A report cut short says nothing, and nothing is what `_judge`
            # reads as `broken`: no test ran for a listed id.
            outcomes = {}
        finally:
            report.unlink(missing_ok=True)

    return Ran(finished.returncode, outcomes)
