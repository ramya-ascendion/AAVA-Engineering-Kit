#!/usr/bin/env python
#
# The guarantee check. The rule it enforces — what the list holds, what each
# result means, and where it runs — lives in `docs/agents/guarantees.md`, not
# here. The list itself is `tools/guarantees.yaml`.
#
# A docstring that states a guarantee is a claim. This asks the only question
# that makes a claim checkable: **remove the code that keeps it, and do the
# named tests go red?** If they stay green, the guarantee was decoration.
#
# That is mutation testing pointed at claims rather than at branches, and it is
# deliberately narrow. A general mutation tool mutates everything and takes
# hours; this mutates a curated list of guarantees somebody already wrote down,
# one edit each, and takes seconds.
#
# **It measures a commit, never the working tree**, and refuses to run against
# any copy of the project package but the one in its own temp tree. The code that
# carries both is `_prepared` and `_GUARD_CONFTEST` below and `_clean_env` in
# `tools/guarantee_proofs.py`, each with the reason it exists written beside it.
# The package is `KIT_PYTHON_PACKAGE` in `.kit/config.env`.

from __future__ import annotations

import argparse
import ast
import io
import os
import queue
import shutil
import subprocess
import tempfile
import tokenize
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, Iterable, List, NoReturn, Optional, Sequence, Tuple

import yaml

from guarantee_results import (
    BROKEN,
    EXEMPT,
    EXIT,
    PROVED,
    UNPROVED,
    exit_for,
    report,
)
from guarantee_proofs import Ran, run_tests
from kit_config import load
from repo import REPO

SETTINGS = load()
LIST = REPO / "tools" / "guarantees.yaml"

# What an entry gets when it does not ask for its own. Generous enough for a
# unit proof and nowhere near entry 3's wait, which asks in the list.
DEFAULT_TIMEOUT = 60

# How many entries are measured at once, each in a tree of its own. Half the
# cores, because each entry's two pytest runs are a whole interpreter each, and
# at most four, because a measured run gained little past four. The figures are
# in `docs/agents/guarantees.md`, "Keeping it fast".
WORKERS = min(4, (os.cpu_count() or 2) // 2 or 1)

_DEFINITIONS = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)


def refuse(headline: str, *rest: str) -> NoReturn:
    """Say the check could not run, and how to make it run.

    Exits as `broken`, never as `unproved`, for the reason `tools/crap.py`
    gives: a reader who cannot tell a failed bar from a broken environment will
    treat one as the other. `EXIT` in `tools/guarantee_results.py` owns both
    codes.

    Worded FAILED rather than NOT RUN, which is where this departs from
    `tools/crap.py`. `pre-push` refuses a push on this exit, and NOT RUN is the
    word both hooks keep for a check that was not needed — printed
    above a refusal, it would say the opposite of what happened.
    """
    print(f"FAILED — {headline}")
    for line in rest:
        print(line)
    raise SystemExit(EXIT[BROKEN])


# ---------------------------------------------------------------- reading code


def span_of(source: str, symbol: str) -> Optional[Tuple[int, int]]:
    """The first and last line of `symbol`, decorators included.

    **The decorator is why this exists.** `ast` keeps decorators in
    `decorator_list`, outside `ClassDef.lineno`, so a span taken from `lineno`
    alone cannot see `@dataclass(frozen=True)` — which is the guard of the
    ticket's own first acceptance criterion.

    A dotted name is matched on its last part: `Investigation.run` finds `run`.
    `async def` is matched as well as `def`, because `Investigation.run` is one.
    """
    wanted = symbol.split(".")[-1]
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, _DEFINITIONS) and node.name == wanted:
            first = min([node.lineno] + [one.lineno for one in node.decorator_list])
            return first, node.end_lineno or first
    return None


def literal_in_span(path: Path, symbol: str, keyword: str) -> Optional[int]:
    """The integer a keyword argument is called with inside one symbol.

    For a bound an entry borrows rather than owns. Scoped to the symbol because
    the same literal usually appears elsewhere in the same file meaning
    something else — AGENTS.md's "a value defined in code is owned by the code",
    applied to a number a list would otherwise hand-copy.
    """
    source = path.read_text()
    span = span_of(source, symbol)
    if span is None:
        return None

    first, last = span
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.keyword) or node.arg != keyword:
            continue
        value = node.value
        if isinstance(value, ast.Constant) and isinstance(value.value, int):
            if first <= value.lineno <= last:
                return value.value
    return None


def parameters_of(path: Path, test: str) -> int:
    """How many times pytest will run one test, from its `parametrize` marker.

    An entry whose proof waits a fixed number of seconds waits it once per
    parameter, so this is the multiplier its `timeout_seconds` has to clear.
    Counted from the decorator rather than from anything the entry says: a
    seventh case added to `wrong_shape` changes what the proof costs, and a
    number hand-copied into the list would not notice.

    One case of a parametrized test, `test_it[2]`, runs once.
    """
    if test.endswith("]"):
        return 1
    for node in ast.walk(ast.parse(path.read_text())):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != test:
            continue
        runs = 1
        for decorator in node.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if "parametrize" not in ast.unparse(decorator.func):
                continue
            # Stacked markers multiply rather than replace: two of three cases
            # is nine runs, and a bound sized for three would kill the
            # subprocess and report `broken` with nothing wrong.
            # The cases are the *last* list argument. `parametrize` takes the
            # argnames first, and a two-name marker spells them as a tuple —
            # counting that would measure the names, not the runs.
            cases = [
                one for one in decorator.args if isinstance(one, (ast.List, ast.Tuple))
            ]
            if cases:
                runs *= len(cases[-1].elts)
        return runs
    return 1


def _prose_in_span(source: str, span: Tuple[int, int], wanted: str) -> bool:
    """Whether the occurrence of `wanted` in the span begins inside prose.

    A guard is code. Matched inside a docstring or a comment it would be mutated
    as prose, the tests would not move, and the entry would report `unproved` —
    a guarantee accused of being decoration because the tool edited a sentence
    about it. `evidence.py`'s frozen guarantee is a sentence *about*
    `frozen=True`, so this is one rewording away from mattering.

    Asked of where the match **starts**, not of what it contains. A guard may
    hold a string of its own — `raise ValueError("refused")` is a guard like any
    other — so anything that blanked the literals out first would lose the guard
    it was looking for.
    """
    first, last = span
    lines = source.splitlines(keepends=True)
    before = sum(len(line) for line in lines[: first - 1])
    within = "".join(lines[first - 1 : last])

    found = within.find(wanted)
    if found < 0:
        return False

    at = before + found
    row = source.count("\n", 0, at) + 1
    column = at - (source.rfind("\n", 0, at) + 1)

    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type not in (tokenize.COMMENT, tokenize.STRING):
            continue
        if token.start <= (row, column) < token.end:
            return True
    return False


def _defined_as(path_in_file: str) -> Tuple[str, ...]:
    """The test a node id names, case cut off first: `[a::b]` can hold `::`."""
    return tuple(path_in_file.split("[", 1)[0].split("::"))


def _definitions_in(source: str) -> List[Tuple[str, ...]]:
    """Every test a module defines, as the path a node id spells.

    A class-based test is `("TestThing", "test_it")` and a module-level one is
    `("test_it",)`. Built by walking the tree rather than by matching text, so a
    name that survives only in a comment does not count as a test that exists.
    """
    found: List[Tuple[str, ...]] = []

    def walk(node: ast.AST, prefix: Tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.ClassDef):
                walk(child, prefix + (child.name,))
            elif isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                found.append(prefix + (child.name,))

    walk(ast.parse(source), ())
    return found


def _marked_xfail(source: str, wanted: Tuple[str, ...]) -> bool:
    """Whether the named test carries an `xfail` marker.

    A proof may not. `strict=True` turns an unexpected pass into a failing line
    while writing `<skipped>` to the junit file, which is a red run that reads
    as proved through one door and as broken through the other.

    If any case carries `xfail`, a proof naming any case of that test is
    refused. That errs toward refusing: name a test with no `xfail` instead.
    """
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != wanted[-1]:
            continue
        if any("xfail" in ast.unparse(one) for one in node.decorator_list):
            return True
    return False


# ------------------------------------------------------------- reading the list


def load(path: Path = LIST) -> List[Dict]:
    """The list, as written. Raises rather than guessing if it will not parse."""
    held = yaml.safe_load(path.read_text())
    return list(held or [])


def is_exempt(entry: Dict) -> bool:
    """An entry is excused exactly when it gives a reason and names no guard.

    One discriminator, so every other field rule can key off it rather than each
    inventing its own idea of what an excused entry looks like.
    """
    return "reason" in entry and "guard" not in entry


def _check_quotation(entry: Dict, repo: Path) -> List[str]:
    """Whether the guarantee and the guard are still where the entry says."""
    path = repo / entry["file"]
    if not path.is_file():
        return [f"{entry['file']} does not exist"]

    source = path.read_text()
    span = span_of(source, entry["symbol"])
    if span is None:
        return [f"{entry['symbol']} is not defined in {entry['file']} any more"]

    first, last = span
    within = "\n".join(source.splitlines()[first - 1 : last])

    problems = []
    for field in ("guarantee", "guard"):
        if field not in entry:
            continue
        seen = within.count(entry[field])
        if seen != 1:
            problems.append(
                f"{field} appears {seen} times inside {entry['symbol']}, not once: "
                f"{entry[field]!r}"
            )

    if "guard" in entry and _prose_in_span(source, span, entry["guard"]):
        problems.append(
            f"guard matches only inside a comment or a string in "
            f"{entry['symbol']}, so removing it would edit prose: "
            f"{entry['guard']!r}"
        )

    if any(entry["guarantee"] in line for line in source.splitlines()) is False:
        problems.append(
            "guarantee is not on one source line — a quote that wraps can never "
            f"match: {entry['guarantee']!r}"
        )
    return problems


def _check_proofs(entry: Dict, repo: Path) -> List[str]:
    """Whether every named test still exists, and may still be used as a proof."""
    problems = []
    for nodeid in entry.get("tests", ()):
        filename, _, path_in_file = nodeid.partition("::")
        module = repo / filename
        if not module.is_file():
            problems.append(f"{filename} does not exist, named by {nodeid}")
            continue

        source = module.read_text()
        wanted = _defined_as(path_in_file)
        if wanted not in _definitions_in(source):
            problems.append(f"no such test: {nodeid}")
            continue

        if _marked_xfail(source, wanted):
            problems.append(
                f"{nodeid} carries an xfail marker, so a red run there cannot be "
                "read as a proof"
            )
    return problems


def _check_shape(entry: Dict) -> List[str]:
    """Whether the entry holds the fields its own kind of entry has to hold."""
    if is_exempt(entry):
        wrong = [f for f in ("replaced_by", "tests", "fails_with") if f in entry]
        if wrong:
            return [f"an excused entry cannot carry {', '.join(sorted(wrong))}"]
        return [] if str(entry.get("reason", "")).strip() else ["reason is empty"]

    problems = []
    for field in ("guard", "replaced_by", "removes", "fails_with", "tests"):
        if field not in entry or not str(entry[field]).strip():
            problems.append(f"{field} is missing or empty")

    # **A short `fails_with` matches everything.** It is a prefix, so `""` makes
    # the check vacuous and `"a"` nearly so — and the entry then reports
    # `proved` for a red run it never looked at. Six characters is enough for
    # `assert`, which is the shortest thing any real proof reports.
    spellings = entry.get("fails_with", "")
    for one in [spellings] if isinstance(spellings, str) else spellings:
        if len(str(one).strip()) < 6:
            problems.append(
                f"fails_with {one!r} is too short to discriminate — it would "
                "match almost any failure, so the entry would report `proved` "
                "without looking at what went red"
            )
    return problems


def check(entry: Dict, repo: Path = REPO) -> List[str]:
    """Every static fault in one entry, named. An empty list is a clean entry.

    Shared with `tests/unit/test_guarantees_list.py` on purpose: the commit gate
    and the tool ask the same question of the list, and two copies of it would
    answer differently the first time one was edited.
    """
    for required in ("guarantee", "file", "symbol"):
        if required not in entry:
            return [f"{required} is missing"]

    problems = _check_shape(entry)
    problems += _check_quotation(entry, repo)
    if not is_exempt(entry):
        problems += _check_proofs(entry, repo)
    return problems


# ------------------------------------------------------------------ the verdict


def _matches(message: str, expected) -> bool:
    """Whether a failure message begins with any spelling the entry allows.

    A list, because one failure can be spelled more than one way — which
    spellings and why is `docs/agents/guarantees.md`. Every parameter has to
    match a member; no member has to be matched, or an entry whose members are
    two interpreters' spellings of one message would be `broken` on both.
    """
    allowed = [expected] if isinstance(expected, str) else list(expected)
    return any(message.startswith(one) for one in allowed)


def _judge(entry: Dict, before: Optional[Ran], after: Optional[Ran]) -> Tuple[str, str]:
    """The result for one entry, from its two runs. Never guesses.

    **A bare non-zero exit is not success.** pytest exits 2 on a collection
    error, 4 on a bad node id and 5 on nothing collected — so a mutation that
    stops the module importing would report every guarantee in that file as
    proved, which is the un-failable test this tool exists to find, rebuilt
    inside the tool. `proved` needs exit 1 *and* a `<failure>` on every id the
    baseline matched *and* a message the entry predicted.
    """
    listed = list(entry["tests"])
    if before is None:
        return BROKEN, "the unmutated run was killed by its own timeout"
    if before.code == 4:
        return BROKEN, "pytest exited 4: an unknown node id, or a usage error"
    if before.code != 0:
        return BROKEN, f"the tests do not pass unmutated (pytest exited {before.code})"

    expected: List[str] = []
    for one in listed:
        found = before.matching(one)
        if not found:
            return BROKEN, f"no test ran for {one}"
        for nodeid in found:
            element, _ = before.outcomes[nodeid]
            if element != "passed":
                return BROKEN, f"{nodeid} was {element} unmutated, so it proves nothing"
        expected.extend(found)

    if after is None:
        return BROKEN, "the mutated run was killed by its own timeout"
    if after.code == 0:
        return UNPROVED, "the guard was removed and every test stayed green"
    if after.code != 1:
        return BROKEN, f"the mutated run exited {after.code}, so nothing was measured"

    for nodeid in expected:
        element, message = after.outcomes.get(nodeid, ("missing", ""))
        if element != "failure":
            return BROKEN, f"{nodeid} was {element} when mutated, not a failure"
        if not _matches(message, entry["fails_with"]):
            return BROKEN, (
                f"{nodeid} failed with {message.splitlines()[0]!r}, which is not "
                f"what the entry predicts ({entry['fails_with']!r})"
            )
    return PROVED, ""


def _mutated(source: str, entry: Dict) -> Optional[str]:
    """The file with the guard removed, or None when the edit does not hold.

    **Scoped to the symbol's span.** `@dataclass(frozen=True)` appears three
    times in `evidence.py`; a whole-file replace would unfreeze two other
    classes and the entry would be measuring them too. Exactly one substitution
    is asserted, because a zero-substitution no-op reads as `unproved` — a
    guarantee accused of being decoration by a tool that never touched it.
    """
    span = span_of(source, entry["symbol"])
    if span is None:
        return None

    first, last = span
    lines = source.splitlines(keepends=True)
    within = "".join(lines[first - 1 : last])
    if within.count(entry["guard"]) != 1:
        return None

    lines[first - 1 : last] = [within.replace(entry["guard"], entry["replaced_by"])]
    rewritten = "".join(lines)
    try:
        ast.parse(rewritten)
    except SyntaxError:
        return None

    # Nothing outside the symbol can have moved: the replace runs on the span's
    # own text and the slice assignment puts it back between an untouched prefix
    # and an untouched suffix. A guard that also appears in another function is
    # therefore left alone there, which `test_nothing_outside_the_symbol_moves`
    # holds this construction to.
    return rewritten


# The temp tree refuses to collect unless the project package resolves inside it. Written
# into the archive rather than asserted afterwards, because it has to run in the
# process that imports the module under test — anywhere else it is a proxy for
# the question rather than the question.
#
# Both sides are resolved: macOS hands out `/var/folders/...`, a symlink to
# `/private/var/folders/...`, and comparing one spelling against the other would
# make every entry `broken` on this platform and nowhere else.
_GUARD_CONFTEST = '''"""Refuse to run against any copy of the package but the one in this tree."""

from pathlib import Path

import __PACKAGE__ as _package

_here = Path(__file__).resolve().parent
_found = Path(_package.__file__).resolve()

if _here not in _found.parents:
    raise RuntimeError(
        f"__PACKAGE__ was imported from {_found}, which is outside {_here}. "
        "The mutation under test is not what these tests are running against, "
        "so every result would be a lie."
    )
'''


def _prepared(ref: str, tree: Path) -> None:
    """Lay the commit out in `tree`, plus the two things git cannot carry."""
    archive = subprocess.run(
        ["git", "archive", "--format=tar", ref],
        cwd=REPO,
        capture_output=True,
        check=False,
    )
    if archive.returncode != 0:
        refuse(
            f"git could not archive {ref!r}.",
            archive.stderr.decode(errors="replace").strip(),
        )
    subprocess.run(["tar", "-x", "-C", str(tree)], input=archive.stdout, check=True)

    # No package in this commit means nothing to guard: the entries then test
    # something that does not import it, and the guard would refuse them all.
    package = SETTINGS["KIT_PYTHON_PACKAGE"]
    if (tree / SETTINGS["KIT_PACKAGE_DIR"]).is_dir():
        conftest = tree / "conftest.py"
        conftest.write_text(
            (conftest.read_text() + "\n\n" if conftest.exists() else "")
            + _GUARD_CONFTEST.replace("__PACKAGE__", package)
        )


def measure(
    tree: Path, entries: Iterable[Dict], workers: int = WORKERS
) -> List[Tuple[Dict, str, str]]:
    """Every entry's result, against a tree already laid out, in list order.

    The seam `git archive` calls, and the one the tool's own tests drive: no
    test here builds a throwaway git repository to ask what a verdict is.

    **No two entries share a mutated file.** Up to `workers` entries run at
    once, each in a tree of its own: `tree` itself, and a copy of it for every
    worker after the first. An entry mutates and restores its file only in the
    tree it was handed. An entry that waits on real time says so with its own
    `timeout_seconds`, and a timeout is `broken`.

    Each result is printed as it is known, in the order entries finish.

    **A failure stops the run rather than waiting it out.** When one entry
    raises, or the run is interrupted, entries not yet started are canceled and
    only the ones already running are waited for, so no copy is removed while a
    worker is still using it. A second interrupt during that wait skips it, and
    what that can leave behind is a temp tree, never a file in the checkout.
    """
    entries = list(entries)
    results: Dict[int, Tuple[Dict, str, str]] = {}
    pooled = list(range(len(entries)))
    alone: List[int] = []

    def record(at: int, result: str, why: str) -> None:
        results[at] = (entries[at], result, why)
        report(entries[at], result, why)

    copies: List[Path] = []
    free: "queue.Queue[Path]" = queue.Queue()
    free.put(tree)
    try:
        for _ in range(min(workers, len(pooled)) - 1):
            copies.append(
                Path(tempfile.mkdtemp(prefix="kit-guarantees-worker-")).resolve()
            )
            shutil.copytree(tree, copies[-1], symlinks=True, dirs_exist_ok=True)
            free.put(copies[-1])

        def measured(at: int) -> Tuple[int, str, str]:
            own = free.get()
            try:
                return (at, *_measure_one(own, entries[at]))
            finally:
                free.put(own)

        pool = ThreadPoolExecutor(max_workers=len(copies) + 1)
        try:
            for done in as_completed([pool.submit(measured, at) for at in pooled]):
                record(*done.result())
        finally:
            pool.shutdown(wait=True, cancel_futures=True)

        for at in alone:
            record(at, *_measure_one(tree, entries[at]))
    finally:
        for copy in copies:
            shutil.rmtree(copy, ignore_errors=True)

    # Every entry is pooled or alone, and a failure has already raised, so a
    # missing result is a bug here and fails loudly rather than being dropped.
    return [results[at] for at in range(len(entries))]


def _measure_one(tree: Path, entry: Dict) -> Tuple[str, str]:
    """One entry, in the tree it was handed, restored before that tree is reused."""
    if is_exempt(entry):
        return EXEMPT, entry["reason"]

    faults = check(entry, tree)
    if faults:
        return BROKEN, faults[0]

    path = tree / entry["file"]
    original = path.read_text()
    timeout = entry.get("timeout_seconds", DEFAULT_TIMEOUT)
    listed = list(entry["tests"])

    try:
        before = run_tests(tree, listed, timeout)
        rewritten = _mutated(original, entry)
        if rewritten is None:
            return BROKEN, "the guard could not be removed without breaking the file"
        path.write_text(rewritten)
        after = run_tests(tree, listed, timeout)
    finally:
        path.write_text(original)

    return _judge(entry, before, after)


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", default="HEAD", help="the commit to measure")
    asked = parser.parse_args(argv)

    named = subprocess.run(
        ["git", "log", "-1", "--format=%h %s", asked.ref],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    print(f"measuring {asked.ref} — {named.stdout.strip()}")

    dirty = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    ).stdout.split("\n")
    differing = len([one for one in dirty if one.strip()])
    if differing:
        print(
            f"the working tree was not measured; {differing} files differ from "
            "this commit"
        )

    tree = Path(tempfile.mkdtemp(prefix="kit-guarantees-")).resolve()
    try:
        _prepared(asked.ref, tree)
        listed = tree / LIST.relative_to(REPO)
        if not listed.exists():
            refuse(
                f"{asked.ref} has no {LIST.relative_to(REPO)}, so there is nothing to measure."
            )
        entries = load(listed)
        if not entries:
            # An empty list measures nothing and would exit as a pass — one that
            # checked nothing, from a commit that emptied the list.
            refuse(
                f"{asked.ref}'s {LIST.relative_to(REPO)} is empty, so nothing was measured."
            )
        return exit_for(measure(tree, entries))
    except Exception as unexpected:  # pylint: disable=broad-exception-caught
        # Uncaught, Python's exit is the code `EXIT` gives `unproved`. A tool that broke has
        # measured nothing, so it says so and exits as `broken`, as
        # `tools/crap.py` does.
        print(f"FAILED — {type(unexpected).__name__}: {unexpected}")
        return EXIT[BROKEN]
    finally:
        shutil.rmtree(tree, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
