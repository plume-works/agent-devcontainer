# Structure

This document explains how the workspace is put together and why — the design
rationale behind the layout. The repo itself is the deliverable: a template
knowledge base a software project copies and fills.

## Provenance

The structure is generalized from a production app-development knowledge base
(hundreds of documents, maintained daily by agents) built on IWE; the template
conventions — root docs, fill-in tracker, `*.example.md` demo set, workflow
skills — follow its sibling, the IWE marketing workspace template. Two ideas are
adapted from [OpenSpec](https://github.com/Fission-AI/OpenSpec) (see Influences
below).

## Layout

```
README.md          # the pitch and quickstart (humans)
AGENTS.md          # the operating manual (agents) — CLAUDE.md points here
SCHEMA.md          # frontmatter reference (humans)
STRUCTURE.md       # this file: design rationale
.iwe/
  config.toml      # markdown conventions + schema→glob bindings
  schemas/         # validation schemas, one per document type
.agents/plugins/agentdev/skills/iwe-*/  # state workflows: setup, explore, plan,
                   # capture, implement, verify, ship, weekly (invoked as /agentdev:iwe-*)
data/              # the graph
  index.md         # the root hub — every hub is its child
  product.md       # ✏️ fill-in tracker: the doc every session reads first
  <hub>.md + <hub>/  # plans, features, bugs, adr, spec, findings, guides, concept,
                     # releases, backlog, someday (+ milestone.md)
  archive/<release>/<folder>/  # finished work, one folder per cut version
                     # plus next-release
```

## Design decisions

**Hub + directory; membership is a link.** Each entity type pairs a hub file
(`data/plans.md`) with a directory (`data/plans/`). What makes a document a plan
is the inclusion link from the hub, not its path — the directory is storage, the
graph is truth. A hub is one flat list sorted by member key, with no sections,
so it changes only when a member is created, archived, or renamed — two pull
requests conflict on a hub only when their members sort next to each other.

**Work items vs. reference.** Plans, features, bugs, releases, backlog tasks,
and ADRs are *work items*: a lifecycle `stage`, dates, a commit gate
(`iwe schema validate`). Specs, findings, guides, concept, and someday docs are
*durable reference*: they carry a `type` and the shared OKF families, but no
`stage`, because nothing about them is a lifecycle. The split keeps the ceremony
where it pays. Every document is validated — OKF conformance requires a `type`
everywhere — but only work items are asked for more than that.

**Frontmatter is the only record of state.** A work item's `stage`, `priority`,
`completed`, and `rank` live in its own document, so a stage change edits one
file that only its own pull request touches. The build order is a query over
`rank`, not a file.

**One home for each kind of knowledge.** Behaviour lives in the code and its
tests. A decision, with the alternatives it rejected, lives in an ADR — the
document the Consult step reads. A finding is a measurement and lives in
`findings/`; a procedure lives in `guides/`, whose anchors are checked on every
commit. A feature is a proposal, live only until its plan ships. A statement
with two homes drifts in the one nobody maintains, so no type restates another's
content. `data/spec/` gets no new text.

**Finished work is archived, not deleted.** Whoever closes a plan, bug, task,
feature, or ADR moves it with `iwe rename` to `archive/next-release/<folder>/`
and removes its hub link; the release cut moves `next-release` to the version's
folder. Keeping the original subfolder keeps every archived document under its
type's schema, and the folder is the only record of which release took it, so no
field repeats it. Hubs list live work only.

**Minimal frontmatter; relationships are links.** Six stage vocabularies, three
date fields, one `rank`, and the `supersedes` list of an ADR — that's the entire
frontmatter surface. Everything relational (plan → ADR, plan → feature, plan →
plan dependency) is a markdown link in the body, which keeps relationships
visible while reading and traversable via `iwe find --references`.

**The funnel.** Ideas harden stepwise: `someday/` (no commitment) → `backlog/`
(prioritized) → `plans/YYYYMMDD-<slug>` (committed, dated) → ADRs accepted and
the plan archived → a cut release. Each promotion is a new doc, a frontmatter
change, or an archive move.

**ADRs are short, and nobody edits an accepted ADR.** An ADR is a short title
and 1 to 3 sentences that give the context, the decision, and the reason. Plan
files it at `stage: proposed`, Ship sets it to `accepted`, and a cancelled
plan's ADR becomes `rejected`. A changed decision is a new ADR that supersedes
the earlier one, so a reader sees each decision as it was made. Code comments
cite an ADR as `ADR-NNNN`.

**Acceptance lives in the plan.** A plan states each behaviour it adds, changes,
or removes as an `## Acceptance` scenario that names the test that proves it,
or, for behaviour no test can reach, the file that the verifier reads. Verify
checks the scenarios against the code before Ship. Ship copies nothing: the
scenarios stay in the archived plan.

**The release cut reads the archive.** The cut writes the release page in plain
text from the `## Acceptance` scenarios of the plans in
`archive/next-release/plans/`, the titles of the ADRs accepted or superseded
since the previous cut, and the titles of the archived bugs. The archived plans
are what changed, so the page needs no link to a document written before the
work.

**Milestones are plans of plans.** An aggregator plan inclusion-links its child
plans as one flat list; their `rank` sets the build order, and dependencies stay
in prose. `milestone.md` links the aggregators. No special milestone machinery —
the graph already does it.

**Code anchors name, never count.** `## Key references` lists anchors —
`path::symbol` in code, `path#heading-slug` in Markdown, `path#key.path` in
YAML, JSON, and TOML, plus a short verbatim quote for a spot inside one — taken
from the current checkout, never from memory. An anchor stays true until its
target is renamed or removed, and then it stops resolving, so it carries no
date. A line number gives no such signal and is never recorded.

**Authoring rules travel with the product doc.** `data/product.md` carries an
optional `## Authoring rules` section — per-document-type constraints the plan
and ship skills consult before writing. Project-specific discipline lives in
data, not in forked skill prompts.

## Influences: OpenSpec

Adopted, in IWE-native form:

- **Requirement/Scenario format** — `### Requirement:` + SHALL +
  `#### Scenario:` WHEN/THEN, with OpenSpec's "progressive rigor" stance: scale
  ceremony with risk, as a convention rather than a validation gate.
- **Authoring rules** — modeled on OpenSpec's per-artifact `rules:` config,
  relocated into the product doc.
- **Dependencies** — OpenSpec's `dependsOn` metadata becomes a `## Depends on`
  section of inline links: queryable, no new machinery.
- **The explore / implement / verify skills** — adapted from OpenSpec's explore
  (thinking-partner stance, never writes code), apply/continue (task-by-task
  execution with artifact discipline), and verify-change (completeness /
  correctness / coherence report) workflows, translated onto the
  single-plan-document model.

Deliberately not adopted:

- **Archive by file move** (`changes/archive/YYYY-MM-DD-*`) — `stage: done` plus
  graph queries gives the same lifecycle without moving files or breaking links.
- **Per-change file bundles** (proposal/design/tasks/specs per change) — one
  plan document with sections is leaner; when a plan genuinely outgrows one
  file, inclusion links split it natively.
- **Spec deltas and their merge at archive** — a plan states acceptance
  scenarios that stay in the plan, and nothing merges them into a spec.

## Improvements over the source KB

Lessons from the knowledge base this template generalizes:

- Its `## Failed` plans section had no frontmatter counterpart — failed plans
  were indistinguishable from active ones in queries. Here `stage: cancelled` ⇄
  `## Cancelled` covers abandoned work completely.
- It accumulated overlapping ad-hoc hubs (dated snapshot indexes duplicating the
  real ones). This template ships exactly one hub per entity type; point-in-time
  views should be queries, not files.
- Its examples of convention lived in real (product-specific) docs. Here the
  `*.example.md` set demonstrates every convention on a fictional product,
  schema-validated so it can't rot, and deleted by setup.

## Publishing

Intended to live as a GitHub template repository. The `.iwe/` runtime artifacts
(databases, snapshots) are gitignored; only `config.toml` and the schemas are
authored files.
