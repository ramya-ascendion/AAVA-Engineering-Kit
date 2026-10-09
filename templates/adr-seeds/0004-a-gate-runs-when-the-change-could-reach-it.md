---
status: accepted (baseline)
---

# A gate runs when the change could reach it, and says NOT RUN otherwise

One function, `path_affects_tests`, decides whether a staged change could alter what a test does. If it could, the suites run. If it could not, the hook prints NOT RUN. A missing tool is FAILED, never NOT RUN and never passed.

## Why

A check that did not run is not a check that passed. Running every suite on every comment edit teaches people to skip hooks.

## Consequences

- The path list is deliberately wide and configured in `.kit/config.env`.
- A worktree runs the same gates as the main checkout. The hook hands off to the branch's own copy when git was sent elsewhere.
