#!/usr/bin/env python
#
# The coverage and CRAP gate, run by hand and by the work-the-path skill before
# its pull-request gate. The rule it enforces — the two bars, the scope, and the
# exemption list — lives in `docs/agents/coverage-and-crap.md`, not here.
#
# **Configuration** is `.kit/config.env`: `KIT_PACKAGE_DIR` is what is measured,
# `KIT_COVERAGE_BAR` and `KIT_CRAP_BAR` are the two bars, `KIT_TEST_DIRS` is the
# suite the measurement is taken over. Flags override them for one run.
#
# CRAP is one number per function, built from two measurements that are already
# taken separately:
#
#     CRAP = complexity^2 * (1 - coverage)^3 + complexity
#
# Read what that formula does before arguing with a score. At full coverage the
# first term is zero and **CRAP is just the complexity** — so a bar of 30 is a
# hard complexity bar of 30 for any well-tested function, and no amount of extra
# testing moves it. At zero coverage the same function scores complexity^2 plus
# complexity. Only the middle of the range is about testing at all.
#
# Both halves come from tools the dev environment already has. `coverage json` reports
# statements covered per function, keyed `Class.method` for a method and by the
# bare name for a plain function. `radon cc -j` reports complexity per block,
# keyed the same way. That shared key is the whole join — no line arithmetic.
#
# **It refuses rather than guesses.** Coverage data that does not
# describe the code in front of it is not a measurement, and scoring a function
# it does not mention as zero-covered turns stale input into a failing gate —
# which teaches a reader that red means "run it again". The exit codes tell a
# failed bar apart from a check that never ran; `coverage-and-crap.md` lists
# them.

from __future__ import annotations

import argparse
import datetime
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import NoReturn

from kit_config import load

SETTINGS = load()

# What takes the measurement. Printed by every refusal, so a reader never has to
# go and look it up, and kept beside the refusals rather than in each one.
MEASURE = (
    "coverage run --source={source} -m pytest --quiet -ra "
    + SETTINGS["KIT_TEST_DIRS"]
)
SETUP = "./setup-dev-env.sh"

# Classes are skipped on purpose. Radon reports a class as a block whose
# complexity is the sum of its methods', so scoring it counts every method a
# second time and blames the class for the total. CRAP is a per-method score.
SCORED_KINDS = ("function", "method")

# Directories radon does not descend into, which must name the same files
# `[tool.coverage.run]`'s `omit` drops in `pyproject.toml`. Tests that sit
# inside the package are measured by nothing, and that file says why they are
# left out.
#
# **The two lists are one decision and split across two files only because the
# tools are two.** `scored_rows` refuses when radon reports a file coverage
# never mentioned, so excluding a directory here and not there does not measure
# it twice — it stops the gate running at all.
IGNORED_DIRS = "tests"

# Folders under `--source` that hold no project Python. A `node_modules` inside
# the package ships stray `.py` files that `npm ci` writes after any measurement
# and coverage never measures. The staleness check and radon both read this, so
# neither can see the file.
NOT_PROJECT = "node_modules"


def refuse(headline: str, *rest: str) -> NoReturn:
    """Say the check did not run, and how to make it run.

    Exit 2, never 1. `1` is a measurement that came back and failed a bar, and a
    reader who cannot tell those apart will treat a broken environment as bad
    code — or worse, the other way round.
    """
    print(f"NOT RUN — {headline}")
    for line in rest:
        print(line)
    raise SystemExit(2)


def require(tool: str) -> None:
    """A missing tool is a check that cannot run, named as such.

    Named after `require` in the pre-commit hook, and borrows its rule that
    a missing tool must never pass quietly. It departs on the exit code: the
    hook has only "failed" to report, and this has a third answer for a check
    that could not run at all.

    Without it the tool dies on a bare `FileNotFoundError` from `subprocess`,
    which reads as a bug in the gate instead of an environment nobody activated.
    """
    if shutil.which(tool) is None:
        refuse(
            f"{tool} is not on PATH, so nothing was measured.",
            "",
            "The project environment is probably not active:",
            f"    source {SETTINGS['KIT_VENV_DIR']}/bin/activate"
            f"  (Windows: {SETTINGS['KIT_VENV_DIR']}/Scripts/activate)",
            f"If it is missing entirely, build it: {SETUP}",
        )


def crap_score(complexity: int, covered: float) -> float:
    uncovered = 1.0 - covered
    return complexity**2 * uncovered**3 + complexity


def exempt_keys(exempt_file: Path) -> set[str]:
    # One `path::name` per line. Blank lines and `#` lines are ignored, which is
    # what makes the reason for each entry live next to the entry — the same
    # shape as the hooks' `spelling-exempt`.
    if not exempt_file.exists():
        return set()
    keys = set()
    for line in exempt_file.read_text(encoding="utf-8").splitlines():
        entry = line.split("#", 1)[0].strip()
        if entry:
            keys.add(entry)
    return keys


def data_file() -> Path:
    """Where `coverage` keeps what it collected.

    Asked of `coverage` rather than assumed to be `.coverage`, because the path
    is configurable and a hard-coded guess would check the age of a file nobody
    is using.

    **Only `ImportError` falls back.** A missing library is answered by the
    documented default; anything else — a broken `.coveragerc`, an unreadable
    config — is allowed to surface. Swallowing it would send the age check at a
    file nobody wrote, which is the guess this whole file exists to refuse.
    """
    try:
        # Imported here rather than at the top: this is the only place that
        # needs the library itself, and the tool otherwise talks to `coverage`
        # as a command. A top-level import would make an unimportable library
        # break every path, including the refusals that exist to explain it.
        import coverage  # pylint: disable=import-outside-toplevel
    except ImportError:
        return Path(".coverage")
    return Path(coverage.Coverage().config.data_file or ".coverage")


def refuse_if_stale(source: str, tests: str) -> None:
    """Refuse when the collected data is older than what it was collected from.

    **The tests count as well as the source.** A measurement taken before a test
    was written describes a suite nobody ran, and its numbers are as wrong as
    they would be after a change to the code — in the flattering direction, if
    the new test is the one that covers the gap.

    **Not `coverage json`'s `meta.timestamp`** — that records when the *report*
    was generated, which is a moment ago every time and says nothing about the
    data. The mtime of the data file is when the suite actually ran.
    """
    collected = data_file()
    if not collected.exists():
        refuse(
            f"there is no coverage data at {collected}, so nothing was measured.",
            "",
            "Take the measurement:",
            f"    {MEASURE.format(source=source)}",
        )

    watched = [Path(source), Path(tests)]
    files = [
        one
        for where in watched
        for one in where.rglob("*.py")
        if NOT_PROJECT not in one.parts
    ]
    if not files:
        refuse(
            f"neither {source} nor {tests} holds any Python, so there is "
            "nothing to measure.",
            "",
            "Are --source and --tests right?",
        )

    newest = max(files, key=lambda one: one.stat().st_mtime)
    if collected.stat().st_mtime >= newest.stat().st_mtime:
        return

    refuse(
        "the coverage data is older than the code it describes.",
        "",
        f"    {collected} collected {_stamp(collected)}",
        f"    {newest} changed   {_stamp(newest)}",
        "",
        "Take the measurement again:",
        f"    {MEASURE.format(source=source)}",
    )


def _stamp(path: Path) -> str:
    return datetime.datetime.fromtimestamp(path.stat().st_mtime).isoformat(
        timespec="seconds"
    )


def coverage_json(source: str) -> dict:
    # Written to a temporary file rather than read off stdout, because
    # `coverage json` prints its own progress line there on some versions and a
    # parse error would then read as a missing measurement.
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as handle:
        target = Path(handle.name)
    try:
        finished = subprocess.run(
            ["coverage", "json", "--include", f"{source}/*", "-q", "-o", str(target)],
            capture_output=True,
            text=True,
            check=False,
        )
        if finished.returncode != 0:
            refuse(
                "`coverage json` could not read the collected data.",
                "",
                finished.stderr.strip(),
                "",
                "Take the measurement again:",
                f"    {MEASURE.format(source=source)}",
            )
        return json.loads(target.read_text(encoding="utf-8"))
    finally:
        target.unlink(missing_ok=True)


def radon_blocks(source: str) -> dict:
    finished = subprocess.run(
        # Both exclusions: `-i` keeps radon out of the test packages coverage
        # omits, `-e` keeps it out of the client's `node_modules`.
        ["radon", "cc", "-j", "-i", IGNORED_DIRS, "-e", f"*/{NOT_PROJECT}/*", source],
        capture_output=True,
        text=True,
        check=False,
    )
    if finished.returncode != 0:
        refuse(
            "`radon cc` could not read the code.",
            "",
            finished.stderr.strip(),
        )
    return json.loads(finished.stdout)


def coverage_key(block: dict) -> str:
    # The name `coverage json` files this block under. A method is
    # `Class.method` in both tools once radon's `classname` is put back on the
    # front — radon reports the bare name and the class beside it.
    classname = block.get("classname")
    return f"{classname}.{block['name']}" if classname else block["name"]


def flatten(blocks: list, parent_key: str | None = None) -> list:
    # Radon nests an inner function inside its parent's `closures`. Flattened
    # here so a complex closure cannot hide behind a simple outer function.
    #
    # A closure is paired with its *parent's* coverage key, because
    # `coverage json` has no row of its own for an inner function — its
    # statements are counted inside the function that defines it. So a closure
    # is scored on its own complexity and its parent's coverage, which is the
    # closest honest reading available.
    out = []
    for block in blocks:
        own_key = coverage_key(block)
        out.append((block, parent_key or own_key))
        out.extend(flatten(block.get("closures", []), parent_key or own_key))
    return out


def scored_rows(source: str) -> tuple[list, float]:
    """One row per function radon can see, joined to its coverage.

    Anything the join cannot answer is handed to `refuse_on_anomalies`, which
    decides whether to stop. Nothing here scores a guess: a function this
    function cannot pair with a measurement never reaches the bars.
    """
    measured = coverage_json(source)
    complexities = radon_blocks(source)
    reported = measured.get("files", {})

    rows = []
    unparsed = []
    unmatched = []
    unmeasured = []

    for path, blocks in sorted(complexities.items()):
        if not isinstance(blocks, list):
            # Radon reports a file it could not parse as an object holding an
            # error rather than a list of blocks.
            unparsed.append(path)
            continue

        if path not in reported:
            unmeasured.append(path)
            continue

        per_function = reported[path].get("functions", {})
        for block, key in flatten(blocks):
            if block["type"] not in SCORED_KINDS:
                continue
            name = key if key == coverage_key(block) else f"{key} > {block['name']}"
            summary = per_function.get(key, {}).get("summary")
            if summary is None:
                unmatched.append(f"{path}::{name}")
                continue
            covered = summary["percent_covered"] / 100.0
            rows.append(
                (
                    path,
                    name,
                    block["complexity"],
                    covered,
                    crap_score(block["complexity"], covered),
                )
            )

    refuse_on_anomalies(
        source, unparsed=unparsed, unmeasured=unmeasured, unmatched=unmatched
    )
    return rows, measured.get("totals", {}).get("percent_covered", 0.0)


def refuse_on_anomalies(
    source: str, *, unparsed: list, unmeasured: list, unmatched: list
) -> None:
    """Stop on anything the join could not answer, one reason at a time.

    Its own function because `scored_rows` should read as the join and nothing
    else; three refusals inline made it a function that scored, bucketed and
    exited.
    """
    if unparsed:
        refuse(
            f"{len(unparsed)} file(s) could not be parsed, so their complexity "
            "is unknown.",
            "",
            *(f"    {path}" for path in unparsed),
        )

    if unmeasured:
        # **Not scored at zero.** Zero is what a module nothing imports really
        # measures, but it is also what a half-finished measurement looks like —
        # and the two are indistinguishable from here. Scoring them alike is the
        # defect this gate exists to prevent: it failed at 420 on untouched code.
        refuse(
            f"{len(unmeasured)} file(s) are in {source} and in no coverage "
            "report, so nothing in them was measured.",
            "",
            *(f"    {path}" for path in unmeasured),
            "",
            "Either the measurement did not run the whole suite, or nothing "
            "imports these at all. Both are worth knowing; neither is a score.",
            "",
            "Take the measurement again:",
            f"    {MEASURE.format(source=source)}",
        )

    if unmatched:
        refuse(
            f"coverage and radon disagree about {len(unmatched)} function(s), "
            "so neither one can be scored.",
            "",
            *(f"    {one}" for one in unmatched[:10]),
            *(
                [f"    ... and {len(unmatched) - 10} more"]
                if len(unmatched) > 10
                else []
            ),
            "",
            "Their files were measured, so this is not a module nobody imports.",
            "A fresh measurement is the first thing to try:",
            f"    {MEASURE.format(source=source)}",
            "",
            "**This has never been seen.** It could not be provoked, because "
            "`coverage json` rebuilds its function list from the source in "
            "front of it. It is kept because the alternative is scoring an "
            "unmatched function at zero, which is the defect this gate exists "
            "to prevent. Reaching it means the join itself is wrong — report it "
            "rather than working around it.",
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Report line coverage and a CRAP score per function."
    )
    parser.add_argument("--source", default=SETTINGS["KIT_PACKAGE_DIR"])
    parser.add_argument("--bar", type=float, default=float(SETTINGS["KIT_CRAP_BAR"]))
    parser.add_argument(
        "--coverage-bar", type=float, default=float(SETTINGS["KIT_COVERAGE_BAR"])
    )
    parser.add_argument("--exempt", default="tools/crap-exempt")
    parser.add_argument(
        "--all",
        action="store_true",
        help="print every function worst-first, and the exempt ones too",
    )
    parser.add_argument(
        "--tests",
        default="tests",
        help="the suite the measurement was taken over; watched for staleness",
    )
    args = parser.parse_args()

    # In this order on purpose: no tools beats no data beats stale data, and
    # each refusal should name the first thing actually wrong.
    require("coverage")
    require("radon")
    refuse_if_stale(args.source, args.tests)

    rows, total_covered = scored_rows(args.source)
    exempted = exempt_keys(Path(args.exempt))

    # Exempt first, then the bar. A function named in the list is out of the
    # analysis whatever it scores — not merely spared a failure — so it leaves
    # the count as well as the failure list.
    excused = [row for row in rows if f"{row[0]}::{row[1]}" in exempted]
    scored_rows_only = [row for row in rows if f"{row[0]}::{row[1]}" not in exempted]
    over = [row for row in scored_rows_only if row[4] > args.bar]

    def show(label, entries):
        print(f"\n{label}")
        for path, name, complexity, covered, score in sorted(
            entries, key=lambda row: -row[4]
        ):
            print(
                f"  {score:7.1f}  {path}::{name} — complexity {complexity}, "
                f"{covered * 100:.0f}% covered"
            )

    print(
        f"Line coverage of {args.source}: {total_covered:.1f}%  (bar {args.coverage_bar:.0f}%)"
    )
    print(f"Functions scored: {len(scored_rows_only)}  (CRAP bar {args.bar:.0f})")
    if excused:
        print(f"Left out by {args.exempt}: {len(excused)}")

    if args.all:
        show("Every function scored, worst first:", scored_rows_only)
        # Only on request. An exempt function is out of the analysis, so
        # printing it beside the failures every run reads as an open problem.
        if excused:
            show(f"Exempt in {args.exempt}, not scored:", excused)
    if over:
        show(f"Over {args.bar:.0f} — FAILED:", over)

    failed = False
    if total_covered < args.coverage_bar:
        print(
            f"\nFAILED — coverage is {total_covered:.1f}%, under the "
            f"{args.coverage_bar:.0f}% bar. Write unit tests."
        )
        failed = True
    if over:
        print(
            f"\nFAILED — {len(over)} function(s) score over {args.bar:.0f}. "
            "Simplify the code, or add an entry and a reason to "
            f"{args.exempt}."
        )
        failed = True
    if not failed:
        print("\nok — both bars passed.")
    return 1 if failed else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    # `SystemExit` is not an `Exception`, so `refuse`'s exit and `main`'s own
    # return code both pass through here untouched.
    except Exception as unexpected:  # pylint: disable=broad-except
        # **A crash is a check that did not run, not a bar that failed.**
        # Without this the default exit code is 1, which the table in
        # `coverage-and-crap.md` reads as "one bar failed. Fix the code." —
        # sending a reader to look for a defect that is in this tool.
        print(f"NOT RUN — {type(unexpected).__name__}: {unexpected}")
        print("")
        print("That is a defect in the gate itself. Report it.")
        sys.exit(2)
