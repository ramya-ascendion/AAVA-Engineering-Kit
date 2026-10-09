#!/bin/bash
#
# Prove the suite runs with no internet — and prove the proof. A TEMPLATE: see
# `offline/README.md`.
#
#   OFFLINE_STAGED_PATH=.cache/server OFFLINE_FAIL_PATTERN='could not download' \
#       ./offline/run.sh
#
# Two runs in a container with `--network none`, and **both are required**:
#
#   | Run     | Network | Staged asset | Required result            |
#   | ------- | ------- | ------------ | -------------------------- |
#   | Staged  | off     | yes          | passes                     |
#   | Control | off     | no           | fails, for the named cause |
#
# **The control run is the whole point.** A prefetched dependency is a separate
# thing a tool downloads on first use and caches, so a passing offline run on its
# own proves only that something was already cached somewhere. The control run is
# what shows the network really was off. This script fails unless it gets both
# results, and it checks the control run failed for the right reason rather than
# for any reason at all.
#
# The build needs the network. Everything after it does not: `--network none` is
# on every `docker run`.
#
# Settings (environment, or `.kit/config.env` for the first two):
#   KIT_PROJECT_NAME     names the image (`<name>-offline`)
#   KIT_TEST_CMD         the suite; defaults to `python -m pytest -q`
#   OFFLINE_STAGED_PATH  REQUIRED. The path inside the image the staging step
#                        produces, which the control run deletes.
#   OFFLINE_FAIL_PATTERN REQUIRED. A grep -E pattern the control run's log must
#                        contain: the error a missing asset gives.
#   STAGE_CMD            the staging command, passed to the Dockerfile build.

set -uo pipefail

cd "$(dirname "$0")/.." || exit 1

# shellcheck disable=SC1091
[ -f .kit/config.env ] && source .kit/config.env

IMAGE="${KIT_PROJECT_NAME:-project}-offline"
SUITE="${KIT_TEST_CMD:-python -m pytest -q}"
LOGS="${TMPDIR:-/tmp}"
STAGED_LOG="${LOGS%/}/${IMAGE}-staged.log"
CONTROL_LOG="${LOGS%/}/${IMAGE}-control.log"
BUILD_LOG="${LOGS%/}/${IMAGE}-build.log"

# A template with nothing to stage cannot prove anything: without the control
# run the staged run proves only that something was cached. Refused, not skipped.
if [ -z "${OFFLINE_STAGED_PATH:-}" ] || [ -z "${OFFLINE_FAIL_PATTERN:-}" ]; then
    echo "OFFLINE NOT PROVED — this template is not configured."
    echo "  Set OFFLINE_STAGED_PATH (what the staging step produces) and"
    echo "  OFFLINE_FAIL_PATTERN (the error a missing asset gives). Without a"
    echo "  control run the staged run proves nothing. See offline/README.md."
    exit 2
fi

# The image's own ignore file is `offline/Dockerfile.dockerignore`, which only
# BuildKit reads. Without BuildKit it is silently ignored and the build context
# grows to include the venv and .env — so it is asked for explicitly.
export DOCKER_BUILDKIT=1

# The last line pytest prints about counts. The pass/fail decisions below rest
# on exit status and on the failure pattern, never on this string, which exists
# to fill the table.
result_line() {
    grep -Eo "[0-9]+ (passed|failed|error|skipped)[^=]*" "$1" |
        tail -1 |
        sed 's/ *$//'
}

show_tail() {
    tail -20 "$1" | sed 's/^/    /'
}

if ! command -v docker >/dev/null 2>&1; then
    echo "docker is not installed, and there is no other way to turn the network"
    echo "off for a test run. Nothing was proved."
    exit 1
fi

if ! docker info >/dev/null 2>&1; then
    echo "docker is installed but not running. Start it — nothing was proved."
    exit 1
fi

echo "Building $IMAGE (this is the part that needs the network)..."
# Both streams, because docker build reports progress on stderr — redirecting
# only stdout buries the two results below in a page of install output.
if ! docker build -f offline/Dockerfile --build-arg "STAGE_CMD=${STAGE_CMD:-true}" \
    -t "$IMAGE" . >"$BUILD_LOG" 2>&1; then
    echo "  FAILED — the build did not finish. Nothing was proved."
    echo "  $BUILD_LOG has it. The last lines:"
    show_tail "$BUILD_LOG"
    exit 1
fi
echo "  ok"

# Anything but 0 here means the proof did not come out, and the exit status at
# the bottom follows it.
not_proved=0

# ---------------------------------------------------------------------------
# Run 1 — staged. The asset is in the image, the network is off, this passes.
# ---------------------------------------------------------------------------
echo "Staged run, --network none..."
docker run --rm --network none "$IMAGE" sh -c "$SUITE" >"$STAGED_LOG" 2>&1
staged_status=$?
staged_result=$(result_line "$STAGED_LOG")

if [ $staged_status -eq 0 ]; then
    echo "  ok — $staged_result"
else
    echo "  FAILED — the suite does not pass with the network off."
    echo "  $STAGED_LOG has the run. The last lines:"
    show_tail "$STAGED_LOG"
    not_proved=1
fi

# ---------------------------------------------------------------------------
# Run 2 — control. Same image, same network, same command, staged asset
# deleted. **Must fail.**
#
# The delete happens in the container, so the image is untouched.
# ---------------------------------------------------------------------------
echo "Control run, --network none, staged asset removed..."
docker run --rm --network none "$IMAGE" \
    sh -c "rm -rf '$OFFLINE_STAGED_PATH' && $SUITE" >"$CONTROL_LOG" 2>&1
control_status=$?
control_result=$(result_line "$CONTROL_LOG")

if [ $control_status -eq 0 ]; then
    echo "  FAILED — the control run passed."
    echo "  That means the suite got the asset from somewhere the network was"
    echo "  supposed to have cut off, so the staged run above proves nothing."
    not_proved=1
else
    # **Failing is not enough — it has to fail for the right reason.** A typo in
    # this script, a broken image or a missing dependency would also fail, and
    # would read as a passing control run.
    reason=$(grep -E -m1 "$OFFLINE_FAIL_PATTERN" "$CONTROL_LOG")
    if [ -n "$reason" ]; then
        echo "  ok — $control_result"
        echo "  and it failed for the right reason:"
        echo "    $(echo "$reason" | sed 's/^ *//')"
    else
        echo "  FAILED — the control run failed, but not for the named cause"
        echo "  ($OFFLINE_FAIL_PATTERN). So it does not show the network was off."
        echo "  $CONTROL_LOG has the run. The last lines:"
        show_tail "$CONTROL_LOG"
        not_proved=1
    fi
fi

echo
echo "| Run     | Network | Staged asset | Result |"
echo "| ------- | ------- | ------------ | ------ |"
echo "| Staged  | off     | yes          | ${staged_result:-no result} |"
echo "| Control | off     | no           | ${control_result:-no result} |"
echo
echo "Full output: $STAGED_LOG"
echo "             $CONTROL_LOG"
echo "             $BUILD_LOG"

# A missing result line is not a pass either. "no result" in the table while the
# script exits 0 would be the same class of false claim this script refuses.
if [ -z "$staged_result" ] || [ -z "$control_result" ]; then
    echo
    echo "One of the runs printed no test counts at all, so neither line above is"
    echo "evidence of anything. The logs have what really happened."
    not_proved=1
fi

if [ $not_proved -ne 0 ]; then
    echo
    echo "OFFLINE NOT PROVED."
    exit 1
fi

echo
echo "Offline proved: the suite passes with no network, and does not without the"
echo "staged asset."
