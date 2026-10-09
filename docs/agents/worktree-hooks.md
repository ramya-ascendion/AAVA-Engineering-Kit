# Hooks in a worktree

**The rule: a commit or push made from a worktree runs the same gates as one
made from the main checkout. `--no-verify` is for a change that touches no code
the gates look at, and nothing else.**

Three things make that rule hard to follow in a repo with worktrees, so people
stop trying. The hooks in this kit fix all three, and this file is the map. In an
installed repo the hooks live in `.git-hooks/`.

**Figure:** how a commit from a worktree finds its hook, decides what to run, and
finds both its tools and the source it tests. Source:
[`worktree-hook-lookup.mmd`](worktree-hook-lookup.mmd).

Read the picture as three questions asked in order. Which hook file runs. Whether
this change could reach a test. Where the tools are, and which source they test.
Every path but one ends in a commit you can make. The failure-colored one is the
refusal: no environment anywhere, on a change that needs one.

## One: which hook file runs

A worktree can carry `core.hooksPath` in **worktree scope**, holding an absolute
path to the main checkout's `.git-hooks`. Nothing in this kit writes it, and
`setup-dev-env.sh` sets the repo-wide, relative one, so it arrives with whatever
created the worktree, next to settings like `core.longpaths`. Many worktrees end
up carrying it.

Git then runs main's hook while this branch may be editing its own. That could
be a refusal pointing at `git config core.hooksPath .git-hooks`, which is
repo-wide and already correct. Nothing you did would change anything, so
`--no-verify` would be the only thing that worked, on the exact branch where the
hooks most need to run.

**So the hook hands off.** It `exec`s this branch's own copy, with the same
arguments and the same stdin, and says that it did. You need to do nothing.

Clearing the override is still tidier, and makes git run the right file directly:

```bash
git config --worktree --unset core.hooksPath
```

### `common.sh` is an interface between checkouts, so its names are fixed

The hand-off depends on something easy to miss. Every hook sources
`$(git rev-parse --show-toplevel)/.git-hooks/common.sh`, and that path resolves
to the worktree git is working in, **not** to the checkout the hook file came
from. So the main checkout's older `pre-commit` sources this branch's
`common.sh`, then calls the function names it was written against.

Rename one and that hook dies with `command not found` before it reaches the
hand-off, which is the only path that makes committing from a worktree work.
`refuse_if_stale` reads oddly now that it usually hands off rather than refusing.
The name stays anyway: it is an interface, not a label.

Removing or renaming a name needs a release where the old name stays as a shim
until every checkout carries the new file. **Adding one is only safe in that
direction.** A new hook that calls a name an older `common.sh` does not define
dies the same way, and the hooks run under `set -uo pipefail` with no `-e`, so it
dies quietly and the hook carries on with that step skipped.
`tests_not_needed_note` is the sort of function this applies to: the newer hooks
call it, and a checkout still on an older `common.sh` has no such function.

A unit test in `tests/unit/test_git_hooks.py` should own the list of names
reached from outside `common.sh`, with who calls each, and fail when one goes
missing.

What no test covers is the other direction: a newer hook sourcing an older
`common.sh`. That needs two checkouts of different ages, which a test harness
rarely builds.

## Two: whether this change could reach a test

**The suites run when something in the change could alter what a test does, and
report NOT RUN when nothing could.** The rule is `path_affects_tests` in
`.git-hooks/common.sh`, asked by both hooks: `pre-commit` about the staged files,
`pre-push` about the files in the refs git hands it on stdin.

Anything arguable counts as reaching a test:

- any `.py`
- anything under the test directories (`KIT_TEST_DIRS`), the package directory
  (`KIT_PACKAGE_DIR`), `tests/`, `tools/` or the hooks directory itself
- `pytest.ini`, `pyproject.toml`, `setup.py`, `setup.cfg`, `.flake8`, `.pylintrc`,
  `.kit/config.env`
- any `requirements*.txt`

The list errs toward running. Running the suite when it was not needed costs a
minute; skipping it when it was needed is the failure the hooks exist to prevent.
The hooks directory is in the list because a unit test runs those very files.

A change outside all of that needs no virtual environment and is not refused for
lacking one. The prose gates (American spelling, the skill mirror, the document
structure) still run; they are shell scripts and need nothing installed.

A project that adds another kind of code (a web client, say) adds a second rule
beside `path_affects_tests`, asked independently by both hooks, so a change can
run one, both or neither. Extend `common.sh`'s rules rather than special-casing a
hook.

## Three: where the tools are, and which source they test

The virtualenv at `KIT_VENV_DIR` is built by `setup-dev-env.sh`. `git worktree
add` does not copy it, and never will. It is a cache on disk, not something the
repository tracks.

So `activate_venv` looks in two places: this checkout, then the main checkout,
which `git rev-parse --path-format=absolute --git-common-dir` names from inside
any worktree. It only builds that second path when the answer ends in `.git`. A
bare repository has no checkout beside it, and `dirname` on `repo.git` would name
an ordinary folder above it, whose virtualenv, if one is there, belongs to
somebody else.

Finding neither is a refusal, in both hooks, whenever the change could reach a
test. A system pytest on `PATH` does not count: it would run the suite against a
different project and report the answer as if it were this one.

**Activating that environment is not enough on its own.** The editable install
inside the virtualenv holds one absolute path, to the checkout it was built in,
and every worktree reaches that environment by symlink or lookup. So a
worktree's gate would import the main checkout's package and test code the
commit did not contain. It shows up as a false failure, on a file the branch
never touched. A false pass is the same mechanism with the sign flipped, which is
the failure these hooks exist to prevent.

So `activate_venv` also prepends this checkout's source directory to
`PYTHONPATH`, which Python reads before the `.pth` file the editable install left
behind. Prepended rather than assigned, so a caller who set it on purpose keeps
their entries behind this one. Guarded on the directory existing, because outside
a checkout `git rev-parse --show-toplevel` says nothing and the path would be a
bare `/src`.

Per-worktree environments would fix the same thing and are a reasonable
alternative when disk is cheap: the trade is the size of one environment per
worktree, and giving up the single environment the hooks look for.

You need no manual setup for any of this. If you want the worktree to have its
own environment anyway, a symlink works and stays invisible to `git status` if
the `.gitignore` entry has no trailing slash, because a symlink is not a
directory:

```bash
ln -s "$(dirname "$(git rev-parse --path-format=absolute --git-common-dir)")/<KIT_VENV_DIR>" <KIT_VENV_DIR>
```

## Four: a check whose answer depends on the file set runs at push

**A check that compares files against each other belongs at push, over every
tracked file, not at commit over whatever was staged.** One check in the kit is
that shape: `duplicate-code`.

**Figure:** a developer commits, the hook splits the staged Python into two
pylint calls, and duplicate-code compares files only inside one call, so whether
the commit is refused depends on which two files it happened to stage. Source:
[`lint-gate-staged-set.mmd`](lint-gate-staged-set.mmd).

Almost every pylint message reads one file at a time, so it answers the same
whatever else is in the run. `duplicate-code` (R0801) compares files against
each other, and only within one invocation. At commit the invocation holds the
staged files, so a developer who touched two files with similar lines would be
refused over code the change never went near. The only way past is
`--no-verify`, which drops flake8, the spelling gate, mypy and the test suites
along with it.

**Figure:** the commit hook keeps the per-file checks and duplicate-code moves to
the push hook over every tracked file. Source:
[`lint-gate-cross-file-split.mmd`](lint-gate-cross-file-split.mmd).

So `pre-commit` passes `--disable=duplicate-code` to its pylint calls, and
`.git-hooks/duplicate-code.sh` runs the check at push over every tracked `.py`
outside `vendor/`. That file set is the same every time, so the answer is about
the tree rather than about the commit.

Two things follow from the move, and both are improvements rather than costs.
The push check is one call, so it compares a test file with a source file,
something a commit hook's test / non-test split could never do. And it is keyed
off the same "could this reach a test" rule with every other Python gate, because
`pyproject.toml` and `.pylintrc` can change what it answers with no `.py` in the
push at all.

**The exempt list names pairs.** `gate_over` in `common.sh` walks a path list one
file at a time, and "these two files may resemble each other" is not a fact about
either file alone, so `.git-hooks/duplicate-code-exempt` is read by the gate
script itself. An entry never drops a file from pylint's arguments and never
writes a `disable` comment into one: both would hide every other pair those files
take part in, and whatever they grow later. An entry is also not a threshold
change. Raising `min-similarity-lines` hides every future pair, while a named
pair leaves the next one failing.

## Five: the guarantee check runs at push (optional)

Only a project that installed [`guarantees.md`](guarantees.md)'s tool and list
has this step. With no `tools/guarantees.yaml`, the push says NOT RUN and goes on.

**`pre-push` runs the duplicate-code gate and then, when the project has one, the
guarantee check.** The guarantee check is `tools/guarantees.py`. It sits behind
the "could this reach a test" rule, after the environment is activated and the
duplicate-code gate has run. The pushed sha, not `HEAD`, is what it measures.

**Figure:** the order `pre-push` takes. It reads the refs, keeps each pushed
sha, checks the tool and Python are there, runs the tool once per tree, and ranks
the results. A refusal stops the push; a warning or a clean run goes on. Source:
[`guarantee-check-at-push.mmd`](guarantee-check-at-push.mmd).

**The tip of every ref the push changes is measured, and the worst result
decides.**

- Only the tip. A commit behind it on the same ref is not measured on its
  own: the check asks whether the code being pushed defends its guarantees,
  and that code is the tip.
- A ref that is a deletion, or that the remote already has, sends no code and
  is not measured.
- Every other ref is measured, including a new branch with no remote default
  branch to diff against. The check needs the commit, not a diff.
- Two refs at the same tree are measured once.
- Once one tip makes the refusal certain, the rest are not measured.
- A push of deletions and refs the remote already has sends no commit, and
  says NOT RUN for every check. Run by hand, with no refs on stdin, the hook
  measures `HEAD`.

**What each result does to a push** is ranked by `RANK` in
`tools/guarantee_results.py`: the hook ranks the tool's exits in that order,
never by comparing the numbers, and it ranks any exit the tool does not name
worst of all. `unmeasured` should not block a push, because it is a fact about
the machine. `unproved` and `broken` do.

What the check costs is [`guarantees.md`](guarantees.md), "Keeping it fast".

## What is pinned

`tests/unit/test_git_hooks.py` runs the real hook files in a subprocess against
checkouts it builds itself (worktrees, virtual environments and pushed refs
included). Nothing depends on how the machine running it is set up. The
behaviors worth a test each:

- Both hooks run to the end from a fresh worktree whose only environment sits in
  the main checkout, and the pytest they ran logged itself to a ledger inside
  that environment. A hook that exits zero without running the suite fails it.
- A prose-only commit and a prose-only push need no environment anywhere and go
  through, saying what they skipped.
- A commit touching a hook still needs the environment. That is the edge easiest
  to get wrong: no `.py` staged, and the suites still run.
- `activate_venv` puts this checkout's source first. Both checkouts get a probe
  module that names itself, and the one that gets imported is this checkout's.
  The claim is which file wins, not which variable is set.
- A caller who set `PYTHONPATH` on purpose keeps it. The prepend, not the
  assignment, is the point; make sure the test would fail against a mutation
  that clobbers the caller.
- An empty commit pushed does not push unchecked. git names the refs and the diff
  between them is empty, so the hook cannot tell what is being pushed and runs
  everything.
- Both pylint passes turn duplicate-code off, not one, so a similar pair that
  lands in whichever pass matches is not refused.
- The whole tree is compared when the push carries Python, and a duplicate pair
  across files refuses the push.
- A pair on the exempt list is let through, in either order, because pylint
  decides which side it prints first.
- A tree with no tracked Python does not call pylint with no files. Pylint given
  nothing to lint is a usage error, and a usage error exits non-zero.

These need a pylint stub that records `"$@"`, because a stub that logs its own
name and nothing else cannot tell the two behaviors apart. `_stub_pylint` in
`tests/unit/hook_harness.py` is that stub, and it can report an `R0801` and exit
8 so the refusal path is real.

A narrower question lives next door in `tests/unit/test_gate_coverage.py`: not
what the hooks do, but what the gates are pointed at and whether this file
describes it. Both failures are silent. A gate that never sees a file reports
nothing and passes, and a stale diagram renders cleanly and looks authoritative.

- The word gates look at the hooks themselves. `pre-commit` and `pre-push` are
  the two files git insists on naming, so they carry no suffix and no `*.sh`
  glob ever reaches them, which makes them the densest prose in the repo and the
  one place a spelling gate could not see. The test reads the pathspec out of
  `pre-commit` and hands it to git, so it cannot pass against a list that has
  drifted from the one the hook uses.
- The diagram says the same skip rule as the hooks. Corrected prose beside an
  uncorrected picture is how a diagram goes stale, so both sides are read out of
  the files.

## One way these tests could damage the real repository

Every test here shells out to git in a scratch directory. Run by `pre-commit`,
they inherit `GIT_DIR`, `GIT_INDEX_FILE` and `GIT_WORK_TREE` from git itself, and
a git command that inherits those operates on the **real** repository while
looking like it is working on the scratch one.

`_clean_env` strips them, and a test should assert that nothing inherits the
caller's git variables.

The worst case is worth naming, because it is silent and wide. `git init --bare`
with an inherited `GIT_DIR` and **no path argument** sets `core.bare = true` on
whatever those variables point at, which breaks `git add`, `git commit` and
`git status` in that checkout and every worktree of it at once. Reproduced
deliberately:

```bash
cd /some/scratch && GIT_DIR=/real/repo/.git git init --bare --quiet
```

A plain `git init` under the same variables does not do it, and every `git init`
in a hook test should pass an explicit target. The scrubbing is what makes that a
rule rather than a coincidence.

## Windows: what must be on `PATH`

The hooks run in Git Bash. A missing tool is a refusal, never a silent skip, so
put these on `PATH` before the first commit or the hook reports `FAILED`:

- `gitleaks` (winget installs it, but not onto Git Bash's `PATH`).
- `node`, for a project whose `KIT_TEST_CMD` runs `node`.
- `python`, for the document-structure gate (PyYAML is optional: without it the
  typed-docs check is skipped, with it the check runs).

In Git Bash, `export PATH="$PATH:/c/Program Files/nodejs:$HOME/AppData/Local/Microsoft/WinGet/Links"`
in the shell that runs `git commit`. A worktree whose `core.hooksPath` still
points at the project's older hook folder runs only those hooks; run the kit's
with `bash .git-hooks/pre-commit` until the hand-over in `AGENTS.md` is done.
