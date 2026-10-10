---
name: iwe-capture
description: File a finished inbox item in the IWE graph — a bug, a proposed feature, or a backlog task — after checking for a duplicate and refusing any document that misses a section or field SCHEMA.md requires. Use when Explore settles a defect, feature, or task, when Implement finds a defect or work its plan should not absorb, or to promote a someday idea with `task --from someday/<slug>`. Plans belong to /agentdev:iwe-plan; ideas, architecture, and concept notes stay with /agentdev:iwe-explore.
allowed-tools: Bash(${CLAUDE_SKILL_DIR}/agent-code/*)
---

# Capture an inbox item

`/agentdev:iwe-capture <bug|feature|task> [--from someday/<slug>]`

Capture is the single writer of the three inbox lanes: `data/bugs/`,
`data/features/` at `stage: proposed`, and `data/backlog/`. It is a gate, not a
drafting aid — the thinking happened in the caller, and Capture files the
result only when it is complete and new. It writes graph documents only, never
code.

Run every `iwe` command from the repository root; keys are relative to
`docs/knowledge/` (`data/bugs/<slug>`).

## Steps

1. **Read the contract.** Read `docs/knowledge/SCHEMA.md` — the section for
   the type, `## Fields every type carries`, and the `stage`/`status` table —
   and `data/product.md` `## Authoring rules`. SCHEMA.md is the authority for
   what the document must contain; the bug and feature schemas in `.iwe/schemas/`
   enforce the same body sections, so a document that skips this step fails
   `iwe schema validate` anyway.
2. **Check for a duplicate.** Search with both
   `iwe find --fuzzy "<title words>" -f keys` and
   `iwe find --lexical "<one-line summary>" -f keys`, then read the top hits
   among bugs, features, backlog tasks, plans, and someday ideas. A hit that
   describes the same defect, feature, or work is a duplicate: **STOP**, write
   nothing, and show the matching key with the sentence that matches. Extending
   the existing document is the caller's decision, not this skill's.
3. **Gate on completeness.** Check the supplied content against every required
   frontmatter field and body section for the type:
   - **bug** — an H1 starting `Bug: `, then `## Symptom`, `## Reproduction`,
     `## Root cause`, `## Fix`, and `## Key references` in that order, with
     `path:line — symbol` anchors verified in the current checkout under a
     `Verified anchor points (line numbers as of YYYY-MM-DD):` line. An
     unfixed bug says so in `## Fix`.
   - **feature** — `## Purpose`, `## Behaviour`, `## Edge cases`, and
     `## Open questions` in that order; an Open questions section with nothing
     open says so in one line.
   - **task** — an H1, a body that states the work and why it matters, a
     `priority` of `high`, `medium`, or `low`, and a one-sentence
     `description`.

   Every type needs a one-sentence `description`. If anything is missing,
   **STOP**, write nothing, and list every gap at once — not the first one.
   Never invent content to close a gap; return it to the caller.

4. **Write the document** at `data/bugs/<slug>.md`, `data/features/<slug>.md`,
   or `data/backlog/<slug>.md`, choosing a short kebab slug no existing key
   uses. Frontmatter:
   - `type` — `bug`, `feature`, or `task`.
   - `stage` and `status` derived from the SCHEMA.md table: a new bug omits
     both (open); a feature is `stage: proposed` with `status: draft`; a task
     is `stage: planned` with `priority` and `created: <today>`, and no
     `status`.
   - `description`, `generated: { by: <actor>, at: <ISO 8601 now> }`, and
     `sources` naming every code path, page, and GitHub issue URL the item was
     derived from.

   Sections beyond the required set are allowed after them. Capture never
   files a feature past `proposed`; accepting one is `/agentdev:iwe-plan`'s
   step.

5. **Link it from its hub** with an inclusion link — a markdown link on its own
   line. A task goes under its priority's `## High`, `## Medium`, or `## Low`
   section of `data/backlog.md`; a bug is appended to `data/bugs.md` and a
   feature to `data/features.md`.
6. **Validate.** Run `iwe normalize`, then `iwe schema validate`; both must
   pass before anything else happens.
7. **Close the issue** when the item grew from a GitHub issue, with the bundled
   script, which posts a comment naming the captured document and then closes
   the issue:

   ```bash
   agent-code/close-issue.sh \
     --issue <url-or-ref> --doc docs/knowledge/data/<lane>/<slug>.md
   ```

   The last stdout line is `RESULT=<NAME>`; see `## Closing the issue`.

8. **Report** the key written, its hub section, any `sources`, and the issue
   outcome.

## Promoting a someday idea

`task --from someday/<slug>` turns an idea into a backlog task instead of
writing a fresh document. The idea's body is the task's starting content, so
Step 2 skips the idea itself and Step 3 checks the idea plus whatever the
caller adds — usually the priority. Then:

1. `iwe rename data/someday/<slug> data/backlog/<slug>` moves the document and
   repoints every reference, including the link in `data/someday.md`.
2. Rewrite the frontmatter to the task shape in Step 4, keeping `sources`.
3. Remove the link from `data/someday.md` and add it under the priority section
   of `data/backlog.md`.
4. Continue from Step 6.

## Closing the issue

The captured document replaces the issue: it carries the issue URL under
`sources:`, and the closing comment names the document, so either side reaches
the other. Close only after validation passes — a refused or failed capture
leaves the issue open.

| RESULT            | Exit   | Action                                                                                                                                                        |
| ----------------- | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SUCCESS`         | `0`    | Report the closed `ISSUE_URL` alongside the document.                                                                                                         |
| `ALREADY_CLOSED`  | `5`    | Nothing to do; report that the issue was already closed. The document still links it.                                                                         |
| `ISSUE_NOT_FOUND` | `4`    | **STOP.** Show the resolved `OWNER/REPO#N` and ask for the right reference; the document stays filed.                                                         |
| `GH_UNAVAILABLE`  | `3`    | **Fallback.** Comment and close through a connected GitHub MCP server, if one is present. Otherwise report the document as filed and the issue as still open. |
| `PREFLIGHT_ERROR` | `2`    | **STOP.** Report the blocker verbatim (not a repo, missing document, unparseable reference).                                                                  |
| `SCRIPT_FAILURE`  | `1`    | **STOP.** Report the blocker verbatim; do not retry or work around it.                                                                                        |
| `SIGNAL_*`        | `129`+ | **STOP.** The run was interrupted; report it and whether the issue closed.                                                                                    |

## Boundaries

- Someday ideas, architecture notes, and concept documents are written by
  `/agentdev:iwe-explore`; plans by `/agentdev:iwe-plan`.
- Capture is model-invocable so the `iwe-implementer` rulebook can file a
  defect or deferred task mid-run without stopping for the user. A refusal returns to
  that caller, which keeps the item in its handoff report.
- Capture edits only the new document and its hub links, plus the someday hub
  when promoting.
