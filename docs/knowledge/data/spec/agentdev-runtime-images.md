---
type: spec
description: The agentdev image family — a lifecycle-neutral agentdev-base and sibling agentdev-deploy and agentdev-devcontainer runtimes — how they are provisioned and trust a host's extra CA, and the runtime CLI, supervised services, lifecycle phases, and hook interface the Dev Container image gives consumers without copied lifecycle scripts.
sources:
- resource: ansible/roles/agentic_tools/defaults/main.yml
- resource: py_packages/agentdev_runtime/pyproject.toml
- resource: py_packages/agentdev_runtime/agentdev_runtime/cli.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/settings.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py
- resource: .github/actions/run-claude-responder/action.yml
- resource: .devcontainer/devcontainer-init.sh
- resource: .devcontainer/docker-compose.yml
- resource: .devcontainer/firewall-allowlist.txt
- resource: ansible/roles/git_ppa/tasks/main.yml
- resource: ansible/roles/git_ppa/defaults/main.yml
- resource: scripts/cache-git-ppa-release.py
- resource: .github/workflows/cache-git-ppa-release.yml
- resource: ansible/roles/validate_agent_files/tasks/main.yml
- resource: docker/base/agentdev-base.Dockerfile
- resource: ansible.cfg
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: scripts/tests/test_agent_runtime_acceptance.py
- resource: docker/devcontainer/supervisord.conf
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/hooks.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/integrity.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/trust.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/worktree.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/doctor.py
- resource: .github/workflows/ci.yml
- resource: docker/ansible/setup-ansible.sh
- resource: docker/desktop/entrypoint.sh
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .dockerignore
- resource: .github/actions/docker/build-push-action/action.yml
- resource: ansible/roles/github_cli/tasks/main.yml
- resource: .devcontainer/devcontainer.json
- resource: py_packages/agentdev_runtime/agentdev_runtime/health.py
- resource: ansible/roles/xpra_setup/tasks/main.yml
- resource: ansible/roles/fish_setup/tasks/main.yml
---

# agentdev runtime images

The image family of the reusable agentdev Dev Container. The deploy runtime's
own requirements are in [Standalone OpenCode
runtime](standalone-opencode-runtime.md).

## Requirements

### Requirement: image builds contact no Launchpad host

No Ansible role SHALL add a PPA apt source, and the firewall allowlist SHALL
name neither `launchpad.net` nor `ppa.launchpadcontent.net`. The `git_ppa` role
SHALL install the Git Core PPA's `git` and `git-man` from the release of this
repository that `git_ppa_release_tag` names (`pinned-deps/git/<version>`),
checking each package's SHA-256, in one apt transaction that replaces any other
`git` build, and SHALL delete the `git-core-ppa` apt source. The daily
`cache-git-ppa-release.yml` workflow SHALL publish the PPA's newest noble build
as such a release only after the PPA's `InRelease` verifies against the pinned
key in `scripts/git-core-ppa.asc` and each `Packages` index and `.deb` matches
the SHA-256 that signed index chains to; it SHALL never mark the release as the
repository's latest and SHALL never replace a release that exists.

#### Scenario: an image starts from one provisioned with the PPA

- **WHEN** the `git_ppa` role runs where
  `/etc/apt/sources.list.d/git-core-ppa.list` exists or a newer `git` is
  installed
- **THEN** the source is deleted and the pinned release's `git` is installed

#### Scenario: the PPA index is not signed by the pinned key

- **WHEN** the workflow fetches an `InRelease` without a valid signature by the
  pinned key, or a file whose SHA-256 differs from the signed index
- **THEN** it publishes nothing and fails

### Requirement: gh resolves to the image's wrapper

The images SHALL install the `gh` authentication wrapper at `/usr/local/bin/gh`
from the `github_cli` role, and no shell configuration the images or
`setup-dev.yml` provide SHALL put a path from the workspace checkout ahead of it
on `PATH`.

#### Scenario: a checkout carries its own gh

- **WHEN** a Dev Container opens a checkout that contains `docker/bin/gh`
- **THEN** `command -v gh` in an interactive bash or fish shell resolves to
  `/usr/local/bin/gh`

#### Scenario: a host carries the legacy `github_cli_wrapper` block

- **WHEN** `setup-dev.yml` runs again on a host whose `~/.bashrc` or
  `config.fish` carries the `github_cli_wrapper` block
- **THEN** the block is removed

### Requirement: the bootstrap trusts an extra CA bundle

Before any service starts, the root bootstrap of both runtime images SHALL make
the system certificate store hold exactly the PEM certificates of the bundle at
`AGENTDEV_EXTRA_CA_CERTS`, withdrawing those of an earlier start, and SHALL fail
when that file is non-empty but holds no certificate. The image SHALL point
`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, and `NODE_EXTRA_CA_CERTS` at the system
store. The Dev Container's host init SHALL hand over the host's
`AGENTDEV_EXTRA_CA_CERTS`, else its `NODE_EXTRA_CA_CERTS` when that names a
readable file: it SHALL always write `.devcontainer/.extra-ca.crt`, empty when
the host names none, which the Compose service mounts read-only at
`/etc/agentdev/extra-ca.crt`, and SHALL fail when an explicit
`AGENTDEV_EXTRA_CA_CERTS` is not readable. The bundle SHALL be read once per
container start.

#### Scenario: a host behind a TLS-intercepting proxy starts a runtime

- **WHEN** the proxy's CA bundle is mounted at `AGENTDEV_EXTRA_CA_CERTS`
- **THEN** a certificate it signed verifies against the system store inside the
  container, so nested pulls and package downloads succeed

#### Scenario: no extra CA is given

- **WHEN** the file is absent or empty
- **THEN** the bootstrap adds nothing and continues

#### Scenario: the bundle holds no certificate

- **WHEN** the file is non-empty and holds no PEM certificate
- **THEN** the bootstrap fails naming the file

#### Scenario: the host's proxy CA rotates

- **WHEN** the host's bundle changes while a Dev Container runs
- **THEN** the new CA is trusted only after `devcontainer-init.sh` runs again
  and the container restarts, and the previous CA is withdrawn then

#### Scenario: the host names an unreadable bundle

- **WHEN** the host sets `AGENTDEV_EXTRA_CA_CERTS` to a file it cannot read
- **THEN** `devcontainer-init.sh` fails and the container does not start
