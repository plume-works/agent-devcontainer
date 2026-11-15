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
SCHEMA.md          # the definition of each document type
STRUCTURE.md       # this file: design rationale
.iwe/
  config.toml      # markdown conventions + schema→glob bindings
  schemas/         # validation schemas, one per document type
.agents/plugins/agentdev/skills/iwe-*/  # state workflows: setup, explore, plan,
                   # capture, implement, verify, ship, weekly (invoked as /agentdev:iwe-*)
data/              # the graph
  index.md         # the root hub — every hub is its child
  product.md       # ✏️ fill-in tracker: the doc every session reads first
  <hub>.md + <hub>/  # plans, features, bugs, adr, findings, guides, product-vision,
                     # releases, backlog, someday (+ milestone.md)
  archive/<release>/<folder>/  # finished work, one folder per cut version
                     # plus next-release
```

## Design decisions

`SCHEMA.md` is the only definition of the document types, the hubs, the build
order, and the archive. This section gives the reason for each decision and
names the section of `SCHEMA.md` that defines it.

**A hub is one flat sorted list** (`SCHEMA.md#hubs`). Two pull requests then
conflict on a hub only when their members sort next to each other.

**Work items and reference documents** (`SCHEMA.md#what-goes-where`). Only a
work item has a lifecycle, so only a work item has a `stage`. Each document is
validated, but only a work item must have more than a `type`.

**Frontmatter is the only record of state**
(`SCHEMA.md#fields-every-type-carries`). A stage change then edits one file, and
only the pull request of that work item touches the file. The build order
(`SCHEMA.md#build-order`) is a query, not a file, for the same reason.

**Each kind of knowledge has one home** (`SCHEMA.md#what-goes-where`). A
statement with two homes becomes incorrect in the home that nobody maintains.

**Finished work is archived, not deleted** (`SCHEMA.md#archive`). The archive
keeps the subfolder of each document, so the schema of its type continues to
check it. The folder is the only record of the release, so no field repeats it.

**Relationships are links, not fields.** A relation between documents (plan →
ADR, plan → feature, plan → plan) is a Markdown link in the body. The reader
sees it in the text, and `iwe find --references` follows it.

**The funnel.** An idea becomes firm in steps: a someday idea, a backlog task, a
plan, a shipped plan in the archive, a cut release. Each step is a new document,
a frontmatter change, or a move to the archive.

**Nobody edits an accepted ADR** (`SCHEMA.md#adrs`). A reader then sees each
decision as it was made.

**Acceptance is in the plan** (`SCHEMA.md#plans`). Verify checks the scenarios
against the code before Ship. Ship copies nothing: the scenarios stay in the
archived plan.

**The release cut reads the archive** (`SCHEMA.md#releases`). The archived plans
are what changed, so the page needs no link to a document that was written
before the work.

**A milestone is a plan of plans** (`SCHEMA.md#plans`). The graph already gives
this structure, so a milestone needs no mechanism of its own.

**A code anchor names a place and never counts lines**
(`SCHEMA.md#code-anchors`). An anchor stays correct until its target gets a new
name or goes away, and then it does not resolve. A line number gives no such
signal.

**Authoring rules are in the product document** (`SCHEMA.md#trackers`). The
rules of one project are then data, not a changed copy of a skill.

## Influences: OpenSpec

Adopted, in IWE-native form:

- **Scenario format** — a plan's `### Scenario:` blocks with WHEN/THEN lines,
  with the OpenSpec "progressive rigor" rule: the higher the risk, the more
  scenarios a plan has. This is advice, not a validation check.
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
