# Coverage and CRAP: the two bars a branch clears before its pull request

Two measurements gate a branch, taken after `/code-review` is clean and before
the pull-request question is asked. A third check may run in the same block and
is [`guarantees.md`](guarantees.md)'s, if the project turned it on; these two are
here.

**The bars come from `.kit/config.env`.** `KIT_PACKAGE_DIR` names the code that is
measured, `KIT_COVERAGE_BAR` the line-coverage floor, `KIT_CRAP_BAR` the CRAP
ceiling, and `KIT_TEST_DIRS` the suites that are run to measure them. This page
says `<package>` for the first and uses the shipped defaults (75 and 30) only
as examples. Read the config, not this page, for the numbers a project holds.

- **Line coverage of `<package>` is at least `KIT_COVERAGE_BAR` percent.** Under
  the bar, write unit tests until it is over.
- **Every function in `<package>` scores under `KIT_CRAP_BAR` on CRAP.** Over the
  bar, simplify the code, or add the function to `tools/crap-exempt` with a
  reason.

Both are measured across the whole package, not only the files the branch
touched. A branch inherits the bar the same way it inherits the test suite.

**A package's own tests are not measured**, even when they sit inside the
package directory. The coverage config in `pyproject.toml` drops them, and
`tools/crap.py` drops the same directories. Keep the two lists in step, and say
in the config why, so the two cannot disagree.

## Take the measurement

```bash
coverage run --source=<package> -m pytest --quiet -ra <test dirs>
python tools/crap.py
```

The first command runs the same suites the commit gate runs, with counting
turned on. It runs them one test at a time on purpose: `coverage` does not
follow `pytest-xdist`'s worker processes without more setup, and a commit gate
using `-n auto` would hand back an empty measurement. The second reads what it
wrote, asks `radon` for the complexity of every function, and prints both bars
with a pass or fail.

Add `--all` to see every function worst-first rather than only the failures.

## Three exit codes, and they mean different things

| Code | Meaning |
| --- | --- |
| `0` | Both bars were measured and passed. |
| `1` | Both bars were measured, and one failed. Fix the code. |
| `2` | Nothing was measured. Fix the input, then run it again. |

**A `2` is never a reason to look at the code.** The output says what was wrong
and prints the command that fixes it. A bad command line exits `2` as well, for
the same reason: nothing was measured.

`1` means a measurement came back and a bar failed, and nothing else. An
unexpected crash exits `2`, so a defect in the gate can never be mistaken for a
defect in the code it was grading.

## What it refuses to score

The gate stops rather than guessing. Four things end a run before any score is
printed:

- **`coverage` or `radon` is not on the path.** Almost always an environment
  nobody activated.
- **There is no coverage data.** Take the measurement first.
- **The data is older than what it was collected from.** Any file under
  `<package>` *or* the test directories counts. A measurement taken before a
  test was written describes a suite nobody ran, and it is wrong in the
  flattering direction when that test is the one covering the gap.
- **A file under `<package>` is in no coverage report at all.** Zero is the
  honest number for a module nothing imports, and it is also what a
  half-finished measurement looks like. Those cannot be told apart from here,
  so neither is scored.

There is no flag to skip any of this. Re-measuring is a couple of minutes and
it is the only thing that makes the numbers true.

## Why staleness is worth stopping for

Old data rarely announces itself by dropping a function. It reports **wrong
percentages that look plausible**, because `coverage json` rebuilds each
function's line range from the source in front of it while the recorded line
numbers still point at the old shape.

Insert forty lines at the top of a module and re-run the report without
re-measuring, and a fully covered function can come back at a fraction of its
real coverage, with its CRAP score several times too high. Nothing on screen
looks odd. That is the failure this refusal exists to prevent, and it is worse
than a plain failure, because a red gate at least gets read.

## What CRAP measures

CRAP is one number per function, built from complexity and coverage together:

```
CRAP = complexity^2 * (1 - coverage)^3 + complexity
```

**Read what the formula does before arguing with a score.** At full coverage the
first term is zero and CRAP is just the complexity. So a bar of 30 is a hard
complexity bar of 30 for any well-tested function, and no amount of extra
testing moves it. At zero coverage the same function scores its complexity
squared plus its complexity. Only the middle of the range is about testing at
all.

That is the point of one score instead of two. A simple function is allowed to
be thinly tested, because little can hide in it. A complex one is not.
Complexity here is cyclomatic complexity (the number of independent paths
through a function) as `radon` counts it.

Classes are not scored. `radon` reports a class as a block whose complexity is
the sum of its methods', so scoring it counts every method a second time and
blames the class for the total. CRAP is a per-method score.

## The exemption list

`tools/crap-exempt` names functions that are out of the analysis. They are not
scored, and they are not listed among the failures. The run says how many were
left out, and `--all` names them.

An entry needs a reason that outlives the score, and the reason lives in the
file above the entry. A function belongs there only when a decision already made
says it stays the shape it is. Not because simplifying it is awkward, and never
because a number is inconvenient. If the reason is not already written down
somewhere else, it is not a reason yet.

## When a fix changes code

Fixing either bar is a code change, and a code change has not been reviewed.
So the branch goes back around: `/code-review`, then coverage, then CRAP,
until a full pass changes nothing. Only then does the pull-request question get
asked.

## Where this is enforced

`/aes-work-the-path` runs both checks between `/aes-implement` and its
pull-request gate, alongside the guarantee check when the project uses one. The
commit and push hooks do not. They run what is fast and needs nothing standing,
and a coverage run over the whole suite is neither. If the project wants it
enforced in CI, add a job that runs the two commands above.
