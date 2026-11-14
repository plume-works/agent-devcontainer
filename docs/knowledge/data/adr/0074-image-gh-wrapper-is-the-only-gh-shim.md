---
type: adr
stage: accepted
description: The gh wrapper that the image installs at /usr/local/bin/gh authenticates gh, and no shell configuration puts a checkout path before it.
---

# Only the gh wrapper of the image authenticates gh

The first `gh` on `PATH` gets the authority of the token that the wrapper adds.
A checkout that is open in the container is not always trusted. As a result, the
`github_cli` role installs the wrapper at `/usr/local/bin/gh`, and no shell
configuration of the images puts a checkout path before it. The wrapper
authenticates each caller with no agent action.

## Considered Options

- A documented procedure or a skill for each shell. Rejected: a caller that does
  not know it fails with an authentication error far from the cause, also in
  tools that call `gh` themselves.
- The `docker/bin` directory of the open checkout first on `PATH`. Rejected: it
  gives the token to each executable that a repository puts at that path.
- A `GIT_ASKPASS` fallback in the wrapper. Rejected: `GITHUB_TOKEN` is a Coder
  user secret that does not change for the life of the agent. As a result, the
  copy that a session gets does not expire.

## Consequences

- A change to the wrapper applies only after an image build. The wrapper is in
  the `files/` directory of the role, so the provisioning step of the role
  mounts only `ansible/`.
- The wrapper never replaces a `GH_TOKEN` or `GITHUB_TOKEN` that is set. It asks
  the credential helper only when Git has one, and it stops the request after
  two seconds.
- The wrapper writes nothing to stdout, so a program that reads the output of
  `gh` gets only the output of `gh`. It writes reports to stderr only when
  `VERBOSE_GH` is set.
- `GH_WRAPPER_ACTIVE` makes the wrapper do its work one time in each process
  tree. The wrapper stops with exit code 127 when it finds no real `gh`.
- The wrapper is on the `PATH` of the image, so it also applies to a container
  that `docker run` starts without the Dev Container lifecycle.
- The wrapper finds the real `gh` on `PATH` and skips copies of itself, so it
  does not break when `gh` moves. It continues with no message when the
  credential helper does not apply, for example in CI with its own token.
- The role removes the `github_cli_wrapper` block from `~/.bashrc` and
  `~/.config/fish/config.fish`.
