---
type: codebase
description: 'Every gate a pull request passes: formatting, the image build, agent-file, knowledge-base and Renovate-config validation, and the AI review, with the local pre-commit mirror.'
source:
- .github
- .pre-commit-config.yaml
source_digest: sha256:e8bf5910dc67a07c0d7398341944fb9b4ed83dae28b981ceedeb3e596e0135b3
verified:
  by: claude-code/opus-5.5
  at: 2026-10-18T18:45:54Z
stale_after: 2027-01-16
generated:
  by: claude-code/opus-5.5
  at: 2026-10-18T18:45:54Z
sources:
- id: code
  resource: .github
---

# Flow: pull request checks

Six workflows fire on a pull request; five are path-filtered, one is
policy-filtered. Locally, pre-commit runs the same formatters and validators
before the push.

## Trace

1. `pre-commit` (local, on every commit): Prettier, clang-format, ansible-lint,
   hadolint, ruff format and lint, shellcheck, gitleaks, actionlint (with
   `.github/actionlint.yml`, which Super-Linter reads too),
   `renovate-config-validator`, zizmor, the agent-files validator, plan-checkbox
   and IWE validation and normalization, Prettier and the Renovate validator
   through `bunx` — `.pre-commit-config.yaml:2-126`; `no-commit-to-branch`
   refuses a commit on `main` or `master` — `.pre-commit-config.yaml:11`
2. `primary-checks.yml` → `reformat.yml`: Super-Linter in fix mode; for a
   same-repository, non-draft PR, formatting changes are committed back and the
   `gate` withholds `run_downstream` so the next run checks the pushed commit;
   on a Renovate bot's PR nothing is pushed and the `gate` fails —
   `.github/workflows/reformat.yml:186,280,422`, in
   [workflows](github/workflows.md)
3. `primary-checks.yml` → `ci.yml`, when the image filter matched: [the image
   build](flow-image-build.md), whose `finished` also waits on native
   `agent-opencode` container acceptance
4. `opencode-runtime-checks.yml`, when `opencode-compose-pins.yml` or a
   `compose.opencode*.yml` file changed: unless CI/CD's own path filter also
   matched, it requires a `@sha256:` pin, renders the Compose tests, and runs
   container acceptance on that digest on amd64 and arm64, without building;
   otherwise it defers to step 3 —
   `.github/workflows/opencode-runtime-checks.yml:47,57-65`
5. `validate-agent-files.yml`, when any source declared by the codebase map or
   the map itself changed: the validator, agentdev, and self-improve pytest
   suites, the OpenCode bridge `bun test` suite,
   `validate_agent_files --recommend . --require-marketplace claude codex`, then
   `stale-map-docs.py`, which fails the job when a map doc no longer matches the
   code it describes — `.github/workflows/validate-agent-files.yml:39-100`
6. `validate-knowledge-base.yml`, when `docs/knowledge/`, `.iwe/`, the IWE seed,
   or the `dev_tools` pins changed, with the pinned `iwe`:
   `iwe schema validate`, `iwe normalize` must be a no-op, and the plan-checkbox
   tests; a second, path-filtered pytest pass assembles and validates the
   consumer seed — `.github/workflows/validate-knowledge-base.yml:39-48,70-105`,
   in [the knowledge workspace](docs/knowledge.md)
7. `validate-renovate-config.yml`: its `paths-filter` passes when
   `renovate.json`, `.pre-commit-config.yaml`, `devcontainer-compose-pins.yml`,
   the workflow, or the image sources changed; `validate` then runs
   `renovate-config-validator --no-global --strict` inside the pinned
   `agent-desktop` image at the Renovate release the hook's `bunx` pin names,
   and `finished` reports the required result either way —
   `.github/workflows/validate-renovate-config.yml:26,52,70-76,78`
8. `ai-responder.yml`: `preflight` admits only `plume-works` events from
   non-fork, non-bot PRs or `@claude` mentions and resolves the review's effort
   tier; `claude-respond` runs the review or task through
   `anthropics/claude-code-action`, sizing the session from that tier;
   `ai-review-present` reports whether an accepted review exists, waived for the
   Renovate and Dependabot bots —
   `.github/workflows/ai-responder.yml:89,421,509`
9. Merge: `merge_group` runs steps 2, 3, and 5–8 again with a clean image build;
   step 4 runs on pull requests only.

## Failure modes

- A formatting commit in step 2 means this run's downstream jobs are skipped;
  the pushed commit's run is the one that counts.
- Step 2 never pushes to a Renovate branch, since Renovate abandons a branch
  carrying a foreign commit; formatting a Renovate PR needs is the post-upgrade
  task's job — [Renovate
  post-upgrade](../architecture/renovate-post-upgrade.md).
- A fork PR never gets step 8; the review gate is then a human's.
- Step 8's effort tier changes what the review costs, never whether it runs:
  `ai-review-present` does not read it, and both tiers keep the metadata check
  and the durable-knowledge pass.
- Step 1 and step 7 run the same validator against the same file at the one
  Renovate version the bot runs; an `agent-desktop` digest bump reaches step 7
  through the pin file, so an image that cannot run the bot fails here first.
- Step 1 and step 2 must agree on tool versions; `renovate.json` disables
  Renovate for the Super-Linter family so
  `/agentdev:sync-super-linter-tool-versions` moves them together.
