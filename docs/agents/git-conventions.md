# Git conventions: branches, commits, and PRs

The ticket key (`PROJ-123`, using `KIT_TICKET_PREFIX` from `.kit/config.env`)
is what ties git history to a ticket. Put it in the branch name, the commit
subject and the pull request title, and the history behind a ticket can be found
from the ticket and the ticket from the history.

How the link shows up depends on `KIT_TRACKER`:

- **`jira`**: the Jira site is connected to the git host. The connector links a
  branch, commit, or pull request to a ticket by finding the key in its name,
  message, or title, and shows everything it finds in the ticket's Development
  panel. Naming is only half of it. The repo also has to be connected on the
  Jira side, under the site's GitHub app settings. If the repo is not in the
  connector's list, the keys below are still correct and still link nothing.
- **`github`**: the key is the prefix plus the issue number (`PROJ-123` for
  issue 123). Add `Refs #123` on its own line in the commit body, and close the
  issue with `Closes #123` in the pull request body, never in a commit message.
  Only the pull request form lists the pull request as linked on the issue.
- **`local`**: nothing connects automatically. The key in the branch and
  commit is how a person finds the ticket file under `.scratch/`.

## When a project states its own form

A project's `AGENTS.md` may replace the commit rule below. A repo that already
uses conventional commits (`feat: ...`, `fix: ...`) keeps its subject lines and
puts the key on its own `Ticket: PROJ-123` line in the body instead. Where the
project's section says so, it wins over this file for the commit line only. The
branch and pull-request rules still apply unless it overrides those too. When
you override, say so in `AGENTS.md`, because a reader of this file alone cannot
tell.

## The rules

- **Branch**: put the ticket key in the branch name when the branch is created.
  Agent sessions use `claude/PROJ-123-short-slug`. Humans must include the key;
  the rest of the name is up to them. The key must be uppercase: `proj-123`
  is never detected.
- **Commit**: put the ticket key in the first line of the commit message.
  `Reject requests with no customer id (PROJ-123)` and `PROJ-123: reject
  requests with no customer id` both work.
- **Pull request**: put the ticket key in the PR title. A PR whose source
  branch carries the key also links, but the title is the seatbelt for when it
  does not.
- **Merge**: a squash merge writes one new commit on the default branch
  (`KIT_DEFAULT_BRANCH`). Keep the key in that commit's message, or the history
  there loses the link.

One branch serves one ticket. Work that spans several tickets gets several
branches, or its own umbrella ticket.

## Check it worked

Open the ticket and look for the linked branch, commit, or PR (the Development
panel in Jira, the linked pull requests on a GitHub issue). It shows up within a
minute or two. If it is empty after a keyed push, the problem is the connection,
not the name. Say so instead of renaming things.

## When there is no ticket

Create a branch without a key only when the work genuinely has no ticket. If a
ticket could exist in thirty seconds, create it first. `/aes-implement` fetches
the ticket before it writes code, so it always has the key in hand.

## Automated dependency-bump pull requests

**A dependency bot's pull request needs no ticket key.** This covers its branch,
its commit, its title, and the squash-merge commit, which keeps the bot's own
message. A version bump is routine upkeep that belongs to no ticket, so there
is nothing for a key to link to. The bot's config file (for example
`.github/dependabot.yml`) decides what it may propose.

A person who changes such a pull request by hand, beyond merging it, is
doing ticketed work, and the rules above apply to that change.

## Tracker commands in commit messages

Do not use the tracker's inline commands in commit messages: Jira's smart
commits (`#comment`, `#time`, `#transition`), or closing keywords such as
`Closes #123`. Agents talk to the tracker through its own tools, and two write
paths to one ticket is how statuses get fought over. Smart commits also only
work when the git author email matches a tracker account, which is not true for
agent-authored commits.
