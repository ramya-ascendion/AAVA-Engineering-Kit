#!/bin/bash
# The cross-file duplicate-code check, over a file set that does not move.
#
# **Why this runs at push rather than at commit with the rest of pylint.**
# Duplicate-code is the one pylint check whose answer depends on which files are
# in the run, and a commit's file set is whatever it happened to stage. At push
# the set is every tracked `.py`, so the answer is stable. Why the exempt list
# holds pairs rather than paths is written at the top of `duplicate-code-exempt`.
#
# One pylint call, over every tracked `.py` outside `vendor/`, with only
# `duplicate-code` enabled. One call rather than the two `pre-commit` makes, so
# a test file and a source file are compared too.
#
# Only for `KIT_STACK=python`; `pre-push` decides that, not this script.

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
EXEMPT="$HERE/duplicate-code-exempt"

if ! command -v pylint >/dev/null 2>&1; then
    echo "    FAILED — pylint is not installed, so nothing here can check this"
    echo "    push. Run ./setup-dev-env.sh."
    exit 1
fi

files=()
while IFS= read -r one; do
    case "$one" in
        vendor/*) continue ;;
    esac
    [ -n "$one" ] && files+=("$one")
done < <(git ls-files '*.py')

# **A guard, not a formality.** Pylint with no files to lint is a usage error,
# and a usage error exits non-zero — so without this a tree holding no tracked
# Python would refuse every push, for a reason nobody could act on.
if [ ${#files[@]} -eq 0 ]; then
    echo "    NOT RUN — this tree tracks no Python outside vendor/."
    exit 0
fi

report="$(pylint --disable=all --enable=duplicate-code "${files[@]}" 2>&1)"
pylint_said=$?

# **Pylint's own exit code, checked before its output is read.** It is a
# bitfield: 0 is a clean run and 8 is "a refactor message was issued", which is
# the only message this run can produce. Anything else — 1 fatal, 32 usage
# error, a broken rcfile — means the run did not happen, and a run that did not
# happen prints no `R0801` block. Without this the filter below would find
# nothing, report nothing, and the gate would say `ok` having measured nothing.
# That is the `broken` result the guarantee check names, and it is worse than a
# failure because it looks like a pass.
case "$pylint_said" in
    0 | 8) ;;
    *)
        echo "    FAILED — pylint exited $pylint_said, so nothing was compared."
        printf '%s\n' "$report" | sed 's/^/      /'
        exit 1
        ;;
esac

# Pylint prints one `R0801` line, then one `==module:[start:end]` line per side,
# then the shared code, then a line ending `(duplicate-code)`. A finding is that
# whole block, and the pair of module names is what the exempt list matches —
# in either order, so a list entry does not depend on which side pylint printed
# first.
printf '%s\n' "$report" | awk -v exempt_file="$EXEMPT" '
# One spelling of a pair, whichever order it was written in. Pylint decides
# which side it prints first and a person writing an exempt entry cannot know
# which that will be, so both ends sort the same way before they are compared.
function pair_key(one, two) {
    return (one < two) ? one " " two : two " " one
}
BEGIN {
    while ((getline line < exempt_file) > 0) {
        sub(/#.*$/, "", line)
        # `named` is rebuilt per line rather than reused, and the counter is
        # not called `found` — awk has one global namespace, and an earlier
        # version of this shared that name with the findings counter below, so
        # parsing a two-word entry left the gate reporting two findings it had
        # never seen.
        how_many = split(line, word, /[[:space:]]+/)
        named[1] = named[2] = ""
        kept = 0
        for (i = 1; i <= how_many; i++)
            if (word[i] != "" && kept < 2) named[++kept] = word[i]
        if (kept == 2) exempt[pair_key(named[1], named[2])] = 1
    }
}
/R0801: Similar lines/ { open = 1; block = $0 "\n"; sides = 0; next }
open && /^==/ {
    name = $0
    sub(/^==/, "", name)
    sub(/:.*$/, "", name)
    side[++sides] = name
    block = block $0 "\n"
    next
}
open {
    block = block $0 "\n"
    if ($0 ~ /\(duplicate-code\)[[:space:]]*$/) {
        # **Two sides, because that is all pylint reports.** Its similarity
        # checker pairs files off, so a finding names exactly two. If that ever
        # changes, a finding naming three would be keyed on its first two and
        # could match an exempt entry it was never meant to, so the count is
        # checked rather than assumed.
        if (sides != 2) { printf "%s", block; found++ }
        else if (pair_key(side[1], side[2]) in exempt) { let_through++ }
        else { printf "%s", block; found++ }
        open = 0
    }
    next
}
END {
    if (let_through > 0)
        printf "    %d pair(s) let through by duplicate-code-exempt.\n", let_through
    if (found > 0) {
        printf "    %d duplicate-code finding(s). Extract the shared part, or\n", found
        print  "    add the pair to duplicate-code-exempt with a reason."
        exit 1
    }
}
'
exit "${PIPESTATUS[1]}"
