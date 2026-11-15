---
name: iwe-capture
description: File a finished inbox item in the IWE graph. The item is a bug, a proposed feature, or a backlog task. First, look for a duplicate. Do not accept a document that does not have a section or field that its document in docs/knowledge/schema/ requires. Use when Explore settles a defect, feature, or task, when Implement finds a defect or work its plan should not absorb, or to promote a someday idea with `task --from someday/<slug>`. Plans belong to /agentdev:iwe-plan; ideas, findings, guides, and product-vision documents stay with /agentdev:iwe-explore.
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

1. **Read the contract.** Read the schema document for the
   type (`docs/knowledge/schema/bugs.md`, `docs/knowledge/schema/features.md`, or
   `docs/knowledge/schema/backlog-tasks.md`) and
   `docs/knowledge/schema/fields-every-type-carries.md`. Read `data/product.md`
   `## Authoring rules`. The schema document is the only definition of what the
   document must contain, and `iwe schema validate` enforces it.
2. **Check for a duplicate.** Search with both
   `iwe find --fuzzy "<title words>" -f keys` and
   `iwe find --lexical "<one-line summary>" -f keys`, then read the top hits
   among bugs, features, backlog tasks, plans, and someday ideas. A hit that
   describes the same defect, feature, or work is a duplicate: **STOP**, write
   nothing, and show the matching key with the sentence that matches. Extending
   the existing document is the caller's decision, not this skill's.
3. **Check for completeness.** Use the schema document for the type.
   Compare the supplied content with each frontmatter field and each body
   section that the schema document requires. Then compare it with each
   content rule that the schema document gives. If something is missing,
   **STOP** and write nothing.
   List all the gaps, not only the first gap. Never invent content to close a
   gap; return it to the caller.

4. **Write the document** at the path that the section gives, with a short kebab
   slug that no existing key uses. Write the frontmatter and the body as the
   section defines them, with `created: <today>` on a task. File the document at
   the stage that the section gives for Capture. A bug that the same change
   already fixed is closed work: file it at `stage: done` in the archive
   (`docs/knowledge/schema/archive.md`), with its `## Fix`. Add `sources` that
   name each code path, each page, and each GitHub issue URL that the item came
   from. Capture files a feature only at `proposed`. `/agentdev:iwe-plan`
   accepts a feature.

5. **Link it from its hub** at its sorted position, as
   `docs/knowledge/schema/hubs.md` defines. A bug filed into the archive gets no
   hub link.

   The caller can say that the captured item closes an existing task or bug.
   Then close that document as `done`. Set the fields that its section gives for
   that stage. For a bug, write the `## Fix` that the caller gives. Move the
   document to the archive as `docs/knowledge/schema/archive.md` gives.

6. **Validate.** Run `iwe normalize`, then `iwe schema validate`; both must
   pass before anything else happens.
7. **Close the issue** when the item grew from a GitHub issue, with the bundled
   script, which posts a comment naming the captured document and then closes
   the issue:

   ```bash
   agent-code/close-issue.py \
     --issue <url-or-ref> --doc docs/knowledge/data/<lane>/<slug>.md
   ```

   The last stdout line is `RESULT=<NAME>`; see `## Closing the issue`.

8. **Report** the key written, its hub, any `sources`, and the issue
   outcome.

## Promoting a someday idea

`task --from someday/<slug>` turns an idea into a backlog task instead of
writing a fresh document. The idea's body is the task's starting content, so
Step 2 skips the idea itself and Step 3 checks the idea plus whatever the
caller adds — usually the priority. Then:

1. `iwe rename data/someday/<slug> data/backlog/<slug>` moves the document and
   repoints every reference, including the link in `data/someday.md`.
2. Rewrite the frontmatter to the task shape in Step 4, keeping `sources`.
3. Remove the link from `data/someday.md`, since the document left that hub,
   and add it at its sorted position in `data/backlog.md`.
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

- `/agentdev:iwe-explore` writes someday ideas, findings, guides, and
  product-vision documents. `/agentdev:iwe-plan` writes plans.
- Capture is model-invocable so the `iwe-implementer` rulebook can file a
  defect or deferred task mid-run without stopping for the user. A refusal returns to
  that caller, which keeps the item in its handoff report.
- Capture edits only the new document and its hub links, the someday hub when
  promoting, and a task or bug the caller says the new item closes.
