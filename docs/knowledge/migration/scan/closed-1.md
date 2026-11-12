# Batch 1 — durable knowledge held only in closed documents

## docs/knowledge/data/plans/20260902-audit-plan-edits-in-fresh-context.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - ~~[rationale] The plan-edit audit runs in a fresh subagent because the
    session that wrote the residue holds the context that buried the rule; a
    self-audit step inside the Plan skill's own context was rejected (re-reads
    the polluted context, and duplicates rule text into each skill), as was each
    caller spawning a generic subagent with the rule inlined (same drift at
    every call site). — already partly in:
    `docs/knowledge/data/spec/iwe-workflow-skills.md` › "A plan edit is audited
    before validation" (behaviour only);
    `docs/knowledge/data/architecture/fresh-context-verify.md#rejected-alternatives`
    names the Durable Knowledge Auditor only as a contrast~~ — struck: already
    held by
    `iwe-workflow-skills#the-durable-knowledge-audit-is-an-isolated-leaf`
  - ~~[constraint] The `Durable Knowledge Auditor` agent carries no rule text
    (it invokes `/agentdev:iwe-audit`) and has no `Edit`/`Write` tools, so
    "report-only" is enforced by tooling rather than instruction. — already
    partly in:
    `.agents/plugins/agentdev/agents/durable-knowledge-auditor.agent.md` (code
    only); nowhere in spec/ or architecture/~~ — struck: already held by
    `iwe-workflow-skills#requirement-the-durable-knowledge-audit-reads-from-a-fresh-context-and-changes-nothing`
    (no `Edit` or `Write` tool, `/agentdev:iwe-audit` its only rulebook) and
    `#the-durable-knowledge-audit-is-an-isolated-leaf` ("cannot edit what it
    reads"); matches the agent's `tools:` line
  - ~~[rationale] One gate in Plan (create and revise) covers every intent edit
    by construction, because every route back from Implement, Verify, and Ship
    funnels through Plan's revise mode; `- **Evidence:**` children are the only
    plan content written outside Plan (by Implement at tick time). — already
    partly in: `docs/knowledge/data/spec/iwe-workflow-skills.md` › "which state
    intent and remain the Plan skill's to own"~~ — struck: already held by
    `iwe-workflow-skills#the-durable-knowledge-audit-is-an-isolated-leaf`
    ("Every plan-intent edit funnels through Plan") and
    `#scenario-a-plan-edit-is-audited-before-validation` (Evidence children left
    out)
- conflicts: ~~plan `## Approach` says Evidence blocks "need the same auditor's
  smell vocabulary applied where Implement writes and Verify checks";
  `docs/knowledge/data/spec/iwe-workflow-skills.md` › "A plan edit is audited
  before validation" says "`- **Evidence:**` children are left out of that
  audit". Not a hard contradiction (different gate), but the Implement/Verify
  side is stated only in `docs/knowledge/data/spec/plan-checkbox-evidence.md` ›
  "it is residue rather than evidence".~~ — struck: no contradiction; the Plan
  gate leaves Evidence out and
  `plan-checkbox-evidence#requirement-a-ticked-task-carries-the-evidence-that-closed-it`
  owns the residue check where Implement writes and Verify checks

## docs/knowledge/data/plans/20260902-persist-pre-commit-cache.md

- verdict: DEAD (subject removed)
- owning spec: NONE (nearest:
  `docs/knowledge/data/architecture/devcontainer-home-volume.md`)
- conflicts: plan sets "`PRE_COMMIT_HOME` in `devcontainer.json`'s
  `containerEnv` to a subfolder of the existing `agentdev-cache` volume";
  `docs/knowledge/data/architecture/devcontainer-home-volume.md#the-account-and-its-volumes`
  says "the pre-commit cache all live there at their default paths" (the home
  volume), and no tracked file sets `PRE_COMMIT_HOME`. The measured 33 s / 935
  MB cold install is also gone:
  `docs/knowledge/data/architecture/formatter-ownership.md#decision` says "No
  hook names a remote repository, so `pre-commit install-hooks` builds no
  environment". The pre-commit fact (store records an absolute path per
  `(repo, ref)`, so a cache is valid only at the path it was installed to and
  must never be copied) is recorded nowhere, but no current design relies on it.

## docs/knowledge/data/plans/20260903-iwe-map-skill.md

- verdict: DEAD (subject removed)
- owning spec: NONE
- conflicts: plan ships "`/agentdev:iwe-map` as the eighth IWE workflow skill";
  no `iwe-map` skill exists under `.agents/plugins/agentdev/skills/`, and
  `docs/knowledge/data/spec/template-consumption.md` › "Requirement: an update
  removes a retired codebase map" treats the map as retired. Note: the decision
  to retire the codebase map, with its reason, was not found in spec/ or
  architecture/ (only the consumer-side removal requirement).

## docs/knowledge/data/plans/20260903-pr-description-guidance.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: template-consumption
- unique items:
  - [rationale] The guidance lives in a separate file, not a block inside
    `.github/pull_request_template.md`: the template stays a pure two-state
    pointer (stub or real template), and template updates can preserve the
    guidance as consumer-created state. — already partly in:
    `docs/knowledge/data/architecture/template-boundary.md` (row
    `.github/pr-description-guidance.md`, classification only) — written:
    `template-consumption#pr-description-guidance-is-a-separate-instruction-file`
  - [rationale] The guidance holds instructions, not section headings: a
    headings list is a structure file by another name, which is what
    `pr-gen-description`'s own section list supersedes; hence capture translates
    `## Rollback plan` into an instruction. — already partly in:
    `docs/knowledge/data/spec/template-consumption.md` › "capturing SHALL
    translate a template section into a generation instruction" (behaviour only)
    — written:
    `template-consumption#pr-description-guidance-is-a-separate-instruction-file`
- conflicts: none

## docs/knowledge/data/plans/20260903-single-ai-review-workflow.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: ai-review-gate
- unique items:
  - [rationale] The gate is a job of the review workflow coupled by `needs:`
    rather than a second workflow re-triggered by `workflow_run`: `workflow_run`
    fixes only the missed-review case, leaves the head SHA with no signal while
    a review runs (so auto-merge can fire mid-review), and moves PR-number
    discovery across runs. — already partly in:
    `docs/knowledge/data/spec/ai-review-gate.md` › "The check SHALL be a job of
    the same workflow as the review job" (behaviour and the pending reason, not
    the rejected alternative) — written:
    `ai-review-gate#the-gate-is-a-job-of-the-review-workflow`
  - ~~[constraint] GitHub starts no workflow run for an event produced with
    `GITHUB_TOKEN` (`workflow_dispatch` is the documented exception), so a gate
    in another workflow cannot observe a review posted with that token. —
    already partly in:
    `docs/knowledge/data/architecture/dispatched-review-identity.md` (mentions
    the token, not this rule); nowhere stated as the reason for needs-coupling~~
    — struck: stale; reviews are now posted by the `plume-works-quill` App token
    (`ai-review-gate#the-responder-posts-as-its-own-github-app`), so the token
    rule no longer bears on the gate, which is coupled by `needs:` for the
    pending signal alone
- conflicts:
  - ~~plan: "Codex web reviews must keep satisfying it" and Out of scope
    "Posting reviews under the Claude App identity. Attribution is unchanged." —
    `docs/knowledge/data/spec/ai-review-gate.md` › "PRs are blocked until an AI
    review exists": "SHALL accept a review only from
    `plume-works-quill[bot]`".~~ — struck: plan statement stale; the spec
    matches `.github/actions/ai-review-status/action.yml` › "const reviewerLogin
    = 'plume-works-quill[bot]'"
  - ~~plan: comment "bridge … then `workflow_dispatch`" —
    `docs/knowledge/data/architecture/pull-request-only-responder.md`: no
    "`workflow_dispatch` trigger, no job that bridges a comment".~~ — struck:
    plan statement stale; `.github/workflows/ai-responder.yml#on` has no
    `workflow_dispatch`, as `ai-review-gate` states
  - ~~plan Out of scope: "A push during a running review. The new head's gate
    passes on the prior review while the older head's run is pending" —
    `.github/workflows/ai-responder.yml#concurrency` sets `cancel-in-progress`
    for `pull_request` `synchronize`, so the older run is cancelled.~~ — struck:
    plan statement stale; the spec's
    `#scenario-a-push-lands-during-a-requested-review` matches the code

## docs/knowledge/data/plans/20260905-consumer-iwe-seed.md

- verdict: ALL ALREADY HELD
- owning spec: template-consumption, iwe-bootstrap
- conflicts: plan: "Keep the canonical seed in `templates/iwe/data/`" and "There
  is no second seed copy inside the plugin" —
  `docs/knowledge/data/spec/template-consumption.md` › "the installed catalog
  owns a complete reusable IWE scaffold": "The installed agentdev catalog SHALL
  carry one complete IWE scaffold … SHALL NOT maintain or copy a second seed
  source"; `templates/` no longer exists. Plan: "run iwe-setup followed by
  iwe-map" — spec invokes `iwe-bootstrap` then `iwe-setup`; `iwe-map` is
  retired.

## docs/knowledge/data/plans/20260905-digest-masks.md

- verdict: DEAD (subject removed)
- owning spec: NONE (the surviving format is in
  `docs/knowledge/data/architecture/agent-metadata-files.md`)
- conflicts: plan adds `iwe-map.digest_ignore`;
  `docs/knowledge/data/spec/template-consumption.md` › "an update removes a
  retired codebase map" removes "the `iwe-map` key" from `.agent.metadata.json`,
  and `stale-map-docs.py` no longer exists.

## docs/knowledge/data/plans/20260905-python-skill-scripts.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: skill-script-result-contract); rationale home
  today is `docs/knowledge/data/architecture/catalog-script-language.md`
- unique items:
  - [constraint] `bin/result_codes.py` names a terminating signal in `RESULT=`,
    then restores the default handler and re-signals itself, so a shell caller
    observes real signal death (negative `returncode`); `sys.exit(128 + signum)`
    is not equivalent. — already partly in:
    `.agents/plugins/agentdev/skills/skill-scripts/SKILL.md` (skill text, not
    spec/ or architecture/) — written:
    `catalog-scripts#a-terminating-signal-is-named-then-re-raised`
- conflicts: ~~plan Out of scope: "`bin/result-codes.sh` stays, and stays the
  implementation they source" —
  `docs/knowledge/data/architecture/catalog-script-language.md#decision`: "Every
  script under the agentdev plugin's `bin/` and `skills/*/agent-code/` is
  Python"; `bin/result-codes.sh` is gone.~~ — struck: plan statement stale;
  `catalog-scripts#requirement-catalog-scripts-are-standard-library-python`
  matches `.agents/plugins/agentdev/bin/`

## docs/knowledge/data/plans/20260905-xpra-vscode-port-forwarding.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: xpra-port-forwarding
- unique items:
  - [rationale] The container port is fixed instead of derived from
    `DEVCONTAINER_ID`: separate devcontainers have separate network namespaces
    so each may listen on the same port, and a hash over 100 values could not
    guarantee uniqueness anyway; local-port conflicts are VS Code's to resolve
    because the Dev Container spec defaults `requireLocalPort` to false. —
    already partly in: `docs/knowledge/data/spec/xpra-port-forwarding.md` ›
    description "VS Code handles local port conflicts" — written:
    `xpra-port-forwarding#one-fixed-container-port-forwarded-explicitly`
  - [rationale] The port is declared explicitly in `forwardPorts` so Xpra's
    availability does not depend on VS Code's process auto-detection. — already
    partly in: nowhere — written:
    `xpra-port-forwarding#one-fixed-container-port-forwarded-explicitly`
  - [non-goal] No automatic server-port allocation for several Xpra servers in
    one network namespace, and no Docker host-port publication. — already partly
    in: nowhere — written:
    `xpra-port-forwarding#one-fixed-container-port-forwarded-explicitly`
- conflicts: ~~plan names the startup script `/start-xpra.sh`;
  `docs/knowledge/data/spec/xpra-port-forwarding.md` names
  `agentdev-runtime xpra`
  (`py_packages/agentdev_runtime/agentdev_runtime/xpra.py`). Old name only.~~ —
  struck: old name only; the spec matches the code

## docs/knowledge/data/plans/20260906-template-consumption-progress.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: template-consumption
- unique items:
  - [rationale] `.agentdev-template-progress.md` lives at the consumer root, not
    in the consumer's IWE graph, because the graph does not exist until the
    bootstrap step (itself one of the tasks) and a consumer who declines IWE
    never has one; a root file gives one mechanism for both. — already partly
    in: `docs/knowledge/data/architecture/template-boundary.md` ›
    "`.agentdev-template-progress.md` is Customize / consumer-created state"
    (classification only) — written:
    `template-consumption#setup-progress-lives-in-a-root-file-the-consumed-ref-stays-in-json`
  - [rationale] `consumed_ref` stays machine-parsed JSON and the progress
    document names the SHA as context only: the JSON has one parse with one
    failure signal (`INVALID_MARKER`), while a SHA in prose has neither, and a
    wrongly advanced ref silently skips upstream changes forever. — already
    partly in: `docs/knowledge/data/spec/template-consumption.md` › "adoption is
    recorded for later updates" (rule without the reason) — written:
    `template-consumption#setup-progress-lives-in-a-root-file-the-consumed-ref-stays-in-json`
  - [rationale] The graph summary never mirrors the task list because two copies
    extended on every update have nothing keeping them in sync; the summary
    records why the consumer is configured this way, the root file stays the
    live record. — already partly in:
    `docs/knowledge/data/spec/template-consumption.md` › "It SHALL NOT mirror
    the task list" (rule without the reason) — written:
    `template-consumption#setup-progress-lives-in-a-root-file-the-consumed-ref-stays-in-json`
- conflicts: none

## docs/knowledge/data/plans/20260907-connect-validator-warnings.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: agent-file-validation, beside
  `agent-file-discovery`)
- unique items:
  - ~~[behaviour] `validate_agent_files --recommend` reports only the
    warning-level findings of `SkillFrontmatterValidator` and
    `SkillStructureValidator`; their error-level checks stay direct-library
    behaviour and are not part of `ValidationEngine.validate`'s contract. —
    already partly in: nowhere (code:
    `py_packages/validate_agent_files/validate_agent_files/core.py::ValidationEngine.validate`)~~
    — struck: already held by
    `agent-file-discovery#requirement-skill-recommendations-add-warnings-only`
    (matches `core.py::ValidationEngine.validate` and `main.py::main`)
  - [rationale] `--no-warnings` was removed rather than repaired because it and
    `--errors-only` resolved to the same `show_warnings = False`; the
    recommendation set was connected as written, not redesigned, since it had
    never been judged insufficient. — already partly in: nowhere — written:
    `agent-file-discovery#one-flag-hides-warnings` (the second clause, that the
    set was not redesigned, is history and was dropped)
- conflicts: none

## docs/knowledge/data/plans/20260909-consolidate-self-improve-plugin.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: self-improve-learning-loop (rationale today in
  `docs/knowledge/data/architecture/self-improve-consolidation.md`)
- unique items:
  - [rationale] The `self-improve` plugin has no `pyproject.toml` or separate
    Python project of its own, unlike `py_packages/validate_agent_files/`: that
    isolation exists only because the validator is released independently, and
    `self-improve` is not. — already partly in:
    `docs/knowledge/data/architecture/module-layout.md` ›
    "`validate_agent_files`'s test suite is deliberately kept separate" (the
    validator's side only) — written:
    `self-improve-learning-loop#the-runtime-is-standard-library-python-behind-one-dispatcher`
    (Rejected bullet)
- conflicts: ~~plan Out of scope: "The role selects its plugin by name and
  asserts exactly one match, so a second entry is invisible to it" —
  `docs/knowledge/data/architecture/self-improve-consolidation.md#the-catalog-is-no-longer-single-plugin`:
  "`agentdev-runtime catalog install` installs every plugin the Claude
  marketplace manifest publishes".~~ — struck: plan statement stale;
  `py_packages/agentdev_runtime/agentdev_runtime/catalog.py` iterates every
  plugin in the marketplace manifest

## docs/knowledge/data/plans/20260909-resumable-claude-review-sessions.md

- verdict: NOTHING DURABLE
- owning spec: ai-review-gate (would have been)
- conflicts: none. The plan is cancelled and nothing implements
  `resume-ai-review`; its decisions and rejected alternatives describe a design
  that is not in force. The extract does not state why it was cancelled, so no
  standing "we will not do this" decision can be taken from it.

## docs/knowledge/data/plans/20260909-self-improve-mvp.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: self-improve-learning-loop
- unique items:
  - ~~[non-goal] The loop has no prompt optimizer, user-authored evaluation
    datasets, or model-generated rubrics treated as proof of improvement; no
    per-turn full `/improve` scan or unattended transcript harvesting; no
    long-term usage scoring or stale-skill curation; no certification for VS
    Code, Desktop, SSH, devcontainer, cloud, or multi-user surfaces; no daemon,
    federation, vector-memory, or model-weight infrastructure. — already partly
    in: `docs/knowledge/data/spec/self-improve-learning-loop.md` (SHALL NOT
    clauses cover auto-memory edits, cleanup, deletion, consolidation, and
    unapproved adoption only)~~ — struck: an MVP scope list with no decision or
    reason behind it; the part that is a decision is held by
    `self-improve-learning-loop#purpose` (no claim that a retained lesson
    improves behaviour) and
    `#requirement-a-deterministic-gate-decides-whether-to-spend-a-review`
- conflicts: none

## docs/knowledge/data/plans/20260917-pr-review-effort-tiers.md

- verdict: ALL ALREADY HELD
- owning spec: ai-review-gate (rationale in
  `docs/knowledge/data/architecture/pr-review-effort-tiers.md`)
- conflicts: plan: "A tier reaches preflight from two channels, an
  `@claude review <label>` comment or a `[ci:review-effort=<label>]` marker" and
  "An explicit override is absolute" —
  `.agents/plugins/agentdev/skills/pr-review/SKILL.md#effort-tiers`: "Nothing
  requests a tier: no PR body marker, label, or prompt line selects one", and
  `docs/knowledge/data/architecture/label-review-triggers.md`: "requested effort
  tiers no longer start or shape a review".
  `docs/knowledge/data/architecture/pr-review-effort-tiers.md` still carries the
  superseded sections "An explicitly requested tier is absolute" and "Why
  preflight resolves the tier"; only the matrix and its reasons remain in force.

## docs/knowledge/data/plans/20260925-bun-for-node-tooling.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: pre-commit-gate, dependency-updates (rationale today in
  `docs/knowledge/data/architecture/formatter-ownership.md`,
  `renovate-config-validation.md`)
- unique items:
  - [constraint] Renovate's `pre-commit` manager reads only a remote repo's
    `rev` and the `additional_dependencies` of `node`, `python`, and `golang`
    hooks; it never parses a `language: system` hook's `entry`, so the
    `bunx <package>@<version>` pins are tracked by a `custom.regex` manager over
    `.pre-commit-config.yaml`. — already partly in:
    `docs/knowledge/data/architecture/renovate-config-validation.md#decision` ›
    "A `custom.regex` manager … tracks that pin" (the fact, not why) — written:
    `pre-commit-gate#javascript-hooks-run-through-bunx` (Rejected bullet)
  - ~~[rationale] Node-based hooks run as `language: system` + `bunx`, not
    `language: node`: pre-commit has no bun backend, so a `language: node` hook
    environment is always built with `npm install`. — already partly in:
    `.pre-commit-config.yaml` (a one-line comment);
    `docs/knowledge/data/architecture/formatter-ownership.md#rejected-alternatives`
    rejects remote hook repositories for a different reason~~ — struck: already
    held by `pre-commit-gate#javascript-hooks-run-through-bunx`
  - [non-goal] The bun-only rule governs how this repository runs JavaScript,
    not what the image ships: Node.js with its bundled `npm`, and Yarn
    (installed by the `nodejs` role as a bun global), stay in the image for its
    users. — already partly in: nowhere — written:
    `pre-commit-gate#the-bun-rule-governs-how-this-repository-runs-javascript`
- conflicts: ~~plan: "The Prettier version still follows the Super-Linter image:
  `scripts/validate-super-linter-tool-versions.sh`" —
  `docs/knowledge/data/architecture/formatter-ownership.md#rejected-alternatives`:
  "Super-Linter as the CI gate" rejected; the script no longer exists.~~ —
  struck: plan statement stale; the Prettier pin is the hook's `bunx` entry, as
  `pre-commit-gate` states

## docs/knowledge/data/plans/20260925-self-hosted-renovate.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: dependency-updates (rationale today in
  `docs/knowledge/data/architecture/renovate-post-upgrade.md`,
  `renovate-config-validation.md`)
- unique items:
  - ~~[rationale] Renovate is self-hosted in a repository workflow because the
    hosted app cannot run commands after a bump (`allowedCommands` is
    global-only), which leaves checksums, tool-owned lock files, and pre-commit
    output stale; it runs in the devcontainer image so those commands use the
    contributors' toolchain with no second provisioning path. — already partly
    in:
    `docs/knowledge/data/architecture/renovate-config-validation.md#why---no-global`
    (names `allowedCommands` as global-only);
    `docs/knowledge/data/spec/dependency-updates.md` › "produced by the same
    toolchain contributors use"~~ — struck: already held by
    `dependency-updates#renovate-runs-self-hosted-as-a-github-app` (the hosted
    app rejected for not running the post-upgrade task in the contributor
    toolchain)
  - ~~[rationale] Renovate authenticates as a GitHub App so that its pull
    requests start CI. — already partly in:
    `docs/knowledge/data/architecture/renovate-post-upgrade.md#the-app-token-carries-only-renovates-permissions`
    (token scope, not why an App)~~ — struck: already held by
    `dependency-updates#renovate-runs-self-hosted-as-a-github-app`
  - [non-goal] No check asserts that every copy of the image digest agrees: the
    Renovate group rule moves them together and a hand edit that splits them is
    reviewed like any other change. — already partly in:
    `docs/knowledge/data/architecture/renovate-config-validation.md#the-workflow-is-the-image-canary`
    (the group rule only) — written:
    `image-pinning#digest-copies-agree-through-one-renovate-group`
  - ~~[non-goal] Publisher signatures (for example a sigstore bundle) are not
    verified; a recomputed checksum is trust-on-first-use. — already partly in:
    nowhere~~ — struck: already held by
    `dependency-updates#a-recomputed-checksum-is-trust-on-first-use`
- conflicts:
  - ~~plan Out of scope: "The Ubuntu base release, which Renovate stays disabled
    for" — `docs/knowledge/data/spec/image-pinning.md` › "Requirement: the
    Ubuntu base is pinned by digest and refreshed weekly"
    (`.github/renovate.json` carries the weekly rule).~~ — struck: plan
    statement stale; the spec matches `.github/renovate.json`
  - ~~plan: runs "inside `ghcr.io/plume-works/agent-desktop`" and pins Renovate
    through "the hook's `rev`" —
    `docs/knowledge/data/architecture/renovate-config-validation.md#decision`:
    the image is `agentdev-devcontainer` and the pin is the hook's
    "`bunx --package renovate@<version>` entry".~~ — struck: plan statement
    stale;
    `dependency-updates#requirement-the-renovate-config-is-validated-at-the-bots-version`
    states the current pin
  - ~~plan: the script "regenerates the devcontainer lock when
    `devcontainer.json` changed" —
    `docs/knowledge/data/architecture/renovate-post-upgrade.md#decision` lists
    checksums, `iwe normalize`, and pre-commit only.~~ — struck: plan statement
    stale; `scripts/renovate-post-upgrade.py` regenerates no devcontainer lock,
    as
    `dependency-updates#requirement-derived-files-are-regenerated-with-the-bump`
    states

## docs/knowledge/data/plans/20260927-iwe-capture-skill.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [rationale] `/agentdev:iwe-capture` is model-invocable, unlike
    `/agentdev:iwe-plan`, because Implement must be able to file a deferred task
    or a defect mid-run without stopping for the user. — already partly in:
    `docs/knowledge/data/architecture/explicit-only-workflow-agents.md` (lists
    the explicit-only skills; Capture's exemption and reason not stated) —
    written:
    `iwe-workflow-skills#ship-is-gated-implement-and-verify-are-model-invocable`
  - [rationale] Issue closing has one implementation in the shared
    `bin/github_issue.py`; Capture calling `iwe-plan`'s close script was
    rejected (couples one skill to another's `--plan` contract) and a second
    copy was rejected as duplication. — already partly in:
    `docs/knowledge/data/architecture/catalog-script-language.md#constraints` ›
    "A skill never imports a sibling skill's code. Code two skills share moves
    to `bin/`" (general rule) — written:
    `iwe-workflow-skills#issue-closing-has-one-implementation-in-bin`
- conflicts: ~~plan names `bin/github-issue.sh` and `close-issue.sh`; the
  catalog now ships `bin/github_issue.py` (old names only).~~ — struck: old
  names only

## docs/knowledge/data/plans/20260928-git-new-branch-skill.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: git-new-branch
- unique items:
  - [rationale] The branch is created `--no-track`: a branch made with
    `git switch -c X origin/main` tracks the base, so `git pull` pulls the base
    and `pr-open`'s `find-branch-pr` refuses it as `PROTECTED_BRANCH` ("the
    upstream it tracks is `main`"). — already partly in:
    `docs/knowledge/data/spec/git-new-branch.md` › "SHALL NOT set the base as
    the branch's upstream" (rule without reason) — written:
    `git-new-branch#the-branch-tracks-its-own-upstream-from-creation`
  - [rationale] The push happens at creation, not at the first commit: deferring
    it leaves the upstream unset in between and makes `pr-open` finish the
    setup. — already partly in: `docs/knowledge/data/spec/git-new-branch.md` ›
    "SHALL push the branch immediately" (rule without reason) — written:
    `git-new-branch#the-branch-tracks-its-own-upstream-from-creation`
  - [constraint] The script pops only the stash entry it created, located by its
    commit (`STASH_SHA`), never whatever is at `stash@{0}`; when the branch or
    worktree cannot be created it pops the changes back and names the entry as
    `STASH_REF` if that pop fails. — already partly in:
    `docs/knowledge/data/spec/git-new-branch.md` › "Scenario: Nothing was
    stashed" (pre-existing entry untouched; the `CREATE_FAILED` restore is not
    stated) — written:
    `git-new-branch#requirement-uncommitted-changes-survive-branch-creation` and
    `#scenario-the-branch-cannot-be-created-after-stashing` (behaviour, so a
    requirement and scenario rather than Rationale)
  - ~~[non-goal] Branch creation never rebases local commits, and never deletes
    or prunes branches or worktrees. — already partly in: `AGENTS.md` ("NEVER
    rebase or reset a branch that has been pushed"), not in the spec~~ — struck:
    the no-rebase half is held by
    `git-new-branch#requirement-commits-on-the-default-branch-move-to-the-new-branch`
    (the base is merged in); the no-prune half is a scope line with no decision
    behind it, and the spec's requirements state the skill's whole effect
- conflicts: ~~plan: "a plan key `data/plans/<date>-<slug>` → `<slug>`" as the
  suggested branch name — `docs/knowledge/data/spec/iwe-branch-name.md` names
  plan work branches `iwe/<slug>/iter-<N>-plan|impl|ship`. Plan's worktree
  parent rule ("`/workspaces` when the main checkout lives directly under
  `/workspaces`") is narrower than `docs/knowledge/data/spec/git-new-branch.md`
  › "Worktree mode leaves the current checkout alone" (deploy mode and
  unwritable `/workspaces` go to `.worktrees/`); the spec is current.~~ —
  struck: plan statements stale; `iwe-branch-name` and
  `git-new-branch#requirement-worktree-mode-leaves-the-current-checkout-alone`
  match the code

## docs/knowledge/data/plans/20260929-map-refresh-before-push.md

- verdict: DEAD (subject removed)
- owning spec: NONE
- conflicts: plan: "`push-branch.sh` … runs `stale-map-docs.py` immediately
  before it pushes" with `MAP_STALE` and `--skip-map-check` —
  `.agents/plugins/agentdev/skills/pr-open/agent-code/push-branch.py` contains
  no map check and `stale-map-docs.py` no longer exists. `push-branch.py` is
  still the push path of `pr-open`, `update-branch`, `pr-feedback-resolution`,
  and `pr-merge`, but the only reason this plan gives for a single agent push
  path is the removed map gate.
