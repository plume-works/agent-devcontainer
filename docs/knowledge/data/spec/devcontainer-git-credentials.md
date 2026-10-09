---
type: spec
description: Git identity passes from the outer workspace into the nested devcontainer, and HTTPS git reuses the gh login.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-09T00:00:00Z
sources:
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
`https://github.com`, post-start SHALL configure `gh` as the helper, checking
authentication only after the keyring session is available, so git never waits
at an interactive credential prompt. An existing helper SHALL be kept.

## Supplying the identity

Create or update the four Git identity secrets in the Coder account, mapped to
the exact `GIT_*` names listed above. Identity values are configuration, not
credentials, but they should still be supplied through Coder rather than baked
into the image.
