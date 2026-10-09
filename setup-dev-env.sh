#!/bin/bash
#
# The development environment: the pre-commit hooks pointed at, gitleaks checked
# for, and — when the project is Python — a virtual environment holding the
# gate tools.
#
# **Everything it needs comes from `.kit/config.env`.** `KIT_STACK` decides
# whether a virtual environment is built at all (only `python` gets one), and
# `KIT_VENV_DIR` names it. A Node or documentation-only project gets the hooks
# and the secret-scanner check and nothing else; its gates that need no
# environment (secrets, document structure, skill mirror, spelling) run as is.
#
# **The hooks directory is `.git-hooks`**, in the kit and in an installed project
# alike. An older install that still has `hooks` is found as a fallback.
#
# It is safe to re-run. Nothing here overwrites a virtual environment, a `.env`
# or an `environments.yaml` that already exists.

set -uo pipefail

# Settings, with defaults for a missing file.
if [ -f .kit/config.env ]; then
    # shellcheck disable=SC1091
    source .kit/config.env
fi
: "${KIT_PROJECT_NAME:=project}"
: "${KIT_VENV_DIR:=.venv}"
: "${KIT_STACK:=none}"
: "${KIT_TEST_DIRS:=tests/unit}"

VENV="$KIT_VENV_DIR"

if [ -d .git-hooks ]; then
    HOOKS=".git-hooks"
elif [ -d hooks ]; then
    HOOKS="hooks"
else
    echo "Neither .git-hooks nor hooks exists here, so there are no hooks to install."
    echo "Run this from the repository root."
    exit 1
fi

echo "Setting up the development environment for ${KIT_PROJECT_NAME} (stack: ${KIT_STACK})..."

# Where a virtual environment keeps its executables: `bin` on Linux and macOS,
# `Scripts` on Windows. Asked of the directory rather than of the platform, so a
# venv made by either one is found.
venv_bin() {
    if [ -d "$VENV/Scripts" ]; then
        echo "$VENV/Scripts"
    else
        echo "$VENV/bin"
    fi
}

# The venv's interpreter: `python` in `bin`, `python.exe` in `Scripts`.
venv_python() {
    local bin_dir
    bin_dir="$(venv_bin)"
    if [ -x "$bin_dir/python" ]; then
        echo "$bin_dir/python"
    elif [ -x "$bin_dir/python.exe" ]; then
        echo "$bin_dir/python.exe"
    fi
}

# The floor is 3.10. Asked of Python rather than compared as a string: an older
# check was `[[ "$VERSION" < "3.9" ]]`, which sorts lexicographically, so "3.10"
# came out less than "3.9" and every modern Python was rejected as too old.
meets_floor() {
    "$1" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null
}

# Asked of the interpreter, not parsed out of `--version`: a shim that cannot
# resolve a real toolchain writes something that is not a version string at all.
py_version() {
    "$1" -c 'import sys; print("%d.%d.%d" % sys.version_info[:3])' 2>/dev/null || echo "unknown"
}

setup_python_env() {
    local py existing candidate installer
    py=""
    existing="$(venv_python)"

    if [ -n "$existing" ] && meets_floor "$existing"; then
        echo "Python version: $(py_version "$existing") (from the existing $VENV)"
    else
        # A virtual environment that exists and is too old is worse than none:
        # the installs below would fail somewhere further down, blaming a
        # package. Said here instead, where the cause is.
        if [ -n "$existing" ]; then
            echo "$VENV runs Python $(py_version "$existing"), which is older than 3.10."
            echo "Remove it and re-run:  rm -rf $VENV && ./setup-dev-env.sh"
            return 1
        fi

        # **The bare name first, then versioned newest-first, then the Windows
        # launcher.** `python3` and `python` lead because they are the machine's
        # own answer to "the Python I use"; overriding that would be this
        # script deciding it knows better. Each is run, because on Windows a
        # Store stub can exist on PATH and do nothing.
        for candidate in python3 python python3.13 python3.12 python3.11 python3.10 py; do
            if command -v "$candidate" >/dev/null 2>&1 && meets_floor "$candidate"; then
                py="$candidate"
                break
            fi
        done
        if [ -z "$py" ]; then
            echo "No Python 3.10 or higher found. Looked for: python3, python,"
            echo "python3.13 to python3.10, and the py launcher."
            echo "  Windows:  winget install Python.Python.3.12"
            echo "  macOS:    brew install python@3.12"
            return 1
        fi
        echo "Python version: $(py_version "$py") (using $py)"

        echo "Creating $VENV..."
        if ! "$py" -m venv "$VENV"; then
            echo "Could not create $VENV."
            return 1
        fi
        existing="$(venv_python)"
    fi

    # **Kept if it is already there.** Re-running installs into it rather than
    # recreating it, so nothing a developer added to it is taken away.
    #
    # The gate tools, unpinned: CI installs its own pinned, hash-checked copies
    # (`tools/requirements-*.txt`), and these are only what a commit runs
    # locally. A project that pins its own versions installs them from its own
    # lock file instead; edit this list, or install after it runs.
    local tools=(pytest pyyaml black flake8 pylint mypy radon coverage pytest-xdist)
    echo "Installing the gate tools: ${tools[*]}..."
    if command -v uv >/dev/null 2>&1; then
        installer="uv"
        uv pip install --python "$existing" "${tools[@]}" || return 1
    else
        installer="pip"
        "$existing" -m pip install --upgrade pip \
            && "$existing" -m pip install "${tools[@]}" || return 1
    fi
    echo "  installed with $installer"

    # A project that declares itself in pyproject.toml gets itself installed
    # editable, so its tests can import it. The kit's own pyproject.toml is tool
    # configuration only and has no [project] table, so this is then skipped.
    if [ -f pyproject.toml ] && grep -q '^\[project\]' pyproject.toml; then
        echo "Installing the project itself (editable)..."
        if [ "$installer" = "uv" ]; then
            uv pip install --python "$existing" -e ".[dev]" 2>/dev/null \
                || uv pip install --python "$existing" -e . || return 1
        else
            "$existing" -m pip install -e ".[dev]" 2>/dev/null \
                || "$existing" -m pip install -e . || return 1
        fi
    fi
    return 0
}

if [ "$KIT_STACK" = "python" ]; then
    if ! setup_python_env; then
        echo "The environment setup failed. Nothing further was set up."
        exit 1
    fi
else
    echo "No virtual environment: KIT_STACK is ${KIT_STACK}, and only python gets one."
fi

# **Pointed at, not copied.** Copying a hook into `.git/hooks/` lets the copy
# drift: an installed copy that is an older version runs a weaker gate than the
# project defines, and nobody can tell, because a copy carries no trace of what
# it came from.
#
# `core.hooksPath` makes git run the tracked files directly. There is no second
# copy, so there is nothing left to go stale — and the hooks themselves refuse to
# run if they are ever not their own source, which catches anyone still holding
# an old copy from before this change.
echo "Setting up the Git hooks..."
git config core.hooksPath "$HOOKS"
chmod +x "$HOOKS"/pre-commit "$HOOKS"/pre-push "$HOOKS"/commit-msg "$HOOKS"/*.sh
echo "  core.hooksPath -> $HOOKS (pre-commit, commit-msg, pre-push)"

# **Set here rather than asked for in a README.** A reformat commit is skippable
# in `git blame` only if the reader's checkout has been told to skip it, and a
# step somebody has to remember is a step most people do not take. GitHub reads
# the file without being asked; this is the same courtesy locally.
# `.git-blame-ignore-revs` says what may go in it.
if [ -f .git-blame-ignore-revs ]; then
    git config blame.ignoreRevsFile .git-blame-ignore-revs
    echo "  blame.ignoreRevsFile -> .git-blame-ignore-revs"
fi

# The old copies are dead once hooksPath is set, and a dead hook that still looks
# installed is the next person's confusing hour.
for stale in .git/hooks/pre-commit .git/hooks/pre-push; do
    if [ -f "$stale" ]; then
        mv -f "$stale" "$stale.superseded"
        echo "  moved aside $stale (superseded, kept as .superseded)"
    fi
done

# **The secret scanner is not optional**: the commit gate fails without it. Found
# the same way the gate finds it, including where a winget install puts it that
# Git Bash does not search.
echo "Checking for gitleaks..."
# shellcheck disable=SC1091
source "$HOOKS/common.sh"
if scanner="$(find_gitleaks)"; then
    echo "  gitleaks: $scanner"
    if [ "$scanner" != "gitleaks" ]; then
        echo "  (not on PATH here; the hook finds it anyway. To put it on PATH:"
        echo "   export PATH=\"$(dirname "$scanner"):\$PATH\")"
    fi
else
    echo "  WARNING: gitleaks is not installed, so every commit will FAIL its"
    echo "  secret scan until it is."
    echo "    Windows:  winget install Gitleaks.Gitleaks"
    echo "    macOS:    brew install gitleaks"
    echo "    Linux:    https://github.com/gitleaks/gitleaks/releases"
fi

# **No `.env` is written here, and no `environments.yaml`.** Both hold values
# that are each developer's own, so both are gitignored and both are yours to
# write. `.env.example` says what to put in a `.env`.

if [ "$KIT_STACK" = "python" ]; then
    echo "Checking the environment can run the tests..."
    py_bin="$(venv_python)"
    # **The environment's executables go on PATH, because the hook puts them
    # there too.** Several tests run a gate the way the pre-commit hook runs it —
    # a bare `python tools/doc_structure.py` — and the hook can spell it that way
    # because `activate_venv` has already put this directory on PATH. Calling the
    # interpreter by its full path and nothing else leaves `python` unfindable,
    # and a check that fails on a healthy environment is as bad as one that
    # passes on a broken one.
    #
    # **Absolute, because `$VENV` is relative to wherever this script was run.**
    # Tests that need it run their subprocess in a scratch directory, where a
    # relative path on PATH names nothing.
    if ! "$py_bin" -c 'import yaml, pytest'; then
        echo "  FAILED — the environment cannot import pytest and yaml."
        exit 1
    fi
    # shellcheck disable=SC2086
    if [ -d "${KIT_TEST_DIRS%% *}" ] \
        && ! PATH="$PWD/$(venv_bin):$PATH" "$py_bin" -m pytest $KIT_TEST_DIRS --quiet; then
        echo "  FAILED — the test suite does not pass in this environment."
        exit 1
    fi
fi

echo
echo "Development environment ready."
if [ "$KIT_STACK" = "python" ]; then
    if [ -d "$VENV/Scripts" ]; then
        echo "  source $VENV/Scripts/activate      # in future sessions (Windows)"
    else
        echo "  source $VENV/bin/activate          # in future sessions"
    fi
fi
echo "  git config core.hooksPath             # should print: $HOOKS"
