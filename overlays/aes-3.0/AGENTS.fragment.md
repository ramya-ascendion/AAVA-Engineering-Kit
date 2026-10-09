## AAES-3.0

The Claude-core line: one codebase, four profiles, TypeScript on Node, one command bus. Vocabulary is in `CONTEXT.md` and `CONTEXT-MAP.md`. Decisions are in `docs/adr/`.

- This is one of three parallel lines with AAVA-AES-2.0 and the Activation Control Plane. Code carried over from AES 2.0 is copied with recorded provenance (source repo and commit), one way, never imported.
- New work in this line is new files only, so a carry-over never edits a file another line owns.
- `TODO: confirm` the test command and package layout once the first code lands, then set `KIT_TEST_CMD` in `.kit/config.env`.
