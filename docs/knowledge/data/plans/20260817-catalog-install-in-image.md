---
type: plan
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
`postCreateCommand.sh:67-73` persists it inside the volume and symlinks it into
place. Today the image ships no such file, so on first start
`/root/.claude.json` is absent: `codebase-memory-mcp-install.sh` creates it
fresh with just its MCP entry, then the handoff takes the `elif` branch and the
volume starts from that `{}`-plus-MCP file. After the build-time install, the
image *will* ship a real `/root/.claude.json`. Left in place it would poison
this sequence: cbm-install runs before the handoff (`postCreateCommand.sh:56`)
and, because the file is not yet a symlink, writes its MCP entry straight into
the image's file rather than a clean one; the handoff's `mv` then carries that
combined file into the volume, clobbering an existing volume's `claude.json` on
every rebuild and seeding a fresh volume from image content. The mounted volume
is the source of truth for Claude files, so postCreate removes the image's
`/root/.claude.json` before cbm-install runs (guarded to a real, non-symlink
file, so an existing volume's symlink is never disturbed). That restores the
pre-image behavior exactly: no `/root/.claude.json` exists when cbm-install
runs, so a fresh volume is seeded clean and an existing volume keeps its
accumulated state. Task 3 verifies both volume states.

Rejected: having each raw-image consumer install the catalog itself as an
explicit step (duplicates logic the lifecycle scripts own, and leaves the image
carrying a catalog that looks installed but is not).

## Implementation Steps

### Task 1: Add the install task to agentic_tools

**Files:** Create: `ansible/roles/agentic_tools/tasks/install_catalog.yml`;
Modify: `ansible/roles/agentic_tools/tasks/main.yml`,
`ansible/roles/agentic_tools/defaults/main.yml`,
`ansible/roles/agentic_tools/tasks/stage_catalog.yml` (comments only)

- [x] Add `agentic_tools_install_catalog` (default `false`) to the role
  defaults, gating the new task file the way `agentic_tools_stage_catalog` gates
  staging
  - **Evidence:** `ansible/roles/agentic_tools/defaults/main.yml` now declares
    `agentic_tools_install_catalog: false` with a comment pointing at the spec
    and architecture docs; committed on `skills-updates`.
- [x] Write `install_catalog.yml` registering the staged root as a marketplace
  and installing the plugin for Claude at user scope and for Codex, reading the
  marketplace and plugin names from the manifests rather than hardcoding them
  - **Evidence:** `ansible/roles/agentic_tools/tasks/install_catalog.yml` slurps
    the staged Claude and Codex marketplace manifests, resolves each marketplace
    name via `from_json`, then runs
    `claude plugin marketplace add/install --scope user` and
    `codex plugin marketplace add`/`plugin add`; plugin name comes from
    `agentic_tools_plugin_name`. Mirrors
    `.devcontainer/scripts/reinstall-agentdev-{claude,codex}.sh`.
- [x] Import `install_catalog.yml` from `main.yml` after the staging import,
  guarded by both `agentic_tools_install_catalog` and
  `agentic_tools_stage_catalog` (installing without staging is incoherent)
  - **Evidence:** `ansible/roles/agentic_tools/tasks/main.yml` imports
    `install_catalog.yml` immediately after the `stage_catalog.yml` import,
    under
    `when: [agentic_tools_stage_catalog | bool, agentic_tools_install_catalog | bool]`.
- [x] Correct the comments in `stage_catalog.yml:2-7` and on
  `agentic_tools_stage_catalog` that assert the install cannot happen at build
  time
  - **Evidence:** `stage_catalog.yml`'s header now says staging is a plain copy
    that `install_catalog.yml` installs from at build time so a raw-image
    consumer resolves with no hooks; the `agentic_tools_stage_catalog` comment
    in `defaults/main.yml` no longer claims install belongs only to lifecycle
    scripts.
- [x] `uv run ansible-lint ansible` and
  `uv run ansible-playbook --syntax-check ansible/playbooks/setup-dev.yml` pass
  from the repository root
  - **Evidence:** both run from the repo root exit 0 —
    `uv run ansible-lint ansible` clean (no findings), and the syntax check
    reports only pre-existing `apt_repository` deprecation warnings in unrelated
    roles.

### Task 2: Turn the install on and correct the documentation

**Files:** Modify: `docker/desktop/agent-desktop.Dockerfile`,
`ansible/roles/agentic_tools/README.md`

- [x] Pass `agentic_tools_install_catalog=true` in the Dockerfile's
  `ansible-playbook` invocation
  - **Evidence:** `docker/desktop/agent-desktop.Dockerfile` now passes
    `agentic_tools_install_catalog=true` on the line after
    `agentic_tools_stage_catalog=true` in the `ansible-playbook -e` block.
- [x] Correct the `ENV AGENTDEV_CATALOG_DIR` comment block
  (`agent-desktop.Dockerfile:62-67`), which states the catalog is "only staged
  here, never installed"
  - **Evidence:** the `ENV AGENTDEV_CATALOG_DIR` comment now states the catalog
    is staged and installed at build time so a raw-image consumer resolves with
    no hooks, and that a devcontainer's mounted volumes shadow that install so
    postCreate installs again.
- [x] Rewrite the README's staged-catalog rationale: staging and installing both
  happen now, the volume-shadowing explanation stays as the reason `postCreate`
  must *also* install, and link the architecture doc
  - **Evidence:** `ansible/roles/agentic_tools/README.md` now heads the section
    "This role both stages and installs", explains the build-time install for
    raw-image consumers, keeps volume-shadowing as the reason the lifecycle
    scripts must also install, links `ci-agent-plugin-availability`, and adds
    `agentic_tools_install_catalog` and the Codex marketplace manifest var to
    the table (prettier-aligned).

### Task 3: Remove the image's `/root/.claude.json` before the volume handoff

**Files:** Modify: `.devcontainer/scripts/postCreateCommand.sh`

The image now ships a real `/root/.claude.json`. It must be removed before
`codebase-memory-mcp-install.sh` runs (`postCreateCommand.sh:56`), not in the
handoff at 67-73: cbm-install writes its MCP entry into whatever
`/root/.claude.json` is present, and on first start the file is not yet a
symlink, so its materialization guard is skipped and it edits the file in place.
Leaving the image copy for the handoff to `mv` would carry image content into
the volume. Removing it up front reproduces the pre-image sequence (no file
present when cbm-install runs); the existing `mv`/`elif`/`ln -sf` handoff then
stays as written, with its `mv` branch dead on first start.

- [ ] Before the `codebase-memory-mcp-install.sh` call, remove a real
  (non-symlink) `/root/.claude.json` so the mounted `agentdev-claude` volume
  remains the source of truth for Claude files. Guard it to `-f && ! -L` so an
  existing volume's symlink into the volume is never removed, and comment why
  the removal precedes cbm-install. `shellcheck` clean.

### Task 4: Prove it, including both volume states

**Files:** none — verification only

Stands alone: its evidence is a real image build, which the session writing
Tasks 1-3 cannot produce by editing files.

- [x] Build `agent-desktop` locally through `/agentdev:microvm-sandbox`
  - **Evidence:** on this Docker-enabled host,
    `docker build -t local/ubuntu-ansible docker/ansible` then
    `docker buildx build -f docker/desktop/agent-desktop.Dockerfile --build-arg FROM_IMAGE=local/ubuntu-ansible --build-arg AGENTDEV_PLUGIN_VERSION=3.1.0 -t local/agent-desktop-install-test .`
    both exit 0. The Ansible log shows the four
    `agentic_tools : Register/Install ... marketplace/plugin` tasks running with
    no fatal/failed. `AGENTDEV_PLUGIN_VERSION=3.1.0` matches the manifest's
    current version (the Dockerfile default `3.0.0` is a stale pin that
    CI/release bumps; it is unrelated to this plan).
- [x] Run a container from the built image with **no** volumes mounted and
  confirm `claude plugin list` shows `agentdev` installed, and that a Codex
  skill resolves too
  - **Evidence:** `docker run --rm local/agent-desktop-install-test` (no
    volumes) reports `claude plugin list` → `agentdev@agent-devcontainer`
    version 3.1.0, scope user, status enabled. `codex plugin list` reports the
    same plugin `installed, enabled` from
    `/opt/agentdev/.agents/plugins/marketplace.json`, and Codex materialized the
    skills into
    `/root/.codex/plugins/cache/agent-devcontainer/agentdev/3.1.0/skills/` (e.g.
    `iwe-ship/SKILL.md`, `microvm-sandbox/SKILL.md`) with the marketplace and
    plugin registered in `/root/.codex/config.toml` — a Codex skill resolves.
- [ ] Start a devcontainer on a **fresh** volume and confirm Task 3's removal
  restores the pre-image sequence: `/root/.claude.json` is gone before
  `codebase-memory-mcp-install.sh` runs, so cbm-install creates a clean file
  with only its MCP entry, the handoff takes the `elif` branch (not `mv`), and
  the volume's `claude.json` is that clean file with `/root/.claude.json`
  symlinked to it — no image content folded in.
- [ ] Start a devcontainer on an **existing** volume and confirm the image's
  `/root/.claude.json` is removed before cbm-install and the volume's existing
  `claude.json` is preserved unchanged across the rebuild (byte-identical to
  before, no image content merged), with `/root/.claude.json` symlinked back to
  it, and a workspace skill edit still wins on attach

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
image build wrote. Because the build-time Claude install seeds a real
`/root/.claude.json` into the image, `postCreateCommand.sh` SHALL remove that
file before `codebase-memory-mcp-install.sh` runs whenever it is a real,
non-symlink file, so the mounted `agentdev-claude` volume remains the source of
truth for `claude.json` and no image content is folded into it.

#### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `ghcr.io/plume-works/agent-desktop` and no
  lifecycle hook runs
- **THEN** the catalog installed during the image build is present, and an
  `agentdev:*` skill resolves.

#### Scenario: a devcontainer starts for the first time on a fresh volume

- **WHEN** `postCreateCommand` runs, `$AGENTDEV_CATALOG_DIR` exists, and the
  image ships a real `/root/.claude.json`
- **THEN** `postCreateCommand` removes that image file before
  `codebase-memory-mcp-install.sh` runs, so cbm-install seeds a clean
  `claude.json` carrying only its MCP entry into the newly created volume, and
  `reinstall-agentdev-codex.sh` and `reinstall-agentdev-claude.sh ... user`
  install the staged catalog into the fresh `agentdev-claude` / `agentdev-codex`
  volumes.

#### Scenario: a devcontainer starts with a catalog already installed on its volume

- **WHEN** the `agentdev-claude` / `agentdev-codex` volumes already contain a
  prior install and `claude.json` (they persist per devcontainer instance), and
  the recreated container carries the image's `/root/.claude.json`
- **THEN** `postCreateCommand` removes the image's `/root/.claude.json` before
  the handoff so the volume's existing `claude.json` is preserved unchanged and
  re-symlinked, the volume mount shadows the image-build catalog install, and
  `postCreateCommand` re-applies that install every time the container is
  created, so it is never silently stale.
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
- A devcontainer on a fresh volume completes `postCreate` without error, and the
  image's `/root/.claude.json` is removed before cbm-install so the volume's
  `claude.json` holds only cbm-install's clean output — no image content (Task
  4).
- A devcontainer on an existing volume has the image's `/root/.claude.json`
  removed before the handoff, preserves its volume `claude.json` byte-identical
  across the rebuild, and still picks up a workspace skill edit on attach (Task
  4).

## Out of scope

- **Changing how the devcontainer lifecycle scripts install the catalog.** They
  keep installing unconditionally; this plan only adds a second, earlier install
  for consumers that never run them. The one lifecycle-script change it does
  make is Task 3's removal of the image's `/root/.claude.json` before the
  handoff — a consequence of the image now shipping that file, needed to keep
  the volume authoritative, not a change to the catalog-install behavior.
- **The AI responder workflows.** They use the checkout and do not depend on
  this.
- **Making `~/.claude.json` volume-backed.** Docker volumes are
  directory-backed; the symlink workaround stays.

## Key references

Verified anchor points (line numbers as of 2026-09-01):

- `ansible/roles/agentic_tools/tasks/main.yml:26,30` — the `stage_catalog.yml`
  import and, right after it, the `install_catalog.yml` import Task 1 added
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:2-7` — the header
  comment, corrected by Task 1 to say `install_catalog.yml` installs from the
  staged copy
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:123` —
  `Make the staged catalog root-owned and read-only`, the last staging task
- `ansible/roles/agentic_tools/defaults/main.yml:25` —
  `agentic_tools_stage_catalog`
- `ansible/roles/agentic_tools/defaults/main.yml:32` —
  `agentic_tools_install_catalog`, added by Task 1
- `ansible/roles/agentic_tools/defaults/main.yml:53` —
  `agentic_tools_catalog_root: /opt/agentdev`
- `ansible/roles/extra_facts/tasks/main.yml:16` — `user_home` resolves from
  `ansible_facts['env'].HOME`, i.e. `/root`
- `docker/desktop/agent-desktop.Dockerfile:54-55` —
  `agentic_tools_stage_catalog=true` and `agentic_tools_install_catalog=true`
- `docker/desktop/agent-desktop.Dockerfile:68` — the `ENV AGENTDEV_CATALOG_DIR`
  declaration whose comment block Task 2 corrected
- `.devcontainer/scripts/postCreateCommand.sh:56` —
  `codebase-memory-mcp-install.sh`, which runs before the handoff; Task 3's
  removal must precede this call
- `.devcontainer/scripts/postCreateCommand.sh:67-73` — the `~/.claude.json`
  move-and-symlink handoff; its `mv` branch is the one Task 3's removal keeps
  from ever firing on image content
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:56-61` — cbm-install's
  symlink-materialization guard (`if [[ -L … ]]`), skipped on first start when
  the file is a real image copy, which is why removal must precede it
- `.devcontainer/scripts/postCreateCommand.sh:91-93` — the existing lifecycle
  catalog install this one mirrors
- `.github/actions/paths-filter/action.yml:38` — `ansible/**`, so the change
  triggers a CI image rebuild
