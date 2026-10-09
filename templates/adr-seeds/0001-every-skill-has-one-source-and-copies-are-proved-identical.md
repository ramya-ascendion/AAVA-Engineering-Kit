---
status: accepted (baseline)
---

# Every skill has one source, and every other copy is proved identical

Skills we write live in `.agents/skills/`. Borrowed skills live pristine under `vendor/`. `.claude/skills/` and the borrowed entries in `.agents/skills/` are generated from those sources, either as links (`KIT_SKILL_LAYOUT="link"`) or as real files (`"copy"`, the default).

## Why

Two copies that differ mean each harness reads a different skill. A link has one copy, but it needs symlink rights on Windows, is stored as a text file by a clone without them, and shows as empty in many viewers. Real files work everywhere, so the copy layout adds a gate that proves them byte-identical instead.

## Consequences

- A skill's `name:` field equals its directory name.
- Behavior changes to a borrowed skill go in a wrapper skill, never in the vendored file.
- `bin/sync-skills` regenerates every copy. Nobody edits a copy by hand.
- The `skill-mirror` gate checks the layout on every commit that touches either tree.
