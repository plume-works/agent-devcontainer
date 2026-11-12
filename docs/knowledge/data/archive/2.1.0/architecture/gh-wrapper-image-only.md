---
type: architecture
description: The image's baked gh wrapper at /usr/local/bin/gh is the only gh shim, and no checkout path precedes it on PATH, because a checkout's own gh would otherwise run with the token the wrapper injects.
sources:
- resource: ansible/roles/github_cli/tasks/main.yml
- resource: ansible/roles/github_cli/files/gh
---

# gh wrapper only from the image

## Decision

The `github_cli` role installs the `gh` authentication wrapper from its own
`files/gh` to `/usr/local/bin/gh`, and that baked copy is the only `gh` shim.
Nothing the images or `setup-dev.yml` provide puts a path from the workspace
checkout ahead of it on `PATH`. `setup-dev.yml` removes the `github_cli_wrapper`
block from an existing `~/.bashrc` and `config.fish`.

This supersedes the live-workspace override in [gh authentication
shim](../../1.0.0/architecture/gh-authentication-shim.md); the wrapper's
contract recorded there is unchanged.

## Why no checkout path precedes it

The wrapper exists to hand `gh` a token. Whatever runs first on `PATH` under the
name `gh` gets that token's authority, and a checkout opened in the container is
not necessarily trusted: any repository can carry an executable at
`docker/bin/gh`. Only a file that came from the image build can be trusted to
run with the injected token.

Keeping the wrapper inside its role also keeps the image's inputs where the
provisioning step reads them: the role's step mounts `ansible/`, and needs no
other directory of the repository.

## Rejected: the live-workspace override

Prepending the opened checkout's `docker/bin` let a wrapper edit take effect in
a running container without rebuilding the image. That convenience is what this
decision gives up: a wrapper change now ships through an image build, like every
other file the image carries.

## Consequences

- `command -v gh` resolves to `/usr/local/bin/gh` in interactive bash and fish
  shells whatever checkout is mounted at the workspace folder.
- The wrapper still walks `PATH` past every copy of itself and keeps its
  `GH_WRAPPER_ACTIVE` guard. Both are defensive: one copy is expected, and a
  stray copy elsewhere on `PATH` still resolves to the real binary.
