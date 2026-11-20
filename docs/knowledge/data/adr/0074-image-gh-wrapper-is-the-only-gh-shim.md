---
type: adr
stage: accepted
description: The gh wrapper that the image installs at /usr/local/bin/gh authenticates gh, and no shell configuration puts a checkout path before it.
---

# Only the gh wrapper of the image authenticates gh

The gh wrapper is a script that runs the real `gh` with a token from the git
credential helper. The first `gh` on `PATH` gets the authority of the token that
the wrapper adds. A checkout that is open in the container is not always
trusted. As a result, the `github_cli` role installs the wrapper at
`/usr/local/bin/gh`, and no shell configuration of the images puts a checkout
path before it. The wrapper authenticates each caller with no agent action.

## Considered Options

- A documented procedure or a skill for each shell. Rejected: a caller that does
  not know it fails with an authentication error far from the cause, also in
  tools that call `gh` themselves.
- The `docker/bin` directory of the open checkout first on `PATH`. It lets a
  wrapper edit take effect without an image rebuild. Rejected: it hands the
  injected token to any executable that a repository ships under that path.
- A `GIT_ASKPASS` fallback in the wrapper. Rejected: `GITHUB_TOKEN` is a Coder
  user secret, stable for the life of the agent, so the copy that a session
  inherits does not go stale.

## Consequences

- The wrapper writes nothing to stdout, so a program that reads the output of
  `gh` gets only the output of `gh`. It writes reports to stderr only when
  `VERBOSE_GH` is set.
