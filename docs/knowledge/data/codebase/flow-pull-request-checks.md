---
type: codebase
description: 'Every gate a pull request passes: formatting, the image build, agent-file and knowledge-base validation, and the AI review, with the local pre-commit mirror.'
source:
- .github
- .pre-commit-config.yaml
source_digest: sha256:b5a2883e1b540b9411851c8686a579030a6658a8f9aba7f019be4444d7defb87
verified:
  by: claude-code/opus-5.5
  at: 2026-09-25T00:00:00Z
stale_after: 2026-12-24
generated:
  by: claude-code/opus-5.5
  at: 2026-09-25T00:00:00Z
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
   hadolint, ruff format and lint, shellcheck, gitleaks, actionlint,
   `renovate-config-validator`, zizmor, the agent-files validator, plan-checkbox
   and IWE validation and normalization — `.pre-commit-config.yaml:2-137`
2. `primary-checks.yml` → `reformat.yml`: Super-Linter in fix mode; for a
   same-repository, non-draft PR, formatting changes are committed back and the
   `gate` withholds `run_downstream` so the next run checks the pushed commit —
   `.github/workflows/reformat.yml:180,274,409`, in
   [workflows](github/workflows.md)
3. `primary-checks.yml` → `ci.yml`, when the image filter matched:
   [the image build](flow-image-build.md)
4. `validate-agent-files.yml`, when any source declared by the codebase map or
   the map itself changed: the validator, agentdev, and self-improve pytest
   suites,
   `validate_agent_files --recommend . --require-marketplace claude codex`, then
   `stale-map-docs.py`, which fails the job when a map doc no longer matches the
   code it describes — `.github/workflows/validate-agent-files.yml:38-93`
5. `validate-knowledge-base.yml`, when `docs/knowledge/`, `.iwe/`, or the IWE
   seed changed: `iwe schema validate`, `iwe normalize` must be a no-op, and the
   plan-checkbox tests; a second, path-filtered pytest pass assembles and
   validates the consumer seed —
   `.github/workflows/validate-knowledge-base.yml:40-45,69-109`, in
   [the knowledge workspace](docs/knowledge.md)
6. `validate-renovate-config.yml`, when `.github/renovate.json` changed:
   `renovate-config-validator --no-global --strict` against it, from the current
   unpinned Renovate rather than the version the hook pins —
   `.github/workflows/validate-renovate-config.yml:48-51`
7. `ai-responder.yml`: `preflight` admits only `plume-works` events from
   non-fork, non-bot PRs or `@claude` mentions and resolves the review's effort
   tier; `claude-respond` runs the review or task through
   `anthropics/claude-code-action`, sizing the session from that tier;
   `ai-review-present` reports whether an accepted review exists —
   `.github/workflows/ai-responder.yml:89,421,509`
8. Merge: `merge_group` runs steps 2–7 again with a clean image build.

## Failure modes

- A formatting commit in step 2 means this run's downstream jobs are skipped;
  the pushed commit's run is the one that counts.
- A fork PR never gets step 7; the review gate is then a human's.
- Step 7's effort tier changes what the review costs, never whether it runs:
  `ai-review-present` does not read it, and both tiers keep the metadata check
  and the durable-knowledge pass.
- Step 1 and step 6 run the same validator against the same file on purpose, the
  hook at a pinned Renovate and the workflow at whatever the hosted app
  currently runs; a break in the workflow alone is the warning that the live bot
  is about to break too.
- Step 1 and step 2 must agree on tool versions; `renovate.json` disables
  Renovate for the Super-Linter family so
  `/agentdev:sync-super-linter-tool-versions` moves them together.
