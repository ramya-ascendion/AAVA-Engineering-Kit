#!/bin/bash
#
# What both hooks need before they can check anything.
#
# Sourced by `pre-commit` and `pre-push`. One copy of each shared check,
# because two copies is how the one that drifted becomes the one guarding the
# thing you care about — the same failure the self-check below exists to catch.
#
# **Where the hooks live.** The kit and every project store them in `.git-hooks/`; the installer copies
# them into a target project as `.git-hooks/` and points `core.hooksPath` there.
# `kit_hooks_dir` answers whichever exists, so the same files run in both.
#
# **Per-project settings come from `.kit/config.env`**, which this file sources
# (`kit_load_config`). A missing file is not an error: every key has a default.
# Nothing here names a project, a package or a virtualenv.

# Settings, defaults filled in. Safe under `set -u`. The file is shell syntax
# (KEY="value"), the same file `tools/kit_config.py` reads.
# **The kit's Python tools print non-ASCII (an em dash in a status line), and on
# Windows a piped Python writes the legacy code page unless told otherwise.**
# UTF-8 mode makes every tool a hook starts write what the hooks and the tests
# read. A caller who set it on purpose keeps their value.
export PYTHONUTF8="${PYTHONUTF8:-1}"

kit_load_config() {
    local config_root
    config_root="$(git rev-parse --show-toplevel 2>/dev/null)"
    if [ -n "$config_root" ] && [ -f "$config_root/.kit/config.env" ]; then
        # shellcheck disable=SC1091
        source "$config_root/.kit/config.env"
    fi
    : "${KIT_PROJECT_NAME:=project}"
    : "${KIT_PACKAGE_DIR:=src/app}"
    : "${KIT_PYTHON_PACKAGE:=app}"
    : "${KIT_VENV_DIR:=.venv}"
    : "${KIT_TICKET_PREFIX:=PROJ}"
    : "${KIT_SKILL_PREFIX:=aes}"
    : "${KIT_SPELLING_LOCALE:=american}"
    : "${KIT_TRACKER:=github}"
    : "${KIT_DEFAULT_BRANCH:=main}"
    : "${KIT_SKILL_LAYOUT:=link}"
    : "${KIT_PROTECT_BRANCHES:=no}"
    : "${KIT_PROTECTED_BRANCHES:=}"
    : "${KIT_COVERAGE_BAR:=75}"
    : "${KIT_CRAP_BAR:=30}"
    : "${KIT_TEST_DIRS:=tests/unit}"
    : "${KIT_STACK:=none}"
    : "${KIT_TEST_CMD:=}"
    : "${KIT_LINT_CMD:=}"
}

kit_load_config

# The directory these hooks run from, relative to the repo root: `.git-hooks`
# in an installed project, `hooks` in the kit itself.
kit_hooks_dir() {
    local hooks_root
    hooks_root="$(git rev-parse --show-toplevel)"
    if [ -f "$hooks_root/.git-hooks/common.sh" ]; then
        echo ".git-hooks"
    else
        echo "hooks"
    fi
}

# True when the project's language gates (black, flake8, pylint, mypy, layering,
# CRAP, import resolution, duplicate code) apply.
kit_is_python() {
    [ "$KIT_STACK" = "python" ]
}

# The command a commit runs for tests, empty when none is configured. A Python
# project that names none gets pytest over KIT_TEST_DIRS.
kit_test_cmd() {
    if [ -n "${KIT_TEST_CMD// /}" ]; then
        echo "$KIT_TEST_CMD"
    elif kit_is_python; then
        echo "python -m pytest $KIT_TEST_DIRS -q"
    fi
}

# An interpreter for the kit's own tools (`doc_structure.py` and friends). Not
# the project's language: a Node or docs-only project needs one too. Each
# candidate is run, because on Windows `python3` can be a Store stub that exists
# on PATH and does nothing. Prints the command; non-zero when there is none.
find_python() {
    local candidate
    for candidate in python python3 py; do
        if command -v "$candidate" >/dev/null 2>&1 \
            && "$candidate" -c "import sys" >/dev/null 2>&1; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

# **A hook must be the hook the repo defines.**
#
# An installed copy under `.git/hooks` can drift from the tracked source and go
# on running a weaker gate, and a copy carries no trace of what it came from, so
# nobody finds out. The rule the hooks apply to everything else — a check that
# did not run is not a check that passed — applies to the hook itself.
#
# **This cannot rescue somebody still running a copy made before it existed.**
# That copy has no self-check in it, so nothing fires. `setup-dev-env.sh` moves
# such copies aside and points `core.hooksPath` here, and that remains the only
# cure for a checkout that predates this change. What the check does guarantee is
# that no copy made from here on can go stale unnoticed.
#
# **A worktree sent to another checkout's hooks runs its own anyway.** A
# worktree-scope `core.hooksPath` makes git run that other copy; this hands off
# to the branch's own with `exec` — same arguments, same stdin — and
# `KIT_HOOK_REEXEC` caps it at one. Refusing was the wrong answer, because a
# gate nobody can satisfy gets switched off wholesale.
#
# With no override there is nothing to hand off to, so a stale copy is still a
# refusal.
#
# **These function names cannot be renamed.** Another checkout's hook sources
# this file, not its own copy: `$(git rev-parse --show-toplevel)` resolves to the
# worktree git is working in, so an older `pre-commit` from the main checkout
# ends up sourcing the branch's `common.sh` and calling the names it knew. Rename
# one and that hook dies with "command not found" before it reaches the hand-off
# — which is the one path that makes a worktree work at all. `refuse_if_stale`
# reads oddly for a function that usually hands off rather than refusing; that is
# the price of the name being an interface. Renaming it needs a release where the
# old name stays as a shim, not an edit. New functions are free to add.
#
# **Every variable here is `local`.** These names are sourced into the hook's own
# shell, so an unlocalized one is a name the rest of the hook silently shares.
# `exec` below replaces the process, so nothing is lost by scoping them.
refuse_if_stale() {
    local hook_name running_hook hooks_override tracked_hook hooks_dir
    hook_name="$1"
    running_hook="$2"
    shift 2

    hooks_override=""
    hooks_dir="$(kit_hooks_dir)"
    tracked_hook="$(git rev-parse --show-toplevel)/${hooks_dir}/${hook_name}"

    [ -f "$tracked_hook" ] && cmp -s "$running_hook" "$tracked_hook" && return 0
    [ -f "$tracked_hook" ] || return 0

    # Silent when `extensions.worktreeConfig` is off, which is the ordinary case:
    # no worktree scope exists, so there is no override to find.
    hooks_override="$(git config --worktree --get core.hooksPath 2>/dev/null)"

    if [ -n "$hooks_override" ] && [ -z "${KIT_HOOK_REEXEC:-}" ]; then
        echo "  this worktree's core.hooksPath points at ${hooks_override},"
        echo "  so git ran that ${hook_name} instead of this branch's. Running"
        echo "  this branch's copy instead."
        export KIT_HOOK_REEXEC=1
        exec "$tracked_hook" "$@"
    fi

    echo "  FAILED — the hook that ran is not this checkout's ${hooks_dir}/${hook_name}."
    if [ -n "$hooks_override" ]; then
        echo "  Handing off to this branch's copy did not help, which should not"
        echo "  happen. This worktree's core.hooksPath is:"
        echo "      ${hooks_override}"
        echo "  Clearing it makes git run this checkout's hooks directly:"
        echo "      git config --worktree --unset core.hooksPath"
    else
        echo "  It is running checks the project no longer defines. Re-install it:"
        echo "      git config core.hooksPath ${hooks_dir}"
    fi
    return 1
}

# **What a change has to contain before the tests are worth running.**
#
# **Deliberately wide.** Running the tests when they were not needed costs a
# minute; skipping them when they were needed is the failure this file exists to
# prevent, so anything arguable is in. The hooks directory because the hook tests
# run these very files; `tools/` because the gates there are half code and half
# data (a commit touching `tools/crap-exempt` alone changes what a test asserts).
#
# What counts is read from the config: the first path segment of each
# `KIT_TEST_DIRS` entry, and the package directory.
path_affects_tests() {
    local test_dir test_top
    case "$1" in
        *.py|*.js|*.mjs|*.cjs|*.ts|*.tsx|*.jsx) return 0 ;;
        tests/*|.git-hooks/*|hooks/*|tools/*) return 0 ;;
        pytest.ini|pyproject.toml|setup.py|setup.cfg|.flake8|.pylintrc) return 0 ;;
        package.json|package-lock.json|.kit/config.env) return 0 ;;
        requirements*.txt|*/requirements*.txt) return 0 ;;
    esac
    [ -n "${KIT_PACKAGE_DIR:-}" ] && case "$1" in
        "$KIT_PACKAGE_DIR"/*) return 0 ;;
    esac
    for test_dir in $KIT_TEST_DIRS; do
        test_top="${test_dir%%/*}"
        case "$1" in
            "$test_dir"/*|"$test_top"/*) return 0 ;;
        esac
    done
    return 1
}

# True when any path given could change what a test does. No paths at all is
# false — nothing staged, nothing to break.
any_path_affects_tests() {
    local one
    for one in "$@"; do
        [ -n "$one" ] && path_affects_tests "$one" && return 0
    done
    return 1
}

# The one sentence both hooks say when they skip the tests, written here so the
# two cannot drift into describing different rules. `$1` names what was looked
# at.
#
# **It recites every branch of `path_affects_tests` above, not the memorable
# ones.** A sentence narrower than the rule tells someone the tests will run on
# a change the gate lets straight through. A new entry above is a new entry
# here.
tests_not_needed_note() {
    echo "    Nothing $1 can change what a test does: no source code, nothing"
    echo "    under the test directories ($KIT_TEST_DIRS), $KIT_PACKAGE_DIR/,"
    echo "    tests/, the hooks directory or tools/, and nothing that configures"
    echo "    a run — pytest.ini, pyproject.toml, setup.py, setup.cfg, .flake8,"
    echo "    .pylintrc, package.json, .kit/config.env or a requirements*.txt."
}

# Where a cache built beside a checkout may be, one path per line: this
# checkout, then the main checkout.
#
# **Two places, because a worktree has no cache of its own.**
# `--path-format=absolute` is not optional: without it the main checkout answers
# a bare `.git`, and the path built from that depends on which directory the hook
# started in. The answer names a checkout only when it ends in `.git` — `dirname`
# on a bare `repo.git` points at an unrelated folder above it.
cache_candidates() {
    local common
    echo "$PWD/$1"
    # Empty when git is missing, or when this is not a repository at all.
    common="$(git rev-parse --path-format=absolute --git-common-dir 2>/dev/null)"
    if [ "$(basename "${common:-}")" = ".git" ]; then
        echo "$(dirname "$common")/$1"
    fi
}

# The tools are installed in the project environment, not system-wide. A hook
# that called the system pytest would be checking a different project, so
# finding nothing is said out loud and both callers check the return.
#
# **The activation script is `bin/activate` on Linux and macOS and
# `Scripts/activate` on Windows.** Both are tried, so the same hook runs under
# Git Bash on either.
#
# **The environment supplies the tools; this checkout supplies the source.**
# An editable install holds one absolute path, to the checkout it was built in —
# so every worktree sharing that environment imports the main checkout's package,
# not the branch's. A gate testing code the commit does not contain can refuse a
# good commit and pass a bad one. `PYTHONPATH` is prepended below because it is
# read before the `.pth`, so the checkout being committed wins.
activate_venv() {
    local venv_main venv_candidate venv_src venv_script
    local venv_candidates=()

    while IFS= read -r venv_candidate; do
        venv_candidates+=("$venv_candidate")
    done < <(cache_candidates "$KIT_VENV_DIR")
    venv_main="${venv_candidates[1]:-}"

    for venv_candidate in "${venv_candidates[@]}"; do
        venv_script=""
        if [ -f "$venv_candidate/bin/activate" ]; then
            venv_script="$venv_candidate/bin/activate"
        elif [ -f "$venv_candidate/Scripts/activate" ]; then
            venv_script="$venv_candidate/Scripts/activate"
        fi
        if [ -n "$venv_script" ]; then
            # shellcheck disable=SC1091
            source "$venv_script"
            # The directory the package imports from: `src` for `src/pkg`, the
            # checkout itself for a package at the root. Guarded on the
            # directory, not on the answer: outside a checkout `--show-toplevel`
            # says nothing and the path would be a bare `/src`. Prepended rather
            # than assigned, so a caller who set it on purpose keeps their
            # entries behind this one.
            venv_src="$(git rev-parse --show-toplevel 2>/dev/null)"
            case "$KIT_PACKAGE_DIR" in
                */*) venv_src="$venv_src/${KIT_PACKAGE_DIR%/*}" ;;
            esac
            [ -d "$venv_src" ] \
                && export PYTHONPATH="${venv_src}${PYTHONPATH:+:${PYTHONPATH}}"
            return 0
        fi
    done

    echo "  no ${KIT_VENV_DIR} found. Looked in $PWD/${KIT_VENV_DIR}"
    # Only when it is somewhere else. In an ordinary checkout the two are the
    # same path, and "looked in X and in X" reads as a bug in the hook.
    [ -n "$venv_main" ] && [ "$venv_main" != "$PWD/$KIT_VENV_DIR" ] \
        && echo "  and in $venv_main"
    echo "  Run ./setup-dev-env.sh to build one."
    return 1
}

# Where gitleaks is, whether or not it is on PATH. Prints the command and
# returns 0, or returns 1 when it cannot be found.
#
# **On Windows a winget install does not reach Git Bash's PATH.** The binary
# sits under `%LOCALAPPDATA%/Microsoft/WinGet/`, so it is looked for there as
# well. A missing scanner is a FAILED gate, never a skipped one.
find_gitleaks() {
    local found winget_root
    if command -v gitleaks >/dev/null 2>&1; then
        echo "gitleaks"
        return 0
    fi
    for winget_root in \
        "${LOCALAPPDATA:-}/Microsoft/WinGet/Packages" \
        "${LOCALAPPDATA:-}/Microsoft/WinGet/Links" \
        "$HOME/AppData/Local/Microsoft/WinGet/Packages" \
        "$HOME/AppData/Local/Microsoft/WinGet/Links" \
        "$HOME/bin" "$HOME/.local/bin" "$HOME/go/bin"; do
        [ -d "$winget_root" ] || continue
        found="$(find "$winget_root" -maxdepth 3 \( -name 'gitleaks.exe' -o -name 'gitleaks' \) \
            -type f 2>/dev/null | head -1)"
        if [ -n "$found" ]; then
            echo "$found"
            return 0
        fi
    done
    return 1
}

# **The shape both content gates share.** Walk the files given, ask one function
# what is wrong with each, print what it says under that file's name, and fail if
# anything spoke.
#
# One driver rather than one per gate, because two copies is how the gates start
# disagreeing about what an exemption means — a file exempt from one and not the
# other, depending on how its path was typed.
#
# `$1` is the exempt-list file. `$2` is the name of a function taking one path
# and printing `line:text` for every hit in it — nothing at all when the file is
# clean. The rest of the arguments are the files to look at.
#
# **Every variable here is `local`.** `pre-commit` has a `run_gate` of its own
# using the same `gate_` prefix, and two functions writing one namespace is a
# gate reporting under another gate's file name — the kind of wrongness a gate
# cannot afford.
gate_over() {
    local gate_exempt gate_hits_fn gate_failed gate_one gate_hits
    gate_exempt="$1"
    gate_hits_fn="$2"
    shift 2

    gate_failed=0
    for gate_one in "$@"; do
        [ -f "$gate_one" ] || continue
        if gate_is_exempt "$gate_exempt" "$gate_one"; then
            continue
        fi
        gate_hits="$("$gate_hits_fn" "$gate_one")"
        if [ -n "$gate_hits" ]; then
            echo "    $gate_one"
            echo "$gate_hits" | sed 's/^/        /'
            gate_failed=1
        fi
    done
    return "$gate_failed"
}

# Exact path match on a non-comment, non-blank line of the exempt list. Any
# leading `./` is stripped first, because a hook passes `docs/...` and a person
# at a prompt passes `./docs/...` — the same file, and the list should not care
# which.
#
# A line ending in `/` exempts the whole directory under it. That form exists
# for `vendor/`, where the exemption's reason ("not ours to spell") is true of
# every file upstream ships, including ones a future update adds — a file list
# would go stale on exactly the update it is meant to survive.
gate_is_exempt() {
    [ -f "$1" ] || return 1
    local gate_path gate_list gate_dir
    gate_path="${2#./}"
    gate_list="$(grep -v '^[[:space:]]*#' "$1" 2>/dev/null | grep -v '^[[:space:]]*$')"
    # A here-string, not a pipe. `grep -q` stops at the first match, a writer
    # still writing then dies on a broken pipe, and `pipefail` fails the test.
    grep -qxF -- "$gate_path" <<<"$gate_list" && return 0
    # One line at a time, not `for gate_dir in $(...)`. Unquoted word-splitting
    # would cut an exempt line containing a space into two bogus prefixes, and a
    # short one like `docs/my` then prefix-matches files the list never named.
    # An exemption that is too wide stops a gate checking a file and says
    # nothing, which is the worst way for a gate to be wrong.
    #
    # Redirected rather than piped, so the `return 0` below returns from this
    # function instead of from a subshell.
    while IFS= read -r gate_dir; do
        case "$gate_path" in
            "$gate_dir"*) return 0 ;;
        esac
    done < <(printf '%s\n' "$gate_list" | grep '/$')
    return 1
}
