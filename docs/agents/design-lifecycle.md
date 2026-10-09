# The design lifecycle

The phases before an implementation ticket exists: wayfinding, `/to-spec`,
`/to-tickets`. [`ticket-lifecycle.md`](ticket-lifecycle.md) covers everything
after: what happens once a Story, Task, or Bug is in hand. This file is the
phases that produce one.

## Model tiers

Two tiers are named below, and the project records which concrete models fill
them in `AGENTS.md`, because the names change faster than this file should.

- **Strongest model** is the most capable model you can run. Settling a scope
  or a design is where a wrong answer costs the most, so it gets this tier.
- **Fast model** is the capable, faster and cheaper tier. Turning an agreed
  design into specs, tickets and code is well-bounded work, so it runs here.

The effort levels are the reasoning-effort settings of the harness: Medium,
High, Extra. The table is a recommendation, not a gate. The one place a check
is made is the model-and-effort question at the start of `/aes-implement`
([`ticket-states.md`](ticket-states.md), step 2). Other harnesses can add a
column to the table with their own recommendations rather than assuming one
harness runs every phase forever.

## The phases

| Phase | Skill | Produces | Model | Effort |
| --- | --- | --- | --- | --- |
| Chart the way | `/aes-wayfinder` | An ADR and a map | Strongest | Extra |
| | `/artifact-diagramming` | A conceptual diagram, the whole project | Strongest | Medium |
| Write the spec | `/to-spec` | Project Epics: user stories, implementation decisions | Fast | High |
| | `/artifact-diagramming` | An Epic diagram, for planning | Fast | Medium |
| Break it into tickets | `/to-tickets` | Tasks and Stories: what to build, acceptance criteria, blocker links | Fast | High |
| | `/artifact-diagramming` | A Story diagram, verifying planning hasn't drifted | Fast | Medium |

`/to-spec` asks for "prior art for the tests". Title that section **"Existing
code to build on"** and use those words in prose too. Prior art is a patent-law
term for earlier work that decides whether an invention is new, and it names the
wrong thing here: the section lists the tests and modules in this repo a new
test should copy. Earlier published papers are "published work".

**Figure:** two lanes, one per model tier, six phases from a loose idea to a
ticket ready to implement. In the strongest-model lane, wayfinding produces an
ADR and a map and a conceptual diagram follows. The flow crosses into the
fast-model lane, where to-spec produces Project Epics, an Epic diagram follows,
to-tickets produces Stories, and a Story diagram follows. Then it hands off to
the delivery lifecycle. Source:
[`design-lifecycle-phases.mmd`](design-lifecycle-phases.mmd).

Once `/to-tickets` produces a Story (or Task, or Bug), diagrammed or
deliberately not, it enters [`ticket-lifecycle.md`](ticket-lifecycle.md)'s flow.
This file's job ends there.

## The diagram is encouraged, not a gate

A diagram at the end of each phase is **strongly encouraged**, not a hard
requirement. Skip it when it genuinely wouldn't clarify anything for that
piece of work. Nothing here refuses to hand off the way the delivery
lifecycle's acceptance-criteria check does.

That said, a picture is the thing to draw before implementing, and early
wayfinder and grilling sessions tend to skip it anyway, because nothing written
down says to stop and draw one. This file is that.

**A diagram gets built two ways at once, not one instead of the other:**

- **Published as an Artifact** (via `/artifact-diagramming`), for review:
  something a person can look at and comment on before the phase is called
  done. Skip this half in a harness with no artifact tool.
- **Committed as `.mmd`** (and a rendered `.png`), per [`diagramming.md`](diagramming.md):
  the permanent record, sitting in the repo next to whatever it illustrates.

## Backfilling a ticket that skipped its diagram

Some tickets already sit past `/to-tickets` with no Story diagram, because this
file postdates them. There is no separate migration effort for that backlog.
Instead, `/aes-work-the-path` checks for a linked Story diagram before
implementing each ticket it walks to, and creates one on the spot if it's
missing. Old and new tickets get the same rule, applied lazily, the moment
work actually starts on one. See `.agents/skills/aes-work-the-path/SKILL.md`.
