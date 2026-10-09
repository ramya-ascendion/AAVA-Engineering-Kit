# Aurora Kit runbook

This runbook is for whoever installs, upgrades and maintains the kit. Each procedure lists its steps and how to tell it worked. The last section maps a symptom to a fix. For day-to-day use, see [how to use the kit](how-to-use.md).

All commands run in Git Bash from the kit repo unless a step says otherwise.

## 1. Install the kit into a project

Use when: a project has never had the kit.

1. Dry-run and read the output: `bin/install-kit <target> <overlay> --dry-run`.
2. Install: `bin/install-kit <target> <overlay>`.
3. Edit `<target>/.kit/config.env`. Confirm the stack, tracker, ticket prefix, protected branches and test command.
4. If the installer printed a note that `CONTEXT.md` is the unfilled template, fill it in. If the project already has its own `CONTEXT.md` elsewhere (for example untracked in another checkout), delete the seeded one so it cannot overwrite the real one on a merge.
5. Run the gates once by hand: `bash .git-hooks/pre-commit` in the target.
6. Commit the installed files in one commit.

Worked when: step 5 ends with "Pre-commit checks passed." and the Python gates say NOT RUN for a Node project.

Do not run `setup-dev-env.sh` in a repo that other people or sessions are using until they know. It changes `core.hooksPath` for every worktree.

## 2. Upgrade an installed project to a newer kit

Use when: the kit gained a fix and a project should have it.

1. Work on a branch or throwaway worktree of the project, not on its default branch.
2. Re-run the installer with `--force`: `bin/install-kit <target> <overlay> --force`. It overwrites kit-owned files with the kit's current copy.
3. Read `git diff` in the target. Only files you expect should change. The installer does not touch `.kit/config.env` or the block in `AGENTS.md`, so apply any new setting or text there by hand.
4. Run `bash .git-hooks/pre-commit`, then the project's own test command.
5. Commit as "upgrade the kit install" and merge the normal way.

Worked when: the diff shows only kit files, and every gate passes.

## 3. Run the kit's own tests

Use when: before any change to the kit is merged or pushed.

1. Make a virtual environment outside the repo, or in an ignored folder: `python -m venv <dir>`.
2. Install the pinned dependencies with hashes, one file at a time:
   - `<dir>/Scripts/python -m pip install --require-hashes -r tools/requirements-ci.txt`
   - `<dir>/Scripts/python -m pip install --require-hashes -r tools/requirements-test-ci.txt`
3. Run: `<dir>/Scripts/python -m pytest -q`.

Expect: 357 passed, 1 skipped. It takes 7 to 18 minutes. The skip is a platform test.

On Linux or macOS the interpreter is `<dir>/bin/python`.

## 4. Change the kit

Use when: editing a skill, a doc, a gate or an overlay.

1. Branch in the kit repo. Do not commit on `master` directly.
2. Edit a skill only under `.agents/skills/<name>/`, then run `bash bin/sync-skills` to copy it to `.claude/skills/`. Never edit vendored skills under `vendor/`; wrap them instead (`docs/agents/skill-overrides.md`).
3. A new document under `docs/` needs a type in `tools/document_types.yaml`. A project-only type goes in that overlay's `document_types.local.yaml`.
4. A new gate must be shown failing on a broken file and on empty input, with a test, before it merges (hard rule 6).
5. Run `bash bin/check-no-leaks`, then `python tools/doc_structure.py` with PyYAML installed, then the full tests from section 3.
6. Commit. Build the `Co-Authored-By` address with `printf` so no tool can replace it with a placeholder:
   `printf 'Co-Authored-By: Name <noreply%sexample.com>' '@'`

Worked when: leak check says clean, doc-structure says five ok lines, and the suite passes.

## 5. Regenerate the test lock file

Use when: raising a pinned version, or adding a test dependency.

1. Edit `tools/requirements-test.in` and pin each package with `==`.
2. Run:
   `uv pip compile tools/requirements-test.in --universal --generate-hashes --python-version 3.12 --no-header -o tools/requirements-test-ci.txt`
3. Restore the explanatory comment at the top of the lock file, then reinstall it as in section 3.

The `--universal` flag matters. A lock built for Linux only fails on Windows because pytest needs `colorama` there.

## 6. Add a project overlay

Use when: a fourth project needs the kit.

1. Copy an existing folder under `overlays/` and rename it.
2. Set `config.env`, the `AGENTS.fragment.md` text, and `gitignore.append`.
3. If the project has docs outside the generic types, add `document_types.local.yaml` with its types and any `allowed_paths:`.
4. Install into a scratch copy of the project with `--dry-run`, then for real, and run the gates.

## 7. Release (push) the kit

Use when: the tests pass and the owner has said to publish.

1. Confirm `master` is the commit you tested: `git log --oneline -1`.
2. Confirm no placeholder trailers: `git log --format=%B | grep -c REDACTED` prints 0.
3. Add the remote the owner gave you: `git remote add origin <url>`.
4. Ask the owner to confirm the push, then `git push -u origin master`.

A push publishes the code, and a later delete does not unpublish it. The kit has no remote today.

## 8. Roll back

- A bad kit commit not yet pushed: `git revert <sha>` on a branch, then merge it.
- A bad upgrade in a project: it was a branch, so drop the branch.
- A bad lock file: `git checkout <good-sha> -- tools/requirements-test-ci.txt tools/requirements-test.in`.

## 9. Symptom to fix

| Symptom | Cause | Fix |
| --- | --- | --- |
| Hook prints `FAILED` and names gitleaks | gitleaks is not on the Git Bash path | Export the WinGet links folder onto `PATH`, then retry. |
| Hook says node or python is missing | Same, for that tool | Export its folder onto `PATH`. |
| `pip` says every requirement needs `==` under `--require-hashes` | An old Linux-only lock | Pull the current lock (section 5), or regenerate it with `--universal`. |
| Crap-gate tests error with FileNotFoundError | `coverage` or `radon` not installed | Install `tools/requirements-test-ci.txt`; the current lock includes both. |
| doc-structure prints `matches no document type` | A doc sits in a folder no type claims | Add the folder to a type's `paths:` in `tools/document_types.local.yaml`, or move the file. |
| doc-structure prints `sits where no document may` | The file is in a forbidden path | Move it, or list it under `allowed_paths:` in the local registry. |
| The typed-docs check seems to do nothing | PyYAML is not installed in the Python the gate runs | Install PyYAML. Without it that one check is skipped. |
| commit-msg prints `this trailer has no real address` | A placeholder was pasted into the trailer | Rewrite the trailer; build it with `printf`. |
| Commit refused on `master` | protected-branch gate | Make a branch or worktree. |
| skill-mirror fails | `.claude/skills` drifted from `.agents/skills` | `bash bin/sync-skills`, then stage both. |
| Commit works but the kit gates did not run | `core.hooksPath` still points at the project's older hooks | Run `bash .git-hooks/pre-commit` by hand until the hook hand-over is done. |
| LF will be replaced by CRLF warnings | The machine has `core.autocrlf=true` | Harmless. Ignore them. |
| A second-opinion run cannot find a route or a PR | The project uses the local tracker | Use the local-tracker path in the skill: build the route from the commit range. |

## 10. Known limits

- The Jira and GitHub tracker paths were not run end to end.
- Linux CI is untested.
- Only the Claude Code harness path is traced. Codex and others read `AGENTS.md` but nothing proves their skills load.
- The pre-commit test gate runs the project's whole suite when a staged path could affect a test, so it can take over a minute on a small change.
