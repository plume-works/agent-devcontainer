---
created: 2026-08-17
description: Install the agentdev catalog into the agent-desktop image at build time so a raw-image consumer resolves agentdev skills without running devcontainer lifecycle hooks.
generated:
  by: claude-code/opus-5
  at: 2026-08-17T00:00:00Z
---

# Install the agentdev catalog into the image

## Context

The `agent-desktop` image stages the `agentdev` catalog at `/opt/agentdev` but
never installs it: the marketplace is not registered and the plugin cache under
`~/.claude` is empty. Installation belongs to the devcontainer lifecycle
scripts, because `~/.claude` and `~/.codex` are usually mounted as volumes that
shadow whatever the build wrote.

A consumer that starts the image *without* those hooks — a plain `docker run`, a
Codespace, a CI job — therefore gets a catalog that is present on disk and
unusable. The failure is quiet: an agent asked for a skill that does not resolve
improvises instead of failing.

This was first raised as a prerequisite for the AI responder workflow and then
withdrawn from it. That plan's responder checks out the branch and runs the
lifecycle hooks, which is both sufficient and better for its purpose — it gets
the branch's own catalog. See
[CI agent plugin availability](../architecture/ci-agent-plugin-availability.md)
for that reasoning.

So this work is no longer on any consumer's critical path. It closes a real gap
for raw-image consumers, but nothing currently blocked depends on it.

## Approach

`agentic_tools` gains an install step after staging, for both Claude and Codex,
mirroring what `postCreate` already does. The install runs as the same user the
rest of the provisioning runs as — `user_home` is `ansible_facts['env'].HOME`,
i.e. `/root`, which is also the `$HOME` a raw-image consumer runs as, since the
Dockerfile declares no `USER`. The marketplace is added from a local path, so
the build needs no auth and stays offline.

The devcontainer path is unaffected in the directories that matter: its volumes
mount over `/root/.claude` and `/root/.codex`, so the image's install is not
visible there and `postCreate` installs into the volumes exactly as today.

`~/.claude.json` is the one shared surface and the main risk this plan carries.
It cannot be volume-backed (Docker volumes are directory-backed), so
`postCreateCommand.sh:52-59` persists it inside the volume and symlinks it into
place. Today the image ships no such file and a fresh volume takes the `elif`
branch, starting from `{}`. After this change the image *will* ship one, so the
`mv` branch fires instead and seeds the volume from the image — a behavior
change to the devcontainer path caused entirely by the image, with no
devcontainer script changing. Task 3 verifies both volume states rather than
assuming it is benign.

Rejected: having each raw-image consumer install the catalog itself as an
explicit step (duplicates logic the lifecycle scripts own, and leaves the image
carrying a catalog that looks installed but is not).

## Implementation Steps

### Task 1: Add the install task to agentic_tools

**Files:** Create: `ansible/roles/agentic_tools/tasks/install_catalog.yml`;
Modify: `ansible/roles/agentic_tools/tasks/main.yml`,
`ansible/roles/agentic_tools/defaults/main.yml`,
`ansible/roles/agentic_tools/tasks/stage_catalog.yml` (comments only)

- [ ] Add `agentic_tools_install_catalog` (default `false`) to the role
  defaults, gating the new task file the way `agentic_tools_stage_catalog` gates
  staging
- [ ] Write `install_catalog.yml` registering the staged root as a marketplace
  and installing the plugin for Claude at user scope and for Codex, reading the
  marketplace and plugin names from the manifests rather than hardcoding them
- [ ] Import `install_catalog.yml` from `main.yml` after the staging import,
  guarded by both `agentic_tools_install_catalog` and
  `agentic_tools_stage_catalog` (installing without staging is incoherent)
- [ ] Correct the comments in `stage_catalog.yml:2-7` and on
  `agentic_tools_stage_catalog` that assert the install cannot happen at build
  time
- [ ] `uv run ansible-lint ansible` and
  `uv run ansible-playbook --syntax-check ansible/playbooks/setup-dev.yml` pass
  from the repository root

### Task 2: Turn the install on and correct the documentation

**Files:** Modify: `docker/desktop/agent-desktop.Dockerfile`,
`ansible/roles/agentic_tools/README.md`

- [ ] Pass `agentic_tools_install_catalog=true` in the Dockerfile's
  `ansible-playbook` invocation
- [ ] Correct the `ENV AGENTDEV_CATALOG_DIR` comment block
  (`agent-desktop.Dockerfile:62-67`), which states the catalog is "only staged
  here, never installed"
- [ ] Rewrite the README's staged-catalog rationale: staging and installing both
  happen now, the volume-shadowing explanation stays as the reason `postCreate`
  must *also* install, and link the architecture doc

### Task 3: Prove it, including both volume states

**Files:** none — verification only

Stands alone: its evidence is a real image build, which the session writing
Tasks 1-2 cannot produce by editing files.

- [ ] Build `agent-desktop` locally through `/agentdev:microvm-sandbox`
- [ ] Run a container from the built image with **no** volumes mounted and
  confirm `claude plugin list` shows `agentdev` installed, and that a Codex
  skill resolves too
- [ ] Start a devcontainer on a **fresh** volume and confirm the
  `~/.claude.json` handoff is correct: the `mv` branch now fires where the
  `elif` used to, and `codebase-memory-mcp-install.sh` (which runs before the
  symlink exists, `postCreateCommand.sh:42`) still behaves when `~/.claude.json`
  is a real file rather than absent
- [ ] Start a devcontainer on an **existing** volume and confirm the image's
  `~/.claude.json` is ignored (`/root/.claude.json` is already a symlink, so
  both branches skip) and a workspace skill edit still wins on attach

## Spec changes

[Catalog lifecycle](../spec/catalog-lifecycle.md) — its first requirement
forbids exactly what this plan does. The contract-heavy form applies: the
requirement is reversed rather than extended, and its scenario set changes.

``` markdown
## MODIFIED Requirements

### Requirement: the catalog is installed at image build time and again by postCreateCommand

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state during the image build, at Claude user scope and via
Codex's own registration, so a consumer that runs the image without devcontainer
lifecycle hooks resolves `agentdev:*` skills. `postCreateCommand.sh` SHALL also
install it, because a mounted `~/.claude` / `~/.codex` volume shadows what the
image build wrote.

#### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `ghcr.io/plume-works/agent-desktop` and no
  lifecycle hook runs
- **THEN** the catalog installed during the image build is present, and an
  `agentdev:*` skill resolves.

#### Scenario: a devcontainer starts for the first time on a fresh volume

- **WHEN** `postCreateCommand` runs and `$AGENTDEV_CATALOG_DIR` exists
- **THEN** `reinstall-agentdev-codex.sh` and
  `reinstall-agentdev-claude.sh ... user` install the staged catalog into the
  newly created `agentdev-claude` / `agentdev-codex` volumes.

#### Scenario: a devcontainer starts with a catalog already installed on its volume

- **WHEN** the `agentdev-claude` / `agentdev-codex` volumes already contain a
  prior install (they persist per devcontainer instance)
- **THEN** the volume mount shadows the image-build install, and
  `postCreateCommand` re-applies it every time the container is created, so it
  is never silently stale.
```

The other two requirements in that spec — the attach-time workspace override and
the credentials-only sharing — are unaffected and unchanged.

## Depends on

None. Deliberately independent of
[AI responder workflows](20260816-ai-responder-workflows.md): that plan was
revised to use the checkout instead, so neither blocks the other and they touch
no common files.

## Verification

- `uv run ansible-lint ansible` and
  `uv run ansible-playbook --syntax-check ansible/playbooks/setup-dev.yml` pass
  from the repository root (Task 1).
- A locally built image, run as a plain container with no volumes, reports
  `agentdev` in `claude plugin list` and resolves a Codex skill (Task 3).
- A devcontainer on a fresh volume completes `postCreate` without error and ends
  with a coherent `~/.claude.json` (Task 3).
- A devcontainer on an existing volume ignores the image's `~/.claude.json` and
  still picks up a workspace skill edit on attach (Task 3).

## Out of scope

- **Changing what the devcontainer lifecycle scripts do.** They keep installing
  unconditionally; this plan only adds a second, earlier install for consumers
  that never run them.
- **The AI responder workflows.** They use the checkout and do not depend on
  this.
- **Making `~/.claude.json` volume-backed.** Docker volumes are
  directory-backed; the symlink workaround stays.

## Key references

Verified anchor points (line numbers as of 2026-08-17):

- `ansible/roles/agentic_tools/tasks/main.yml:26` —
  `Stage the agent catalog into the image`, the import the install follows
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:2-7` — the header comment
  asserting this is "not an installation"
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:123` —
  `Make the staged catalog root-owned and read-only`, the last staging task
- `ansible/roles/agentic_tools/defaults/main.yml:26` —
  `agentic_tools_stage_catalog`, whose comment says the install belongs to
  lifecycle scripts
- `ansible/roles/agentic_tools/defaults/main.yml:45` —
  `agentic_tools_catalog_root: /opt/agentdev`
- `ansible/roles/extra_facts/tasks/main.yml:16` — `user_home` resolves from
  `ansible_facts['env'].HOME`, i.e. `/root`
- `docker/desktop/agent-desktop.Dockerfile:54` —
  `agentic_tools_stage_catalog=true`, where the install flag joins
- `docker/desktop/agent-desktop.Dockerfile:62-67` — the
  `ENV AGENTDEV_CATALOG_DIR` comment claiming the catalog is never installed
- `.devcontainer/scripts/postCreateCommand.sh:42` —
  `codebase-memory-mcp-install.sh`, which runs before the symlink exists
- `.devcontainer/scripts/postCreateCommand.sh:52-59` — the `~/.claude.json`
  move-and-symlink whose branch selection this plan changes
- `.devcontainer/scripts/postCreateCommand.sh:77-79` — the existing lifecycle
  install this one mirrors
- `.github/actions/paths-filter/action.yml:38` — `ansible/**`, so the change
  triggers a CI image rebuild
