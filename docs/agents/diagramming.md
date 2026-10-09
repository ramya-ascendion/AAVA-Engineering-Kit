# Diagramming standard

Every diagram in this repo makes two decisions, and they are independent.

1. **Which notation.** Six types, drawn from UML, C4, BPMN and ER. Picked by the
   question the diagram answers. Always written as Mermaid.
2. **How it gets rendered.** `mmdc` by default. Hand-drawn SVG when Mermaid's
   auto-layout makes a mess of it.

The notation is the foundation, and it is not negotiable. A reader who knows
`sequenceDiagram` or crow's foot should recognize what they are looking at. The
renderer is a quality decision, and hand-drawing is allowed for any of the six
types, not just some of them.

**The Mermaid source is committed for every diagram, hand-drawn ones included.**
It is what anyone edits, diffs, or reads on a harness that renders Mermaid
natively. A hand-drawn SVG overrides the layout, never the content.

Why a subset of several standards rather than one whole one: each of UML, C4,
BPMN and ER is good at one kind of question (order, structure, ownership,
records), and none is good at all of them. Taking the part of each that answers
one question keeps every diagram recognizable to someone who knows the standard
and light enough to draw in Mermaid.

## When to draw one

Draw one by default, and do not ask first. If the thing being explained has a
shape (a path something travels, an order things happen in, a set of states, a
set of relationships), the picture is the explanation and the prose is the note
underneath it. The table in section 1 doubles as the trigger list: if what you
are describing fits one of those six rows, it gets a diagram.

Two cases where it does not.

- **Three steps or fewer in a straight line.** A short list reads faster than a
  picture of a short list.
- **A claim with no shape.** "The retry loop is slow" is a sentence. There is
  nothing to lay out.

## 1 · Pick the notation from the question

**Figure:** what the reader needs to see picks one of six notations, each with
the Mermaid syntax that writes it. Source:
[`diagram-type-picker.mmd`](diagram-type-picker.mmd).

| The reader needs to see | Notation | Mermaid |
| --- | --- | --- |
| Which parts talk to what | C4 container level | `flowchart` |
| What happens in what order | UML sequence | `sequenceDiagram` |
| The states a thing moves through | UML state machine | `stateDiagram-v2` |
| Who owns each step | BPMN lanes | `flowchart` + one `subgraph` per lane |
| How records relate, and how many | ER crow's foot | `erDiagram` |
| Option A against option B | comparison | `flowchart` + one `subgraph` per option |

The last row is the weak one, and it is worth knowing why. No standard on this
list draws a *choice*. Each of them describes one system as it is. So a
comparison gets the nearest honest Mermaid form, one subgraph per option, and it
is the row that most often needs a hand-drawn layout to read well.

Four rules apply to all six.

- **Label every arrow.** `streams raw events` is information. A bare arrow means
  "related somehow", which the prose already said.
- **One figure, one claim.** The caption states the claim. If the picture
  needs two claims, it is two pictures.
- **Twelve boxes is the ceiling.** Past that, split it.
- **Hold one altitude.** This is the C4 rule, and it applies everywhere. A
  diagram mixing a queue, a Python class and a whole third party is three
  diagrams wearing one coat.

### Two Mermaid limits, both deliberate

These are notation limits, not layout ones. Hand-drawing does not fix either,
because the `.mmd` stays the record of what the diagram says.

- **Do not use `C4Context` or `C4Container` syntax.** It renders, but it has no
  layout engine: fixed positions, labels landing on boxes, hardcoded blue that
  ignores the theme. Use a plain `flowchart` and apply the C4 discipline by
  hand: name, technology, one line of purpose, one altitude.
- **Mermaid has no BPMN.** One `subgraph` per participant gets the lanes and the
  handoffs, which is the part that carries the meaning. The formal gateway and
  event symbols are not available, and a hand-drawn version does not get to
  invent them either.

## 2 · The style

The style is a project decision, made once and written down, so every diagram
matches wherever it appears. The kit fixes the roles, not the values.

### Color, and what each one means

Color carries meaning. Do not spend it on decoration. Pick these roles, and
write the values you chose in [`mermaid-theme.json`](mermaid-theme.json) so
every diagram reads from one place:

| Role | What it means in a diagram |
| --- | --- |
| In-scope color | The path being explained. One color, used for nothing else. |
| Gap color | A gap: the thing that does not exist or does not reach. One color, used for nothing else. |
| Failure color | A failure path. Optional. |
| Ground and surfaces | Page ground, figure ground, ordinary box fill, and the fill of the one box under discussion. |
| Text colors | Box titles, default arrows and secondary text, tertiary text. |

**Pick one in-scope color and one gap color, and document them in
`mermaid-theme.json`.** The in-scope and gap colors carry most of the meaning in
a repo's diagrams, and reusing either for anything else breaks every diagram
that came before. The default theme file in this kit uses a dark ground with one
accent for each of those two roles; change the values to suit, but keep the
roles.

### Type

Choose one sans family for titles and body, one monospace for tool and
identifier names, and one display face for the heading above a figure if you use
one. Set the sizes once: box title about 14 and semibold, box subtitle and list
lines about 11 to 12 and regular, identifiers about 13 to 14 in the monospace.

Explanatory sentences never go in the drawing. They go in the caption or the
notes under it.

### Shapes and arrows

- Corner radius `rx="10"`. Stroke width `1.5`, or `2` for the one emphasised edge.
- An ordinary box, an in-scope box (in-scope stroke at about 45% opacity), and
  the box under discussion (a lighter fill, in-scope stroke at about 70%) are
  three fills, so the eye finds the subject first.
- Group container: no fill, stroke at about 20% opacity.
- Dashed means "not built" or "not the normal path": `stroke-dasharray="5 4"`.
- One arrowhead marker per color, never an image:

```svg
<marker id="ar" viewBox="0 0 10 10" refX="9" refY="5"
        markerWidth="7" markerHeight="7" orient="auto-start-reverse">
  <path d="M0 0 L10 5 L0 10 z" fill="currentColor"/>
</marker>
```

### The figure wrapper

Wrap a hand-drawn SVG in a figure with a rule above the caption, and let the SVG
scroll sideways in a narrow viewport rather than shrink its text.

Give every `<svg>` `role="img"` and an `aria-label` that carries the same claim
the caption does, in full sentences. A reader who cannot see the picture should
get the mechanism, not the word "diagram".

## 3 · How to render

**Figure:** two routes from one Mermaid source to a committed png: `mmdc` for
most diagrams, and a hand-drawn svg that overrides the layout when auto-layout
fails. Source: [`diagram-render-pipeline.mmd`](diagram-render-pipeline.mmd).

Both routes start at the same committed `.mmd` and end at a committed `.png`.
The PNG exists because Markdown viewers often do not render Mermaid; the `.mmd`
exists because it is the thing a person edits. The kit ships the `.mmd` sources;
render the PNGs in your own repo.

### Where the files go

**A diagram lives in a file in the repo. Never only in a chat reply.** Most chat
views do not render Mermaid, so a fenced `mermaid` block in an answer is a wall
of text that nobody reads. Write the `.mmd`, render the `.png` next to it,
embed the `.png` from a Markdown file, and tell the reader the path to that
file. That is the whole delivery.

Give the embedded image real alt text: the same claim the caption carries, in a
full sentence. `![diagram]` helps nobody.

When `mmdc` renders a Markdown file holding more than one diagram, it numbers
the output `name-1.png`, `name-2.png`, and so on. Rename each one for what it
shows before committing. `ticket-lifecycle-states.png` tells the next person
what they are about to open. `ticket-lifecycle-2.png` does not.

### The default route

The palette lives in [`mermaid-theme.json`](mermaid-theme.json). Pass it to
`mmdc` and the six notations come out in the house style:

```bash
mmdc -i docs/agents/my-diagram.mmd -o docs/agents/my-diagram.png -c docs/agents/mermaid-theme.json -b '#0F1622' -s 2
```

The `-b` background should match your theme's figure ground.

- **Accent inside a Mermaid diagram with `classDef`,** not by hand-editing the
  output, or the next render throws your edit away. Use your in-scope and gap
  colors:

  ```
  classDef inScope fill:#0F1622,stroke:#34E0B4,stroke-width:1.5px,color:#E9F1F9
  classDef gap fill:#1A2638,stroke:#FFC53D,stroke-width:1.5px,color:#E9F1F9
  ```

  The two lines above are the kit's default values. Replace the hex values with
  your own palette, in `mermaid-theme.json` and in every `classDef`.

- **Mermaid draws square corners.** It exposes no corner radius, so its boxes
  are squarer than a hand-drawn one. Not a reason to hand-draw on its own.

### When to hand-draw instead

Hand-drawing is a **layout** decision. Reach for it when `mmdc` produces
something a reader has to work at, not because you would enjoy the control:

- Arrows crossing each other, or crossing a box
- A label landing on top of an edge or a node
- Large dead space that pushes related boxes far apart
- Lanes or subgraphs that come out in a confusing order
- A comparison, where the two options need to sit side by side to be compared

Everything else stays on the default route. A diagram that renders cleanly does
not get hand-drawn just to look bespoke.

### The rule that keeps the two in step

**The `.mmd` owns the content. The `.svg` owns only the layout.** Every box,
every arrow, and every label in a hand-drawn SVG must match the `.mmd` exactly.
If the diagram needs a new box, it goes in the `.mmd` first.

Two things make that survivable:

- **Mark the `.mmd`** with a comment on line one, so nobody re-renders over a
  hand-drawn image:

  ```
  %% layout: hand-drawn in my-diagram.svg — mmdc output is not the committed png
  ```

- **Commit all three files** (`.mmd`, `.svg`, `.png`) next to each other. A
  `.svg` sitting beside a `.mmd` is the signal that this diagram's PNG does not
  come from `mmdc`.
- **The `.mmd` still has to parse.** A hand-drawn diagram's source is not
  decoration. It is the notation, and notation that does not compile is prose.
  Check it before committing:

  ```bash
  mmdc -i docs/agents/my-diagram.mmd -o /tmp/parse-check.png -c docs/agents/mermaid-theme.json
  ```

Hand-drawn SVGs need a real browser to render, because they name web fonts that
`rsvg-convert` cannot fetch. Follow [`render-diagrams.mjs`](render-diagrams.mjs).

## One thing this style does not do

The default theme is dark only. There is no light palette, so a diagram dropped
into a light-themed page will not adapt: it will stay dark against a light
ground.

If a diagram has to work in both themes, draw it with `currentColor` for strokes
and text instead of hex values, and keep the in-scope and gap colors as the only
literal colors.
