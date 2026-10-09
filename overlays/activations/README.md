# Overlay: activations

Existing `CLAUDE.md` and `CONTEXT.md` are kept. The installer appends `@AGENTS.md` to `CLAUDE.md` instead of replacing it.

Files here:

- `config.env` is copied to `.kit/config.env` when that file is absent.
- `AGENTS.fragment.md` is added to the target's `AGENTS.md` between kit markers.

Every fact here comes from the project's own `CONTEXT.md`, README or ADRs. Anything marked `TODO: confirm` has not been verified.
