# Writing the review route

Read this at "Hand over the review" in `SKILL.md`, once the pull request is
open. Nothing before that gate needs it, and a `report` run never reaches it.

**This file owns what a route is.** `/aes-work-the-review` walks a route it
is handed or finds; it does not describe how to write one.

This is not a summary of the change. The pull request already holds that. It
is an ordered route through the diff, written for the person who has to decide
whether to merge it. Their time is the scarce thing, so the route spends it
where a defect would actually hurt.

**Write it as numbered passes, in the order they should be read.** Each pass
names the files, says what question that pass answers, and gives the command to
run. Roughly:

1. **The diagram first**, when the ticket has one. It is the cheapest way to
   find out the whole shape is wrong, and it costs three minutes. Say plainly
   that a wrong picture means stop, because the rest of the review is only
   asking whether the code matches it.
2. **The pure code next**: the modules with no IO in them. They hold the rules
   and they read fastest.
3. **The code that had to change to hold the rules**: the workflow, the
   store, whatever the ticket's seam actually cut into.
4. **Run the tests that carry the hard criteria**, named individually, with the
   command. Tell them how long it takes.
5. **The blast radius**: everything the change forced elsewhere. This is where
   a reviewer's judgment is worth most, so say which call was a judgment call.
6. **The gates and formats**: a version bump, a migration, a regenerated
   fixture. Short, but never left out.

Skip a pass that this ticket does not have. Never pad the list to six.

**On a project with more than one package, passes 2 and 3 split by package
rather than by IO.** Read the package with no dependencies on the others first,
then the ones that depend on it. Pass 6 carries whatever a gate regenerated: a
committed generated type, a message catalog, a changeset.

Five things the route must carry:

- **One command per pass, ready to run.** Not "look at the tests": the exact
  line, in a `bash` block, so the terminal's Run button works.
- **Every command runs from the reviewer's checkout, not from yours.** A route
  is read in a worktree the writer never saw, so a relative path to the virtual
  environment resolves somewhere else or nowhere. Write the venv's `bin`
  absolutely (the directory `KIT_VENV_DIR` names), and pin `PYTHONPATH` to the
  reviewer's own source directory:

  ```bash
  PATH="/abs/path/to/<venv dir>/bin:$PATH" PYTHONPATH="$PWD/<source dir>" python -m pytest ... -q
  ```

  **Both halves, and the second is the one that lies.** Without `PATH`, a gate
  that shells out to a bare `python` fails for no reason. Without `PYTHONPATH`,
  the editable install points at the main checkout, so the suite imports a
  package the branch does not contain and reports a pass or a failure about the
  wrong code. That is the failure `docs/agents/worktree-hooks.md` says the hooks
  exist to prevent, arriving by the one route the hooks do not cover.

  **Diff against a freshly fetched `origin/<default branch>`, never the local
  default branch.** The reviewer's local branch is wherever they last pulled it,
  so a diff against it can show everything merged since then as well as the pull
  request. A stale `origin/<default branch>` inflates the diff the same way, so
  the command fetches first:

  ```bash
  git fetch origin <default branch> && git diff origin/<default branch>...HEAD -- <files>
  ```

  **Add no flag that the suite's own `addopts` already sets.** A second `-q`
  on top of one from the config drops the summary line, so a clean run prints
  no count, and the reviewer cannot check the number the route predicted. Read
  the `pytest.ini` of the suite a command runs before adding one.
- **The question each pass answers**, in one sentence. A reviewer who knows
  what they are looking for finds it; one who is reading for general badness
  does not.
- **At least one way to break it.** Name a line to change and say which tests
  should go red. A test suite nobody has tried to falsify is a suite nobody
  has checked.
- **Every judgment call, named.** Anything decided rather than derived (a
  criterion met differently than written, a trade taken, an alternative
  rejected) is put in front of them as a decision to confirm, never buried as
  a fact. If `/code-review` found something real, say what it was and how it
  was fixed; a defect the engineer never hears about is a defect they cannot
  weigh.

**Time it honestly.** Give each pass a rough number of minutes, and make the
numbers real. An engineer who is told twenty minutes and spends ninety stops
trusting the next estimate.

End with what is still open and what the agent did not do: the unreviewed fix
commit the stopping rule leaves behind (`AGENTS.md`), and that it has not
merged and will not.
