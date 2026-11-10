# Proposal

## Why

Behavior is written down twice: once as requirements in
`docs/knowledge/data/spec/` and again as prose in `docs/knowledge/data/architecture/`.
`architecture/standalone-opencode-runtime` states readiness, latching, and
recovery rules in more detail than the spec it sits beside. When the two
disagree, nothing says which one is right. The repository is moving to OpenSpec,
and `openspec/specs/` is still empty. This is the point to make the OpenSpec
specs the only home of behavior, before a second copy is migrated alongside the
first.

## What Changes

- Every durable spec moves from `docs/knowledge/data/spec/<slug>.md` to
  `openspec/specs/<slug>/spec.md`, normalized to the OpenSpec format
  (`## Purpose`, `## Requirements`, `### Requirement:`, `#### Scenario:`).
- Every architecture document is split by kind:
  - behavior the code implements becomes requirements in the spec that owns it,
    or in a new spec when none does;
  - the decision in force and the alternatives it rejected become that spec's
    `## Rationale` section, which sits after `## Requirements`;
  - measurements and investigations become findings in a new
    `docs/knowledge/data/findings/` document type;
  - how-to procedures become guides under `docs/`.
- `docs/knowledge/data/spec/`, `docs/knowledge/data/architecture/`, their hubs,
  and their IWE schemas are removed. Every link and code comment that names them
  is repointed to the new location.
- **BREAKING** (agentdev catalog): IWE plans stop carrying spec impact, and
  Ship stops merging spec deltas. Spec changes go through OpenSpec changes, and
  archiving a change also updates the spec's `## Rationale`. The catalog's
  `iwe-*` agents and skills lose their spec steps. A consuming repository that
  relied on IWE spec handling must adopt OpenSpec for its specs.
- `scripts/check-anchors.py` scans `openspec/specs/` for line numbers and
  resolves the anchors in each spec. It stops resolving anchors in the removed
  architecture folder.

## Capabilities

### New Capabilities

- `project-knowledge`: where each kind of durable project knowledge lives —
  behavior in specs, rationale in a spec's `## Rationale`, findings in the
  knowledge graph, procedures in `docs/` — and how an archived change keeps a
  spec's rationale current.

### Modified Capabilities

These capabilities exist once the migration has brought their specs into
`openspec/specs/`; the deltas apply at archive.

- `iwe-workflow-skills`: Plan no longer records spec impact and Ship no longer
  synchronizes specs. Findings route to `data/findings/` rather than
  `data/architecture/`. The OKF-model requirement no longer forbids OpenSpec.
- `line-free-anchors`: the line-number gate also scans `openspec/specs/`, and
  the resolver checks anchors in specs, not in architecture documents.

The rest of the migration moves existing behavior without changing it and is
written straight into the main specs, as covered in design.md.

## Impact

- `docs/knowledge/data/`: the `spec/` and `architecture/` folders and their
  hubs are removed, a `findings/` folder and hub are added, and links are
  rewritten across plans, bugs, backlog, features, releases, and concept notes.
  `docs/knowledge/AGENTS.md`, `SCHEMA.md`, and `.iwe/schemas/` change to match.
- `openspec/specs/`: 32 migrated specs, plus new specs for behavior that only
  architecture documents describe today.
- `openspec/config.yaml`: rules for spec `## Rationale` and archive guidance.
- `AGENTS.md`: the comment rule that references a spec or architecture key.
- Code comments in workflows, scripts, Ansible, and `py_packages/` that cite
  `spec/<slug>` or `architecture/<slug>`.
- `scripts/check-anchors.py` and its tests.
- agentdev catalog: `iwe-planner`, `iwe-implementer`, `iwe-verifier`,
  `iwe-shipper`, `iwe-revision-evaluator`, `iwe-adversarial-reviewer`, and the
  `iwe-explore`, `iwe-audit`, and `iwe-setup` skills.
