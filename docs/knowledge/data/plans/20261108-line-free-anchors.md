---
type: plan
created: 2026-11-08
release:
- features/agentdev-iwe-workflow-skills
description: Never record a line number — anchor every reference by symbol, heading slug, key path, or verbatim quote, in the graph, the catalog, and skill chat reports — and enforce it with a line-number gate and an anchor resolver.
sources:
- resource: .agents/plugins/agentdev/agents/iwe-planner.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-implementer.agent.md
- resource: .agents/plugins/agentdev/agents/iwe-verifier.agent.md
- resource: docs/knowledge/AGENTS.md
- resource: .pre-commit-config.yaml
stage: done
completed: 2026-11-08
released: 3.0.0
---

# Replace line-number anchors with symbol, heading, key, and quote anchors

## Context

The maintainer's rule: **NEVER RECORD LINE NUMBERS.** A line number is wrong the
next time its file changes. The planner writes `## Key references` as
`path:line — symbol` under a `Verified anchor points (line numbers as of …)`
stamp, the implementer re-locates and re-dates them at every session start, and
the graph holds about 2,400 such references across 185 documents. Of the anchors
in the 20 most recently shipped plans, 47% pointed at the wrong line on the
commit before they shipped; against the checkout of 2026-11-08, 57% of the
anchors in plans dated 2026-10-30 to 2026-11-07 are wrong and 13% name a deleted
file. Every one of them also named its symbol — the part that still locates the
code.

Skill chat reports have the same defect for a different reason: the maintainer
finds reports that cite `path:line` impossible to read, and wants anchors there
too, as human-readable references.

The change belongs to the [agentdev IWE workflow
skills](../features/agentdev-iwe-workflow-skills.md): the planner, implementer,
verifier, shipper, and reviewer rules and the knowledge templates the bootstrap
skill ships.

## Approach

Every reference names its target by the address the file already has, and pins a
spot inside it with a short verbatim quote. Nothing is planted in the target
file. The syntax:

| Target                     | Anchor                                                                                |
| -------------------------- | ------------------------------------------------------------------------------------- |
| Code                       | `path::Class.method`, `path::function`, `path::shell_function`                        |
| Markdown                   | `path#heading-slug` (GitHub's heading slug)                                           |
| YAML, JSON, TOML           | `path#key.path`; a list element is named by its `id` or `name`                        |
| Makefile, Dockerfile       | `path#target`, `path#stage`                                                           |
| A spot inside any of these | the anchor, then ` › "verbatim quote"`, e.g. `SKILL.md#workflow-2 › "never reset it"` |
| A whole file               | `path`                                                                                |

The rule binds everything committed or published to last — graph documents,
skills, agent definitions, code comments, PR and issue bodies — and every
skill's chat report. Only machine positions keep a line: the `line` field
GitHub's review API needs to place an inline comment, and raw tool or gate
output, which a report never quotes with its line numbers.

One repository script, `scripts/check-anchors.py`, holds both checks and runs as
an always-run pre-commit hook, so the CI pre-commit job enforces it too:

- **Line-number gate** — fails on any line-number reference in
  `docs/knowledge/data/` and in the agentdev catalog's skills and agents
  (`.agents/plugins/agentdev/skills/` and `agents/`, which includes the
  bootstrap assets).
- **Anchor resolver** — every anchor under `## Key references` in an active
  plan, and every anchor anywhere in an open bug or backlog item (`stage`
  pending or planned) and in every `architecture/` document, must resolve in the
  current checkout. Anchors elsewhere in a plan are written in anchor syntax but
  not resolved, since a plan's tasks name code it has not created yet.

The hook runs on every commit, not on a path filter, because a code rename
anywhere can break an architecture or open-bug anchor.

All existing references are rewritten — closed documents included — so the gate
scans the whole tree with no exemption.

Rejected: keeping line numbers with a date stamp (the measured drift is the
status quo); planting `<a id>` or `anchor:` comments in target files (every
reference would edit the file it points at, and a symbol or heading already
identifies the spot); exempting closed documents from the gate (agents copy the
shape they read, and the exemption needs its own rule).

## Implementation Steps

### Task 1: Line-number gate

**Files:** Create: `scripts/check-anchors.py`,
`scripts/tests/test_check_anchors.py`

- [x] `scripts/check-anchors.py` reports, and exits non-zero on, every
  line-number reference in the scanned files: `file.ext:N` and `file.ext:N-M`,
  an extensionless `Dockerfile…:N`, `Makefile…:N`, or `Containerfile…:N`, a
  `#LN` URL fragment, and prose `line N` / `lines N` (any case). It scans
  `docs/knowledge/data/**/*.md`, `.agents/plugins/agentdev/skills/**/*.md`, and
  `.agents/plugins/agentdev/agents/**/*.md`, fenced blocks included, and lists
  every violation, not only the first. Tests run the script against synthetic
  trees under the tests' `TMP_ROOT` (`scripts/tests/scratch.py`): each form
  fails, an anchor-syntax reference and a `host:port` without a file extension
  pass.
  - **Evidence:** commit `a97465fb` adds the gate;
    `uv run pytest scripts/tests/test_check_anchors.py` passes 18 tests at that
    commit.

### Task 2: Anchor resolver

**Files:** Modify: `scripts/check-anchors.py`,
`scripts/tests/test_check_anchors.py`

- [x] The same script resolves the anchors in its resolver scope:
  `## Key references` of every plan without `stage`, the whole body of every bug
  and backlog item with `stage: pending` or `stage: planned`, and every document
  under `docs/knowledge/data/architecture/`. An anchor is a back-ticked span
  holding a relative path with `::` or `#`, or a relative path and ` › "…"` in
  one back-ticked span (`path#slug › "quote"`); an all-digit fragment (`#123`,
  `owner/repo#123`) and a URL are not anchors. Resolution rules:

  - `path::A.b` in Python: `ast` finds class, function, or module- and
    class-level assignment `A`, then `b` inside it. In any other file: each
    dotted segment occurs as a whole word, in order.
  - `path#slug` in Markdown: a heading whose GitHub slug equals `slug` (a
    repeated heading's slug takes `-1`, `-2`, …).
  - `path#a.b` in YAML, JSON, or TOML: the key path exists; a segment that meets
    a list matches the element whose `id` or `name` equals it.
  - `path#name` in a Makefile or Dockerfile: a `name:` target or a
    `FROM … AS name` stage.
  - ` › "quote"`: the quote occurs, whitespace-collapsed on both sides, in the
    anchored region — the heading's section for a Markdown slug, the whole file
    otherwise.

  Every unresolved anchor is reported with its document and the reason. Tests
  run the script against synthetic trees: each form resolves, a renamed symbol,
  a removed heading, a missing key, a reworded quote, and a missing file each
  fail, and an unresolvable anchor in a closed plan, a done bug, or a plan's
  `## Implementation Steps` passes.

  - **Evidence:** commit `e316306f` adds the resolver;
    `uv run pytest scripts/tests/test_check_anchors.py` passes 54 tests at that
    commit, and `uv run scripts/check-anchors.py` resolves all eleven of this
    plan's `## Key references` anchors. Commit `6f31df25` makes the closed-plan
    cases hold an anchor that does not resolve, and adds an active-plan case
    where the same anchor fails; 55 tests pass.

### Task 3: The rule in AGENTS.md

**Files:** Modify: `AGENTS.md`

- [x] Add the rule as Best Practice 12, after item 11, in this wording:

  ``` markdown
  12. **NEVER RECORD LINE NUMBERS.** A line number is wrong the next time its
      file changes. Everything committed or published — graph documents,
      skills, agent definitions, code comments, PR and issue bodies — and every
      skill's chat report names a place by an anchor:
      - code: `path::Class.method` or `path::function`
      - Markdown: `path#heading-slug`
      - YAML, JSON, TOML: `path#key.path`, a list element by its `id` or `name`
      - Makefile, Dockerfile: `path#target` or `path#stage`
      - a spot inside any of these: the anchor plus a short verbatim quote,
        `SKILL.md#workflow-2 › "never reset it"`

      Only machine positions keep a line: the `line` field GitHub's API needs
      to place an inline review comment, and raw tool output, which a report
      never quotes with its line numbers. `scripts/check-anchors.py` enforces
      the graph and the catalog.
  ```

  - **Evidence:** commit `2ec90546` adds item 12 to `AGENTS.md`; a `diff` of
    that item against the fenced block above reports no difference.

### Task 4: Knowledge templates, workspace and bootstrap copies

**Files:** Modify: `docs/knowledge/AGENTS.md`, `docs/knowledge/STRUCTURE.md`,
`docs/knowledge/SCHEMA.md`, and the identical copies under
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/`, plus
`.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/data/plans/20260701-focus-sessions.example.md`

- [x] In both copies of each file: the `AGENTS.md` **Code anchors** bullet, the
  `STRUCTURE.md` **Code anchors are dated** paragraph, and the `SCHEMA.md` plan
  body list describe `## Key references` as anchors in the Approach syntax,
  taken from the current checkout, with no line number and no date stamp. The
  bootstrap copies state the rule themselves, since a consuming repository's
  `AGENTS.md` does not carry it. Each workspace file stays byte-identical to its
  bootstrap copy.
  - **Evidence:** commit `458c93f0` rewrites the three rules in both copies;
    `cmp` of each workspace file against its bootstrap copy reports no
    difference at that commit.
- [x] The example plan's `## Key references` drops its stamp and reads
  `src/store/sessions.ts::appendSession` — the log writer, and
  `src/main.ts::bootstrap` — window/tray bootstrap where the view mounts.
  - **Evidence:** commit `458c93f0` rewrites the example plan's
    `## Key references`; `uv run scripts/check-anchors.py` reports no line
    number in the bootstrap assets at that commit.

### Task 5: Planner and implementer rules

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-planner.agent.md`,
`.agents/plugins/agentdev/agents/iwe-implementer.agent.md`

- [x] `iwe-planner`: step 3 collects anchors, not line numbers; step 4's
  `## Key references` bullet is an anchor list in the Approach syntax with no
  stamp; revise mode re-resolves affected anchors with no date to refresh; the
  **Rules** bullet on code anchors drops the date stamp. The rulebook states
  that a plan never records a line number anywhere in its body.
  - **Evidence:** commit `81d78ff6` rewrites steps 3 and 4, revise mode, and the
    **Rules** bullet;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 0 errors at that commit.
- [x] `iwe-implementer`: step 5 confirms each `## Key references` anchor still
  names its target in the current checkout and corrects a renamed or removed
  one, with no date to refresh; evidence written under a ticked task names code
  by anchor, never by line.
  - **Evidence:** commit `81d78ff6` rewrites step 5 and step 6's evidence rule;
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 0 errors at that commit.

### Task 6: Skill and agent reports

**Files:** Modify: `.agents/plugins/agentdev/agents/iwe-verifier.agent.md`,
`.agents/plugins/agentdev/agents/iwe-shipper.agent.md`,
`.agents/plugins/agentdev/agents/iwe-adversarial-reviewer.agent.md`,
`.agents/plugins/agentdev/skills/iwe-audit/SKILL.md`,
`.agents/plugins/agentdev/skills/iwe-explore/SKILL.md`,
`.agents/plugins/agentdev/skills/pr-review/SKILL.md`,
`.agents/plugins/agentdev/skills/pr-feedback-resolution/SKILL.md`,
`.agents/plugins/agentdev/skills/get-codeql-data/SKILL.md`

- [x] Every `path:line` / `file:line` evidence, citation, or table column in
  these files becomes an anchor in the Approach syntax: the verifier's
  correctness mapping, finding format, and evidence rule; the shipper's blocker
  evidence; the adversarial reviewer's **Evidence** field; `iwe-audit`'s
  verification citation and its output table's first column; `iwe-explore`'s
  observed-occurrence list; `pr-review`'s scenario **Path** chain, its
  `iwe-audit` table mapping, and its Step 8 fallback comment;
  `pr-feedback-resolution`'s location notes and coverage-gap summary;
  `get-codeql-data`'s extracted locations as presented to the user.
  - **Evidence:** commit `b540e482` rewrites every listed citation, field, and
    column; `uv run scripts/check-anchors.py` reports no line number under
    `.agents/plugins/agentdev/` and
    `uv run validate_agent_files --recommend . --require-marketplace claude`
    reports 0 errors at that commit.
- [x] `pr-review` keeps the inline comment's `line` as a machine position: it
  places the comment by locating the anchored or quoted line in the diff, and
  the comment text and every review body use anchors. Its constraint against
  prose locations is reworded without a numeric example.
  - **Evidence:** commit `b540e482` places inline comments on the diff line
    holding the quoted text, names fallback locations by anchor, and rewords the
    constraint without a numeric example.

### Task 7: Architecture prose

**Files:** Modify:
`docs/knowledge/data/architecture/pr-review-scenario-validation.md`

- [x] The three-part scenario's **Path** is an anchor chain, not a `file:line`
  chain.
  - **Evidence:** commits `5ee57f76` and `1e748f13` make the **Path** an anchor
    chain; `uv run scripts/check-anchors.py` reports nothing for the document at
    `1e748f13`.

### Task 8: Rewrite the live documents' references

**Files:** Modify: the active plans
`data/plans/20260909-resumable-claude-review-sessions`,
`data/plans/20261013-shared-buildkit-workspace`,
`data/plans/20261030-devcontainer-home-volume`,
`data/plans/20261101-build-on-unshipped-dependencies`,
`data/plans/20261101-per-checkout-uv-environments`,
`data/plans/20261103-backfill-ship-reviews`,
`data/plans/20261103-nested-dispatch-depth`,
`data/plans/20261103-per-worktree-catalog`,
`data/plans/20261103-plan-review-skill`,
`data/plans/20261103-shipper-dispatches-verifier`,
`data/plans/20261103-ship-records-gate`, `data/plans/20261103-ship-review`,
`data/plans/20261104-main-ci-cooldown`; the open bugs
`data/bugs/claude-json-symlink-replaced`,
`data/bugs/doctor-fails-healthy-claude-cloud-devcontainer`,
`data/bugs/firewall-docker-hub-cloudfront`,
`data/bugs/plan-tasks-bundle-independent-observations`,
`data/bugs/plan-tasks-edit-specs`,
`data/bugs/self-improve-reviewer-decline-asymmetry`,
`data/bugs/self-improve-unstageable-routing-option`,
`data/bugs/shared-uv-environment-across-worktrees`,
`data/bugs/ship-ignores-unshipped-dependency`; the open backlog items
`data/backlog/base-image-catalog-smoke-test`,
`data/backlog/exercise-removed-delta-blocks`,
`data/backlog/fail-review-run-without-review`; and
`data/architecture/agent-metadata-files`,
`data/architecture/assignee-review-trigger`,
`data/architecture/pr-verification-sections`

- [x] Every line-number reference in these documents becomes an anchor that
  resolves in the current checkout, each `Verified anchor points` stamp is
  removed, and the resolver passes on the whole resolver scope. A document that
  gained a reference since this list was written is in scope too.
  - **Evidence:** commit `58e0f2cd` rewrites every reference in the listed
    documents and removes their stamps; `uv run scripts/check-anchors.py`
    reports no line number in any active plan, open bug or backlog item, or
    architecture document, and no unresolved anchor, at that commit.

### Task 9: Rewrite the closed plans' references

**Files:** Modify: every plan under `docs/knowledge/data/plans/` with
`stage: done` or `stage: cancelled` that carries a line-number reference

- [x] Every line-number reference becomes an anchor in the Approach syntax and
  every `Verified anchor points` stamp is removed; the gate reports nothing
  under `docs/knowledge/data/plans/`. An anchor in a closed plan names what the
  reference named — its symbol, heading, key, or quoted text — and need not
  resolve: a file the plan cites may since have been deleted.
  - **Evidence:** commit `851f545e` rewrites the references and removes the
    stamps in every closed plan, bare `:N` continuations included;
    `uv run scripts/check-anchors.py` reports nothing under
    `docs/knowledge/data/plans/` at that commit.

### Task 10: Rewrite the remaining closed documents' references

**Files:** Modify: every other document under `docs/knowledge/data/` that
carries a line-number reference (closed bugs and backlog items)

- [x] Same rewrite as Task 9; the gate reports nothing anywhere in its scan
  scope.
  - **Evidence:** commit `ac54dd7f` rewrites the references and removes the
    stamps in the 51 closed bugs and backlog items;
    `uv run scripts/check-anchors.py` exits 0 on the whole checkout at that
    commit.

### Task 11: Wire the hook

**Files:** Modify: `.pre-commit-config.yaml`

- [x] A local `check-anchors` hook runs `uv run scripts/check-anchors.py` with
  `always_run: true` and `pass_filenames: false`, beside the `plan-checkboxes`
  hook, and `uv run pre-commit run check-anchors --all-files` passes.
  - **Evidence:** commit `874d23d9` adds the always-run hook beside
    `plan-checkboxes`; `uv run pre-commit run check-anchors --all-files` passes
    at that commit and fails naming the document when a `path:N` reference is
    planted in an architecture document. This plan's own `## Key references`
    resolve.

### Task 12: Record the decision

**Files:** Create: `docs/knowledge/data/architecture/line-free-anchors.md`;
Modify: `docs/knowledge/data/architecture.md`

- [x] The architecture document records the decision, the anchor syntax by
  reference to `spec/line-free-anchors`, the resolver's scope and its limits,
  and the rejected alternatives from `## Approach`; it is linked from the
  architecture hub.
  - **Evidence:** commit `ed493d66` adds `architecture/line-free-anchors` with
    the decision, the syntax by reference to `spec/line-free-anchors`, the
    resolver's scope and limits, and the rejected alternatives, linked from the
    architecture hub; `iwe schema validate` and
    `uv run scripts/check-anchors.py` pass at that commit.

## Spec changes

A new spec, [Line-free anchors](../spec/line-free-anchors.md), and a modified
requirement in [IWE workflow skills](../spec/iwe-workflow-skills.md).

[Line-free anchors](../spec/line-free-anchors.md):

``` markdown
## ADDED Requirements

### Requirement: References never record a line number

Every reference to a place in a file that is committed or published — graph
documents, catalog skills and agents, code comments, PR and issue bodies — and
every skill or agent chat report SHALL name the place by an anchor and SHALL
never record a line number. An anchor is `path::symbol` in code,
`path#heading-slug` in Markdown, `path#key.path` in YAML, JSON, and TOML (a
list element named by its `id` or `name`), `path#target` or `path#stage` in a
Makefile or Dockerfile, any of those followed by ` › "verbatim quote"` for a
spot inside it, or a bare `path` for a whole file. Only machine positions keep a
line: the `line` GitHub's review API needs to place an inline comment, and raw
tool output, which a report never quotes with its line numbers.

#### Scenario: A plan names the code it touches

- **WHEN** Plan writes `## Key references`
- **THEN** each entry is an anchor taken from the current checkout, with no line
  number and no date stamp

#### Scenario: A verifier cites evidence

- **WHEN** Verify, Ship, or an adversarial review reports a finding
- **THEN** its evidence names the code or document by anchor, never by line

#### Scenario: A pull request review comments inline

- **WHEN** `pr-review` posts a finding as an inline comment
- **THEN** the API call carries the line that places the comment, and the
  comment text and the review body name every location by anchor

### Requirement: A gate rejects line-number references

`scripts/check-anchors.py`, run by an always-run pre-commit hook and therefore by
the CI pre-commit job, SHALL fail on every `file.ext:N` or `file.ext:N-M`
reference, extensionless `Dockerfile`, `Makefile`, or `Containerfile` `:N`
reference, `#LN` fragment, and prose `line N` or `lines N` in
`docs/knowledge/data/` and in the agentdev catalog's skills and agents, fenced
blocks included, and SHALL list every violation. It cannot see chat reports,
code comments, or PR bodies; those rest on the catalog's instructions.

#### Scenario: A plan cites a line

- **WHEN** a commit adds a `scripts/x.py:<number>` reference to any graph
  document
- **THEN** the hook fails and names the document

#### Scenario: A reference uses an anchor

- **WHEN** a document cites `scripts/x.py::main` or `README.md#usage`
- **THEN** the gate passes it

### Requirement: Live anchors resolve

The same script SHALL resolve every anchor under `## Key references` in a plan
without `stage`, and every anchor in a bug or backlog item at `stage: pending`
or `stage: planned` and in every `architecture/` document, against the current
checkout, and SHALL fail naming each anchor that does not resolve. A Python
symbol resolves through its syntax tree; a symbol in any other language resolves
when each dotted segment occurs as a whole word in order, so a symbol moved into
a comment still resolves. A quote resolves when it occurs, whitespace-collapsed,
in the anchored region. Anchors elsewhere in a plan, and in closed documents,
are not resolved.

#### Scenario: A refactor renames an anchored function

- **WHEN** a commit renames a function an active plan's `## Key references` or
  an `architecture/` document anchors
- **THEN** the hook fails naming the document and the anchor, until the anchor
  is updated

#### Scenario: A plan names code it will create

- **WHEN** an active plan's task names `scripts/new.py::main`, which does not
  exist yet
- **THEN** the resolver does not check it, because it is outside
  `## Key references`

#### Scenario: A shipped plan names deleted code

- **WHEN** a plan with `stage: done` anchors a file that has since been deleted
- **THEN** the resolver does not check it
```

[IWE workflow skills](../spec/iwe-workflow-skills.md):

``` markdown
## MODIFIED Requirements

### Requirement: The Verify report reaches the conversation verbatim

Every Verify report SHALL number its findings by severity in report order —
`C<n>` for CRITICAL, `W<n>` for WARNING, `S<n>` for SUGGESTION — and every
caller of Verify SHALL show the report verbatim in its final message text:
`/agentdev:iwe-verify` on the session route, on a saved hit and after a save;
`iwe-shipper` ahead of its Ship summary; and the Implement session for the last
Verify round of a run. A path to the saved report, or the report appearing only
in a tool call or tool result, SHALL not count as showing it. A Ship blocker
report SHALL route each Verify CRITICAL by its ID without restating it, and
SHALL state in full, with anchored evidence, each blocker Ship found outside
Verify.

#### Scenario: A session verifies a plan

- **WHEN** the user runs `/agentdev:iwe-verify <plan>` and the verifier returns
  a report, or the skill finds a saved one
- **THEN** the session's final message contains that report verbatim, not only
  its verdict or the saved report's path

#### Scenario: Ship is blocked by Verify

- **WHEN** `iwe-shipper` gets a Verify report with CRITICAL findings
- **THEN** its final message carries the Verify report verbatim, then a blocker
  report that names each CRITICAL by its ID with its route, and
  `/agentdev:iwe-ship` re-posts that message verbatim

#### Scenario: Ship finds a blocker Verify did not

- **WHEN** Verify reports zero CRITICAL findings and the spec merge finds an
  intent-versus-implementation mismatch
- **THEN** the Shipper's final message carries the Verify report verbatim and
  states the mismatch in full with its anchored evidence and route

#### Scenario: A plan ships

- **WHEN** `iwe-shipper` ships a plan
- **THEN** its final message carries the Verify report verbatim before the
  completed and preserved operations and the commit

#### Scenario: The Implement loop runs several Verify rounds

- **WHEN** an Implement run verifies, fixes findings, and verifies again
- **THEN** its final report carries the last Verify report verbatim and each
  earlier round's verdict with the first line of each finding it fixed
```

## Verification

- `uv run pytest scripts/tests/test_check_anchors.py` passes.
- `uv run scripts/check-anchors.py` exits 0 on the checkout.
- `uv run pre-commit run check-anchors --all-files` passes.
- `grep -rnE '^Verified anchor points \(line numbers as of' docs/knowledge .agents/plugins/agentdev`
  finds no stamp line; prose that mentions the stamp does not match.
- `cmp` of each of `docs/knowledge/AGENTS.md`, `STRUCTURE.md`, and `SCHEMA.md`
  against its copy under
  `.agents/plugins/agentdev/skills/iwe-bootstrap/assets/docs/knowledge/` reports
  no difference.
- `uv run validate_agent_files --recommend . --require-marketplace claude`
  passes.
- `iwe normalize && git diff --exit-code` and `iwe schema validate` pass.

## Out of scope

- Shipping the checker to consuming repositories: they get the rule through the
  bootstrap templates and catalog instructions only.
- Gating code comments, PR bodies, and chat reports mechanically; the catalog
  instructions carry the rule there.
- Planting anchors (`<a id>`, `anchor:` comments) in any file.
- Commit ids in task evidence surviving rebase and squash —
  [backlog/resilient-task-evidence](../backlog/resilient-task-evidence.md).
- Line numbers in the plan-checkbox gate's own output, which is raw tool output.

## Key references

- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "Discover."` —
  step 3, discovery
- `.agents/plugins/agentdev/agents/iwe-planner.agent.md#steps › "a list of anchors, each with a short note"`
  — step 4, the `## Key references` template
- `.agents/plugins/agentdev/agents/iwe-implementer.agent.md › "Re-verify the anchors"`
  — step 5
- `.agents/plugins/agentdev/agents/iwe-verifier.agent.md › "Every claim cites"`
  — the evidence rule
- `.agents/plugins/agentdev/skills/pr-review/SKILL.md#constraints › "Never write a location as a line number"`
  — the prose-location constraint
- `docs/knowledge/AGENTS.md#conventions › "Code anchors"` — the workspace rule
- `docs/knowledge/STRUCTURE.md › "Code anchors name, never count"` — the
  template rationale
- `docs/knowledge/tests/test_plan_checkboxes.py::Violation` — the existing
  gate's report shape
- `.pre-commit-config.yaml › "id: plan-checkboxes"` — the neighbouring hook
- `scripts/tests/scratch.py::TMP_ROOT` — test scratch root
- `docs/knowledge/data/spec/iwe-workflow-skills.md#requirement-the-verify-report-reaches-the-conversation-verbatim`
  — the modified requirement
