#!/bin/bash
#
# Refuses a commit made directly on a protected branch.
#
# **Several sessions can work one repo at once, and a commit on the shared
# branch is easy to lose track of.** Work goes on its own branch or worktree.
# The gate is on only when `KIT_PROTECT_BRANCHES="yes"` in `.kit/config.env`,
# and the branches it protects are `KIT_PROTECTED_BRANCHES`, which falls back to
# `KIT_DEFAULT_BRANCH`, space separated.
#
# Not refused: the very first commit of a repository (there is no other branch
# to be on yet), and a detached HEAD. Bypass once with `git commit --no-verify`.

set -uo pipefail

# shellcheck source=.git-hooks/common.sh
source "$(dirname "$0")/common.sh"

[ "${KIT_PROTECT_BRANCHES:-no}" = "yes" ] || exit 0

# Symbolic-ref, not rev-parse --abbrev-ref, so it works before HEAD resolves.
current="$(git symbolic-ref --short HEAD 2>/dev/null)" || exit 0
git rev-parse --verify -q HEAD >/dev/null 2>&1 || exit 0

for protected in ${KIT_PROTECTED_BRANCHES:-$KIT_DEFAULT_BRANCH}; do
    if [ "$current" = "$protected" ]; then
        echo "    Blocked: direct commit to '$protected'."
        echo "    Other sessions may be working this repo, so put the work on its own branch or worktree:"
        echo "        git checkout -b my-feature-branch"
        echo "    (Bypass once, deliberately: git commit --no-verify)"
        exit 1
    fi
done
exit 0
