"""What a run of a skill loads, in characters and in estimated tokens.

A skill split into companion files is worth its pointers only if some runs skip
a step, and "some runs skip a step" is a claim about size. This prints the size,
so the claim is checkable rather than remembered.

**Why it exists at all.** The first figures for the `aes-work-the-path` split
were worked out by hand and written into a pull request body. A later commit
moved one companion back into the `SKILL.md` and every figure went stale at
once, with no way to tell because no one could reproduce them. A number nothing
recomputes is a number that was true once.

Name the skill directory and the files one run reads, in the order it reads
them:

    python tools/skill_load.py .agents/skills/aes-work-the-path \\
        SKILL.md quality-bars.md review-route.md

**The token figure is an estimate, and the comparison is the point.** It is
characters divided by `CHARS_PER_TOKEN`, which is the usual rule of thumb for
English prose and is what the original hand figures used. No tokenizer here
matches the one a harness actually runs, so the absolute number is approximate
in a way the difference between two runs is not — both sides of a comparison
are wrong by the same ratio, and the ratio is what a split is judged on.

Exits non-zero when a named file is missing, so a path list that has gone stale
fails rather than quietly measuring less.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Characters per token, for English prose. Stated once here so every figure this
# prints moves together if it is ever revised.
CHARS_PER_TOKEN = 4


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__.strip().splitlines()[0])
        print("usage: skill_load.py <skill-directory> <file> [<file> ...]")
        return 2

    root = Path(argv[1])
    total = 0
    missing = []

    for name in argv[2:]:
        path = root / name
        if not path.is_file():
            missing.append(str(path))
            continue
        size = len(path.read_text(encoding="utf-8"))
        total += size
        print(f"  {name:24} {size:6} chars  {size // CHARS_PER_TOKEN:6} tok")

    for gone in missing:
        print(f"  MISSING {gone}")

    print(f"  {'total':24} {total:6} chars  {total // CHARS_PER_TOKEN:6} tok")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
