# Batch 6 — durable knowledge held only in closed documents

## docs/knowledge/data/plans/20261102-rereview-after-metadata-edit.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: ai-review-refresh
- unique items:
  - [rationale] A review's input is the head commit plus the title and
    description, because the metadata gate reads them once when a responder run
    starts; that is why only runs started after the latest edit (and the reviews
    they submit) cover a head. The rule applies to every AI review, not only
    metadata-gate stops, because a full review also runs the gate, and it cannot
    loop because each extra review needs an edit. — already partly in:
    `spec/ai-review-refresh.md` (requirement text carrying "submitted after the
    latest title or description edit by a run that started after it" states the
    behaviour, not the reason)
  - [rationale] Rejected: a hash of title and description stored in the gate's
    review body (precise on a revert, but needs a review-body format, a
    computation in `pr-review`, and a text-normalization rule; timestamps change
    only `request-review.py` and cost at worst one extra review). Rejected: an
    override argument on `request-review.py` (moves the per-head guard to the
    caller's judgment). — already partly in: nowhere
  - [constraint] The edit cutoff is read from GitHub in one GraphQL query:
    `PullRequest.lastEditedAt` for the description and the newest
    `RENAMED_TITLE_EVENT` for the title; the design assumes GitHub records no
    edit when the text is unchanged, and accepts one extra review if it does. —
    already partly in: nowhere (still in
    `.agents/plugins/agentdev/skills/pr-request-ai-review/agent-code/request-review.py`)
  - [non-goal] A title or description edit never starts a review by itself
    (`pull_request: edited` is not a trigger); requesting stays explicit. No
    review is marked as a metadata-gate stop. — already partly in: nowhere
- conflicts: none

## docs/knowledge/data/plans/20261103-backfill-ship-reviews.md

- verdict: NOTHING DURABLE
- owning spec: iwe-workflow-skills, pre-commit-gate
- conflicts: none (cancelled; the backfill flag and the "require
  `## Ship review` on every done plan" rule were never built —
  `spec/pre-commit-gate.md` checks the section only where it exists)

## docs/knowledge/data/plans/20261103-explore-evidence-gate.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [rationale] The evidence gate sits at the top of Explore's stance, before
    any proposal is formed; extending the existing `Evidence before argument`
    interview rule was rejected because that rule runs only once open questions
    exist, which is after an over-scoped proposal has been written. — already
    partly in: `spec/iwe-workflow-skills.md` (Explore requirement and the
    scenario beginning "WHEN Explore is about to propose a change to the system"
    hold the behaviour only)
- conflicts: none

## docs/knowledge/data/plans/20261103-nested-dispatch-depth.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: nested-agent-dispatch (OpenCode half:
  devcontainer-opencode-policy)
- unique items:
  - [rationale] Claude Code's depth is set in the compose `environment:` blocks
    because the repository owner wanted the value stated where the container is
    defined; rejected: writing `env.CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH` into
    Claude Code's `settings.json` from `agentdev-runtime state agent-policy`. —
    already partly in: nowhere
    (`architecture/nested-subagent-dispatch.md#how-each-harness-behaves` states
    only where the value is set)
  - [constraint] An image-build write of `~/.claude/settings.json` (Ansible
    `agentic_tools` role) cannot carry the setting: the home is a volume, which
    hides the image's file once the volume holds one. — already partly in:
    `architecture/devcontainer-home-volume.md` (the volume, not this
    consequence)
  - [non-goal] The depth is not raised outside the devcontainer and the
    standalone runtime, for example on a native macOS host. — already partly in:
    nowhere
- conflicts: none

## docs/knowledge/data/plans/20261103-remove-iwe-workflow-e2e.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [rationale] The workflow e2e suite was deleted rather than kept unrun,
    because unrun tests rot and still read as coverage. — already partly in:
    `architecture/skill-rehearsal-runs.md` ("the repository writes no end-to-end
    test that drives an agent session against a live model" — the rule, not the
    reason)
  - [non-goal] The ban names the agentdev workflow skills only: the self-improve
    plugin's `smoke`, `pty`, and `auto_memory` live-session tests are kept by
    the maintainer's decision, so "no live-model test at all" was rejected. —
    already partly in: `architecture/self-improve-runtime.md` (says the smoke
    suite exists, not that it is exempt)
- conflicts: `architecture/skill-rehearsal-runs.md` says "the repository writes
  no end-to-end test that drives an agent session against a live model", while
  this plan says "The self-improve plugin's `smoke`, `pty`, and `auto_memory`
  tests also drive live sessions; the maintainer kept them" (the root `Makefile`
  still has `smoke` and `wake` targets). The note's sentence is broader than the
  decision.

## docs/knowledge/data/plans/20261103-rereview-after-changes-requested.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: ai-review-refresh
- unique items:
  - [rationale] Rejected: requesting a re-review on every push while no AI
    approval exists — it would also re-request after a `COMMENTED`-only review,
    which cannot produce an approval (GitHub accepts only `COMMENT` on the
    reviewer's own pull request), and adds a review per push for no gain. An AI
    reviewer with only `COMMENTED` reviews is therefore left to the scope test.
    — already partly in: `spec/ai-review-refresh.md` (defines "newest verdict"
    as the latest `APPROVED` or `CHANGES_REQUESTED` review);
    `architecture/ai-review-event-selection.md` (why `COMMENT` exists)
  - [non-goal] A human reviewer's change request never triggers an AI re-review;
    lifting it is that reviewer's call. — already partly in: nowhere
- conflicts: none

## docs/knowledge/data/plans/20261103-ship-records-gate.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: pre-commit-gate
- unique items:
  - [constraint] The "done bug has `## Fix`" rule is a CLI
    (`scripts/check-ship-records.py`) and not a schema rule because `iwe`
    (observed on 0.29.3) accepts conditionals in a document schema only inside
    `frontmatter`; a document-level `if`/`then` or `anyOf` fails with "unknown
    keyword", and requiring `## Fix` on every bug is wrong because open bugs
    have none. The repository now pins `iwe-v0.33.0`
    (`ansible/roles/dev_tools/defaults/main.yml`), so the tool fact needs
    re-checking before it is recorded. — already partly in: nowhere
  - [rationale] The owner reversed the earlier decision that nothing mechanical
    enforces a done bug's `## Fix`; the check is a CLI under test (tests run it
    on made-up documents) rather than a pytest file like the `plan-checkboxes`
    hook. — already partly in: nowhere
  - [non-goal] The CLI lives in `scripts/` and is not shipped to template
    consumers; it checks section shape only, and `iwe-ship-reviewer` judges
    whether a `## Fix` describes the shipped fix. — already partly in: nowhere
- conflicts: none

## docs/knowledge/data/plans/20261103-ship-review.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [rationale] The review-and-fix loop belongs to `/agentdev:iwe-ship` (and to
    Plan revise mode answering a Ship blocker report, because
    `/agentdev:iwe-ship` is explicit-only); `iwe-shipper` dispatching
    `iwe-ship-reviewer` as its last step was rejected by the repository owner.
    `iwe-ship-reviewer` commits its own `## Ship review` because it is that
    section's only writer. — already partly in: `spec/iwe-workflow-skills.md`
    (the requirement naming `iwe-ship-reviewer`, `fix`, and "at most 3 fix
    rounds" holds the behaviour; no architecture note covers the Ship review)
- conflicts: none

## docs/knowledge/data/plans/20261107-coder-template-history-to-template.md

- verdict: NOTHING DURABLE
- owning spec: coder-ide-baseline
- conflicts: none (a one-time move of finished documents; its copy rules
  describe that migration only)

## docs/knowledge/data/plans/20261107-drop-claude-task-responder.md

- verdict: ALL ALREADY HELD
- owning spec: ai-review-gate
- conflicts: this plan's `## Context` says "Reviews are requested by toggling
  the pull request author's assignment"; `spec/ai-review-refresh.md` and
  `architecture/label-review-triggers.md` now say "a `request-ai-review` label
  is the one way to request a review".
  `architecture/pull-request-only-responder.md#context` repeats the same
  superseded sentence ("Reviews are requested by assignment").

## docs/knowledge/data/plans/20261107-remove-iwe-coordinators.md

- verdict: ALL ALREADY HELD
- owning spec: iwe-workflow-skills
- conflicts: none in this plan. Related stale text:
  `architecture/nested-subagent-dispatch.md` still says "only the user's session
  or a coordinator dispatches", against
  `architecture/explicit-only-workflow-agents.md` "No coordinator runs workflows
  across plans or sessions."

## docs/knowledge/data/plans/20261108-drop-okf-provenance-fields.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills (consumer delivery: template-consumption)
- unique items:
  - [rationale] `generated.at` changed on every edit, so two branches touching
    one document collided in its frontmatter even when their content did not;
    that merge cost, plus review noise and upkeep, is why the fields were
    dropped. — already partly in: `spec/iwe-workflow-skills.md` (requirement
    "Workflow improvements preserve the IWE and OKF model" gives only "source
    control records when and by whom");
    `architecture/kb-conflict-free-layout.md` (names `status` as "the one
    divergence" and does not mention `generated` or `verified`)
  - [constraint] `okf.yaml` accepts undeclared fields, so removing a field's
    declaration does not keep it out of documents; the ban therefore has to be
    the `banned-frontmatter-keys` check. One check covers `status`, `generated`,
    and `verified`; a second near-copy test was rejected. — already partly in:
    nowhere
  - [non-goal] `sources` stays: it records what a document derives from and does
    not change on every edit. `iwe-bootstrap` does not install the check,
    because its spec bars it from adding pre-commit configuration. — already
    partly in: `spec/template-consumption.md` ("A repository initialized by
    `iwe-bootstrap` alone gets no such check, because bootstrap adds no hooks")
- conflicts: `architecture/kb-conflict-free-layout.md` says "The one divergence
  is `status`", while `spec/iwe-workflow-skills.md` bans `status`, `generated`,
  and `verified`.

## docs/knowledge/data/plans/20261108-label-review-triggers.md

- verdict: ALL ALREADY HELD
- owning spec: ai-review-gate, ai-review-refresh
- unique items: none; one assumption is not in `spec/` or `architecture/` —
  "Adopting repositories create both labels; the consumption guide says so" —
  and belongs in template-consumption if it is to be a requirement.
- conflicts: none

## docs/knowledge/data/plans/20261108-line-free-anchors.md

- verdict: ALL ALREADY HELD
- owning spec: line-free-anchors
- conflicts: this plan says "every anchor anywhere in an open bug or backlog
  item ... must resolve" and "All existing references are rewritten — closed
  documents included — so the gate scans the whole tree with no exemption"; both
  agree with `architecture/line-free-anchors.md`. none.

## docs/knowledge/data/plans/20261109-evidence-without-commit-ids.md

- verdict: ALL ALREADY HELD
- owning spec: plan-checkbox-evidence
- conflicts: none

## docs/knowledge/data/plans/20261109-one-observation-per-checkbox.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: plan-checkbox-evidence
- unique items:
  - [rationale] Checkbox granularity is a planning rule the planner owns;
    extending the Durable Knowledge Auditor's plan scope to flag bundled
    checkboxes was rejected because that audit asks one question
    (durable-knowledge residue) and a second gate would widen it. — already
    partly in: `spec/plan-checkbox-evidence.md` (the requirement stating "one
    checkbox is one observation" holds the behaviour)
- conflicts: none

## docs/knowledge/data/plans/20261109-planner-spec-redundancy-check.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [rationale] Only the planner can keep redundancy out of a spec, because Ship
    preserves every requirement and scenario a plan's `## Spec changes` does not
    touch; having Verify or `iwe-revision-evaluator` flag a restated rule was
    rejected because the check belongs where the delta is written and a Verify
    finding would arrive after implementation. — already partly in:
    `spec/iwe-workflow-skills.md` (scenarios "Plan names that requirement
    instead of restating the rule" and "A modification makes a scenario
    redundant" hold the behaviour)
  - [non-goal] A spec duplicating the behaviour its code or rulebook carries is
    intended and is not the redundancy this rule targets; statements of how the
    catalog is wired keep their copy in the spec. — already partly in: nowhere
- conflicts: none

## docs/knowledge/data/bugs/ai-rereview-comment-keeps-changes-requested.md

- verdict: ALL ALREADY HELD
- owning spec: ai-review-gate
- conflicts: none (`architecture/ai-review-event-selection.md` and
  `architecture/actions-approval-permission.md` hold the GitHub rule;
  `spec/ai-review-gate.md` holds the scenario "stays blocked until a later
  review from the same reviewer approves it")

## docs/knowledge/data/bugs/ai-review-gate-self-waivable.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: ai-review-gate
- unique items:
  - [rationale] Rejected: letting a writer waive the gate by checking
    `getCollaboratorPermissionLevel` on whoever set the skip signal. It keeps
    the waiver and only narrows who holds it, so a writer could merge unreviewed
    work with no trace in the branch-protection record; ruleset bypass expresses
    the same intent through a permission GitHub already audits. — already partly
    in: `spec/ai-review-gate.md` ("The label SHALL NOT waive the
    `ai-review-present` gate ... only a user with ruleset bypass can merge it" —
    the behaviour and the self-waive reason, not this rejected alternative)
- conflicts: this bug says "The marker, renamed `[ci:skip-ai-review]` ... now
  reaches only `wantsReview`"; `architecture/label-review-triggers.md` says "a
  `block-ai-reviews` label replaces the `[ci:skip-ai-review]` body marker". The
  marker no longer exists; the principle carried over to the label.

## docs/knowledge/data/bugs/body-shape-schemas-shared-scratch.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: a line in `AGENTS.md` `### Tests`, next to the
  `/tmp` scratch rule, rather than a spec)
- unique items:
  - [constraint] `/tmp` is shared by every worktree and session in the
    container, so a test fixture's scratch directory under `/tmp/agentdev-tests`
    must be unique per run (a `uuid4` suffix, removed on teardown); a fixed path
    lets concurrent runs read each other's mutations or a tree another run just
    deleted. — already partly in: nowhere in `spec/` or `architecture/`
    (`AGENTS.md` states only that tests write under `/tmp`; the fixtures in
    `docs/knowledge/tests/` carry the pattern)
- conflicts: none; no spec requirement or scenario states the fixed behaviour.

## docs/knowledge/data/bugs/cbm-cache-under-foreign-owned-checkout.md

- verdict: DEAD (subject removed)
- owning spec: NONE
- conflicts: none (`architecture/no-code-graph.md`: codebase-memory-mcp was
  removed; only `agentdev_runtime/cbm_purge.py` remains, which clears what it
  left)

## docs/knowledge/data/bugs/cbm-codex-hooks-block-foreign-tables.md

- verdict: DEAD (subject removed)
- owning spec: NONE
- conflicts: none (both codebase-memory-mcp and Codex support are removed)

## docs/knowledge/data/bugs/cbm-pin-staging-races-under-xdist.md

- verdict: DEAD (subject removed)
- owning spec: NONE
- conflicts: none (`stage_pinned_cbm` no longer exists)

## docs/knowledge/data/bugs/cbm-start-failure-latches-degraded.md

- verdict: DEAD (subject removed)
- owning spec: NONE
- conflicts: none

## docs/knowledge/data/bugs/ci-publishes-images-before-acceptance.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: image-pinning
- unique items:
  - [rationale] Tags are promoted only after acceptance because neither
    assumption behind "publish, then test" holds: `main`'s rebuild is not
    equivalent to the pull request's tested image (it rebuilds from a clean
    `ubuntu:24.04` with unpinned apt packages and upstream repositories that
    change between runs), and runs on `main` do not finish in order (frequent
    Renovate automerges used to cancel an in-progress run). — already partly in:
    `spec/image-pinning.md` (requirement "published tags name only tested
    images" and its four scenarios hold the behaviour, including "Primary checks
    runs on `main` SHALL NOT cancel one another")
- conflicts: none

## docs/knowledge/data/bugs/claude-json-symlink-replaced.md

- verdict: ALL ALREADY HELD
- owning spec: agentdev-runtime-images (rationale in
  `architecture/devcontainer-home-volume.md`,
  `architecture/agent-auth-persistence.md`)
- conflicts: none (the root cause was never confirmed; the notes hold
  "`~/.claude.json` is a regular file on the home volume" and the replacement of
  a leftover link, and `agent_state.py::unlink_claude_json` still exists)

## docs/knowledge/data/bugs/cloud-startup-dockerd-ready-race.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: a cloud-session-host spec, built from
  `architecture/cloud-session-host-toolchain.md`)
- unique items:
  - [behaviour] `.claude/startup.py::start_docker` counts an exited `dockerd` as
    a failure only when the daemon still does not answer; a daemon that is ready
    when its exit is seen counts as started. Covered by
    `scripts/tests/test_cloud_startup.py::test_dockerd_that_exits_once_ready_counts_as_started`,
    stated in no spec. — already partly in:
    `architecture/cloud-session-host-toolchain.md` (says startup "starts
    `dockerd` ... when it does not answer", not the exit rule)
- conflicts: none

## docs/knowledge/data/bugs/coder-askpass-push-hang.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: devcontainer-git-credentials (also coder-ide-baseline)
- unique items:
  - [constraint] With no github.com credential helper, git falls back to
    `GIT_ASKPASS`, which Coder sets to its agent binary; that binary does not
    return when it has no GitHub credential to give, so an HTTPS push hangs.
    This is why the helper must be configured from the agent-start command,
    where `GITHUB_TOKEN` exists. — already partly in:
    `spec/devcontainer-git-credentials.md` (requirement "HTTPS git uses the gh
    login": "so git never waits at an interactive credential prompt");
    `spec/coder-ide-baseline.md` (post-start runs before Coder injects its agent
    and SHALL NOT depend on `GITHUB_TOKEN`, `CODER_*`, `GIT_ASKPASS`)
- conflicts: this bug says "`.devcontainer/scripts/coder-agent-start.sh` runs
  `setup-gh-credential-helper.sh`"; `spec/devcontainer-git-credentials.md` says
  "`agentdev-runtime coder start`, which the Coder template's `coder_script`
  runs on every agent start", and `.devcontainer/scripts/` no longer exists.

## docs/knowledge/data/bugs/coder-docker-storage-accumulates.md

- verdict: ALL ALREADY HELD
- owning spec: devcontainer-docker-storage
- conflicts: none (hourly pass, the 72-hour creation-time cutoff, "SHALL leave
  cache that a kept image shares", disposable-name volumes only, and the
  scenario "a login volume is unused" are all in the spec; the unsettled
  BuildKit-timer hypothesis is not durable)

## docs/knowledge/data/bugs/codex-catalog-agents-not-loaded.md

- verdict: DEAD (subject removed)
- owning spec: NONE
- conflicts: this bug says "The contract is in [Catalog
  lifecycle](../spec/catalog-lifecycle.md)" for `bin/install-codex-agents.py`;
  `architecture/supported-harnesses.md` records Codex support as removed.

## docs/knowledge/data/bugs/codex-skill-dir-unresolved.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: catalog-lifecycle (or opencode-catalog-bridge, which already has
  the scenario "a relative `agent-code/` step resolves inside that skill")
- unique items:
  - [rationale] A skill's bundled code directory is named `agent-code/` rather
    than `scripts/` so that a path misresolved against the working directory
    cannot run a consuming repository's own `scripts/`; skills reference it
    skill-relative because `${CLAUDE_SKILL_DIR}` is a Claude Code text
    substitution other harnesses do not resolve, so it survives only in the
    Claude-only `allowed-tools` field. — already partly in: `.agents/AGENTS.md`
    (the rule, without the naming reason);
    `architecture/catalog-script-language.md` (uses the directory name, no
    reason)
- conflicts: none (the Codex half is dead; the `agent-code/` convention is live)

## docs/knowledge/data/bugs/command-result-evidence-ambiguous.md

- verdict: ALL ALREADY HELD
- owning spec: plan-checkbox-evidence
- conflicts: this bug's `## Fix` says "A check and its result count as evidence
  only together with the commit that holds the change they check" and "A task's
  code is committed first. The checkbox flip and its evidence line, naming that
  commit, follow in a commit of their own";
  `architecture/evidence-without-commit-ids.md` says "A commit id on its own is
  not evidence" and "a task's code, its checkbox flip, and its evidence line
  land in one commit". The bug's fix is superseded; its lasting finding
  (Verify's judgment flips when a line names nothing it can repeat) is in that
  note's `## Alternatives rejected`.

## docs/knowledge/data/bugs/devcontainer-dbus-autolaunch-leak.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: agentdev-runtime-images (standalone half:
  standalone-opencode-runtime)
- unique items:
  - [constraint] `gh` looks its token up in the Secret Service on every call;
    with no session bus address in its environment the D-Bus client library
    autolaunches a new bus through `dbus-launch` and the lookup activates a
    fresh `gnome-keyring-daemon`, and neither exits. Every process — supervised
    programs, `docker exec` shells, the VS Code server, agent sessions — must
    therefore inherit one fixed `DBUS_SESSION_BUS_ADDRESS` naming the bus the
    runtime's keyring serves; publishing a random address in a file only some
    scripts source is not enough. — already partly in: nowhere
    (`spec/agentdev-runtime-images.md` says only that the image starts D-Bus and
    the keyring)
  - [behaviour] Both images set
    `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/agentdev/xdg/bus` as an image
    `ENV`, and a `gh` call from the `agent` or `root` shell adds no bus or
    keyring (`scripts/tests/test_agent_runtime_acceptance.py`); no spec
    requirement or scenario states this. — already partly in: nowhere
- conflicts: this bug says "`devcontainer.json` sets `DBUS_SESSION_BUS_ADDRESS`
  in `containerEnv` to the fixed `unix:path=/tmp/agentdev-dbus/bus`" and names
  `setup-keyring.sh`; the current code sets
  `DBUS_SESSION_BUS_ADDRESS=unix:path=/run/agentdev/xdg/bus` in
  `docker/devcontainer/agentdev-devcontainer.Dockerfile` and
  `docker/deploy/agentdev-deploy.Dockerfile`, and the keyring code is
  `py_packages/agentdev_runtime/agentdev_runtime/keyring.py`.
