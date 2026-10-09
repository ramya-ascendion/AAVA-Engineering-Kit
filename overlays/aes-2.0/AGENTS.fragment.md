## AAVA-AES-2.0

The working Autonomous Engineering Studio: a VS Code extension and a browser studio served by one Node-stdlib server on port 7420, with no build step. It is the governance and promotion layer around AAVA, not a second coding agent. Vocabulary is in `CONTEXT.md`.

How work is done here, taken from the repo as it is:

- Commits are conventional: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, with an optional scope, so the subject carries no ticket key. The key (`AES-n`, tickets are local files under `.scratch/`) goes on its own `Ticket: AES-n` line in the body. This overrides the subject-line rule in `docs/agents/git-conventions.md`.
- Each piece of work gets its own branch or worktree, named `worktree-<slug>`. A direct commit to `master` is refused by the `protected-branch` gate.
- The tracker is `docs/PENDING-BRANCHES.md`: one section per branch, with what, why isolated, status and what is not done. Update it when a branch merges.
- The commit gate runs `node tools/unit.js`, which also runs the adapter and Portable suites. CI runs the same command.
- `node tools/e2e.js` writes to the live AAVA realm. It is never part of a gate. Run only `--only portable` or `--only-mentor`.
- Secrets: the repo's own `.gitleaks.toml` rules (Azure keys, SAS URLs, bearer tokens) are used by the kit's secret gate, and `tools/scan-secrets.js` still audits `data/`.
- A server-side merge needs a restart of the studio on port 7420 before anyone tests it. Probe a scratch server on another port, never the live one.
- One of three parallel lines with AAES-3.0 and the Activation Control Plane. Code moves between lines by copy with recorded provenance, one way, never by import.

Hook handover, to be done by a person once: this repo has two hook folders today. `.githooks/pre-commit` (gitleaks) is the active one, and `hooks/pre-commit` (branch protection) is opt-in and unused. The kit's `.git-hooks/` does both jobs, so after comparing, point `core.hooksPath` at `.git-hooks` and retire the other two.
