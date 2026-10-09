---
name: aes-second-opinion-to-tickets
description: "Have a second model review the ticket breakdown /to-tickets drafts, and revise it until it gives a thumbs-up. Pass the key of the Epic or spec the tickets come from. Use whenever /to-tickets has a breakdown ready, before it is shown to the user for approval and before anything is created in the tracker."
argument-hint: "<PROJ-123>"
---

# Second-opinion review of a ticket breakdown

A second model checks every ticket breakdown before it reaches the tracker. The
reviewer answers with a thumbs-up or with suggestions. On suggestions, revise
the breakdown and send it back. On a thumbs-up, show the breakdown to the user
for approval.

A thumbs-up does not replace the user's approval. Nothing is created in the
tracker until the user says yes.

## The reviewer is a parameter

The reviewer CLI and the reviewer model are the user's choice, as set out in
`/aes-second-opinion-design`, "The reviewer is a parameter". Take them from
`AGENTS.md` or ask once per session. Neither is hardcoded here.

Argument: `<PROJ-123>`, the key of the Epic or spec the tickets come from
(`/aes-second-opinion-to-tickets PROJ-364`). Without one, use the key this
session's `/to-tickets` run started from. If there is none, ask for it.

## Steps

1. Fetch the source. Completion: you have the ticket's summary, full
   description, and comments, and the key and title of each child it already
   has. Fetch by the operation table in `docs/agents/issue-tracker.md` for the
   tracker `KIT_TRACKER` names, asking for children by parent and only the
   summary field.
2. Find or draft the breakdown. Completion: you have a breakdown drafted from
   this source. Use the one in this session if there is one. If not, read
   `vendor/mattpocock-skills/to-tickets/SKILL.md` and follow its steps 1 to 3
   for the source ticket.
3. Draft every ticket in full. Completion: each ticket has the fields under
   "What a ticket holds", not just the short list `/to-tickets` step 4 shows.
4. Write the review prompt to a file. Completion: a file in the scratchpad
   holds the source, any existing children, and the full breakdown, in the
   shape under "The prompt".
5. Send the first round. Completion: you have the reply text and, if the CLI
   returns one, its session id.
6. Read the verdict. Completion: the first line is `VERDICT: THUMBS-UP` or
   `VERDICT: SUGGESTIONS`.
7. On suggestions, revise and resend on the same session. Completion: the
   reply is a thumbs-up. If the round cap under "When to stop" is hit, or
   the call fails as under "When the call fails", stop here and wait for the
   user. A breakdown with no thumbs-up is not shown for approval.
8. After a thumbs-up, go back to `/to-tickets` step 4 with the revised
   breakdown. Completion: the user has the breakdown, the round count, what
   changed, and any suggestion you declined with its reason.
9. If the user changes the breakdown, follow "When the user changes it".
   Completion: the user has said yes to the final breakdown.

## What a ticket holds

The reviewer can only check what it is shown. Give each ticket:

- A number in the breakdown, used for blocking edges until tracker keys exist.
- Title.
- Issue type and label, picked from `docs/agents/issue-types.md`.
- Parent: the Epic it belongs to, and the capability it links to if any.
- Blocked by: ticket numbers, or "None".
- What to build.
- Acceptance criteria.

## The prompt

The reviewer may not be able to read the tracker. Paste what it needs into the
prompt: the source ticket's full description, any comments that change its
scope, and the children found in step 1.

```text
You are reviewing a ticket breakdown, drafted from <PROJ-123>: <summary>.

The source:
<paste its full description, and any comments that change its scope>

Tickets that already exist under this parent:
<key and title of each, or "None">

The proposed tickets:
<paste every ticket in full>

Check that the breakdown is accurate:
- Every requirement in the source is covered by a ticket.
- No ticket adds scope the source does not ask for.
- No ticket repeats one that already exists.
- Each ticket is a vertical slice that can be shown working on its own and
  fits in one fresh context window.
- Each blocking edge is real, none is missing, and there is no cycle.
- Each acceptance criterion can be checked, and matches the source.
- What a ticket says about existing code is true. Read the repo to check.
- Terms match GLOSSARY.md, and no ticket breaks an ADR in docs/adr/.

You may read the repo, AGENTS.md, and docs/agents/. Do not edit anything.

Reply in this shape. The first line is exactly one of:
VERDICT: THUMBS-UP
VERDICT: SUGGESTIONS
After SUGGESTIONS, give a numbered list. Each item names the ticket by
number, the problem, and the change you want.
```

## The command

Run it from the repo root, so the reviewer reads the same checkout. One example,
for the Claude Code CLI:

```bash
claude -p --permission-mode plan --model opus --output-format json "$(cat <prompt-file>)"
```

- `--permission-mode plan` keeps it read-only.
- `--output-format json` returns the reply in `result` and the thread in
  `session_id`.

For every later round, resume the same session if the CLI supports it (with
Claude, add `--resume <session_id>`), so the reviewer remembers the earlier
breakdown and its own suggestions. If the CLI cannot resume, resend the whole
revised breakdown with the earlier suggestions listed above it.

## Each later round

Send the whole revised breakdown, not a diff. Keep ticket numbers stable
across rounds. A new ticket gets the next unused number, and a removed
ticket's number is not reused. Above the breakdown, list each suggestion by
number with what you did:

- adopted: say what changed in the breakdown.
- declined: say why in one sentence.

Decline a suggestion only when it is wrong for this breakdown: it breaks an
ADR, contradicts the source, or widens the scope. The reviewer may accept the
reason or press the point. Its verdict decides the round.

## When the user changes it

The user's call wins over the reviewer's. If the user adds, removes, splits,
merges, or re-links a ticket, or changes its acceptance criteria, send the
changed breakdown back on the same session. Show the user anything the reviewer
objects to, and let them decide. A change to wording alone does not need
another round.

## When to stop

Stop after ten rounds without a thumbs-up. Show the user the open
suggestions and your reasons, and ask how to proceed. Do not show the
breakdown for approval until they answer.

## When the call fails

A failed call is not a thumbs-up. Do not show the breakdown for approval
until the user answers.

- An authentication error: ask the user to log in to the reviewer CLI, then
  retry.
- An unknown model: list the CLI's models, tell the user, and ask which to use.
  Do not swap models without asking.
- No `VERDICT:` first line: resend once on the same session asking for the
  required shape. A second miss counts as a failed call; tell the user.
