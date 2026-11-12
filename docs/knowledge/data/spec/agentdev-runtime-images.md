---
type: spec
description: The agentdev image family — a lifecycle-neutral agentdev-base and sibling agentdev-deploy and agentdev-devcontainer runtimes — how they are provisioned and trust a host's extra CA, and the runtime CLI, supervised services, lifecycle phases, and hook interface the Dev Container image gives consumers without copied lifecycle scripts.
sources:
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
- resource: docker/deploy/agentdev-deploy.Dockerfile
- resource: docker/devcontainer/agentdev-devcontainer.Dockerfile
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
- resource: .agents/plugins/agentdev/skills/template-consume/SKILL.md
- resource: .dockerignore
- resource: .github/actions/docker/build-push-action/action.yml
- resource: ansible/roles/github_cli/tasks/main.yml
---

# agentdev runtime images

The image family for the [Reusable agentdev Dev
Container](../features/reusable-agentdev-devcontainer.md) feature. The deploy
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

### Requirement: the runtime is one CLI installed as a uv tool

The runtime of `agentdev-deploy` and `agentdev-devcontainer` SHALL be the one
`agentdev_runtime` package and its one console script, `agentdev-runtime`: PID 1
and its supervisor, the health probes, every supervised service, the lifecycle
commands, the bootstrap, and the firewall SHALL be its subcommands. Both images
SHALL install it from the build context with
`uv tool install --reinstall --python /usr/bin/python3` into `/opt/uv-tools`,
with the entry point on `/usr/local/bin`, no uv cache, and no interpreter
download. The package SHALL pin its dependencies, `supervisor` among them, so
the images carry no apt `supervisor` and nothing resolves a dependency at
container start.

#### Scenario: a runtime container starts

- **WHEN** an `agentdev-deploy` or `agentdev-devcontainer` container starts
- **THEN** PID 1 is `/usr/local/bin/agentdev-runtime supervisor run`, and every
  module it runs was installed at build time

### Requirement: the base image carries the agent-file validator

`agentdev-base` SHALL install `validate_agent_files`, built from the
`py_packages/validate_agent_files/` of the build context, as an isolated uv tool
under `/opt/uv-tools` on the system interpreter, with its entry point at
`/usr/local/bin/validate_agent_files`. The build SHALL fail unless the installed
distribution's version equals `VALIDATE_AGENT_FILES_VERSION`, which the image
carries as its `org.opencontainers.image.version.validate-agent-files` label.

#### Scenario: a non-root user validates without a checkout

- **WHEN** the non-root runtime account runs `validate_agent_files --help` in a
  container from the image, with no repository checked out and no `uv run`
- **THEN** the command resolves on `PATH` and exits 0

#### Scenario: the pin and the package disagree

- **WHEN** `VALIDATE_AGENT_FILES_VERSION` differs from the version in
  `py_packages/validate_agent_files/pyproject.toml`
- **THEN** the image build fails naming both versions

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

#### Scenario: the newest build is already released

- **WHEN** a `pinned-deps/git/<version>` release exists for the PPA's newest
  build
- **THEN** the workflow leaves it unchanged

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
with deploy. OpenCode and Remote Control SHALL be opt-in clients that start only
after the create phase finishes and never gate readiness.

#### Scenario: an editor attaches to a healthy runtime

- **WHEN** the Dev Container start lifecycle waits for runtime readiness
- **THEN** attachment proceeds only after every required service reports ready

#### Scenario: a required service exhausts recovery

- **WHEN** a required service cannot recover within its configured budget
- **THEN** readiness is withdrawn, the failure names the service, and the
  container exits nonzero

#### Scenario: an opt-in client fails

- **WHEN** OpenCode or Remote Control is enabled and fails
- **THEN** the runtime is degraded, not failed, and readiness stays published

### Requirement: the Dev Container runs as a non-root account on one home volume

The Dev Container image SHALL run its user services, lifecycle commands, and
editor sessions as a non-root account remapped to the host user's UID and GID,
with its home on one per-instance volume. Its create phase SHALL run under the
supervisor after the root bootstrap, once per container, and gate readiness;
`postCreateCommand` SHALL wait for it and fail when the runtime fails first.

### Requirement: lifecycle phases remain distinct

The image SHALL provide stable create, start/readiness, and attach commands —
`agentdev-runtime lifecycle created`, `agentdev-runtime lifecycle ready`, and
`agentdev-runtime lifecycle attached`, published through the image's Dev
Container metadata — and SHALL NOT move create-once or attach-scoped work into
the entrypoint. The same `devcontainer.metadata` label SHALL set `waitFor` to
`postStartCommand`, `overrideCommand` to `false`, `DEV_WORKSPACE_FOLDER` to the
container workspace folder through `containerEnv`, and a per-container volume at
`/var/lib/docker`. `agentdev-runtime lifecycle ready --no-wait` SHALL run the
per-start repairs without waiting for supervised services, so a container with
no supervisor as PID 1 — the Claude responder's GitHub `container:` job — runs
`created`, `ready --no-wait`, and `attached` and starts no service.

#### Scenario: a descriptor selects the image and declares no lifecycle

- **WHEN** a Dev Container client starts a descriptor that selects
  `agentdev-devcontainer`
- **THEN** the client keeps the image entrypoint, runs the three lifecycle
  commands, and attaches only after `postStartCommand` finishes

#### Scenario: a job runs the image without its entrypoint

- **WHEN** the responder's container job runs the lifecycle commands with
  `ready --no-wait`
- **THEN** the checkout's catalog is installed and no keyring, firewall, Docker
  engine, or desktop starts

#### Scenario: only the attach lifecycle runs

- **WHEN** an attach-only lifecycle event occurs
- **THEN** attach-scoped catalog and index refresh runs without rerunning
  create-once initialization or restarting supervised services

### Requirement: consumers do not copy lifecycle implementation

A direct or derived consumer SHALL be able to obtain the complete managed
lifecycle by referencing `agentdev-devcontainer` and SHALL customize it through
documented environment values and executable files in explicit ordered hook
directories. The documented environment SHALL be the variables
`agentdev_runtime.settings` declares, each with one default, which
`agentdev-runtime settings` prints. The executable files in
`/etc/agentdev/hooks/{created,started,attached}.d/` SHALL run in C-locale name
order at the end of their phase, and a failing hook SHALL fail the phase; a hook
directory that resolves inside the workspace SHALL be refused.

#### Scenario: a hook fails

- **WHEN** a hook in `started.d` exits nonzero
- **THEN** `agentdev-runtime lifecycle ready` fails naming the hook and its exit
  status

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
root bootstrap SHALL, before anything else, refuse to run when a file its
`RECORD` lists differs from the recorded hash or is missing, or a file other
than a recorded module's bytecode was added beside the recorded files, and SHALL
name the file and direct the consumer to the hook directories and documented
environment. A source checkout, whose egg-info records no files, is not checked.
The check catches accidental or partial edits to the runtime and is not a
security boundary: a derived image that deliberately deletes the distribution's
metadata or rewrites its `RECORD` passes it.

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

### Requirement: each checkout has its own project environment

The Dev Container SHALL give every checkout of the workspace repository,
including each Git worktree, its own uv project environment: `.venv` in the
checkout SHALL be a link to a directory named after the checkout under
`AGENTDEV_VENV_ROOT` (`/home/agent/.local/share/uv/venvs` in
`agentdev-devcontainer`, else `/uv/venvs`), on the same volume as the uv cache.
The create phase SHALL register `agentdev-runtime worktree create` and
`agentdev-runtime worktree remove` as the user's Claude `WorktreeCreate` and
`WorktreeRemove` hooks. The link SHALL exist before a worktree's first command
when the worktree is made by `git worktree add` or by that `WorktreeCreate`
hook, and the attach phase SHALL create it for the workspace folder. The
`WorktreeRemove` hook SHALL delete the environment of the worktree it removes;
attach SHALL keep every environment named after a listed checkout or linked from
the `.venv` of any checkout, in any repository, and remove the rest.

#### Scenario: two worktrees run uv at once

- **WHEN** two worktrees with different versions of the project's packages run
  `uv run` concurrently
- **THEN** each imports its own checkout's packages, and neither sync changes
  the other's environment

#### Scenario: an agent creates a worktree

- **WHEN** a Claude Code session or a worktree-isolated subagent starts in a new
  worktree
- **THEN** the worktree is at `.claude/worktrees/<name>` on branch
  `worktree-<name>`, and its `.venv` links to its own environment before the
  session starts

#### Scenario: a worktree name is used again

- **WHEN** `WorktreeCreate` fires with a name used before, such as a session
  Remote Control revives
- **THEN** the hook reuses that name's worktree, or checks out its kept
  `worktree-<name>` branch when the worktree was removed, and prints its path

#### Scenario: Claude Code removes a worktree

- **WHEN** Claude Code removes a worktree its `WorktreeCreate` hook made
- **THEN** that worktree's environment directory is deleted at once, and its
  `worktree-<name>` branch is kept

#### Scenario: a worktree is removed outside Claude Code

- **WHEN** a worktree is removed with `git worktree remove` and the workspace is
  next attached
- **THEN** its environment directory is deleted, and no environment a checkout
  of any repository still links to is touched

#### Scenario: a consumer sets no environment root

- **WHEN** a consumer of `agentdev-devcontainer` that sets no
  `AGENTDEV_VENV_ROOT` attaches to a Python checkout
- **THEN** the checkout's `.venv` links to its directory under
  `/home/agent/.local/share/uv/venvs`, on the home volume that holds uv's cache

### Requirement: full adoption remains supported

`template-consume` SHALL remain a supported full-adoption workflow whose adopted
Dev Container uses the published runtime image; minimal adoption SHALL not be a
prerequisite for full adoption.

#### Scenario: an existing full-adoption repository updates

- **WHEN** it follows the supported template-consume update path
- **THEN** its repository-owned customization is preserved and its managed
  runtime resolves through the published image contract

## Rationale

### One runtime package behind one CLI

The runtime images run one Python package, `agentdev_runtime`, installed as a uv
tool the way the validator is, with its dependencies pinned in the package.
`agentdev-base` never carries it, so the base stays lifecycle-neutral.

Rejected:

- **Loose standard-library scripts on the system interpreter.** Keeps either a
  PyPI fetch at container start or an apt dependency hunt, and needs a separate
  per-file checksum manifest for integrity.
- **Bash shims under the old `/opt/agentdev-runtime/*.sh` names.** Nothing
  outside the images calls those paths, and one CLI replaces them.
- **Keeping the firewall script as bash behind a Python wrapper.** The policy is
  one module whose rule sequence is under test.

### Runtime integrity is the distribution's own `RECORD`

A derived image that replaced, added, or removed a runtime file would run
lifecycle code nobody tested, so the bootstrap refuses it and names the hook
directories and documented environment instead. The installed wheel's `RECORD`
already holds every file's hash, so no second manifest is built or maintained.
The check catches accidental and partial edits; it is not a security boundary.

Rejected:

- **A build-time per-file checksum manifest.** A second record of what `RECORD`
  already holds, written by its own build step.

### A container with no supervisor runs only the lifecycle commands

A GitHub `container:` job runs no image entrypoint and accepts no
`--entrypoint`, and `claude-code-action` is a composite action that runs in the
job's own runtime, so the supervisor can never be PID 1 there. The job needs the
checkout's catalog, never the keyring, the firewall, or a desktop.

Rejected:

- **Porting the legacy no-supervisor starters.** Preserves a second start path
  with its own keyring, firewall, and Xpra handling that no caller needs.
- **Starting the supervisor in the background inside the responder's container
  job.** Needs a privileged job container for the profile's core `dockerd`, and
  buys only the removal of the `--no-wait` path.
- **Running the responder as a host job through `devcontainers/ci`.** Gives the
  supervisor PID 1 but loses `claude-code-action` and its `claude[bot]`
  authentication.

### PID 1 owns the create phase; the image label owns the lifecycle commands

The create phase needs what the root bootstrap prepares — the runtime account's
sudoers entry, its home, and the shared auth directory — so it runs as a
supervised oneshot after the bootstrap, as the deploy profile's `prepare` does,
and `postCreateCommand` only waits for it. Work whose timing PID 1 cannot
observe stays in three thin commands declared in the image's metadata label, so
every descriptor that selects the image inherits them; a descriptor that also
declares them runs each twice.

### A latched failure ends a Dev Container

A deploy container stays up for an explicit retry; a Dev Container exits. An
editor has no retry command, and a container that keeps running with withdrawn
readiness looks attached and healthy.

### No aliases for the retired image names

`agent-desktop` and `agent-opencode` are not published as aliases.
`agent-desktop` would have to name the lifecycle-neutral base, which cannot run
the new descriptor, so a consumer needs the same migration either way and an
alias only adds a second name to maintain. Full-adoption consumers move through
`/agentdev:template-consume` update mode.

### Extra CA trust goes through the system store

A host behind a TLS-intercepting proxy hands its CA bundle over as a file, and
the root bootstrap adds it to the system store before any service starts.
`SSL_CERT_FILE`, `REQUESTS_CA_BUNDLE`, and `NODE_EXTRA_CA_CERTS` point at the
system store because uv, Python `requests`, Node, and Bun otherwise read their
own root stores; with no extra CA they name the stock bundle and change nothing.
The nested `dockerd` reads the system store, so image pulls are covered without
a daemon setting. `NODE_EXTRA_CA_CERTS` is the host-side fallback because it
means "CAs added to the defaults", which is exactly this bundle, and hosts
behind such proxies, Claude Code cloud sessions among them, already export it.
Containers the nested engine starts are out of scope: trusting the CA is their
image's business.

Rejected:

- **Mounting the bundle over `/etc/ssl/certs/ca-certificates.crt`.** Works only
  when the bundle also carries every public root, and hides the image's own
  store.
- **Pointing `SSL_CERT_FILE` at the mounted bundle.** The same dependence on a
  complete bundle, and the nested `dockerd` and every OpenSSL tool reading the
  hashed store stay untrusting.
- **Per-tool settings (`UV_SYSTEM_CERTS`, pip and npm config).** One per tool,
  and each new tool is a new gap.
- **Copying the CA into the image at build time.** The proxy belongs to the
  host, not the image, and its CA rotates.

### Packages come from sources that are not Launchpad

A package comes from one of four sources, in this order of preference: the
Ubuntu archive; the vendor's own apt repository with its key under a `signed-by`
keyring; a pinned release archive with a SHA-256 per architecture through
`dev_tools_pinned_tools`; or a PPA's packages republished unchanged as
`pinned-deps/<name>/<version>` releases of this repository, pinned by tag and
SHA-256. The `ppa:` shorthand fetches the signing key from the Launchpad API at
build time, and an apt source on `ppa.launchpadcontent.net` makes every build
depend on Launchpad's archive host. The PPA keeps only its newest build, so a
release is the only lasting copy of one, which is why the workflow never
replaces a release. The image carries the PPA's git because Ubuntu's trails the
upstream release.

Rejected:

- **An apt source on `ppa.launchpadcontent.net` with a pinned key.** Removes the
  Launchpad API call but keeps the build's dependency on Launchpad.
- **Releases in a dedicated repository.** GitHub disables a public repository's
  scheduled workflows after 60 days without activity, which a repository holding
  only releases reaches, and publishing there from this repository needs a
  cross-repository credential.
- **Pinned URLs into the PPA's pool.** The PPA deletes a build once a newer one
  is published, so every pin breaks at its next upload.
- **Ubuntu's own git.** It trails the upstream release by the age of the base
  image's Ubuntu release.
- **Building git from its kernel.org source release in the image.** Adds a
  compile of over a minute per architecture and a Rust toolchain to every build.

### The validator is built from the build context

`validate_agent_files` is built from the build context, as the catalog is
staged, so the image and its validator come from the same commit and its release
stays inside this repository. The image build therefore needs
`py_packages/validate_agent_files/` in the build context. Its version is a pin
the build verifies against the installed distribution, so the image label states
what the image carries rather than what the source claimed.

Rejected:

- **Publishing the validator to PyPI.** Needs a package name, a release
  workflow, and trusted publishing, and splits the validator's release from the
  image's.
- **A task file inside `agentic_tools`.** A role of its own keeps one
  responsibility, its own `install_validate_agent_files` toggle, and its own
  variables, as every other tool in the image has.
- **The system interpreter or a project environment.** A uv tool puts one entry
  point on `PATH` and touches neither.
