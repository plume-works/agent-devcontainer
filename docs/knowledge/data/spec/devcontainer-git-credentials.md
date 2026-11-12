---
type: spec
description: Git identity passes from the outer workspace into the nested devcontainer, HTTPS git reuses the gh login, and the image's gh wrapper hands gh a token from the git credential helper.
sources:
- resource: py_packages/agentdev_runtime/agentdev_runtime/coder.py
- resource: scripts/tests/test_coder_agent_start.py
- resource: .devcontainer/docker-compose.yml
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/git.py
- resource: scripts/tests/test_setup_gh_credential_helper.py
- resource: ansible/roles/github_cli/files/gh
- resource: ansible/roles/github_cli/tasks/main.yml
---

# Devcontainer Git credentials

## Requirements

### Requirement: Git identity reaches the nested container

Compose SHALL propagate each of these variables that the outer workspace sets,
and SHALL leave an unset one unset in the nested container, because Git treats
an empty value as an override of `user.name` or `user.email`:

- `GIT_AUTHOR_NAME`
- `GIT_AUTHOR_EMAIL`
- `GIT_COMMITTER_NAME`
- `GIT_COMMITTER_EMAIL`

### Requirement: HTTPS git uses the gh login

When `gh` is authenticated to github.com and no git credential helper matches
`https://github.com`, post-start (`agentdev-runtime lifecycle ready`) SHALL
configure `gh` as the helper, and so SHALL `agentdev-runtime coder start`, which
the Coder template's `coder_script` runs on every agent start. Both SHALL check
authentication only after the keyring session is available, so git never waits
at an interactive credential prompt. An existing helper SHALL be kept. A failed
helper setup SHALL NOT stop `agentdev-runtime coder start` from starting Remote
Control.

#### Scenario: gh's only login is a Coder user secret

- **WHEN** a Coder workspace supplies `GITHUB_TOKEN` as a user secret, `gh` has
  no stored login, and the agent starts
- **THEN** `agentdev-runtime coder start` configures `gh` as the github.com
  helper, and `git push` over HTTPS completes without a prompt.

#### Scenario: gh has a stored login outside Coder

- **WHEN** a container whose `gh` login is stored on disk or in the keyring
  starts
- **THEN** post-start configures `gh` as the github.com helper.

#### Scenario: a helper is already configured

- **WHEN** a git credential helper already matches `https://github.com`
- **THEN** neither post-start nor `agentdev-runtime coder start` changes it.

#### Scenario: helper setup fails at agent start

- **WHEN** `agentdev-runtime git credential-helper` exits non-zero during
  `agentdev-runtime coder start`
- **THEN** a warning is printed and `agentdev-runtime remote-control start`
  still runs.

### Requirement: gh authenticates from the git credential helper

The image's `gh` SHALL be a wrapper that derives `GH_TOKEN` from the git
credential helper and then execs the real `gh` with the same arguments. It SHALL
leave an existing `GH_TOKEN` or `GITHUB_TOKEN` untouched, SHALL run
`git credential fill` for `https://github.com` under `timeout 2` and only when a
`credential.helper` is configured, and SHALL write nothing to stdout or stderr
unless `VERBOSE_GH` is set. It SHALL find the real `gh` by walking `PATH` and
skipping every script that contains the marker `gh-wrapper`, falling back to
`/usr/bin/gh`, and SHALL exit 127 with a message on stderr when none is found.
Under `GH_WRAPPER_ACTIVE`, set by the first wrapper in a process tree, a further
wrapper SHALL exec the real `gh` without extracting a token.

#### Scenario: a token is already supplied

- **WHEN** `gh` runs with `GH_TOKEN` or `GITHUB_TOKEN` set
- **THEN** the wrapper execs the real `gh` with that token unchanged

#### Scenario: a credential helper holds a github.com login

- **WHEN** `gh` runs with no token set and a configured `credential.helper`
  returns a password for `github.com`
- **THEN** the real `gh` runs with `GH_TOKEN` set to that password

#### Scenario: no credential helper is configured

- **WHEN** `gh` runs with no token set and no `credential.helper`
- **THEN** the real `gh` runs without a token and the wrapper prints nothing

#### Scenario: the real gh is missing

- **WHEN** no `gh` other than a wrapper copy is on `PATH` and `/usr/bin/gh` does
  not exist
- **THEN** the wrapper exits 127 and names the problem on stderr

### Requirement: the image's gh wrapper is the only gh shim

The `github_cli` role SHALL install the wrapper from its own `files/gh` to
`/usr/local/bin/gh`, ahead of `/usr/bin` on the default `PATH`, and nothing the
images or `setup-dev.yml` provide SHALL put a workspace checkout path ahead of
it. The role SHALL remove the `github_cli_wrapper` managed block from an
existing `~/.bashrc` and `~/.config/fish/config.fish`.

#### Scenario: a checkout carries its own gh

- **WHEN** a checkout mounted at the workspace folder contains an executable
  `docker/bin/gh`
- **THEN** `command -v gh` still resolves to `/usr/local/bin/gh` in interactive
  bash and fish shells

#### Scenario: a shell config carries the old prepend

- **WHEN** the role runs against a home whose `~/.bashrc` holds the
  `github_cli_wrapper` block
- **THEN** the block is removed

## Rationale

### gh is authenticated by a wrapper baked into the image

`gh` authentication is a wrapper on `PATH`, not a procedure an agent follows. A
per-shell procedure puts a prerequisite on every shell, and skipping it surfaces
as an authentication error far from its cause, including in tools that shell out
to `gh` themselves; a wrapper authenticates every caller with no agent action.
It falls through silently where the credential helper does not apply, such as CI
with its own token, because treating that as an error would break `gh` exactly
where a token is already supplied. It walks `PATH` rather than exec a fixed path
so it neither breaks when `gh` moves nor execs itself.

Only the image's copy runs: whatever runs first on `PATH` as `gh` gets the
injected token's authority, and a checkout opened in the container is not
necessarily trusted. Keeping the wrapper inside its role also keeps the image
build's inputs inside `ansible/`. A wrapper change therefore ships through an
image build, like every other file the image carries.

Rejected:

- **A documented per-shell procedure or skill.** Every caller that does not know
  it fails with an authentication error far from its cause.
- **Prepending the opened checkout's `docker/bin` to `PATH`.** It let a wrapper
  edit take effect without an image rebuild, but hands the injected token to any
  executable a repository ships under that path.
