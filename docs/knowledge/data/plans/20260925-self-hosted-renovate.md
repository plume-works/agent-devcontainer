---
type: plan
created: 2026-09-25
description: Run Renovate from a workflow inside the pinned agent-desktop image so post-upgrade tasks can refresh checksum pins, lock files, and pre-commit output in the same commit as the bump.
generated:
  by: claude-code/opus-5
  at: 2026-09-25T00:00:00Z
sources:
- resource: .github/renovate.json
- resource: .github/workflows/validate-renovate-config.yml
- resource: .github/workflows/ai-responder.yml
- resource: .pre-commit-config.yaml
- resource: ansible/roles/dev_tools/defaults/main.yml
- resource: ansible/roles/agentic_tools/defaults/main.yml
- resource: ansible/roles/xpra_setup/tasks/main.yml
- resource: https://github.com/renovatebot/renovate/blob/main/lib/modules/manager/github-actions/extract.ts
  title: Renovate github-actions manager extracts job container images
- resource: https://docs.renovatebot.com/self-hosted-configuration/
- resource: https://docs.renovatebot.com/configuration-options/#postupgradetasks
---

# Self-hosted Renovate in the agent-desktop image

## Context

[Renovate maintains checksum-carrying pins](../features/renovate-maintains-checksums.md)
motivates this plan. The hosted Renovate app cannot run commands after a bump,
because `allowedCommands` is a global-only option. Three kinds of update
therefore stay manual or go stale: the per-architecture SHA-256 beside a pinned
download, lock files whose owning tool Renovate does not run
(`.devcontainer/devcontainer-lock.json`), and pre-commit output for the files a
bump touches.

Running Renovate from a workflow in this repository moves the command gate here.
Running it inside `ghcr.io/plume-works/agent-desktop` gives those commands the
same toolchain contributors use — uv, bun, pre-commit, iwe — without a second
provisioning path.

## Approach

`renovate.yml` runs on push to `main`, daily, and on manual dispatch, inside
`agent-desktop:edge@sha256:…`. It runs Renovate per run with `bunx`, at the
version the local `renovate-config-validator` pre-commit hook pins in its
`bunx --package renovate@<version>` entry, so one pin serves hook, validation
workflow, and bot. That hook form and the custom manager that bumps its pin come
from
[Run Node tooling through bun instead of npm](20260925-bun-for-node-tooling.md);
this plan makes the pin automerge. It authenticates as a GitHub App so its pull
requests start CI, and the hosted app is disconnected when it lands.

One repository-level post-upgrade task runs one script. The script derives what
changed from the working tree, refreshes checksums for the pin files that
changed, regenerates the devcontainer lock when `devcontainer.json` changed, and
finishes with pre-commit on the changed files. `uv.lock` needs no script: the
`pep621` manager relocks with the image's uv, and lock file maintenance
refreshes it on Renovate's default schedule.

Every job that runs in agent-desktop pins the same digest as
`devcontainer-compose-pins.yml`. Renovate's `github-actions` manager extracts
job `container` images, so one group rule moves every copy in one pull request.
`validate-renovate-config.yml` runs in that image, and a digest bump edits it,
so every bump runs a required check inside the new image before it can
automerge.

### Rejected alternatives

**Renovate provisioned into the image.** One fewer download per run, but every
Renovate upgrade would take two pull requests — role bump, then digest bump —
and the image would carry a large package only CI uses.

**A per-rule `postUpgradeTasks` for each pin kind.** `postUpgradeTasks` is an
object that a later matching `packageRule` replaces rather than extends, so a
checksum rule would silently drop the pre-commit step. One script behind one
task avoids the override ordering entirely.

**A separate check that all agent-desktop pins agree.** Declined: the group rule
moves them together, and a hand edit that splits them is reviewed like any
other.

**Renovate's global configuration in a checked-in file.** The
`renovate-config-validator` hook matches Renovate config filenames and runs with
`--no-global`, which rejects global-only options. The workflow passes global
options as `RENOVATE_*` environment variables instead.

### Assumptions

- Lock file maintenance automerges, like the other lock-free bumps; it only
  moves transitive versions within the ranges `pyproject.toml` already allows.
- The devcontainer CLI is invoked with a pinned version that Renovate tracks.

## Implementation Steps

### Task 1: Settle hadolint inside a container job

**Files:** Modify: none (throwaway branch)

- [ ] Run `pre-commit run hadolint-docker --all-files` in a job with
  `container: ghcr.io/plume-works/agent-desktop:edge@sha256:…` and record
  whether it lints `docker/**/Dockerfile*` successfully. The outcome decides
  Task 7: success keeps the hook; failure (bind paths from `/__w` not resolving
  on the host daemon) makes the script set `SKIP=hadolint-docker`, and
  Super-Linter's hadolint in `reformat.yml` remains the gate.

### Task 2: Move the VirtualGL pin into role defaults

**Files:** Create: `ansible/roles/xpra_setup/defaults/main.yml`; Modify:
`ansible/roles/xpra_setup/tasks/main.yml`

- [ ] `xpra_setup_virtualgl_version` and `xpra_setup_virtualgl_checksums` move
  out of the `set_fact` into the new defaults file, so the existing
  `defaults/main.yml` manager pattern and digest mask reach them. The
  architecture fact stays in the task.

### Task 3: Stop iwe's asset prefix repeating its version

**Files:** Modify: `ansible/roles/dev_tools/defaults/main.yml`,
`ansible/roles/dev_tools/tasks/install_pinned_tool.yml`

- [ ] A version bump must be a one-field edit. `asset_prefix: iwe-v0.19.0-`
  repeats `version`, so a Renovate bump would leave the download URL pointing at
  the old asset. Derive the prefix from the version instead; the image build
  proves the assembled URL is unchanged.

### Task 4: Checksum refresh script

**Files:** Create: `scripts/refresh-pin-checksums.py`,
`scripts/tests/test_refresh_pin_checksums.py`; Modify: `pyproject.toml`

- [ ] Given pin files, the script assembles each architecture's download URL
  exactly as the consuming role does, downloads it, and rewrites the SHA-256 in
  place. It covers `dev_tools_pinned_tools`, cc-filter, and VirtualGL.
- [ ] It exits non-zero, leaving the file untouched, when a download fails, or
  when a pin whose version did not change against `HEAD` hashes differently — a
  tag that moved under an unchanged version.
- [ ] Tests serve fixture assets locally and cover a bumped pin, an unchanged
  pin, a failed download, and a moved tag. `scripts/tests` joins `testpaths`.

### Task 5: Bring checksum-carrying pins under Renovate

**Files:** Modify: `.github/renovate.json`,
`ansible/roles/dev_tools/defaults/main.yml`,
`ansible/roles/agentic_tools/defaults/main.yml`,
`ansible/roles/xpra_setup/defaults/main.yml`

- [ ] Each pin gains a `# renovate:` comment naming its datasource. The
  `version` field is the release tag used in the URL, so the comment keeps
  Renovate proposing tags — a `versioning=` override where the tag carries a
  prefix (`bun-v…`, `iwe-v…`).
- [ ] zizmor gets no comment: its version participates in the Super-Linter
  parity contract and moves only with `sync-super-linter-tool-versions`.
- [ ] A custom manager matches the indented, unquoted `version:` field of a
  `dev_tools_pinned_tools` entry.
- [ ] The provisioning-tools rule's description stops presenting checksum pins
  as unsafe to batch: they join the automerged group now that the checksum moves
  in the same commit.

### Task 6: Automerge the Renovate version pin

**Files:** Modify: `.github/renovate.json`

- [ ] A package rule automerges the `renovate` dependency the `bunx --package`
  custom manager extracts from `.pre-commit-config.yaml`. A bump edits that
  file, which runs the required validation check at the new Renovate version
  before it can merge.

### Task 7: Post-upgrade script

**Files:** Create: `scripts/renovate-post-upgrade.sh`; Modify:
`.github/renovate.json`

- [ ] Changed files come from `git diff --name-only HEAD` in Renovate's clone,
  not from template variables.
- [ ] Changed pin files go through `refresh-pin-checksums.py`; a changed
  `.devcontainer/devcontainer.json` regenerates
  `.devcontainer/devcontainer-lock.json` with the devcontainer CLI, run through
  `bunx`.
- [ ] pre-commit then runs on every changed file. A hook that only rewrites
  files does not fail the task; a hook still failing on a second pass does.
- [ ] Any failure exits non-zero, so Renovate fails the branch instead of
  committing a version beside a stale checksum.
- [ ] `.github/renovate.json` sets one top-level `postUpgradeTasks` running the
  script in `branch` mode, with `fileFilters` covering what it may add beyond
  Renovate's own edits: `ansible/roles/**` and
  `.devcontainer/devcontainer-lock.json`. It also enables `lockFileMaintenance`
  with automerge.

### Task 8: Digest masks for the new pins

**Files:** Modify: `ansible/roles/.agent.metadata.json`,
`.github/.agent.metadata.json`

- [ ] Mask the checksum values and the `dev_tools_pinned_tools` version fields
  the way the version-only pins already are, keeping each `# renovate:` comment
  unmasked.
- [ ] Mask `@sha256:` digests in `.github/**/*.yml`, so a digest bump across
  workflows does not mark the `github` map docs stale.

### Task 9: One agent-desktop pin across the devcontainer and workflows

**Files:** Modify: `.github/workflows/ai-responder.yml`, `.github/renovate.json`

- [ ] Both responder jobs pin `container.image` to the digest in
  `devcontainer-compose-pins.yml`, written as a literal string — the
  `github-actions` manager cannot read an expression.
- [ ] A group rule keeps every `ghcr.io/plume-works/agent-desktop` dependency,
  across the `docker-compose` and `github-actions` managers, in one pull
  request. The existing automerge rule already matches both.

### Task 10: Renovate workflow

**Files:** Create: `.github/workflows/renovate.yml`

- [ ] Triggers: push to `main`, a daily `schedule`, and `workflow_dispatch`. A
  concurrency group queues runs rather than cancelling one mid-run.
- [ ] The job runs in the agent-desktop digest pin, reads the Renovate version
  from the hook's `bunx --package renovate@<version>` entry in
  `.pre-commit-config.yaml`, and runs
  `bunx --package renovate@<version> renovate` against this repository only.
- [ ] Authentication mints a token from the GitHub App through
  `actions/create-github-app-token`; `GITHUB_TOKEN` is never Renovate's token.
- [ ] Global options — `allowedCommands` naming exactly the post-upgrade script,
  `onboarding: false`, `requireConfig`, the repository — come from `RENOVATE_*`
  environment variables.

### Task 11: Validate the config in the pinned image at the pinned version

**Files:** Modify: `.github/workflows/validate-renovate-config.yml`

- [ ] The validation job runs in the agent-desktop digest pin and calls
  `bunx --package renovate@<version>` with the hook's version, not an unpinned
  resolution. The image provides bun, so the `oven-sh/setup-bun` step the bun
  plan adds is removed.
- [ ] A paths-filter job and an always-reporting
  `Renovate config validation finished` job follow the pattern in
  `validate-agent-files.yml`, so the check can be required without blocking pull
  requests it does not apply to. The filter covers `.github/renovate.json`,
  `.pre-commit-config.yaml`, `devcontainer-compose-pins.yml`, and the workflow
  itself.

### Task 12: Record the decisions

**Files:** Modify:
`docs/knowledge/data/architecture/renovate-config-validation.md`,
`docs/knowledge/data/architecture/template-boundary.md`

- [ ] `renovate-config-validation` replaces its
  pinned-hook-versus-latest-workflow decision, as worded after the bun plan: the
  bot now runs the hook's version, so hook, workflow, and bot share one pin, and
  the workflow doubles as the image canary.
- [ ] `template-boundary` lists `renovate.yml` and
  `validate-renovate-config.yml` as Customize: both name this image, and
  `renovate.yml` needs a GitHub App and its secrets.

### Task 13: Create and install the Renovate GitHub App

**Files:** none (repository settings)

- [ ] The App is installed on this repository with the permissions Renovate
  documents for self-hosting, and its ID and private key are stored as
  repository secrets named in `renovate.yml`.

### Task 14: Require the validation check

**Files:** none (ruleset `main`)

- [ ] `Renovate config validation finished` joins the required status checks in
  the `main` ruleset.

### Task 15: Disconnect the hosted Renovate app

**Files:** none (organization settings)

- [ ] The hosted app loses access to this repository immediately before Tasks
  9–11 merge, so the first push-triggered run has no competing bot.

### Task 16: First self-hosted run

**Files:** none (CI)

- [ ] A `renovate.yml` run completes and any pull request it opens carries
  refreshed checksums or lock files and passes CI.

### Task 17: A digest bump runs the check in the new image

**Files:** none (CI)

- [ ] The first agent-desktop digest pull request after merge changes
  `devcontainer-compose-pins.yml` and every workflow pin together, and
  `Renovate config validation finished` reports from a job running in the new
  digest.

## Spec changes

[Image pinning](../spec/image-pinning.md) gains a requirement for workflow
container images:

``` markdown
## ADDED Requirements

### Requirement: workflow container images share the devcontainer pin

Every workflow job that runs in `ghcr.io/plume-works/agent-desktop` SHALL
reference it by the same tag and digest as `devcontainer-compose-pins.yml`, and
a digest update SHALL move every reference in one change.

#### Scenario: Renovate bumps the agent-desktop digest

- **WHEN** Renovate proposes a new agent-desktop digest
- **THEN** one pull request changes `devcontainer-compose-pins.yml` and every
  workflow `container.image` to that digest.

#### Scenario: a bumped digest is exercised before merge

- **WHEN** a pull request changes the agent-desktop digest
- **THEN** a required check runs inside the new image, and the pull request
  cannot merge while it fails.
```

`spec/dependency-updates` is created:

``` markdown
## ADDED Requirements

### Requirement: checksums move with their version

A bump of a pinned download that carries a per-architecture SHA-256 SHALL
recompute every architecture's checksum from the released asset and commit it
in the same change as the version.

#### Scenario: a checksum-carrying pin is bumped

- **WHEN** Renovate raises a pinned version whose asset carries checksums
- **THEN** the pull request carries the new version and a checksum for every
  architecture computed from the new asset.

#### Scenario: an asset cannot be fetched

- **WHEN** any architecture's asset fails to download during the refresh
- **THEN** Renovate fails the branch and commits no version change.

#### Scenario: a tag moves under an unchanged version

- **WHEN** a pin whose version did not change hashes differently than its
  recorded checksum
- **THEN** the refresh fails and the recorded checksum is kept.

### Requirement: derived files are regenerated with the bump

A Renovate change SHALL carry the lock files and pre-commit output its edits
imply, produced by the same toolchain contributors use.

#### Scenario: a dev container feature is bumped

- **WHEN** Renovate changes a feature reference in `.devcontainer/devcontainer.json`
- **THEN** the same pull request carries the regenerated
  `.devcontainer/devcontainer-lock.json`.

#### Scenario: a bumped file needs formatting

- **WHEN** a pre-commit hook rewrites a file Renovate changed
- **THEN** the rewrite is part of Renovate's commit, not a follow-up push.
```

## Depends on

[Run Node tooling through bun instead of npm](20260925-bun-for-node-tooling.md)
ships first: it gives the Renovate pin its `bunx` hook form and the custom
manager that bumps it.

## Verification

- `uv run pytest scripts/tests` passes.
- `renovate-config-validator --no-global --strict .github/renovate.json` passes
  at the hook's version; `pre-commit run --all-files` passes.
- `actionlint` and `zizmor` pass on `renovate.yml` and the modified workflows.
- `LOG_LEVEL=debug bunx --package renovate@<version> renovate --platform=local`,
  run inside the image from the checkout, extracts every checksum-carrying pin
  (not zizmor), both responder `container` images, and the compose pin, with the
  group rule applied.
- The image builds in CI with Tasks 2 and 3 applied.
- `.agents/plugins/agentdev/skills/iwe-map/scripts/stale-map-docs.sh` reports no
  doc stale from a digest-only or checksum-only change.
- Tasks 16 and 17 close on their CI runs.

## Out of scope

- apt packages, which stay unpinned.
- The Ubuntu base release, which Renovate stays disabled for.
- Super-Linter and the tools in its parity contract, zizmor included.
- Verifying publisher signatures such as codebase-memory-mcp's sigstore bundle;
  a recomputed checksum is trust-on-first-use.
- A check that all agent-desktop pins agree.

## Key references

Verified anchor points (line numbers as of 2026-09-26):

- `.github/renovate.json:16-23` — agent-desktop automerge rule
- `.github/renovate.json:54-62` — provisioning-tools automerge group
- `.github/renovate.json:72` — `customManagers`
- `.pre-commit-config.yaml:68-77` — `renovate-config-validator` hook; the bun
  plan moves it into the `repo: local` block as a `bunx --package renovate@…`
  entry
- `.github/workflows/validate-renovate-config.yml:3-26` — triggers and path
  filters
- `.github/workflows/validate-renovate-config.yml:37-43` — unpinned validation
  step; `npx` until the bun plan makes it `bunx`
- `.github/workflows/validate-agent-files.yml:101-108` — always-reporting
  `finished` job pattern
- `.github/workflows/ai-responder.yml:429-430` and `:475-476` — bare `:edge`
  container images
- `.github/actions/paths-filter/action.yml:35-44` — `image` filter; excludes
  `.github/workflows/`
- `ansible/roles/dev_tools/defaults/main.yml:14` — `dev_tools_pinned_tools`;
  zizmor at `:15`, iwe at `:29` with its version-bearing `asset_prefix` at `:32`
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:13-35` — URL assembly
  and checksum use
- `ansible/roles/agentic_tools/defaults/main.yml:22-33` — cc-filter version,
  URL, and checksums
- `ansible/roles/xpra_setup/tasks/main.yml:45-65` — VirtualGL version and
  checksums in `set_fact`
- `ansible/roles/.agent.metadata.json` — role pin digest mask
- `.github/.agent.metadata.json` — workflow pin digest masks
- `pyproject.toml:29` — pytest `testpaths`
- `.devcontainer/devcontainer.json:15-17` — feature references the lock follows
