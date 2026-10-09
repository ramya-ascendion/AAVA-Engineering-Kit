# Setup guide

Copy to `SETUP.md` at the root of a runnable unit. It answers one question: how
does a newcomer get this running and prove it works. Product explanation belongs
in the README, and the reason for a decision belongs in its ADR.

Template starts below the line.

# Setup

## Prerequisites

- <Tool and the version floor, and how to check it: `node --version`.>

## The dev environment

<The one command that creates it, and what it does. It must be safe to run
twice.>

```bash
bash setup-dev-env.sh
```

## Running the tests

<The one command the commit gate runs, and what it needs. Say which tests are
live, what they need running, and the flag that turns them on.>

## Running the thing

<How to start it, the port or URL, and how to tell it is up.>

## The hooks

<Which gates run on commit and push, and the one command that turns them on.
Say that `--no-verify` is never the way past a gate.>

## Secrets and environment files

<Which process reads which env file. Name the variable a secret comes from,
never the secret.>

## What is not here

<What this guide deliberately does not cover, and where to read for it.>

## Where to read next

- <Link to the README, the context file and the ADRs.>
