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
