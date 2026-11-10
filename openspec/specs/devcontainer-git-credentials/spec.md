# Devcontainer Git credentials Specification

## Purpose

Git identity passes from the outer workspace into the nested devcontainer, and HTTPS git reuses the gh login.

## Requirements

### Requirement: Git identity reaches the nested container

Compose SHALL propagate each of these variables that the outer workspace sets,
and SHALL leave an unset one unset in the nested container, because Git treats
an empty value as an override of `user.name` or `user.email`:

- `GIT_AUTHOR_NAME`
- `GIT_AUTHOR_EMAIL`
- `GIT_COMMITTER_NAME`
- `GIT_COMMITTER_EMAIL`

#### Scenario: the outer workspace sets only some identity variables

- **WHEN** the outer workspace sets `GIT_AUTHOR_NAME` and leaves
  `GIT_COMMITTER_EMAIL` unset
- **THEN** the nested container has the same `GIT_AUTHOR_NAME` and no
  `GIT_COMMITTER_EMAIL` variable, not an empty one

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

### Requirement: the gh wrapper derives a token without disturbing callers

The `gh` wrapper SHALL leave an existing `GH_TOKEN` or `GITHUB_TOKEN` untouched.
Otherwise, only when a `credential.helper` is configured, it SHALL run
`git credential fill` for github.com under a two-second timeout and export the
password it returns as `GH_TOKEN`. It SHALL write nothing unless `VERBOSE_GH` is
set, and then only to stderr. It SHALL do this once per process tree, guarded by
`GH_WRAPPER_ACTIVE`, SHALL exec the first `gh` on `PATH` that is not a copy of
itself, and SHALL exit 127 with a message when no real `gh` is found.

#### Scenario: a CI job supplies its own token

- **WHEN** `gh` runs with `GITHUB_TOKEN` set
- **THEN** the wrapper execs the real `gh` with the token unchanged

#### Scenario: no credential helper is configured

- **WHEN** `gh` runs with no token and no `credential.helper`
- **THEN** the wrapper execs the real `gh` silently, without running
  `git credential fill`

#### Scenario: the real gh is missing

- **WHEN** no `gh` other than the wrapper is on `PATH`
- **THEN** the wrapper exits 127 naming the problem

## Supplying the identity

Create or update the four Git identity secrets in the Coder account, mapped to
the exact `GIT_*` names listed above. Identity values are configuration, not
credentials, but they should still be supplied through Coder rather than baked
into the image.

## Rationale

### gh authentication is a wrapper on PATH

A documented per-shell procedure puts a prerequisite on every shell, and
skipping it fails as an authentication error far from its cause; a wrapper
authenticates every caller, tools that shell out to `gh` included. It falls
through silently because it runs where the trick does not apply, such as CI with
its own token, and stdout stays clean for anything parsing `gh` output. It walks
`PATH` past its own copies, recognized by a marker string, rather than exec a
fixed path that could move. Only the image's baked copy may run with the
injected token, because a checkout opened in the container is not necessarily
trusted and any repository can carry an executable at `docker/bin/gh`.

Rejected:

- **Prepend the live checkout's `docker/bin` so a wrapper edit applies without
  a rebuild.** It hands the injected token to whatever `gh` a checkout carries;
  a wrapper change now ships through an image build.
