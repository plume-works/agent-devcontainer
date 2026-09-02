# Project Update Log

The history of this workspace, newest first. The `ship` skill appends a dated
group on every release; any skill that creates or retires a document adds a line
to the current day's group.

## 2026-09-02

- **Creation**:
  [Install the agentdev catalog into the image](features/catalog-installed-in-image.md)
  implemented, recorded in [unreleased](releases/unreleased.md), with the
  build-time install and the `~/.claude.json` handoff reorder synced into
  [Catalog lifecycle](spec/catalog-lifecycle.md);
  [its plan](plans/20260817-catalog-install-in-image.md) is done.
- **Creation**:
  [Gitignore-aware agent file discovery](features/gitignore-aware-agent-file-discovery.md)
  implemented, recorded in [unreleased](releases/unreleased.md), and specified
  by [Agent file discovery](spec/agent-file-discovery.md);
  [its plan](plans/20260901-gitignore-aware-discovery.md) is done.
- **Creation**:
  [Agentdev IWE workflow skills](features/agentdev-iwe-workflow-skills.md)
  implemented, recorded in [unreleased](releases/unreleased.md), and reflected
  in [Template consumption](spec/template-consumption.md);
  [its plan](plans/20260816-move-iwe-skills-to-agentdev.md) is done.
- **Update**:
  [Persist the pre-commit hook cache on the agentdev-cache volume](plans/20260902-persist-pre-commit-cache.md)
  done — `PRE_COMMIT_HOME` now points at the per-worktree `agentdev-cache`
  volume, so the ~33s cold hook install is paid only on the first create per
  worktree and every rebuild starts warm. The failure-log tail in
  `setup-pre-commit.sh` follows `PRE_COMMIT_HOME`. No behavioral change — cache
  location and startup latency only, so no spec changed.
- **Creation**:
  [Persist the pre-commit hook cache](features/persist-pre-commit-cache.md)
  implemented, recorded in [unreleased](releases/unreleased.md).

## 2026-09-01

- **Update**: PR body structure moved into the `agentdev` catalog, replacing
  `## How to Test` with `## Verification` (closed items, `- [x]` +
  `**Evidence:**`) and `## Reviewer Handoff` (open items, `- [ ]` +
  `**Closed by:**`), per
  [PR verification sections](architecture/pr-verification-sections.md).
  **Downstream break**, in the same register as the `setup-python-venv`
  activation change: a consuming repository that copied
  `.github/pull_request_template.md` still holds the old structural version, and
  its updated `agentdev` skills now ignore it — `pr-gen-description` states the
  structure itself and reports that the copied template was not consulted rather
  than reading one out of it. Adopting means replacing the copied file with the
  pointer stub or deleting it; keeping it costs nothing but a report on every
  run.
- **Creation**:
  [Split PR How to Test into Verification and Reviewer Handoff](features/pr-verification-sections.md)
  implemented, recorded in [unreleased](releases/unreleased.md);
  [its plan](plans/20260815-pr-verification-sections.md) is done.
- **Creation**:
  [Critical docs and durable-knowledge review in pr-review](features/pr-review-docs-durable-knowledge.md)
  implemented, recorded in [unreleased](releases/unreleased.md);
  [its plan](plans/20260831-pr-review-docs-durable-knowledge.md) is done.
  `pr-review` now reviews docs and skills critically by invoking `iwe-audit` in
  a report-only diff mode, with a conditional file-following durable-knowledge
  pass; only version-only and generated-file-only diffs stay fast-approved.

## 2026-08-31

- **Update**:
  [Let pre-commit own formatting](plans/20260831-pre-commit-owns-formatting.md)
  done — the pre-commit hooks are the single local formatting path, now extended
  to merge commits via the `pre-merge-commit` hook type. The `local-reformat`
  mandates in `pr-open` and `git-merge-resolve` and the formatting routes in the
  `principal-engineer` and `tdd-refactor` agents are removed, `local-reformat`'s
  obligation language is softened, and the redundant `python-format-lint` skill
  is retired into the `AGENTS.md` Python section.
- **Creation**:
  [Let pre-commit own formatting](features/pre-commit-owns-formatting.md)
  implemented, recorded in [unreleased](releases/unreleased.md).
- **Update**: [Template consumption](spec/template-consumption.md) §5 item 5 now
  keeps the consuming project's `zizmor` hook as `language: system` resolved
  from `PATH`, dropping the bare-host `zizmorcore/zizmor-pre-commit`
  substitution — a workflow this container-only product does not support. No
  requirement or scenario changed; the edit is procedural adoption guidance.
- **Update**: [AI responder workflows](plans/20260816-ai-responder-workflows.md)
  done — the Claude-only `ai-responder.yml` and the `require-ai-review.yml` gate
  are imported; the responder reviews with the branch's own agentdev catalog and
  an indexed CBM by running the devcontainer lifecycle hooks after checkout, and
  `ai-review-present` is now a required status check in the `main` ruleset.
- **Creation**: [AI responder workflows](features/ai-responder-workflows.md)
  implemented, and [AI review gate](spec/ai-review-gate.md) records the gate's
  acceptance contract and the responder's fork/write-access security boundary.

## 2026-08-24

- **Update**:
  [Preserve approved wording across the explore handoff](plans/20260817-preserve-approved-wording.md)
  done — Explore now writes approved text to `.tmp/approved-wording-<slug>.md`
  before the conversation continues and names that file in the handoff, and
  Plan's task format distinguishes describing an action from paraphrasing
  approved content. Both skills carry the same falsifiable test: whether a
  session starting cold from the written plan could reproduce the agreed bytes.
- **Creation**:
  [Preserved approved wording](features/preserved-approved-wording.md) records
  the split obligation — Explore writes, Plan inlines — and why neither half
  binds alone, plus the rejection of a `data/drafts/` hub in favour of `.tmp/`.
- **Update**: [IWE workflow skills](spec/iwe-workflow-skills.md) extends the
  Explore and Plan requirements with the verbatim-preservation obligation, one
  new scenario on each side.
- **Update**:
  [Never write a working logbook](plans/20260817-no-logbooks-in-the-graph.md)
  done — the rule against working-logbook prose now binds every file in the
  repository from `AGENTS.md` Best Practice 8, with the durable-knowledge
  vocabulary extracted there from `## Project memory` so the graph manual and
  the `iwe-audit` skill point at one definition instead of three.
- **Creation**: [Never write a working logbook](features/no-working-logbooks.md)
  records the two coexisting tests, the graph's three narrative exceptions, the
  plan's single narrative section, Implement's capture-and-route contract, and
  the widened auditor scope. Commit messages stay out; `/agentdev:git-commit`
  owns them.
- **Update**: [IWE workflow skills](spec/iwe-workflow-skills.md) gains
  `Requirement: Plans record intent, not the path taken to it` — the
  workflow-skill half of the rule. The general authoring convention gets no spec
  document, since `AGENTS.md` is its only statement.
- **Creation**:
  [Detect plan narration growth mechanically](backlog/detect-plan-narration-growth.md)
  files the deferred automation. The plan-shape gate reads structure, and
  narration has none — every proxy considered fires on legitimately long plans
  or misses a short dense one.

## 2026-08-16

- **Update**:
  [Embed structured spec deltas in IWE plans](plans/20260816-structured-plan-spec-deltas.md)
  done — `## Spec changes` now has three risk-scaled forms: an explicit `None`,
  a linked spec plus a concise normative outcome, or a fenced
  `ADDED`/`MODIFIED`/`REMOVED` delta carrying complete post-change requirements.
  The change that mattered was naming the delta *intent* rather than truth,
  which dissolved a structural disagreement: Verify had demanded that durable
  specs already reflect an unshipped change while Ship was the skill that
  updates them afterwards. Verify now judges code against the durable spec plus
  the plan's intent, and a not-yet-created spec is valid when the plan supplies
  its contract.
- **Creation**: [Risk-scaled spec deltas](features/risk-scaled-spec-deltas.md)
  records the three forms, the intent-versus-truth boundary, and the four
  exclusions — no change bundle, store, separate delta file, or application
  engine. OpenSpec's notation is adopted; its parser is not.
- **Creation**:
  [Exercise REMOVED delta blocks end to end](backlog/exercise-removed-delta-blocks.md)
  files the gap this shipment left open. `ADDED` and `MODIFIED` were worked end
  to end by the plan's own delta; `REMOVED` was specified in the same pass and
  never run, so the plan's fixture bullet asking for all three is unmet. Verify
  flagged it as a WARNING, not a CRITICAL — no ticked task claimed otherwise.
- **Update**:
  [Make plan checkboxes carry their evidence](plans/20260815-honest-plan-checkboxes.md)
  done — a ticked `- [x]` now requires an indented `- **Evidence:**` child
  naming the commit, test run, or CI run that closed it. A find-and-replace can
  flip eight boxes; it cannot write eight evidence lines. Plan specifies the
  format and gains a task-atomicity rule, Implement writes the evidence in the
  same edit and never changes two boxes at once, and Verify's unchecked-box
  CRITICAL finally has a ticked-box counterpart recommending "untick it". A
  pytest over `data/plans/` enforces the shape from the suite, a pre-commit
  hook, and the knowledge-base CI job — the first gate here that reads plan
  documents rather than agent files.
- **Creation**: [Plan checkbox evidence](spec/plan-checkbox-evidence.md) records
  the contract as durable requirements: what a tick must carry, how tasks are
  sized so a tick can be honest, and what the gate does and cannot do. It reads
  shape only; whether a claim is *true* stays Verify's judgment and a human's.
- **Update**: [Plan checkbox over-claiming](bugs/plan-checkbox-over-claiming.md)
  fixed and recorded in [unreleased](releases/unreleased.md). `48d0f79` had
  fixed the instance and left both root causes standing; this closes them.
- **Update**:
  [Name the missing handoff routes in explore and verify](plans/20260816-skill-handoff-routes.md)
  done — Explore's `## Capturing` now routes an established defect to
  `data/bugs/<slug>.md`, and Verify's unchecked-box CRITICAL offers a third way
  out (revise the plan to drop the task) alongside completing and ticking, which
  Ship's no-override rule had left unstated.
  [Verification in the main loop](features/verification-in-the-main-loop.md)
  records the same three routes. No spec changed: the plan's rationale for that
  was corrected at ship time, since
  [IWE workflow skills](spec/iwe-workflow-skills.md) now covers these skills and
  was re-checked against both edits.
- **Creation**:
  [Strengthen the workflow skill contracts](plans/20260815-strengthen-workflow-skill-contracts.md)
  reconstructed post-hoc from the OpenSpec change bundle's proposal, design, and
  tasks artifacts, which `.gitignore` keeps out of the repository. Records the
  eight design decisions and their rejected alternatives behind the Explore-to-
  Ship prompt edits in `0d4d37b`, `61cce13`, `fcdd45a`, and `a35c802`; filed
  `done` because the graph already carries the shipped state.
- **Creation**: [IWE workflow skills](spec/iwe-workflow-skills.md) records the
  verified Explore, Plan, Implement, Verify, and Ship behavior as durable
  requirements and scenarios.
- **Update**:
  [Verification in the main loop](features/verification-in-the-main-loop.md)
  implemented and recorded in [unreleased](releases/unreleased.md).

## 2026-08-15

- **Update**: [Finish uv-run-only in CI](plans/20260815-uv-run-in-ci.md) done —
  all nine tasks verified green in CI (PR #61). CI stops activating the
  environment, syncs with `--locked` so lockfile drift fails at provisioning,
  and pins uv to the `actions/setup-python` interpreter; `python-lint-check.sh`
  no longer installs as a side effect of a check. Harvested from the parallel
  `no-venv-openspec` branch (PR #60); two of its changes declined with reasoning
  recorded.
- **Update**: [uv-run-only environment](features/uv-run-only-environment.md)
  extended to cover CI — the feature now spans both sides of the repository, so
  no spec changed: `data/spec/template-consumption.md` covers adapting the
  template into a consuming project, not this repository's CI provisioning
  contract.
- **Update**: [Drop the .venv symlink](plans/20260814-drop-venv-symlink.md) done
  — the in-tree symlink is gone and every consumer reaches the environment
  through `uv run` or the fixed `/uv/venvs/ws-project` path.
- **Creation**: [uv-run-only environment](features/uv-run-only-environment.md)
  implemented, recorded in [unreleased](releases/unreleased.md).
- **Creation**: Proposed
  [Verification in the main loop](features/verification-in-the-main-loop.md) —
  ship's step 1 names the verify skill without invoking it, so verification at
  ship time is discretionary rather than compelled.

## 2026-08-01

- **Initialization**: Created the project workspace — [product](product.md) as
  the foundation, with [plans](plans.md), [backlog](backlog.md),
  [milestones](milestone.md), and [someday](someday.md) for work, and
  [features](features.md), [bugs](bugs.md), and [releases](releases.md) for
  delivery.
- **Creation**: Seeded the reference side — [spec](spec.md),
  [codebase](codebase.md), [architecture](architecture.md), and
  [concept](concept.md) — with example documents showing the shape of each type.
