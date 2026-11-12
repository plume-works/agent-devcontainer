# Batch 4 — durable knowledge held only in closed documents

## docs/knowledge/data/plans/20261023-pr-skills-ai-review-lifecycle.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: ai-review-refresh
- unique items:
  - [rationale] A `Claude PR Review Responder` check that completed `skipped`
    (or `cancelled`) does not count as a request because a skipped responder is
    the gate-only run that a push to an already-reviewed pull request starts;
    doubt resolves toward requesting, because a duplicate costs one redundant
    review while a wrongly counted check leaves the head unreviewed. — already
    partly in:
    `docs/knowledge/data/spec/ai-review-refresh.md#requirement-one-ai-review-trigger-per-head-commit`
    (behaviour and the scenario "a push to a reviewed pull request", no reason);
    the reason is otherwise only in
    `.agents/plugins/agentdev/skills/pr-request-ai-review/SKILL.md` — written:
    docs/knowledge/data/spec/ai-review-refresh.md#a-responder-check-counts-as-a-request-unless-it-was-skipped-or-cancelled
  - [rationale] A completed responder check that failed still counts as that
    head's request, so a failed review is reported to a person, not retried on
    the same head. — already partly in:
    `docs/knowledge/data/spec/ai-review-refresh.md` scenario "a second request
    for the same head" (behaviour);
    `docs/knowledge/data/architecture/label-review-triggers.md#approach` ("A
    failed review removes the label, so it is not retried on every later push",
    about the label only) — written:
    docs/knowledge/data/spec/ai-review-refresh.md#a-responder-check-counts-as-a-request-unless-it-was-skipped-or-cancelled
  - [rationale] The re-review evaluation is hooked into `pr-open` update mode
    and runs on every update-mode run whatever the push or body edit changed.
    Rejected: hooking it into `pr-sync` alone (`pr-open` reached directly in
    update mode would stay uncovered) and gating it on whether this push moved
    the head (a head pushed earlier by another path would be skipped
    unevaluated). — already partly in:
    `docs/knowledge/data/spec/ai-review-refresh.md#requirement-every-push-to-a-reviewed-pull-request-is-evaluated`
    (behaviour only) — written:
    docs/knowledge/data/spec/ai-review-refresh.md#re-review-evaluation-hangs-off-pr-open-update-mode
  - [constraint] `pr-feedback-resolution` calls `pr-eval-review-needed` itself
    and pushes through `push-branch` rather than through the `pr-open` skill, so
    one feedback pass never evaluates twice. — already partly in: nowhere —
    written:
    docs/knowledge/data/spec/ai-review-refresh.md#re-review-evaluation-hangs-off-pr-open-update-mode
  - [rationale] The evaluation reads its evidence (review threads and review
    comments since the newest reviewed commit) from the pull request, so a cold
    run from `pr-sync` or `pr-merge` decides on the same footing as a feedback
    pass that holds the conversation. — already partly in:
    `docs/knowledge/data/spec/ai-review-refresh.md#requirement-every-push-to-a-reviewed-pull-request-is-evaluated`
    ("read from the pull request rather than from the session", no reason) —
    written:
    docs/knowledge/data/spec/ai-review-refresh.md#re-review-evaluation-hangs-off-pr-open-update-mode
  - [non-goal] `update-branch`'s own pushes run no re-review evaluation after a
    base merge, even though `pr-eval-review-needed` counts a judgment-call
    conflict merge as new scope. — already partly in: nowhere — written:
    docs/knowledge/data/spec/ai-review-refresh.md#re-review-evaluation-hangs-off-pr-open-update-mode
  - [rationale] No per-request marker comment naming the head is posted with a
    review request, because the responder check already names the head commit;
    the optional rationale comment is the only comment. — already partly in:
    `docs/knowledge/data/spec/ai-review-refresh.md#requirement-one-ai-review-trigger-per-head-commit`
    (rationale comment format only) — written:
    docs/knowledge/data/spec/ai-review-refresh.md#a-responder-check-counts-as-a-request-unless-it-was-skipped-or-cancelled
- conflicts:
  - ~~Document `## Approach`: "It requests a review by toggling the author's
    assignment, which fires the `pull_request`/`assigned` event the responder
    reviews on." Spec
    `ai-review-refresh.md#requirement-one-ai-review-trigger-per-head-commit`:
    "SHALL request it by adding the `request-ai-review` label ... SHALL NOT
    change the pull request's assignees to request a review". The whole
    assignee-toggle mechanism (toggle order, restoring assignees, `unassigned`
    not a trigger) is dead.~~ — resolved: the spec matches the code
    (`request-review.py` adds the `request-ai-review` label and never touches
    assignees); the plan statement is stale and is archived as is
  - ~~Document: "Accepted reviewers are ... `claude[bot]` and
    `github-actions[bot]`". Spec
    `ai-review-gate.md#requirement-prs-are-blocked-until-an-ai-review-exists`:
    "SHALL accept a review only from `plume-works-quill[bot]`".~~ — resolved:
    the spec matches the code (`.github/actions/ai-review-status/action.yml`
    accepts only `plume-works-quill[bot]`); the plan statement is stale
  - ~~Document `## Out of scope`: "A push during a running review: the new
    head's gate passes on the prior review while the older head's run is
    pending." Spec `ai-review-gate.md` scenario "a push lands during a requested
    review": "the label stays, and the push's run reviews the new head and
    removes it" (`ai-responder.yml#concurrency` cancels in progress on
    `synchronize`).~~ — resolved: the spec matches the code
    (`.github/workflows/ai-responder.yml#concurrency`); the plan statement is
    stale
  - ~~Document names `request-review.sh` and `push-branch.sh`; the code is
    `request-review.py` and `push-branch.py`, and the result table lacks the
    spec's `BLOCKED`.~~ — resolved: the specs name `request-review.py` and
    `push-branch.py` and list `BLOCKED`, as the code does; the plan statement is
    stale

## docs/knowledge/data/plans/20261023-reusable-agentdev-devcontainer.md

- verdict: ALL ALREADY HELD
- owning spec: agentdev-runtime-images, template-consumption
- conflicts: none in this document. Its statement "reject derived images
  overwriting managed runtime files" is held twice with different mechanisms:
  `docs/knowledge/data/architecture/devcontainer-runtime.md#customization-interface`
  says "The bootstrap checks `/opt/agentdev-runtime/` against the build-time
  manifest `/etc/agentdev/runtime.sha256`", while
  `docs/knowledge/data/spec/agentdev-runtime-images.md#requirement-the-bootstrap-refuses-a-changed-runtime-package`
  and `docs/knowledge/data/architecture/agentdev-runtime-package.md#integrity`
  say the check is the installed distribution's `RECORD`; no `runtime.sha256`
  exists in `docker/` or `py_packages/`. The architecture note is stale, not the
  plan.

## docs/knowledge/data/plans/20261023-reusable-iwe-bootstrap.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-bootstrap (scaffold identity); agent-file-discovery
  (validator scan)
- unique items:
  - [constraint] The scaffold's schemas, `.iwe/` configuration, and knowledge
    instructions under `skills/iwe-bootstrap/assets/` are the same bytes this
    repository's own workspace uses; a publisher-side test
    (`.agents/plugins/agentdev/tests/test_iwe_seed.py`) keeps the two identical
    and every asset tracked, so a schema change here is a scaffold change. —
    already partly in: `docs/knowledge/data/architecture/template-boundary.md`
    (scaffold source table; no identity invariant) — written:
    docs/knowledge/data/spec/iwe-bootstrap.md#the-scaffold-ships-the-publishers-own-workspace-files
  - [constraint] `validate_agent_files` does not scan the `assets/` directory
    beside a `SKILL.md` for references: in the Agent Skills layout that
    directory holds output templates, not documents read in place, and the
    scaffold's Markdown uses IWE extension-less links that resolve only once
    installed. No spec governs this scan
    (`py_packages/validate_agent_files/validate_agent_files/validators/bundled_markdown.py::SKILL_ASSETS_DIR`).
    — already partly in: nowhere — written:
    docs/knowledge/data/spec/agent-file-discovery.md#requirement-bundled-markdown-discovery-skips-a-skills-assets-directory
    and
    docs/knowledge/data/spec/agent-file-discovery.md#a-skills-assets-are-output-not-documents-read-in-place
- ~~conflicts: Document `## Context` says the seed "lives under
  `templates/iwe/`"; that directory no longer exists (old state, superseded by
  this plan itself). Otherwise none.~~ — resolved: no spec names
  `templates/iwe/`; the plan statement is stale

## docs/knowledge/data/plans/20261025-claude-remote-control-spawn-mode.md

- verdict: ALL ALREADY HELD
- owning spec: claude-remote-control
- conflicts: Document `## Approach` › Rejected alternatives: "revival of a
  worktree session is an assumption, not a measured behaviour."
  `docs/knowledge/data/architecture/claude-remote-control-server-mode.md#claude-code-behavior-the-decision-relies-on`:
  "Measured on Claude Code 2.1.310 ... A spawned session returns after a restart
  in either spawn mode." The architecture note supersedes the plan. Two small
  points sit only in the plan and are implied, not stated, elsewhere: a non-git
  workspace gets no fallback to `same-dir`, and session mode ignoring the spawn
  variable was chosen over failing in a mode that does not use it.

## docs/knowledge/data/plans/20261026-assignee-review-trigger.md

- verdict: ALL ALREADY HELD
- owning spec: ai-review-gate
- conflicts:
  - Document `## Approach`: "`opened`, `ready_for_review`, `reopened`, and
    `assigned` always review". Spec
    `ai-review-gate.md#requirement-a-review-runs-on-first-push-and-on-explicit-request`:
    "An assignment, a reviewer request, and a reviewer request's removal SHALL
    NOT start a run."
  - Document: "`workflow_dispatch` keeps carrying free-form tasks ... The bridge
    still dispatches `@claude <prompt>` task mentions" and "A mention that opens
    `@claude review` ... posts the approved message". Spec: "a comment, an
    issue, or a mention of `@claude` SHALL start no run, and the workflow SHALL
    accept no `workflow_dispatch`."
  - Document: "the `[ci:skip-ai-review]` marker is always respected" and "the
    body marker [`[ci:review-effort=…]`] stays".
    `docs/knowledge/data/architecture/label-review-triggers.md#context`: "a
    `block-ai-reviews` label replaces the `[ci:skip-ai-review]` body marker" and
    "the `[ci:review-effort=light|full]` marker and requested effort tiers are
    removed".
  - Document: "`ai-review-status` accepts only `claude[bot]` and
    `github-actions[bot]` reviews." Spec: "only from `plume-works-quill[bot]`".
  - What survives (which runs the ruleset counts; bot pull requests outside
    `TRUSTED_BOT_ACTORS` merge only by bypass; a replaced queued run is
    accepted) is in
    `docs/knowledge/data/architecture/assignee-review-trigger.md#which-runs-the-gate-is-counted-from`,
    `label-review-triggers.md`, and `spec/ai-review-gate.md`.

## docs/knowledge/data/plans/20261026-autonomous-implement-loop.md

- verdict: ALL ALREADY HELD
- owning spec: iwe-workflow-skills
- conflicts:
  - Document `## Context`: "Implement acts on every CRITICAL and every WARNING
    with a concrete route."
    `docs/knowledge/data/architecture/autonomous-implement-loop.md#decision`:
    "The loop acts on every CRITICAL, and on a WARNING only when its fix fits a
    task the plan already has and adds no claim the code must newly meet; every
    other WARNING is filed through `/agentdev:iwe-capture`."
  - Document: "the coordinator runs it for `/agentdev:iwe-implement-all`" and
    "That holds on all three harnesses". No `iwe-implement-all` skill exists
    under `.agents/plugins/agentdev/skills/`, and the architecture note says
    "the loop runs on Claude Code and OpenCode"
    (`docs/knowledge/data/architecture/supported-harnesses.md`: Codex is not
    supported). The coordinator half of the plan is dead.
  - Document rejects running the loop in a dispatched `iwe-implementer` because
    "a coordinator could then no longer see what its Implementer dispatched";
    the architecture note gives the current reason: "`iwe-implementer` is never
    dispatched".

## docs/knowledge/data/plans/20261026-verify-in-fresh-context.md

- verdict: ALL ALREADY HELD
- owning spec: iwe-workflow-skills
- conflicts:
  - Document `## Approach`: "The agent body is the rulebook on all three
    harnesses ... the Codex installer renders it into
    `agentdev-iwe-verifier.toml`".
    `docs/knowledge/data/architecture/fresh-context-verify.md#decision`: "The
    agent body is the rulebook on both harnesses"; `supported-harnesses.md`:
    "Codex is not supported anywhere".
  - Document: "`Write` is there so the Codex installer gives it a
    `workspace-write` sandbox". That reason is dead with Codex, yet
    `.agents/plugins/agentdev/agents/iwe-verifier.agent.md` still lists `Write`
    and `fresh-context-verify.md` records the tool list with no reason. The same
    applies to the document's reason the Shipper invokes the skill ("an agent
    body rendered into a Codex TOML cannot" follow a plugin-relative link).

## docs/knowledge/data/plans/20261027-standalone-remote-control-autostart.md

- verdict: ALL ALREADY HELD
- owning spec: claude-remote-control, standalone-opencode-runtime
- conflicts: none of substance. The document names
  `runtime-remote-control.sh run`, `claude-remote-control-start.sh`, and
  `runtime-health.sh`; the code and
  `docs/knowledge/data/architecture/standalone-opencode-runtime.md#remote-control-watcher`
  name `agentdev-runtime remote-control run|start` and
  `agentdev-runtime health`. The document compares "mtime and size"; the
  architecture note says "inode, mtime, or size".

## docs/knowledge/data/plans/20261028-move-expo-bridge-kb.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: template-consumption
- unique items:
  - [rationale] The VS Code Expo bridge's whole record — design, plans, bugs,
    backlog, finished ones included — lives in the graph of
    `plume-works/vscode-expo-bridge`, not here; this repository keeps only the
    Expo profile's wiring and its release notes for that wiring, and links to
    bridge documents by absolute GitHub URL on `main`. Rejected: keeping
    finished bridge plans and fixed bugs here (splits the product's record
    across two repositories, and open bugs link into finished plans); adopting
    the whole template in the extension repository (brings a devcontainer and
    catalog it does not need for project memory — it uses
    `/agentdev:iwe-bootstrap` alone). — already partly in:
    `docs/knowledge/data/spec/template-consumption.md#requirement-an-expo-consumer-can-build-ios-on-a-mac-host-through-the-bridge`
    ("The protocol contract and security model are specified in
    `plume-works/vscode-expo-bridge` ... not in this repository") — written:
    docs/knowledge/data/spec/template-consumption.md#the-expo-bridges-record-lives-in-its-own-repository
- conflicts: none

## docs/knowledge/data/plans/20261029-catalog-scripts-python.md

- verdict: ALL ALREADY HELD
- owning spec: NONE for the script-language rule (held in
  `docs/knowledge/data/architecture/catalog-script-language.md`; suggest:
  catalog-scripts); git-new-branch for the worktree parent
- conflicts: none. The document's counts and shell file names describe the
  removed shell scripts.

## docs/knowledge/data/plans/20261029-off-bash-migration.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: agentdev-runtime-images (package, doctor, hooks); ai-review-gate
  (responder install)
- unique items:
  - [behaviour] The AI responder's composite action installs `agentdev-runtime`
    from the checkout with `uv tool install` when its pinned image lacks the
    CLI, so the responder keeps working while the image pin trails the package
    (`.github/actions/run-claude-responder/action.yml` › "A pinned image built
    before the runtime package lacks the CLI"). — already partly in: nowhere
    (`docs/knowledge/data/architecture/agentdev-runtime-package.md#a-container-with-no-supervisor`
    lists the lifecycle commands the job runs, not the install) — written:
    docs/knowledge/data/spec/ai-review-gate.md#requirement-the-review-job-reviews-with-the-pr-review-skill-as-a-submitted-review
    (scenario "the pinned image predates the runtime CLI")
  - [constraint] These stay shell and outside the package:
    `.devcontainer/devcontainer-init.sh` (runs on the host as the initialize
    command, where Python is not guaranteed), `docker/ansible/setup-ansible.sh`
    (runs before the toolchain exists), and `docker/desktop/entrypoint.sh`. —
    already partly in: `AGENTS.md` Best Practice 6 (location rule, no reason);
    `docs/knowledge/data/architecture/extra-ca-trust.md`
    ("`devcontainer-init.sh` runs on the host") — written:
    docs/knowledge/data/spec/agentdev-runtime-images.md#one-runtime-package-behind-one-cli
  - [rationale] A missing `language: system` hook executable is a warning, not a
    failure, in both profiles, so a consumer whose own hooks need tools the
    image lacks still starts. — already partly in:
    `docs/knowledge/data/spec/agentdev-runtime-images.md#requirement-missing-pre-commit-hook-executables-are-reported`
    ("SHALL warn, without failing"; no reason) — written:
    docs/knowledge/data/spec/agentdev-runtime-images.md#one-runtime-package-behind-one-cli
  - [non-goal] `agentdev_runtime` is not published to PyPI and is installed only
    in the two runtime images. — already partly in:
    `docs/knowledge/data/architecture/agentdev-runtime-package.md#decision`
    (install path and "`agentdev-base` ... never carries it"; PyPI not
    mentioned) — written:
    docs/knowledge/data/spec/agentdev-runtime-images.md#one-runtime-package-behind-one-cli
- conflicts:
  - ~~Document `## Approach`: "A container with no supervisor socket runs
    `lifecycle ready --no-wait`, one function that starts the CBM daemon and
    then the per-start repairs."
    `docs/knowledge/data/architecture/agentdev-runtime-package.md#a-container-with-no-supervisor`:
    "`ready --no-wait` runs the per-start repairs. Nothing else starts";
    `docs/knowledge/data/architecture/no-code-graph.md`: codebase-memory-mcp was
    removed.~~ — resolved:
    docs/knowledge/data/spec/agentdev-runtime-images.md#requirement-lifecycle-phases-remain-distinct
    matches `lifecycle.py` (per-start repairs only); the plan statement is stale
  - ~~Document: "`doctor` checks the `mcp-gateway` sidecar only when
    [`COMPOSE_PROFILES`] names the opt-in `mcp` profile".
    `py_packages/agentdev_runtime/agentdev_runtime/doctor.py` has no sidecar
    check, and
    `spec/agentdev-runtime-images.md#requirement-doctor-judges-a-healthy-compose-dev-container-healthy`
    states only the git identity rule.~~ — resolved: no spec states a sidecar
    check and `doctor.py` has none; the plan statement is stale
  - ~~Document: "The package pins `supervisor`, `tomlkit`, `json5`, `pyyaml`,
    and `setuptools<85`". Architecture note: "pins `supervisor` and its
    `setuptools<85` requirement, `json5`, and `pyyaml`";
    `py_packages/agentdev_runtime/pyproject.toml` has no `tomlkit`.~~ —
    resolved: no spec names `tomlkit`, matching
    `py_packages/agentdev_runtime/pyproject.toml`; the plan statement is stale
  - ~~Document `## Out of scope` lists `docker/bin/gh`; `docker/bin/` no longer
    exists (the wrapper is installed by the `github_cli` role per
    `spec/agentdev-runtime-images.md#requirement-gh-resolves-to-the-images-wrapper`).~~
    — resolved: the spec names the `github_cli` role wrapper, as the code does;
    the plan statement is stale

## docs/knowledge/data/plans/20261029-remote-control-environment-names.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: claude-remote-control
- unique items:
  - ~~[behaviour] The Compose `devcontainer` service falls back to hostname
    `agentdev` when `CONTAINER_HOSTNAME` is unset, so a direct `docker compose`
    run that skipped `devcontainer-init.sh` still starts
    (`.devcontainer/docker-compose.yml#services.devcontainer.hostname`). —
    already partly in: nowhere~~ — struck: already held by
    docs/knowledge/data/spec/claude-remote-control.md#requirement-the-dev-container-hostname-names-its-launcher
    (scenario "Compose runs without the initialize command")
  - [non-goal] Two containers of the same checkout opened by the same launcher
    on one machine get the same environment name, and a container that is not
    recreated keeps its old name; the standalone and deploy runtimes are not
    named by this rule. — already partly in: nowhere — written:
    docs/knowledge/data/spec/claude-remote-control.md#the-environment-name-says-where-a-dev-container-came-from-not-which-one
- conflicts: none

## docs/knowledge/data/plans/20261030-ai-review-verdicts-and-bot-approval.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: ai-review-gate
- unique items:
  - [rationale] Rejected for trusted-bot approval: a `pull_request_target`
    workflow — it would also approve from Dependabot-triggered runs, but adds a
    dangerous-trigger workflow for a bot this repository does not configure for
    version updates. — already partly in: nowhere
    (`docs/knowledge/data/architecture/ai-review-event-selection.md#alternatives-rejected`
    omits it) — written:
    docs/knowledge/data/spec/ai-review-gate.md#trusted-bot-approval-checks-the-branchs-whole-push-history
  - [rationale] Rejected for trusted-bot pull requests: ruleset bypass for the
    Renovate App — it removes the approval requirement for dependency bumps
    instead of recording an approval on each. — already partly in: nowhere —
    written:
    docs/knowledge/data/spec/ai-review-gate.md#trusted-bot-approval-checks-the-branchs-whole-push-history
- conflicts:
  - ~~Document `## Context` and `## Approach`: "An `APPROVE` from
    `github-actions[bot]` satisfies that approval" and the job "dismisses a
    standing `github-actions[bot]` approval". Spec
    `ai-review-gate.md#requirement-the-responder-acts-as-its-own-github-app`:
    "The review responder and the trusted-bot approval SHALL post with an
    installation token of the `plume-works-quill` App".~~ — resolved:
    docs/knowledge/data/spec/ai-review-gate.md matches `ai-responder.yml`
    (approval posted as `plume-works-quill[bot]`); the plan statement is stale
  - ~~Document: a Dependabot-triggered run is skipped because it "holds a
    read-only `GITHUB_TOKEN`". Spec
    `ai-review-gate.md#requirement-trusted-bot-pull-requests-are-approved-without-an-ai-review`:
    skipped because it "cannot read the App secrets in the `plume-works-review`
    environment".
    `docs/knowledge/data/architecture/ai-review-event-selection.md#trusted-bot-approval-covers-only-the-bots-commits-and-pushes`
    still gives the old reason ("its `GITHUB_TOKEN` is read-only") and still
    names `github-actions[bot]`/`claude[bot]` as reviewer identities.~~ —
    resolved: docs/knowledge/data/spec/ai-review-gate.md matches
    `ai-responder.yml` ("cannot read the App secrets"); the architecture note is
    archived and no spec gives the old reason
  - ~~Document `## Out of scope`: "Moving the reviewer to a GitHub App identity
    (`plume-works-quill[bot]`); a later plan owns it" — since done.~~ —
    resolved: history; the spec records the App identity
  - ~~Document names `post-review.sh`; the code is `post-review.py`.~~ —
    resolved: the spec sources name `post-review.py`; the plan statement is
    stale

## docs/knowledge/data/plans/20261030-dbus-keyring-flaky-test.md

- verdict: ALL ALREADY HELD
- owning spec: standalone-opencode-runtime
- conflicts: none. Note: the fixed behaviour (a confirmed client failure is
  charged to the root-most failing long-running dependency, bypassing the probe
  debounce; Defer rejected; accepted cost) is held only in
  `docs/knowledge/data/architecture/standalone-opencode-runtime.md#recovery`. No
  requirement or scenario in
  `docs/knowledge/data/spec/standalone-opencode-runtime.md` or
  `spec/agentdev-runtime-images.md` states it, so the behaviour needs a
  requirement when the note is folded into Rationale. The document names
  `runtime-health.sh`; the code is `agentdev-runtime health`.

## docs/knowledge/data/plans/20261030-devcontainer-home-volume.md

- verdict: ALL ALREADY HELD
- owning spec: agentdev-runtime-images, catalog-lifecycle, git-new-branch
- conflicts: none. Held in
  `docs/knowledge/data/architecture/devcontainer-home-volume.md`,
  `architecture/uv-environment-location.md`,
  `architecture/devcontainer-runtime.md#lifecycle-ownership`, and
  `spec/catalog-lifecycle.md` (the `~/.claude.json` link replacement).

## docs/knowledge/data/plans/20261030-iwe-branch-name-v2.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-branch-name
- unique items:
  - [rationale] One iteration counter per plan, across phases, exists so that
    `N` is the plan's Nth work branch and the names alone order a plan's pull
    requests; per-phase counters could not say whether `impl/foo/iter-3` came
    before or after `ship/foo/iter-1`. — already partly in:
    `docs/knowledge/data/spec/iwe-branch-name.md#requirement-the-next-iteration-follows-every-iteration-already-used`
    (behaviour only) — written:
    docs/knowledge/data/spec/iwe-branch-name.md#one-iteration-counter-per-plan-under-one-prefix
  - [constraint] The fixed `iwe/` prefix keeps every plan branch in one ref
    namespace, so a branch named after a bare slug never blocks a work branch
    (only a ref named exactly `iwe` or `iwe/<slug>` could, and the tooling makes
    neither); every name ends in `iter-<N>-<phase>`, so no work branch is a path
    prefix of another. — already partly in:
    `docs/knowledge/data/spec/iwe-branch-name.md#requirement-plan-work-branches-carry-phase-slug-and-iteration`
    ("SHALL always include the `iwe/` prefix and the iteration suffix"; no
    reason) — written:
    docs/knowledge/data/spec/iwe-branch-name.md#one-iteration-counter-per-plan-under-one-prefix
  - [rationale] Rejected name shapes: `<slug>/iter-<N>-<phase>` without a prefix
    (a branch named after the bare slug blocks every work branch of that plan),
    and phase-first with a shared counter such as `impl/foo/iter-3` (the phase
    prefix reads as a per-phase count). — already partly in: nowhere — written:
    docs/knowledge/data/spec/iwe-branch-name.md#one-iteration-counter-per-plan-under-one-prefix
  - [non-goal] Names in the first shape (`impl/<slug>/iter-<N>`,
    `ship/<slug>/iter-<N>`) are not work branches, are never counted, renamed,
    or migrated; the maintainer chose a clean break over carrying two shapes, so
    a plan in flight restarts at `iter-1`. — already partly in:
    `docs/knowledge/data/spec/iwe-branch-name.md` scenario "Names from before
    the iwe/ shape are not counted" (behaviour only) — written:
    docs/knowledge/data/spec/iwe-branch-name.md#one-iteration-counter-per-plan-under-one-prefix
  - [constraint] Two checkouts racing may both take one `N` in different phases;
    this is accepted because the maximum still orders every later name after
    both. — already partly in: nowhere — written:
    docs/knowledge/data/spec/iwe-branch-name.md#one-iteration-counter-per-plan-under-one-prefix
- ~~conflicts: Document `## Approach`: "`phase` ∈ `impl`, `ship`" and the regex
  `iwe/([^/]+)/iter-([1-9][0-9]*)-(impl|ship)`. Spec
  `iwe-branch-name.md#requirement-plan-work-branches-carry-phase-slug-and-iteration`:
  "`phase` is `plan`, `impl`, or `ship`". The spec is newer.~~ — resolved: the
  spec matches `iwe-branch-name.py::WORK_BRANCH` (`plan|impl|ship`); the plan
  statement is stale
