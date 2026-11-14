---
type: spec
description: The pre-commit hooks are the CI lint gate and each hook tool has one version owner — the commit range they check, when every file is checked, and how gitleaks scans a range.
sources:
- resource: .github/workflows/primary-checks.yml
- resource: .github/workflows/ci.yml
- resource: scripts/pre-commit-ci-range.py
- resource: ansible/roles/nodejs/tasks/main.yml
- resource: scripts/ci_runs.py
- resource: .pre-commit-config.yaml
- resource: devcontainer-compose-pins.yml
- resource: scripts/check-ship-records.py
- resource: scripts/tests/test_check_ship_records.py
- resource: .iwe/schemas/bug.yaml
- resource: pyproject.toml
- resource: ansible/roles/dev_tools/defaults/main.yml
- resource: .github/renovate.json
- resource: ansible/roles/nodejs/tasks/main.yml
- resource: Makefile
- resource: py_packages/agentdev_runtime/agentdev_runtime/project.py
- resource: .devcontainer/devcontainer.json
- resource: .agents/plugins/agentdev/skills/pr-open/SKILL.md
- resource: .agents/plugins/agentdev/agents/principal-engineer.agent.md
- resource: .agents/plugins/agentdev/bin/python_lint_check.py
---

# pre-commit gate

## Requirements

### Requirement: CI runs the pre-commit hooks as the lint gate

Primary checks SHALL run `pre-commit run` inside the `agentdev-devcontainer`
image pinned by the same tag and digest as `devcontainer-compose-pins.yml`, over
the files the event's commit range changed, and the `ci` job SHALL start only
after it succeeds. `uv sync --locked`, `pre-commit install-hooks`, and
`pre-commit run` SHALL be separate steps, so each is timed on its own.

#### Scenario: a pull request changes source files

- **WHEN** a pull request changes files a hook matches
- **THEN** the pre-commit job runs those hooks on the files changed between the
  base and head commits, and fails when any hook fails or rewrites a file.

#### Scenario: a push to main

- **WHEN** commits are pushed to `main`
- **THEN** the job checks the files changed between the head commit of Primary
  checks' last successful push run on `main` and `after`, and skips
  `no-commit-to-branch`.

#### Scenario: the last successful run cannot be found

- **WHEN** a push to `main` finds no successful Primary checks push run, or the
  lookup fails
- **THEN** the job warns and checks the files changed between `before` and
  `after`.

#### Scenario: a manual run

- **WHEN** Primary checks is started by `workflow_dispatch`
- **THEN** the job checks every file.

#### Scenario: hooks bypassed locally

- **WHEN** a commit was made with `--no-verify` or without the hooks installed
- **THEN** the pre-commit job runs the hooks on it and fails where they fail.

### Requirement: every hook runs a tool from one version owner

Every hook in `.pre-commit-config.yaml` SHALL be a `repo: local` hook with
`language: system`, and SHALL run its tool from one version owner:
`uv run <tool>` for a tool in `pyproject.toml`'s `dev` dependency group (ruff,
ruff-format, ansible-lint, clang-format, the `pre-commit-hooks` fixers), an
image binary pinned in `dev_tools_pinned_tools` under a `# renovate:` comment
(hadolint, shellcheck, gitleaks, actionlint, zizmor, iwe), or
`bunx <package>@<version>` (prettier, the Renovate config validator). No hook
SHALL name a remote repository. Each `bunx` pin SHALL sit in the hook's `entry`,
where a `custom.regex` manager in `.github/renovate.json` tracks it against the
npm registry.

#### Scenario: hooks are installed

- **WHEN** `pre-commit install-hooks` runs
- **THEN** it builds no hook environment, and each hook runs the copy of its
  tool that its owner pins

#### Scenario: a hook runs outside the devcontainer

- **WHEN** a hook whose tool is an image binary runs on a host
- **THEN** it runs whatever binary of that name is on `PATH`

#### Scenario: npm publishes a new Prettier

- **WHEN** a Prettier release newer than the hook's `bunx prettier@<version>`
  pin is published
- **THEN** Renovate proposes a pull request that moves the pin in the hook's
  `entry`

### Requirement: JavaScript runs through bun

Every JavaScript tool this repository runs — from a pre-commit hook, a CI
workflow, an Ansible role, a script, or a Makefile target — SHALL be invoked
through `bun` or `bunx`, never `npm`, `npx`, `yarn`, or `pnpm`. A
JavaScript-based hook SHALL be a `language: system` hook whose `entry` runs
`bunx`. The image SHALL NOT carry Ubuntu's `npm` package; a global JavaScript
package it provides SHALL be installed with `bun add --global`.

#### Scenario: a JavaScript hook runs

- **WHEN** the prettier or renovate-config-validator hook runs
- **THEN** `bunx` fetches the pinned package release and runs it, and pre-commit
  builds no Node environment

### Requirement: every commit path runs the hooks, merges included

`agentdev-runtime project hooks` SHALL install the `pre-commit`, `pre-push`, and
`pre-merge-commit` hook types, and `.pre-commit-config.yaml`'s `default_stages`
SHALL include `pre-merge-commit`, so a merge commit runs the same hooks as an
ordinary commit.

#### Scenario: a merge commits on its own

- **WHEN** `git merge` completes without conflicts and creates a merge commit
- **THEN** the `pre-merge-commit` hook runs the hooks on the merged files before
  the commit is written

#### Scenario: a conflicted merge is concluded

- **WHEN** a conflicted merge is resolved and concluded with `git commit`
- **THEN** the `pre-commit` hook runs the hooks

#### Scenario: a hook rewrites a staged file

- **WHEN** a formatter hook rewrites a file in the commit
- **THEN** the commit stops, and succeeds once the rewritten file is staged and
  the commit retried

### Requirement: formatting is left to the hooks

The pre-commit hooks SHALL be the only local formatting step. No catalog skill
or agent SHALL run a formatter of its own or require a formatting pass before a
commit; a Python check outside a commit SHALL use `python_lint_check.py`, which
runs ruff's format and lint checks without rewriting files.

#### Scenario: a pull request is opened

- **WHEN** `/agentdev:pr-open` commits pending changes
- **THEN** the pre-commit hooks format the staged files as part of that commit,
  and the skill runs no formatter itself

### Requirement: pre-commit's store lives on the home volume

The Dev Container SHALL NOT set `PRE_COMMIT_HOME`, so pre-commit keeps its store
at `~/.cache/pre-commit` on the per-instance home volume, and SHALL mount no
cache volume inside the checkout. When `agentdev-runtime project hooks` fails to
install the hooks, it SHALL print `pre-commit.log` from `PRE_COMMIT_HOME` when
that is set and from `$HOME/.cache/pre-commit` otherwise.

#### Scenario: the Dev Container is rebuilt

- **WHEN** a Dev Container is rebuilt on its existing home volume
- **THEN** pre-commit finds its store where the previous container left it

### Requirement: a tool-version change is checked against every file

When the commit range changes `uv.lock`, `pyproject.toml`,
`.pre-commit-config.yaml`, `ansible/roles/dev_tools/defaults/main.yml`, or
`devcontainer-compose-pins.yml`, the pre-commit job SHALL run every hook on
every file.

#### Scenario: Renovate bumps ruff

- **WHEN** a pull request moves ruff's version in `uv.lock`
- **THEN** the job runs every hook on every file, and fails if the new version
  would rewrite any of them.

### Requirement: the rebuilt image passes every hook before promotion

When CI builds a candidate `agentdev-devcontainer` image, it SHALL run every
hook on every file inside that candidate, and SHALL NOT promote the image family
unless the run passes.

#### Scenario: Renovate bumps a tool the image provisions

- **WHEN** a pull request changes a version the image build installs, and the
  new version fails a hook on a file the pull request did not touch
- **THEN** the candidate pre-commit job fails, and no moving tag names the
  candidate.

#### Scenario: the image is not rebuilt

- **WHEN** the path filter skips the image build
- **THEN** only the pre-commit job in the pinned image runs.

### Requirement: gitleaks scans every commit in a range

The gitleaks hook SHALL scan each commit's patch in the range when one is given,
and the staged change otherwise.

#### Scenario: a secret added and removed inside a pull request

- **WHEN** one commit in a pull request adds a secret and a later commit removes
  it
- **THEN** the pre-commit job fails on the commit that added it.

#### Scenario: a push from a working copy

- **WHEN** `git push` runs the pre-push hooks
- **THEN** gitleaks scans every commit being pushed.

#### Scenario: a manual run scans all history

- **WHEN** Primary checks is started by `workflow_dispatch`
- **THEN** gitleaks scans every commit in the repository's history.

#### Scenario: a push that creates a ref

- **WHEN** a push has an all-zero `before` SHA
- **THEN** the job checks every file and gitleaks scans the pushed commit.

### Requirement: Ship records are gated in pre-commit

A pre-commit hook SHALL run a checker CLI over every bug, plan, backlog task,
feature, and release document pre-commit passes it, live or archived, at commit
time, over a commit range, and with `--all-files`. The CLI SHALL fail a bug at
`stage: done` that has no `## Fix` heading. It SHALL fail a plan whose
`## Ship review` section is different from the fixed structure and from each of
the three earlier structures. The oldest earlier structure ends with the item
"Ship edited no hub, release page, or `data/log.md`". The CLI SHALL report every
error with `path:line`. The CLI SHALL also fail a document for each archive
location error and release page error that `iwe-workflow-skills` gives.

#### Scenario: an open bug has no Fix

- **WHEN** a bug document at `stage: pending` or `stage: planned` has no
  `## Fix`
- **THEN** the hook passes it.

#### Scenario: a Ship review is malformed

- **WHEN** a plan's `## Ship review` does not have an item, has the items in a
  different order, has an item with no tick, or marks the Verify, plan-stage, or
  archive-move item `not applicable`
- **THEN** the hook fails and names the line.

#### Scenario: a Ship review carries the earlier checklist

- **WHEN** a plan's `## Ship review` holds the earlier fixed structure, every
  item ticked, ending with "Ship edited no hub, release page, or `data/log.md`"
- **THEN** the hook passes it.

## Rationale

### The pre-commit hooks are the one owner of every formatter and the CI gate

Each formatter and linter has one owner, a pre-commit hook, and CI's gate is the
same hooks run inside the pinned `agentdev-devcontainer` image. Two tools that
both claim a file rewrite each other's output, so the diff depends on which ran
last; one owner per language removes that churn. When CI runs the very hooks a
commit ran, against tools from the same version owners, there is no second
version to drift from and nothing to keep in parity by hand. A version bump
still changes output under unchanged files, which is why a range touching a
version owner checks every file. The cost accepted: a tool a hook runs as an
image binary reaches CI only after a digest bump of the pinned image, so adding
one takes two pull requests, the provisioning and then the hook.

Rejected:

- **Super-Linter as the CI gate.** Its image duplicated every hook and pinned
  its own tool versions, so every bump was a manual sync Renovate could not do.
- **`gitleaks/gitleaks-action`.** It needs a licence key for an organization,
  lists only the first 30 commits of a pull request, and downloads its own
  gitleaks beside the pinned one.
- **Running the job on the image the pull request builds.** It puts lint behind
  the full image build, while the pinned image already carries every binary
  hook.
- **Remote hook repositories.** Each installs its own copy of a tool beside
  `uv.lock` or the image, which is the drift single ownership removes.

### JavaScript hooks run through bunx

A `language: system` hook running `bunx <package>@<version>` keeps one runner,
bun, for every JavaScript invocation, and keeps the version in the hook's own
`entry` where Renovate can move it.

Rejected:

- **`language: node` hooks.** pre-commit installs their environments with npm, a
  second JavaScript runner beside bun.
- **Renovate's `pre-commit` manager alone for the `bunx` pins.** It reads only a
  remote repository's `rev` and the `additional_dependencies` of `node`,
  `python`, and `golang` hooks, never a `language: system` hook's `entry`, so a
  `custom.regex` manager over `.pre-commit-config.yaml` tracks the pins.

### The bun rule governs how this repository runs JavaScript

Running JavaScript through `bun` binds this repository's own invocations, not
what the image ships to its users: Node.js with its bundled `npm`, and Yarn,
installed by the `nodejs` role as a bun global, stay in the image.

Rejected:

- **Removing Node.js, `npm`, and Yarn from the image.** Users of the image run
  their own projects' JavaScript tooling, which this repository's rule does not
  govern.

### pre-commit's store stays off the checkout

The store takes its default path on the home volume, which belongs to the
container and outlives a rebuild. A cache mounted inside the checkout would make
its usability depend on the checkout's owner and filesystem.

Rejected:

- **A cache volume shared by every worktree.** Warm across worktrees after the
  first create, but one more volume to manage; each instance's home volume
  already isolates a worktree's state.

### A push to main is checked from the last passing run

The cooldown on `main` cancels runs before they build, so their commits never
reach a pre-commit job of their own. Starting the range at the head commit of
the last successful push run keeps every commit on `main` checked by the hooks
and scanned by gitleaks.

Rejected:

- **Checking only `before..after` of the latest push.** A commit whose run the
  cooldown cancelled would never be checked or scanned.

### The gitleaks mode switch is inline in the hook

The gitleaks hook chooses its scan mode in an inline `bash -c` entry in
`.pre-commit-config.yaml`, so the hook is self-contained for a template consumer
who copies that one file.

Rejected:

- **A script the hook calls.** A consumer copying the configuration would also
  have to copy the script.

### The `pre-commit` CI job has no path filter

pre-commit already skips a hook whose files did not change, so a path filter
saves nothing, and the `always_run` hooks, gitleaks and `no-commit-to-branch`,
must run on every event.

### Ship records are checked by a CLI, not a schema

A done bug's `## Fix` is enforced mechanically, by
`scripts/check-ship-records.py`. `iwe` accepts a conditional in a document
schema only inside `frontmatter`: a document-level `if`/`then` or `anyOf` fails
as an unknown keyword, and requiring `## Fix` on every bug is wrong because an
open bug has none. The check is a CLI under test, run by its tests on made-up
documents, rather than a pytest file like the `plan-checkboxes` hook. It checks
section shape only; whether a `## Fix` describes the shipped fix is
`iwe-ship-reviewer`'s judgment. It lives in `scripts/`, outside the agentdev
plugin, so `iwe-bootstrap` does not install it.

Rejected:

- **A `## Fix` section required by the bug schema.** It fails every open bug.
- **Nothing mechanical enforces a done bug's `## Fix`.** Reversed by the
  repository owner.
