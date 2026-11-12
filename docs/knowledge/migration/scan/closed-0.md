# docs/knowledge/data/plans/20260814-drop-venv-symlink.md

- verdict: DEAD (subject removed)
- owning spec: agentdev-runtime-images (rationale already in
  `architecture/uv-environment-location.md`)
- note: the plan's decision (keep `UV_PROJECT_ENVIRONMENT`, drop the `.venv`
  symlink, fixed path `/uv/venvs/ws-project`, Compose-project-scoped
  `agentdev-uv` volume) has been reversed and replaced. The one lasting fact —
  cache and environment must share a filesystem so uv can hardlink, which rules
  out an in-tree environment — is held in
  `architecture/uv-environment-location.md#why-the-environment-is-out-of-tree`;
  CI and host checkouts keeping an in-tree `.venv` is held in
  `architecture/uv-environment-location.md#consequences`.
- conflicts:
  - plan `## Approach`: "Keep `UV_PROJECT_ENVIRONMENT`, drop the symlink" versus
    `architecture/uv-environment-location.md#why-a-venv-link-rather-than-uv_project_environment`:
    "The Dev Container therefore sets no `UV_PROJECT_ENVIRONMENT`" and "The
    checkout's `.venv` is a symlink to it".
  - plan `## Approach`: "can be a fixed string, `/uv/venvs/ws-project`" versus
    `architecture/uv-environment-location.md`: "its own uv environment at
    `$AGENTDEV_VENV_ROOT/<checkout directory name>`" and
    `#why-one-environment-per-checkout`: "A single shared environment breaks as
    soon as two checkouts use it".
  - `architecture/pr-verification-sections.md#alternatives-rejected` still says
    "this repository tracks no symlinks at all, having just removed its only one
    — the reasoning in uv environment location transfers clause for clause",
    which the current `architecture/uv-environment-location.md` contradicts (a
    stale statement in the note, inherited from this plan).

# docs/knowledge/data/plans/20260815-honest-plan-checkboxes.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: plan-checkbox-evidence
- unique items:
  - [rationale] ~~The evidence requirement changes the shape of the artifact
    instead of adding prose rules to Implement: the rules that would have
    prevented the over-claiming incident were already written in the Implement
    skill and were violated anyway, so another round of prose rules was
    rejected; a find-and-replace can flip boxes but cannot write evidence lines.
    — already partly in: `spec/plan-checkbox-evidence.md#purpose` ("Shape is
    what failed") and
    `#requirement-a-ticked-task-carries-the-evidence-that-closed-it` scenario
    "Several boxes would be ticked at once"; the rejected alternative is
    nowhere~~ — written:
    spec/plan-checkbox-evidence.md#honest-ticks-come-from-the-artifacts-shape-not-more-prose-rules
  - [rationale] ~~The gate is a pytest under `docs/knowledge/tests/` and not an
    extension of `validate_agent_files`, because that package must stay usable
    with zero knowledge of this repository and plan documents are this
    workspace's knowledge graph, not agent files. — already partly in:
    `architecture/module-layout.md` (states the zero-knowledge constraint on
    `validate_agent_files`, not its consequence for the plan-checkbox gate)~~ —
    written:
    spec/plan-checkbox-evidence.md#the-gate-is-a-knowledge-base-test-not-a-validator-extension
- conflicts: none (plan `## Out of scope` says the `agentdev` catalog skills "do
  not use plan checkboxes"; that described the state before the IWE skills moved
  into the catalog and is dead, not a live contradiction)

# docs/knowledge/data/plans/20260815-pr-verification-sections.md

- verdict: ALL ALREADY HELD
- owning spec: template-consumption (`#pull-request-description-guidance`) for
  the consumer side; NONE for the section format itself (suggest:
  pr-description-format), currently held whole in
  `architecture/pr-verification-sections.md`
- note: decision, both filters, the pointer stub, the inverted authority, the
  "tell the consumer their template was not consulted" rule, the need to read
  `.github/workflows/`, the rename-only alternative, and "no mechanical gate"
  are all in `architecture/pr-verification-sections.md` (`#decision`,
  `#alternatives-rejected`, `#consequences`). The only detail not repeated there
  is the instruction not to add a check that inspects `./.tmp/pr-body.md`, which
  is a corollary of the note's "A mechanical gate is not available".
- conflicts: none

# docs/knowledge/data/plans/20260815-strengthen-workflow-skill-contracts.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [rationale] ~~Plan revision and spec synchronization have no skills of their
    own: Plan has create and revise modes and Ship is the only workflow that
    synchronizes durable specs; separate Update and Sync skills were rejected
    because they add entry points and weaken the existing ownership boundaries
    (Explore investigates, Plan owns planning state, Implement records tactical
    deviations, Verify proves, Ship merges specs). — already partly in:
    `spec/iwe-workflow-skills.md#requirement-plan-creates-or-revises-planning-state-without-implementing`
    and `#requirement-ship-synchronizes-durable-specs-by-intelligent-merge`
    (behaviour only; the rejected alternative is nowhere)~~ — written:
    spec/iwe-workflow-skills.md#revision-and-spec-synchronization-belong-to-plan-and-ship
  - [rationale] ~~A user confirmation may not override a CRITICAL Verify finding
    at Ship: a plan stays active or is cancelled rather than being recorded as
    shipped while its durable claims are known false; duplicating Verify's
    checks inside Ship was rejected because two copies drift. — already partly
    in:
    `spec/iwe-workflow-skills.md#requirement-normal-shipping-requires-a-clean-independent-verification`
    (refusal and "rulebook SHALL be defined once"; the no-override reason is
    nowhere)~~ — written:
    spec/iwe-workflow-skills.md#a-critical-blocks-ship-with-no-override
    (Rejected: "Ship running its own copy of Verify's checks"; the no-override
    reason was already held there)
  - [rationale] ~~A revision stays in the same plan only while topic, intended
    outcome, and verification story remain materially the same, because
    replacing an active plan's intent in place destroys the meaning of its
    already-completed tasks and their evidence. — already partly in:
    `spec/iwe-workflow-skills.md#requirement-plan-creates-or-revises-planning-state-without-implementing`
    scenario "A revision changes the work's intent" (behaviour without the
    reason)~~ — written:
    spec/iwe-workflow-skills.md#a-revision-keeps-its-plan-only-while-the-plans-intent-holds
  - [rationale] ~~Ship merges specs from verified evidence and only then moves
    plan, feature, bug, release, and log state: overwriting specs from plan
    prose was rejected because a plan can be stale and would erase unaffected
    scenarios, and updating stages before verifying the spec merge was rejected
    because it produces a falsely completed plan. — already partly in:
    `spec/iwe-workflow-skills.md#requirement-ship-synchronizes-durable-specs-by-intelligent-merge`
    (behaviour; neither rejected alternative is stated)~~ — written:
    spec/iwe-workflow-skills.md#ship-merges-specs-from-verified-evidence-before-it-moves-any-state
- held elsewhere: adopt OpenSpec language but not its machinery
  (`spec/iwe-workflow-skills.md#requirement-workflow-improvements-preserve-the-iwe-and-okf-model`);
  the shared materiality threshold (Plan and Implement requirements of the same
  spec); restart-safe Ship and `iwe delete` for spec retirement (same spec,
  scenarios "Shipping resumes after partial graph updates" and "A durable spec
  is retired"); no test asserting exact skill wording (root `AGENTS.md#tests`).
- conflicts: none

# docs/knowledge/data/plans/20260815-uv-run-in-ci.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: ci-python-environment); nearest existing homes are
  `architecture/uv-environment-location.md` and pre-commit-gate
- unique items:
  - [constraint] ~~CI provisioning syncs with `uv sync --locked`, never
    `--frozen`: `--frozen` skips the lockfile currency check, so a dependency
    added to `pyproject.toml` but not locked passes provisioning and is then
    installed silently by a later `uv run` mid-job; `--locked` fails at
    provisioning. — already partly in: nowhere in spec/ or architecture/ (only a
    code comment in `.github/actions/setup-python-venv/action.yml`)~~ — struck:
    already held by
    spec/ci-python-environment.md#requirement-one-action-provisions-the-environment-and-activates-nothing
    (scenario "the lock file is out of date") and
    spec/ci-python-environment.md#provision-never-activate
  - [constraint] ~~CI sets `UV_PYTHON_PREFERENCE: only-system`: uv's default
    `python-preference` is `managed`, so without it uv may resolve or download
    its own interpreter and the one `actions/setup-python` installed is used
    only by coincidence. — already partly in: nowhere (code only,
    `.github/actions/setup-python-venv/action.yml`)~~ — struck: already held by
    spec/ci-python-environment.md#requirement-one-action-provisions-the-environment-and-activates-nothing
    (scenario "the runner has another Python on PATH") and
    spec/ci-python-environment.md#provision-never-activate
  - [constraint] ~~A check script must not install packages: it resolves its
    tool through `uv run --no-sync`, because nothing provisions before a check
    and a developer's `pyproject.toml` can legitimately be mid-edit. — already
    partly in: nowhere (code only,
    `.agents/plugins/agentdev/bin/python_lint_check.py`,
    `py_packages/agentdev_runtime/agentdev_runtime/doctor.py`)~~ — struck:
    already held by
    spec/catalog-scripts.md#requirement-the-python-lint-check-finds-ruff-without-installing-anything;
    `agentdev-runtime doctor` probes with `uv run --no-sync` too
    (py_packages/agentdev_runtime/agentdev_runtime/doctor.py), a detail of a
    check, not a separate rule
  - [rationale] ~~The action keeps the name `setup-python-venv` after its
    contract changed to "callers use `uv run`": `uv sync` still creates an
    in-tree `.venv` on a runner so the name stays accurate, and the path is
    consumer-facing template surface, so a rename would add churn without
    removing the need to document the contract. — already partly in:
    `architecture/template-boundary.md` (lists the action as
    consumer-customizable, without this reasoning)~~ — written:
    spec/ci-python-environment.md#the-action-keeps-the-name-setup-python-venv
  - [non-goal] ~~Devcontainer and CI provisioning are not unified — a persistent
    volume and an ephemeral runner stay different; only the invocation contract
    (`uv run`) is shared, and CI's in-tree `.venv` is not removed. — already
    partly in: `architecture/uv-environment-location.md#consequences` ("CI
    checkouts ... keep uv's default in-tree `.venv`")~~ — struck: already held
    by spec/ci-python-environment.md#provision-never-activate ("an ephemeral
    runner here, a persistent volume there")
- held elsewhere / dead: the narrow symlink cleanup (only links this
  repository's shape created are touched) is held as `link-venv` behaviour in
  `architecture/uv-environment-location.md#which-events-create-and-remove-an-environment`;
  the trailing-slash and `/uv/venvs/ws-project` points are dead with the fixed
  path.
- conflicts: ~~plan `## Context`: "the `agentdev-uv` volume is
  Compose-project-scoped and the fixed `/uv/venvs/ws-project` path holds" versus
  `architecture/uv-environment-location.md`: environments live at
  `$AGENTDEV_VENV_ROOT/<checkout directory name>` on the home volume.~~ —
  struck: stale plan statement; the current layout is
  spec/agentdev-runtime-images.md#requirement-each-checkout-has-its-own-project-environment

# docs/knowledge/data/plans/20260816-ai-responder-workflows.md

- verdict: ALL ALREADY HELD
- owning spec: ai-review-gate (rationale in
  `architecture/ci-agent-plugin-availability.md`)
- note: run the lifecycle hooks against the job's own checkout, why all three
  hooks, what a `container:` job must supply, the `AGENTDEV_SKIP_PRE_COMMIT`
  guard, the tolerated missing-mount `chown`, and the rejected alternatives
  (image-time install, bare runner, vendored `pr-review`) are in
  `architecture/ci-agent-plugin-availability.md`. The fork and write-access
  gates and "the check SHALL NOT require that the review name the pull request's
  current head commit", with its reason, are in
  `spec/ai-review-gate.md#requirement-prs-are-blocked-until-an-ai-review-exists`
  and the responder requirement of the same spec. Claude-only responder is in
  `architecture/supported-harnesses.md`. Dead: everything about
  codebase-memory-mcp (removed; `spec/catalog-lifecycle.md` now clears its
  leftovers), `require-ai-review.yml` (replaced by
  `.github/actions/ai-review-status`), the Xpra guard.
- conflicts:
  - plan `## Approach`: "Its codex acceptance path is live, not dead: Codex
    reviews arrive via Codex web as `chatgpt-codex-connector[bot]`" versus
    `spec/ai-review-gate.md`: "SHALL accept a review only from
    `plume-works-quill[bot]`" and `architecture/assignee-review-trigger.md`:
    "drop Codex reviews, and the Codex `+1` reaction, from the AI review gate".
  - `architecture/ci-agent-plugin-availability.md#problem-this-solved` ("stage
    the plugin catalog at `/opt/agentdev` but does not install it") and its
    `## Status` ("Not yet implemented") contradict `spec/catalog-lifecycle.md`
    ("SHALL be installed into each agent's plugin state during the
    `agentdev-base` build"); the stale text is in the note, mirrored from this
    plan's `## Context`.

# docs/knowledge/data/plans/20260816-move-iwe-skills-to-agentdev.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills (placement) and template-consumption
  (distribution)
- unique items:
  - [rationale] ~~The IWE workflow skills ship inside the `agentdev` catalog
    under `iwe-` prefixed names (`/agentdev:iwe-plan`), a maintainer decision. A
    separate `iwe` plugin was rejected in favour of a single catalog to version
    and install, accepting that `agentdev` then ships a workflow that assumes an
    IWE graph; the prefix is kept although `agentdev:` already namespaces,
    because `plan`, `ship`, and `verify` are generic enough to read as peers of
    the `pr-*` skills in the same directory. Keeping them under
    `.claude/skills/` was rejected because every template consumer would inherit
    them outside the supported install path. — already partly in: nowhere (specs
    use the `iwe-` names without stating the decision)~~ — written:
    spec/iwe-workflow-skills.md#the-iwe-workflow-skills-carry-an-iwe-prefix-in-the-agentdev-catalog
- not carried over: "the catalog validator only inspects markdown links, so a
  backticked path validates green" and "`iwe rename` repairs only links between
  graph documents" are tool observations from the move;
  `scripts/check-anchors.py` now checks catalog anchors, so the first was not
  treated as durable. Not verified whether the second is recorded; no hit for
  `iwe rename` in spec/ or architecture/.
- conflicts: none

# docs/knowledge/data/plans/20260816-skill-handoff-routes.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [behaviour] ~~For an unticked task, Verify recommends one of three routes:
    complete it, tick it if already done, or revise the plan to drop it through
    Plan's revise mode, which treats dropping a task as a material scope change
    and asks the user. Present in
    `.agents/plugins/agentdev/agents/iwe-verifier.agent.md`; no spec requirement
    or scenario states it. — already partly in:
    `spec/plan-checkbox-evidence.md#requirement-verify-audits-ticked-and-unticked-boxes-asymmetrically`
    (the CRITICAL for an unchecked task, not the routes)~~ — written:
    spec/plan-checkbox-evidence.md#requirement-verify-audits-ticked-and-unticked-boxes-asymmetrically
    (scenario "A task is left unticked")
  - [rationale] ~~The third route exists because zero-CRITICAL Verify is a hard
    precondition of Ship with no override, so a task the user declined would
    otherwise block shipping unless the whole plan were cancelled; softening
    Ship's no-override rule was rejected. A spec-versus-code contradiction found
    with no plan in flight is filed as a bug and not handed to Ship, because
    Ship acts only on a selected plan's `## Spec changes`. — already partly in:
    `spec/iwe-workflow-skills.md#requirement-capture-files-complete-inbox-documents`
    (defects go to Capture; no reason given)~~ — written:
    spec/iwe-workflow-skills.md#a-critical-blocks-ship-with-no-override
    (Rejected: softening the no-override rule) and
    spec/iwe-workflow-skills.md#a-spec-contradiction-found-outside-a-plan-becomes-a-bug
- conflicts: ~~plan `## Approach`: "Explore gains one `## Capturing` bullet
  routing an established defect to `data/bugs/<slug>.md`" versus
  `spec/iwe-workflow-skills.md#requirement-capture-files-complete-inbox-documents`:
  "The Capture skill SHALL be the only writer of new bug, proposed-feature, and
  backlog-task documents" (superseded as the plan anticipated, not a live
  defect).~~ — struck: stale plan statement, superseded as anticipated;
  spec/iwe-workflow-skills.md#requirement-capture-files-complete-inbox-documents
  holds the current rule

# docs/knowledge/data/plans/20260816-structured-plan-spec-deltas.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
  (`#requirement-plans-express-spec-impact-at-risk-appropriate-fidelity`)
- unique items:
  - [behaviour] ~~A plan's spec delta has no `RENAMED Requirements` operation; a
    requirement-only rename is written as an explicit removal plus an addition,
    because a fourth operation would carry identity semantics that imply a
    parser. Present in `.agents/plugins/agentdev/agents/iwe-planner.agent.md`;
    not in any spec. — already partly in: nowhere~~ — written:
    spec/iwe-workflow-skills.md#plan-deltas-adopt-the-notation-not-an-application-engine
    (Rejected: "A `RENAMED` operation"); the behaviour was already held by
    spec/iwe-workflow-skills.md#requirement-plans-express-spec-impact-at-risk-appropriate-fidelity
    scenario "A requirement is renamed"
  - [rationale] ~~Structured deltas are conditional on behavioural risk:
    requiring a full delta for every plan was rejected as ceremony on refactors
    and small changes; separate delta documents or change bundles were rejected
    because they duplicate the plan lifecycle; the fenced form inside
    `## Spec changes` keeps canonical Requirement/Scenario heading levels
    without adding a document type, schema binding, directory, or skill. —
    already partly in:
    `spec/iwe-workflow-skills.md#requirement-plans-express-spec-impact-at-risk-appropriate-fidelity`
    (the three forms) and
    `#requirement-workflow-improvements-preserve-the-iwe-and-okf-model` (no
    bundles, no application engine); the reasons are not stated~~ — struck:
    already held by
    spec/iwe-workflow-skills.md#plan-deltas-adopt-the-notation-not-an-application-engine
    (delta in every plan, separate bundle rejected) and the fence sentence of
    spec/iwe-workflow-skills.md#requirement-plans-express-spec-impact-at-risk-appropriate-fidelity
- held elsewhere: Verify judging against durable spec plus plan delta, Ship not
  rewriting intent from code, and no deterministic application engine are all
  requirements or scenarios in `spec/iwe-workflow-skills.md`.
- conflicts: none

# docs/knowledge/data/plans/20260817-catalog-install-in-image.md

- verdict: ALL ALREADY HELD
- owning spec: catalog-lifecycle
- note: the surviving decision — the image installs the staged catalog at build
  time so a consumer that runs no lifecycle command still resolves `agentdev:*`
  skills, and the create phase installs again onto the volume — is
  `spec/catalog-lifecycle.md#requirement-the-catalog-is-installed-at-image-build-time-and-again-by-postcreatecommand`,
  including "content preservation, not byte-identity". The rejected "each
  raw-image consumer installs it itself" alternative has its reason (duplicates
  logic the lifecycle owns) in
  `architecture/ci-agent-plugin-availability.md#alternatives-considered`.
  Everything about the `~/.claude.json` symlink handoff, its ordering before
  `codebase-memory-mcp-install.sh`, `/root` as home, and Codex is dead: the
  link, CBM, the root account, and Codex support are all gone.
- conflicts:
  - plan `## Approach`: "It cannot be volume-backed (Docker volumes are
    directory-backed), so postCreate persists it as a plain file inside the
    `agentdev-claude` volume ... and symlinks `/root/.claude.json` to it" and
    `## Out of scope`: "the symlink workaround stays" versus
    `spec/catalog-lifecycle.md`: "`~/.claude.json` SHALL be a regular file on
    that volume" and scenario "a home volume still holds the ~/.claude.json link
    ... it is replaced by a regular file".
  - plan `## Approach`: "an install step after staging, for both Claude and
    Codex" versus `architecture/supported-harnesses.md`: "Codex is not supported
    anywhere".

# docs/knowledge/data/plans/20260817-no-logbooks-in-the-graph.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
  (`#requirement-plans-record-intent-not-the-path-taken-to-it`); the rule itself
  lives in root `AGENTS.md` Best Practice 8, outside spec/ and architecture/
- unique items:
  - [rationale] ~~A read-only rule making a plan's `## Context` and
    `## Approach` untouchable by Implement was rejected: genuine intent
    corrections do arrive mid-implementation, so the rule would be broken for
    good reasons and then discounted; the material-deviation route through
    Plan's revise mode handles them. — already partly in:
    `spec/iwe-workflow-skills.md#requirement-plans-record-intent-not-the-path-taken-to-it`
    (intent sections "remain the Plan skill's to own"; scenario "A finding
    changes the plan's intent"), without the rejected alternative~~ — struck:
    already held by
    spec/iwe-workflow-skills.md#the-durable-knowledge-audit-is-an-isolated-leaf
    (Rejected: making `## Context` and `## Approach` read-only)
  - [rationale] ~~The two tests in Best Practice 8 are deliberately distinct:
    "rewritten from scratch" asks whether a fact is durable, "gone right the
    first time" asks whether a sentence is a logbook trace, and a durable fact
    can still be phrased as narration. The rule sits in root `AGENTS.md` and not
    under the graph manual because the residue appears in every kind of text an
    agent writes; `docs/knowledge/AGENTS.md` keeps only the narrative exceptions
    (`data/bugs/`, `data/log.md`, a plan's `## Verification results`). — already
    partly in: root `AGENTS.md` Best Practice 8 (both tests, no statement of why
    there are two); nowhere in spec/ or architecture/~~ — written:
    spec/iwe-workflow-skills.md#the-no-logbook-rule-lives-in-the-root-agentsmd-with-two-tests
  - [non-goal] ~~Narration in plans is not detected mechanically: the
    plan-checkbox gate reads shape and narration has no reliable shape — a
    line-count or prose-to-task ratio would fire on legitimately long plans and
    miss a short dense logbook. Closed plans and `data/log.md` are not rewritten
    retroactively. — already partly in: `spec/plan-checkbox-evidence.md#purpose`
    ("The gate reads shape only"); the non-goal is nowhere~~ — struck:
    mechanical detection already held by
    spec/iwe-workflow-skills.md#the-durable-knowledge-audit-is-an-isolated-leaf;
    not rewriting closed plans and `data/log.md` is history (`data/log.md` no
    longer exists)
- held elsewhere: `## Verification results` as the only narrative section,
  Implement routing findings out of the plan, and the fresh-context audit are in
  `spec/iwe-workflow-skills.md`; commit messages excluded from `iwe-audit` is in
  `.agents/plugins/agentdev/skills/iwe-audit/SKILL.md`.
- conflicts: none

# docs/knowledge/data/plans/20260817-preserve-approved-wording.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [rationale] ~~Approved wording is carried in
    `.tmp/approved-wording-<slug>.md` and not in a graph location: `.tmp/` is
    the mandated, gitignored scratch path and the window is short, since the
    plan's fenced task blocks become the durable copy. A `data/drafts/` hub was
    rejected because the hub set is closed, it would be the first hub of
    temporary content needing a deletion lifecycle, and a second copy of the
    same bytes would drift from the plan. — already partly in:
    `spec/iwe-workflow-skills.md#requirement-plan-creates-or-revises-planning-state-without-implementing`
    scenario "A task applies text the user already approved" (names the file,
    not the reason)~~ — struck: already held by
    spec/iwe-workflow-skills.md#approved-wording-is-carried-in-tmp-and-inlined-in-the-plan
  - [non-goal] ~~The verbatim-carrier rule covers only the Explore-to-Plan
    handoff. Plan-to-Implement and Implement-to-Ship carry no conversation
    context by construction — the written plan is the sole channel — so there is
    nothing for a carrier to preserve; no CI gate checks the verbatim match
    because `.tmp/` is gitignored. — already partly in: nowhere~~ — struck:
    already held by
    spec/iwe-workflow-skills.md#approved-wording-is-carried-in-tmp-and-inlined-in-the-plan
    (Rejected: carrying text across later handoffs; "No CI gate can see
    `.tmp/`")
- held elsewhere: Explore persists approved text verbatim and never paraphrases;
  Plan reproduces it verbatim in a fenced block so "a session holding only the
  plan can reproduce the approved bytes" — both in
  `spec/iwe-workflow-skills.md`.
- conflicts: none

# docs/knowledge/data/plans/20260831-pr-review-docs-durable-knowledge.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: pr-review); `spec/ai-review-gate.md` covers only
  the gate and the submit event, and `architecture/pr-review-effort-tiers.md`
  and `architecture/pr-review-correctness-bar.md` mention the durable-knowledge
  pass without defining it
- unique items:
  - [behaviour] ~~`pr-review` fast-approves only version-only and
    generated-file-only diffs; a docs-only diff is reviewed and always runs the
    durable-knowledge pass. Present in
    `.agents/plugins/agentdev/skills/pr-review/SKILL.md`; no spec states it. —
    already partly in: `architecture/pr-review-effort-tiers.md` ("fast-approves
    a mechanical diff"; "Dropping the metadata gate and the durable-knowledge
    pass at light effort" rejected)~~ — struck: already held by
    spec/pr-review.md#requirement-only-mechanical-diffs-are-fast-approved
  - [behaviour] ~~The lens follows the file, not the pull request: code files
    get the correctness passes and docs, skill, and agent files get one
    durable-knowledge pass, added only when the diff contains such files, in the
    same review; durable-knowledge findings are blocking (critical/P1) like
    correctness findings, without changing the submit-event rule. — already
    partly in: `architecture/pr-review-correctness-bar.md` ("must respect
    `pr-review`'s file lens")~~ — struck: already held by
    spec/pr-review.md#requirement-docs-and-skills-get-a-durable-knowledge-pass
  - [behaviour] ~~`iwe-audit` has a diff scope: the candidate set is the diff's
    added lines and the skill is report-only, returning its findings table
    without applying; `pr-review` maps each row to an inline comment and adds
    only its own high-signal bar. — already partly in: nowhere in spec/ or
    architecture/ (`.agents/plugins/agentdev/skills/iwe-audit/SKILL.md` only)~~
    — struck: already held by
    spec/pr-review.md#requirement-docs-and-skills-get-a-durable-knowledge-pass
    ("diff mode", "reports its table without editing")
  - [rationale] ~~The durable-knowledge criteria stay in `iwe-audit` alone:
    restating them in `pr-review` was rejected because two copies drift, and an
    `iwe-audit` mode that emits GitHub review comments was rejected because it
    puts review mechanics inside the auditor — `iwe-audit` stays ignorant of
    GitHub. — already partly in: nowhere~~ — written:
    spec/pr-review.md#docs-and-skills-are-reviewed-for-durable-knowledge
    (Rejected: "An `iwe-audit` mode that emits GitHub review comments"; the
    two-copies rejection was already held)
  - [rationale] ~~The durable-knowledge pass is an additional pass and never
    replaces a correctness pass, because repurposing one dilutes
    code-correctness coverage on code-heavy pull requests. — already partly in:
    nowhere~~ — struck: already held by
    spec/pr-review.md#docs-and-skills-are-reviewed-for-durable-knowledge
    (Rejected: "Turning a correctness pass into the durable-knowledge pass")
- conflicts: none found (~~plan `## Approach` says "Step 9 still caps at
  `COMMENT`, never `REQUEST_CHANGES`"; `spec/ai-review-gate.md` accepts state
  `changes_requested` and `architecture/ai-review-event-selection.md` discusses
  a review that "must request changes" — the submit-event rule appears to have
  changed since; not resolved here)~~ — struck: stale plan statement; the code
  submits `REQUEST_CHANGES` on any blocking finding
  (.agents/plugins/agentdev/skills/pr-review/SKILL.md › "Any blocking finding,
  inline or not → `REQUEST_CHANGES`"), as
  spec/ai-review-gate.md#requirement-the-ai-review-verdict-follows-its-findings
  states

# docs/knowledge/data/plans/20260831-pre-commit-owns-formatting.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: pre-commit-gate
- unique items:
  - [behaviour] ~~Hook installation includes the `pre-merge-commit` hook type,
    so the commit a non-conflicted `git merge` creates passes the same hooks as
    an ordinary commit; without it a merge commit runs no hooks. Present in
    `py_packages/agentdev_runtime/agentdev_runtime/project.py` (`HOOK_TYPES`)
    and `.pre-commit-config.yaml#default_stages`; no spec requirement or
    scenario states it. — already partly in:
    `architecture/cloud-session-host-toolchain.md` (lists the installed hook
    types, no reason)~~ — struck: already held by
    spec/pre-commit-gate.md#requirement-every-commit-path-runs-the-hooks-merges-included
- held elsewhere / dead: skills and agents carry no format-before-commit mandate
  because hooks own formatting — `architecture/formatter-ownership.md#decision`;
  the `noqa` and isort rules — root `AGENTS.md#python`. Super-Linter,
  `local-reformat`, `super-linter-env.sh`, `reformat.yml`, and
  `scripts/validate-super-linter-tool-versions.sh` are gone, so everything about
  keeping them is dead.
- conflicts: ~~plan `## Approach`: "Rejected: replacing Super-Linter in CI with
  `pre-commit run --all-files`" and `## Out of scope`: "Super-Linter remains the
  CI formatter" versus
  `architecture/formatter-ownership.md#rejected-alternatives`: "**Super-Linter
  as the CI gate.** Its image duplicated every hook" and
  `spec/pre-commit-gate.md` requirement "CI runs the pre-commit hooks as the
  lint gate".~~ — struck: stale plan statement; Super-Linter is gone and
  spec/pre-commit-gate.md#the-pre-commit-hooks-are-the-one-owner-of-every-formatter-and-the-ci-gate
  rejects it

# docs/knowledge/data/plans/20260901-gitignore-aware-discovery.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: agent-file-discovery
- unique items:
  - [rationale] ~~`git check-ignore` is the ignore primitive, not
    `git ls-files --others --exclude-standard`: it answers "is this path
    ignored" for any path whether tracked or not, whereas `ls-files` conflates
    ignore state with tracked state; candidates go to one batched
    `git check-ignore --stdin -z` call per walk root, not a process per
    directory. — already partly in:
    `spec/agent-file-discovery.md#requirement-git-work-tree-discovery-follows-git-ignore-rules`
    (names `git check-ignore`, no reason or batching)~~ — written:
    spec/agent-file-discovery.md#inside-a-work-tree-git-is-the-one-ignore-authority
    (batching is per walked directory, per
    py_packages/validate_agent_files/validate_agent_files/loaders.py::\_git_ignored
    callers)
  - [rationale] ~~Inside a work tree the hardcoded excluded-directory set is not
    applied, so there is a single ignore authority — a repository says "skip
    `__pycache__`" through `.gitignore` — and the set is a caller-supplied
    parameter reserved for the no-git fallback; applying both always was
    rejected. — already partly in: `spec/agent-file-discovery.md` requirements
    "Git work-tree discovery follows git ignore rules" and "Plain-directory
    discovery uses caller-supplied pruning" (behaviour only)~~ — written:
    spec/agent-file-discovery.md#inside-a-work-tree-git-is-the-one-ignore-authority
  - [constraint] ~~`git check-ignore` does not report `.git/`, which is why
    discovery prunes `.git/` unconditionally in both modes; nested `.gitignore`
    precedence is left entirely to git and not reimplemented. — already partly
    in:
    `spec/agent-file-discovery.md#requirement-git-internals-are-never-discovered`
    (the pruning, not the git fact behind it)~~ — written:
    spec/agent-file-discovery.md#inside-a-work-tree-git-is-the-one-ignore-authority
    (git reports `.git/` only when a repository names it in an ignore rule)
- conflicts: none
