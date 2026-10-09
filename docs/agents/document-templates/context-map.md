# Context map: <Project>

Use this when a repo or a set of repos holds more than one context, each with its
own vocabulary. Copy to `CONTEXT-MAP.md` at the root of the repo that owns the
map. A repo with one context does not need it.

Template starts below the line.

# <Project> context map

## Contexts

- [<Context A>](<path>/CONTEXT.md): <what it owns, in one line>
- [<Context B>](<path>/CONTEXT.md): <what it owns, in one line>

## Relationships

- **A -> B**: <what crosses the line, and which side owns it>
- **A <-> B**: <shared terms, and who defines them>

## How words cross

State how a term moves between contexts: copied with recorded provenance,
translated at a seam, or never shared. A word with one meaning in two contexts
is a collision, and the map says which context wins.
