---
name: iwe-map
description: Map a codebase into data/codebase/ — an archaeology pass that reads the code and writes one derived doc per component at its canonical key, plus flow- and api- docs, each pinned to the commit it was read at — and refresh that map by re-reading only what moved. Use when the user says "map the codebase", "map the repo", "refresh the map", after setup for the per-module map it defers, or when verify flags stale data/codebase/ docs.
disable-model-invocation: true
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/scripts/*)
---

# Map the codebase

`data/codebase/` is the fourth kind of truth in the graph: spec is what must
be, architecture is why it is shaped this way, concept is why at all, and the
map is **what the code is** — written only by reading it. A map doc is freely
rewritable from a fresh read; a decision record never is. Everything here is
derived, so the only rule that matters is the one every other rule serves:
**read the checkout, never memory, and say "unknown" where the code is silent.**

Two modes. **Initial** writes the map for a workspace whose hub has no members.
**Refresh** re-reads only the docs whose code moved. A scoped request — "map
`crates/parser`", "add a flow for the request path" — runs the initial steps on
that one subtree and wires it into the existing map.

## Steps

1. **Pick the mode.** `iwe find --included-by data/codebase -f keys` — no
   output, or a `✏️` left in `data/codebase.md`, means initial mode. Members
   exist means refresh mode (step 8), unless the request scopes a subtree.
   Read `data/product.md` `## Constraints` and `## Authoring rules` — they
   bind what you write — and `data/architecture.md`, so the map does not
   restate decisions the graph already records.
2. **Survey the outside before the inside.** You cannot understand the inside
   until you know what it is for. From `git ls-files`, the README, manifests,
   build configuration, and CI:
   - **Entry points** — `main`s, CLI commands, lifecycle hooks, workflow
     triggers, published packages and images.
   - **External surfaces** — HTTP routes, CLI contracts, files and formats
     written, environment variables honored, IPC. Each becomes an `api-` doc.
   - **Build, run, test** — the exact commands, from CI and manifests rather
     than the README's memory of them.

   A code-graph tool (a codebase-memory MCP server's architecture overview,
   a language server) is a fast source of leads; every lead is verified in
   the source before it is written down.

3. **Draw the containment tree.** A component is a unit someone names in
   conversation: a crate, package, service, Ansible role, plugin, lifecycle
   layer. A directory earns its own doc when it has its own manifest or
   README, its own tests, or a responsibility its parent cannot state in one
   sentence. Otherwise it is a row in its parent's tables. Skip vendored and
   generated trees, `.tmp/`, and anything gitignored. Compute each doc's key
   with the rules under `## Canonical keys`, then show the tree with a
   one-line role per doc and the count, and ask before writing. Prefer the
   structured-question tool. Thirty docs are a lot to unwind, and the tree is
   the one thing the user can judge faster than you can. Depth is a budget:
   every top-level component, one level deeper where earned; deeper
   candidates stay as unlinked bullets under their parent's `## Contains`,
   marked _not mapped_, so the tree stays honest about its edges.
4. **Dig one component at a time.** Read in this order, stopping when the
   sections below can be filled: the directory's README or agent instructions,
   its manifest, the entry file and what it exports, then the tests — tests
   state the contract and the gotchas better than the implementation does.
   Then the history:

   ```bash
   git log --oneline -- <source> | head -20                      # what has been happening here
   git log --since='1 year ago' --format= --name-only -- <source> | sort | uniq -c | sort -rn | head   # the hot files
   git log -S'<puzzling constant>' --oneline -- <source>          # only for a specific puzzle
   ```

   Hot files get the anchors; a comment that explains a constraint becomes a
   line under `## Invariants & gotchas`; a commit message that explains a
   choice is a lead for `## How it works`, confirmed in the code before it is
   written. A **why** the code reveals — a rejected alternative, a rationale —
   goes into the run's report as a candidate `data/architecture/` doc; the map
   records what, never why.

5. **Write the component doc.** `iwe new --key data/codebase/<key>`, then the
   frontmatter under `## Frontmatter` and this body, in order, omitting a
   section only when it is genuinely empty:
   - A **role paragraph** — what this component is, in the words of its
     directory, not a paraphrase of its README.
   - `## Contains` — inclusion links to child docs, one per line; unmapped
     children as plain bullets.
   - `## Public surface` — the symbols, commands, files, or variables other
     components consume, each with a `path:line` anchor.
   - `## How it works` — the mechanism, in a paragraph or two.
   - `## Depends on` — one way only: what this component consumes. "Used by"
     is `iwe find --references <key>` and is never written.
   - `## Invariants & gotchas` — what breaks if violated, from comments,
     tests, and guards in the code.
   - `## Key references` — `path:line — symbol` anchors under
     `Verified anchor points (line numbers as of <today>):`, from the current
     checkout.

   Keep a doc under about sixty lines of body; a longer one is two components.
   No code listings — anchors point at code, they do not copy it.

6. **Write the flows and interfaces.** A `flow-<name>` doc earns its place by
   crossing component boundaries — a request, a build, a lifecycle, a release
   — and carries a numbered `## Trace` (each step anchored `path:line` and
   linking the component doc it runs in) plus `## Failure modes`. A trace that
   stays inside one component belongs in that component's `## How it works`.
   An `api-<name>` doc describes one external surface: what a consumer can
   rely on, anchored where it is enforced. Two to five flows and one api doc
   per surface is the usual shape; more is a sign the tree is too fine.
7. **Wire the hub and commit.** In `data/codebase.md`: inclusion-link
   top-level components under `## Components`, flows under `## Flows`,
   interfaces under `## Interfaces`. Replace the `✏️` under `## Getting around`
   with how to build, run, and test, the entry points, and a
   `directory → component` table covering every top-level path in
   `git ls-files`, including the ones that earned no doc. Then:

   ```bash
   iwe normalize && iwe schema validate
   iwe tree -k data/codebase -d 3                         # renders the containment tree
   ${CLAUDE_SKILL_DIR}/scripts/stale-map-docs.sh          # RESULT=SUCCESS: every doc is fresh at HEAD
   ```

   Add one bullet to today's group in `data/log.md` naming the map and its
   commit, creating the group if absent. Commit with a message like
   `map: <n> components, <m> flows, <k> interfaces` and report the tree, the
   candidate architecture docs, and what stayed unmapped.

8. **Refresh mode.** Run `${CLAUDE_SKILL_DIR}/scripts/stale-map-docs.sh` and
   branch on its last line (table below). Verify's audit produces the same
   list; take its report as the worklist when it hands off. For each doc:
   - `STALE` — `git diff --stat <commit>..HEAD -- <source>`, re-read the
     changed files and any test that changed with them, rewrite only the
     sections they affect, re-verify every anchor, and bump `commit`,
     `verified`, `stale_after`, and `generated`. A new subdirectory that now
     earns a doc gets one (steps 4–5) and a `## Contains` link.
   - `GONE` — `git log --oneline --diff-filter=D -- <source>` and
     `git log --follow` on a file it held show whether the code moved or was
     removed. Moved: `iwe rename data/codebase/<old> data/codebase/<new>`, fix
     `source`, refresh as stale. Removed: `iwe delete data/codebase/<key>`, then
     sweep the parent's `## Contains` and any flow that traced through it.
   - `UNKNOWN_COMMIT` — the pinned revision is not in this clone (a rewritten
     branch, a shallow clone). Treat as stale over the whole `source`.
   - `EXPIRED` — untouched code past its `stale_after`. Re-read the entry file
     and tests, confirm the doc still holds, and bump `verified` and
     `stale_after`; rewrite what no longer holds.
   - `FRESH` — leave it alone.

   Finish as in step 7. Rerunning the script must end in `RESULT=SUCCESS`.

## Script results

`stale-map-docs.sh` reads every `data/codebase/**/*.md` under the IWE library
and prints one status line per doc, then the counts, then `RESULT`:

| RESULT            | Exit   | Action                                                                                    |
| ----------------- | ------ | ----------------------------------------------------------------------------------------- |
| `SUCCESS`         | `0`    | Every doc is fresh. Nothing to refresh; report so.                                        |
| `STALE_FOUND`     | `3`    | Work the `STALE`, `GONE`, `UNKNOWN_COMMIT`, and `EXPIRED` lines as in step 8.             |
| `NO_MAP_DOCS`     | `4`    | The lane is empty — switch to initial mode.                                               |
| `PREFLIGHT_ERROR` | `2`    | **STOP.** Not a git repository, or no `.iwe/config.toml` at the root; report it verbatim. |
| `SCRIPT_FAILURE`  | `1`    | **STOP.** Report the blocker verbatim; do not work around it.                             |
| `SIGNAL_*`        | `129`+ | **STOP.** The run was interrupted; rerun it.                                              |

## Canonical keys

An agent holding a code path must compute the doc key without searching, and
an agent holding a key must find the code. So the key **is** the path, with
three transformations and nothing else:

1. **Wrapper segments are elided** — a segment that exists only to hold the
   rest and names nothing of its own: `src`, `lib`, `source`, and a package's
   inner directory that repeats the package name
   (`py_packages/foo/foo/validators` → `py_packages/foo/validators`;
   `crates/liwe/src/graph` → `crates/liwe/graph`). A segment that names a
   concept stays: `ansible/roles/xpra_setup` keeps `roles`.
2. **Leading dots are dropped** — `.devcontainer` → `devcontainer`,
   `.github/workflows` → `github/workflows`.
3. **A single-file component drops its extension** — `src/store/streak.ts` →
   `store/streak`.

`flow-<name>` and `api-<name>` docs live at the root of the lane
(`data/codebase/flow-image-build`), named for the trace or surface, not for a
path. `source` on a flow is the broadest path the trace touches; on an api doc,
the code that enforces the surface.

## Frontmatter

```yaml
---
type: codebase
description: <one sentence — what this component is>
source: <repo-relative path, or a list whose first entry is primary>
commit: '<git rev-parse HEAD when the code was read>' # always quoted
verified: { by: <actor>, at: <ISO 8601 now> }
stale_after: <today + 90 days, sooner for code that churns>
generated: { by: <actor>, at: <ISO 8601 now> }
sources:
  - id: code
    resource: <the primary source path>
    title: the code this map describes, read at commit <short sha>
---
```

`commit` is written quoted because an all-digit SHA parses as a number and
fails the schema; `iwe normalize` drops quotes it considers unnecessary, which
is why the pin is the full 40-character SHA rather than a short one — the
all-digit case is then out of reach. Match the pin unquoted when editing a
normalized doc. The actor is the one writing — `claude-code/<model>`,
`human:<handle>`.
`commit` is the HEAD you _read_; the map commit itself never touches a
`source` path, which is why a map doc never lists the knowledge directory that
holds it as its own source.

## Rules

- **Read, never remember.** Every sentence traces to a file in the current
  checkout; an anchor comes from that checkout today. "Unknown" beats
  plausible fiction, and a role you cannot state from the code is a doc you
  do not write yet.
- **What, never why.** Rationale and rejected alternatives belong in
  `data/architecture/`; the map may link a decision record, never restate it.
  Report the candidates; do not write them from this skill.
- **One direction per relationship.** `## Contains` points down,
  `## Depends on` points out; "part of" and "used by" are backlink queries and
  are never written, so they can never rot.
- **Never `mv` or hand-delete a map doc** — `iwe rename` and `iwe delete`
  repair every reference; a plain move breaks the tree silently.
- **Propose before bulk-writing.** The tree is confirmed before the first doc
  exists; a scoped request confirms its subtree the same way.
- **Refresh touches only what moved.** A fresh doc is not rewritten because
  the session would phrase it differently.
- **Ends green.** `iwe normalize`, `iwe schema validate`, and
  `stale-map-docs.sh` at `RESULT=SUCCESS` before the commit, every time.
