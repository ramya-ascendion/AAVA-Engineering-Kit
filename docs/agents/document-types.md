# Document types: what this repo's documents are, and how to add a kind

**Every document in this repo belongs to a type, and the type says what the
document is for, when it is created, when it stops being current, and who
answers for it.** A file that belongs to no type has no owner, and a document
with no owner is the one nobody updates and nobody deletes.

`tools/document_types.yaml` holds the types. It is the list, and it owns the
values. This file says what a type is, how to read an entry, and how to add one.
Do not copy a value out of the YAML into prose. Point at the type by name.

## The four questions every type answers

A type entry answers the same four questions, in this order.

- **For.** What this document is. One sentence, and it says what the document
  holds rather than what it is about.
- **Born.** When one gets created. A type whose answer is "whenever someone
  feels like it" is not a type yet.
- **Dies.** When it stops being current. This is the field most often left
  blank, and it is the reason a repo fills up.
- **Owner.** Who answers for it. A person, a ticket, or another document, never
  "the team".

A type may add extra fields on top of those four. An ADR adds its amendment
history, a research note adds the date its claims were true, an external
document adds its audience. The entry's `extras` names them, so one script can
check each document against its own type's rule rather than a pile of bespoke
checks being written and then drifting apart.

## Settled and pending

An entry's `status` says whether its rules are agreed.

- **Settled** means the rules are written down, and the entry names the file
  that holds them. That file wins over anything summarized here.
- **Pending** means the type is real and its documents exist, but the rules are
  still being agreed. The entry's `ruled` field holds what has been decided so
  far, and it grows until the type is settled.

A pending type is not a license to ignore it. It is a record of what is still
owed, in the one place someone will look.

## How a type is enforced

Each entry carries an `enforcement` value, chosen by the tree in
[`writing-a-rule.md`](writing-a-rule.md). The short version is that a rule a
script can decide should be a script, because prose costs tokens every time an
agent loads it and a gate costs none.

- **Deterministic** means a script decides it, and the entry names the gate.
- **Hybrid** means a script checks the shape and a person judges the content.
- **Inferred** means there is nothing to check, and the rule is prose.

## Adding a type

Add the entry to `tools/document_types.yaml` first, with whatever is already
ruled. Then write the document. `status: pending` is the usual answer at that
point, because a type invented this minute has no agreed rules yet. But the
status says what is true, not what stage the entry is at, so a type whose rule
file is already written and named goes in `settled`. A type invented while
writing its first document is a type shaped by that one document, and the second
one never fits it.

Two things to get right before adding an entry. Check that the thing really is a
new type rather than an existing one used loosely. A research note that reads
like a design note is usually a research note written badly. And write the
`dies` answer even when it is "never", because "never" is a decision and a blank
is an oversight.

## Templates

A type's template lives beside it in `docs/agents/document-templates/`, named
for the type. A pending type may not have one yet. The registry's `template:`
says which types do, and the gate refuses a `template:` naming a file nobody
wrote. A rule names its template, never a live document: a document cited as an
example drifts, and then the rule and its example disagree.

## What this file does not decide

- **What each settled type's rules are.** The entry names the file that owns
  them: [`adr-format.md`](adr-format.md) for ADRs, [`diagramming.md`](diagramming.md)
  for diagrams, [`skill-overrides.md`](skill-overrides.md) for skills.
- **How to choose between deterministic, hybrid and inferred.**
  [`writing-a-rule.md`](writing-a-rule.md).
- **Where a rule about the tracker lives.** [`issue-tracker.md`](issue-tracker.md).
