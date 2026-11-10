# Structure

This document explains how the workspace is put together and why — the design
rationale behind the layout. The repo itself is the deliverable: a template
knowledge base a software project copies and fills.

## Provenance

The structure is generalized from a production app-development knowledge base
(hundreds of documents, maintained daily by agents) built on IWE; the template
conventions — root docs, fill-in tracker, `*.example.md` demo set, workflow
skills — follow its sibling, the IWE marketing workspace template. Behavior is
specified with [OpenSpec](https://github.com/Fission-AI/OpenSpec) itself (see
Influences below).

## Layout

```
README.md          # the pitch and quickstart (humans)
AGENTS.md          # the operating manual (agents) — CLAUDE.md points here
SCHEMA.md          # frontmatter reference (humans)
STRUCTURE.md       # this file: design rationale
.iwe/
  config.toml      # markdown conventions + schema→glob bindings
  schemas/         # validation schemas: plan, feature, bug, release, task
.agents/plugins/agentdev/skills/iwe-*/  # state workflows: setup, explore, plan,
                   # capture, implement, verify, ship, weekly (invoked as /agentdev:iwe-*)
data/              # the graph
  index.md         # the root hub — every hub is its child
  product.md       # ✏️ fill-in tracker: the doc every session reads first
  <hub>.md + <hub>/  # plans, features, bugs, findings, concept,
                     # releases, backlog, someday (+ milestone.md)
```

## Design decisions

**Hub + directory; membership is a link.** Each entity type pairs a hub file
(`data/plans.md`) with a directory (`data/plans/`). What makes a document a plan
is the inclusion link from the hub, not its path — the directory is storage, the
graph is truth. A hub is one flat list sorted by member key, with no sections,
so it changes only when a member is created, removed, or renamed — two pull
requests conflict on a hub only when their new members sort next to each other.

**Work items vs. reference.** Plans, features, bugs, releases, and backlog tasks
are *work items*: a lifecycle `stage`, dates, a commit gate
(`iwe schema validate`). Findings, concept, and someday docs are *durable
reference*: they carry a `type` and the shared OKF families, but no `stage`,
because nothing about them is a lifecycle. The split keeps the ceremony where it
pays. Every document is validated — OKF conformance requires a `type` everywhere
— but only work items are asked for more than that.

**Frontmatter is the only record of state.** A work item's `stage`, `priority`,
`completed`, and `rank` live in its own document, so a stage change edits one
file that only its own pull request touches. The build order is a query over
`rank`, not a file. No item is ever delisted from its hub — done and cancelled
work is history, not a trash can.

**Minimal frontmatter; relationships are links.** Five stage vocabularies, three
date fields, and one `rank` — that's the entire frontmatter surface. Everything
relational (plan → OpenSpec change, bug → requirement, release → feature, plan →
plan dependency) is a markdown link in the body, which keeps relationships
visible while reading and traversable via `iwe find --references`.

**The funnel.** Ideas harden stepwise: `someday/` (no commitment) → `backlog/`
(prioritized) → `plans/YYYYMMDD-<slug>` (committed, dated) → feature
`implemented` → a cut release. Each promotion is a new doc or a frontmatter
change; the release cut builds the release page from the done plans no earlier
cut took, and stamps each with `released: <version>`.

**Behavior lives in OpenSpec specs, not the graph.** Every behavior is a
requirement in exactly one `openspec/specs/<capability>/spec.md`, and the
decision behind it, with the alternatives it rejected, is that spec's
`## Rationale`. A behavior change is an OpenSpec change; archiving it merges the
delta into the spec and folds the lasting design decisions into its Rationale. A
plan carries no spec content and links the change instead. The graph keeps work
state, findings, and the vision — one home per kind of fact, so a spec and a
design note can never disagree about what the system does.

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

Specs are OpenSpec's own, in `openspec/specs/`, changed through OpenSpec changes
under `openspec/changes/` and merged by `openspec archive`. Adopted alongside,
in IWE-native form:

- **Authoring rules** — modeled on OpenSpec's per-artifact `rules:` config,
  relocated into the product doc.
- **Dependencies** — OpenSpec's `dependsOn` metadata becomes a `## Depends on`
  section of inline links: queryable, no new machinery.
- **The explore / implement / verify skills** — adapted from OpenSpec's explore
  (thinking-partner stance, never writes code), apply/continue (task-by-task
  execution with artifact discipline), and verify-change (completeness /
  correctness / coherence report) workflows, translated onto the
  single-plan-document model.

Not adopted for plans:

- **Archive by file move** (`changes/archive/YYYY-MM-DD-*`) — a plan's
  `stage: done` plus graph queries gives the same lifecycle without moving files
  or breaking links.

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
