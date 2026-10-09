"""The five results `tools/guarantees.py` gives, and the exit a run ends on.

Its own module because the tool reached its line cap, and because this is the
part a caller reads: `pre-push` ranks the exits in the order `RANK` puts results.
What each result means is `docs/agents/guarantees.md`; what each does to a push
is ADR-0086. `RANK` owns the order and `EXIT` owns each result's exit.
"""

from __future__ import annotations

from typing import Dict, Iterable, Tuple

PROVED, EXEMPT, UNMEASURED, UNPROVED, BROKEN = (
    "proved",
    "exempt",
    "unmeasured",
    "unproved",
    "broken",
)

# **The order is not the exit code's.** `unmeasured` has an exit of its own so a
# caller can tell a fact about the machine apart, but it ranks below `unproved`,
# so a missing server never hides a guarantee nothing defends.
RANK = {PROVED: 0, EXEMPT: 0, UNMEASURED: 1, UNPROVED: 2, BROKEN: 3}
EXIT = {PROVED: 0, EXEMPT: 0, UNMEASURED: 3, UNPROVED: 1, BROKEN: 2}


def exit_for(results: Iterable[Tuple[Dict, str, str]]) -> int:
    """The exit of the worst result by rank — not the largest exit code.

    A result this module does not name raises `KeyError` rather than ranking
    as anything. The caller turns that into a refusal, never a pass.
    """
    worst = max(
        (result for _, result, _ in results), key=RANK.__getitem__, default=PROVED
    )
    return EXIT[worst]


def report(entry: Dict, result: str, why: str) -> None:
    """One result, printed the moment it is known.

    Not held to the end: one entry takes ninety seconds, and a hook that shows
    nothing for that long reads as hung. `flush` because stdout is a pipe under
    a hook, and a pipe is block-buffered. An entry missing its quotation is
    `broken` already, and is still named rather than crashing the report.
    """
    named = entry.get("guarantee", "<an entry with no guarantee>")
    print(
        f"  {result:10} {named}" + (f"\n             {why}" if why else ""), flush=True
    )
