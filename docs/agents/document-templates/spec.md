# Specification: <NN - Title>

Copy to `specifications/NN-name.md` or `docs/specs/NN-name.md`. One spec per
slice. It records what was built, so it is never deleted.

Template starts below the line.

# NN - <Title>

**Slice Epic**: <tracker link or key>

Assembled <date> for <epic> from <the design notes, ADRs and decisions it draws on>.

Vocabulary: see `CONTEXT.md` (or `GLOSSARY.md`). Use its terms exactly.

**Done means**: <one sentence a person could check.>

## What a person can do when this is finished

<The demonstrable ability, in plain words. A slice is named for this, not for a
layer or a component.>

## Problem statement

<Who has what problem, and what it costs them today.>

## Solution

<The approach, in a few short paragraphs. Decision first, backstory after.>

## The scenarios

<Each scenario in full: start state, the action, the observable result. Number
them `NNN-short-name`, and use that one id everywhere.>

## User stories

### <Story title>

As a <named role>, I can <do something>, so that <outcome>. From <ticket>.

Acceptance criteria:

- <checkable statement>
- <checkable statement>
- Hard-zero failure class: <what must never happen, however good the average is>

## Implementation decisions

- <A decision that is settled, with a link to the ADR that owns it.>

## Existing code to build on

- <The tests and modules in this repo that a new test should copy.>
