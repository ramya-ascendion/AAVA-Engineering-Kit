# Overlay: aes-2.0

Existing `CONTEXT.md`, `hooks/pre-commit` and `tools/` are kept. The installer skips any file that already exists.

Files here:

- `config.env` is copied to `.kit/config.env` when that file is absent.
- `AGENTS.fragment.md` is added to the target's `AGENTS.md` between kit markers.

Every fact here comes from the project's own `CONTEXT.md`, README or ADRs. Anything marked `TODO: confirm` has not been verified.
