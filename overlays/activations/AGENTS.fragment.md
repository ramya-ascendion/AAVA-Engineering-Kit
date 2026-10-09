## Activation Control Plane

A Claude-only system that governs Claude activations. The pack in `docs/` is written and no code exists yet. Vocabulary is in `CONTEXT.md`, and its `_Avoid_` words are banned here.

- Gates decide, models draft. No model output opens a Gate, records a Sign-off, moves a Value Status or changes a Control. Operators return Proposals only.
- Documents use headings and spacing, never horizontal rules. This rule is stricter than the kit baseline and wins here.
- Demo and fixture data carries the label "illustrative, not a real account". Customer data and credentials stay out of the repo.
- Any claim about what Anthropic's platform exposes comes from `docs/research/` only. Unverified means design intent.
- This directory is not yet a git repository. Run `git init` before installing the hooks.
- This is one of three parallel lines with AAVA-AES-2.0 and AAES-3.0. Code moves between lines by copy with recorded provenance, one way.
