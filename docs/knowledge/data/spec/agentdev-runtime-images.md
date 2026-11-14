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

### Requirement: the base image is lifecycle-neutral

`agentdev-base` SHALL contain the shared development tools, agentdev catalog,
and default policy without containing deploy or Dev Container lifecycle
implementation; it SHALL NOT carry the `agentdev_runtime` package.

#### Scenario: a consumer runs the base image directly

- **WHEN** a consumer starts `agentdev-base` with its own command
- **THEN** the tools and staged catalog are available, and no agentdev runtime
  supervisor or workspace lifecycle starts implicitly

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

### Requirement: uv and pre-commit state lives on the home volume

Neither runtime image SHALL move uv's cache, uv's Python installs, or
pre-commit's cache away from their default paths under the runtime account's
home, so they persist on its home volume. `agentdev-deploy` SHALL set
`UV_PROJECT_ENVIRONMENT` to `/home/agent/.local/share/uv/venvs/project`.

#### Scenario: a deploy container is recreated on the same home volume

- **WHEN** an `agentdev-deploy` container is recreated with its home volume kept
- **THEN** the project environment, uv's cache, and its Python installs are
  still present under `/home/agent`

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
`agentdev-base` never carries it, so the base stays lifecycle-neutral. The
package is not published to PyPI: the two runtime images are its only installs.

Three scripts stay shell, outside the package, because each runs where the
package cannot: `.devcontainer/devcontainer-init.sh` runs on the host as the
initialize command, where Python is not guaranteed;
`docker/ansible/setup-ansible.sh` runs before the toolchain exists; and
`docker/desktop/entrypoint.sh` is the entrypoint of `agentdev-base`, which never
carries the package.

A `language: system` pre-commit hook whose executable is missing is a warning,
not a failure, in both profiles, so a consumer whose own hooks need tools the
image lacks still starts.

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
  supervisor PID 1 but loses `claude-code-action` and the GitHub App
  authentication it carries.

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

### The build context is an allow-list and each step binds only its inputs

BuildKit keys a `RUN` step on the contents of its bind mounts, so a step that
binds the whole build context is invalidated by any repository change and the
layer cache never hits. `.dockerignore` therefore admits only the image inputs,
and each provisioning step bind-mounts only the inputs it reads.

### Xpra is installed by name from the stable repository

No Xpra apt repository serves an exact pinned version: for noble,
`https://xpra.org/lts` serves 5.1.x and `https://xpra.org` the current 6.x
stable. The role therefore installs `xpra` by name from the stable repository,
and the major-version assertion catches a fallback to Ubuntu's 3.x.

Rejected:

- **Xpra's `setup.py install-lts-repo`.** It ignores its own step failures, and
  the LTS repository serves 5.1.x.

### fish plugins are reconciled through `fish_plugins`

`fisher install <owner>/<repo>@<ref>` refuses to overwrite files it does not
track under that exact spec, so it fails on a system holding the same plugin
under another spec. The `fish_setup` role writes the pinned specs into
`fish_plugins` and runs `fisher update`, which reconciles the tree to that file
from an empty system and from one holding the plugins under a different spec.

Rejected:

- **`fisher install` of each pinned spec.** It fails when a plugin is already
  installed under a different spec.

### OpenCode is installed as a trusted Bun package

The `@opencode/cli` package fetches its platform binary in a postinstall, which
Bun blocks until the package is trusted, so `agentic_tools` installs it with
`trust: true` and every other agent CLI without.

Rejected:

- **Installing `@opencode/cli` untrusted.** The postinstall never runs and the
  image ships no OpenCode binary.

### The session bus address is an image `ENV`

`gh` looks its token up in the Secret Service on every call. With no session bus
address in its environment, the D-Bus client library autolaunches a new bus
through `dbus-launch`, the lookup activates a fresh `gnome-keyring-daemon`, and
neither exits. Every process — supervised programs, `docker exec` shells, the VS
Code server, agent sessions — must therefore inherit one fixed address, and only
an image `ENV` reaches them all.

Rejected:

- **A random bus address published in a file that scripts source.** Only the
  processes that source it name the bus; every other `gh` call leaks a bus and a
  keyring.

### `agentdev-base` provisions in three tagged steps from a stable parent digest

The most frequent image change is a catalog edit, so provisioning is three `RUN`
steps selected by Ansible tag, each mounting only its inputs, and a catalog edit
reruns only the catalog step. `entrypoint.sh` is a narrow `COPY` from `docker/`,
because a role would make host provisioning carry a container entrypoint it
never uses. Each step sets `ANSIBLE_LOG_PATH=` because `ansible.cfg`'s
`log_path` resolves inside the read-only `/provision` mount. `agentdev-base`
starts from `ubuntu-ansible` by digest, so that digest must not change per run:
`ubuntu-ansible` is built without the per-run labels, and `agentdev-base` is
passed the per-architecture manifest digest, not the pushed index's, whose
provenance attestation changes every run.

Rejected:

- **One provisioning step behind the `.dockerignore` allow-list.** A catalog
  edit would reprovision every role.
