---
name: ship
description: Close or cancel planned work safely — normal shipping requires a zero-CRITICAL Verify report, merges verified behavior into durable specs, and records idempotent graph transitions; cancellation bypasses implementation and release transitions. Also cuts a release when asked. Use when the user says "ship <plan>", "mark <plan> done", "cancel <plan>", "the <feature> work is finished", or "cut release X.Y.Z".
---

# Ship or cancel finished work

Shipping is a state change across the whole graph, not one frontmatter flip.
Specs sync and validate first — a plan is not done while the specs it
invalidated still describe the old behavior. Every operation is restart-safe:
inspect current state before mutating it, preserve an already-correct result,
and continue from the first incomplete operation.

## Steps

1. **Select the operation and inspect current state.** A release cut requested
   without a plan goes to step 8. Otherwise identify the plan, read it in full,
   and select one plan mode before doing anything else:
   - **Cancellation** only when the user explicitly abandons the plan. Go to
     step 2.
   - **Normal shipping** records implemented work. Go to step 3.

   Read the current plan frontmatter and its exact hub section, plus the linked
   feature or bug, every entry in `## Spec changes`,
   `data/releases/unreleased.md`, and today's `data/log.md` group. Record which
   intended results already exist. Do not assume a prior Ship invocation
   finished or failed atomically.

2. **Cancel without shipping.** Do not verify implementation, synchronize
   specs, mark a feature implemented or bug fixed, or add a release entry. If
   needed, set the plan to `stage: cancelled` and move its one existing hub
   link to `## Cancelled`; do not duplicate the link if either change already
   happened. Run `iwe normalize` and `iwe schema validate`, commit the
   cancellation, report it, and stop.
3. **Run Verify for normal shipping.** Invoke the report-only workflow in
   `.claude/skills/verify/SKILL.md` for the selected plan, including its named
   verification commands and evidence checks. Preserve Verify's requirement
   for user approval before commands with effects beyond the working tree. If
   the report contains any CRITICAL finding, make no shipping state transition,
   report every blocker, and stop; there is no CRITICAL override. Continue only
   with a zero-CRITICAL verdict.
4. **Merge every planned durable spec.** Use the plan's complete
   `## Spec changes` list and Verify's implementation evidence, not plan prose
   alone. The plan's recorded form — `None`, a concise normative outcome, or a
   fenced `ADDED` / `MODIFIED` / `REMOVED` delta — is reviewed intent, and
   Verify's zero-CRITICAL report is the evidence that the intent was built.
   Merge only what both support. This is a careful reading, not a patch
   application: nothing here parses the delta, applies operations in a fixed
   order, or resolves conflicts mechanically, so never describe or perform it
   as though it did. For each entry:
   - Read the current spec before editing. Merge the verified changed behavior
     into it while preserving unaffected requirements, scenarios, ordering,
     and still-accurate explanatory content.
   - If the recorded intent and the verified implementation disagree, stop.
     Make no lifecycle transition, do not rewrite the plan's intent from the
     code, and report that the plan needs revision — the reviewed contract is
     the thing worth keeping, and silently restating it from the implementation
     destroys the only record of what was agreed.
   - If the spec does not exist, create it in Requirement / Scenario format,
     add one inclusion link to `data/spec.md`, and replace the plan's
     back-ticked name with a real link. Check for each result before adding it.
   - Retire a whole spec only when the plan explicitly requires retirement and
     Verify confirms the final represented behavior was removed. Use
     `iwe delete <key>` so references are repaired; never leave an empty or
     orphaned spec or hand-delete its file.
5. **Verify the complete spec merge before lifecycle changes.** Re-read every
   spec named by the plan and compare each affected requirement and scenario
   with the zero-CRITICAL implementation evidence. Then walk the plan's
   recorded intent a second time and account for **every** part of it: each
   `ADDED`, `MODIFIED`, and `REMOVED` operation, each post-change requirement,
   and each scenario inside them, plus every normative outcome a concise entry
   states. A merge that lands most of the delta is a failed merge, not a
   partial success — an operation you cannot find in the durable spec is a
   mismatch to report, not a detail to tidy up later. Confirm too that content
   the delta never mentioned survived untouched. Run `iwe normalize`, then
   `iwe schema validate`. If any planned update is incomplete, disagrees with
   verified behavior, has broken references, or fails validation, report the
   mismatch and stop without marking the plan, feature, or bug complete.
6. **Apply graph transitions idempotently.** Before each mutation, re-inspect
   that document and hub or release section; skip a result that is already
   correct and never add a second copy.
   - Set the plan to `stage: done` with `completed: <today>`, then ensure its
     single inclusion link is under `## Done` rather than `## Active`.
   - Set the linked feature to `stage: implemented`, or the linked bug to
     `stage: done`. If the plan requires a new feature, first confirm none
     exists, create it from the verified outcome and plan Context, and add one
     inclusion link to `data/features.md`.
   - Ensure `data/releases/unreleased.md` contains exactly one inclusion link
     to the feature under `## Added`, or to the bug under `## Fixed`; release
     pages link feature and bug docs, never plans.
   - Ensure today's `data/log.md` group contains exactly one state-change
     bullet for each transition. Create the group only if absent and never
     duplicate a matching prior bullet. For example:
     <!-- validate_skills: ignore-cross-reference-start -->
     `- **Update**: [Focus sessions](features/focus-sessions.md) implemented.`
     <!-- validate_skills: ignore-cross-reference-end -->
7. **Validate, commit, and report.** Run `iwe normalize`, then
   `iwe schema validate` — both must pass. Re-inspect the final plan, hub,
   feature or bug, unreleased page, log, and all planned specs before
   committing. Report which valid results were preserved from an earlier
   attempt and which operations this invocation completed. If the plan's
   milestone aggregator lists it, check whether it was the last child and tell
   the user when the milestone is complete.
8. **Cut a release only when asked.** Inspect `data/releases.md`, the current
   unreleased page, and any page for the requested version before every
   mutation. Refuse a conflicting existing version; otherwise preserve each
   already-correct result and perform only the missing operations:
   - `iwe rename data/releases/unreleased data/releases/<X.Y.Z>`
   - `iwe update -k data/releases/<X.Y.Z> --set version=<X.Y.Z> --set date=<today> --set stage=released`
   - Recreate `data/releases/unreleased.md` with version/stage `unreleased` and
     empty `## Added` / `## Fixed` sections.
   - Keep one `Unreleased` link on top of `data/releases.md` and one new-version
     link immediately below it, newest first.
   - Add one linked release-cut bullet to today's log group.

   Run `iwe normalize` and `iwe schema validate`, re-inspect the release graph,
   and commit with a message describing the release cut.

## Rules

- Cancellation and normal shipping are separate paths; cancellation never
  inherits normal shipping's verification, spec, feature/bug, or release work.
- Normal shipping never proceeds past a Verify report containing a CRITICAL.
- Specs sync and validate before lifecycle stage changes, never after them.
- Derive durable specs from verified shipped behavior and preserve unaffected
  content; never overwrite a whole spec from plan prose.
- Reviewed intent and verified behavior must agree before anything merges. When
  they don't, the plan goes back for revision — Ship never edits the intent to
  match the code, and never presents its merge as a deterministic application
  of the delta.
- Inspect before every mutation so rerunning Ship cannot duplicate plan-hub,
  feature/bug, unreleased, release-hub, or log entries.
- Never invent verification results or mark durable state complete after a
  mismatch or validation failure.
