# Document types

This file is the only definition of the document types in `data/`. For each
type, it gives what the type holds, the path, the frontmatter, the body, and the
stages. No other file gives these again. A document, a skill, or an agent
rulebook that needs a definition names a section of this file, for example
`docs/knowledge/SCHEMA.md#bugs`.

The schemas in `.iwe/schemas/*.yaml` enforce the shapes. The `[schemas]` section
of `.iwe/config.toml` binds each schema to a path, and each document under
`data/` has a binding, hubs included. `iwe schema validate` must exit 0 before a
commit.

The examples in this file describe one fictional product (Pomodux, a focus-timer
app). The `*.example.md` documents show each shape in place.

`data/` is a conformant [Open Knowledge
Format](https://github.com/GoogleCloudPlatform/knowledge-catalog/blob/main/okf/SPEC.md)
v0.2 bundle. That is why each document has a `type`, and why `data/index.md` has
a shape of its own.

## What goes where

Each kind of knowledge has one home, and no type repeats the content of a
different type.

| Knowledge                                             | Home                          | Writer                                  |
| ----------------------------------------------------- | ----------------------------- | --------------------------------------- |
| How the product behaves                               | The code and its tests        | The change that builds the behaviour    |
| What the product is, its constraints, authoring rules | `data/product.md` (Trackers)  | `/agentdev:iwe-setup`                   |
| A project term                                        | `data/glossary.md` (Trackers) | The change that first uses the term     |
| A principle that stays true in each release           | Product vision                | `/agentdev:iwe-explore`                 |
| An idea that is not a commitment                      | Someday ideas                 | `/agentdev:iwe-explore`                 |
| Work to do that fits in one sitting                   | Backlog tasks                 | `/agentdev:iwe-capture`                 |
| A defect in shipped behaviour                         | Bugs                          | `/agentdev:iwe-capture`                 |
| What users must get, written before the work          | Features                      | `/agentdev:iwe-capture`                 |
| Committed work: its tasks, acceptance, and checks     | Plans                         | `/agentdev:iwe-plan`                    |
| A design decision and its reason                      | ADRs                          | `/agentdev:iwe-plan`                    |
| A measurement that does not yet settle a question     | Findings                      | The session that made the measurement   |
| A procedure that a contributor repeats                | Guides                        | The session that found the procedure    |
| What one release changed                              | Releases                      | The release cut of `/agentdev:iwe-ship` |
| Finished work                                         | Archive                       | The session that closes the work        |

The Home column names a section of this file, or a file. In each path below, a
`<slug>` is a short name in kebab case, and one document has one topic.

Plans, features, bugs, ADRs, releases, and backlog tasks are work items. A work
item has a `stage`. Findings, guides, product-vision documents, and someday
ideas are permanent reference documents. A reference document has a `type` and
no `stage`.

## Fields every type carries

The optional families of OKF (SPEC §4.1, §5) are on each schema.
`.iwe/schemas/okf.yaml` checks them.

- `type` — required on each document under `data/`, with one exception:
  `data/index.md`.
- `description` — one sentence. Each document has one. An OKF consumer and
  `data/index.md` show it before a reader opens the file.
- `sources` — the materials that a document derives from. Each entry is
  `{ id, resource, title, author, usage_count, last_modified }`, and `resource`
  is required. A `resource` is a URL or a repository path. To attribute one
  claim, use a Markdown footnote with the `id` of the entry as its label.
- `resource`, `tags`, `stale_after`, `usage_window` — optional.

`stage` is the only lifecycle field. The state of a work item is only in its own
frontmatter, and no hub repeats it. No document sets the optional `status` of
OKF, so a state change edits one field. No document sets `generated` or
`verified` of OKF: source control records when a document changed and who
changed it.

## Build order

An active plan, a pending or planned bug, and a pending backlog task can have a
`rank`. The `rank` is a positive integer. It gives the place of the item in one
build order that the three types share. A lower `rank` comes first.

``` yaml
rank: 300 # optional; positive integer
```

- The sequence is
  `iwe find --filter '{rank: {$exists: true}}' --sort rank:1 -f keys`. An item
  without `rank` is not in the sequence. The query `rank: {$exists: false}`
  finds these items.
- Ranks step by 100. An item that goes between two others takes the midpoint of
  their ranks. Only a reorder pull request changes the `rank` of more than one
  item.
- A done or cancelled item has no `rank`. The session that closes the item
  removes it.
- Equal ranks are valid. The key decides their order, and CI gives a warning.

## Code anchors

An anchor names a place in a file. A document never records a line number.

- Code: `path::Class.method` or `path::function`.
- Markdown: `path#heading-slug`.
- YAML, JSON, and TOML: `path#key.path`. A list element is named by its `id` or
  its `name`.
- A Makefile or a Dockerfile: `path#target` or `path#stage`.
- A place inside one of these: the anchor, then ` › "verbatim quote"`.

The `path` is relative to the repository root. The writer takes each anchor from
the current checkout, never from memory. An anchor has no date.

## Plans

A plan is committed work that a later session can do with no other context. A
plan is an implementation plan, a migration, or a design proposal. One plan has
one topic: work that needs two verification stories that are not related is two
plans.

- Path: `data/plans/YYYYMMDD-<slug>.md`. The date is the day of creation.
- Hub: `data/plans.md`.

``` yaml
---
type: plan # required
stage: done # done | cancelled — absent while the plan is active
created: 2026-07-01 # required, YYYY-MM-DD
completed: 2026-07-18 # required when stage: done
release: # required while the plan is active: internal, or the keys below
- features/focus-sessions
---
```

- `release` lists the documents that the plan closes: the `features/` keys and
  the `bugs/` keys that Ship marks implemented or done when the plan ships. The
  value is `internal` when the plan closes no document. The field supplies no
  release page, so a plan needs no feature to change what users see.
- `sources` lists the GitHub issue that the plan grew from, if there is one.
- `rank` is optional. See Build order.

| Stage        | Meaning                | Set by | Other fields               |
| ------------ | ---------------------- | ------ | -------------------------- |
| (no `stage`) | Active                 | Plan   | `release` is required      |
| `done`       | The work shipped       | Ship   | `completed` set, no `rank` |
| `cancelled`  | The work was abandoned | Ship   | No `rank`                  |

A done or cancelled plan is in the archive. See Archive.

Body, in this order. A plan leaves out a section that has no content, with two
exceptions: `## Acceptance` and `## Verification` are always there.

- `## Context` — why the work is done now. It links the feature, bug, or backlog
  task that started the work, each document in `release`, and the GitHub issue
  that the plan grew from.
- `## Approach` — the shape of the solution, in a few sentences. A rejected
  option goes in an ADR.
- `## Implementation Steps` — `### Task N: <name>` blocks. Each block has a
  `**Files:**` line (`Create:` and `Modify:`) and `- [ ]` checkboxes.
  - A task that only a later event can close has a
    `**Closed by:** <who or what event>` line.
  - Wording that the user approved is in a fenced block, word for word.
  - A checkbox that is not ticked has no child. A ticked checkbox (`- [x]`) has
    one indented `- **Evidence:**` child: a short note, in free form, of what
    was done and how it was checked. A plan does not prescribe the form of the
    note, and nobody audits it.
- `## Acceptance` — one `### Scenario:` block for each behaviour that the plan
  adds, changes, or removes. A block has a `- **WHEN**` line and a `- **THEN**`
  line. Then it has one of two lines: `- **Test:**` names the test that proves
  the scenario, as `path::test_name`; `- **Checked at ship:**` names the
  rulebook or the file that the verifier reads, for behaviour that no test can
  reach. A plan that changes no behaviour writes `None — no behavioral change`.
- `## ADRs` — one link for each ADR that the plan proposes.
- `## Depends on` — inline links to the plans that must ship first. Each plan
  that the section links is a prerequisite. The exception is a section whose
  text starts with `None`: that plan has no prerequisite, and a plan that it
  links is only related.
- `## Verification` — the commands and tests that the verifier runs to prove
  that the work is done.
- `## Verification results` — the results of the `## Verification` checks, and
  findings that change what the plan claims. This is the only narrative section
  of a plan. The writer adds to it while the work is done, not at the end.
- `## Out of scope` — what the plan does not do.
- `## Key references` — a list of code anchors, each with a short note. See Code
  anchors.
- `## Ship review` — the checklist that `iwe-ship-reviewer` appends after the
  plan ships.

``` markdown
### Scenario: A done bug without a fix fails the check

- **WHEN** a bug at `stage: done` has no `## Fix` section
- **THEN** the `ship-records` check reports the bug and exits 1
- **Test:** `scripts/tests/test_check_ship_records.py::test_done_bug_without_fix_fails`
```

A milestone is a plan whose children are plans: the work for one release. This
aggregator plan has inclusion links to its child plans as one flat list. The
`rank` of each child sets the build order, and dependencies stay in prose. The
milestone ships when its last child plan ships.

## Features

A feature is a proposal: what users must get, written before the work. After its
plan ships, the code and its tests give the behaviour, and the feature goes to
the archive.

- Path: `data/features/<slug>.md`.
- Hub: `data/features.md`.

``` yaml
---
type: feature # required
stage: accepted # required: see the table
---
```

| Stage         | Meaning                               | Set by  | Location         |
| ------------- | ------------------------------------- | ------- | ---------------- |
| `proposed`    | Filed, with no plan                   | Capture | `data/features/` |
| `accepted`    | A plan lists the feature in `release` | Plan    | `data/features/` |
| `implemented` | The plan shipped                      | Ship    | Archive          |
| `deprecated`  | The behaviour is no longer wanted     |         | Archive          |
| `cancelled`   | The proposal was abandoned            |         | Archive          |

Body: `## Purpose`, `## Behaviour`, `## Edge cases`, and `## Open questions`,
all required, in this order. An `## Open questions` section with no open
question says so in one line. Other sections can come after these.

## Bugs

A bug is a defect in shipped behaviour: behaviour that is incorrect and that a
reader can reproduce, or code that does not agree with an accepted ADR. A bug
holds the report and the investigation.

- Path: `data/bugs/<slug>.md`.
- Hub: `data/bugs.md`.

``` yaml
---
type: bug # required
stage: pending # required: see the table
severity: high # critical | high | medium | low — required
---
```

- `severity` is the effect of the defect when it occurs, not its urgency. It
  does not set `rank`.
- `rank` is optional. See Build order.

| Stage       | Meaning                           | Set by                                             | Location     |
| ----------- | --------------------------------- | -------------------------------------------------- | ------------ |
| `pending`   | Open, with no plan                | Capture; Ship or Plan, when the plan drops the bug | `data/bugs/` |
| `planned`   | A plan lists the bug in `release` | Plan                                               | `data/bugs/` |
| `done`      | Fixed                             | Ship; Capture, when the same change fixed it       | Archive      |
| `cancelled` | The bug will not be fixed         |                                                    | Archive      |

Body: an H1 that starts with `Bug: `. Then `## Symptom`, `## Reproduction`, and
`## Root cause`, all required, in this order. Then two optional sections, in
this order. Other sections can come after these.

- `## Potential solution` — the direction that is intended, at any stage.
- `## Fix` — the fix that shipped, in a few sentences. A bug at `done` has it.
  The writer is the session that fixed the bug directly, or Ship, which writes
  it from the plan that fixed the bug and links that plan.

A `## Reproduction` or a `## Root cause` that is not yet known is never only
"unknown". It gives what is known, each hypothesis that was eliminated and what
eliminated it, and a link to the backlog task whose spike settles it. No section
gives the lifecycle of the bug: `stage` does.

## ADRs

An ADR records one design decision and its reason. A decision gets an ADR only
when all three of these are true:

1. **It is hard to reverse.** A later change of the decision has a real cost.
2. **It is a surprise without context.** A later reader of the code will ask why
   it is done this way.
3. **It is the result of a real trade-off.** There were real alternatives, and
   one was selected for specific reasons.

These decisions qualify: the shape of the architecture; an integration pattern
between parts of the system; a technology that is expensive to replace; a
boundary or a scope decision, a refusal included; a deliberate deviation from
the obvious path; a constraint that the code does not show; and an alternative
that was rejected for a reason that is not obvious.

- Path: `data/adr/NNNN-<slug>.md`. `NNNN` is the next free four-digit number in
  `data/adr/` and `data/archive/*/adr/`.
- Hub: `data/adr.md`.

``` yaml
---
type: adr # required
stage: proposed # required: see the table
description: One sentence that gives the decision. # required
supersedes: # optional: the earlier ADRs that this ADR replaces
- adr/0001-code-and-tests-state-behaviour
---
```

The frontmatter has no date field. Git records the date.

| Stage        | Meaning                                        | Set by | Location    |
| ------------ | ---------------------------------------------- | ------ | ----------- |
| `proposed`   | A plan proposes the decision                   | Plan   | `data/adr/` |
| `accepted`   | The plan shipped                               | Ship   | `data/adr/` |
| `rejected`   | The plan was cancelled                         | Ship   | Archive     |
| `superseded` | An accepted ADR names this ADR in `supersedes` | Ship   | Archive     |
| `deprecated` | The decision does not apply now                |        | Archive     |

Body: an H1 that is the short title of the decision, then 1 to 3 sentences that
give the context, the decision, and the reason. `## Considered Options` and
`## Consequences` are optional, in this order, and the schema permits no other
section. An ADR has an optional section only when the section adds value: the
rejected options, for example, only when a later reader needs them.

- Nobody edits an accepted ADR. A decision that changes gets a new ADR that
  names the earlier ADR in `supersedes`.
- A code comment refers to an ADR as `ADR-NNNN`.

## Releases

A release page says what one cut version changed. Only the release cut writes
it, and nothing edits it after the cut.

- Path: `data/releases/<version>.md`. The version is a semantic version.
- Hub: `data/releases.md`.

``` yaml
---
type: release # required
version: 0.1.0 # required
date: 2026-07-18 # required: the day of the release cut
stage: released # required, always released
---
```

Body: plain text with no Markdown link, with these sections in this order. A
page leaves out a section that has no content.

- Sections with a theme as the heading — the changes that the `## Acceptance`
  scenarios of the plans in the archive folder of the release give, in plain
  language. For an archived plan with no `## Acceptance`, the page uses its
  `## Spec changes`.
- `## Removed` — behaviour that went away.
- `## Upgrade notes` — a change that needs action from a consumer.
- `## Decisions` — the title of each ADR that became accepted or superseded
  after the commit that added the previous release page.
- `## Fixed` — the title of each bug in the archive folder of the release.

## Backlog tasks

A backlog task is one small work item with a priority, which waits to become a
plan or a quick fix. A task that does not fit in one sitting becomes a plan.

- Path: `data/backlog/<slug>.md`.
- Hub: `data/backlog.md`.

``` yaml
---
type: task # required
stage: pending # required: see the table
priority: high # high | medium | low
created: 2026-08-01 # required, YYYY-MM-DD
completed: 2026-08-14 # set when the task is done
---
```

- `priority` is required on a new task.
- `rank` is optional. See Build order.

| Stage       | Meaning                                 | Other fields               | Location        |
| ----------- | --------------------------------------- | -------------------------- | --------------- |
| `pending`   | Open                                    |                            | `data/backlog/` |
| `done`      | The work is complete, or a plan took it | `completed` set, no `rank` | Archive         |
| `cancelled` | The task was abandoned                  | No `rank`                  | Archive         |

Capture files a task at `pending`. The session that completes or abandons the
task closes it. Plan closes a task as `done` when a plan grows from it.

Body: an H1, then text that gives the work and why it is important.

## Findings

A finding is a measurement that does not yet settle a question. A finding is not
a design, and it gives no behaviour that the code must have.

- Path: `data/findings/<slug>.md`.
- Hub: `data/findings.md`.
- Frontmatter: `type: finding`. The schema does not accept a `stage`.

Body: `## Measurement` and `## Closing` are required, in this order. Other
sections can be there. A finding gives:

- the measurement;
- each hypothesis that was eliminated, and what eliminated it;
- what can settle the question;
- what closes the finding. "Not worth the cost" is a valid closing, and the
  finding records it as a decision.

A finding has its own document. The document that the question came from keeps
no summary of the finding, no section about it, and no link to it. The one
exception is its status line, and only when the finding changes its own
acceptance. A reference points from the newer document to the older document.

## Guides

A guide is a procedure that a contributor follows to do one job in the
repository, and that the README does not give.

- Path: `data/guides/<slug>.md`.
- Hub: `data/guides.md`.
- Frontmatter: `type: guide`. The schema does not accept a `stage`.

Body: one H1 and the steps. Each code anchor in a guide is resolved on each
commit.

## Product vision

A product-vision document gives one principle that stays true in each release:
why the product exists, and what decides a feature discussion.

- Path: `data/product-vision/<slug>.md`.
- Hub: `data/product-vision.md`.
- Frontmatter: `type: product-vision`. No other field is necessary.

## Someday ideas

A someday idea is an idea, a proof of concept, or a brainstorm that is not a
commitment.

- Path: `data/someday/<slug>.md`.
- Hub: `data/someday.md`.
- Frontmatter: `type: someday`. No other field is necessary.

An idea that becomes real moves to the backlog with
`/agentdev:iwe-capture task --from someday/<slug>`, or becomes a plan.

## Hubs

A hub is the list of the live documents of one type. Each type above has one
hub, and the hub set is closed: `[schemas.hub]` in `.iwe/config.toml` lists it.

- Frontmatter: `type: hub` and `stage: living`.
- Body: an H1, then one flat list of inclusion links, one for each member. The
  list is sorted by the key of the member, with a `YYYYMMDD-` prefix removed. A
  hub has no `##` section: `.iwe/schemas/hub.yaml` rejects one, and a test
  checks the order.
- The `description` of a hub names the section of this file that defines its
  members. A hub gives no rule.
- A hub lists live documents only. It changes only when a member is created,
  archived, or renamed, never for a change of stage or priority.

## Trackers

A tracker is a living document that is edited in place. There are three, each
with `type: tracker` and `stage: living`.

- `data/product.md` — what the product is, its users, platforms, and stack. Its
  `## Constraints` section and its optional `## Authoring rules` section bind
  each plan and each document. Plan and Ship read them before they write. Each
  session reads it first.
- `data/milestone.md` — the links to the aggregator plans. See Plans.
- `data/glossary.md` — the project terms that the prose rule permits.

## Index file

`data/index.md` is a reserved filename of OKF, not a concept document. It has no
`type`, and `okf-index.yaml` checks it. Its only frontmatter is
`okf_version: "0.2"`. The body is `#` sections of link bullets. Each bullet is a
Markdown link to a hub or a tracker, then `-`, then the `description` of that
document. The index lists hubs and trackers, never their members, so it changes
only when a hub is added or removed. The graph has no `data/log.md`, which OKF
makes optional.

## Archive

Finished work goes to the archive and is never deleted. `data/archive/` has one
folder for each cut version, and the folder `next-release`. Each folder has the
subfolder that its documents were in: `plans/`, `bugs/`, `backlog/`,
`features/`, `adr/`, or `architecture/`. Each archived document keeps the schema
of its type and is validated in full.

- The session that closes a plan, a bug, a task, a feature, or an ADR moves it
  with `iwe rename` to `data/archive/next-release/<folder>/` in the same change,
  and removes its link from its hub. The stage tables above show which stages
  are in the archive.
- The release cut moves all documents under `next-release` to the folder of the
  version, and keeps the subfolders.
- The folder is the only record of the release of a document. No document has a
  `released` field. A document that no plan closed is part of the release that
  was open when the document closed.
- `type: architecture` is valid only under `data/archive/`. It is a retired
  type: a system design note, with the alternatives that were rejected.
- The `ship-records` check fails when a document is in the incorrect folder for
  its stage.
