# Plans

A plan is committed work that a later session can do with no other context. A
plan is an implementation plan, a migration, or a design proposal. One plan has
one topic: work that needs two unrelated verification stories is two plans.

- Path: `data/plans/YYYYMMDD-<slug>.md`. The date is the day of creation.
- Hub: `data/plans.md`.

``` yaml
---
type: plan # required
stage: done # done | cancelled — absent while the plan is active
created: 2026-07-01 # required, YYYY-MM-DD
completed: 2026-07-18 # required when stage: done
release: # required while the plan is active: internal, or the keys below
- bugs/timer-drifts-on-sleep
---
```

- `release` lists the `bugs/` keys of the bugs that Ship marks done when the
  plan ships. The value is `internal` when the plan closes no bug. The field
  feeds no release page: the release cut writes the page from the
  `## Acceptance` scenarios of the archived plans. A shipped plan can also list
  `features/` keys of the retired feature type.
- `sources` lists the GitHub issue that the plan grew from, if there is one.
- `rank` is optional. See `schema/build-order.md`.

| Stage        | Meaning                | Set by | Other fields               |
| ------------ | ---------------------- | ------ | -------------------------- |
| (no `stage`) | Active                 | Plan   | `release` is required      |
| `done`       | The work shipped       | Ship   | `completed` set, no `rank` |
| `cancelled`  | The work was abandoned | Ship   | No `rank`                  |

A done or cancelled plan is in the archive. See `schema/archive.md`.

Body, in this order. A plan leaves out a section that has no content, with two
exceptions: `## Acceptance` and `## Verification` are always there.

- `## Context` — why the work is done now. It links the bug, or backlog task
  that started the work, each document in `release`, and the GitHub issue that
  the plan grew from.
- `## Approach` — the shape of the solution, in a few sentences. A rejected
  option goes in an ADR.
- `## Implementation Steps` — `### Task N: <name>` blocks. Each block has a
  `**Files:**` line (`Create:` and `Modify:`) and `- [ ]` checkboxes.
  - A task that only a later event can close has a
    `**Closed by:** <who or what event>` line.
  - Wording that the user approved is in a fenced block, word for word.
  - A checkbox has no evidence line. The commit that ticks a checkbox ticks only
    that checkbox. Its message ends with the completion evidence block. The
    block has a line `---`, a line `completion evidence:`, and a short note in
    free form that tells how the agent checked the work. Git trailer lines at
    the end of the message are not part of the note. A plan does not specify the
    form of the note, and nobody examines it.
- `## Acceptance` — one `### Scenario:` block for each behaviour that the plan
  adds, changes, or removes. A block has a `- **WHEN**` line and a `- **THEN**`
  line. Then it has one of two lines. `- **Test:**` names the test that proves
  the scenario, as `path::test_name`. `- **Checked at ship:**` is for behaviour
  that no test can reach. It names the rulebook or the file that the verifier
  reads.
  - A plan that changes no behaviour writes `None — no behavioral change`.
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
- `## Key references` — a list of code anchors, each with a short note. See
  `schema/code-anchors.md`.
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
