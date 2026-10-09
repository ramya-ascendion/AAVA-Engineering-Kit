# Guarantees: the claims a docstring makes, and the tests that keep them honest

**OPTIONAL.** This check needs `tools/guarantees.py` and a list at
`tools/guarantees.yaml`. A project that has not installed the tool and written a
list skips everything on this page, and every other rule in `docs/agents/` still
holds. Turn it on when the code makes promises that a refactor could quietly
break, and the project has tests it trusts to catch that.

A docstring that says "**A session idle past the limit is refused.**" is making a
claim. The only way to check a claim is to remove what keeps it and see whether
anything notices.

`tools/guarantees.yaml` lists guarantees the code states. For each one it names
the line that keeps it and the tests that prove it. `tools/guarantees.py`
removes that line and runs those tests. If they stay green, the guarantee was
decoration.

The decision behind it, worth recording as an ADR in the project: measure a
commit rather than a working tree, and put every claim written in bold in a
docstring or comment on the list, so a promise cannot be made without being
checked.

## Run it

```bash
python tools/guarantees.py
```

It measures `HEAD` (a commit, never the working tree) and says so, along with
how many files differ. `--ref` measures another commit.

## Five results

| Result | Meaning | What to do |
| --- | --- | --- |
| `proved` | the tests go red when the guard is removed | nothing |
| `unproved` | the guarantee is stated and no test defends it | fix the test |
| `exempt` | the list declares it untestable, with a reason | nothing |
| `unmeasured` | its proof needs infrastructure (a staged test server, say) and none is available | stage it, then run again |
| `broken` | nothing was measured: the list no longer matches the code, is empty, or a proof or the tool itself could not run | fix what the run names |

A run exits on the worst result it reached. `RANK` in
`tools/guarantee_results.py` owns the order, and `EXIT` beside it owns each
result's exit code. The two orders differ on purpose.

`proved` and `unproved` are verdicts a guarantee earns. `exempt` is a
declaration the list makes instead of earning one. `broken` is not about the
guarantee at all. It says the run measured nothing, which is why it does not
share `unproved`'s exit. [`coverage-and-crap.md`](coverage-and-crap.md) sets that
shape for `tools/crap.py` (a pass, a failed bar, and a run that could not
measure, each with its own exit) and this follows it for those four.

**`unmeasured` is where the tool leaves that shape.** It is a fact about the
machine, not the code, and a push should survive it. So it needs an exit of its
own that a caller can tell apart, and it ranks below `unproved`, so a run
holding both still exits as `unproved`.

**A runtime entry is one whose proofs live in a suite that needs standing
infrastructure**, so it needs that staged first. From a worktree, the tool looks
in the main checkout too, because the staging directory is ignored by git and a
worktree never has one of its own.

**A timeout is `broken`, never `unmeasured`.** A hang is the tool or the proof
failing, not the machine lacking something.

**A refusal says FAILED.** A crash, a commit that carries no list or an empty
one, or a ref git cannot archive all exit as `broken` and print `FAILED — …`.
NOT RUN is the word both hooks keep for a check that was not needed, and
`pre-push` refuses on this exit.

**`broken` is the interesting one.** It means a quotation in the list no longer
resolves: a docstring was reworded, a guard moved out of its symbol, a proof was
renamed. The code may be perfect. Nothing was measured, so nothing is claimed.

## What an entry holds

```yaml
- guarantee: "**A session idle past the limit is refused.**"
  file: src/example_app/session.py
  symbol: open_session
  guard: "if fields is None or not _fresh(settings, fields[\"t\"]):"
  replaced_by: "if fields is None:"
  removes: "the idle limit, and only that"
  fails_with: "assert 200 == 401"
  tests:
    - tests/unit/test_session.py::TestSession::test_a_session_idle_past_the_limit_is_401
```

This entry is an invented example. `guarantee` and `guard` must each appear
**exactly once inside `symbol`'s span**, and the guarantee must fit on one source
line. The span starts at the first decorator, because a decorator such as
`@dataclass(frozen=True)` is a guard and `ast` keeps decorators outside
`ClassDef.lineno`.

**`fails_with` is transcribed from what pytest printed**, never from what the
code raises. Those differ, and the difference is not small: a `pytest.raises`
block whose mutation stops the raise reports `Failed: DID NOT RAISE
MissingSecret`, not the exception's name. Measure first, then write the entry.
It may be a list where one failure has more than one spelling.

An entry that cannot be tested carries `reason` and no `guard`. The reason has
to point at something already written down: an ADR, a docstring, a ticket. If
it is not written down somewhere else, it is not a reason yet, which is the rule
`tools/crap-exempt` asks for and the same rule here.

## Checking a guarantee by hand

Removing a guard and watching a test go red is the quickest way to see whether
an entry is honest. **From a worktree, put its own source on the path first:**

```bash
PYTHONPATH=$(git rev-parse --show-toplevel)/<source dir> pytest <the proof> -q
```

The virtualenv is the main checkout's, and its editable install names that
checkout's source absolutely ([`worktree-hooks.md`](worktree-hooks.md)). Without
the override, pytest imports the *other* tree's package, the mutation is
invisible, and **the test stays green**. That reads as "the guarantee was
decoration" when nothing was measured at all.

`tools/guarantees.py` closes this for itself: it replaces `PYTHONPATH` and the
temp tree refuses to collect unless the package resolves inside it. A person
typing pytest directly gets no such guard, which is why it is written down here.

## Choosing the mutation

**The mutation removes the guarantee and nothing else.** That is the one
judgment in an entry no machine repeats, which is what `removes` is for: it says
in words what the edit takes away, so a reader can tell whether the entry proves
the guarantee it quotes or something next to it.

Two ways to get it wrong:

- **Too wide.** `if not secret:` → `if False:` stops refusing a blank secret and
  a never-set one. `if variable not in secrets:` removes only the blank half.
- **Beside the point.** Replacing a whole check's result with an empty value can
  complete a workflow in seconds, but it discards the activity's answer as well
  as the check, so it stops modeling a worker that answers wrongly.

## Keeping it fast

**A proof is the narrowest node id that can fail**: a test, or one case of a
parametrized test, spelled the way pytest reports it (`test_it[2]`). Never a
class, never a file. The cost is two pytest starts per entry plus each proof's
own time, so the work is flat in the size of the suite and linear in the length
of the list. Running entries in parallel divides the wait, not the work.

**Entries are measured in parallel, and no two running entries share a
tree**, so no entry ever reads another's mutated file. The trees are the one
the commit was laid out in and a copy of it for each extra worker, and a free
tree goes to the next entry. `WORKERS` in `tools/guarantees.py` owns how many
run at once. Entries whose proofs are runtime tests run after the rest, one at
a time in the first tree, because they wait on real time and a timeout is
`broken`. If one entry makes the tool fail, the entries not yet started are
canceled rather than waited out.

Measure your own list before choosing `WORKERS`: gains flatten past a few
workers, and a long list on every push can miss a two-minute budget. Say so in
the project's notes rather than raising the worker count to meet it.

`timeout_seconds` on an entry is checked against the bound its proof actually
waits, read out of the test's own `ast` span rather than copied into the list.

## Every bold claim is accounted for (optional)

If the project also installs `tools/claims.py`, **bold in a source docstring or
`#` comment is a guarantee**, and a commit fails on any bold run that nothing
accounts for. `tools/claims.py` owns what counts as a run. Run it by hand:

```bash
python tools/claims.py
```

It prints how many claims there are and how many are owed, then names every
claim that is not accounted for, by file, line and symbol. Each one takes one
of three answers:

- **Prove it.** Write an entry in `tools/guarantees.yaml`, the way the rest of
  this document describes. Pick this when a test already fails without the
  guard, or one is cheap to write. The bold run has to fit on one source line,
  so reflow it first if it wraps.
- **Owe it.** Add a line to `tools/guarantees-owed.yaml` with the claim's words
  and a ticket of its own. Pick this when the promise is real and proving it is
  work for later. The ticket cannot be the umbrella ticket whose count only
  falls, or the ticket that built the gate. `SEEDED_TICKET` and `THIS_TICKET` in
  `tools/claims.py` name them.
- **Remove the bold.** Pick this when it was emphasis, a heading, history or a
  reason, not a promise about what the code does. Use italic when the emphasis
  still matters. On a pull request, CI lists every claim that lost its bold, so
  the reviewer sees each one.

An owed line whose claim no longer exists anywhere fails too. When you reword a
claim, reword its owed line to match.

To plan a batch of owed claims, list the ones under a folder or a file:

```bash
python tools/claims.py --owed-under <folder>
```

It prints each owed claim's file, line, symbol, the ticket it is owed to, and
its words, sorted by file and line, and exits 0. It checks nothing, so it never
changes what the gate decides.

- **The path is read from the repository root.** `./` and an absolute path
  inside the checkout name the same place. Only source is scanned, never its
  tests, so a path anywhere else lists nothing. A path that names nothing is
  refused with exit 2, because an empty listing would read as nothing owed.
- **A claim bold in two places is listed at both**, so the line count can be
  more than the owed count. One owed line covers every copy, and so does one
  list entry with the same words. The gate matches words, not places, so a
  proof at one copy satisfies it for the rest without testing their code.
  Copies in different modules can guard different code, so look at each.
- **Nothing owed is missing from the listing.** An owed line whose claim is
  bold nowhere already fails the gate.

**Figure:** a commit or a pull request runs `tools/claims.py`, which reads every
bold run in the source and the two lists. On a pull request it also reads the
owed list at the base, and lists claims that lost their bold. It passes when
everything is accounted for, and otherwise fails with three ways out. Source:
[`guarantee-claims-gate.mmd`](guarantee-claims-gate.mmd).

## What nothing checks

Said plainly, because a limit nobody wrote down is a limit nobody remembers.

- **Whether `removes` is true.** It is prose. Only review catches a mutation
  that removes something other than what the entry claims.
- **A guarantee written without bold.** The claim gate above reads bold and
  nothing else, so plain prose escapes it by design.
- **Which copy of the tool runs at push.** `pre-push` runs the working tree's
  `tools/guarantees.py` against the pushed commit's code and list. A push of a
  ref other than the one checked out, or one with uncommitted edits to the
  tool, is judged by a tool that is not the one being pushed.

## What does run automatically

**The whole list, on every push that could change what a test does**, once for
the tip of each ref the push changes, when the project wires it into
`pre-push`. [`worktree-hooks.md`](worktree-hooks.md), "The guarantee check runs
at push", says which tips are measured.

**Figure:** the order `pre-push` takes. It reads the refs, keeps each pushed
sha, checks the tool and Python are there, runs the tool once per tree, and ranks
the results. A refusal stops the push. Source:
[`guarantee-check-at-push.mmd`](guarantee-check-at-push.mmd).

Ordinary unit tests, so the commit gate runs them on every Python change:

- `tests/unit/test_guarantees_list.py`: the list still points at the code.
  Every quotation resolves, every proof exists, the excused count is what it was.
  No mutation, no subprocess.
- `tests/unit/test_guarantees_tool.py`: the tool's own behavior.

The measure-`HEAD` check is a **lagging** check. Run from `pre-commit`, `HEAD` is
the state before the change, so a commit that breaks a proof passes and the next
commit fails naming something that looks unrelated. That is the price of
measuring a commit rather than a tree somebody is editing, and the design takes
it knowingly.

**The claim gate also runs on every pull request**, in the CI gates workflow,
where `--no-verify` cannot skip it. It needs no test infrastructure.

## The tool is outside the quality bars

`tools/` is outside the measured package and is not in `tools/crap-exempt`
either, because it never enters the analysis. Coverage and CRAP say nothing
about this tool whatever it does, so its own unit tests are the only thing
between it and rot. Apply the CRAP bar to it by hand if it matters.

Measure it deliberately, the same way the bars are measured:

```bash
COVERAGE_FILE=/tmp/.cov-tools coverage run --source=tools -m pytest -q \
  tests/unit/test_guarantees_tool.py tests/unit/test_guarantees_list.py \
  tests/unit/test_claims.py
COVERAGE_FILE=/tmp/.cov-tools coverage report \
  --include="*/tools/guarantee*.py,*/tools/claims.py"
```

Record the result as a measurement with a date rather than as a bar, because
nothing enforces it. If it matters enough to enforce, that is a decision
somebody makes on purpose.
