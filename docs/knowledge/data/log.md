# Project Update Log

The history of this workspace, newest first. The `ship` skill appends a dated
group on every release; any skill that creates or retires a document adds a line
to the current day's group.

## 2026-08-16

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
