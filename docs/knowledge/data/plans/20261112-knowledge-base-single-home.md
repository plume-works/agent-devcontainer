---
type: plan
created: 2026-11-12
release:
- features/single-home-knowledge
description: Give every kind of knowledge in the graph one home — behaviour and its rationale in specs, findings and guides in their own types, finished work in a per-release archive, release notes written from the spec diff — and fold the architecture notes, features, and closed history into that layout.
sources:
- resource: docs/knowledge/AGENTS.md
- resource: docs/knowledge/SCHEMA.md
- resource: .iwe/config.toml
- resource: .agents/plugins/agentdev/agents/iwe-shipper.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
---

# One home for each kind of knowledge

## Context

The graph states one behaviour in up to three document types, and only one of
them is kept current. Ship maintains `data/spec/`. Nothing maintains
`data/architecture/` or the `## Behaviour` of a feature after it is written, and
closed plans, bugs, and tasks hold rationale that exists nowhere else.

Measured on this checkout:

- `data/architecture/`: 69 notes, 51k words. They mix decisions, behaviour
  written as prose, findings, and procedures.
- `data/features/`: 637 behaviour statements, of which a spec already states
  387, no spec states 227, and a spec contradicts 23.
  `docs/knowledge/migration/scan/features.md` at commit `5265563a` lists them
  per feature.
- Closed plans, bugs, and tasks: `closed-0.md` to `closed-7.md` under
  `docs/knowledge/migration/scan/` at commit `5265563a` cover 202 of them, one
  section per document, and 103 hold knowledge found nowhere else.
- Release pages link features. The 2.1.0 page shows one feature added and five
  changed; comparing each requirement's text in `data/spec/` between the 2.0.0
  and 2.1.0 cuts shows 22 requirements added, 18 removed, and 33 modified across
  19 specs.

The user set the principles for the new layout: DRY and KISS. The user also
decided that the whole of `docs/knowledge/data/` is redesigned, so no rule in
`docs/knowledge/AGENTS.md`, `docs/knowledge/SCHEMA.md`, or an `iwe-*` rulebook
constrains it, and that this is one plan.

The feature is [One home for each kind of
knowledge](../features/single-home-knowledge.md). It changes what the workflow
skills of [agentdev IWE workflow
skills](../archive/1.0.0/features/agentdev-iwe-workflow-skills.md) write. It
absorbs two backlog tasks: [Remove redundancy from the durable
specs](../archive/3.0.0/backlog/deduplicate-spec-requirements.md) and [Give
architecture notes a
lifecycle](../archive/3.0.0/backlog/architecture-note-lifecycle.md).

## Approach

Each kind of knowledge has one home:

| Kind                          | Home                                   |
| ----------------------------- | -------------------------------------- |
| Behaviour                     | `data/spec/` requirements              |
| Why, and what was rejected    | `## Rationale` in the same spec        |
| Findings                      | `data/findings/`, a new `finding` type |
| Procedures                    | `data/guides/`, a new `guide` type     |
| Proposals                     | `data/features/`                       |
| Work in flight                | plans, bugs, tasks                     |
| What a release changed        | the release page, as text              |
| Finished or retired documents | `data/archive/`                        |

The `architecture` type is retired and the schemas reject it outside the
archive. A feature is a proposal: it is live at `stage: proposed` or
`stage: accepted`, and Ship archives it with the plan that implements it.

Finished work is archived, never deleted. `data/archive/` holds one folder per
release plus `next-release`, and each holds one subfolder per type, so every
archived document stays under its type's schema. Whoever closes a plan, bug,
task, or feature moves it to `data/archive/next-release/<type>/` with
`iwe rename` in the same change and removes its hub link. Before the move, Ship
writes the plan's lasting decision, and a closed bug's lasting root cause, into
the `## Rationale` of the spec that owns the behaviour. The release cut moves
the contents of `next-release` into the version's folder. The folder is the only
record of a document's release: the `released` field is removed. A document that
no plan closed belongs to the release that was open when it closed.

The release cut writes the release page from the specs. It diffs the
requirements and scenarios of `data/spec/` between the commit that added the
previous release page and the cut, and writes what changed in plain language,
grouped by theme, with no link. It appends the titles of the bugs in the
release's folder. It reads the release's archived plans only to settle what the
diff leaves unclear, and reports what stays unclear. Nothing edits the page
afterwards. `data/log.md` is removed; OKF makes it optional. A plan's `release`
field no longer feeds a page: it lists the feature and bug documents the plan
closes, or `internal` when it closes none.

The existing documents are migrated in this plan. Migration tasks edit specs
directly: they record behaviour the code already has, each statement checked
against the code first, and a statement the code contradicts is filed as a bug
through `/agentdev:iwe-capture` and not migrated. `## Spec changes` below
carries only the behaviour this plan changes. A release is cut under the current
rules before the migration starts, so the first spec diff after it holds the
migration alone.

The catalog's `iwe-bootstrap` assets scaffold the same layout the rulebooks
write, so they change with the rulebooks. A repository that already consumed the
old scaffold is migrated by a follow-up task this plan files.

Rejected:

- **Moving specs to OpenSpec.** OpenSpec keeps specs outside the graph and
  outside the plan and Ship flow (`origin/specs-over-arch`). The user chose to
  fix the graph in place.
- **`data/architecture/` kept for decisions only.** No script can check that a
  note states no behaviour, and no workflow step maintains a note.
- **Rationale only in the plan that made the decision.** The operating loop's
  Consult step reads specs, not closed plans, so rationale needs a home that
  step reads.
- **Minimal validation for archived documents.** The user chose full validation;
  a schema change is applied to that type's archived documents in the same
  change.
- **Release pages that link features.** A feature's text is written at proposal
  time, so a link to it names a change without saying what changed, and omits
  every change a plan declared `internal`.
- **An implemented feature whose `## Behaviour` links spec requirements.** It
  keeps a second document per behaviour for a release page that no longer reads
  it.

## Implementation Steps

### Task 1: A release is cut before the migration

- [x] A release page exists for every plan shipped before this plan's first
  commit, cut by `/agentdev:iwe-ship` under the rules in force before this plan.
  - **Closed by:** the user, by running the release cut and naming the version.
  - **Evidence:** `docs/knowledge/data/releases/3.0.0.md` and
    `docs/knowledge/data/releases/3.0.1.md`, the latter taking
    `data/plans/20261103-per-worktree-catalog`, its `released` field set to
    `3.0.1`.

### Task 2: Schemas and bindings for the new layout

**Files:** Create: `.iwe/schemas/finding.yaml`, `.iwe/schemas/guide.yaml`,
`docs/knowledge/data/findings.md`, `docs/knowledge/data/guides.md`,
`docs/knowledge/tests/test_archive_layout.py`. Modify: `.iwe/config.toml`,
`.iwe/schemas/okf.yaml`, `.iwe/schemas/release.yaml`,
`docs/knowledge/data/index.md`,
`docs/knowledge/tests/test_reserved_file_shapes.py`. Delete:
`.iwe/schemas/okf-log.yaml`, `docs/knowledge/data/log.md`.

- [x] `.iwe/config.toml` binds the plan, bug, task, and feature schemas to
  `data/archive/*/<type>/**` beside their live folders, and binds `finding` and
  `guide` to `data/findings/**` and `data/guides/**`, with both hubs in
  `[schemas.hub]` and in `data/index.md`. `iwe schema validate` passes.
  - **Evidence:**
    `uv run pytest docs/knowledge/tests/test_archive_layout.py::test_conforming_document_validates`
    and `iwe schema validate`; `.iwe/config.toml#schemas.hub`,
    `docs/knowledge/data/index.md#reference`.
- [x] A test in `test_archive_layout.py` runs `iwe schema validate` on a scratch
  graph under `/tmp` holding an archived plan with an invalid `stage` and
  expects a failure naming the document.
  - **Evidence:**
    `uv run pytest 'docs/knowledge/tests/test_archive_layout.py::test_broken_document_is_rejected[archived-plan-invalid-stage]'`
- [x] A finding requires `## Measurement` and `## Closing` and carries no
  `stage`; a guide requires an H1 and carries no `stage`. A test in
  `test_archive_layout.py` expects a failure for a finding without `## Closing`.
  - **Evidence:**
    `uv run pytest docs/knowledge/tests/test_archive_layout.py::test_broken_document_is_rejected`
    (finding without `## Closing`, finding with `stage`, guide with `stage`);
    `.iwe/schemas/finding.yaml`, `.iwe/schemas/guide.yaml`.
- [x] `data/log.md`, `.iwe/schemas/okf-log.yaml`, and the `okf-log` binding do
  not exist, `test_reserved_file_shapes.py` holds no log case, and
  `iwe schema validate` passes.
  - **Evidence:**
    `test ! -e docs/knowledge/data/log.md && test ! -e .iwe/schemas/okf-log.yaml && ! grep -q okf-log .iwe/config.toml`,
    `uv run pytest docs/knowledge/tests/test_reserved_file_shapes.py`, and
    `iwe schema validate`.

### Task 3: Scripts that find a plan by key

**Files:** Modify:
`.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py`,
`.agents/plugins/agentdev/skills/iwe-verify/agent-code/verify-cache.py`,
`.agents/plugins/agentdev/bin/plan_predecessors.py`, `scripts/check-anchors.py`,
and their tests under `.agents/plugins/agentdev/tests/` and `scripts/tests/`.

- [x] `iwe-branch-name.py plan-state` reports `done` for a plan that exists only
  under `data/archive/<release>/plans/`, with a test.
  - **Evidence:**
    `uv run pytest .agents/plugins/agentdev/tests/test_iwe_branch_name_plan_state.py::test_plan_state_reads_an_archived_plan`
- [x] `plan-state` reports `AMBIGUOUS_PLAN` when a live plan and an archived
  plan share a slug, with a test.
  - **Evidence:**
    `uv run pytest .agents/plugins/agentdev/tests/test_iwe_branch_name_plan_state.py::test_plan_state_refuses_a_slug_shared_with_the_archive`
- [x] `verify-cache.py` resolves an archived plan's key to its archive path,
  with a test.
  - **Evidence:**
    `uv run pytest .agents/plugins/agentdev/tests/test_verify_cache.py::test_archived_plan_keeps_its_archive_key`
- [x] `plan_predecessors.py` reads the stage of a `## Depends on` link that
  points into `data/archive/`, with a test.
  - **Evidence:**
    `uv run pytest .agents/plugins/agentdev/tests/test_plan_predecessors.py::test_an_archived_dependency_is_read_by_its_stage`
- [x] `scripts/check-anchors.py` resolves every anchor in a `data/guides/`
  document and none in `data/findings/`, `data/archive/`, or
  `data/architecture/`, with tests.
  - **Evidence:**
    `uv run pytest scripts/tests/test_check_anchors.py::test_live_documents_resolve_everywhere scripts/tests/test_check_anchors.py::test_out_of_scope_anchors_are_not_resolved`

### Task 4: The knowledge base's own documents

**Files:** Modify: `docs/knowledge/AGENTS.md`, `docs/knowledge/SCHEMA.md`,
`docs/knowledge/STRUCTURE.md`, `docs/knowledge/README.md`, `AGENTS.md`,
`docs/knowledge/data/product.md`.

- [x] `docs/knowledge/AGENTS.md` describes the homes in the `## Approach` table,
  the archive move at close, and the release cut from the spec diff, and names
  none of `data/architecture/`, `released`, and `data/log.md`.
  - **Evidence:** `docs/knowledge/AGENTS.md#conventions` › "Each kind of
    knowledge has one home" and `docs/knowledge/AGENTS.md#the-operating-loop`;
    `grep -nE 'data/architecture|data/log\.md|released:' docs/knowledge/AGENTS.md`
    prints nothing.
- [x] `docs/knowledge/SCHEMA.md` documents the `finding` and `guide` types, the
  archive folders, the feature as a proposal, the `release` field as the
  documents a plan closes, and the release page as text, and drops the
  architecture type, the `released` field, and `data/log.md`.
  - **Evidence:**
    `docs/knowledge/SCHEMA.md#the-archive--dataarchivereleasefolder`,
    `#reference-documents--type-only`, `#features--datafeaturesslugmd`,
    `#plans--dataplansyyyymmdd-slugmd`, and `#releases--datareleasesversionmd`.
- [x] `docs/knowledge/STRUCTURE.md` and `docs/knowledge/README.md` describe the
  same layout.
  - **Evidence:** `docs/knowledge/STRUCTURE.md#design-decisions` › "One home for
    each kind of knowledge" and › "Finished work is archived, not deleted";
    `docs/knowledge/README.md#whats-inside`.
- [x] `AGENTS.md#project-memory`, `AGENTS.md#comments`, and the investigation
  rule in `docs/knowledge/data/product.md#authoring-rules` send a decision to a
  spec's `## Rationale` and a finding to `data/findings/`.
  - **Evidence:** `AGENTS.md#project-memory` › "a decision in the `## Rationale`
    of the spec", `AGENTS.md#comments` › "the rationale and rejected
    alternatives in its `## Rationale`", and
    `docs/knowledge/data/product.md#authoring-rules` › "a measurement that
    settles nothing yet".

### Task 5: The workflow rulebooks

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`,
`iwe-shipper.agent.md`, `iwe-ship-reviewer.agent.md`, `iwe-verifier.agent.md`,
`iwe-implementer.agent.md` in the same folder, and
`.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`, `iwe-capture/SKILL.md`,
`iwe-setup/SKILL.md`, `iwe-audit/SKILL.md`, `iwe-ship/SKILL.md`,
`iwe-verify/SKILL.md`, `iwe-weekly/SKILL.md` in the skills folder; and
`scripts/check-ship-records.py` for the checklist.

- [x] `iwe-planner.agent.md#the-three-forms-of-spec-changes` says a plan names
  the `## Rationale` entries each touched spec gains.
  - **Evidence:**
    `.agents/plugins/agentdev/agents/iwe-planner.agent.md#the-three-forms-of-spec-changes`
    › "name the `## Rationale` entries that spec gains or rewrites".
- [x] `iwe-planner.agent.md#steps` defines `release` as the documents the plan
  closes, requires no feature for user-visible work, and has a plan that grew
  from a backlog task mark the task done and move it to the archive.
  - **Evidence:** `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps` ›
    "`release` lists the documents the plan closes", › "a plan whose work users
    see needs no feature", and › "`data/archive/next-release/backlog/`".
- [x] `iwe-shipper.agent.md#steps`: after the spec merge, Ship writes the
  `## Rationale` entries, sets the stages, and moves the plan and each feature
  and bug it closes to `data/archive/next-release/` with `iwe rename`, removing
  their hub links. Cancel moves the plan the same way.
  - **Evidence:** `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps` ›
    "Write the `## Rationale` entries", › "Archive what closed, last", and ›
    "Then archive the plan as step 6's last bullet does".
- [x] `iwe-shipper.agent.md#steps`: the release cut moves every document in
  `next-release` to `data/archive/<X.Y.Z>/`, writes the release page as
  `## Spec changes` below requires, and writes no `released` and no log.
  - **Evidence:** `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps` ›
    "Diff the requirements and scenarios of every spec" and › "Move every
    document under `data/archive/next-release/`";
    `grep -nE 'released:|log\.md' .agents/plugins/agentdev/agents/iwe-shipper.agent.md`
    prints nothing.
- [x] The `## Ship review` template in `iwe-ship-reviewer.agent.md` and the
  fixed structure in `scripts/check-ship-records.py` replace the "edited no hub"
  item with items for the archive move and the `## Rationale` entries, with the
  checker's tests updated. A `## Ship review` that carries the "edited no hub"
  item still passes, with a test, so the plans stamped before this change stay
  valid.
  - **Evidence:** `uv run pytest scripts/tests/test_check_ship_records.py`,
    including `::test_earlier_ship_review_passes` and
    `::test_na_on_a_mandatory_item_fails`;
    `.agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md#ship-mode`.
- [x] `iwe-explore/SKILL.md#capturing`, `iwe-implementer.agent.md`
  (`#capturing-what-implementation-turns-up`), and `iwe-setup/SKILL.md` route a
  decision to a spec's `## Rationale`, a finding to `data/findings/`, and a
  procedure to `data/guides/`.
  - **Evidence:**
    `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#capturing`,
    `.agents/plugins/agentdev/agents/iwe-implementer.agent.md#capturing-what-implementation-turns-up`,
    and `.agents/plugins/agentdev/skills/iwe-setup/SKILL.md#steps`, each naming
    `## Rationale`, `data/findings/`, and `data/guides/`.
- [x] `iwe-capture/SKILL.md` moves a bug filed at `stage: done`, and a task or
  bug it closes, to the archive.
  - **Evidence:** `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md#steps` ›
    "write it at `data/archive/next-release/bugs/<slug>.md` instead" and › "move
    it with `iwe rename` to".
- [x] No file under `.agents/plugins/agentdev/agents/` or
  `.agents/plugins/agentdev/skills/iwe-*/` outside `iwe-bootstrap/assets/` names
  `data/architecture`, `data/log.md`, or the `released` field.
  - **Evidence:**
    `git grep -nE 'data/architecture|data/log\.md|released:|released: \{' -- .agents/plugins/agentdev/agents ':(glob).agents/plugins/agentdev/skills/iwe-*/**' ':!.agents/plugins/agentdev/skills/iwe-bootstrap/assets'`
    prints nothing.
- [x] `uv run pytest .agents/plugins/agentdev/tests -k 'validate or catalog'`
  and the `validate_agent_files` pre-commit hook pass on the catalog.
  - **Evidence:**
    `uv run pytest .agents/plugins/agentdev/tests -k 'validate or catalog'` and
    `uv run validate_agent_files --recommend . --require-marketplace claude`.

### Task 6: The bootstrap scaffold

**Files:** Modify: `.agents/plugins/agentdev/skills/iwe-bootstrap/assets/` (its
`.iwe/`, `docs/knowledge/AGENTS.md`, `SCHEMA.md`, `STRUCTURE.md`, hubs, and
example documents),
`.agents/plugins/agentdev/skills/iwe-bootstrap/references/scaffold.md`,
`.agents/plugins/agentdev/tests/test_iwe_bootstrap.py`.

- [x] The scaffold installs the `finding` and `guide` types, the archive
  bindings, and no architecture hub or example and no `data/log.md`, and
  `uv run pytest .agents/plugins/agentdev/tests/test_iwe_bootstrap.py` passes.
  - **Evidence:**
    `uv run pytest .agents/plugins/agentdev/tests/test_iwe_bootstrap.py .agents/plugins/agentdev/tests/test_iwe_seed.py`,
    including
    `test_iwe_bootstrap.py::test_installed_graph_has_the_single_home_layout`.
- [x] `/agentdev:iwe-capture task` files a backlog task for migrating a
  repository that consumed the earlier scaffold.
  - **Evidence:** `docs/knowledge/data/backlog/migrate-earlier-iwe-scaffold.md`,
    linked from `docs/knowledge/data/backlog.md`.

### Task 7: Fold the architecture notes

For each note: check every behaviour statement against the code it anchors. A
statement the code confirms and no spec holds becomes a requirement with a
scenario in the destination spec. The decision in force and its rejected
alternatives go to that spec's `## Rationale`. A statement the code contradicts
is filed through `/agentdev:iwe-capture bug`. The note then moves to
`data/archive/<release>/architecture/` — the release whose plan wrote it, or
`next-release` — keeping `type: architecture`. Destinations are the table in
`origin/specs-over-arch:openspec/changes/specs-sole-source-of-truth/design.md`
(commit `19fbac9f`), with `openspec/specs/<slug>` read as `data/spec/<slug>`.
`per-worktree-catalog`, which that table does not list, goes to
`catalog-lifecycle`.

**Files:** Modify: `docs/knowledge/data/spec/*.md`,
`docs/knowledge/data/spec.md`, `.iwe/config.toml`, `.iwe/schemas/okf.yaml`,
`docs/knowledge/tests/test_archive_layout.py`. Create:
`docs/knowledge/data/findings/*.md`, `docs/knowledge/data/guides/*.md`, new
specs `catalog-scripts`, `cloud-session-host`, `devcontainer-state`,
`ci-workflows`, `pr-description`, `supported-harnesses`. Move:
`docs/knowledge/data/architecture/*.md`.

- [x] The notes destined for `ai-review-gate` are folded and archived.
  - **Evidence:** `docs/knowledge/data/spec/ai-review-gate.md#rationale`;
    `ls docs/knowledge/data/archive/*/architecture/{actions-approval-permission,ai-review-event-selection,dispatched-review-identity,label-review-triggers,pr-review-effort-tiers,pr-review-scenario-validation,pull-request-only-responder,responder-app-identity,assignee-review-trigger,pr-review-correctness-bar}.md`
    lists all ten.
- [x] The notes destined for `iwe-workflow-skills` are folded and archived.
  - **Evidence:** `docs/knowledge/data/spec/iwe-workflow-skills.md#rationale`;
    `ls docs/knowledge/data/archive/*/architecture/{adversarial-review,autonomous-implement-loop,explicit-only-workflow-agents,fresh-context-verify,iwe-cli-over-mcp,kb-conflict-free-layout}.md`
    lists all six.
- [x] The notes destined for `agentdev-runtime-images` are folded and archived.
  - **Evidence:**
    `docs/knowledge/data/spec/agentdev-runtime-images.md#rationale`;
    `ls docs/knowledge/data/archive/*/architecture/{agentdev-runtime-package,devcontainer-runtime,extra-ca-trust,no-launchpad-ppas,validator-image-install}.md`
    lists all five.
- [x] The notes destined for `dependency-updates` are folded and archived.
  - **Evidence:** `docs/knowledge/data/spec/dependency-updates.md#rationale`;
    `ls docs/knowledge/data/archive/*/architecture/{ansible-apt-pins,renovate-config-validation,renovate-post-upgrade}.md`
    lists all three.
- [x] The notes destined for `catalog-lifecycle` and the new
  `supported-harnesses` are folded and archived.
  - **Evidence:** `docs/knowledge/data/spec/catalog-lifecycle.md#rationale` and
    `docs/knowledge/data/spec/supported-harnesses.md#rationale`;
    `ls docs/knowledge/data/archive/*/architecture/{ci-agent-plugin-availability,no-code-graph,per-worktree-catalog,supported-harnesses}.md`
    lists all four.
- [x] The notes destined for `claude-remote-control` are folded and archived.
  - **Evidence:** `docs/knowledge/data/spec/claude-remote-control.md#rationale`;
    `ls docs/knowledge/data/archive/*/architecture/{claude-remote-control-resume,claude-remote-control-server-mode}.md`
    lists both; the `-server-continue` and `-spawn-mode-switch` notes, whose
    decisions are in that `## Rationale`, carry Measurement and Closing sections
    and are findings under `docs/knowledge/data/findings/`.
- [x] The notes with one destination each (`agent-file-discovery`,
  `plan-checkbox-evidence`, `pre-commit-gate`, `devcontainer-git-credentials`,
  `line-free-anchors`, `stacked-prs`, `devcontainer-docker-storage`,
  `devcontainer-opencode-policy`, `self-improve-learning-loop`) are folded and
  archived.
  - **Evidence:** each destination spec's `#rationale`;
    `ls docs/knowledge/data/archive/*/architecture/{agent-metadata-files,evidence-without-commit-ids,formatter-ownership,gh-authentication-shim,gh-wrapper-image-only,line-free-anchors,manual-stacked-prs,nested-docker-provisioning,opencode-full-access-in-devcontainer,self-improve-consolidation,self-improve-runtime}.md`
    lists all eleven.
- [x] The notes destined for `template-consumption`, `opencode-catalog-bridge`,
  `standalone-opencode-runtime`, and `nested-agent-dispatch` are folded and
  archived.
  - **Evidence:** each destination spec's `#rationale`;
    `ls docs/knowledge/data/archive/*/architecture/{module-layout,template-boundary,opencode-catalog-bridge,standalone-opencode-runtime,nested-subagent-dispatch}.md`
    lists all five; the nested-dispatch fixture is
    `docs/knowledge/data/guides/skill-rehearsal-runs.md#the-nested-dispatch-fixture`.
- [x] The notes that describe behaviour no spec owns are folded into the new
  specs `catalog-scripts`, `cloud-session-host`, `devcontainer-state`,
  `ci-workflows`, and `pr-description`, each linked from `data/spec.md`, and
  archived.
  - **Evidence:** `docs/knowledge/data/spec.md` links each of the five;
    `ls docs/knowledge/data/archive/*/architecture/{catalog-script-language,cloud-session-host-toolchain,agent-auth-persistence,uv-environment-location,devcontainer-home-volume,fork-pull-request-builds,self-repository-uses,pr-verification-sections}.md`
    lists all eight.
- [x] Every note whose sections are Measurement, Question, or Closing is a
  `data/findings/` document linked from `data/findings.md`.
  - **Evidence:** `docs/knowledge/data/findings.md` links the eleven documents
    under `docs/knowledge/data/findings/`, and `iwe schema validate` passes them
    against `.iwe/schemas/finding.yaml`.
- [x] `drqp-devcontainer-testing`, `sibling-devcontainer-testing`,
  `skill-rehearsal-runs`, and `worktree-hooks` are `data/guides/` documents
  linked from `data/guides.md`.
  - **Evidence:** `docs/knowledge/data/guides.md` links each of them, and
    `uv run scripts/check-anchors.py` resolves their anchors.
- [x] `docs/knowledge/data/architecture/` and
  `docs/knowledge/data/architecture.md` do not exist, and
  `.iwe/schemas/architecture.yaml` is bound only to
  `data/archive/*/architecture/**`.
  - **Evidence:**
    `test ! -e docs/knowledge/data/architecture && test ! -e docs/knowledge/data/architecture.md`;
    `.iwe/config.toml#schemas.architecture`.
- [x] `iwe schema validate` fails a document outside `data/archive/` whose
  frontmatter says `type: architecture`, a test in
  `docs/knowledge/tests/test_archive_layout.py` expects that failure, and
  `iwe schema validate` passes on the graph.
  - **Evidence:**
    `uv run pytest 'docs/knowledge/tests/test_archive_layout.py::test_broken_document_is_rejected[live-architecture-note]'`
    and `iwe schema validate`.
- [x] No frontmatter `sources` entry under `docs/knowledge/data/` outside
  `data/archive/` names a path under `data/architecture/`.
  - **Evidence:**
    `git grep -nE 'resource: (docs/knowledge/)?data/architecture/' -- docs/knowledge/data ':!docs/knowledge/data/archive'`
    prints nothing.
- [x] No code comment, workflow, or script outside `docs/knowledge/` cites
  `architecture/<slug>`:
  `git grep -nE 'architecture/[a-z0-9-]+' -- ':!docs/knowledge' ':!docs/research'`
  prints nothing.
  - **Evidence:**
    `git grep -nE 'architecture/[a-z0-9-]+' -- ':!docs/knowledge' ':!docs/research'`
    prints nothing.

### Task 8: Fold and archive the features

Input: `docs/knowledge/migration/scan/features.md` at commit `5265563a`. For
each implemented feature, each statement its row counts as unique and its
destination table keeps becomes a requirement or scenario in the destination
spec after a check against the code. Each conflict is resolved for the code: the
stale side is corrected, and a spec the code contradicts is corrected as a
recorded behaviour, not a change. Then the feature moves, unchanged, to
`data/archive/<release>/features/` — the first release whose page names it.

**Files:** Modify: `docs/knowledge/data/spec/*.md`,
`docs/knowledge/data/features.md`. Create: new specs `pr-review`,
`ci-python-environment`. Move: every `docs/knowledge/data/features/*.md` at
`stage: implemented` or `stage: deprecated`.

- [x] Every conflict listed under `## Conflicts` in `features.md` has its stale
  side corrected, or a bug filed through `/agentdev:iwe-capture bug` when the
  code is the wrong side.
  - **Evidence:** the two spec-side conflicts are corrected in
    `docs/knowledge/data/spec/opencode-web.md#requirement-opencode-logins-and-chats-survive-a-rebuild`
    and
    `docs/knowledge/data/spec/claude-remote-control.md#requirement-remote-control-autostarts-only-on-a-live-claudeai-login`
    › "`agentdev-runtime coder start`"; every other conflict's feature side is
    stale and the feature is archived unchanged, the code agreeing with the
    spec: `iwe-implementer.agent.md#running-the-loop`,
    `verify-cache.py::run_save`, `agent_state.py::unlink_claude_json`,
    `bootstrap.py::prepare_shared_auth`, `settings.py` › "AGENTDEV_VENV_ROOT",
    `iwe-branch-name.py::read_plan_state`, `supervisor.py` › "DEPLOY_SERVICES",
    `xpra.py` › "--tcp-auth=env:name=XPRA_PASSWORD",
    `.github/workflows/ci.yml#jobs.candidate-pre-commit`, and
    `.github/workflows/renovate.yml#jobs.renovate.container.image`. No bug was
    needed.
- [x] `data/spec/opencode-web.md` and `data/spec/catalog-lifecycle.md` agree on
  where OpenCode's data lives, matching `.devcontainer/docker-compose.yml`.
  - **Evidence:**
    `docs/knowledge/data/spec/opencode-web.md#requirement-opencode-logins-and-chats-survive-a-rebuild`
    and
    `docs/knowledge/data/spec/catalog-lifecycle.md#requirement-only-agent-credentials-are-shared-across-worktrees`
    both place `~/.local/share/opencode` on the per-instance home volume;
    `git grep -nE 'agentdev-opencode([^-]|$)' -- .devcontainer docker` prints
    nothing.
- [x] The unique statements of every implemented feature whose owning spec is
  `iwe-workflow-skills`, `plan-checkbox-evidence`, `git-new-branch`,
  `iwe-branch-name`, `stacked-prs`, `update-branch`, or `pr-merge-conflicts` are
  in that spec.
  - **Evidence:**
    `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-the-iwe-workflow-skills-ship-in-the-agentdev-catalog`,
    `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-the-durable-knowledge-audit-reads-from-a-fresh-context-and-changes-nothing`,
    `docs/knowledge/data/spec/update-branch.md#requirement-update-branch-brings-in-the-branchs-upstream-before-the-base`,
    and
    `docs/knowledge/data/spec/stacked-prs.md#requirement-pr-merge-stack-merges-a-chain-bottom-up`
    › "retargeted"; the other features' statements were already stated.
- [x] The unique statements of every implemented feature whose owning spec is
  `ai-review-gate`, `template-consumption`, `pre-commit-gate`,
  `dependency-updates`, or `image-pinning` are in that spec, with the new
  `pr-review` and `ci-python-environment` specs linked from `data/spec.md`.
  - **Evidence:**
    `docs/knowledge/data/spec/ai-review-gate.md#requirement-the-review-job-reviews-with-the-pr-review-skill-as-a-submitted-review`,
    `docs/knowledge/data/spec/pre-commit-gate.md#requirement-javascript-runs-through-bun`,
    `docs/knowledge/data/spec/pre-commit-gate.md#requirement-every-commit-path-runs-the-hooks-merges-included`,
    `docs/knowledge/data/spec/dependency-updates.md#requirement-renovate-runs-self-hosted-in-the-development-image`,
    `docs/knowledge/data/spec/pr-review.md#requirement-docs-and-skills-get-a-durable-knowledge-pass`,
    `docs/knowledge/data/spec/ci-python-environment.md#requirement-one-action-provisions-the-environment-and-activates-nothing`;
    `docs/knowledge/data/spec.md` links `spec/pr-review.md` and
    `spec/ci-python-environment.md`.
- [x] The unique statements of every other implemented feature are in their
  destination spec.
  - **Evidence:**
    `docs/knowledge/data/spec/catalog-lifecycle.md#requirement-registering-a-catalog-root-replaces-earlier-registrations`,
    `docs/knowledge/data/spec/agentdev-runtime-images.md#requirement-uv-and-pre-commit-state-lives-on-the-home-volume`,
    `docs/knowledge/data/spec/standalone-opencode-runtime.md#requirement-the-compose-deployment-owns-per-project-volumes-and-one-shared-auth-volume`,
    `docs/knowledge/data/spec/agent-file-discovery.md#requirement-an-explicit-file-path-bypasses-the-walk`,
    `docs/knowledge/data/spec/self-improve-learning-loop.md#requirement-the-root-makefile-runs-the-plugins-checks`,
    `docs/knowledge/data/spec/cloud-session-host.md#requirement-the-cloud-instructions-describe-the-host-toolchain`,
    and
    `docs/knowledge/data/spec/catalog-scripts.md#requirement-the-python-lint-check-finds-ruff-without-installing-anything`.
- [x] Every feature at `stage: implemented` or `stage: deprecated` is under
  `data/archive/`, and `data/features.md` links only features at
  `stage: proposed` or `stage: accepted`.
  - **Evidence:**
    `iwe find --filter '{type: feature, stage: {$nin: [proposed, accepted]}}' -f keys`
    prints only keys under `data/archive/`, and
    `docs/knowledge/data/features.md` links only
    `features/single-home-knowledge.md`, at `stage: accepted`.

### Task 9: Distil and archive the closed history

Input: `closed-0.md` to `closed-7.md` under `docs/knowledge/migration/scan/` at
commit `5265563a`. For each document with the verdict `HAS UNIQUE KNOWLEDGE`,
each listed item is checked against the code and then written to its owning spec
— a `behaviour` item as a requirement or scenario, every other kind in
`## Rationale` — or is struck in the scan file with the reason it is dropped. A
constraint that is about tests goes to `AGENTS.md#tests`. A conflict the scan
lists is handled as in Task 8.

**Files:** Modify: `docs/knowledge/data/spec/*.md`, `AGENTS.md`,
`docs/knowledge/data/releases/*.md`, `docs/knowledge/data/plans.md`,
`docs/knowledge/data/bugs.md`, `docs/knowledge/data/backlog.md`,
`.iwe/schemas/plan.yaml`, `docs/knowledge/tests/test_archive_layout.py`. Move:
every closed document under `docs/knowledge/data/plans/`, `bugs/`, and
`backlog/`. Delete: `docs/knowledge/tests/test_released_stamp.py`.

- [x] Every item in `closed-0.md` is in a spec or struck with a reason.
  - **Evidence:** every item of `docs/knowledge/migration/scan/closed-0.md`
    under a `HAS UNIQUE KNOWLEDGE` verdict ends in `written: <spec>#<anchor>` or
    `struck: <reason>` until Task 12 removes the file, for example
    `docs/knowledge/data/spec/plan-checkbox-evidence.md#honest-ticks-come-from-the-artifacts-shape-not-more-prose-rules`.
- [x] Every item in `closed-1.md` is in a spec or struck with a reason.
  - **Evidence:** every item of `docs/knowledge/migration/scan/closed-1.md`
    under a `HAS UNIQUE KNOWLEDGE` verdict ends in `written: <spec>#<anchor>` or
    `struck: <reason>` until Task 12 removes the file, for example
    `docs/knowledge/data/spec/template-consumption.md#pr-description-guidance-is-a-separate-instruction-file`.
- [x] Every item in `closed-2.md` is in a spec or struck with a reason.
  - **Evidence:** every item of `docs/knowledge/migration/scan/closed-2.md`
    under a `HAS UNIQUE KNOWLEDGE` verdict ends in `written: <spec>#<anchor>` or
    `struck: <reason>` until Task 12 removes the file, for example
    `docs/knowledge/data/spec/pr-review.md#requirement-a-batch-of-passes-runs-as-foreground-calls`.
- [x] Every item in `closed-3.md` is in a spec or struck with a reason.
  - **Evidence:** every item of `docs/knowledge/migration/scan/closed-3.md`
    under a `HAS UNIQUE KNOWLEDGE` verdict ends in `written: <spec>#<anchor>` or
    `struck: <reason>` until Task 12 removes the file, for example
    `docs/knowledge/data/spec/opencode-web.md#rationale`.
- [x] Every item in `closed-4.md` is in a spec or struck with a reason.
  - **Evidence:** every item of `docs/knowledge/migration/scan/closed-4.md`
    under a `HAS UNIQUE KNOWLEDGE` verdict ends in `written: <spec>#<anchor>` or
    `struck: <reason>` until Task 12 removes the file, for example
    `docs/knowledge/data/spec/iwe-branch-name.md#one-iteration-counter-per-plan-under-one-prefix`.
- [x] Every item in `closed-5.md` is in a spec or struck with a reason.
  - **Evidence:** every item of `docs/knowledge/migration/scan/closed-5.md`
    under a `HAS UNIQUE KNOWLEDGE` verdict ends in `written: <spec>#<anchor>` or
    `struck: <reason>` until Task 12 removes the file, for example
    `docs/knowledge/data/spec/template-consumption.md#the-graph-keeps-no-codebase-map`.
- [x] Every item in `closed-6.md` is in a spec or struck with a reason.
  - **Evidence:** every item of `docs/knowledge/migration/scan/closed-6.md`
    under a `HAS UNIQUE KNOWLEDGE` verdict ends in `written: <spec>#<anchor>` or
    `struck: <reason>` until Task 12 removes the file, for example
    `docs/knowledge/data/spec/ai-review-refresh.md#only-the-ai-reviewers-own-change-request-forces-a-re-review`.
- [x] Every item in `closed-7.md` is in a spec or struck with a reason.
  - **Evidence:** every item of `docs/knowledge/migration/scan/closed-7.md`
    under a `HAS UNIQUE KNOWLEDGE` verdict ends in `written: <spec>#<anchor>` or
    `struck: <reason>` until Task 12 removes the file, for example
    `docs/knowledge/data/spec/ci-workflows.md#requirement-a-push-to-the-base-branch-filters-paths-from-the-last-passing-run`.
- [x] Every plan, bug, and task that is closed and has no section in
  `closed-0.md` to `closed-7.md` is read the same way, and each durable item it
  alone holds is in a spec.
  - **Evidence:** the six (`plans/20261103-per-worktree-catalog`,
    `-plan-review-skill`, `-shipper-dispatches-verifier`,
    `plans/20261104-main-ci-cooldown`, `backlog/architecture-note-lifecycle`,
    `backlog/deduplicate-spec-requirements`) were read; their items are in
    `docs/knowledge/data/spec/catalog-lifecycle.md#requirement-each-claude-worktree-of-a-catalog-checkout-loads-its-own-catalog`
    › "cannot be read",
    `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-plan-review-runs-both-reviewers-from-fresh-contexts-and-changes-nothing`,
    `docs/knowledge/data/spec/image-pinning.md#pushes-to-main-build-after-a-cancellable-cooldown`,
    and
    `docs/knowledge/data/spec/pre-commit-gate.md#a-push-to-main-is-checked-from-the-last-passing-run`;
    the two backlog tasks are carried by this plan.
- [x] `data/spec/iwe-workflow-skills.md` states where Ship reads a dependency's
  stage, and no spec contradicts it.
  - **Evidence:**
    `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-ship-waits-for-every-dependency`
    › "through `/agentdev:iwe-branch-name plan-state`";
    `grep -rn 'default branch' docs/knowledge/data/spec/` finds no statement
    that Ship reads a dependency there.
- [x] A `## Rationale` entry in `data/spec/template-consumption.md` records why
  the codebase map was retired.
  - **Evidence:**
    `docs/knowledge/data/spec/template-consumption.md#the-graph-keeps-no-codebase-map`.
- [x] Every done plan carrying `released` is under
  `data/archive/<that version>/plans/` with `released` removed.
  - **Evidence:** `iwe find --filter '{released: {$exists: true}}' -f keys`
    prints nothing, and `ls docs/knowledge/data/archive/*/plans/` lists the 122
    plans that carried it, each under its version's folder.
- [x] `.iwe/schemas/plan.yaml` rejects `released`, a test in
  `test_archive_layout.py` expects a failure for a plan carrying it,
  `test_released_stamp.py` is deleted, and `iwe schema validate` passes.
  - **Evidence:**
    `uv run pytest 'docs/knowledge/tests/test_archive_layout.py::test_broken_document_is_rejected[plan-carrying-released]'`,
    `test ! -e docs/knowledge/tests/test_released_stamp.py`, and
    `iwe schema validate`.
- [x] Every done plan without `released`, and every cancelled plan, is under
  `data/archive/next-release/plans/` or the folder of the release open when it
  closed.
  - **Evidence:**
    `iwe find --filter '{type: plan, stage: {$in: [done, cancelled]}}' -f keys`
    prints only keys under `data/archive/<release>/plans/`, each in the folder
    of the first release cut after the commit that closed it.
- [x] Every closed bug and task is in the archive folder of the plan that closed
  it, or of the release open when it closed.
  - **Evidence:**
    `iwe find --filter '{type: {$in: [bug, task]}, stage: {$in: [done, cancelled]}}' -f keys`
    prints only keys under `data/archive/`; a bug a plan's `release` lists sits
    in that plan's folder.
- [x] `data/plans.md`, `data/bugs.md`, and `data/backlog.md` link only open
  documents.
  - **Evidence:**
    `grep -c '](archive' docs/knowledge/data/plans.md docs/knowledge/data/bugs.md docs/knowledge/data/backlog.md`
    prints 0 for each, and their link counts equal the open-document queries: 1
    active plan, 6 open bugs, 19 pending tasks.
- [x] On every existing release page, each link is replaced by its link text.
  - **Evidence:** `grep -c '](' docs/knowledge/data/releases/*.md` prints 0 for
    every page.

### Task 10: The archive placement and release page checks

The checks land once Tasks 8 and 9 have moved every document they would fail.

**Files:** Modify: `scripts/check-ship-records.py`,
`scripts/tests/test_check_ship_records.py`, `.pre-commit-config.yaml`.

- [x] `scripts/check-ship-records.py` fails a plan, bug, or task at
  `stage: done` or `stage: cancelled` that is outside `data/archive/`, with a
  test.
  - **Evidence:**
    `uv run pytest scripts/tests/test_check_ship_records.py::test_closed_item_outside_the_archive_fails`.
- [x] It fails a plan without `stage`, or a bug or task at an open stage, that
  is inside `data/archive/`, with a test.
  - **Evidence:**
    `uv run pytest scripts/tests/test_check_ship_records.py::test_open_item_inside_the_archive_fails`.
- [x] It fails a feature outside `data/archive/` at any stage but `proposed` or
  `accepted`, and a feature inside it at either of those, with a test.
  - **Evidence:**
    `uv run pytest scripts/tests/test_check_ship_records.py::test_feature_placement_follows_its_stage`.
- [x] It fails a release page that holds a Markdown link, with a test.
  - **Evidence:**
    `uv run pytest scripts/tests/test_check_ship_records.py::test_release_page_with_a_link_fails_naming_the_line`.
- [x] The `ship-records` hook's `files` pattern covers `data/backlog/`,
  `data/features/`, `data/releases/`, and `data/archive/`.
  - **Evidence:** `.pre-commit-config.yaml#repos` ›
    "(archive|backlog|bugs|features|plans|releases)".
- [x] `uv run scripts/check-ship-records.py` over every document under
  `docs/knowledge/data/` passes.
  - **Evidence:**
    `uv run scripts/check-ship-records.py $(find docs/knowledge/data -name '*.md')`
    exits 0.

### Task 11: One home for each rule inside a spec

**Files:** Modify: `docs/knowledge/data/spec/*.md`.

- [x] In every spec, a rule stated in more than one requirement is stated in one
  and referenced from the others, and a scenario that only restates its
  requirement is removed. `/agentdev:semantic-refactor-audit` reports every
  behaviour the specs stated before the task has exactly one home after it.
  - **Evidence:** `git diff 85e8c2eb -- docs/knowledge/data/spec` removes 150
    restating scenarios and merges duplicate rules in ai-review-gate,
    devcontainer-docker-storage, plan-checkbox-evidence,
    self-improve-learning-loop, stacked-prs, standalone-opencode-runtime, and
    template-consumption; every requirement title, `## Rationale` section, and
    frontmatter is unchanged, and the requirement count stays 261. The audit
    judged every hunk of that diff against the spec text before it, and each
    scenario or sentence it found carrying a case nothing else states was
    restored.

### Task 12: Remove the migration inputs

**Files:** Delete: `docs/knowledge/migration/`.

- [x] `docs/knowledge/migration/` does not exist.
  - **Evidence:** `test ! -e docs/knowledge/migration` exits 0. The scan files
    the Task 8 and Task 9 evidence names stay readable at commit `5265563a`.

## Spec changes

[IWE workflow skills](../spec/iwe-workflow-skills.md):

``` markdown
## ADDED Requirements

### Requirement: Each kind of knowledge has one home

The graph SHALL hold behaviour only in `data/spec/` requirements, the decision
in force and the alternatives it rejected only in the `## Rationale` section of
the spec that owns the behaviour, a finding only in `data/findings/`, and a
procedure only in `data/guides/`. The schemas SHALL reject a document of type
`architecture` outside `data/archive/`. A feature SHALL be a proposal: outside
`data/archive/` its `stage` is `proposed` or `accepted`, and the `ship-records`
check SHALL fail any other. Nothing checks mechanically that a `## Rationale`
states no behaviour; the Durable Knowledge Auditor and review judge it.

#### Scenario: An architecture note is written

- **WHEN** a document outside `data/archive/` carries `type: architecture`
- **THEN** `iwe schema validate` fails and names the document

#### Scenario: An implemented feature is left in place

- **WHEN** a feature under `data/features/` is at `stage: implemented`
- **THEN** the `ship-records` check fails and names the document

### Requirement: Closed work is distilled and archived by release

Whoever sets a plan, bug, or backlog task to `stage: done` or
`stage: cancelled`, or a feature to `stage: implemented` or `stage: cancelled`,
SHALL, in the same change, move it with `iwe rename` to
`data/archive/next-release/<type>/` and remove its hub link. Before Ship moves
a plan, it SHALL write the plan's decision in force and its rejected
alternatives, and each closed bug's lasting root cause, into the `## Rationale`
of the spec that owns the behaviour. The release cut SHALL move every document
under `data/archive/next-release/` to `data/archive/<X.Y.Z>/`, keeping the type
subfolders. The folder SHALL be the only record of a document's release: no
document SHALL carry `released`. Every archived document SHALL pass the schema
of its type. The `ship-records` check SHALL fail a closed document outside
`data/archive/` and an open one inside it.

#### Scenario: A plan ships

- **WHEN** Ship marks a plan done
- **THEN** the plan and each feature and bug it closed are under
  `data/archive/next-release/`, no hub links them, and every link to them
  resolves

#### Scenario: A plan made a decision

- **WHEN** Ship ships a plan whose `## Approach` records a decision and a
  rejected alternative for behaviour a spec owns
- **THEN** that spec's `## Rationale` states the decision and the rejected
  alternative before the plan is moved

#### Scenario: A release is cut

- **WHEN** Ship cuts release `X.Y.Z`
- **THEN** every document that was under `data/archive/next-release/` is under
  `data/archive/X.Y.Z/`

#### Scenario: A closed document is left in place

- **WHEN** a commit stages a plan, bug, or task at `stage: done` or
  `stage: cancelled` outside `data/archive/`
- **THEN** the `ship-records` check fails and names the document

#### Scenario: An archived document breaks its schema

- **WHEN** an archived plan carries a `stage` its schema does not allow
- **THEN** `iwe schema validate` fails and names the document

### Requirement: Release notes are written from the spec diff

The release cut SHALL write the release page from the difference in the
requirements and scenarios of `data/spec/` between the commit that added the
previous release page and the cut, ignoring `## Rationale`. The page SHALL say
in plain language what changed, grouped by theme, with a Removed section for
behaviour that went away, an Upgrade notes section when a change requires
action, and a Fixed section listing the titles of the bugs in the release's
folder. The page SHALL hold no Markdown link, and the `ship-records` check SHALL
fail one that does. The cut SHALL read the release's archived plans only to
settle what the diff leaves unclear, and SHALL report each change it could not
settle and leave it off the page. No skill SHALL edit a release page after its
cut; nothing checks that mechanically. The graph SHALL hold no `data/log.md`.

#### Scenario: A requirement changed between cuts

- **WHEN** a requirement's statement or a scenario differs between the previous
  cut and this one
- **THEN** the release page says what changed in it, not only that it changed

#### Scenario: A requirement left a spec

- **WHEN** a requirement present at the previous cut is absent at this one and
  an archived plan of the release retired the behaviour
- **THEN** the release page lists the behaviour under Removed

#### Scenario: The diff does not say why

- **WHEN** a requirement left a spec and no archived plan of the release says
  whether the behaviour was retired or moved
- **THEN** the cut reports the requirement and leaves it off the page

#### Scenario: Only rationale changed

- **WHEN** the only difference in a spec between the cuts is under
  `## Rationale`
- **THEN** the release page does not mention the spec

#### Scenario: A release page links a document

- **WHEN** a commit stages a release page holding a Markdown link
- **THEN** the `ship-records` check fails and names the line

## MODIFIED Requirements

### Requirement: Plans declare their release impact

The plan schema SHALL require every active plan to carry a `release` frontmatter
value: `internal`, or a non-empty list of the `features/` and `bugs/` keys the
work closes. The Plan skill SHALL set that value when it files a plan, SHALL
declare `internal` when the work closes no feature and no bug, SHALL set every
feature the plan lists to `stage: accepted`, and SHALL set every bug the plan
lists to `stage: planned`. A plan revision that adds a bug to `release` SHALL
set it to `stage: planned`, and one that removes a bug SHALL return it to
`stage: pending`. Ship SHALL take the documents a plan closes only from that
value, SHALL never create a feature, SHALL write the `## Fix` of each bug it
marks done, and SHALL return each listed bug to `stage: pending` when it cancels
the plan.

#### Scenario: A plan implements a proposed feature

- **WHEN** Plan files a plan whose `release` lists a feature at
  `stage: proposed`
- **THEN** Plan sets the feature to `stage: accepted`

#### Scenario: A milestone aggregator plan is filed

- **WHEN** Plan files a milestone aggregator plan whose children are plans
- **THEN** the aggregator declares `release: internal`, and each child plan
  lists the features and bugs it closes

#### Scenario: A plan closes no document

- **WHEN** Ship ships a plan that declares `release: internal`
- **THEN** Ship marks the plan done and closes no feature or bug

#### Scenario: A plan declares features and bugs

- **WHEN** Ship ships a plan whose `release` lists feature and bug keys
- **THEN** Ship marks each feature implemented and each bug done, and writes
  each bug's `## Fix` describing the shipped fix and linking the plan

#### Scenario: A plan listing bugs is cancelled

- **WHEN** Ship cancels a plan whose `release` lists a bug at `stage: planned`
- **THEN** Ship sets the bug to `stage: pending` and writes no `## Fix`

#### Scenario: An active plan has no release declaration

- **WHEN** an active plan lacks `release`, or its value is neither `internal`
  nor a list of `features/` and `bugs/` keys
- **THEN** `iwe schema validate` fails and names the plan, and Ship returns a
  blocker report for Plan revise mode without a lifecycle transition

#### Scenario: A declared document does not exist

- **WHEN** a plan's `release` lists a key with no document behind it
- **THEN** Ship returns a blocker report for Plan revise mode without a
  lifecycle transition and creates no document

#### Scenario: A shipped plan predates the field

- **WHEN** a plan at `stage: done` or `stage: cancelled` has no `release`
- **THEN** `iwe schema validate` accepts it

### Requirement: Plans record intent, not the path taken to it

Plan documents SHALL record what is settled rather than the sequence of attempts
that settled it. `## Verification results` SHALL be a plan's only narrative
section. Implement SHALL route a finding that does not change the plan's intent
to its own document — `data/findings/`, `data/bugs/`, or `data/backlog/` —
rather than into the plan's `## Context` or `## Approach`, which state intent
and remain the Plan skill's to own. Every edit to a plan's intent sections SHALL
be reviewed through `/agentdev:iwe-plan-review` before the edit is validated:
audited for durable-knowledge residue by a reviewer holding no context beyond
the audit scope and the plan file, and checked by `iwe-ship-reviewer` in plan
mode for what Ship will need.

#### Scenario: Implementation produces a durable finding

- **WHEN** implementation establishes a constraint, root cause, or rejected
  alternative that the plan did not anticipate
- **THEN** Implement records it in the reference document that owns the area and
  reports the capture, leaving the plan's intent sections unchanged

#### Scenario: A session narrates its attempts into a plan

- **WHEN** a plan would gain a running account of an in-flight investigation —
  failed attempts, CI run identifiers, per-attempt tables
- **THEN** that content is excluded from the plan, because it would not be true
  had the work succeeded the first time

#### Scenario: A finding changes the plan's intent

- **WHEN** a finding alters scope, observable behavior, compatibility,
  acceptance criteria, dependencies, or an out-of-scope boundary
- **THEN** it goes back through the Plan skill's revise mode rather than being
  captured elsewhere or written into the plan directly

#### Scenario: A plan edit is audited before validation

- **WHEN** Plan creates or revises a plan and reaches validation
- **THEN** a reviewer holding only the audit scope and the plan file audits its
  intent sections for durable-knowledge residue, its verdicts are applied, and
  the narrative-sanctioned `## Verification results` and `- **Evidence:**`
  children are left out of that audit

#### Scenario: A plan edit is checked for what Ship needs

- **WHEN** Plan creates or revises a plan and reaches validation
- **THEN** `iwe-ship-reviewer` in plan mode reports whether the plan gives Ship
  what it needs, and Plan resolves each finding before validating

### Requirement: Ship synchronizes durable specs by intelligent merge

The Ship skill SHALL treat a plan-local spec delta as reviewed intent, SHALL
derive durable updates only from intent that agrees with verified shipped
behavior, SHALL preserve unaffected requirements, scenarios, and `## Rationale`
entries, SHALL complete and verify all required spec updates before marking
work done, and SHALL be safe to resume after a partial prior attempt.

#### Scenario: Existing behavior remains unaffected

- **WHEN** a shipped change modifies one requirement or scenario in an existing
  durable spec
- **THEN** Ship updates the changed behavior while preserving all unaffected
  requirements, scenarios, ordering, and `## Rationale` entries

#### Scenario: A decision is overturned

- **WHEN** a shipped plan replaces a decision a spec's `## Rationale` records
- **THEN** Ship rewrites that entry to state the new decision and lists the old
  one among its rejected alternatives

#### Scenario: Plan intent and implementation disagree

- **WHEN** a normative outcome or structured delta disagrees with the verified
  implementation
- **THEN** Ship makes no lifecycle transition, does not rewrite intent from
  code, and reports that the plan requires revision

#### Scenario: A spec update cannot be validated

- **WHEN** any planned spec update is incomplete, disagrees with the verified
  implementation, or fails graph validation
- **THEN** Ship does not mark the plan or related feature or bug complete and
  reports the mismatch

#### Scenario: Shipping resumes after partial graph updates

- **WHEN** a prior Ship attempt already performed some valid state changes
- **THEN** Ship inspects current state, preserves completed valid work, avoids
  duplicate `## Rationale` entries, archive moves, and release pages,
  and continues from the first incomplete operation

#### Scenario: A durable spec is retired

- **WHEN** the verified implementation and plan explicitly remove the final
  behavior represented by a durable spec
- **THEN** Ship uses IWE's graph-aware deletion operation, repairs references,
  and does not leave an empty or orphaned spec document

### Requirement: Workflow improvements preserve the IWE and OKF model

The strengthened skills SHALL continue to use IWE's single-plan-document
workflow, graph links, durable specs, existing stage conventions, `sources`
attribution, and schema validation. Risk-scaled spec deltas SHALL remain
embedded planning content without introducing OpenSpec change bundles, stores,
separate delta files, or a claimed programmatic delta application engine. The
graph SHALL remain a conformant OKF v0.2 bundle — `data/index.md` lists the
hubs, and the `okf` and `okf-index` schemas check every document — and SHALL
diverge from OKF only where OKF costs merges or upkeep. No document under
`data/` SHALL set OKF's optional `status`, because `stage` is the lifecycle
field, nor OKF's `generated` or `verified`, because source control records when
and by whom a document changed. The `banned-frontmatter-keys` pre-commit check
SHALL reject a document that sets any of them.

#### Scenario: Updated skills write project memory

- **WHEN** an updated skill creates or meaningfully changes an IWE document
- **THEN** it follows the existing OKF metadata, graph membership,
  normalization, validation, and commit requirements defined by the workspace

#### Scenario: A document sets a banned frontmatter key

- **WHEN** a document under `data/` carries `status`, `generated`, or `verified`
- **THEN** the `banned-frontmatter-keys` check fails and names the document and
  the key

#### Scenario: The index loses its OKF shape

- **WHEN** `data/index.md` departs from the shape its OKF schema defines
- **THEN** `iwe schema validate` fails and names the file

### Requirement: Capture files complete inbox documents

The Capture skill SHALL be the only writer of new bug, proposed-feature, and
backlog-task documents, SHALL refuse a document missing any frontmatter field or
body section `SCHEMA.md` requires for its type, SHALL check the graph for a
likely duplicate before filing, SHALL file a feature at `stage: proposed` and
never promote it, SHALL file a bug at `stage: pending` — or at `stage: done`
with its `## Fix`, under `data/archive/next-release/bugs/`, when the same change
fixed it — and a task at `stage: pending`, and SHALL link every filed document
except a bug filed at `stage: done` from its hub and end with `iwe normalize`
and `iwe schema validate` passing. Capture SHALL file no bug whose Reproduction
or Root cause is a bare "unknown": a section not yet known states what is known,
the hypotheses eliminated and what eliminated each, and links the backlog task
whose spike settles it. No bug section SHALL state lifecycle, which `stage`
alone carries, and a bug's `severity` SHALL measure impact, not urgency, and
set nothing, `rank` included.

#### Scenario: A bug's root cause is not yet known

- **WHEN** Capture is invoked for a bug whose Root cause reads only "unknown"
- **THEN** Capture writes nothing and asks for what is known, the hypotheses
  eliminated, and the backlog task whose spike settles it

#### Scenario: A complete item is captured

- **WHEN** Capture is invoked for a bug, feature, or task whose required
  sections and fields are all supplied, and no likely duplicate exists
- **THEN** Capture writes the document at its lane's key with the `stage`
  `SCHEMA.md` derives for it, stamps `sources`, links it from its hub at its
  sorted position unless it is a bug filed at `stage: done`, and validates the
  graph

#### Scenario: A required section is missing

- **WHEN** the supplied content lacks any section or field required for its
  type, including a bug's `severity`
- **THEN** Capture writes nothing and lists every missing section and field

#### Scenario: A likely duplicate exists

- **WHEN** a fuzzy or lexical search finds an existing document that matches the
  item
- **THEN** Capture writes nothing and shows the match

#### Scenario: A someday idea is promoted

- **WHEN** Capture is invoked for a task with `--from someday/<slug>`
- **THEN** Capture files the backlog task from the idea and moves the idea's
  link out of `data/someday.md`

#### Scenario: The item grew from a GitHub issue

- **WHEN** the exploration behind the item started from a GitHub issue
- **THEN** Capture records the issue under `sources:`, and after validation
  closes it with a comment naming the captured document

#### Scenario: Explore or Implement finds an inbox item

- **WHEN** Explore settles a defect, feature, or task, or Implement finds a
  defect or work its plan should not absorb
- **THEN** it hands the item to Capture rather than writing the document itself

### Requirement: Every ship is reviewed against Ship's obligations

`iwe-shipper` SHALL NOT commit a ship while a bug its plan's `release` lists has
no `## Fix`. After `iwe-shipper` ships a plan, `/agentdev:iwe-ship` and Plan
revise mode answering a Ship blocker report SHALL dispatch `iwe-ship-reviewer`
in ship mode with the plan key. When it reports gaps, they SHALL dispatch
`iwe-shipper` with the operation `fix` and the gaps quoted, which SHALL perform
only those operations without running Verify, and review again, for at most 3
fix rounds. `iwe-ship-reviewer` SHALL append the `## Ship review` checklist to
the plan only when every item is `confirmed` or `N/A`. The checklist SHALL be
fixed — no item added, dropped, reordered, or reworded — and its Verify,
plan-stage, and archive items SHALL never be `N/A`. A plan that already ends
with a `## Ship review` that holds SHALL keep it unchanged.

#### Scenario: a ship meets every obligation

- **WHEN** `iwe-ship-reviewer` finds every obligation met
- **THEN** the plan ends with a `## Ship review` whose every item is ticked
  `confirmed` or `N/A`.

#### Scenario: a ship leaves a gap

- **WHEN** `iwe-ship-reviewer` reports a listed bug with no `## Fix`
- **THEN** `iwe-shipper` runs `fix` for that gap alone, without Verify, and the
  plan is reviewed again.

#### Scenario: gaps outlast three rounds

- **WHEN** a gap remains after 3 fix rounds
- **THEN** Ship reports the gap and the plan has no `## Ship review`.

#### Scenario: an always-applicable item has nothing to confirm

- **WHEN** a shipped plan has no saved Verify report, is not `stage: done`, or
  is not archived
- **THEN** `iwe-ship-reviewer` reports that item as a gap rather than `N/A` and
  writes no `## Ship review`.

#### Scenario: a plan is reviewed before implementation

- **WHEN** `iwe-ship-reviewer` runs in plan mode
- **THEN** it reports whether the plan gives Ship what it needs and changes
  nothing.
```

Removed from "Plans declare their release impact": the scenario "A plan
introduces user-visible behavior with no feature", because a plan no longer
needs a feature. "A plan changes nothing users see" becomes "A plan closes no
document". "Capture files complete inbox documents" now writes a bug fixed in
the same change into the archive with no hub link. "Every ship is reviewed
against Ship's obligations" adds the archive item, which is never `N/A`.

`## Rationale` entries for this spec: the decisions and rejected alternatives in
`## Approach`.

[Pre-commit gate](../spec/pre-commit-gate.md):

``` markdown
## MODIFIED Requirements

### Requirement: Ship records are gated in pre-commit

A pre-commit hook SHALL run a checker CLI over every bug, plan, backlog task,
feature, and release document pre-commit passes it, live or archived, at commit time,
over a commit range, and with `--all-files`. The CLI SHALL fail a bug at
`stage: done` that has no `## Fix` heading, and a plan whose `## Ship review` section matches neither the fixed structure nor the earlier one, which ends with the item "Ship edited no hub, release page, or `data/log.md`", and SHALL report every violation with
`path:line`. Its archive placement and release page failures are those
`iwe-workflow-skills` states.

#### Scenario: an open bug has no Fix

- **WHEN** a bug document at `stage: pending` or `stage: planned` has no
  `## Fix`
- **THEN** the hook passes it.

#### Scenario: a Ship review is malformed

- **WHEN** a plan's `## Ship review` misses an item, reorders the items, leaves
  one unticked, or marks the Verify, plan-stage, or archive-move item `N/A`
- **THEN** the hook fails and names the line.

#### Scenario: a Ship review carries the earlier checklist

- **WHEN** a plan's `## Ship review` holds the earlier fixed structure, every
  item ticked, ending with "Ship edited no hub, release page, or `data/log.md`"
- **THEN** the hook passes it.
```

[Line-free anchors](../spec/line-free-anchors.md):

``` markdown
## MODIFIED Requirements

### Requirement: Live anchors resolve

The same script SHALL resolve every anchor under `## Key references` in a plan
without `stage`, and every anchor in a bug or backlog item at `stage: pending`
or `stage: planned` and in every `guides/` document, against the current
checkout, and SHALL fail naming each anchor that does not resolve. A Python
symbol resolves through its syntax tree; a symbol in any other language resolves
when each dotted segment occurs as a whole word in order, so a symbol moved into
a comment still resolves. A quote resolves when it occurs, whitespace-collapsed,
in the anchored region. Anchors elsewhere in a plan, in a finding, and in
archived documents are not resolved.

#### Scenario: A refactor renames an anchored function

- **WHEN** a commit renames a function an active plan's `## Key references` or
  a `guides/` document anchors
- **THEN** the hook fails naming the document and the anchor, until the anchor
  is updated

#### Scenario: An archived plan names deleted code

- **WHEN** a plan under `data/archive/` anchors a file that has since been
  deleted
- **THEN** the resolver does not check it
```

[iwe-branch-name](../spec/iwe-branch-name.md):

``` markdown
## MODIFIED Requirements

### Requirement: Plan state is read in the checkout

The skill SHALL read the plan from the working tree, never from another branch,
looking under `data/plans/` and under every `data/archive/<release>/plans/`,
reporting `missing`, `cancelled`, `done`, `complete` when the plan has no
`stage`, has at least one task checkbox under `## Implementation Steps` or
`## Tasks`, and every such checkbox is ticked, or `incomplete` otherwise, and
SHALL refuse a slug that matches more than one plan with `AMBIGUOUS_PLAN`.

#### Scenario: Working-tree edits count

- **WHEN** a plan's last checkbox is ticked only in the working tree
- **THEN** `plan-state` reports `complete`

#### Scenario: The remote default branch does not count

- **WHEN** a plan is finished only on the remote default branch
- **THEN** `plan-state` reports the plan as the working tree holds it

#### Scenario: A plan with no task checkboxes is not complete

- **WHEN** a plan has no `stage` and no task checkbox
- **THEN** `plan-state` reports `incomplete`

#### Scenario: The older task heading counts

- **WHEN** a plan without `stage` lists every task ticked under `## Tasks`
- **THEN** `plan-state` reports `complete`

#### Scenario: An archived plan is a dependency

- **WHEN** a plan exists only under `data/archive/2.1.0/plans/` at
  `stage: done`
- **THEN** `plan-state` reports `done`

#### Scenario: Two plans share a slug

- **WHEN** `data/plans/20261001-foo` and
  `data/archive/2.1.0/plans/20261020-foo` both exist in the working tree
- **THEN** a lookup by slug `foo` reports `AMBIGUOUS_PLAN`
```

Specs that Tasks 7 to 9 and 11 create or extend record behaviour the code
already has and change none: [catalog-scripts](../spec/catalog-scripts.md),
[cloud-session-host](../spec/cloud-session-host.md),
[devcontainer-state](../spec/devcontainer-state.md),
[ci-workflows](../spec/ci-workflows.md),
[pr-description](../spec/pr-description.md),
[supported-harnesses](../spec/supported-harnesses.md),
[pr-review](../spec/pr-review.md),
[ci-python-environment](../spec/ci-python-environment.md).

## Depends on

[Give each Claude worktree its own agentdev
catalog](../archive/3.0.1/plans/20261103-per-worktree-catalog.md) ships first,
so Task 1's release includes it, Task 9 archives it with the rest of the closed
history, and no plan is in flight while the rulebooks change.

## Verification

- `iwe normalize` leaves no diff, and `iwe schema validate` exits 0.
- `uv run pytest docs/knowledge/tests scripts/tests/test_check_anchors.py scripts/tests/test_check_ship_records.py`
  passes.
- `uv run pytest .agents/plugins/agentdev/tests/test_iwe_branch_name_plan_state.py .agents/plugins/agentdev/tests/test_plan_predecessors.py .agents/plugins/agentdev/tests/test_verify_cache.py .agents/plugins/agentdev/tests/test_iwe_bootstrap.py`
  passes.
- `uv run scripts/check-anchors.py` exits 0.
- `uv run scripts/check-ship-records.py $(git ls-files 'docs/knowledge/data/**/*.md')`
  exits 0.
- `test ! -e docs/knowledge/data/architecture && test ! -e docs/knowledge/migration && test ! -e docs/knowledge/data/log.md`
  succeeds.
- `iwe find --filter '{released: {$exists: true}}' -f keys` prints nothing.
- `iwe find --filter '{type: {$in: [plan, bug, task]}, stage: {$in: [done, cancelled]}}' -f keys`
  prints only keys under `data/archive/`.
- `iwe find --filter '{type: feature, stage: {$nin: [proposed, accepted]}}' -f keys`
  prints only keys under `data/archive/`.
- `iwe stats` reports no broken link.

## Out of scope

- Migrating a repository that already consumed the earlier scaffold; Task 6
  files the follow-up.
- Rules about the graph that `docs/knowledge/AGENTS.md`, `SCHEMA.md`, and the
  rulebooks each restate.
- The `product`, `milestone`, `concept`, and `someday` documents.
- Any change to code the specs describe: a contradiction between a spec and the
  code is recorded or filed, never fixed here.
- Rewriting the existing release pages from old spec diffs; their links become
  plain titles.

## Key references

- `.iwe/config.toml#schemas.plan` — the path binding each type's archive folders
  join.
- `.iwe/config.toml#schemas.hub` — the closed hub set.
- `.iwe/schemas/architecture.yaml` — the retired type, bound only to the
  archive.
- `.iwe/schemas/release.yaml` — the release page's schema.
- `.agents/plugins/agentdev/agents/iwe-shipper.agent.md#steps` — the spec merge,
  the stage transitions, and the release cut.
- `.agents/plugins/agentdev/agents/iwe-ship-reviewer.agent.md#ship-mode` — the
  fixed checklist.
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps` — where a plan
  sets `release` and closes the backlog task it grew from.
- `.agents/plugins/agentdev/skills/iwe-explore/SKILL.md#capturing` — where a
  decision is routed to a spec's `## Rationale` and a finding to
  `data/findings/`.
- `.agents/plugins/agentdev/skills/iwe-branch-name/agent-code/iwe-branch-name.py::find_plan`
  — finds a plan by slug under `data/plans/` and every
  `data/archive/<release>/plans/`.
- `.agents/plugins/agentdev/skills/iwe-verify/agent-code/verify-cache.py::canonical_target`
  — maps a plan to its live or archived plan key.
- `.agents/plugins/agentdev/bin/plan_predecessors.py::stage_of` — reads a
  dependency's stage.
- `scripts/check-anchors.py::resolver_spans` — which documents have their
  anchors resolved.
- `scripts/check-ship-records.py::check` — the per-document dispatch the new
  checks join.
- `docs/knowledge/AGENTS.md#the-operating-loop` — the record step that names
  each home.
