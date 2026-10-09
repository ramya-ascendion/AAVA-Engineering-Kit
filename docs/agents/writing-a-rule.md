# Writing a rule: classify it before you write it

**Decide how a rule will be enforced before writing a sentence of it, because
the answer decides where it lives.** A rule a script can decide should be a
script. Prose costs tokens every time an agent loads it; a gate costs none, and
a gate never forgets.

## Pick the enforcement from one question

**Figure:** whether a script can decide a rule with no judgment sets whether it
becomes a pre-commit hook, a CI job, a short prose rule backed by a gate, or
prose alone. Source: [`rule-enforcement-picker.mmd`](rule-enforcement-picker.mmd).

The question is never "is this rule important". It is "can a script decide it".

- **Deterministic.** A script decides pass or fail. Write the script, and write
  no prose beyond a line saying the gate exists.
- **Hybrid.** A script checks the shape and a person judges the content. This is
  the common case, and the gate is what lets the prose stay short.
- **Inferred.** There is nothing to check. The rule is prose in a leaf file,
  reached by a pointer.

## Pick where the gate runs

A pre-commit hook and a CI job are not alternatives. The hook gives the agent
fast feedback in the loop it is already in. The CI job makes the rule
unskippable, and writes its failure onto the pull request where the next agent
reads it. A rule that matters gets both.

`--no-verify` skips every hook, so a hook alone is a reminder rather than a
gate. Anything slow, anything that must not be skipped, and anything needing
more than a checkout belongs in CI.

Some checks need infrastructure that may not exist yet, such as a deployed test
environment reachable from CI. The slow test suites, the coverage bar and the
CRAP bar are the usual cases. Keep them out of the commit gate because they are
neither fast nor free, which is exactly what makes them CI work rather than hook
work. Checks that need only a checkout and a shell ship now.

## Three rules about where prose goes

**One question per leaf file.** A file in `docs/agents/` answers one question.
If an agent has to load it to learn something unrelated, it is two files. A
thousand-line file is not thorough, it is a file that has stopped answering one
question.

**`AGENTS.md` holds the pointer and the gist, never the rule.** It is loaded in
every session, so it pays for its own length one hundred percent of the time.
A leaf file is loaded only when it is needed.

**A rule names a template, never a live document.** A document cited as an
example drifts, and then the rule and its example disagree. Templates live in
`docs/agents/document-templates/`.

## Before it lands

A gate that does not go red is not a gate. Break a file on purpose, watch the
check fail, then fix the file. Do this before the rule is merged, not after
someone wonders why nothing has ever failed.

**Break the invocation as well as the file.** A check can be correct and still
never run, and the wiring around it is where that happens: an input it cannot
resolve, an empty file list, a step that swallows a failure and carries on. Ask
what the gate does when it is handed nothing, and make sure the answer is that
it fails rather than passes.

A worked example of the trap: a script had every one of its checks proved red on
a broken file before it landed, yet the CI step running it skipped all the checks
and reported success whenever the base commit could not be resolved, which is
every branch-creation push. The script was tested; the step that runs it was not.

**A run that happened to pass is not a red test.** A first CI run that comes
back green proves the setup for the one event that fired. The event that breaks
it may not have run yet.

## What this file does not decide

- **What document types exist, and what each one is for.**
  [`document-types.md`](document-types.md) and `tools/document_types.yaml`.
- **Which hooks run and when.** [`worktree-hooks.md`](worktree-hooks.md).
- **How to structure the prose once you have chosen it.**
  `.agents/skills/aes-writing-for-agents/SKILL.md`, and the writing standard in
  `AGENTS.md`.
