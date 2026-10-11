---
type: bug
stage: done
description: The image build installed gh-stack with `gh extension install`, which demands GitHub authentication even for a public extension, so any gh-stack pin bump failed the development image build.
generated:
  by: claude-code/opus-5.5
  at: 2026-10-10T08:00:00Z
sources:
- resource: ansible/roles/github_cli/tasks/main.yml
- resource: ansible/roles/github_cli/defaults/main.yml
- resource: scripts/refresh-pin-checksums.py
- resource: https://github.com/plume-works/agent-devcontainer/pull/296
- resource: https://github.com/github/gh-stack/releases/tag/v0.2.1
---

# Bug: gh-stack extension install needs a token the image build lacks

## Symptom

A development image build that changes `github_cli_gh_stack_version` fails in
the `github_cli` role with exit code 4 and
`To get started with GitHub CLI, please run: gh auth login`. Builds that keep
the pin pass, because the cached layer's extension manifest already names the
pinned tag and the install is skipped.

## Reproduction

1. Bump `github_cli_gh_stack_version` in
   `ansible/roles/github_cli/defaults/main.yml` (Renovate PR #296 bumps it to
   `v0.2.1`).
2. Build the development image without a `GH_TOKEN`.
3. The install task runs
   `/usr/bin/gh extension install github/gh-stack --pin <tag>` and fails with
   exit code 4.

## Root cause

`gh extension install` requires an authenticated `gh` regardless of the
extension's visibility, and the image build provides no token. The task bypassed
the auth shim on the premise that a public extension needs none.

## Fix

Fixed. The role downloads the `linux-<arch>` release binary straight from
`github.com/github/gh-stack/releases`, verifies it against a per-architecture
SHA-256 in `github_cli_gh_stack_checksums`, and writes the binary-extension
`manifest.yml` that `gh` reads. The pin is registered in `PIN_FILES`, so
Renovate's post-upgrade task recomputes the checksums on every bump.

## Key references

Verified anchor points (line numbers as of 2026-10-10):

- `ansible/roles/github_cli/tasks/main.yml:102` — Download the pinned gh-stack
  extension binary
- `ansible/roles/github_cli/tasks/main.yml:111` — Register gh-stack as a pinned
  binary extension
- `ansible/roles/github_cli/defaults/main.yml:11` —
  `github_cli_gh_stack_checksums`
- `scripts/refresh-pin-checksums.py:119` — `PIN_FILES` entry for the
  `github_cli` defaults
