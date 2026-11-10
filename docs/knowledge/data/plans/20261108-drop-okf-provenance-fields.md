---
type: plan
created: 2026-11-08
release:
- features/agentdev-iwe-workflow-skills
- features/consumer-iwe-seed
description: Drop OKF's `generated` and `verified` provenance fields from the graph, the schemas, the instructions, and the bootstrap scaffold, and reject them with a `banned-frontmatter-keys` check that template adoption ships to consumers.
sources:
- resource: .iwe/schemas/okf.yaml
- resource: docs/knowledge/SCHEMA.md
- resource: docs/knowledge/AGENTS.md
- resource: docs/knowledge/tests/test_banned_frontmatter_keys.py
- resource: .pre-commit-config.yaml
- resource: .agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md
stage: done
completed: 2026-11-08
---

# Drop OKF provenance fields from the graph

## Context

Every document under `docs/knowledge/data/` carries `generated: { by, at }`, and
`docs/knowledge/AGENTS.md` step 5 requires rewriting it on every edit. The field
adds nothing source control does not already hold: git records when and by whom
a document changed, the whole graph is agent-written, and the actor does not
matter. It costs:

- **Merges** — `at` changes on every edit, so two branches that touch the same
  document collide in its frontmatter even when their content does not.
  [Conflict-free knowledge layout](20261031-kb-conflict-free-layout.md) left
  `generated` and `verified` out of its scope.
- **Review noise** — [PR review scenario bar
  spike](20260929-pr-review-scenario-bar-spike.md) classified findings U21 and
  U22, both about a "wrong generated-by value", as noise.
- **Upkeep** — [Remove Codex](20261031-remove-codex.md) needed carve-outs for
  `generated.by` values naming Codex models; the graph holds three spellings of
  the same models.

`verified: { by, at }` is the same actor-and-date shape. No document sets it.

The [IWE workflow
skills](../../../../openspec/specs/iwe-workflow-skills/spec.md) requirement
"Workflow improvements preserve the IWE and OKF model" reads "existing stage and
status conventions" and lacks the OKF bundle sentence and the two scenarios
[Keep the graph an OKF bundle in the spec](20261101-okf-bundle-in-spec.md)
specified for it. The modified requirement below restores them along with the
new divergence.

## Approach

Remove `generated` and `verified` everywhere they are declared, documented, or
set — schemas, the knowledge manuals, the Capture skill, the graph, and the
bootstrap scaffold, whose support files stay identical to the workspace's. OKF
marks both optional, so the bundle stays conformant.

`okf.yaml` accepts undeclared fields, so removing a declaration does not keep a
field out. The existing `status` check becomes a banned-key check:
`test_no_status_field.py` and its `no-status-field` hook are renamed to
`test_banned_frontmatter_keys.py` and `banned-frontmatter-keys`, and reject
`status`, `generated`, and `verified`, naming the document and the key. A branch
cut before this change that re-adds `generated` to a document fails it.

Consumers get the check the way they get `test_plan_checkboxes.py`: template
adoption's knowledge-base bundle tracks the test file and the consumption guide
lists its hook among those to retain. `iwe-bootstrap` stays unchanged — the [IWE
bootstrap](../../../../openspec/specs/iwe-bootstrap/spec.md) spec forbids it
from adding pre-commit configuration. The test skips the scaffold graph when its
directory is absent, since consumers delete `.agents/`.

A separate test and hook beside `no-status-field` was rejected: a second
near-copy of the same file.

## Implementation Steps

### Task 1: The schemas no longer declare `generated` or `verified`

**Files:** Modify:
`.iwe/schemas/{architecture,bug,concept,feature,hub,okf,plan,release,someday,spec,task,tracker}.yaml`
and the same twelve under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/.iwe/schemas/`

- [x] The `generated` and `verified` properties and the `verification`
  definition `verified` references are gone from all 24 schema files, and the
  workspace and scaffold copies of each schema stay byte-identical
  - **Evidence:** commit ecb2f299;
    `grep -nE 'generated|verified|verification|\$defs'` over both schema
    directories finds nothing, `diff -r` between them reports no difference,
    `iwe schema validate` exits 0, and `uv run pytest docs/knowledge/tests`
    passed (88 tests)

### Task 2: No graph document sets `generated` or `verified`

**Files:** Modify: every Markdown file under `docs/knowledge/data/` and under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/`
whose frontmatter sets either key

- [x] The `generated` mapping is removed from the frontmatter of every document
  in both graphs, by a one-off script kept under `./.tmp/` and not committed;
  body text, including shipped plans' and `data/log.md`'s mentions of
  `generated`, is unchanged
  - **Evidence:** commit b7abea4f (418 files, deletions only); every deleted
    line is a frontmatter `generated:`, `by:`, or `at:` line, and
    `grep -rlE '^(generated|verified):'` over both graphs finds nothing
- [x] `iwe normalize` leaves both graphs unchanged and `iwe schema validate`
  exits 0
  - **Evidence:** commit b7abea4f; at the repo root and in a committed scratch
    copy of the scaffold assets, `iwe normalize` changed no file and
    `iwe schema validate` exited 0

### Task 3: A `banned-frontmatter-keys` check rejects the three keys

**Files:** Rename: `docs/knowledge/tests/test_no_status_field.py` →
`docs/knowledge/tests/test_banned_frontmatter_keys.py`; Modify:
`.pre-commit-config.yaml`

- [x] A document whose frontmatter sets `status`, `generated`, or `verified`
  makes the test fail, naming the document and the key; a key nested under
  another mapping and body text are not reported. The fixture that nests
  `status` under `generated` nests it under a key that stays allowed
  - **Evidence:** commit 1cbfa638;
    `uv run pytest docs/knowledge/tests/test_banned_frontmatter_keys.py` passed
    (5 tests, `test_a_banned_key_is_named` once per key, nesting under
    `sources`), and with `generated:` added to `features/consumer-iwe-seed.md`
    the workspace case failed naming `features/consumer-iwe-seed.md: generated`
- [x] The scaffold graph's case is skipped when its directory is absent, and the
  workspace graph's case always runs
  - **Evidence:** commit 1cbfa638; the test file copied alone into a scratch
    repository with only `docs/knowledge/data/` passed 4 and skipped the
    scaffold case as absent
- [x] The `no-status-field` hook is renamed `banned-frontmatter-keys`, runs the
  renamed test on the same `files` pattern, and
  `pre-commit run banned-frontmatter-keys --all-files` passes
  - **Evidence:** commit 1cbfa638;
    `pre-commit run banned-frontmatter-keys --all-files` passed
- [x] The comment above the hook names all three banned keys and points at
  `spec/iwe-workflow-skills`
  - **Evidence:** commit 1cbfa638;
    `.pre-commit-config.yaml › "The graph never sets"` reads "The graph never
    sets `status`, `generated`, or `verified`; see spec/iwe-workflow-skills."

### Task 4: The manuals and Capture stop stamping provenance

**Files:** Modify: `docs/knowledge/AGENTS.md`, `docs/knowledge/SCHEMA.md`,
`docs/knowledge/README.md`, their scaffold copies under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/`, and
`.agents/plugins/agentdev/skills/iwe-capture/SKILL.md`

- [x] `AGENTS.md` step 5 reads:

  ``` markdown
  5. **Stamp** — every document you create or meaningfully change gets a
     one-sentence `description` if it has none, and — when you derived it from
     code or an external page — a `sources` entry naming that path or URL.
  ```

  - **Evidence:** commit c573dbd6;
    `docs/knowledge/AGENTS.md#the-operating-loop › "— every document you create or meaningfully change gets a"`
    holds this text byte for byte

- [x] The `AGENTS.md` convention on OKF divergence reads:

  ``` markdown
  - **The workspace diverges from OKF only to cut merge and upkeep cost.** It
    never sets OKF's optional `status`: `stage` is the one lifecycle field, so a
    state change edits one field in one file. It never sets OKF's `generated` or
    `verified`: source control records when and by whom a document changed.
  ```

  - **Evidence:** commit c573dbd6;
    `docs/knowledge/AGENTS.md#conventions › "The workspace diverges from OKF only to cut merge and upkeep"`
    holds this text byte for byte

- [x] `SCHEMA.md` loses its `generated` and `verified` bullets under
  `## Fields every type carries`, and the paragraph after them ends:

  ``` markdown
  `stage` is the only lifecycle field: the per-type enums below. A work item's
  state lives only in its own frontmatter; no hub section repeats it. OKF's
  optional `status` is never set, so a state change edits one field. Nor are
  OKF's `generated` and `verified`: source control records when and by whom a
  document changed.
  ```

  - **Evidence:** commit c573dbd6; both bullets are gone and
    `docs/knowledge/SCHEMA.md#fields-every-type-carries › "is the only lifecycle field: the per-type enums below. A"`
    holds these words, rewrapped by `iwe normalize`

- [x] `README.md` describes provenance as `sources` alone: "carries a `type`,
  provenance (`sources`) and lifecycle (`stage`,"

  - **Evidence:** commit c573dbd6;
    `docs/knowledge/README.md#dev-workspace › ") and lifecycle"` reads "carries
    a `type`, provenance (`sources`) and lifecycle (`stage`, `rank`,"

- [x] `iwe-capture/SKILL.md` step 3's stamp bullet reads:

  ``` markdown
     - `description` and `sources` naming every code path, page, and GitHub
       issue URL the item was derived from.
  ```

  - **Evidence:** commit c573dbd6;
    `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md#steps › "naming every code path, page, and GitHub"`
    holds this text byte for byte

- [x] Each scaffold copy is byte-identical to its workspace file

  - **Evidence:** commit c573dbd6; `diff -q` between each of `AGENTS.md`,
    `SCHEMA.md`, `README.md` and its scaffold copy reports no difference

### Task 5: The template changelog drops the fields and tells consumers to delete them

**Files:** Modify: `docs/knowledge/CHANGELOG.md` and its scaffold copy

- [x] Under `## [Unreleased]` → `### Added`, the OKF families bullet no longer
  names `generated`

  - **Evidence:** commit f8b25123;
    `docs/knowledge/CHANGELOG.md#added › "OKF's optional families on every type"`
    lists `description`, `sources`, `resource`, `stale_after`, and `tags`

- [x] Under `### Migration`, step 3 (convert `verified:`) and step 6 (add
  `description` and `generated`) are deleted, the steps are renumbered, and a
  final step reads:

  ``` markdown
  Delete `generated:` and `verified:` from every document under `data/` —
  source control records when and by whom a document changed, and the
  `banned-frontmatter-keys` pre-commit check rejects both.
  ```

  - **Evidence:** commit f8b25123; the old steps 3 and 6 are gone, steps 1-4 are
    renumbered, and
    `docs/knowledge/CHANGELOG.md#migration › "schema-binding key."` holds this
    text as step 5

- [x] The scaffold copy is byte-identical to the workspace file

  - **Evidence:** commit f8b25123; `diff -q` between
    `docs/knowledge/CHANGELOG.md` and its scaffold copy reports no difference

### Task 6: Template adoption ships the check

**Files:** Modify: `.agents/plugins/agentdev/skills/template-consume/SKILL.md`,
`.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`

- [x] `docs/knowledge/tests/test_banned_frontmatter_keys.py` follows
  `docs/knowledge/tests/test_plan_checkboxes.py` in the knowledge-base path list
  of `template-consume/SKILL.md` `## Default Template Surface` and of the
  consumption guide's `### Reusable scaffold`
  - **Evidence:** commit 48da7ed1;
    `.agents/plugins/agentdev/skills/template-consume/SKILL.md#default-template-surface › "docs/knowledge/tests/test_banned_frontmatter_keys.py"`
    and
    `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#reusable-scaffold › "text"`
    list it right after `test_plan_checkboxes.py`
- [x] The consumption guide's `### Reusable scaffold` tells the consumer to copy
  both test files after bootstrap and lists the `banned-frontmatter-keys`
  pre-commit hook among the validation to retain
  - **Evidence:** commit 48da7ed1;
    `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#reusable-scaffold › "docs/knowledge/SCHEMA.md"`
    names both test files to copy and lists the `banned-frontmatter-keys` hook

## Spec changes

[IWE workflow skills](../../../../openspec/specs/iwe-workflow-skills/spec.md) —
contract-heavy: the OKF requirement's text and scenario set change, and
Capture's stamping scenario changes.

``` markdown
## MODIFIED Requirements

### Requirement: Workflow improvements preserve the IWE and OKF model

The strengthened skills SHALL continue to use IWE's single-plan-document
workflow, graph links, durable specs, existing stage conventions, `sources`
attribution, and schema validation. Risk-scaled spec deltas SHALL remain
embedded planning content without introducing OpenSpec change bundles, stores,
separate delta files, archive moves, or a claimed programmatic delta application
engine. The graph SHALL remain a conformant OKF v0.2 bundle — `data/index.md`
lists the hubs, `data/log.md` stays date-grouped, and the `okf`, `okf-index`,
and `okf-log` schemas check every document — and SHALL diverge from OKF only
where OKF costs merges or upkeep. No document under `data/` SHALL set OKF's
optional `status`, because `stage` is the lifecycle field, nor OKF's
`generated` or `verified`, because source control records when and by whom a
document changed. The `banned-frontmatter-keys` pre-commit check SHALL reject a
document that sets any of them.

#### Scenario: Updated skills write project memory

- **WHEN** an updated skill creates or meaningfully changes an IWE document
- **THEN** it follows the existing OKF metadata, graph membership,
  normalization, validation, and commit requirements defined by the workspace

#### Scenario: A document sets a banned frontmatter key

- **WHEN** a document under `data/` carries `status`, `generated`, or `verified`
- **THEN** the `banned-frontmatter-keys` check fails and names the document and
  the key

#### Scenario: A reserved file loses its OKF shape

- **WHEN** `data/index.md` or `data/log.md` departs from the shape its OKF
  schema defines
- **THEN** `iwe schema validate` fails and names the file

### Requirement: Capture files complete inbox documents

The Capture skill SHALL be the only writer of new bug, proposed-feature, and
backlog-task documents, SHALL refuse a document missing any frontmatter field or
body section `SCHEMA.md` requires for its type, SHALL check the graph for a
likely duplicate before filing, SHALL file a feature at `stage: proposed` and
never promote it, SHALL file a bug at `stage: pending` — or at `stage: done`
with its `## Fix` when the same change fixed it — and a task at
`stage: pending`, and SHALL link every filed document from its hub and end with
`iwe normalize` and `iwe schema validate` passing.

#### Scenario: A complete item is captured

- **WHEN** Capture is invoked for a bug, feature, or task whose required
  sections and fields are all supplied, and no likely duplicate exists
- **THEN** Capture writes the document at its lane's key with the `stage`
  `SCHEMA.md` derives for it, stamps `sources`, links it from its hub at its
  sorted position, and validates the graph

#### Scenario: A bug fixed in the same change is captured

- **WHEN** Capture is invoked for a bug the same change already fixed, with a
  `## Fix` describing that fix
- **THEN** Capture files the bug at `stage: done`

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
```

[Template consumption](../../../../openspec/specs/template-consumption/spec.md)
— normative outcome: when `optional_bundles` includes `"knowledge-base"`,
adoption SHALL track `docs/knowledge/tests/test_banned_frontmatter_keys.py` and
SHALL retain its `banned-frontmatter-keys` pre-commit hook, as it does for
`docs/knowledge/tests/test_plan_checkboxes.py`. A repository initialized by
`iwe-bootstrap` alone gets no check: bootstrap adds no hooks.

## Verification

- `uv run pytest docs/knowledge/tests/test_banned_frontmatter_keys.py` passes,
  and on a scratch copy of the graph a document given `generated` makes it fail
  naming that document and `generated`.
- `pre-commit run banned-frontmatter-keys --all-files` passes.
- `grep -rlE '^(generated|verified):' docs/knowledge/data .agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data`
  finds nothing.
- `grep -nE '^ {4}(generated|verified):|verification:' .iwe/schemas/*.yaml .agents/plugins/agentdev/skills/iwe-bootstrap/assets/.iwe/schemas/*.yaml`
  finds nothing.
- `grep -nE 'generated' docs/knowledge/{AGENTS,SCHEMA,README}.md .agents/plugins/agentdev/skills/iwe-capture/SKILL.md`
  finds only the divergence sentences Task 4 writes.
- `diff -r` between `.iwe/schemas` and the scaffold's `.iwe/schemas`, and
  between each of `AGENTS.md`, `SCHEMA.md`, `README.md`, `CHANGELOG.md` and its
  scaffold copy, reports no difference.
- `uv run pytest docs/knowledge/tests .agents/plugins/agentdev/tests/test_iwe_bootstrap.py`
  passes.
- `iwe normalize` leaves the tree unchanged and `iwe schema validate` exits 0.

## Out of scope

- `sources`: it records what a document derives from and does not change on
  every edit.
- Text in shipped plans and in `data/log.md` that mentions `generated`: it stays
  as recorded.
- `iwe-bootstrap` installing the check: its spec bars it from adding pre-commit
  configuration.
- `test_no_schema_declares_status` in
  `docs/knowledge/tests/test_rank_and_base_schemas.py`: the banned-key check
  covers documents, which is where the fields would reappear.

## Key references

- `.iwe/schemas/okf.yaml#frontmatter.properties.sources` — `generated`;
  `.iwe/schemas/okf.yaml#frontmatter.properties.usage_window.properties` —
  `verified`
- `.iwe/schemas/spec.yaml#frontmatter.properties.sources` — `generated`;
  `.iwe/schemas/spec.yaml#frontmatter.properties.sources.items.properties.resource.description`
  — `verified`;
  `.iwe/schemas/spec.yaml#frontmatter.properties.usage_window.properties.to` —
  `verification` definition (the other per-type schemas match)
- `docs/knowledge/AGENTS.md#the-operating-loop › "— every document you create or meaningfully change gets a"`
  — step 5 **Stamp**
- `docs/knowledge/AGENTS.md#conventions › "state change edits one field in one file. It never sets"`
  — the OKF divergence convention
- `docs/knowledge/SCHEMA.md#fields-every-type-carries › "— the materials a document derives from, each"`
  — `generated` bullet;
  `docs/knowledge/SCHEMA.md#fields-every-type-carries › "changed."` — `verified`
  bullet;
  `docs/knowledge/SCHEMA.md#the-build-order--rank › "three types, lower first."`
  — the `status` sentence
- `docs/knowledge/README.md#dev-workspace › ") and lifecycle"` — provenance
  (`generated`, `sources`)
- `docs/knowledge/CHANGELOG.md#added › "OKF's optional families on every type"`
  — OKF families bullet;
  `docs/knowledge/CHANGELOG.md#migration › "source control records when and by whom a document changed"`
  — Migration step 3;
  `docs/knowledge/CHANGELOG.md#migration › "schema-binding key."` — Migration
  step 6
- `.agents/plugins/agentdev/skills/iwe-capture/SKILL.md#steps › "naming every code path, page, and GitHub"`
  — the stamp bullet
- `docs/knowledge/tests/test_banned_frontmatter_keys.py::GRAPHS`,
  `docs/knowledge/tests/test_banned_frontmatter_keys.py::BANNED_KEY`,
  `docs/knowledge/tests/test_banned_frontmatter_keys.py::banned_keys_in`, and
  `docs/knowledge/tests/test_banned_frontmatter_keys.py::test_a_banned_key_is_named`
  — the gate, renamed from `test_no_status_field.py`
- `.pre-commit-config.yaml › "The graph never sets"` — comment above the hook;
  `.pre-commit-config.yaml › "id: banned-frontmatter-keys"` — `no-status-field`
  hook
- `.agents/plugins/agentdev/skills/template-consume/SKILL.md#default-template-surface › "docs/knowledge/tests/test_plan_checkboxes.py"`
  — knowledge-base tracked `test_plan_checkboxes.py`
- `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#reusable-scaffold › "template-owned knowledge paths update mode tracks"`
  — `### Reusable scaffold` path list;
  `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md#reusable-scaffold › "docs/knowledge/README.md"`
  — copy-the-tests sentence
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-capture-files-complete-inbox-documents › "backlog-task documents, SHALL refuse a document missing any"`
  — Requirement: Capture files complete inbox documents;
  `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-workflow-improvements-preserve-the-iwe-and-okf-model › "workflow, graph links, durable specs, existing stage and"`
  — Requirement: Workflow improvements preserve the IWE and OKF model
- `docs/knowledge/data/spec/iwe-bootstrap.md` — Requirement: bootstrap and
  onboarding are separate operations
