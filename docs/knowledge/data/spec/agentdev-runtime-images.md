---
type: spec
description: The agentdev image family — a lifecycle-neutral agentdev-base and sibling agentdev-deploy and agentdev-devcontainer runtimes — and the supervised services, lifecycle phases, and hook interface the Dev Container image gives consumers without copied lifecycle scripts.
sources:
- resource: docker/base/agentdev-base.Dockerfile
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/devcontainer/supervisord.conf
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/hooks.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/integrity.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/trust.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/doctor.py
- resource: .github/workflows/ci.yml
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .dockerignore
- resource: .github/actions/docker/build-push-action/action.yml
- resource: ansible/roles/github_cli/tasks/main.yml
---

# agentdev runtime images

The image family for the [Reusable agentdev Dev
Container](../features/reusable-agentdev-devcontainer.md) feature. Its design is
[Dev Container
runtime](../../../../openspec/specs/agentdev-runtime-images/spec.md#rationale);
the deploy runtime's own requirements are in [Standalone OpenCode
runtime](standalone-opencode-runtime.md).

## Requirements

### Requirement: the base image is lifecycle-neutral

`agentdev-base` SHALL contain the shared development tools, agentdev catalog,
and default policy without containing deploy or Dev Container lifecycle
implementation; it SHALL NOT carry the `agentdev_runtime` package.

#### Scenario: a consumer runs the base image directly

- **WHEN** a consumer starts `agentdev-base` with its own command
- **THEN** the tools and staged catalog are available, and no agentdev runtime
  supervisor or workspace lifecycle starts implicitly

### Requirement: deploy and Dev Container images are sibling runtimes

`agentdev-deploy` and `agentdev-devcontainer` SHALL derive from the same
accepted `agentdev-base` digest and SHALL package their own runtime entrypoint,
profile, and lifecycle surface.

#### Scenario: one base build feeds both runtimes

- **WHEN** CI builds an accepted image family
- **THEN** both runtime images identify the exact base digest produced in that
  run, without deriving either runtime image from the other

### Requirement: image builds read only their declared inputs

The image build context SHALL contain only `ansible.cfg`, `ansible/`, `docker/`,
`.claude-plugin/`, `.agents/plugins/` without plugin `tests/`,
`py_packages/validate_agent_files/`, `py_packages/agentdev_runtime/`, and
`.devcontainer/firewall-allowlist.txt`. `agentdev-base` SHALL provision in three
steps — Ansible roles, the validator, the catalog — each bind-mounting only the
inputs it reads, so a change outside a step's inputs SHALL leave that step's
cached layer valid. `ubuntu-ansible` SHALL carry no per-run labels, so unchanged
inputs keep its digest. A `clean_build` dispatch or a `[ci:clean_build]` marker
SHALL build without the layer cache.

#### Scenario: a change outside the image inputs

- **WHEN** an image build runs with the layer cache after a change only to files
  outside the build context
- **THEN** every provisioning step is reused from the cache

#### Scenario: a catalog-only change

- **WHEN** only files under `.agents/plugins/` change
- **THEN** only the catalog step runs again; the roles and validator steps are
  reused from the cache

#### Scenario: a clean build is requested

- **WHEN** a run is dispatched with `clean_build` or its commit or pull request
  body carries `[ci:clean_build]`
- **THEN** no provisioning step is reused from the layer cache

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

### Requirement: the Dev Container image owns persistent services

`agentdev-devcontainer` SHALL start Docker, D-Bus, keyring, and enabled Xpra
through its supervised entrypoint, SHALL publish readiness only after required
services are healthy, and SHALL recover or fail with the bounded policy shared
with deploy.

#### Scenario: an editor attaches to a healthy runtime

- **WHEN** the Dev Container start lifecycle waits for runtime readiness
- **THEN** attachment proceeds only after every required service reports ready

#### Scenario: a required service exhausts recovery

- **WHEN** a required service cannot recover within its configured budget
- **THEN** readiness is withdrawn, the failure names the service, and the
  container exits nonzero

### Requirement: lifecycle phases remain distinct

The image SHALL provide stable create, start/readiness, and attach commands —
`agentdev-runtime lifecycle created`, `agentdev-runtime lifecycle ready`, and
`agentdev-runtime lifecycle attached`, published through the image's Dev
Container metadata — and SHALL NOT move create-once or attach-scoped work into
the entrypoint.

#### Scenario: only the attach lifecycle runs

- **WHEN** an attach-only lifecycle event occurs
- **THEN** attach-scoped catalog and index refresh runs without rerunning
  create-once initialization or restarting supervised services

### Requirement: consumers do not copy lifecycle implementation

A direct or derived consumer SHALL be able to obtain the complete managed
lifecycle by referencing `agentdev-devcontainer` and SHALL customize it through
documented environment values and executable files in explicit ordered hook
directories.

#### Scenario: a direct consumer has no lifecycle scripts

- **WHEN** its descriptor selects the image, mounts, workspace, and editor
  settings without repository-local agentdev scripts
- **THEN** managed startup, lifecycle commands, tools, and the staged catalog
  remain available

#### Scenario: a derived image adds a hook

- **WHEN** it installs an executable hook in a documented phase directory
- **THEN** the hook runs in deterministic order after the managed phase without
  changing, adding, or removing any file of the installed `agentdev_runtime`
  distribution

#### Scenario: a mounted repository contains a similarly named script

- **WHEN** no explicit image hook registers that script
- **THEN** mounting or attaching the repository does not execute it

### Requirement: the bootstrap refuses a changed runtime package

While the installed `agentdev_runtime` distribution's metadata is present, the
root bootstrap SHALL refuse to run when a file its `RECORD` lists differs from
the recorded hash or is missing, or a file was added beside the recorded files,
and SHALL name the file and direct the consumer to the hook directories and
documented environment. The check catches accidental or partial edits to the
runtime and is not a security boundary: a derived image that deliberately
deletes the distribution's metadata or rewrites its `RECORD` passes it.

#### Scenario: a derived image edits a package file

- **WHEN** a derived image replaces a file of the installed `agentdev_runtime`
  distribution and the container starts
- **THEN** the bootstrap fails naming that file and the extension points

#### Scenario: a derived image adds a file to the package

- **WHEN** a derived image adds a file below the installed distribution's
  package directory
- **THEN** the bootstrap fails naming the added file

#### Scenario: an unmodified image starts

- **WHEN** the installed distribution matches its `RECORD`
- **THEN** the bootstrap continues

### Requirement: the bootstrap trusts an extra CA bundle

Before any service starts, the root bootstrap of both runtime images SHALL make
the system certificate store hold exactly the PEM certificates of the bundle at
`AGENTDEV_EXTRA_CA_CERTS`, withdrawing those of an earlier start, and SHALL fail
when that file is non-empty but holds no certificate. The image SHALL point
`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, and `NODE_EXTRA_CA_CERTS` at the system
store. The Dev Container's host init SHALL hand over the host's
`AGENTDEV_EXTRA_CA_CERTS`, else its `NODE_EXTRA_CA_CERTS`. Design: [Extra CA
trust](../../../../openspec/specs/agentdev-runtime-images/spec.md#rationale).

#### Scenario: a host behind a TLS-intercepting proxy starts a runtime

- **WHEN** the proxy's CA bundle is mounted at `AGENTDEV_EXTRA_CA_CERTS`
- **THEN** a certificate it signed verifies against the system store inside the
  container, so nested pulls and package downloads succeed

#### Scenario: no extra CA is given

- **WHEN** the file is absent or empty
- **THEN** the bootstrap adds nothing and continues

### Requirement: missing pre-commit hook executables are reported

`agentdev-runtime project hooks` SHALL warn, without failing, about each
`language: system` pre-commit hook whose executable is not on `PATH`, and
`agentdev-runtime doctor` SHALL report `gitleaks` and `actionlint` as required
tools.

### Requirement: doctor judges a healthy Compose Dev Container healthy

In the devcontainer profile, `agentdev-runtime doctor` SHALL accept the git
identity git resolves, including one set through `GIT_AUTHOR_*` and
`GIT_COMMITTER_*`.

### Requirement: the agentdev checkout overrides the staged catalog

The complete catalog in this repository's checkout SHALL override the staged
catalog on attach, while repositories without all required catalog manifests
SHALL continue using the staged version.

#### Scenario: an agentdev developer reloads the editor

- **WHEN** the checkout contains the Claude and OpenCode catalog manifests and
  the attach lifecycle runs
- **THEN** both clients register the checkout catalog without rebuilding the
  image

### Requirement: full adoption remains supported

`template-consume` SHALL remain a supported full-adoption workflow whose adopted
Dev Container uses the published runtime image; minimal adoption SHALL not be a
prerequisite for full adoption.

#### Scenario: an existing full-adoption repository updates

- **WHEN** it follows the supported template-consume update path
- **THEN** its repository-owned customization is preserved and its managed
  runtime resolves through the published image contract
