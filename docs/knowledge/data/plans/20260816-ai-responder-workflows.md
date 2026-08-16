---
created: 2026-08-16
description: Import Dr-QP's AI responder and required-AI-review workflows, Claude-only, on top of an agent-desktop image that installs the agentdev catalog at build time.
generated:
  by: claude-code/opus-5
  at: 2026-08-16T00:00:00Z
---

# AI responder workflows

## Context

This repository has no automated PR review. Dr-QP runs two workflows that
together provide one: `ai-responder.yml` answers `@claude` mentions and reviews
PRs, and `require-ai-review.yml` blocks merge until an AI review exists. They
are a matched pair — the gate is satisfiable because the responder produces the
review.

Importing them surfaced a prerequisite. The responder must run in a container
with the project toolchain to produce a grounded review, and the review is
driven by the `agentdev:pr-review` skill. The `agent-desktop` image *stages* the
catalog at `/opt/agentdev` but does not install it, deferring installation to
`postCreate`. A GitHub Actions `container:` job runs no lifecycle hooks, so the
skill would not resolve and the responder would improvise a review — producing a
green required check over an ungrounded review.

The decision to install the catalog at image build time, why the original
staging-only rationale did not hold, and the rejected alternatives are recorded
in
[CI agent plugin availability](../architecture/ci-agent-plugin-availability.md).

## Approach

Three pieces, strictly ordered by dependency: the image change ships first and
`:edge` rebuilds, then the responder can work, then the gate can be required.

`agentic_tools` gains an install step after staging, for both Claude and Codex,
mirroring what `postCreate` already does. This serves the *raw image* consumer:
a `container:` job, a plain `docker run`. The devcontainer path is essentially
untouched — its `agentdev-claude` / `agentdev-codex` volumes mount over
`/root/.claude` and `/root/.codex`, so the build-time install is not visible
there and `postCreate` installs into the volumes exactly as it does today.

One exception keeps the two from being fully disjoint: `~/.claude.json` is not
volume-backed (Docker volumes are directory-backed, so it is persisted inside
the volume and symlinked into place). The image will now ship that file where it
previously shipped none, which changes which branch of
`postCreateCommand.sh:52-59` fires on a fresh volume. Task 3 verifies both the
fresh and existing-volume cases rather than assuming the handoff is unaffected.

`ai-responder.yml` is imported Claude-only: the `codex-respond` job, the codex
preflight conditions, the `AI_RESPONDERS` variable with its validation step and
`enabled()` helper, and every ROS-specific element (the
`scripts/with-ros-env.sh` preflight check and the prompt line naming it) are all
dropped. The fork gate and the write-access gate are kept verbatim — they are
the security spine.

`require-ai-review.yml` is imported verbatim. Its codex acceptance path is live,
not dead: Codex reviews arrive via Codex web as `chatgpt-codex-connector[bot]`,
entirely outside GitHub Actions.

Rejected: running the responder on a bare runner (gives up the toolchain that
makes a review grounded) and vendoring a repo-local `pr-review` skill (forks
from the catalog copy and drifts).

## Implementation Steps

### Task 1: Install the agentdev catalog at image build time

**Files:** Create: `ansible/roles/agentic_tools/tasks/install_catalog.yml`;
Modify: `ansible/roles/agentic_tools/tasks/main.yml`,
`ansible/roles/agentic_tools/defaults/main.yml`,
`ansible/roles/agentic_tools/tasks/stage_catalog.yml` (comment only)

The install runs as the same user the rest of the Ansible provisioning runs as:
`user_home` is `ansible_facts['env'].HOME`, i.e. `/root` — the same path the
devcontainer mounts `agentdev-claude` over and the same `$HOME` a consumer of
the image runs as, since the Dockerfile declares no `USER`. The marketplace is
added from a local path, so the build needs no auth and stays offline.

- [ ] Add `agentic_tools_install_catalog` (default `false`) to the role
  defaults, gating the new task file the same way `agentic_tools_stage_catalog`
  gates staging
- [ ] Write `install_catalog.yml` registering the staged root as a marketplace
  and installing the plugin for Claude at user scope and for Codex, reading the
  marketplace and plugin names from the manifests rather than hardcoding them
- [ ] Import `install_catalog.yml` from `main.yml` after the staging import,
  guarded by both `agentic_tools_install_catalog` and
  `agentic_tools_stage_catalog` (installing without staging is incoherent)
- [ ] Correct the staging comments in `stage_catalog.yml` and the
  `agentic_tools_stage_catalog` default that assert the install cannot happen at
  build time

### Task 2: Turn the build-time install on and document it

**Files:** Modify: `docker/desktop/agent-desktop.Dockerfile`,
`ansible/roles/agentic_tools/README.md`

- [ ] Pass `agentic_tools_install_catalog=true` in the Dockerfile's
  `ansible-playbook` invocation
- [ ] Correct the `ENV AGENTDEV_CATALOG_DIR` comment block, which states the
  catalog is "only staged here, never installed"
- [ ] Rewrite the README's staged-catalog rationale: staging and installing now
  both happen, the volume-shadowing explanation stays as the reason `postCreate`
  must *also* install, and link the architecture doc

### Task 3: Prove the image install works (local build)

**Files:** none — verification only

Stands alone: its evidence is a real image build, which the session writing
Tasks 1-2 cannot produce by editing files.

- [ ] Build `agent-desktop` locally through `/agentdev:microvm-sandbox`
- [ ] Run a container from the built image with **no** `~/.claude` volume
  mounted and confirm `claude plugin list` shows `agentdev` installed
- [ ] Start a devcontainer from the built image on a **fresh** volume and
  confirm the `~/.claude.json` handoff is still correct. This is the one place
  the two paths meet: `~/.claude.json` is not volume-backed, so
  `postCreateCommand.sh:52-59` moves it into the volume and symlinks it back.
  Today the image ships no such file and the `elif` writes `{}`; after this
  change the image ships one, so the `mv` branch fires instead and seeds the
  volume from the image. Confirm the resulting install is coherent and that
  `codebase-memory-mcp-install.sh` (which runs before the symlink exists,
  `postCreateCommand.sh:40`) still behaves when `~/.claude.json` is a real file
  rather than absent
- [ ] Start a devcontainer on an **existing** volume and confirm the image's
  `~/.claude.json` is correctly ignored (`/root/.claude.json` is already a
  symlink, so both branches skip), and that a workspace edit to a skill still
  wins on attach

### Task 4: Provision repository secrets and environment

**Files:** none — repository settings

Stands alone: it is the maintainer's action in GitHub settings, not a code
change, and Task 5 cannot be exercised until it is done.

- [ ] Create the `CLAUDE_CODE_OAUTH_TOKEN` repository secret
- [ ] Create the `claude-review` environment

### Task 5: Import ai-responder.yml, Claude-only

**Files:** Create: `.github/workflows/ai-responder.yml`

- [ ] Add the preflight job with the owner gate set to `plume-works`, the fork
  gate, and the write-access gate kept verbatim from upstream
- [ ] Drop `AI_RESPONDERS` entirely — the env var, the validation step, the
  `enabled()` helper — and reduce the trigger conditions and prompt builder to
  Claude only
- [ ] Drop the `scripts/with-ros-env.sh` preflight step and the ROS line in the
  prompt, replacing neither
- [ ] Add the `claude-respond` job in
  `container: ghcr.io/plume-works/agent-desktop:edge` with no `credentials:`
  (the package is public), keeping the artifact upload and the usage-limit check
- [ ] Confirm `actionlint` and `zizmor` pass on the new workflow

### Task 6: Import require-ai-review.yml verbatim

**Files:** Create: `.github/workflows/require-ai-review.yml`

- [ ] Copy the upstream workflow unchanged, including both the Claude and Codex
  acceptance paths
- [ ] Confirm `.github/actions/log-debug-stats` resolves for its final step
- [ ] Confirm `actionlint` and `zizmor` pass on the new workflow

### Task 7: Prove the responder runs green, then require the gate

**Files:** none — CI and repository settings

Stands alone: its evidence is a CI run on a real PR plus a branch-protection
change, neither of which the session writing Tasks 5-6 can produce.

- [ ] Trigger the responder on a real PR and confirm it posts a review, with the
  job log showing `agentdev:pr-review` resolved rather than improvised
- [ ] Confirm `ai-review-present` passes on that PR
- [ ] Only then add `ai-review-present` to the branch protection required checks

## Spec changes

[Catalog lifecycle](../spec/catalog-lifecycle.md) — its first requirement
currently forbids exactly what this plan does. The contract-heavy form applies:
the requirement is reversed rather than extended, and its scenario set changes.

``` markdown
## MODIFIED Requirements

### Requirement: the catalog is installed at image build time and reinstalled by postCreateCommand

The `agentdev` catalog staged at `$AGENTDEV_CATALOG_DIR` SHALL be installed into
each agent's plugin state during the image build, at Claude user scope and via
Codex's own registration, so that any direct consumer of the image resolves
`agentdev:*` skills with no additional step. `postCreateCommand.sh` SHALL
additionally perform the same install, because a mounted `~/.claude` /
`~/.codex` volume shadows what the image build wrote.

#### Scenario: a GitHub Actions container job runs the image with no volumes

- **WHEN** a workflow job runs in `ghcr.io/plume-works/agent-desktop` and no
  lifecycle hook runs
- **THEN** the catalog installed during the image build is already present, and
  an `agentdev:*` skill resolves.

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

New behavior for the workflows themselves goes in a new spec,
`data/spec/ai-review-gate`, created at ship time:

``` markdown
## ADDED Requirements

### Requirement: PRs are blocked until an AI review exists

A pull request SHALL NOT be mergeable until either Claude or Codex has reviewed
it. The `ai-review-present` check SHALL accept a review from `claude[bot]` or
`github-actions[bot]`, a review from `chatgpt-codex-connector[bot]`, or a `+1`
reaction from `chatgpt-codex-connector[bot]`, in state `approved`,
`changes_requested`, or `commented`.

#### Scenario: Claude reviews a PR through the responder workflow

- **WHEN** `ai-responder.yml` posts a review on a pull request
- **THEN** `ai-review-present` passes.

#### Scenario: Codex reviews a PR through Codex web

- **WHEN** a maintainer runs a Codex review outside GitHub Actions and it posts
  as `chatgpt-codex-connector[bot]`
- **THEN** `ai-review-present` passes.

#### Scenario: no AI has reviewed within the polling window

- **WHEN** neither a Claude nor a Codex review appears within 8 minutes
- **THEN** `ai-review-present` fails, blocking merge.

### Requirement: the responder only acts for authorized same-repository requests

The responder SHALL NOT check out or execute code for a pull request originating
from a fork, and SHALL NOT act on a request from an actor without write access.

#### Scenario: a fork PR triggers the responder

- **WHEN** the pull request head repository differs from the workflow repository
- **THEN** preflight records the fork and every responder job is skipped before
  any checkout.

#### Scenario: a user without write access mentions @claude

- **WHEN** the requesting actor's permission is not `admin`, `maintain`, or
  `write`
- **THEN** preflight fails and no responder job runs.
```

## Depends on

None — no active plan touches CI workflows or the `agentic_tools` role.

## Verification

- `uv run ansible-lint ansible` and
  `uv run ansible-playbook --syntax-check ansible/playbooks/setup-dev.yml`, both
  from the repository root, pass after Tasks 1-2.
- A locally built `agent-desktop` image, run as a plain container with no
  volumes, reports `agentdev` in `claude plugin list` (Task 3).
- A devcontainer started from that image completes `postCreate` without error
  and picks up a workspace skill edit on attach (Task 3).
- `actionlint` and `zizmor` pass on both new workflows, via
  `/agentdev:local-reformat` or the pre-commit hooks.
- The responder posts a review on a real PR, its log showing the `pr-review`
  skill resolved (Task 7).
- `ai-review-present` passes on that PR before it is made a required check (Task
  7).

## Out of scope

- **Loosening the gate's acceptance rules.** The `+1`-reaction path and the
  `commented` state are weak — nearly any bot comment satisfies the check. That
  is upstream's design; changing it during an import would conflate two
  decisions. Worth a backlog item.
- **A Codex responder job in CI.** Codex reviews come from Codex web.
- **Changing `postCreate` / `postAttach` behavior.** The devcontainer path is
  deliberately untouched; that it stays identical is the argument for the image
  change being safe.
- **Renovate, branch-protection automation, or importing any other Dr-QP
  workflow.**

## Key references

Verified anchor points (line numbers as of 2026-08-16):

- `ansible/roles/agentic_tools/tasks/main.yml:26` —
  `Stage the agent catalog into the image`, the import the install task follows
- `ansible/roles/agentic_tools/defaults/main.yml:26` —
  `agentic_tools_stage_catalog`, whose comment asserts the install belongs to
  lifecycle scripts
- `ansible/roles/agentic_tools/defaults/main.yml:45` —
  `agentic_tools_catalog_root: /opt/agentdev`
- `ansible/roles/agentic_tools/tasks/stage_catalog.yml:123` —
  `Make the staged catalog root-owned and read-only`, the last staging task
- `ansible/roles/extra_facts/tasks/main.yml:16` — `user_home` resolves from
  `ansible_facts['env'].HOME`, i.e. `/root`
- `docker/desktop/agent-desktop.Dockerfile:54` —
  `agentic_tools_stage_catalog=true`, where the install flag joins
- `docker/desktop/agent-desktop.Dockerfile:67` — `ENV AGENTDEV_CATALOG_DIR`,
  whose comment claims the catalog is never installed
- `.devcontainer/scripts/postCreateCommand.sh:78-79` — the existing install,
  which the build-time install mirrors
- `.devcontainer/scripts/reinstall-agentdev-claude.sh:64-73` — the
  remove-across-scopes sweep that makes reinstall-over-install safe
- `.github/actions/paths-filter/action.yml:38` — `ansible/**`, so the image
  change triggers a CI rebuild
- `.github/workflows/ci.yml:30` — `DESKTOP_IMAGE_NAME: agent-desktop`
