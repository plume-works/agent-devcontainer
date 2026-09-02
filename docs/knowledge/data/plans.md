---
type: hub
description: Implementation plans, migrations, and design proposals, one document per unit of work.
stage: living
generated:
  by: codex
  at: 2026-08-16T01:27:59Z
---

# 🗺️ Plans

*Every plan lives in `plans/YYYYMMDD-<slug>.md` and is listed here, always — a
status change moves its link between sections, never removes it. `## Active`
holds plans without a `status`; `## Done` mirrors `status: done`; `## Cancelled`
mirrors `status: cancelled`. The plan skill files new plans, the ship skill
moves them.*

## Active

[Persist the pre-commit hook cache on the agentdev-cache volume](plans/20260902-persist-pre-commit-cache.md)

[Gitignore-aware file discovery in validate_agent_files](plans/20260901-gitignore-aware-discovery.md)

[Move the IWE workflow skills into the agentdev plugin](plans/20260816-move-iwe-skills-to-agentdev.md)

[Install the agentdev catalog into the image](plans/20260817-catalog-install-in-image.md)

## Done

[Critical docs and durable-knowledge review in pr-review](plans/20260831-pr-review-docs-durable-knowledge.md)

[Split PR How to Test into Verification and Reviewer Handoff](plans/20260815-pr-verification-sections.md)

[Let pre-commit own formatting](plans/20260831-pre-commit-owns-formatting.md)

[AI responder workflows](plans/20260816-ai-responder-workflows.md)

[Preserve approved wording across the explore handoff](plans/20260817-preserve-approved-wording.md)

[Never write a working logbook](plans/20260817-no-logbooks-in-the-graph.md)

[Embed structured spec deltas in IWE plans](plans/20260816-structured-plan-spec-deltas.md)

[Make plan checkboxes carry their evidence](plans/20260815-honest-plan-checkboxes.md)

[Name the missing handoff routes in explore and verify](plans/20260816-skill-handoff-routes.md)

[Strengthen the workflow skill contracts](plans/20260815-strengthen-workflow-skill-contracts.md)

[Finish uv-run-only in CI](plans/20260815-uv-run-in-ci.md)

[Drop the .venv symlink](plans/20260814-drop-venv-symlink.md)

## Cancelled
