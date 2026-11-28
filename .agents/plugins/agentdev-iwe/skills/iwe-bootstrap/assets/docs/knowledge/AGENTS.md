# Agent operating manual

You are operating a **dev workspace**: a markdown knowledge graph that is a
software project's memory and system of record. The division of labor:

- **Code** lives in the rest of the repository. Writing it is your normal work —
  this workspace doesn't change how you code.

- **Knowledge base** lives here, in `docs/knowledge/data/`:

  - what the product is;
  - the decisions and their reasons (ADRs);
  - what was measured (findings);
  - how to do recurring jobs (guides);
  - what's proposed, planned, broken, and released;
  - the finished work, in the archive.

  When work settles durable knowledge, record it in the graph; a session that
  settles none records nothing. Never keep it only in conversation.

## Start of every session

1. Read `docs/knowledge/data/product.md`. If it still contains ✏️ placeholders,
   run the setup flow (`/agentdev-iwe:iwe-setup`) before anything else —
   planning without product context is guessing. Note `## Constraints` and
   `## Authoring rules`: they bind everything you write.
2. Check the state of work: the build order —
   `iwe find --filter '{rank: {$exists: true}}' --sort rank:1 -f keys` — lists
   active plans, open bugs, and pending tasks together, lowest `rank` first.
   Work not yet sequenced is the second query:
   `iwe find --filter '{rank: {$exists: false}, stage: {$nin: [done, cancelled]}, type: {$in: [plan, bug, task]}}' -f keys`.

## The operating loop

1. **Pick** the next piece of work (the user's request, an active plan, or the
   backlog head).
2. **Consult** before you act: the related ADRs in `data/adr/` (the decisions in
   force and the alternatives they rejected), any `data/findings/` doc on the
   area, and the bug doc the work belongs to. If a plan exists, execute the
   plan; if the work deserves one, write it first (plan skill).
3. **Execute** — implement in the codebase, following the plan's tasks (the
   implement skill keeps checkboxes, anchors, and deviations honest while you
   do).
4. **Record** — write the state in the graph. `SCHEMA.md#what-goes-where` names
   the document type for each kind of knowledge and its writer. The document in
   `schema/` for that type gives its path, frontmatter, body, and stages.
   - Work starts → `/agentdev-iwe:iwe-plan`.
   - A bug or an actionable task → `/agentdev-iwe:iwe-capture`.
   - An idea, a finding, or a guide → write the document and add its link to its
     hub.
   - Work ships, or a plan is abandoned → `/agentdev-iwe:iwe-ship`. It runs
     `/agentdev-iwe:iwe-verify` first.
   - A release cut → the release mode of `/agentdev-iwe:iwe-ship`.
   - A task is complete or cancelled → close it as `schema/backlog-tasks.md` and
     `schema/archive.md` give.
5. **Stamp** — every document you create or meaningfully change gets a
   one-sentence `description` if it has none, unless it is an ADR, and — when
   you derived it from code or an external page — a `sources` entry naming that
   path or URL.
6. **Validate & commit** — `iwe normalize`, then `iwe schema validate` must
   pass; commit with a short message describing the state change.

## Conventions

- **Inclusion link** = a markdown link on its own line — it makes the target a
  child in the graph. Hubs (`data/plans.md`, `data/bugs.md`, …) inclusion-link
  their members. Inline links (inside sentences/list items) are soft references
  for cross-cutting relationships.
- **`SCHEMA.md` and the documents in `schema/` are the only definition of the
  document types.** `SCHEMA.md#what-goes-where` gives what goes where. One
  document in `schema/` for each type gives the path, the frontmatter, the body,
  and the stages of that type. Other documents there give the hubs
  (`schema/hubs.md`), the index file (`schema/index-file.md`), the build order
  (`schema/build-order.md`), and the archive (`schema/archive.md`). Refer to the
  document. Do not give a definition again in a different file.
- **Never put a plan task on `data/index.md` for ordinary document work.**
- **No changelogs.** No document records its own history: no `## Changelog`
  section, no `CHANGELOG` file, no dated list of edits. Git history records what
  changed and when.
- **Queries select documents by `type` and frontmatter fields**, not by hub
  membership.
- **`data/` is an OKF (Open Knowledge Format) v0.2 bundle**, and CI checks
  conformance on each commit. Never unbind a schema to get around `okf.yaml` or
  `okf-index.yaml`.
- **Links carry `.md`** — `refs_extension = ".md"`, so a link resolves for
  readers outside iwe. Run `iwe normalize` after bulk edits rather than
  hand-writing link targets.
- **Code anchors**: `schema/code-anchors.md` gives the forms. Never record a
  line number, anywhere.
- **A tick and the code are in one commit, and its message has the completion
  evidence block.** `schema/plans.md` defines the block. One commit ticks at
  most one plan task, and the plan itself carries no evidence line for it. An
  edit that ticks many boxes across the file is the defect, not a shortcut.
  Verify never re-runs what a completion evidence block records.
- **Markdown links only, never wiki links.** References are extension-less
  (`[Timer](adr/0001-timer-counts-wall-clock-time)`), relative to the containing
  file.
- **Example docs**: files suffixed `.example.md` demonstrate each directory's
  document shape (a fictional product; schema-validated so they can't rot).
  Ignore them when reporting real project state; the setup skill deletes them at
  the end of onboarding.

## Where narrative is the format

Best Practice 8 in the repository `AGENTS.md` binds every file: record what is
settled, not the path taken to settle it. Two places in `data/` are the
exception, by design, and only these:

- `data/bugs/` requires Reproduction and Root cause.
- A plan's `## Verification results` holds results of the `## Verification`
  checks and findings that change what the plan claims.

Each records a *conclusion*, written once, in its own document. What has no home
anywhere is the running account written *while* you are still finding out.

Plans are where this fails most often, because the plan is the document already
open. A plan that doubles in length during implementation has almost certainly
absorbed a logbook; the fix is to route each finding to its own document (see
the implement skill's `## Capturing`) and cut the narration.

## iwe basics

The graph is managed by [IWE](https://iwe.md) — the `iwe` CLI. What you must
know:

- A document's **key** is its extension-less path relative to `[workspace].path`
  in `.iwe/config.toml` (`docs/knowledge` in this repo) — e.g. `data/product`,
  `data/plans/20260801-dark-mode` — that's what `-k` and the structural flags
  take. `iwe` must be invoked with the repo root as the working directory; it
  does not search upward for `.iwe/`.
- A document's title resolves from its H1 header.
- **Never `mv` or hand-delete a document** — use `iwe rename` / `iwe delete`,
  which update every link in the graph; a plain `mv` silently breaks references.
  After a rename or delete, check `git diff`: the reference updates are part of
  the change.
- Run `iwe normalize` after any manual edit — it keeps formatting, links, and
  structure consistent.
- If `iwe` isn't installed (command not found): the workspace is still plain
  markdown — reading and editing work fine — but renames, queries, and
  validation need the CLI. Ask the user to install it
  (https://iwe.md/quick-start/) before restructuring anything.

## iwe CLI cheatsheet

``` bash
iwe retrieve -k data/adr/0001-timer-counts-wall-clock-time       # read a doc
iwe retrieve -k data/plans --expand-includes 1                   # hub + children
iwe find --fuzzy timer -f keys                                   # fuzzy title+key match
iwe find --lexical "session log storage" -f keys                 # full-text ranking
iwe find --filter '{type: plan}' -f keys                         # every plan
iwe find --references data/adr/0001-timer-counts-wall-clock-time -f keys  # backlinks
iwe find --filter '{type: plan, stage: done}' -f keys           # frontmatter query
iwe find --filter '{rank: {$exists: true}}' --sort rank:1 -f keys   # the build order
iwe tree -k data/plans -d 2                                      # subtree overview
iwe new --key data/plans/20260801-my-plan                        # create at an explicit key
iwe update -k data/bugs/foo --set stage=done                     # set frontmatter
iwe rename <old-key> <new-key>                                   # move; references auto-update
iwe delete <key>                                                 # delete + reference cleanup
iwe normalize                                                    # run after manual edits
iwe schema validate                                              # the commit gate (exit 0 = clean)
iwe stats                                                        # counts, orphans, broken links
```

Filters are YAML (`$eq`, `$ne`, `$in`, `$gte`, `$exists`, …), not jq. Structural
anchors: `--includes`, `--included-by`, `--references`, `--referenced-by`,
`--roots`.
