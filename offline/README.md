# Offline proof (template)

Shows that the test suite needs no network, and shows that the showing is real.

A passing run with the network off proves little on its own: the suite may
simply have found a prefetched asset cached from an earlier online run. So the
proof is two runs of one image, both with `--network none`:

| Run     | Staged asset | Required result            |
| ------- | ------------ | -------------------------- |
| Staged  | present      | passes                     |
| Control | deleted      | fails, for the named cause |

The control run is the point. `run.sh` fails unless it gets both results, and
the control run must fail for the cause you name, not for any reason at all.

## Making it yours

1. **`Dockerfile` block 1**: your dependency files and install command.
2. **`Dockerfile` block 2**: the staging step, whatever a fresh machine downloads
   on first use. Pass it with `STAGE_CMD`. It is the last thing in the image
   that touches the network.
3. **`run.sh` settings**: `OFFLINE_STAGED_PATH` (what the staging step produces)
   and `OFFLINE_FAIL_PATTERN` (a `grep -E` pattern for the error a missing asset
   gives). `KIT_PROJECT_NAME` and `KIT_TEST_CMD` come from `.kit/config.env`.

Until `OFFLINE_STAGED_PATH` and `OFFLINE_FAIL_PATTERN` are set, `run.sh` exits 2
with "not configured" rather than running a proof that proves nothing.

A project whose suite downloads nothing has nothing to stage and no use for
this directory; delete it.

## Running

```
OFFLINE_STAGED_PATH=.cache/server \
OFFLINE_FAIL_PATTERN='could not download' \
STAGE_CMD='python tools/fetch_asset.py' \
./offline/run.sh
```

Needs Docker with BuildKit. The build is the only step that uses the network.
