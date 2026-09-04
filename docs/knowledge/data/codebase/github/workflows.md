---
type: codebase
description: 'The seven workflows: primary-checks orchestrating reformat and ci, the agent-files and knowledge-base validators, the AI responder, and the manual container cleanup.'
source: .github/workflows
source_digest: sha256:38b3b7b488124d344c19272797c87d23b1425d8f862f2196fdf9a49b64a890fa
verified:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
stale_after: 2026-12-03
generated:
  by: codex/gpt-5
  at: 2026-09-04T20:20:44Z
sources:
- id: code
  resource: .github/workflows
---

# Workflows

Two reusable workflows behind one entry point, three path-filtered checks, and
one manual job.

## Public surface

| Workflow                      | Trigger                                         | Jobs                                                                                                     |
| ----------------------------- | ----------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `primary-checks.yml`          | push to `main`/`v*`, PR, merge group, dispatch  | `reformat` → `ci` (only when `run_downstream`)                                                           |
| `reformat.yml`                | `workflow_call`                                 | `paths-filter` → `super-linter` (autofix) → `commit-format-changes` → `gate`                             |
| `ci.yml`                      | `workflow_call`                                 | `paths-filter` → `build-dev-image` (amd64 + arm64) → `merge-dev-image` → `dev-container-ci` → `finished` |
| `validate-agent-files.yml`    | PR, push, merge group                           | both pytest suites, then the validator with `--require-marketplace claude codex`                         |
| `validate-knowledge-base.yml` | PR, push, merge group                           | `iwe schema validate`, `iwe normalize` no-op check, plan-checkbox tests                                  |
| `ai-responder.yml`            | `@claude` comments, PR events, issues, dispatch | `preflight` → `bridge` / `claude-respond` / `claude-task` → `ai-review-present`                          |
| `delete-old-containers.yml`   | dispatch                                        | prune old package versions                                                                               |

## How it works

Every check job starts with the shared `paths-filter` action and skips when
nothing relevant changed. `reformat` runs Super-Linter in fix mode and, for a
same-repository non-draft PR, commits the formatting back; its `gate` publishes
`run_downstream`, false when a formatting commit was pushed, so `ci` waits for
the next run. `ci` builds `ubuntu-ansible` then `agent-desktop` per
architecture, reusing the published `edge` image as a base unless the run is on
`main`, a tag, a merge group, or the commit says `[ci:clean_build]`; merges the
per-arch digests into one manifest; then patches the digest pin and smoke-tests
the devcontainer with `devcontainers/ci`. The responder only runs for
`plume-works` and never for a fork PR; its preflight decides between a review
and a task, and `ai-review-present` reports whether an accepted review exists.
The full traces are [the image build flow](../flow-image-build.md) and
[the pull request checks flow](../flow-pull-request-checks.md).

## Depends on

[the composite actions](actions.md), `anthropics/claude-code-action`,
`devcontainers/ci`, `dorny/paths-filter`, `super-linter`.

## Invariants & gotchas

- `IWE_VERSION` in `validate-knowledge-base.yml` must match the `iwe` pin in
  [dev_tools](../ansible/roles/dev_tools.md).
- `permissions: {}` at the top of `primary-checks.yml`; each job grants only
  what it uses.
- Runners are chosen by the `AMD_ONLY`/`ARM_ONLY` repository variables so a fork
  without ARM runners can still build.

## Key references

Verified anchor points (line numbers as of 2026-09-04):

- `.github/workflows/primary-checks.yml:31,51` — `reformat`, `ci`
- `.github/workflows/reformat.yml:180,274,409` — `super-linter`,
  `commit-format-changes`, `gate`
- `.github/workflows/ci.yml:62,97,165,204` — build matrix, base-image selection,
  merge, devcontainer smoke
- `.github/workflows/ci.yml:233` — patch the digest pin for the smoke test
- `.github/workflows/validate-agent-files.yml:68-74` — the three check steps
- `.github/workflows/validate-knowledge-base.yml:18,78-89` — `IWE_VERSION`, the
  three checks
- `.github/workflows/ai-responder.yml:82,325,377,421,462` — the five jobs
