#!/bin/bash
#
# The secret-scan gate: a thin, strict wrapper around gitleaks.
#
# Usage:
#   secret-scan.sh            scan what is staged (the pre-commit question)
#   secret-scan.sh --tree     scan the whole working tree (no git history)
#
# **A scanner that is not installed is a FAILED gate, not a skipped one.** A
# check that did not run is not a check that passed, and a secret that reaches a
# remote cannot be taken back. The install hint is printed with the refusal.
#
# gitleaks is found on PATH first, then in the places a winget, scoop or
# `go install` puts it that Git Bash does not search (`find_gitleaks` in
# `common.sh`). Rules come from the repo's `.gitleaks.toml` when it has one.
#
# `protect --staged` is the documented pre-commit form through 8.x; newer
# releases rename it `git --staged`, so the wrapper falls back to that when the
# old command is gone. Either way the exit code is gitleaks' own: 0 clean,
# 1 a leak was found, anything else means the scan did not happen and is
# reported as such.

set -uo pipefail

# shellcheck source=.git-hooks/common.sh
source "$(dirname "$0")/common.sh"

mode="staged"
[ "${1:-}" = "--tree" ] && mode="tree"

if ! scanner="$(find_gitleaks)"; then
    echo "    FAILED — gitleaks is not installed, so nothing here can check for secrets."
    echo "    Install it, then run again:"
    echo "        Windows:  winget install Gitleaks.Gitleaks"
    echo "        macOS:    brew install gitleaks"
    echo "        Linux:    https://github.com/gitleaks/gitleaks/releases"
    exit 1
fi

config_args=()
[ -f ".gitleaks.toml" ] && config_args=(--config .gitleaks.toml)

if [ "$mode" = "tree" ]; then
    report="$("$scanner" detect --no-git --redact --no-banner         "${config_args[@]+"${config_args[@]}"}" 2>&1)"
    scanned=$?
else
    report="$("$scanner" protect --staged --redact --no-banner         "${config_args[@]+"${config_args[@]}"}" 2>&1)"
    scanned=$?
    case "$report" in
        # The old command is gone in newer releases; ask the new one instead.
        *"unknown command"*|*"unknown flag"*)
            report="$("$scanner" git --staged --redact --no-banner                 "${config_args[@]+"${config_args[@]}"}" 2>&1)"
            scanned=$?
            ;;
    esac
fi
# Findings (and any scanner error) are shown only when the scan did not pass, so
# a clean commit prints nothing extra.
[ "$scanned" -ne 0 ] && printf '%s
' "$report" | sed 's/^/    /'

case "$scanned" in
    0) exit 0 ;;
    1)
        echo "    FAILED — gitleaks found what looks like a secret (above)."
        echo "    Remove it and rotate it if it was ever real. A false positive"
        echo "    is allow-listed in .gitleaks.toml, with a reason."
        exit 1
        ;;
    *)
        echo "    FAILED — gitleaks exited $scanned, so the scan did not happen."
        exit 1
        ;;
esac
