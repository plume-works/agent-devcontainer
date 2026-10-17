---
type: codebase
description: 'The nine workflows: primary-checks orchestrating reformat and ci, the agent-files, knowledge-base and Renovate-config validators, the self-hosted Renovate bot, the AI responder, and the manual container cleanup.'
source: .github/workflows
source_digest: sha256:c43fcd5407aed447f6fee5e4fa78905512a3c62c55a3cc4a05f3325f46a09f44
verified:
  by: claude-code/opus-5.5
  at: 2026-10-17T23:50:00Z
stale_after: 2027-01-15
generated:
  by: claude-code/opus-5.5
  at: 2026-10-17T23:50:00Z
sources:
- id: code
  resource: .github/workflows
---

# Workflows

Two reusable workflows behind one entry point, four path-filtered checks, a
deployment-pin check, the scheduled Renovate bot, and one manual job.

## Public surface

| Workflow                       | Trigger                                                 | Jobs                                                                                                                                         |
| ------------------------------ | ------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `primary-checks.yml`           | push to `main`/`v*`, PR, merge group, dispatch          | `reformat` → `ci` (only when `run_downstream`)                                                                                               |
| `reformat.yml`                 | `workflow_call`                                         | `paths-filter` → `super-linter` (autofix) → `commit-format-changes` → `gate`                                                                 |
| `ci.yml`                       | `workflow_call`                                         | `paths-filter` → `build-dev-image` (amd64 + arm64) → `merge-dev-image` → `dev-container-ci` + `opencode-acceptance` → `finished`             |
| `opencode-runtime-checks.yml`  | PR touching the OpenCode pin or Compose files, dispatch | `acceptance` (amd64 + arm64): native container acceptance of the pinned `agent-opencode` digest, skipped when other files changed too        |
| `validate-agent-files.yml`     | PR, push, merge group                                   | three pytest suites and the OpenCode bridge bun suite, the validator with `--require-marketplace claude codex`, then the map-staleness check |
| `validate-knowledge-base.yml`  | PR, push, merge group                                   | graph schema/normalization, plan-checkbox tests, path-filtered standalone seed tests                                                         |
| `validate-renovate-config.yml` | PR, push, merge group, dispatch                         | `paths-filter` → `validate` (in `agent-desktop`, at the hook's Renovate pin) → `finished`                                                    |
| `renovate.yml`                 | push to `main`, schedule, checkboxes, dispatch          | `renovate`: the bot at the hook's Renovate pin, in `agent-desktop`, as the Renovate GitHub App                                               |
| `ai-responder.yml`             | `@claude` comments, PR events, issues, dispatch         | `preflight` → `bridge` / `claude-respond` / `claude-task` → `ai-review-present`                                                              |
| `delete-old-containers.yml`    | dispatch                                                | prune old package versions                                                                                                                   |

## How it works

Every check job starts with the shared `paths-filter` action and skips when
nothing relevant changed. `reformat` runs Super-Linter in fix mode and, for a
same-repository non-draft PR, commits the formatting back; its `gate` publishes
`run_downstream`, false when a formatting commit was pushed, so `ci` waits for
the next run. `ci` builds `ubuntu-ansible` then `agent-desktop` per
architecture, reusing the published `edge` image as a base unless the run is on
`main`, a tag, a merge group, or the commit says `[ci:clean_build]`, and builds
`agent-opencode` on the desktop digest the same job produced. It merges each
image's per-arch digests into its own manifest, then patches the desktop pin and
smoke-tests the devcontainer with `devcontainers/ci`. In parallel,
`opencode-acceptance` runs `test-agent-runtime.sh` as root against the merged
`agent-opencode` digest on each native architecture.
`opencode-runtime-checks.yml` runs the same acceptance on the digest
`opencode-compose-pins.yml` proposes and builds nothing; it requires the pin to
carry `@sha256:`. The responder only runs for `plume-works` and never for a fork
PR; its preflight decides between a review and a task, resolves the review's
effort tier, and `ai-review-present` reports whether an accepted review exists.
`renovate.yml` and the Renovate-config `validate` job run in `agent-desktop` at
the digest `devcontainer-compose-pins.yml` pins, and both read the Renovate
version from the `renovate-config-validator` hook's
`bunx --package renovate@<version>` entry in `.pre-commit-config.yaml`; the bot
authenticates with a GitHub App token and takes its global options from
`RENOVATE_*` variables. A person's edit of the Dependency Dashboard issue or of
a Renovate PR's body starts a run; the bot's own edits never do. PR edits arrive
through `pull_request_target`, which still fires on a conflicted PR and never
checks out PR code. Every run queues in one job-level concurrency group, so two
never write the same branch at once and a skipped bot edit never enters it.
Knowledge validation always checks this graph when its outer filter passes and
runs the standalone consumer-seed suite only when its inner seed filter passes.
Agent-file validation's filter covers the union of codebase map `source` paths,
then its final step verifies every recorded digest. The full traces are [the
image build flow](../flow-image-build.md) and [the pull request checks
flow](../flow-pull-request-checks.md).

## Depends on

[the composite actions](actions.md), `anthropics/claude-code-action`,
`devcontainers/ci`, `dorny/paths-filter`, `super-linter`.

## Invariants & gotchas

- `validate-knowledge-base.yml` installs `iwe` from the
  [dev_tools](../ansible/roles/dev_tools.md) pin, so its paths filter includes
  that pin file.
- `permissions: {}` at the top of `primary-checks.yml`; each job grants only
  what it uses.
- `finished` needs `opencode-acceptance`, so a failed native runtime acceptance
  fails CI.
- The `agent-desktop` digest in `renovate.yml`, `validate-renovate-config.yml`,
  and the responder's two container jobs must equal
  `devcontainer-compose-pins.yml`'s; see [image
  pinning](../../spec/image-pinning.md).
- `RENOVATE_ALLOWED_COMMANDS` admits only `scripts/renovate-post-upgrade.sh`,
  the one `postUpgradeTasks` command `renovate.json` runs.
- The Renovate App token names its permissions; one Renovate newly needs is
  added to the token step as well as to the App. See [Renovate
  post-upgrade](../../architecture/renovate-post-upgrade.md).
- `Renovate config validation finished` reports on every PR, so it can be a
  required check while `validate` is path-filtered; the version and flag choices
  are [Renovate config
  validation](../../architecture/renovate-config-validation.md).
- `commit-format-changes` skips the push on a PR authored by a login in its
  `RENOVATE_BOT_ACTORS`, so the `gate` fails rather than put a foreign commit on
  a branch Renovate would then stop updating.
- Runners are chosen by the `AMD_ONLY`/`ARM_ONLY` repository variables so a fork
  without ARM runners can still build.
- A `[ci:skip-ai-review]` marker alone on a line of the PR body suppresses the
  review job only; `ai-review-present` never reads it, so the gate cannot be
  waived from an author-controlled body, and an explicit `@claude review`
  outranks it. The policy is in [AI review gate](../../spec/ai-review-gate.md).
- A `[ci:review-effort=light|full]` marker on its own line, or an
  `@claude review light|full` comment that outranks it, selects the review's
  effort tier; preflight resolves it because only a workflow-level `--model` can
  size the session. The reasoning is in [PR review effort
  tiers](../../architecture/pr-review-effort-tiers.md).
- The `if:` gate admitting an `@claude` mention folds case, because the workflow
  expression language's `startsWith` does. Every mention test in the workflow's
  JavaScript folds it too, so the two agree on what a mention is — see [the
  capitalized-mention
  misroute](../../bugs/responder-mention-case-sensitivity.md).

## Key references

Verified anchor points (line numbers as of 2026-10-17):

- `.github/workflows/primary-checks.yml:31,53` — `reformat`, `ci`
- `.github/workflows/reformat.yml:186,280,422` — `super-linter`,
  `commit-format-changes`, `gate`
- `.github/workflows/ci.yml:71,99,182,231` — build matrix, base-image selection,
  merge, devcontainer smoke
- `.github/workflows/ci.yml:163,217` — the `agent-opencode` build on the desktop
  digest and its merge
- `.github/workflows/ci.yml:260` — patch the digest pin for the smoke test
- `.github/workflows/ci.yml:309,347` — `opencode-acceptance`, `finished`
- `.github/workflows/opencode-runtime-checks.yml:50,69-76` — deployment-only
  scope check and the digest requirement
- `.github/workflows/validate-agent-files.yml:39-100` — map-source filter and
  the check steps
- `.github/workflows/validate-knowledge-base.yml:39-48,85-105` — paths filter,
  pinned iwe, graph validation, and the path-filtered seed suite
- `.github/workflows/ai-responder.yml:89,363,421,468,509` — the five jobs
- `.github/workflows/ai-responder.yml:192,194` — the skip and effort body
  markers, both anchored to their own line
- `.github/workflows/ai-responder.yml:298,402-407` — `opensWith`, and the
  bridge's review-versus-task split and effort label
- `.github/workflows/validate-renovate-config.yml:26,52,78` — `paths-filter`,
  `validate`, `finished`
- `.github/workflows/validate-renovate-config.yml:59-60,70-76` — pinned
  container, pin read and validator run
- `.github/workflows/renovate.yml:9-15,31-44` — checkbox triggers and the job
  `if:` admitting only a person's dashboard or Renovate PR body edit
- `.github/workflows/renovate.yml:47-49` — job-level concurrency group
- `.github/workflows/renovate.yml:53-54,64-70` — pinned container, pin read
- `.github/workflows/renovate.yml:75-88` — App token and its named permissions
- `.github/workflows/renovate.yml:90-113` — commit identity, bot run
