# agentdev runtime images Specification

## Purpose

The agentdev image family — a lifecycle-neutral agentdev-base and sibling agentdev-deploy and agentdev-devcontainer runtimes — and the supervised services, lifecycle phases, and hook interface the Dev Container image gives consumers without copied lifecycle scripts.

The image family for the [Reusable agentdev Dev
Container](../../../docs/knowledge/data/features/reusable-agentdev-devcontainer.md) feature. The deploy
runtime's own requirements are in [Standalone OpenCode
runtime](../standalone-opencode-runtime/spec.md).

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
`AGENTDEV_EXTRA_CA_CERTS`, else its `NODE_EXTRA_CA_CERTS`.

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

#### Scenario: a system hook's executable is missing

- **WHEN** `agentdev-runtime project hooks` runs and a `language: system`
  pre-commit hook's executable is not on `PATH`
- **THEN** it warns naming that hook and exits without failing, and
  `agentdev-runtime doctor` reports `gitleaks` and `actionlint` as required

### Requirement: doctor judges a healthy Compose Dev Container healthy

In the devcontainer profile, `agentdev-runtime doctor` SHALL accept the git
identity git resolves, including one set through `GIT_AUTHOR_*` and
`GIT_COMMITTER_*`.

#### Scenario: the identity comes from the environment

- **WHEN** `agentdev-runtime doctor` runs in the devcontainer profile and git's
  identity is set through `GIT_AUTHOR_*` and `GIT_COMMITTER_*`
- **THEN** doctor accepts that identity

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

### Requirement: the runtime is one installed package

The runtime of `agentdev-devcontainer` and `agentdev-deploy` SHALL be the one
Python package `agentdev_runtime`, run as the `agentdev-runtime` CLI, installed
at image build with `uv tool install` from the build context into
`/opt/uv-tools` with its entry point on `/usr/local/bin`, using the system
interpreter, no cache, and no interpreter download. The package SHALL pin its
dependencies, `supervisor` among them, so the images install no apt
`supervisor` and nothing resolves a dependency at container start.

#### Scenario: a runtime container starts offline

- **WHEN** a runtime image starts with no network access
- **THEN** `agentdev-runtime supervisor run` starts without fetching any package

### Requirement: a container with no supervisor runs only the lifecycle commands

Where the supervisor cannot be PID 1, as in a GitHub `container:` job, the
caller SHALL run `agentdev-runtime lifecycle created`,
`agentdev-runtime lifecycle ready --no-wait`, and
`agentdev-runtime lifecycle attached`. `ready --no-wait` SHALL run the per-start
repairs without waiting for supervised services, and nothing else SHALL start.

#### Scenario: the AI review job prepares its container

- **WHEN** `run-claude-responder` prepares the review job's container
- **THEN** it runs the three lifecycle commands, and no keyring, firewall, or
  desktop service starts

### Requirement: image builds contact no Launchpad host

No Ansible role SHALL add a PPA, and the devcontainer firewall SHALL allow
neither `launchpad.net` nor `ppa.launchpadcontent.net`. The Git Core PPA's git
SHALL come from a `pinned-deps/git/<version>` release of this repository, pinned
by tag and SHA-256, and the `git_ppa` role SHALL install `git` and `git-man` from
it in one apt transaction and delete any `git-core-ppa` apt source. A daily
workflow SHALL republish each new PPA build as such a release only after
verifying the PPA's `InRelease` against the pinned key
`F911AB184317630C59970973E363C90F8F1B6217` and every file against the SHA-256
the signed index chains to; it SHALL never mark the release latest and SHALL
never replace a release that exists.

#### Scenario: Launchpad is unreachable during an image build

- **WHEN** the image builds while Launchpad's API and archive are down
- **THEN** the build installs the pinned git release and succeeds

#### Scenario: the PPA index carries a bad signature

- **WHEN** the daily workflow fetches an `InRelease` not signed by the pinned key
- **THEN** it publishes nothing and fails

#### Scenario: a release for the PPA's newest build exists

- **WHEN** the daily workflow runs and `pinned-deps/git/<version>` already exists
- **THEN** it leaves that release unchanged

### Requirement: the agent-file validator is an image tool

`agentdev-base` SHALL install `validate_agent_files` from the build context as
an isolated uv tool, with its entry point at
`/usr/local/bin/validate_agent_files`, at the version
`VALIDATE_AGENT_FILES_VERSION` pins and the
`org.opencontainers.image.version.validate-agent-files` label reports. The build
SHALL fail when the installed distribution's version differs from the pin.

#### Scenario: a consumer validates without the package source

- **WHEN** a container from the published image runs
  `validate_agent_files --help` as the devcontainer user, with no checkout
  holding `py_packages/validate_agent_files/`
- **THEN** it resolves on `PATH` and exits 0 without `uv run`

#### Scenario: the pin and the source disagree

- **WHEN** the image builds with a `VALIDATE_AGENT_FILES_VERSION` that differs
  from the package's own version
- **THEN** the build fails

## Rationale

### The Dev Container image owns its lifecycle

A repository references or derives from `agentdev-devcontainer` instead of
copying lifecycle scripts, so every consumer runs the lifecycle that was tested.
PID 1 owns the persistent services; work whose timing PID 1 cannot observe stays
in three thin commands declared in the image's `devcontainer.metadata` label, so
every descriptor that selects the image inherits them, and the editor never
attaches to a container whose required services failed. A latched failure ends a
Dev Container, where a deploy container stays up for an explicit retry, because
an editor has no retry command and a running container with withdrawn readiness
looks healthy. The old `agent-desktop` and `agent-opencode` names are not
published as aliases: `agent-desktop` would name the lifecycle-neutral base,
which cannot run the new descriptor, so a consumer migrates either way.

Rejected:

- **A build-time per-file sha256 manifest of loose runtime scripts.** Replaced by
  the installed distribution's `RECORD`.
- **Loose standard-library scripts on the system interpreter.** They need a PyPI
  fetch at start or an apt dependency hunt.
- **Bash shims under the old `/opt/agentdev-runtime/*.sh` names.** Nothing
  outside the images calls those paths.
- **Porting the legacy no-supervisor starters.** A second start path with its
  own keyring, firewall, and Xpra handling that no caller needs.
- **Starting the supervisor in the background in the responder's container
  job.** It needs a privileged job container for `dockerd`.
- **Running the responder as a host job through `devcontainers/ci`.** It loses
  `claude-code-action` and its authentication.

### Extra CA trust goes through the system store

The proxy belongs to the host, and its CA rotates, so the bundle arrives at
start and the root bootstrap installs it into the system store, which the nested
`dockerd` and every OpenSSL tool read. uv, Python `requests`, Node, and Bun read
their own root stores, which is why the base image points three variables at the
system bundle. `NODE_EXTRA_CA_CERTS` is the host-side fallback because it means
"CAs added to the defaults", and hosts behind such proxies, Claude Code cloud
sessions among them, already export it. A rotated CA needs a container restart,
and containers the nested `dockerd` starts get no extra CA.

Rejected:

- **Mount the bundle over `/etc/ssl/certs/ca-certificates.crt`, or point
  `SSL_CERT_FILE` at it.** Both need a bundle carrying every public root, and the
  latter leaves `dockerd` untrusting.
- **Per-tool settings (`UV_SYSTEM_CERTS`, pip and npm config).** Each new tool
  is a new gap.
- **Copy the CA into the image at build time.** The CA is the host's and
  rotates.

### No Launchpad at build time

The `ppa:` shorthand of `apt_repository` fetches the signing key from the
Launchpad API at build time, and an apt source on `ppa.launchpadcontent.net`
makes every build depend on Launchpad's archive host, so an outage there failed
every image build. A package comes from the Ubuntu archive, else a vendor apt
repository with a `signed-by` keyring, else a checksummed pinned release
archive, else a PPA's packages republished unchanged here. The PPA keeps only
its newest build, so a release is the only lasting copy and is never replaced.

Rejected:

- **A `ppa.launchpadcontent.net` source with a pinned key.** It keeps the build's
  dependency on Launchpad.
- **Releases in a dedicated repository.** GitHub disables a public repository's
  schedules after 60 days without activity, and publishing there needs a
  cross-repository credential.
- **Pinned URLs into the PPA's pool.** The PPA deletes a build at its next
  upload.
- **Ubuntu's own git.** It trails upstream by the age of the Ubuntu release.
- **Building git from source in the image.** Over a minute per architecture and
  a Rust toolchain in every build.

### The validator ships in the image

A consumer that deletes `py_packages/validate_agent_files/`, as template
consumption requires, still needs a validator in the devcontainer and in CI.
Building from the build context keeps release coupling inside this repository
and matches how the catalog is staged; the image build therefore needs the
package in its build context. The role copies the source to a temporary
directory first, because the build context is mounted read-only and setuptools
writes `*.egg-info` beside the source.

Rejected:

- **Publish the validator to PyPI.** A name reservation, a release workflow, and
  trusted publishing, for a tool only this image consumes.
- **A task file inside `agentic_tools`.** A role of its own keeps one
  responsibility and its own toggle.
- **Install it into the system interpreter or a project environment.** `uv tool
install` touches neither.
