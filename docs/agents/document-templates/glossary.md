# Glossary and context: <Context name>

Copy this to `CONTEXT.md` (or `GLOSSARY.md`) at the repo root. This project's
vocabulary lives in exactly one such file per context, and a repo with several
contexts adds a `CONTEXT-MAP.md` (see `context-map.md`). The `domain-modeling`
skill reads and writes it.

Template starts below the line.

# <Context name> Language

<One or two sentences: what this context is, who it is for, and what it is not.>

## Language

### <Group name>

**<Term>**:
<One or two sentences. Say what it IS, not what it does.>
_Avoid_: <words people use for it that this project does not>

**<Another term>**:
<Definition.>
_Avoid_: <words>

## Words we deliberately do not use

- **<Word>**: <why, and the term to use instead>

## Rules for this file

- Be opinionated. When several words exist for one concept, pick one and list
  the rest under `_Avoid_`. An `_Avoid_` word is banned in code, docs and tickets.
- Keep each definition to one or two sentences.
- Only terms specific to this context belong here, not general programming words.
- Group terms under subheadings when clusters form. A flat list is fine when
  they do not.
- A term is added when it is actually resolved, never in advance.
