---
type: spec
description: Git identity passes from the outer workspace into the nested devcontainer, and HTTPS git reuses the gh login.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-12T00:00:00Z
sources:
- resource: .devcontainer/scripts/coder-agent-start.sh
- resource: scripts/tests/test_coder_agent_start.py
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/scripts/postStartCommand.sh
- resource: .devcontainer/scripts/setup-gh-credential-helper.sh
- resource: scripts/tests/test_setup_gh_credential_helper.py
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
`https://github.com`, post-start SHALL configure `gh` as the helper, and so
SHALL `coder-agent-start.sh`, which the Coder template's `coder_script` runs on
every agent start. Both SHALL check authentication only after the keyring
session is available, so git never waits at an interactive credential prompt. An
existing helper SHALL be kept. A failed helper setup SHALL NOT stop
`coder-agent-start.sh` from starting Remote Control.

#### Scenario: gh's only login is a Coder user secret

- **WHEN** a Coder workspace supplies `GITHUB_TOKEN` as a user secret, `gh` has
  no stored login, and the agent starts
- **THEN** `coder-agent-start.sh` configures `gh` as the github.com helper, and
  `git push` over HTTPS completes without a prompt.

#### Scenario: gh has a stored login outside Coder

- **WHEN** a container whose `gh` login is stored on disk or in the keyring
  starts
- **THEN** post-start configures `gh` as the github.com helper.

#### Scenario: a helper is already configured

- **WHEN** a git credential helper already matches `https://github.com`
- **THEN** neither post-start nor `coder-agent-start.sh` changes it.

#### Scenario: helper setup fails at agent start

- **WHEN** `setup-gh-credential-helper.sh` exits non-zero during
  `coder-agent-start.sh`
- **THEN** a warning is printed and `claude-remote-control-start.sh` still runs.

## Supplying the identity

Create or update the four Git identity secrets in the Coder account, mapped to
the exact `GIT_*` names listed above. Identity values are configuration, not
credentials, but they should still be supplied through Coder rather than baked
into the image.
