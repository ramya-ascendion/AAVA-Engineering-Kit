# How to use the Aurora Kit

This guide is for an engineer who has been told "this project uses the kit" and wants to know what that changes. It covers installing the kit, the daily flow, and what each gate means. For fixing a problem, see the [runbook](runbook.md).

## What the kit is

The kit is one baseline for how AES 2.0, AES 3.0 and the Activation Control Plane are designed, built and gated. It carries the method (design before tickets, tickets before code), the skills that drive that method, the git hooks and CI gates that enforce it, and the document templates. It carries no product knowledge. Each project keeps its own `CONTEXT.md` and decision records.

Four things come with an install:

- `AGENTS.md` and `CLAUDE.md`: the writing standard and twelve hard rules. Claude Code reads `AGENTS.md` through `CLAUDE.md`.
- `.agents/skills/` and `.claude/skills/`: the skills, as real files (no symlinks, so Windows works).
- `.git-hooks/`: the gates that run on commit, on commit message and on push.
- `tools/` and `docs/agents/`: the gate scripts and the one-rule-per-file conventions.

## What the kit builds on: Matt Pocock's skills

The kit's skills are not written from scratch. It starts from the public `mattpocock/skills` collection (MIT licensed) and adds what a team with a ticket board, a review step and gates needs on top.

**What is borrowed.** 23 upstream skills are copied unchanged into `vendor/mattpocock-skills/`, with upstream's license beside them. Their content hashes are recorded in `skills-lock.json`. The kit never edits these files, because an edited copy is a fork that conflicts on every update. The `skill-mirror` gate refuses a working copy in `.agents/skills/` that differs from its vendored original. The originals themselves are protected by the rule and by review: nothing in the kit compares them to upstream, so use the hashes in `skills-lock.json` when you update.

**What the kit adds.** Four layers, in the order the kit prefers them:

1. **Config instead of edits.** The upstream skills read per-repo files by design. The kit supplies them: `docs/agents/issue-tracker.md` (local, GitHub or Jira), `triage-labels.md`, `domain.md` and the ADR rules. Most behaviour changes stop here.
2. **Wrappers, named `aes-*`.** Where config cannot reach, the kit writes a thin skill that says "read the upstream skill first, then these corrections win". The upstream name is then unregistered so the bare skill cannot be run by accident.
3. **Reader-only rules.** Some upstream skills never open a kit doc, so the rule is written where the agent will see it. Examples: `to-tickets` gets a link pass against existing board work, and `domain-modeling` gets extra ADR rules.
4. **Skills with no upstream parent.** Written for the kit.

| Upstream skill | Kit skill | What the kit changes |
| --- | --- | --- |
| `implement` | `aes-implement` | The whole board lifecycle: model check, claim the ticket, plan approval, acceptance-criteria check, ask before opening the PR, then move to In Review. |
| `implement-spec` | `aes-implement-spec` | One Epic in parallel: a branch and PR per ticket, a fix-version ceiling, stacked branches. |
| `grilling` | `aes-grilling` | One question per round, under three lines, with a recommendation and runner-up, a scope check each round, answers recorded on the ticket, and a self-grill mode with no human. |
| `ask-matt` | `aes-ask` | Routes to the kit's skills instead of the bare names, and uses whichever tracker `KIT_TRACKER` names. |
| `triage` | `aes-triage` | Maps triage roles onto the kit's labels and calls `aes-grilling`. |
| `wayfinder`, `grill-me`, `grill-with-docs`, `improve-codebase-architecture` | `aes-` plus the same name | Each calls `aes-grilling` instead of the bare grilling skill. |
| `writing-for-agents` | `aes-writing-for-agents` | American spelling, defined terms, prohibitions kept as prohibitions. |
| `code-review` | none (config only) | Runs twice per ticket: once inside `aes-implement`, once by the reviewer against the PR. |

Thirteen upstream skills are used as they are: `tdd`, `research`, `to-spec`, `to-tickets`, `domain-modeling`, `codebase-design`, `diagnosing-bugs`, `prototype`, `handoff`, `teach`, `to-questionnaire`, `code-review` and `setup-matt-pocock-skills`. The last one is for installing upstream's own setup, and a project rarely needs it.

**Skills with no upstream parent**, written for the kit:

- `aes-second-opinion-design`, `aes-second-opinion-to-tickets` and `aes-second-opinion-review`: a separate headless Claude reviews a design, a ticket breakdown or a diff, and the work is revised until it passes.
- `aes-work-the-path`: works the delivery critical path ticket by ticket.
- `aes-work-the-review`: walks a ticket's review route and comments the result on the ticket.

**Around the skills, the kit adds** everything that makes them enforceable rather than advisory: the git hooks and CI gates, the document types and templates, the ticket state rules, the worktree rules, and the update recipe in `docs/agents/skill-overrides.md` for pulling a newer upstream without losing the wrappers. To see exactly what differs from upstream, read the "Current overrides" table in that file.

The 20 `aurora-*` skills are a separate thing: they come from another internal project, are kept byte for byte for reference, and are not part of the Matt Pocock set. `PROVENANCE.md` has the full account.

## Before you start

You need these on your machine. On Windows, run everything in Git Bash.

- Git and Git Bash.
- Python 3.12, for the document-structure gate and for the kit's own tests.
- Node, only if the project's test command uses it (AES 2.0 does).
- gitleaks, for the secret scan. winget installs it but does not put it on the Git Bash path.
- The Claude Code CLI, only for the second-opinion skills.

In Git Bash, put the tools on the path in the shell that runs `git commit`:

```bash
export PATH="$PATH:/c/Program Files/nodejs:$HOME/AppData/Local/Microsoft/WinGet/Links"
```

A missing tool is never skipped quietly. The hook prints FAILED and names it.

## Install the kit into a project

Always dry-run first. The installer never overwrites a file that already exists, and it lists what it skipped.

```bash
cd aes-engineering-kit
bin/install-kit <target-dir> aes-2.0 --dry-run
bin/install-kit <target-dir> aes-2.0
```

The overlay is one of `aes-2.0`, `aes-3.0` or `activations`.

Then, in the target project:

1. Open `.kit/config.env` and check every setting. Lines marked `TODO: confirm` are guesses.
2. Fill in `CONTEXT.md` if the installer said it is still the template. Do this before the first design document.
3. Point git at the kit's hooks with `bash setup-dev-env.sh`. This sets `core.hooksPath`, which every worktree of the repo shares, so tell anyone else working in the repo first.
4. Commit the installed files in one commit of their own.

Until step 3 is done, run the gates by hand: `bash .git-hooks/pre-commit`.

## The settings that matter

All per-project settings live in `.kit/config.env`. The hooks and the Python tools read the same file.

| Setting | What it decides |
| --- | --- |
| `KIT_STACK` | `node`, `python` or `none`. The Python gates (lint, types, layering, coverage) run only for `python` and say NOT RUN otherwise. |
| `KIT_TRACKER` | Where tickets live: `local`, `github` or `jira`. |
| `KIT_TICKET_PREFIX` | The key prefix in branches and commits, such as `AES-12`. |
| `KIT_DEFAULT_BRANCH`, `KIT_PROTECTED_BRANCHES` | Branches a direct commit is refused on. |
| `KIT_TEST_CMD`, `KIT_TEST_DIRS` | The command the commit gate runs, and the paths that trigger it. |
| `KIT_SPELLING_LOCALE` | `american` or `none`. |
| `KIT_SKILL_LAYOUT` | Keep `copy` on Windows. |

## The daily flow

The method is: design, then tickets, then code, then review. The skills carry you through it. When you are unsure which to use, run `/aes-ask` and describe the situation.

1. Work on a branch or worktree, never on the default branch. The `protected-branch` gate refuses a direct commit.
2. Design. Use `/aes-grill-with-docs` to sharpen the idea and record decisions and terms as you go. Write the design document from the template in `docs/agents/document-templates/`. For work too big for one session, use `/aes-wayfinder`.
3. Tickets. Break the design into small tickets. With `KIT_TRACKER=local` each ticket is a file at `.scratch/<feature>/issues/<KEY>.md`, copied from `docs/agents/document-templates/ticket.md`. These files are tracked state: commit them with the work.
4. Build. `/aes-implement` takes one ticket (claim it, agree a plan, build test-first, check off the acceptance criteria). `/aes-implement-spec` does a whole Epic in parallel worktrees. `/aes-work-the-path` works the critical path ticket by ticket.
5. Commit. The hook runs the gates on every commit (next section). Use conventional commit subjects where the project says so, and the ticket key in the form the project's `AGENTS.md` states.
6. Second opinion. `/aes-second-opinion-review` hands your work to a separate headless Claude (`claude -p`) to walk a review route and report. Fix what is real. `/aes-work-the-review` walks a route and comments the result on the ticket.
7. Move the ticket to In Review when the work is done and a person has to look. With no pull request, "In Review" means the same: name the commit range in a comment.
8. A person reviews, then merges. The kit never merges for you.

With no human to answer questions (a scheduled run or a subagent), `/aes-grilling` switches to self-grill: it answers from the code, labels each guess as an assumption, and writes them into the design doc so a person can overturn them.

## What the gates check

A commit or push from a worktree runs the same gates as one from the main checkout. Skipping them with `--no-verify` is for a change that touches nothing the gates look at.

| Gate | Refuses when |
| --- | --- |
| protected-branch | You commit directly on a protected branch. |
| skill-mirror | A skill in `.claude/skills/` differs from `.agents/skills/`, or a vendored skill was edited. Fix: `bash bin/sync-skills`. |
| doc-structure | A doc in `docs/agents/` is unreachable from `AGENTS.md`, a link breaks, a registry path is missing, or a file under `docs/` belongs to no document type. |
| secrets (gitleaks) | A staged change looks like a credential. |
| spelling | A word breaks the locale, when the locale is not `none`. |
| tests | A staged path could change a test and the project's test command fails. |
| commit-msg | A `Co-Authored-By` trailer has no real email address (a placeholder was copied from a screen). |
| pre-push | The slower whole-tree checks, such as duplicate code, fail. |

Every gate prints one of ok, FAILED or NOT RUN with the reason. NOT RUN is an honest statement, not a pass.

## What has and has not been proven

Verified in this work on Windows 11:

- The kit's own suite: 357 tests pass, 1 skipped.
- The kit installed into AES 2.0, with all gates passing and 4358 of 4358 unit tests.
- One feature (the governance coverage map) taken through design, five local tickets, test-first build, two review rounds by a headless Claude and a dry-run PR description.

Not verified:

- The Jira and GitHub trackers. Only `local` was run end to end.
- Linux CI. The lock file was built to work there but never ran on a runner.
- Codex and other harnesses. Only the Claude Code path has been traced.
