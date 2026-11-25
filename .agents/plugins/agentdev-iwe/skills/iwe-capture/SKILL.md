---
name: iwe-capture
description: File a finished inbox item in the IWE graph — a bug or a backlog task — after checking for a duplicate and refusing any document that misses a section or field its document in docs/knowledge/schema/ requires. Use when Explore settles a defect or a task, when Implement finds a defect or work its plan should not absorb, or to promote a someday idea to the backlog with `task --from someday/<slug>`. Plans belong to /agentdev-iwe:iwe-plan; ideas, findings, and guides stay with /agentdev-iwe:iwe-explore.
---

# Capture an inbox item

`/agentdev-iwe:iwe-capture <bug|task> [--from someday/<slug>]`

Capture is the single writer of the two inbox lanes: `data/bugs/` and
`data/backlog/`. It is a gate, not a
drafting aid — the thinking happened in the caller, and Capture files the
result only when it is complete and new. It writes graph documents only, never
code.

Run every `iwe` command from the repository root; keys are relative to
`docs/knowledge/` (`data/bugs/<slug>`).

## Steps

1. **Read the contract.** Read the schema document for the
   type (`docs/knowledge/schema/bugs.md` or
   `docs/knowledge/schema/backlog-tasks.md`) and
   `docs/knowledge/schema/fields-every-type-carries.md`. Read `data/product.md`
   `## Authoring rules`. The schema document is the only definition of what the
   document must contain, and `iwe schema validate` enforces it.
2. **Check for a duplicate.** Search with both
   `iwe find --fuzzy "<title words>" -f keys` and
   `iwe find --lexical "<one-line summary>" -f keys`, then read the top hits
   among bugs, backlog tasks, plans, and someday ideas. A hit that
   describes the same defect or work is a duplicate: **STOP**, write
   nothing, and show the matching key with the sentence that matches. Extending
   the existing document is the caller's decision, not this skill's.
3. **Gate on completeness.** Check the supplied content against every
   frontmatter field and body section that the schema document for the type
   requires, and against each content rule it gives. If anything is missing,
   **STOP**, write nothing, and list every gap at once — not the first one.
   Never invent content to close a gap; return it to the caller.

4. **Write the document** at the path that the schema document gives, with a
   short kebab slug that no existing key uses. Write the frontmatter and the
   body as the schema document defines them, with `created: <today>` on a task.
   File the document at the stage that the schema document gives for Capture. A
   bug that the same change already fixed is closed work. File it at
   `stage: done` in the archive (`docs/knowledge/schema/archive.md`), with its
   `## Fix`. Add `sources` that name each code path and each page that the item
   came from.

5. **Link it from its hub** at its sorted position, as
   `docs/knowledge/schema/hubs.md` defines. A bug filed into the archive gets no
   hub link.

   When the caller says the captured item closes an existing task or bug — a
   fix that settles a pending task, say — set that document to `stage: done`
   with the fields its schema document gives for that stage (for a bug, the
   caller's `## Fix`), and move it to the archive as
   `docs/knowledge/schema/archive.md` gives.

6. **Validate.** Run `iwe normalize`, then `iwe schema validate`; both must
   pass before anything else happens.
7. **Report** the key written, its hub, and any `sources`.

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

## Boundaries

- `/agentdev-iwe:iwe-explore` writes someday ideas, findings, and guides. `/agentdev-iwe:iwe-plan` writes plans.
- Capture is model-invocable so the `iwe-implementer` rulebook can file a
  defect or deferred task mid-run without stopping for the user. A refusal returns to
  that caller, which keeps the item in its handoff report.
- Capture edits only the new document and its hub links, the someday hub when
  promoting, and a task or bug the caller says the new item closes.
