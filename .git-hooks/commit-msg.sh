#!/bin/bash
#
# Refuses a commit message whose Co-Authored-By trailer has no real address.
#
# **A screen can hide an address behind a placeholder, and a copy of the screen
# then carries the placeholder into history.** A trailer reading
# `Co-Authored-By: Name <[REDACTED...]>` credits nobody and cannot be fixed
# without rewriting the commit. This gate looks for any Co-Authored-By trailer
# whose angle brackets do not hold something shaped like an address.
#
# Called by `commit-msg` with the message file as its first argument. Build the
# address from parts if a tool keeps mangling it:
#     printf 'Co-Authored-By: Name <noreply%sexample.com>' '@'

set -uo pipefail

msg="${1:-}"
[ -f "$msg" ] || exit 0

bad=0
while IFS= read -r line; do
    case "$line" in
        [Cc]o-[Aa]uthored-[Bb]y:*)
            email="${line#*<}"
            email="${email%%>*}"
            if ! [[ "$email" =~ ^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]+$ ]]; then
                echo "    Blocked: this trailer has no real address: $line"
                bad=1
            fi
            ;;
    esac
done < "$msg"

if [ "$bad" -eq 1 ]; then
    echo "    A placeholder was copied from a screen. Write the address in full,"
    echo "    or build it with printf so nothing can rewrite it."
    exit 1
fi
exit 0
