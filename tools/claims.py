#!/usr/bin/env python
#
# Every bold claim in the package is listed, owed or exempt. The rule is in
# `docs/agents/guarantees.md`, which also says how to answer it; this module
# owns what counts as a claim, because a definition written in prose drifts from
# the one the gate applies.
#
# What is scanned is `KIT_PACKAGE_DIR` in `.kit/config.env`, and an owed claim
# cites a ticket with the project's `KIT_TICKET_PREFIX`.
#
# `tools/guarantees.py` proves the claims on its list. This asks the question
# that list cannot ask of itself: is anything bold that the list has never
# heard of? It only reads. It never mutates code and never starts pytest, so it
# runs in the unit suite on every commit and in CI with nothing but PyYAML.

from __future__ import annotations

import argparse
import ast
import io
import os
import re
import subprocess
import sys
import tokenize
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import yaml

import guarantee_proofs
import guarantees
from kit_config import load
from repo import REPO

SETTINGS = load()

# The directory the scan reads. Tests move it; nothing else should.
SCOPE_ROOT = REPO
SCOPE = SETTINGS["KIT_PACKAGE_DIR"]
OWED = REPO / "tools" / "guarantees-owed.yaml"

# An umbrella ticket every seeded owed entry cites, whose count only falls.
# None means the project seeded none, and the "only falls" rule is off. A
# project that backfills owed claims in one sweep names the umbrella here.
SEEDED_TICKET: Optional[str] = None
# The ticket that built this list. Nothing is owed to it. None means no such
# ticket, and the rule is off.
THIS_TICKET: Optional[str] = None
# A one-word owed text would cover every future copy of itself: "200", "not".
# Two words is the shortest promise the seeding met ("Never up.", "No cause.").
SHORTEST = 2

_BOLD = re.compile(r"\*\*")
# A code span never crosses a line, so a stray backtick cannot hide the bold
# on the lines after it. Only `>>>` and `>` open an example or a quote.
_CODE_SPAN = re.compile(r"(`+)(?:(?!\1)[^\n])+?\1")
_QUOTED = re.compile(r"^[ \t]*(>>>|>)[^\n]*", re.M)
_TICKET = re.compile(re.escape(SETTINGS["KIT_TICKET_PREFIX"]) + r"-\d+\Z")
_OWNERS = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)

# The section of `docs/agents/guarantees.md` the report sends a reader to.
GUIDE_SECTION = '"Every bold claim is accounted for"'


class CannotRead(Exception):
    """A git ref could not be read. Never the same thing as "no file there"."""


@dataclass(frozen=True)
class Owner:
    """A def or class: its lines, decorators included, and its dotted name."""

    first: int
    last: int
    name: str
    node: ast.AST


@dataclass(frozen=True)
class Claim:
    """One bold run: where it starts, the definition around it, what it says."""

    path: str
    line: int
    symbol: str
    text: str


def normalize(text: str) -> str:
    """One line, one space between words, no `**`, so a rewrap is not a reword."""
    return " ".join(text.replace("**", "").split())


# ------------------------------------------------------------- finding claims


def _masked(text: str) -> str:
    """`text` with code spans and example or quoted lines blanked, same length.

    **Only to find where runs start and end.** The claim itself is always read
    from the original, so a code span inside the bold stays in what it says.
    """

    def blank(match: re.Match) -> str:
        return re.sub(r"[^\n]", " ", match.group(0))

    return _QUOTED.sub(blank, _CODE_SPAN.sub(blank, text))


def _runs(text: str) -> Optional[List[Tuple[int, str]]]:
    """Each bold run's offset in `text` and its words. None for an odd count."""
    marks = [one.start() for one in _BOLD.finditer(_masked(text))]
    if len(marks) % 2:
        return None
    pairs = zip(marks[::2], marks[1::2])
    return [(start, normalize(text[start + 2 : end])) for start, end in pairs]


def _owners(tree: ast.Module) -> List[Owner]:
    """Every def and class in the module, nested ones included."""
    found: List[Owner] = []

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            name = prefix
            if isinstance(child, _OWNERS):
                name = f"{prefix}.{child.name}" if prefix else child.name
                first = min([child.lineno] + [d.lineno for d in child.decorator_list])
                found.append(Owner(first, child.end_lineno or first, name, child))
            visit(child, name)

    visit(tree, "")
    return found


def _symbol_at(owners: Sequence[Owner], line: int) -> str:
    """The innermost definition around `line`, or `<module>`."""
    around = [owner for owner in owners if owner.first <= line <= owner.last]
    if not around:
        return "<module>"
    return min(around, key=lambda owner: owner.last - owner.first).name


def _docstrings(tree: ast.Module, owners) -> Iterable[Tuple[int, str, ast.Constant]]:
    """Each docstring's first line, its owner's name, and its string node."""
    named = [(tree, "<module>")] + [(owner.node, owner.name) for owner in owners]
    for node, name in named:
        body = getattr(node, "body", [])
        if not body or not isinstance(body[0], ast.Expr):
            continue
        value = body[0].value
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            yield value.lineno, name, value


def _comment_blocks(source: str) -> Iterable[Tuple[int, str]]:
    """Each run of whole-line comments as one block, `#` and a space removed.

    A trailing comment is a block of its own, because the code before it breaks
    the prose: `x = 1  # **a**` and the comment below it are two thoughts.
    """
    lines = source.splitlines()
    block: List[str] = []
    start = last = 0
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type != tokenize.COMMENT:
            continue
        row, column = token.start
        whole = not lines[row - 1][:column].strip()
        text = re.sub(r"^# ?", "", token.string)
        if block and whole and row == last + 1:
            block.append(text)
        else:
            if block:
                yield start, "\n".join(block)
            block, start = [text], row
            if not whole:
                yield start, text
                block = []
        last = row
    if block:
        yield start, "\n".join(block)


def _claims_in(path: str, source: str) -> Tuple[List[Claim], List[str]]:
    """One module's claims, and a fault for each block with a stray `**`."""
    tree = ast.parse(source)
    owners = _owners(tree)
    lines = source.splitlines(keepends=True)
    blocks: List[Tuple[int, str, str]] = []

    for first, name, node in _docstrings(tree, owners):
        # The raw source, not the parsed value: entries quote the source, and an
        # escape in the value would shift every line count after it.
        raw = "".join(lines[first - 1 : node.end_lineno])[node.col_offset :]
        blocks.append((first, name, raw))
    for first, text in _comment_blocks(source):
        blocks.append((first, _symbol_at(owners, first), text))

    claims: List[Claim] = []
    faults: List[str] = []
    for first, name, text in blocks:
        runs = _runs(text)
        if runs is None:
            faults.append(
                f"{path}:{first}  {name}: an odd number of `**`, so a run would pair "
                "with the wrong partner. Close the run, or put a literal `**` in a "
                "code span."
            )
            continue
        for offset, words in runs:
            line = first + text.count("\n", 0, offset)
            claims.append(Claim(path, line, name, words))
    return sorted(claims, key=lambda one: one.line), faults


def in_scope(path: str) -> bool:
    """A Python module under `the package directory` that is not a test."""
    parts = Path(path).parts
    return (
        path.startswith(SCOPE + "/") and path.endswith(".py") and "tests" not in parts
    )


def scan_sources(sources: Dict[str, str]) -> Tuple[List[Claim], List[str]]:
    """Every claim in `{path: source}`, sorted by path and line, plus faults."""
    claims: List[Claim] = []
    faults: List[str] = []
    for path in sorted(sources):
        if not in_scope(path):
            continue
        found, broken = _claims_in(path, sources[path])
        claims += found
        faults += broken
    return claims, faults


def sources_under(root: Path) -> Dict[str, str]:
    """Every in-scope module under `root`, keyed by its path from `root`."""
    return {
        one.relative_to(root).as_posix(): one.read_text()
        for one in (root / SCOPE).rglob("*.py")
        if in_scope(one.relative_to(root).as_posix())
    }


# ------------------------------------------------------ what accounts for one


def unaccounted(claims: Iterable[Claim], entries, owed) -> List[Claim]:
    """Claims no list entry and no owed line names, by whole normalized text.

    Whole text, never a substring: a short entry inside a long claim would cover
    a claim nobody decided about. Exempt entries are list entries, so they count.
    """
    covered = {normalize(one.get("guarantee", "")) for one in entries}
    covered |= {normalize(one.get("claim", "")) for one in owed}
    return sorted(
        (one for one in claims if one.text not in covered),
        key=lambda one: (one.path, one.line),
    )


def stale(claims: Iterable[Claim], owed) -> List[Dict]:
    """Owed lines whose text is no longer claimed anywhere."""
    present = {one.text for one in claims}
    return [one for one in owed if normalize(one.get("claim", "")) not in present]


def owed_under(claims: Iterable[Claim], owed, where: str) -> List[Tuple[Claim, str]]:
    """Every place an owed claim is bold under `where`, with the ticket it is
    owed to, sorted by file and line.

    Owed lines hold only the text, so they are joined to the scan the way
    `stale` joins them. A text bold in two places is listed at both, so a
    batch can choose which place to prove.
    """
    tickets: Dict[str, List[str]] = {}
    for one in owed:
        tickets.setdefault(normalize(one.get("claim", "")), []).append(
            str(one.get("see", ""))
        )
    folder = where.rstrip("/") + "/" if where else ""
    return sorted(
        (
            (one, ", ".join(sorted(set(tickets[one.text]))))
            for one in claims
            if one.text in tickets
            and (one.path == where or one.path.startswith(folder))
        ),
        key=lambda pair: (pair[0].path, pair[0].line),
    )


def in_checkout(given: str, root: Path) -> Optional[str]:
    """`given` as a path from `root`, or None when it names nothing there.

    `./`, a trailing slash and an absolute path inside `root` all mean the
    same place. A path that does not exist is refused rather than listed as
    empty, because an empty listing reads as nothing owed.
    """
    if not given.strip():
        return None
    base = root.resolve()
    found = (base / given).resolve()
    if not found.exists() or (found != base and base not in found.parents):
        return None
    return found.relative_to(base).as_posix()


def load_owed(path: Optional[Path] = None) -> List[Dict]:
    """The owed list, or empty when there is none yet."""
    path = path or OWED
    if not path.is_file():
        return []
    return yaml.safe_load(path.read_text()) or []


def check_owed(entry: Dict) -> List[str]:
    """Every fault in one owed entry, named. Empty is a clean entry."""
    faults = [f"{field} is missing" for field in ("claim", "see") if field not in entry]
    if faults:
        return faults
    if not _TICKET.match(str(entry["see"])):
        faults.append(f"see is not a ticket key: {entry['see']!r}")
    elif THIS_TICKET and entry["see"] == THIS_TICKET:
        faults.append(f"cites {THIS_TICKET}, which built this list and owes nothing")
    if len(normalize(entry["claim"]).split()) < SHORTEST:
        faults.append(
            f"claim is under {SHORTEST} words, so it would cover every future copy "
            f"of itself: {entry['claim']!r}"
        )
    return faults


def seed_grew(before: Optional[List[Dict]], after: List[Dict]) -> List[str]:
    """A fault when the seeded ticket gained entries it did not lose.

    A reworded seeded claim is one out and one in, so it passes. `before` is None
    only when the file did not exist, which is the commit that seeds it.
    """
    if before is None or SEEDED_TICKET is None:
        return []

    def seeded(entries):
        return [
            normalize(one["claim"])
            for one in entries
            if one.get("see") == SEEDED_TICKET
        ]

    was, now = seeded(before), seeded(after)
    added = [one for one in now if one not in set(was)]
    removed = [one for one in was if one not in set(now)]
    if len(added) <= len(removed):
        return []
    return [
        f"{len(added) - len(removed)} new owed claim(s) cite {SEEDED_TICKET}, whose "
        "count only falls. Cite a ticket of the claim's own: "
        + "; ".join(repr(one) for one in added)
    ]


def unbolded(before: Iterable[Claim], after: Iterable[Claim], sources: Dict[str, str]):
    """Claims that lost their bold but whose words are still in the same file.

    The one move the gate cannot block, so CI shows every one to the reviewer.
    """
    still = {(one.path, one.text) for one in after}
    flat = {
        path: normalize(re.sub(r"\n[ \t]*# ?", " ", source))
        for path, source in sources.items()
    }
    return [
        one
        for one in before
        if (one.path, one.text) not in still and one.text in flat.get(one.path, "")
    ]


# ------------------------------------------------------------ reading a ref


def git_env(repo: Path) -> Dict[str, str]:
    """The environment git runs in: the proofs' own, so a hook's `GIT_DIR` stays out."""
    return guarantee_proofs._clean_env(repo)  # pylint: disable=protected-access


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        env=git_env(repo),
        capture_output=True,
        text=True,
        check=False,
    )


def at_ref(ref: str, repo: Path = REPO) -> Optional[List[Dict]]:
    """The owed list as committed at `ref`. None only when the file is not there.

    A ref that does not resolve raises instead: read as "no file", a shallow CI
    checkout would pass as the seeding commit, where anything goes.
    """
    if _git(repo, "rev-parse", "--git-dir").returncode:
        raise CannotRead(f"{repo} is not a git repository, so {ref} cannot be read")
    if _git(repo, "cat-file", "-e", f"{ref}^{{commit}}").returncode:
        raise CannotRead(
            f"{ref} does not resolve in {repo}; fetch it, or pass a base that does"
        )
    shown = _git(repo, "show", f"{ref}:{OWED.relative_to(REPO).as_posix()}")
    if shown.returncode:
        return None
    return yaml.safe_load(shown.stdout) or []


def sources_at(ref: str, repo: Path = REPO) -> Dict[str, str]:
    """Every in-scope module as committed at `ref`."""
    listed = _git(repo, "ls-tree", "-r", "--name-only", ref, "--", SCOPE).stdout.split()
    return {
        path: _git(repo, "show", f"{ref}:{path}").stdout
        for path in listed
        if in_scope(path)
    }


# ----------------------------------------------------------------- reporting


def report(missing: Sequence[Claim], gone: Sequence[Dict]) -> str:
    """What to do about each claim, or an empty string when there is nothing."""
    if not missing and not gone:
        return ""
    out: List[str] = []
    if missing:
        out.append(f"{len(missing)} bold claim(s) in {SCOPE} are not accounted for.")
        path = None
        for one in missing:
            if one.path != path:
                path = one.path
                out += ["", path]
            out.append(f'  {one.line}  {one.symbol}  "{one.text}"')
    if gone:
        out += ["", "Owed lines whose claim is gone (reworded? edit the owed text):"]
        out += [f'  "{one.get("claim")}" ({one.get("see")})' for one in gone]
    out += [
        "",
        f"Bold in a {SCOPE} docstring or comment is a guarantee. For each claim, one of:",
        "  1. A test fails without it: list it in tools/guarantees.yaml. The bold run",
        "     must fit on one source line, so reflow it first if it wraps.",
        '       - guarantee: "**<the claim>**"',
        "         file: / symbol: / guard: / tests:   (see the doc below)",
        "  2. A promise with no proof yet: owe it in tools/guarantees-owed.yaml, citing",
        "     a ticket of its own.",
        '       - claim: "<the claim>"',
        f"         see: {SETTINGS['KIT_TICKET_PREFIX']}-NNN",
        "  3. Not a guarantee: remove the bold, or use *italic* for emphasis.",
        "     Unbolding a real guarantee is flagged in CI for the reviewer.",
        "Pick 1 when the test exists, 2 when it is a promise you mean to keep, 3 otherwise.",
        f"docs/agents/guarantees.md, {GUIDE_SECTION}, says more.",
    ]
    return "\n".join(out)


def _summary(lines: Sequence[str]) -> None:
    """Append to the CI job summary when there is one."""
    target = os.environ.get("GITHUB_STEP_SUMMARY")
    if target:
        with open(target, "a", encoding="utf-8") as summary:
            summary.write("\n".join(lines) + "\n")


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Scan the tree, compare it with both lists, and report what is missing.

    Exits 0 when every claim is accounted for, 1 when not, and 2 when `--base`
    cannot be read.

    With `--owed-under`, only list the owed claims under that path and exit 0,
    or 2 when the path names nothing. It decides nothing, so a batch can be
    planned from it without a gate moving.

    With `--base`, also refuse growth of the seeded ticket and flag unbolding,
    both measured against that commit. CI passes the pull request's base.
    """
    parser = argparse.ArgumentParser(
        description="Fail on any bold claim in the package directory nothing accounts for."
    )
    parser.add_argument("--base", help="the commit to compare the owed list against")
    parser.add_argument(
        "--owed-under",
        metavar="PATH",
        help="only list the owed claims under PATH, one per line, and check nothing",
    )
    args = parser.parse_args(argv)

    sources = sources_under(SCOPE_ROOT)
    claims, faults = scan_sources(sources)
    owed = load_owed()
    if args.owed_under is not None:
        where = in_checkout(args.owed_under, SCOPE_ROOT)
        if where is None:
            print(
                f"FAILED — {args.owed_under!r} is not a file or folder in the repository."
            )
            return 2
        for place, see in owed_under(claims, owed, "" if where == "." else where):
            print(f'{place.path}:{place.line}  {place.symbol}  {see}  "{place.text}"')
        return 0
    for entry in owed:
        faults += [f"owed {entry.get('claim')!r}: {one}" for one in check_owed(entry)]

    warnings: List[str] = []
    if args.base:
        try:
            faults += seed_grew(at_ref(args.base), owed)
            before, _ = scan_sources(sources_at(args.base))
        except CannotRead as refused:
            print(f"FAILED — {refused}")
            return 2
        warnings = [
            f'{one.path}:{one.line}  {one.symbol}  "{one.text}" lost its bold'
            for one in unbolded(before, claims, sources)
        ]

    text = report(unaccounted(claims, guarantees.load(), owed), stale(claims, owed))
    print(f"{len(claims)} bold claims in {SCOPE}, {len(owed)} owed.")
    for one in faults + ([text] if text else []):
        print(one)
    if warnings:
        print(
            "\nWarning, for the reviewer: bold removed from a claim whose words remain."
        )
        print("\n".join(warnings))
        _summary(["### Bold removed from a claim whose words remain", ""] + warnings)
    return 1 if faults or text else 0


if __name__ == "__main__":
    sys.exit(main())
