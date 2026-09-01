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
It cannot be volume-backed (Docker volumes are directory-backed), so postCreate
persists it as a plain file inside the `agentdev-claude` volume
(`/root/.claude/claude.json`) and symlinks `/root/.claude.json` to it. Two
facts, both confirmed by a real image build rather than assumed, force the
ordering:

- `/root/.claude.json` lives in `/root/`, which is **not** volume-backed, so on
  every fresh container it is whatever the image ships — after the build-time
  install, a real file, never a symlink. A `! -L` guard therefore cannot tell an
  image's stale copy from a link that must be kept: on a rebuild there is no
  link to keep, only the image file.
- `codebase-memory-mcp-install.sh` *re-creates* `/root/.claude.json` as a real
  file when it writes its MCP entry, and its existing materialization guard
  folds the result back into the symlink target **only when `/root/.claude.json`
  is already a symlink** when it runs (`codebase-memory-mcp-install.sh:56-61`).
  If it is a real file at that point, cbm-install edits that file in place and
  the volume is never consulted.

So the volume can only stay authoritative if the volume→`/root/.claude.json`
symlink is established **before** cbm-install runs. postCreate does the full
handoff up front, ahead of the cbm-install call: it discards the image's real
`/root/.claude.json` (never `mv`-ing image content into the volume — a real
build proved an image `mv` folds image content in), seeds
`/root/.claude/claude.json` with `{}` only when the volume has none, then
symlinks `/root/.claude.json` to it. cbm-install then sees a symlink,
materializes the volume's file, installs, and folds the MCP entry back into the
volume — so an existing volume's `claude.json` content is preserved (Claude may
append bootstrap fields, so the guarantee is content/marker preservation, not
byte-identity) and a fresh volume is seeded clean with no image content. The old
in-place handoff block becomes dead code once the symlink exists up front, and
is removed. Task 4 verifies both volume states against this corrected sequence.

A first design — an unconditional `rm` of the image's `/root/.claude.json`
before cbm-install — was tried and rejected: a real rebuild proved it clobbers
an existing volume, because removing the file severs cbm-install's only path
back to the volume's content, so cbm-install then creates a fresh file that the
handoff `mv`s over the volume's real `claude.json`.

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

### Task 3: Link the volume's `claude.json` before cbm-install runs

**Files:** Modify: `.devcontainer/scripts/postCreateCommand.sh`

The image now ships a real `/root/.claude.json`. The volume can only stay
authoritative if the volume→`/root/.claude.json` symlink is in place **before**
`codebase-memory-mcp-install.sh` runs: cbm-install re-creates the file and only
folds its MCP entry back into the symlink target when the file is already a
symlink (`codebase-memory-mcp-install.sh:56-61`); a `! -L` guard cannot spare an
existing volume, because on a rebuild `/root/.claude.json` is the image's real
file, not a symlink. Move the full `~/.claude.json` handoff up front, ahead of
the cbm-install call, and remove the now-dead in-place handoff block that
follows it.

- [x] Ahead of the `codebase-memory-mcp-install.sh` call, perform the handoff:
  discard a real (non-symlink) image `/root/.claude.json` without `mv`-ing it
  into the volume; when `/root/.claude/claude.json` does not exist, seed it with
  `{}`; then `ln -sf /root/.claude/claude.json /root/.claude.json`. So an
  existing volume's `claude.json` is kept and re-linked, and a fresh volume is
  seeded clean with no image content. Remove the later in-place handoff block
  (now redundant — the file is already a symlink when it is reached), and
  comment why the handoff must precede cbm-install. `shellcheck` clean.
  - **Evidence:** `.devcontainer/scripts/postCreateCommand.sh:53-62` now runs
    the full up-front handoff before the `codebase-memory-mcp-install.sh` call
    at line 66 — it `rm -f`s a real (non-symlink) image `/root/.claude.json`,
    seeds `/root/.claude/claude.json` with `{}` when the volume has none, then
    `ln -sf`s the symlink into place; the superseded `rm`-only block and the
    dead in-place move-and-symlink block below cbm-install are both removed,
    with the volume-backing rationale folded into the up-front comment
    (`Spec: catalog-lifecycle`).
    `shellcheck .devcontainer/scripts/postCreateCommand.sh` is clean. Committed
    on `skills-updates` in this task's commit.

### Task 4: Prove it, including both volume states

**Files:** none — verification only

Stands alone: its evidence is a real image build and lifecycle reproduction,
which the session writing Tasks 1-3 cannot produce by editing files.

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
- [x] Start a devcontainer on a **fresh** volume and confirm Task 3's up-front
  handoff seeds it clean: the image's `/root/.claude.json` is discarded and
  `/root/.claude.json` is a symlink into the volume **before**
  `codebase-memory-mcp-install.sh` runs, so cbm-install materializes and folds
  its MCP entry back into the volume's `claude.json`; the volume's `claude.json`
  carries only cbm-install's output (no image content, checked by the image's
  distinctive machineID being absent), and `/root/.claude.json` ends symlinked
  to it.
  - **Evidence:** rebuilt `local/agent-desktop-install-test` from the current
    tree (`docker build docker/ansible` then the `docker buildx build` from Task
    4 box 1, both exit 0). The rebuilt image bakes a real `/root/.claude.json`
    with machineID `e35f7558…c7333076` and ships the cbm binary at
    `/usr/local/bin/codebase-memory-mcp`. Ran the shipped `postCreateCommand.sh`
    handoff (verified verbatim in the shipped script by an in-driver fidelity
    guard) + the real `codebase-memory-mcp-install.sh` in a fresh container
    against an empty `agentdev-claude` volume mounted at `/root/.claude`.
    Observed: the image file is `rm`ed and `/root/.claude.json` is a symlink to
    `/root/.claude/claude.json` **before** cbm-install runs ("is symlink? YES");
    cbm-install then materializes it and folds its
    `mcpServers.codebase-memory-mcp` entry into the volume; the volume's
    `claude.json` holds ONLY that MCP entry — image machineID `e35f7558…` is
    ABSENT ("OK: image machineID absent"); `/root/.claude.json` ends symlinked
    to the volume file. Driver: `.tmp/task4-driver.sh` (harness, not committed).
- [ ] Start a devcontainer on an **existing** volume (seed the volume's
  `claude.json` with a distinctive marker, then rebuild in a fresh container
  from the image so `/root/.claude.json` is the image's real file) and confirm
  the volume's `claude.json` **content is preserved** across the rebuild — the
  marker survives and no image content is merged (byte-identity is not required;
  Claude may append bootstrap fields) — with `/root/.claude.json` symlinked back
  to it, and a workspace skill edit still wins on attach.

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
`/root/.claude.json` into the image, `postCreateCommand.sh` SHALL establish the
volume→`/root/.claude.json` symlink before `codebase-memory-mcp-install.sh`
runs — discarding the image's real file, seeding `/root/.claude/claude.json`
with `{}` only when the volume has none — so the mounted `agentdev-claude`
volume remains the source of truth for `claude.json`, cbm-install folds its MCP
entry back into the volume, and no image content is folded into it.

#### Scenario: the image runs with no volumes and no lifecycle hooks

- **WHEN** a container starts from `ghcr.io/plume-works/agent-desktop` and no
  lifecycle hook runs
- **THEN** the catalog installed during the image build is present, and an
  `agentdev:*` skill resolves.

#### Scenario: a devcontainer starts for the first time on a fresh volume

- **WHEN** `postCreateCommand` runs, `$AGENTDEV_CATALOG_DIR` exists, and the
  image ships a real `/root/.claude.json`
- **THEN** `postCreateCommand` discards that image file and symlinks
  `/root/.claude.json` to a freshly-seeded `/root/.claude/claude.json` before
  `codebase-memory-mcp-install.sh` runs, so cbm-install folds only its MCP entry
  into the volume's clean `claude.json` with no image content, and
  `reinstall-agentdev-codex.sh` and `reinstall-agentdev-claude.sh ... user`
  install the staged catalog into the fresh `agentdev-claude` / `agentdev-codex`
  volumes.

#### Scenario: a devcontainer starts with a catalog already installed on its volume

- **WHEN** the `agentdev-claude` / `agentdev-codex` volumes already contain a
  prior install and `claude.json` (they persist per devcontainer instance), and
  the recreated container carries the image's `/root/.claude.json`
- **THEN** `postCreateCommand` discards the image's `/root/.claude.json` and
  symlinks `/root/.claude.json` to the volume's existing `claude.json` before
  cbm-install runs, so that content is preserved (cbm-install folds its MCP entry
  back in; Claude may append bootstrap fields, so the guarantee is content
  preservation, not byte-identity), the volume mount shadows the image-build
  catalog install, and `postCreateCommand` re-applies that install every time the
  container is created, so it is never silently stale.
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
- A devcontainer on a fresh volume completes `postCreate` without error, with
  `/root/.claude.json` symlinked into the volume before cbm-install so the
  volume's `claude.json` holds only cbm-install's clean output — no image
  content (Task 4).
- A devcontainer on an existing volume symlinks `/root/.claude.json` to the
  volume's `claude.json` before cbm-install, preserves that `claude.json`'s
  content across the rebuild (distinctive marker survives, no image content
  merged), and still picks up a workspace skill edit on attach (Task 4).

## Out of scope

- **Changing how the devcontainer lifecycle scripts install the catalog.** They
  keep installing unconditionally; this plan only adds a second, earlier install
  for consumers that never run them. The one lifecycle-script change it does
  make is Task 3's reordering of the `~/.claude.json` handoff to run before
  cbm-install (discarding the image's copy) — a consequence of the image now
  shipping that file, needed to keep the volume authoritative, not a change to
  the catalog-install behavior.
- **The AI responder workflows.** They use the checkout and do not depend on
  this.
- **Making `~/.claude.json` volume-backed.** Docker volumes are
  directory-backed; the symlink workaround stays.

## Key references

Verified anchor points (line numbers as of 2026-09-01; postCreateCommand.sh
re-verified after Task 3):

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
- `.devcontainer/scripts/postCreateCommand.sh:53-62` — the up-front
  `~/.claude.json` handoff Task 3 added (discard the image file, seed `{}` when
  fresh, `ln -sf` the volume symlink), replacing the superseded `rm`-only block
- `.devcontainer/scripts/postCreateCommand.sh:66` —
  `codebase-memory-mcp-install.sh`, which the handoff now precedes so the
  symlink exists when cbm-install runs
- `.devcontainer/scripts/codebase-memory-mcp-install.sh:56-61` — cbm-install's
  symlink-materialization guard (`if [[ -L … ]]`), which folds its edit back
  into the volume only when `/root/.claude.json` is already a symlink — the
  reason the handoff must precede this call
- `.devcontainer/scripts/postCreateCommand.sh:91` — the existing lifecycle
  catalog install this one mirrors
- `.github/actions/paths-filter/action.yml:38` — `ansible/**`, so the change
  triggers a CI image rebuild
