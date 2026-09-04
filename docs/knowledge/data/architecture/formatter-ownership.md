---
type: architecture
description: Every formatter has exactly one owner, Super-Linter's pinned image is the version source of truth, and a script checks the pre-commit and Ansible-provisioned versions against that image so local runs cannot disagree with CI.
generated:
  by: claude-code/opus-5
  at: 2026-09-04T00:00:00Z
sources:
- resource: .pre-commit-config.yaml
- resource: .agents/plugins/agentdev/bin/super-linter-defaults.sh
- resource: scripts/validate-super-linter-tool-versions.sh
- resource: .github/workflows/reformat.yml
- resource: ansible/roles/dev_tools/defaults/main.yml
- resource: https://github.com/Dr-QP/Dr.QP/pull/440
- resource: https://github.com/Dr-QP/Dr.QP/pull/447
---

# Formatter ownership

## Decision

Each formatter and linter has **one owner**. Locally the pre-commit hooks apply
formatting on every commit; in CI the pinned Super-Linter image runs the same
tools as the gate. The pinned image is the **source of truth for versions**, and
`scripts/validate-super-linter-tool-versions.sh` checks the versions used by
pre-commit and by the Ansible-provisioned binaries against the versions actually
inside that image.

The pin lives in two places that must move together:
`SUPER_LINTER_DEFAULT_IMAGE` in `super-linter-defaults.sh`, read by the local
wrapper and by the version check, and the action refs in `reformat.yml`, which
pin the same version independently and never read that file.

## Why single ownership

Two tools that both claim a file rewrite each other's output. The result is not
a merge conflict but a churn: one formatter reformats, the other reverts, and
the diff depends on which ran last. Naming one owner per language removes the
ambiguity.

## Why version parity needs a check rather than a convention

Same tool, different version, different output — neither side misconfigured, and
no local signal that they disagree. A stale local formatter yields a clean
commit and a red pipeline, with the explaining diff invisible in both places.

The drift is introduced by a Super-Linter image bump, which changes a tool
version underneath the repository without touching local configuration. The
check turns that into a failure at the point of drift, naming the tool and both
versions.

The direction of authority matters: the image is what gates merges, so local
configuration is checked **against** it, never the reverse.

## What the check covers

Version agreement across three surfaces: the hook revisions in
`.pre-commit-config.yaml`, the pinned single-binary tools installed by the
`dev_tools` Ansible role, and the versions inside the Super-Linter image. It
requires a container runtime, since it inspects the image itself.

## Consequences

- Bumping the Super-Linter image is not a one-line change; the pre-commit
  revisions and any provisioned binary version move with it, and the check is
  what says which.
- A tool provisioned into the image for local use, rather than pulled by
  pre-commit, still participates in the parity contract.
- Contributors reproduce CI's formatting result locally, so the formatting
  commit is not a surprise in review.
