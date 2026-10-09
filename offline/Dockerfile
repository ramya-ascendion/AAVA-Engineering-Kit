# The test suite, in a container with no network of its own. A TEMPLATE: see
# `offline/README.md` for the three places a project edits it.
#
# Built with the network on — dependency installs and any prefetch step happen
# here. Run with `--network none`, which is the only way to prove the suite
# needs no internet: on a machine that has already run it once, a passing run
# proves nothing, because something may simply have been cached. `run.sh` runs it
# twice for that reason.
FROM python:3.12-slim

WORKDIR /work

# (1) The install first, and on its own layer, so editing a test does not
# reinstall the world. Edit the COPY list to whatever your dependency files are;
# a project with none can delete this block.
COPY pyproject.toml* requirements*.txt* ./
RUN if [ -f requirements.txt ]; then pip install --no-cache-dir -r requirements.txt; fi \
    && pip install --no-cache-dir pytest pyyaml

# (2) The staging step: whatever a fresh machine downloads on first use (a test
# server binary, a model, fixture data). **This is the last thing in the image
# that touches the network.** The path it produces is `OFFLINE_STAGED_PATH` in
# `run.sh`, which the control run deletes. Replace the placeholder with the real
# command; an image with nothing to stage cannot run the control run, and
# `run.sh` says so rather than skipping it.
ARG STAGE_CMD="true"
RUN sh -c "$STAGE_CMD"

# (3) The project, last because it changes most often.
COPY . .

# `run.sh` passes the command for both of its runs rather than relying on this
# line — they have to be the same command, and one literal in one place is how
# that stays true. This CMD is for running the image by hand.
CMD ["python", "-m", "pytest", "-q"]
