---
type: spec
description: The agentdev image family — a lifecycle-neutral agentdev-base and sibling agentdev-deploy and agentdev-devcontainer runtimes — and the supervised services, lifecycle phases, and hook interface the Dev Container image gives consumers without copied lifecycle scripts.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T20:55:00Z
sources:
- resource: docker/base/agentdev-base.Dockerfile
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
- resource: docker/devcontainer/supervisord.conf
- resource: py_packages/agentdev_runtime/agentdev_runtime/supervisor.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/lifecycle.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/hooks.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/integrity.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: py_packages/agentdev_runtime/agentdev_runtime/doctor.py
- resource: .github/workflows/ci.yml
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
---

# agentdev runtime images

The image family for the [Reusable agentdev Dev
Container](../features/reusable-agentdev-devcontainer.md) feature. Its design is
[Dev Container runtime](../architecture/devcontainer-runtime.md); the deploy
runtime's own requirements are in [Standalone OpenCode
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

### Requirement: the Dev Container image owns persistent services

`agentdev-devcontainer` SHALL start Docker, D-Bus, keyring, CBM, and enabled
Xpra through its supervised entrypoint, SHALL publish readiness only after
required services are healthy, and SHALL recover or fail with the bounded policy
shared with deploy.

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

### Requirement: missing pre-commit hook executables are reported

`agentdev-runtime project hooks` SHALL warn, without failing, about each
`language: system` pre-commit hook whose executable is not on `PATH`, and
`agentdev-runtime doctor` SHALL report `gitleaks` and `actionlint` as required
tools.

### Requirement: doctor judges a healthy Compose Dev Container healthy

In the devcontainer profile, `agentdev-runtime doctor` SHALL check the
`mcp-gateway` sidecar only when the Compose `mcp` profile is enabled, and SHALL
accept the git identity git resolves, including one set through `GIT_AUTHOR_*`
and `GIT_COMMITTER_*`.

### Requirement: the agentdev checkout overrides the staged catalog

The complete catalog in this repository's checkout SHALL override the staged
catalog on attach, while repositories without all required catalog manifests
SHALL continue using the staged version.

#### Scenario: an agentdev developer reloads the editor

- **WHEN** the checkout contains the Claude, Codex, and OpenCode catalog
  manifests and the attach lifecycle runs
- **THEN** all three clients register the checkout catalog without rebuilding
  the image

### Requirement: full adoption remains supported

`template-consume` SHALL remain a supported full-adoption workflow whose adopted
Dev Container uses the published runtime image; minimal adoption SHALL not be a
prerequisite for full adoption.

#### Scenario: an existing full-adoption repository updates

- **WHEN** it follows the supported template-consume update path
- **THEN** its repository-owned customization is preserved and its managed
  runtime resolves through the published image contract
