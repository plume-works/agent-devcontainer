---
type: bug
description: A Coder workspace keeps the Dev Container image it was built with, so one built before gitleaks and actionlint were pinned fails every commit and push on those pre-commit hooks while the health report says nothing is missing.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T21:00:00Z
sources:
- resource: .pre-commit-config.yaml
- resource: ansible/roles/dev_tools/defaults/main.yml
- resource: ansible/roles/dev_tools/tasks/install_pinned_tool.yml
- resource: .devcontainer/scripts/environment-health.sh
- resource: .devcontainer/scripts/setup-pre-commit.sh
- resource: docs/knowledge/data/spec/coder-ide-baseline.md
- resource: https://github.com/plume-works/agent-devcontainer/pull/440
stage: done
---

# Bug: a workspace on a pre-pin image has no gitleaks or actionlint and nothing says so

## Symptom

In a Coder workspace whose Dev Container was built before 2026-10-24, every
`git commit` and every `git push` fails in the pre-commit hooks with
`Executable 'gitleaks' not found` and, for a workflow file,
`Executable 'actionlint' not found`. The failure also stops the gh-stack guard's
`publish`, whose push runs the same pre-push hook. The workspace's health report
passes its toolchain section, because neither binary is on its list, so the
workspace looks healthy until the first commit.

## Reproduction

1. In Coder workspace `agent-dev1`, `command -v gitleaks actionlint` finds
   nothing, while `zizmor`, `iwe`, and `bun` are at `/usr/local/bin`, where the
   `dev_tools` role installs every pinned tool.
2. The image's own versions date it: `iwe 0.29.0` and `uv 0.13.5` against the
   repository's `iwe-v0.29.3` and `0.13.6`, and `/usr/local/bin/uv` carries a
   build timestamp of 2026-10-24 00:49 UTC.
3. PR #440, which added the two tools to `dev_tools_pinned_tools`, merged at
   2026-10-24 02:37 UTC, after that build.
4. `docker run --rm --pull always ghcr.io/plume-works/agent-desktop:edge`
   (digest `a4773a7`, revision 208a6bd) has `gitleaks 8.30.1`,
   `actionlint 1.7.12`, `iwe 0.29.3`, and `uv 0.13.6`: the published image is
   complete, and the running one is not it.
5. `SKIP=gitleaks,actionlint git commit` succeeds, which is how the failure
   presents as a missing binary rather than a finding.

## Root cause

Two behaviours combine. The `gitleaks` and `actionlint` hooks are
`language: system`, so they run whatever binary the image provides and fail hard
when it is absent. And a Coder workspace keeps the Dev Container image it was
built with across restarts, as the Coder IDE baseline requires, so a workspace
built before the pins landed never gains the binaries until someone rebuilds the
Dev Container. Nothing closes the gap in between: the health report's required
toolchain list does not include the pre-commit system binaries, and the
pre-commit setup step installs the hooks without checking that their executables
exist.

## Fix

The workspace itself is repaired by rebuilding its Dev Container, which picks up
the current digest pin. The lasting fix is detection, shipped by [Replace the
runtime shell scripts with one agentdev-runtime
CLI](../plans/20261029-off-bash-migration.md): `agentdev-runtime doctor` lists
`gitleaks` and `actionlint` as required tools (commit 76a1836), and
`agentdev-runtime project hooks` warns about each `language: system` hook whose
executable is not on `PATH` when it installs the hooks, instead of leaving the
failure to the first commit (commit 4773feb).

## Key references

Verified anchor points (line numbers as of 2026-10-29):

- `.pre-commit-config.yaml:56` — `gitleaks` hook, `language: system` at `:59`
- `.pre-commit-config.yaml:62` — `actionlint` hook, `language: system` at `:65`
- `ansible/roles/dev_tools/defaults/main.yml:33` — `gitleaks` pin
- `ansible/roles/dev_tools/defaults/main.yml:45` — `actionlint` pin
- `ansible/roles/dev_tools/tasks/install_pinned_tool.yml:50` — install to
  `/usr/local/bin`
- `.devcontainer/scripts/environment-health.sh:79` — required toolchain list
  without the two tools
- `.devcontainer/scripts/setup-pre-commit.sh:41` — hook install with no
  executable check
- `docs/knowledge/data/spec/coder-ide-baseline.md:83` — a restart keeps the
  built Dev Container image
