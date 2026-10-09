#!/bin/bash
#
# **The skills tree has one shape, and this gate reads the commit for it.**
#
# Every skill lives once, and `.claude/skills` only points at it. A skill the
# project wrote lives in `.agents/skills`. A borrowed skill lives pristine under
# `vendor/<source>/` — any directory under `vendor/` — with a link from
# `.agents/skills` to it. Each of those files carries a name and may carry
# companions, and the questions below are all one question asked of different
# parts of the same tree.
#
# Project conventions live in one harness-neutral place so engineers can bring
# their own AI tool, and `.claude/skills` is the Claude Code view of the same
# files. A link has one copy. A committed directory has two, and nothing keeps
# them equal — each harness then reads a different one.
#
# So it asks these of the commit, not the working tree. They are numbered so a
# refusal can be traced back to one of them, and no count is written down here,
# because a count drifts the moment a question is added.
#
#   1. Is every entry under `.claude/skills` a link?
#   2. Does each one point at `../../.agents/skills/<its own name>`?
#   3. Does that target actually exist in the commit?
#   4. Does every skill in `.agents/skills` have a link pointing back?
#   5. Does any name live in both `.agents/skills` and `vendor/` as real files?
#   6. Does each `SKILL.md`'s `name:` field match its directory? A rename that
#      moves the directory and forgets the field leaves a skill the harness
#      lists under one name and the repo files under another.
#   7. Is every companion file beside a `SKILL.md` named from its `SKILL.md`,
#      in backticks?
#   8. Is every companion file free of YAML frontmatter?
#
# **"A link" is three things on Windows, and the gate says which it found.**
#
#   symlink      git mode 120000. The normal case; the target is the blob.
#   plain-file   a mode-100644 file whose whole content is the relative link
#                target. This is what git writes for a link on a clone with
#                `core.symlinks=false`, and it is accepted ONLY there.
#   junction     an NTFS directory junction. It is accepted in the working tree,
#                where it resolves like a symlink, but git cannot store one: it
#                stages the directory behind it as a copy of every file. So a
#                junction that has been staged is reported as exactly that, with
#                the way out, rather than as an unexplained "committed copy".
#
# **It reads the index, not the disk.** `git cat-file -p :<path>` asks what is
# being committed. Checking the working tree would pass a commit that stages a
# copy while an untracked link sits beside it — the exact shape of the bug. The
# working tree is looked at once, afterwards, only to say which kind of link the
# project is using.
#
# It takes no arguments. The staged file list every other gate receives answers
# "what changed"; this asks "what shape is the skills tree", and the answer lives
# in the index either way.
#
# A tree with neither `.claude/skills` nor `.agents/skills` has no shape to
# check and passes, saying so.

set -uo pipefail

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root" || exit 1

# shellcheck source=.git-hooks/common.sh
source "$(dirname "$0")/common.sh"

failed=0

say() {
    echo "    $1"
}

# The index mode at exactly this path, empty when the index has nothing there.
#
# An exact-path match, not a pathspec match. `git ls-files -- <dir>` also lists
# everything inside <dir>, so a pathspec would report a committed copy as a
# mode-100644 entry at the directory's own path and skip the one branch that
# says how to fix it.
#
# Empty is a meaningful answer, not a failure: it means everything committed
# under this name sits inside it, so the name is a real directory rather than a
# link.
mode_at_path() {
    git ls-files -s -- "$1" \
        | awk -F'\t' -v want="$1" '$2 == want {print $1}' \
        | awk '{print $1}' | head -1
}

# Depth-one names committed under a skills directory, however they were
# committed. A link lands here as one entry at the directory's own path; a
# committed copy lands as the file inside it, which is what makes the two
# distinguishable.
#
# `cut -f2-` takes the path field: `git ls-files -s` puts mode, sha and stage
# before a tab, and the path after it.
depth_one_names() {
    git ls-files -s "$1" \
        | cut -f2- \
        | sed "s|^$1/||" \
        | sed 's|/.*$||' \
        | sort -u
}

# True when this clone stores links as plain files.
symlinks_off() {
    [ "$(git config --get core.symlinks 2>/dev/null)" = "false" ]
}

# What the index holds at one path, as a link: prints `symlink <target>` or
# `plain-file <target>`, or `other <mode>` / `none`. A plain file counts as a
# link only where core.symlinks=false, and only when it is a single line that
# looks like a relative path.
index_link() {
    local entry mode body
    entry="$1"
    mode="$(mode_at_path "$entry")"
    case "$mode" in
        120000)
            echo "symlink $(git cat-file -p ":${entry}" 2>/dev/null)"
            ;;
        100644|100755)
            body="$(git cat-file -p ":${entry}" 2>/dev/null | tr -d '\r')"
            if symlinks_off && [ "$(printf '%s\n' "$body" | wc -l)" -le 1 ] \
                && [[ "$body" == ../* ]]; then
                echo "plain-file $body"
            else
                echo "other $mode"
            fi
            ;;
        "") echo "none" ;;
        *) echo "other $mode" ;;
    esac
}

# What a path is in the working tree: symlink, junction, plain-file, directory,
# file or missing. A junction shows as a symlink to Git Bash, so Windows asks
# the file system.
wt_kind() {
    local target parent leaf winparent
    target="$1"
    if [ -L "$target" ]; then
        case "$(uname -s 2>/dev/null)" in
            MINGW*|MSYS*|CYGWIN*)
                parent="$(dirname "$target")"
                leaf="$(basename "$target")"
                winparent="$(cygpath -w "$parent" 2>/dev/null)"
                if MSYS_NO_PATHCONV=1 cmd /c dir /AL "$winparent" 2>/dev/null \
                    | tr -d '\r' | grep -qE "<JUNCTION> +${leaf}( |\$)"; then
                    echo junction
                    return 0
                fi
                ;;
        esac
        echo symlink
    elif [ -d "$target" ]; then
        echo directory
    elif [ -f "$target" ]; then
        if head -n 1 "$target" 2>/dev/null | tr -d '\r' | grep -q '^\.\./'; then
            echo plain-file
        else
            echo file
        fi
    else
        echo missing
    fi
}

# The vendored copy of a skill, if any: the first `vendor/<source>/<name>` that
# holds a committed SKILL.md. Any directory under `vendor/` counts, so a second
# upstream needs no edit here.
vendor_dir_of() {
    git ls-files -- "vendor" \
        | grep -E "^vendor/[^/]+/${1}/SKILL\.md$" \
        | head -1 \
        | sed 's|/SKILL\.md$||'
}


# **Copy layout.** `KIT_SKILL_LAYOUT="copy"` in `.kit/config.env` keeps every
# skill as real files in all three places, and this gate proves the copies are
# byte-identical to their source instead of proving a link. Use it where a link
# cannot be trusted: a Windows machine without symlink rights, a repo that is
# pushed to a host and cloned back, a tool that does not follow links. The cost
# is that the same files are committed more than once, which is why the check
# compares blobs and `bin/sync-skills` exists to regenerate the copies.
#
#   C1. Is any entry in the skills trees a link? A link is the thing this layout
#       avoids, because a clone without symlink rights turns it into a text file.
#   C2. Does every `.agents/skills/<name>` have a `.claude/skills/<name>`, and
#       the reverse, with the same files and the same bytes?
#   C3. Where a pristine copy sits under `vendor/`, is `.agents/skills/<name>`
#       the same files and the same bytes as it?
#   C4. Does each `SKILL.md`'s `name:` match its directory?
#   C5/C6. Companions of our own skills: named in backticks, no frontmatter.
tree_digest() {
    # One line per file: relative path, mode, blob. Same digest means same tree.
    git ls-files -s -- "$1" \
        | awk -F'\t' -v p="$1/" '{split($1, a, " "); print substr($2, length(p) + 1) " " a[1] " " a[3 - 1]}' \
        | sort
}

copy_layout_check() {
    local failed=0 name vendored declared skill_file unprefixed="" links
    local agent_names claude_names

    agent_names="$(depth_one_names .agents/skills)"
    claude_names="$(depth_one_names .claude/skills)"

    links="$(git ls-files -s -- .agents/skills .claude/skills | awk '$1 == "120000"' | cut -f2-)"
    if [ -n "$links" ]; then
        say "the copy layout holds real files only, but these are links:"
        printf '%s\n' "$links" | sed 's/^/        /'
        say "    Run bin/sync-skills to replace them with copies."
        failed=1
    fi

    for name in $agent_names; do
        vendored="$(vendor_dir_of "$name")"
        skill_file=".agents/skills/${name}/SKILL.md"

        if [ -n "$vendored" ]; then
            if [ "$(tree_digest ".agents/skills/${name}")" != "$(tree_digest "$vendored")" ]; then
                say ".agents/skills/${name} differs from its pristine source ${vendored}."
                say "    Never edit a borrowed skill; wrap it. Restore the copy:"
                say "        bin/sync-skills"
                failed=1
            fi
        else
            case "$name" in
                "${KIT_SKILL_PREFIX}"-*) ;;
                *) unprefixed="${unprefixed} ${name}" ;;
            esac
        fi

        if [ -z "$(git ls-files -- "$skill_file")" ]; then
            say ".agents/skills/${name} has no SKILL.md, so it is not a skill."
            failed=1
            continue
        fi

        if [ -z "$(git ls-files -- ".claude/skills/${name}")" ]; then
            say ".agents/skills/${name} has no copy in .claude/skills, so Claude Code"
            say "    cannot see it. Run bin/sync-skills."
            failed=1
        elif [ "$(tree_digest ".claude/skills/${name}")" != "$(tree_digest ".agents/skills/${name}")" ]; then
            say ".claude/skills/${name} is not byte-identical to .agents/skills/${name}."
            say "    Two copies that differ is the bug this gate exists for. Run bin/sync-skills."
            failed=1
        fi

        declared="$(git cat-file -p ":${skill_file}" 2>/dev/null \
            | tr -d '\r' | grep -m1 '^name:' | sed 's/^name:[[:space:]]*//' \
            | tr -d '"'"'"'' | tr -d '[:space:]')"
        if [ -z "$declared" ]; then
            say "${skill_file} has no name: field."
            failed=1
        elif [ "$declared" != "$name" ]; then
            say "${skill_file} declares 'name: ${declared}' but sits in a directory called '${name}'."
            failed=1
        fi

        [ -n "$vendored" ] && continue

        local skill_text companion base needle first_line
        skill_text="$(git cat-file -p ":${skill_file}" 2>/dev/null)"
        for companion in $(git ls-files -- ".agents/skills/${name}" \
                | grep -E "^\.agents/skills/${name}/[^/]+\.md$" | grep -v '/SKILL\.md$'); do
            base="${companion##*/}"
            needle='`'"${base}"'`'
            if ! grep -qF -- "$needle" <<<"$skill_text"; then
                say "${companion} is not named in backticks in ${skill_file}, so no run reaches it."
                failed=1
            fi
            first_line="$(git cat-file -p ":${companion}" 2>/dev/null | tr -d '\r' \
                | grep -m1 -v '^[[:space:]]*$' | sed 's/[[:space:]]*$//')"
            if [ "$first_line" = "---" ]; then
                say "${companion} opens with YAML frontmatter; only a SKILL.md carries it."
                failed=1
            fi
        done
    done

    for name in $claude_names; do
        if ! grep -qxF "$name" <<<"$agent_names"; then
            say ".claude/skills/${name} has no source in .agents/skills. Remove it or run bin/sync-skills."
            failed=1
        fi
    done

    say "layout: copy. $(printf '%s\n' $agent_names | grep -c .) skill(s), each present as real files in .agents/skills and .claude/skills."
    if [ -n "$unprefixed" ]; then
        say "note: skills the project wrote do not start with '${KIT_SKILL_PREFIX}-':${unprefixed}"
        say "    (KIT_SKILL_PREFIX in .kit/config.env; advisory, does not fail the gate)"
    fi
    return "$failed"
}

if [ "${KIT_SKILL_LAYOUT:-link}" = "copy" ]; then
    if [ -z "$(git ls-files -- .claude/skills .agents/skills | head -1)" ]; then
        say "no .claude/skills or .agents/skills in the index — no skills tree to check."
        exit 0
    fi
    copy_layout_check
    exit $?
fi

claude_names="$(depth_one_names .claude/skills)"
agent_names="$(depth_one_names .agents/skills)"

if [ -z "$claude_names" ] && [ -z "$agent_names" ]; then
    say "no .claude/skills or .agents/skills in the index — no skills tree to check."
    exit 0
fi

kinds_found=""

for name in $claude_names; do
    entry_path=".claude/skills/${name}"
    want="../../.agents/skills/${name}"
    found="$(index_link "$entry_path")"
    kind="${found%% *}"
    target="${found#* }"

    case "$kind" in
        none)
            # Nothing at the path itself means everything committed under this
            # name sits inside it — a copy, not a link.
            say "${entry_path} is a committed copy, not a link."
            if [ "$(wt_kind "$entry_path")" = "junction" ]; then
                say "    Found: a junction in the working tree. Git cannot store a"
                say "    junction, so it staged the directory behind it file by file."
                say "    Unstage it and keep the committed link instead:"
                say "        git rm -r --cached ${entry_path}"
            else
                say "    Found: real files. Delete them and link to the one real copy:"
                say "        git rm -r --cached ${entry_path} && rm -rf ${entry_path}"
                say "        ln -s ${want} ${entry_path}"
            fi
            failed=1
            continue
            ;;
        other)
            say "${entry_path} is committed as a plain file (mode ${target}), not a link."
            if ! symlinks_off; then
                say "    A plain file counts as a link only where core.symlinks=false;"
                say "    here git supports real symlinks, so it must be one."
            else
                say "    core.symlinks=false, so a one-line file holding '${want}'"
                say "    would be accepted. This one is not that."
            fi
            failed=1
            continue
            ;;
    esac

    kinds_found="${kinds_found} ${kind}"

    if [ "$target" != "$want" ]; then
        say "${entry_path} (${kind}) points at '${target}'."
        say "    It must point at '${want}' — same name on both sides, so a"
        say "    reader never has to work out which skill this is."
        failed=1
        continue
    fi

    # The target is real if it holds a committed SKILL.md, or if the index has
    # anything at all under that path. The second test is a pathspec, so a
    # link into vendor/ and a directory of files both satisfy it. That looseness
    # is deliberate: the .agents loop below is what decides whether the thing
    # found is actually a skill, and repeating that test here would only be a
    # second copy of it.
    if ! git ls-files --error-unmatch -- ".agents/skills/${name}/SKILL.md" >/dev/null 2>&1 \
        && ! git ls-files --error-unmatch -- ".agents/skills/${name}" >/dev/null 2>&1; then
        say "${entry_path} points at .agents/skills/${name}, which has no"
        say "    committed SKILL.md. The link is dangling."
        failed=1
    fi
done

# The other direction. A skill with no link is invisible to Claude Code, which is
# quieter than a broken link and just as wrong.
unprefixed=""

for name in $agent_names; do
    if ! git ls-files --error-unmatch -- ".claude/skills/${name}" >/dev/null 2>&1; then
        say ".agents/skills/${name} has no link in .claude/skills, so Claude Code"
        say "    cannot see it. Add one:"
        say "        ln -s ../../.agents/skills/${name} .claude/skills/${name}"
        failed=1
    fi

    # A skill the project wrote is a real directory here, and its SKILL.md is
    # committed inside it. A borrowed skill is a link into the pristine tree
    # under vendor/, and its SKILL.md is committed there — same-name rule as the
    # .claude side, so a reader never has to work out which skill a link serves.
    agents_path=".agents/skills/${name}"
    agents_found="$(index_link "$agents_path")"
    agents_kind="${agents_found%% *}"
    agents_target="${agents_found#* }"
    vendored="$(vendor_dir_of "$name")"
    is_link=no

    if [ "$agents_kind" = "symlink" ] || [ "$agents_kind" = "plain-file" ]; then
        is_link=yes
        kinds_found="${kinds_found} ${agents_kind}"
        case "$agents_target" in
            ../../vendor/*/"${name}") ;;
            *)
                say "${agents_path} is a ${agents_kind} to '${agents_target}'."
                say "    A link here may only point at '../../vendor/<source>/${name}' —"
                say "    the pristine vendored copy, under the same name."
                failed=1
                continue
                ;;
        esac
        # The directory named must be the vendored copy that exists.
        if [ "${agents_target#../../}" != "$vendored" ]; then
            say "${agents_path} points at '${agents_target}', but no committed"
            say "    SKILL.md lives there. The link is dangling."
            failed=1
            continue
        fi
        skill_file="${vendored}/SKILL.md"
    else
        # Anything but a link here — a real directory, or a link that a
        # `core.symlinks=false` clone degraded into a text file the gate cannot
        # read as one — is only right when the skill is ours. If a pristine copy
        # also sits under vendor/, this name has two copies and every check
        # above passes anyway: the SKILL.md is committed, the name matches, and
        # the .claude link resolves. That is the shape an upstream update
        # leaves behind when it replaces each link with a directory of fresh
        # files and leaves the vendored copy where it was.
        if [ -n "$vendored" ]; then
            say "${agents_path} is not a link here, but a pristine"
            say "    copy is already vendored at ${vendored}."
            say "    That is two copies of one skill. Restore the link:"
            say "        git rm -r --cached ${agents_path}"
            say "        rm -rf ${agents_path}"
            say "        ln -s ../../${vendored} ${agents_path}"
            failed=1
            continue
        fi
        skill_file="${agents_path}/SKILL.md"
        case "$name" in
            "${KIT_SKILL_PREFIX}"-*) ;;
            *) unprefixed="${unprefixed} ${name}" ;;
        esac
    fi

    if ! git ls-files --error-unmatch -- "$skill_file" >/dev/null 2>&1; then
        say "${agents_path} has no SKILL.md, so it is not a skill."
        failed=1
        continue
    fi

    # Quotes stripped because the field is written both ways, and a quoted name
    # is the same name.
    declared="$(git cat-file -p ":${skill_file}" 2>/dev/null \
        | tr -d '\r' \
        | grep -m1 '^name:' \
        | sed 's/^name:[[:space:]]*//' \
        | tr -d '"'"'"'' \
        | tr -d '[:space:]')"

    if [ -z "$declared" ]; then
        say "${skill_file} has no name: field."
        failed=1
    elif [ "$declared" != "$name" ]; then
        say "${skill_file} declares 'name: ${declared}' but sits in a directory"
        say "    called '${name}'. A half-finished rename lists the skill under"
        say "    one name and files it under the other."
        failed=1
    fi

    # Companion files: one step of the skill in its own file beside SKILL.md,
    # so a run that skips the step never loads it.
    #
    # Only ours are checked. A vendored skill's tree is upstream's shape, and
    # policing it here would be the fork the vendor rule exists to prevent.
    [ "$is_link" = "yes" ] && continue

    skill_text="$(git cat-file -p ":${skill_file}" 2>/dev/null)"

    # Depth one and Markdown only. A skill may commit other things beside its
    # SKILL.md — a diagram, a script — and those are not companions.
    companions="$(git ls-files -- "${agents_path}" \
        | grep -E "^\.agents/skills/${name}/[^/]+\.md$" \
        | grep -v '/SKILL\.md$')"

    for companion in $companions; do
        base="${companion##*/}"

        # The pointer is the backticked basename. A substring match is not:
        # ranking.md passes when SKILL.md only mentions `frontier-ranking.md`.
        # A here-string, not a pipe: `grep -q` stops at the first match, the
        # writer then dies on a broken pipe, and `pipefail` fails the search.
        needle='`'"${base}"'`'
        if ! grep -qF -- "$needle" <<<"$skill_text"; then
            say "${companion} is not named in backticks in ${skill_file}, so no"
            say "    run reaches it. Point at \`${base}\` from the step that"
            say "    needs it, or delete it."
            failed=1
        fi

        # The first line with anything on it, not the first physical line. A
        # companion opening with a blank line, or with `---` plus a trailing
        # space, carries frontmatter every parser will read and a `head -1`
        # equality test would wave through.
        first_line="$(git cat-file -p ":${companion}" 2>/dev/null \
            | tr -d '\r' \
            | grep -m1 -v '^[[:space:]]*$' \
            | sed 's/[[:space:]]*$//')"

        if [ "$first_line" = "---" ]; then
            say "${companion} opens with YAML frontmatter. Only a SKILL.md"
            say "    carries name: and description: — a companion holding them"
            say "    is a second skill the harness may try to run."
            failed=1
        fi
    done
done

# Which kind of link the project uses, said once. In the index, from above; in
# the working tree, here, because a junction exists only there.
wt_kinds=""
for name in $claude_names; do
    wt_kinds="${wt_kinds} $(wt_kind ".claude/skills/${name}")"
done
summarize() {
    # One `kind xN` per distinct kind, in a stable order.
    printf '%s\n' $1 | grep -v '^$' | sort | uniq -c \
        | awk '{printf "%s%s x%s", (NR>1?", ":""), $2, $1}'
}
if [ -n "${kinds_found// /}" ]; then
    say "links in the index: $(summarize "$kinds_found")"
fi
if [ -n "${wt_kinds// /}" ]; then
    say "links in the working tree: $(summarize "$wt_kinds")"
fi

if [ -n "$unprefixed" ]; then
    say "note: skills the project wrote do not start with '${KIT_SKILL_PREFIX}-':${unprefixed}"
    say "    (KIT_SKILL_PREFIX in .kit/config.env; advisory, does not fail the gate)"
fi

exit "$failed"
