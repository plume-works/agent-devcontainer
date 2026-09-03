---
type: codebase
description: 'Every gate a pull request passes: formatting, the image build, agent-file and knowledge-base validation, and the AI review, with the local pre-commit mirror.'
source:
- .github
- .pre-commit-config.yaml
commit: eb60f60450c6009b076bc51993b49a924653eaa4
verified:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:09:00Z
stale_after: 2026-12-02
generated:
  by: claude-code/fable-5.1
  at: 2026-09-03T20:09:00Z
sources:
- id: code
  resource: .github
  title: the code this map describes, read at commit eb60f60
---

# Flow: pull request checks

Four workflows fire on a pull request; three are path-filtered, one is
policy-filtered. Locally, pre-commit runs the same formatters and validators
before the push.

## Trace

1. `pre-commit` (local, on every commit): Prettier, clang-format, ansible-lint,
   hadolint, ruff format and lint, shellcheck, gitleaks, actionlint, zizmor, the
   agent-files validator, plan-checkbox and IWE validation and normalization —
   `.pre-commit-config.yaml:2-111`
2. `primary-checks.yml` → `reformat.yml`: Super-Linter in fix mode; for a
   same-repository, non-draft PR, formatting changes are committed back and the
   `gate` withholds `run_downstream` so the next run checks the pushed commit —
   `.github/workflows/reformat.yml:180,274,409`, in
   [workflows](github/workflows.md)
3. `primary-checks.yml` → `ci.yml`, when the image filter matched:
   [the image build](flow-image-build.md)
4. `validate-agent-files.yml`, when the catalog or the validator changed: both
   pytest suites, then
   `validate_agent_files --recommend . --require-marketplace claude codex` —
   `.github/workflows/validate-agent-files.yml:68-74`
5. `validate-knowledge-base.yml`, when `docs/knowledge/` or `.iwe/` changed:
   `iwe schema validate`, `iwe normalize` must be a no-op, and the plan-checkbox
   tests — `.github/workflows/validate-knowledge-base.yml:78-89`, in
   [the knowledge workspace](docs/knowledge.md)
6. `ai-responder.yml`: `preflight` admits only `plume-works` events from
   non-fork, non-bot PRs or `@claude` mentions; `claude-respond` runs the review
   or task through `anthropics/claude-code-action`; `ai-review-present` reports
   whether an accepted review exists —
   `.github/workflows/ai-responder.yml:82,371,551`
7. Merge: `merge_group` runs steps 2–6 again with a clean image build.

## Failure modes

- A formatting commit in step 2 means this run's downstream jobs are skipped;
  the pushed commit's run is the one that counts.
- A fork PR never gets step 6; the review gate is then a human's.
- Step 1 and step 2 must agree on tool versions; `renovate.json` disables
  Renovate for the Super-Linter family so
  `/agentdev:sync-super-linter-tool-versions` moves them together.
