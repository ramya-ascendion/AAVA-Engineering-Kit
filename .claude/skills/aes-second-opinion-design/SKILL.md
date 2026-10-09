---
name: aes-second-opinion-design
description: "Have a second model review a design plan for a ticket, and revise the plan until it gives a thumbs-up. Use whenever you propose a design plan for a ticket, including inside /aes-implement and /aes-work-the-path."
---

# Second-opinion review of a design plan

A second model checks every design plan before work starts. The reviewer
answers with a thumbs-up or with suggestions. On suggestions, revise the plan
and send it back. On a thumbs-up, carry on with the revised plan.

## The reviewer is a parameter

Two settings say who the second model is. The user picks them, and neither is
hardcoded in this skill.

- **Reviewer CLI**: the command-line agent that runs the second model
  non-interactively and read-only (for example `claude -p`, or any other
  agent CLI the project uses).
- **Reviewer model**: the model that CLI runs (its identifier, as the CLI lists
  it).

Take them from `AGENTS.md` if the project records them there. If they are not
recorded, ask the user once at the start of the session, and use the answer for
every round and for the other `aes-second-opinion-*` skills in the same session.
Do not guess a model name, and do not swap models without asking.

## Steps

1. Write the review prompt to a file. Completion: a file in the scratchpad
   holds the ticket key, the ticket's summary and acceptance criteria, and
   the full plan, in the shape under "The prompt".
2. Send the first round. Completion: you have the reply text and, if the CLI
   returns one, its session id.
3. Read the verdict. Completion: the first line is `VERDICT: THUMBS-UP` or
   `VERDICT: SUGGESTIONS`.
4. On suggestions, revise and resend on the same session. Completion: the
   reply is a thumbs-up. If the round cap under "When to stop" is hit, or
   the call fails as under "When the call fails", stop here and wait for the
   user. A plan with no thumbs-up does not go on to step 5.
5. After a thumbs-up, tell the user the outcome, then continue with the
   revised plan. Completion: the user has the round count, what changed in
   the plan, and any suggestion you declined with its reason.

## The prompt

The reviewer may not be able to read the tracker. Paste what it needs from the
ticket into the prompt.

```text
You are reviewing a design plan for ticket <PROJ-123>: <summary>.

Acceptance criteria:
<paste them>

The plan:
<paste the full plan>

You may read the repo to check the plan against the code and AGENTS.md.
Do not edit anything.

Reply in this shape. The first line is exactly one of:
VERDICT: THUMBS-UP
VERDICT: SUGGESTIONS
After SUGGESTIONS, give a numbered list. Each item names the part of the
plan, the problem, and the change you want.
```

## The command

Run it from the worktree root, so the reviewer reads the same checkout. The shape
is the same for any CLI: print mode, read-only, the reviewer model, the prompt
from the file. Here is one example, for the Claude Code CLI:

```bash
claude -p --permission-mode plan --model opus --output-format json "$(cat <prompt-file>)"
```

- `--permission-mode plan` keeps it read-only.
- `--output-format json` returns the reply in `result` and the thread in
  `session_id`.

For every later round, resume the same session if the CLI supports it (with
Claude, add `--resume <session_id>`), so the reviewer remembers the earlier plan
and its own suggestions. If the CLI cannot resume, resend the whole revised plan
with the earlier suggestions listed above it.

## Each later round

Send the whole revised plan, not a diff. Above it, list each suggestion by
number with what you did:

- adopted: say what changed in the plan.
- declined: say why in one sentence.

Decline a suggestion only when it is wrong for this ticket: it breaks an ADR,
contradicts the acceptance criteria, or widens the scope. The reviewer may accept
the reason or press the point. Its verdict decides the round.

## When to stop

Stop after ten rounds without a thumbs-up. Show the user the open
suggestions and your reasons, and ask how to proceed. Do not start the work
until they answer.

## When the call fails

A failed call is not a thumbs-up. Do not start the work until the user
answers.

- An authentication error: ask the user to log in to the reviewer CLI, then
  retry.
- An unknown model: list the CLI's models, tell the user, and ask which to use.
  Do not swap models without asking.
- No `VERDICT:` first line: resend once on the same session asking for the
  required shape. A second miss counts as a failed call; tell the user.
