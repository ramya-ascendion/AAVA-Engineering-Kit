# What must be green before the pull request gate

Read this at "Three more checks" in `SKILL.md`, after `/aes-implement` has
finished and before Gate 1. Nothing earlier in the loop needs it.

**The bars themselves are `docs/agents/coverage-and-crap.md` and
`docs/agents/guarantees.md`.** This file says when they run, in what order, and
what to do when one of them will not settle. The numbers come from
`.kit/config.env` (`KIT_COVERAGE_BAR`, `KIT_CRAP_BAR`), not from this file.

`/code-review` being clean is not the last check. Up to three measurements come
after it and before the pull-request question. The first applies only when the
project has turned on the guarantee check (`tools/guarantees.yaml` exists).

1. **Check that the guarantees the code claims are still defended.** Run
   `python tools/guarantees.py` and report what it said, one line per result.
   `docs/agents/guarantees.md` owns the results and what to do about each.
   First, because it names tests and the coverage run has to see the suite as it
   ends up. Skip this step, and say so, when the project has no guarantee list.

   `pre-push` runs it too, but only when the push is already under way. Run
   here, it puts the result in the report that goes with the pull-request
   question, where the engineer can read it before anything leaves the machine.
2. **Measure how much of the code the tests actually run.** Report the number
   in plain words: "the tests run 82 out of every 100 lines". The line-coverage
   bar is `docs/agents/coverage-and-crap.md`. Under it, write unit tests until
   the run clears it, and say which files were thin.
3. **Measure the CRAP score of every function.** Report the number of
   functions checked, and the worst score, the same way. The CRAP bar is that
   same file. Over it, simplify that code until the run clears it, and say
   what changed and why.

**These bars measure the code in `KIT_PACKAGE_DIR`.** On a ticket that changes
only code outside that directory (documentation, a script elsewhere, another
language), they run clean while measuring nothing about the change. Report them
in exactly those words, rather than as evidence the ticket is sound. If the
project keeps separate bars for another part of the codebase, clear those and
report them beside these, saying which set measured the change.

Report what each said, pass or fail: the guarantee results, the coverage
percent, the worst CRAP score. A measurement that was taken and not said is a
measurement the engineer cannot check.

**If any fix changed code, go back around.** `/code-review`, then guarantees,
then coverage, then CRAP again, in that order, until one full pass changes
nothing. New tests and simplified code are code nobody has reviewed, and
skipping the second lap is how an unreviewed change reaches a pull request.

Say each lap out loud as it starts: "the fixes changed code, so this is lap 2
of review, guarantees, coverage, and CRAP". The engineer can then see the loop
turning rather than guess why it is still going.

**Two ways this ends early, and both are questions rather than decisions.** A
function that cannot clear the CRAP bar without a refactor the repo has already
argued against belongs in `tools/crap-exempt`. Offer the entry and the reason,
and never add one unasked. And if three laps have not settled it, stop and say
so: name the number, name what is left, and let the engineer choose. An endless
loop is worse than a bar that is missed on the record.
