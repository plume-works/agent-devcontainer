---
type: codebase
description: 'Every gate a pull request passes: formatting, the image build, agent-file and knowledge-base validation, and the AI review, with the local pre-commit mirror.'
source:
- .github
- .pre-commit-config.yaml
source_digest: sha256:5d18a507612e28382e827ae37c8f16cddfefef919961603c62422c56d5857156
verified:
  by: claude/opus-5
  at: 2026-09-06T00:00:00Z
stale_after: 2026-12-05
generated:
  by: claude/opus-5
  at: 2026-09-06T00:00:00Z
sources:
- id: code
  resource: .github
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
4. `validate-agent-files.yml`, when the catalog, the validator, or the codebase
   map changed: both pytest suites,
   `validate_agent_files --recommend . --require-marketplace claude codex`, then
   `stale-map-docs.py`, which fails the job when a map doc no longer matches the
   code it describes — `.github/workflows/validate-agent-files.yml:73-83`
5. `validate-knowledge-base.yml`, when `docs/knowledge/`, `.iwe/`, or the IWE
   seed changed: `iwe schema validate`, `iwe normalize` must be a no-op, and the
   plan-checkbox tests; a second, path-filtered pytest pass assembles and
   validates the consumer seed —
   `.github/workflows/validate-knowledge-base.yml:40-45,69-109`, in
   [the knowledge workspace](docs/knowledge.md)
6. `ai-responder.yml`: `preflight` admits only `plume-works` events from
   non-fork, non-bot PRs or `@claude` mentions; `claude-respond` runs the review
   or task through `anthropics/claude-code-action`; `ai-review-present` reports
   whether an accepted review exists —
   `.github/workflows/ai-responder.yml:82,377,462`
7. Merge: `merge_group` runs steps 2–6 again with a clean image build.

## Failure modes

- A formatting commit in step 2 means this run's downstream jobs are skipped;
  the pushed commit's run is the one that counts.
- A fork PR never gets step 6; the review gate is then a human's.
- Step 1 and step 2 must agree on tool versions; `renovate.json` disables
  Renovate for the Super-Linter family so
  `/agentdev:sync-super-linter-tool-versions` moves them together.
