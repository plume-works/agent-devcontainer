---
type: spec
description: How the plume-works/coder-ide-baseline Coder template runs this repository's Dev Container, and how to change, validate, and ship a template version.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-20T15:00:00Z
sources:
- resource: https://github.com/plume-works/coder-ide-baseline/blob/ab1c595/template/main.tf
- resource: https://github.com/plume-works/coder-ide-baseline/blob/473d64a/template/main.tf
- resource: https://github.com/plume-works/coder-ide-baseline/blob/473d64a/root-container/daemon.json
- resource: https://github.com/plume-works/coder-ide-baseline/blob/ab1c595/template/push.sh
- resource: https://github.com/plume-works/coder-ide-baseline/blob/ab1c595/README.md
- resource: https://github.com/plume-works/coder-ide-baseline/blob/98f892b/template/main.tf
- resource: .devcontainer/scripts/coder-agent-start.sh
---

# Coder IDE baseline template

[plume-works/coder-ide-baseline](https://github.com/plume-works/coder-ide-baseline)
is the Coder template that runs this repository as a Dev Container. Its
`template/main.tf` is published to Coder as the template `coder-ide-baseline`.
The repository README covers the base image, Sysbox, and the `repo` sub-agent.
This spec records the contract between the template and this repository, and how
to work on the template.

## Requirements

### Requirement: the agent-start script is the repository's only start hook

The template SHALL run, on every start of the Dev Container's sub-agent, the
script that the `agent_start_script` workspace parameter names. The path is
relative to the repository root and defaults to
`.devcontainer/scripts/coder-agent-start.sh`. The script SHALL run under the
sub-agent, so it inherits the agent's environment, including Coder user secrets.
When the value is empty, or the path is not an executable file, nothing SHALL
run and the script's log SHALL say so. The template SHALL NOT name any other
script in this repository; new agent-start steps belong in
`coder-agent-start.sh`.

#### Scenario: the repository ships the script

- **WHEN** the workspace starts with the default parameter value
- **THEN** `coder-agent-start.sh` runs in the Dev Container with the Coder user
  secrets in its environment.

#### Scenario: another repository has no agent-start script

- **WHEN** the configured path does not exist in the checkout
- **THEN** the start script logs that the repository ships no agent-start script
  and exits without error.

### Requirement: Coder user secrets reach only agent-started processes

Dev Container lifecycle hooks (`postCreateCommand`, `postStartCommand`) run
inside `devcontainer up`, before Coder injects its agent into the container.
They SHALL NOT depend on Coder user secrets or on the agent's environment
(`GITHUB_TOKEN`, `CODER_*`, `GIT_ASKPASS`). Setup that needs them SHALL run from
the agent-start script.

#### Scenario: setup needs a user secret

- **WHEN** a setup step needs `GITHUB_TOKEN` supplied as a Coder user secret
- **THEN** it runs from `coder-agent-start.sh`, not from post-start.

### Requirement: start scripts never wait for the Dev Container

The agent starts declared Dev Containers only after every `coder_script` on the
outer agent has exited. A start script that needs the Dev Container SHALL detach
its wait (for example `setsid … &`) and return immediately; a blocking wait
deadlocks the workspace start.

#### Scenario: a script needs the running Dev Container

- **WHEN** a start script must act inside the Dev Container
- **THEN** it launches a detached worker that polls `devcontainer exec` and
  exits at once.

### Requirement: workspace state lives in per-workspace volumes

The home directory, `/var/lib/docker`, `/var/lib/containerd`, and the containerd
overlayfs snapshotter directory SHALL each be a Docker volume named after the
workspace ID, with `lifecycle { ignore_changes = all }`, so template changes
never replace them and a restart keeps the built Dev Container image. When a
template version adds a state volume, each workspace created before it SHALL be
reset once on the new version. The reset removes the stale Dev Container
container and runs `docker builder prune -af`, so Docker holds no records that
point at content the new, empty volume lacks.

#### Scenario: the workspace restarts

- **WHEN** a workspace whose Dev Container is built is restarted
- **THEN** the Dev Container comes back without a rebuild.

### Requirement: the workspace engine bounds its own storage

The workspace engine SHALL run with BuildKit garbage collection enabled and a 10
GB build-cache limit, from `/etc/docker/daemon.json` in the base image. The
`coder_agent` startup script SHALL, once Docker is ready, remove images that no
container references and that were created more than 72 hours ago. A failed
prune SHALL NOT fail the startup script.

#### Scenario: a stopped Dev Container's image survives the prune

- **WHEN** the workspace restarts and the startup script prunes before the Dev
  Container is started again
- **THEN** the Dev Container's image is kept, because its stopped container
  references it.

#### Scenario: an old image is unreferenced

- **WHEN** an image created more than 72 hours ago is referenced by no container
  at agent start
- **THEN** the startup script removes it.

### Requirement: the template offers an OpenCode app

The `coder-ide-baseline` template SHALL attach a subdomain `coder_app` named
`OpenCode` to the Dev Container's sub-agent of every workspace with a
repository. Its URL SHALL be the server root, `http://localhost:4096`, and its
healthcheck SHALL request `http://localhost:4096/site.webmanifest`. The server
it opens is specified in [OpenCode web](opencode-web.md).

#### Scenario: the repository runs OpenCode

- **WHEN** the repository's agent-start script started the OpenCode server
  (`opencode serve`)
- **THEN** the dashboard shows a healthy `OpenCode` app that loads the web UI,
  from whose project picker `/workspaces/<repository>` opens.

#### Scenario: the repository runs no OpenCode server

- **WHEN** nothing listens on port 4096 in the Dev Container
- **THEN** the `OpenCode` app shows unhealthy.

### Requirement: an active template version comes from `main`

Every template change SHALL merge to `main` by pull request; the ruleset
requires the `Docker Build and Push` check and linear history. The version
activated in Coder SHALL be pushed from the merge commit. A change that needs a
live probe before merge SHALL be pushed as a named, inactive draft version.

#### Scenario: probing a change before merge

- **WHEN** a change must be tried in a live workspace before it merges
- **THEN** it is pushed with `--activate=false` under a name, and a probe
  workspace is created from that version; active workspaces are not affected.

## Working on the template

### Checkout

In a Coder workspace, the template is cloned beside this repository at
`/workspaces/coder-ide-baseline` through the `second_repo` workspace parameter.

### Validate

Terraform is not installed in the Dev Container; run it from the
`hashicorp/terraform` image. `init` writes `.terraform/`, so `validate` runs in
a copy:

``` bash
cd /workspaces/coder-ide-baseline/template
docker run --rm -v "$PWD":/w -w /w hashicorp/terraform:1.13.5 fmt -check -diff
docker run --rm -v "$PWD":/src:ro --entrypoint sh hashicorp/terraform:1.13.5 -c \
  'cp -r /src /w && cd /w && terraform init -backend=false -input=false >/dev/null && terraform validate'
```

### Push a version

The Coder CLI is at `/.coder-agent/coder` inside the Dev Container and is not on
`PATH`. `template/push.sh` defaults `TEMPLATE_NAME` to `docker-in-docker`, a
different template, so always name `coder-ide-baseline`. `coder templates push`
activates the new version by default.

``` bash
export PATH="/.coder-agent:$PATH"

# Active version, from the merge commit on main:
TEMPLATE_NAME=coder-ide-baseline template/push.sh

# Inactive draft for a probe, then a workspace on it:
coder templates push coder-ide-baseline --directory template \
  --activate=false --name <draft-name> --yes
coder create <probe-workspace> --template coder-ide-baseline \
  --template-version <draft-name>

coder templates versions list coder-ide-baseline
```

### Roll out and verify

After a new version is activated, existing workspaces report as outdated until
`coder update <workspace>`, which restarts them. A restart ends every session
running inside that workspace, including an agent's own. An agent therefore
verifies restart behavior in a different workspace, such as a probe, or hands
the restart to the operator.

Run `coder update <workspace>` from a different workspace or machine, never from
inside the target. The CLI sends a stop build, then a start build, and the stop
ends the CLI with the workspace, so a self-update leaves it stopped and still
outdated. Recover with `coder update <workspace>` from elsewhere.

A workspace that has not yet restarted on a version that runs
`coder-agent-start.sh` has no github.com credential helper. There, `git push`
over HTTPS hangs on Coder's `GIT_ASKPASS` ([Bug: HTTPS git push hangs on Coder's
askpass when gh's login is only a session
token](../bugs/coder-askpass-push-hang.md)). Push with a one-off helper instead,
which changes no git config:

``` bash
GIT_ASKPASS= git -c credential.helper= \
  -c 'credential.helper=!gh auth git-credential' push
```
