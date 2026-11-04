# Observing the adversarial review

Scratch branch for the two observation tasks of
`data/plans/20261102-adversarial-review` (Task 5 and Task 6). Never merge it.
It sits on top of `iwe/adversarial-review/iter-1-impl` and adds only a fixture:

- `scripts/slug_guard.py` — `is_safe_slug("a/b")` returns `True`.
- `docs/knowledge/data/plans/20261104-slug-guard-fixture.md` — requires
  `is_safe_slug` to return False for any slug containing `/` or `..`
  (requirement "Slugs cannot leave the plans directory", scenario "A nested
  slug is refused"). The code defeats both.

Run each task once on Claude Code and once on OpenCode, each in a fresh session
on a fresh checkout of this branch. OpenCode uses `openai/gpt-6.1-sol` as the
model and `openai/gpt-6-luna` as `small_model`.

## Before every run

1. The session's agentdev catalog must come from this checkout, so it has
   `iwe-adversarial-review` and `iwe-adversarial-reviewer`. Check the skill is
   listed before starting; a catalog from another checkout or an older image
   does not have it.
2. Record the baseline: `git rev-parse HEAD` and an empty
   `git status --porcelain`.

## Task 5: a code review

Request, as the session's first message:

```text
/agentdev:iwe-adversarial-review data/plans/20261104-slug-guard-fixture code
```

Pass when every one holds:

1. `iwe-adversarial-review` is loaded once.
2. Exactly one `iwe-adversarial-reviewer` is dispatched (`Agent` on Claude
   Code, `task` on OpenCode).
3. Its prompt carries only the plan key, the target `code`, and approvals —
   no conversation summary and no claim that anything passed.
4. The reviewer makes no `Edit` or `Write` call, dispatches no agent, and runs
   no command that writes to the checkout, commits, or pushes.
5. The final message re-posts the report verbatim. It leads with
   `Adversarial review: data/plans/20261104-slug-guard-fixture — code`, and a
   finding's **Defeats** names "Slugs cannot leave the plans directory" or "A
   nested slug is refused", with `scripts/slug_guard.py:<line>` or a command
   result as **Evidence**, or the label "unverified".
6. Afterwards `git rev-parse HEAD` equals the baseline and
   `git status --porcelain` is empty.

Optional, for the plan target: run
`/agentdev:iwe-adversarial-review data/plans/20261104-slug-guard-fixture plan`
the same way. It should report a weakness of the plan itself and change
nothing.

## Task 6: planning leaves the review alone

Request, as the session's first message:

```text
/agentdev:iwe-plan Plan a change so that is_safe_slug in scripts/slug_guard.py also rejects backslashes.
```

Answer its questions briefly and let create mode finish.

Pass when every one holds, in the session and in every subagent it dispatches:

1. No skill call loads `iwe-adversarial-review`.
2. No `Agent` or `task` call dispatches `iwe-adversarial-reviewer`.
3. The new plan passes `iwe schema validate`.

A plan task that only names `/agentdev:iwe-adversarial-review <plan> code` is
allowed; running it is a failure.

## Closing the boxes

Tick each box on `iwe/adversarial-review/iter-1-impl`, not here, with an
evidence line naming the harness, the models, the session or exported
transcript, the baseline commit of this branch, and the result of each pass
criterion.
