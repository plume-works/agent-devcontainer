# Batch 7 scan

## docs/knowledge/data/bugs/dispatched-review-gate-not-counted.md

- verdict: ALL ALREADY HELD
- owning spec: ai-review-gate (held in
  `architecture/assignee-review-trigger.md#which-runs-the-gate-is-counted-from`:
  `workflow_dispatch` suites not counted, `needs:` coupling holds inside one
  run, a `GITHUB_TOKEN` review raises no `pull_request_review` event)
- conflicts: none

## docs/knowledge/data/bugs/doctor-fails-healthy-claude-cloud-devcontainer.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: cloud-session-host; today
  `architecture/cloud-session-host-toolchain.md`)
- unique items:
  - [constraint] In a Claude Code cloud session the agent proxy injects git's
    HTTP authentication, so no `credential.https://github.com.helper` exists and
    its absence is not missing auth; the proxy also answers the bare root
    `https://github.com/` with 400 while serving repository paths with 200. —
    already partly in: `architecture/cloud-session-host-toolchain.md` (GraphQL
    refusal, `gh auth status` false negative, and "only a repository-scoped path
    shows whether a container reaches GitHub" are held; the credential-helper
    fact is not) — written:
    `spec/cloud-session-host.md#the-agent-proxy-owns-the-sessions-github-access`
- conflicts: none

## docs/knowledge/data/bugs/doctor-fails-healthy-coder-devcontainer.md

- verdict: ALL ALREADY HELD
- owning spec: agentdev-runtime-images
  (`#requirement-doctor-judges-a-healthy-compose-dev-container-healthy` holds
  the git-identity rule; the `mcp-gateway` half is dead — no `mcp-gateway`
  service or `COMPOSE_PROFILES` check remains in the code)
- conflicts: none

## docs/knowledge/data/bugs/eval-skips-rereview-after-changes-requested.md

- verdict: ALL ALREADY HELD
- owning spec: ai-review-refresh (requirement "every push to a reviewed pull
  request is evaluated" holds the newest-verdict rule; the reason — only the AI
  reviewer's own `APPROVE` lifts its `CHANGES_REQUESTED` — is in
  `architecture/ai-review-event-selection.md`)
- conflicts: none

## docs/knowledge/data/bugs/fisher-install-over-untracked-plugins.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: image-provisioning-roles; nearest existing is
  agentdev-runtime-images)
- unique items:
  - [constraint] `fisher install <owner>/<repo>@<ref>` refuses to overwrite
    files it does not track under that exact spec, so the `fish_setup` role
    writes the pinned specs into `fish_plugins` and runs `fisher update`, which
    reconciles the tree to that file and converges both from an empty system and
    from one holding the same plugins under a different spec. — already partly
    in: nowhere (only a code comment in
    `ansible/roles/fish_setup/tasks/main.yml`) — written:
    `spec/agentdev-runtime-images.md#fish-plugins-are-reconciled-through-fish_plugins`
- conflicts: none

## docs/knowledge/data/bugs/fixture-git-inherits-commit-index.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: test-isolation; nearest existing is
  pre-commit-gate, whose hook tests apply the rule)
- unique items:
  - [constraint] (test harness only) `git commit -a` exports an absolute
    `GIT_INDEX_FILE` to hooks, so a test that runs git in a nested fixture
    repository from a hook must strip the inherited `GIT_*` variables or its
    `git add`/`git commit` write the outer repository's index; a plain
    `git commit` exports a relative path and hides the defect. — already partly
    in: nowhere (the named fixture `production_mask_workspace` is removed;
    `scripts/tests/test_gitleaks_hook.py` and
    `scripts/tests/test_pre_commit_ci_range.py` still unset `GIT_DIR`,
    `GIT_INDEX_FILE`, `GIT_WORK_TREE`) — written: `AGENTS.md#tests`
- conflicts: none

## docs/knowledge/data/bugs/gh-stack-install-needs-token.md

- verdict: DEAD (subject removed)
- owning spec: stacked-prs (gh-stack is no longer installed;
  `architecture/manual-stacked-prs.md`)
- conflicts: none

## docs/knowledge/data/bugs/gh-stack-push-overwrites-remote-layer.md

- verdict: DEAD (subject removed)
- owning spec: stacked-prs (`gh stack`, `stack-guard.sh`, and force-pushes are
  gone; the standing "never force-push, never `gh stack`" decision is in
  `AGENTS.md` and `architecture/manual-stacked-prs.md`)
- conflicts: none

## docs/knowledge/data/bugs/git-new-branch-worktree-mode-mismatch.md

- verdict: ALL ALREADY HELD
- owning spec: git-new-branch
  (`#requirement-worktree-mode-leaves-the-current-checkout-alone`, scenarios
  "Deploy runtime" and "An account that cannot write /workspaces")
- conflicts: none

## docs/knowledge/data/bugs/git-new-branch-worktree-unwritable-workspaces.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: git-new-branch
- unique items:
  - [rationale] The deploy image mounts only `/workspaces/project` (named volume
    or host bind); `/workspaces` itself is created root-owned by the image's
    `WORKDIR` and lives in the container layer, so a worktree there is
    unwritable for the agent user and lost when the container is recreated —
    which is why deploy mode puts worktrees in `<checkout>/.worktrees/`. —
    already partly in: `spec/git-new-branch.md` (behaviour only, no reason) —
    written: `spec/git-new-branch.md#deploy-worktrees-live-inside-the-checkout`
- conflicts: this document says "Under `AGENTDEV_RUNTIME_MODE=standalone`,
  worktree mode without `--worktree-root` uses `<checkout>/.worktrees/`";
  `spec/git-new-branch.md` says "under the checkout's ignored `.worktrees/`
  directory when `AGENTDEV_RUNTIME_MODE` is `deploy`" (the later bug
  `git-new-branch-worktree-mode-mismatch` corrected the value). — resolved: the
  spec matches the code
  (`.agents/plugins/agentdev/skills/git-new-branch/agent-code/git-new-branch.py::worktree_parent`
  keys on `deploy`); the bug's `standalone` is stale

## docs/knowledge/data/bugs/image-build-context-whole-repo.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: agentdev-runtime-images
- unique items:
  - [rationale] BuildKit keys a `RUN` step on the contents of its bind mounts,
    so a provisioning step that binds the whole build context is invalidated by
    any repository change and the Actions layer cache never hits; that is why
    `.dockerignore` is an allow-list and each provisioning step bind-mounts only
    its own inputs. — already partly in:
    `spec/agentdev-runtime-images.md#requirement-image-builds-read-only-their-declared-inputs`
    (behaviour), `architecture/template-boundary.md` (allow-list stated, not the
    BuildKit reason) — written:
    `spec/agentdev-runtime-images.md#the-build-context-is-an-allow-list-and-each-step-binds-only-its-inputs`
- conflicts: none

## docs/knowledge/data/bugs/main-image-rebuild-lost-on-cancel.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: image-pinning (it lists `.github/actions/paths-filter/action.yml`
  as a source); NONE for the general CI rule (suggest: ci-path-filter)
- unique items:
  - [behaviour] On a push to its base branch, the shared `paths-filter` action
    filters from the head commit of the calling workflow's last successful
    `push` run on that branch, so commits whose runs were cancelled or failed
    stay in the compared range until a run passes; with no earlier passing run
    or a failed lookup it warns and falls back to the previous push. Every job
    running the action needs `actions: read`. — already partly in: nowhere
    (code: `.github/actions/paths-filter/action.yml`,
    `scripts/tests/test_paths_filter_last_pass.py`) — written:
    `spec/ci-workflows.md#requirement-a-push-to-the-base-branch-filters-paths-from-the-last-passing-run`
    (per the code, only a failed lookup warns; no earlier passing run falls back
    silently)
  - [constraint] `dorny/paths-filter` with `base` equal to the pushed branch
    compares only against the previous push (`github.event.before`), so any
    workflow that cancels in-progress runs on `main` would otherwise drop the
    cancelled commit's path matches. — already partly in: nowhere — written:
    `spec/ci-workflows.md#paths-are-filtered-from-the-last-passing-run`
- conflicts: the document describes Primary checks as `cancel-in-progress: true`
  on `main`; `spec/image-pinning.md` now says "Primary checks runs on `main`
  SHALL NOT cancel one another" (old state, superseded; the validate-* workflows
  still cancel, so the lookup is still load-bearing). — resolved: the spec
  matches `.github/workflows/primary-checks.yml#concurrency`; the bug's
  description is stale

## docs/knowledge/data/bugs/metadata-gate-review-blocks-rerequest.md

- verdict: ALL ALREADY HELD
- owning spec: ai-review-refresh (the "after the latest title or description
  edit" clauses and scenarios)
- conflicts: none

## docs/knowledge/data/bugs/missing-map-skill.md

- verdict: DEAD (subject removed)
- owning spec: NONE (`iwe-map` and `data/codebase/` are retired;
  `spec/template-consumption.md#requirement-an-update-removes-a-retired-codebase-map`,
  `architecture/no-code-graph.md`)
- conflicts: none

## docs/knowledge/data/bugs/opencode-config-reordered-on-restart.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: devcontainer-opencode-policy
- unique items:
  - [behaviour] `apply_policy` keeps every existing key of `opencode.json` in
    place and only replaces the values of the managed keys, adding `$schema`
    first and `permission` last only when missing, so configuring an
    already-configured file leaves it byte-identical. — already partly in:
    `spec/devcontainer-opencode-policy.md` scenario "the config carries catalog
    and user settings" (values survive; key order and byte-identity are not
    stated); `spec/catalog-lifecycle.md` scenario "the container restarts with
    an unchanged catalog" states byte-identity for the catalog step only —
    written:
    `spec/devcontainer-opencode-policy.md#requirement-devcontainer-opencode-runs-with-unrestricted-filesystem-access`
    and its scenario "the container restarts with a configured config"
- conflicts: none

## docs/knowledge/data/bugs/opencode-web-tmux-shared-under-xdist.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: test-isolation; nearest existing is opencode-web)
- unique items:
  - [constraint] (test harness only) A test that starts a real tmux server on a
    fixed `-L` socket name must set `TMUX_TMPDIR` to its own scratch directory;
    with a shared directory every pytest-xdist worker reaches the same server
    and one test's `kill-server` teardown kills another's. — already partly in:
    nowhere (`AGENTS.md` only fixes test scratch under `/tmp`) — written:
    `AGENTS.md#tests`
- conflicts: none

## docs/knowledge/data/bugs/pin-bumps-invalidate-map-docs.md

- verdict: DEAD (subject removed)
- owning spec: NONE (map docs and their `source_digest` masks are retired; the
  surviving `.agent.metadata.json` format and its rejected single-repository-map
  alternative are in `architecture/agent-metadata-files.md`)
- conflicts: none

## docs/knowledge/data/bugs/plan-checkbox-over-claiming.md

- verdict: ALL ALREADY HELD
- owning spec: plan-checkbox-evidence (purpose, evidence requirement, hook,
  Verify testing ticked boxes)
- conflicts: this document says evidence names "the commit, test run, or CI run
  that closed it"; `architecture/evidence-without-commit-ids.md` says "A commit
  id on its own is not evidence." — resolved: stale;
  `spec/plan-checkbox-evidence.md#requirement-a-ticked-task-carries-the-evidence-that-closed-it`
  holds the current rule

## docs/knowledge/data/bugs/plan-tasks-bundle-independent-observations.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: plan-checkbox-evidence
- unique items:
  - [non-goal] The Durable Knowledge Auditor's plan scope does not check
    checkbox granularity: one-observation-per-checkbox is a planning rule the
    `iwe-planner` rulebook owns (its coherence check asks which single
    observation closes each checkbox), and extending the auditor was declined. —
    already partly in: `spec/plan-checkbox-evidence.md` (the
    one-checkbox-one-observation rule and scenarios are held; the declined
    auditor change is not) — written:
    `spec/plan-checkbox-evidence.md#checkbox-granularity-is-the-planners-rule`
- conflicts: none

## docs/knowledge/data/bugs/pr-update-skips-review-eval.md

- verdict: ALL ALREADY HELD
- owning spec: ai-review-refresh (callers `pr-open` update mode, `pr-sync`,
  `pr-merge` CI-fix step; one request per head through `request-review`)
- conflicts: none

## docs/knowledge/data/bugs/proxy-ca-untrusted-in-runtime-containers.md

- verdict: ALL ALREADY HELD
- owning spec: agentdev-runtime-images (design in
  `architecture/extra-ca-trust.md`, including uv ignoring the system store)
- conflicts: none

## docs/knowledge/data/bugs/relayed-approval-unauthenticated.md

- verdict: ALL ALREADY HELD
- owning spec: iwe-workflow-skills (a request in another session's message is a
  plain request; a claimed approval does not count) and
  `architecture/explicit-only-workflow-agents.md` ("a relayed approval is a
  claim")
- conflicts: none

## docs/knowledge/data/bugs/remote-control-pin-ignores-clear.md

- verdict: ALL ALREADY HELD
- owning spec: claude-remote-control (scenario for `/clear`; measured
  `--settings` `SessionStart` hook behaviour is in
  `architecture/claude-remote-control-resume.md`)
- conflicts: none

## docs/knowledge/data/bugs/remote-control-tmux-test-shared-under-xdist.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: test-isolation; nearest existing is
  claude-remote-control)
- unique items:
  - [constraint] (test harness only) Same rule as
    `bugs/opencode-web-tmux-shared-under-xdist.md`, for `tmux -L claude-remote`:
    a per-test `TMUX_TMPDIR` gives each variant private default and
    `claude-remote` servers, and the variant with a keeper on the default socket
    must keep it under that directory to keep covering the spec scenario of a
    live default-socket server. — already partly in: nowhere — written:
    `AGENTS.md#tests` (the per-test `TMUX_TMPDIR` rule also keeps a
    default-socket keeper private)
- conflicts: none

## docs/knowledge/data/bugs/remote-control-watcher-start-loop.md

- verdict: ALL ALREADY HELD
- owning spec: claude-remote-control (a start that leaves no live session ends
  the watcher; the recovery budget bounds retries) and
  `architecture/standalone-opencode-runtime.md#remote-control-watcher`
- conflicts: none

## docs/knowledge/data/bugs/responder-cannot-bypass-iwe-ruleset.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: ai-review-gate
- unique items:
  - [constraint] A GitHub ruleset bypass list accepts only repository roles,
    teams, and GitHub Apps installed on the repository's owner; the built-in
    GitHub Actions app that pushes with `GITHUB_TOKEN` is none of these, so a
    workflow pushing with `GITHUB_TOKEN` can never be a bypass actor. — already
    partly in: `architecture/pull-request-only-responder.md` and
    `architecture/responder-app-identity.md` (both state that no responder job
    pushes so no bypass is needed; neither states the GitHub limit) — written:
    `spec/ai-review-gate.md#the-responder-posts-as-its-own-github-app`
- conflicts: none

## docs/knowledge/data/bugs/responder-mention-case-sensitivity.md

- verdict: DEAD (subject removed)
- owning spec: ai-review-gate (the `@claude` mention path, the bridge, and
  `mentions()` are gone from `.github/workflows/ai-responder.yml`)
- conflicts: none

## docs/knowledge/data/bugs/review-orchestrator-ends-turn-while-passes-run.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: pr-review; nearest existing is ai-review-gate,
  which lists `pr-review/SKILL.md` as a source)
- unique items:
  - ~~[constraint] A headless `claude -p` session ends when its turn ends and no
    later notification resumes it, so background subagents dispatched in the
    final turn are never collected. — already partly in: nowhere (only
    `.agents/plugins/agentdev/skills/pr-review/SKILL.md`)~~ — struck: already
    held by `spec/pr-review.md#passes-are-collected-through-foreground-calls`
  - ~~[behaviour] `pr-review` dispatches every Claude Code pass and validator as
    foreground `Agent` calls (`run_in_background: false`) in a single message,
    which run in parallel and return only when all have finished; nothing waits
    through a separate tool, and the responder job's `timeout-minutes` bounds
    the whole review. — already partly in: nowhere in spec/ or architecture/~~ —
    struck: already held by
    `spec/pr-review.md#requirement-a-batch-of-passes-runs-as-foreground-calls`
- conflicts: none

## docs/knowledge/data/bugs/runner-label-ahead-of-actionlint.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: dependency-updates
- unique items:
  - [constraint] actionlint validates GitHub-hosted runner labels against a list
    compiled into the binary, and Renovate can propose a new label before any
    actionlint release knows it; the accepted bridge is declaring the label
    under `self-hosted-runner.labels` in `.github/actionlint.yml` until a
    release knows it. — already partly in: nowhere (`.github/actionlint.yml` no
    longer exists; the workflows now use `ubuntu-26.04`) — written:
    `spec/dependency-updates.md#runner-labels-move-only-where-renovate-can-read-them`
  - [constraint] Renovate rewrites only literal `runs-on` labels;
    expression-form labels
    (`vars.AMD_ONLY == '1' && 'ubuntu-24.04' || 'ubuntu-24.04-arm'`) are not
    extracted, so a runner bump leaves the workflows on mixed releases. —
    already partly in: nowhere (the mixed state is visible in
    `.github/workflows/ai-responder.yml` today) — written:
    `spec/dependency-updates.md#runner-labels-move-only-where-renovate-can-read-them`
- conflicts: none

## docs/knowledge/data/bugs/self-test-unwritable-root-check.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: self-improve-learning-loop
- unique items:
  - [constraint] (test harness only) Permission-bit checks are unreachable as
    failures for UID 0 (`CAP_DAC_OVERRIDE`), so the self-improve
    unwritable-state-root test is skipped when run as root; covering root needs
    a refusal privilege does not bypass, such as a read-only mount. — already
    partly in: nowhere (`architecture/self-improve-runtime.md` covers state-root
    resolution only) — written: `AGENTS.md#tests`
- conflicts: none

## docs/knowledge/data/bugs/shared-uv-environment-across-worktrees.md

- verdict: ALL ALREADY HELD
- owning spec: agentdev-runtime-images
  (`#requirement-each-checkout-has-its-own-project-environment`; reasons in
  `architecture/uv-environment-location.md`)
- conflicts: none

## docs/knowledge/data/bugs/ship-ignores-unshipped-dependency.md

- verdict: ALL ALREADY HELD
- owning spec: iwe-workflow-skills
  (`#requirement-ship-waits-for-every-dependency`)
- conflicts: ~~this document says every `## Depends on` plan "must be
  `stage: done` at the remote default branch, read through
  `/agentdev:iwe-branch-name plan-state`"; `spec/iwe-workflow-skills.md` says
  Ship SHALL "read the stage of every plan in the plan's `## Depends on` in the
  checkout, never on another branch".~~ — resolved: stale; the spec is right —
  `iwe-shipper.agent.md#steps` reads each dependency through
  `iwe-branch-name plan-state`, whose `iwe-branch-name.py::read_plan_state`
  reads the working tree; written:
  `spec/iwe-workflow-skills#requirement-ship-waits-for-every-dependency`

## docs/knowledge/data/bugs/ship-release-link-without-feature.md

- verdict: ALL ALREADY HELD
- owning spec: iwe-workflow-skills (the `release` value requirement; "SHALL
  never create a feature")
- conflicts: none

## docs/knowledge/data/bugs/skip-ai-review-marker-overreach.md

- verdict: DEAD (subject removed)
- owning spec: ai-review-gate (no `[ci:skip-ai-review]` marker remains in
  `.github/workflows/ai-responder.yml` or the spec)
- conflicts:
  `architecture/assignee-review-trigger.md#behaviour-of-the-assignee-trigger`
  still says "**The skip marker wins.** `[ci:skip-ai-review]` is evaluated
  before the…", while this document says "an explicit request outranks the
  marker"; the current workflow has no marker at all. — resolved: no spec or
  workflow carries the marker and the note is archived; nothing to correct

## docs/knowledge/data/bugs/stack-guard-reverts-post-merge-rebase.md

- verdict: DEAD (subject removed)
- owning spec: stacked-prs (the replacement — merges only, `pr-restack-all` — is
  in `architecture/manual-stacked-prs.md`)
- conflicts: none

## docs/knowledge/data/bugs/standalone-codex-auth-unshared.md

- verdict: DEAD (subject removed)
- owning spec: NONE (Codex support removed;
  `architecture/supported-harnesses.md`)
- conflicts: none

## docs/knowledge/data/bugs/supervision-orphan-kill-test-flaky.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: standalone-opencode-runtime
- unique items:
  - [constraint] (test harness only) `os.kill(pid, 0)` succeeds on a zombie, and
    an orphan in a container is reaped by PID 1's supervisord only on its next
    poll, so supervision tests must judge "no longer running" with a
    zombie-aware helper and poll; and a fake service's child must not inherit
    the `exec` wrapper's stdout, or the wrapper outlives the service and
    supervisord's `killasgroup` — not `Controller.restart`'s `os.killpg` — ends
    the orphan, leaving the group kill untested. — already partly in:
    `architecture/standalone-opencode-runtime.md#recovery` (states the
    controller's group kill and that supervisord signals a group only on an
    orderly stop; nothing on the test constraints) — written: `AGENTS.md#tests`
- conflicts: none

## docs/knowledge/data/bugs/supervisor-client-recovered-before-dependency.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: standalone-opencode-runtime
- unique items:
  - ~~[rationale] Rejected: not charging a client's recovery budget while its
    dependency is down — it still restarts the client against a dead dependency
    and removes the budget's bound on those restarts. — already partly in:
    `architecture/standalone-opencode-runtime.md#recovery` (holds the escalation
    rule, its accepted cost, and the rejected "defer the client"; for this
    alternative it only points at this bug)~~ — struck: already held by
    `spec/standalone-opencode-runtime.md#a-client-failure-is-charged-to-its-failing-dependency`
  - ~~[rationale] Rejected: dependency-ordered recovery — it covers the case but
    is the general init-system behaviour deliberately held back
    (`someday/dependency-ordered-recovery.md`), and the defect does not need it.
    — already partly in: same note, by pointer to this bug only~~ — struck:
    already held by
    `spec/standalone-opencode-runtime.md#a-client-failure-is-charged-to-its-failing-dependency`
- conflicts: none

## docs/knowledge/data/bugs/validator-warning-visibility.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: validate-agent-files-cli; nearest existing is
  agent-file-discovery, which covers discovery only)
- unique items:
  - [behaviour] `validate_agent_files --recommend` runs
    `SkillFrontmatterValidator` and `SkillStructureValidator` from
    `ValidationEngine.validate` and surfaces only their warning-level issues, so
    their stricter error checks do not widen the default validation contract;
    `--errors-only` is the one flag that hides warnings (`--no-warnings` was
    removed). — already partly in: nowhere — written:
    `spec/agent-file-discovery.md#requirement-skill-recommendations-add-warnings-only`
- conflicts: none

## docs/knowledge/data/bugs/workspace-image-lacks-hook-binaries.md

- verdict: ALL ALREADY HELD
- owning spec: agentdev-runtime-images (doctor lists `gitleaks` and
  `actionlint`; `project hooks` warns for a `language: system` hook whose
  executable is missing)
- conflicts: none

## docs/knowledge/data/bugs/xpra-setup-installs-ubuntu-xpra.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: agentdev-runtime-images (role) and standalone-opencode-runtime
  (runtime side)
- unique items:
  - [constraint] No Xpra apt repository serves an exact pinned version: for
    noble `https://xpra.org/lts` serves 5.1.x and `https://xpra.org` the current
    6.x stable, so the role installs `xpra` by name from the stable repository
    through a deb822 source, with no `setup.py install-lts-repo` step (which
    ignores its own step failures). — already partly in:
    `architecture/no-launchpad-ppas.md` (lists `xpra_setup` as a
    vendor-repository role), `architecture/ansible-apt-pins.md` (unpinned apt in
    general) — written:
    `spec/agentdev-runtime-images.md#xpra-is-installed-by-name-from-the-stable-repository`
    (the code adds a one-line `apt_repository` source, not deb822)
  - [behaviour] The `xpra_setup` role runs an upgrade-only step after install,
    because CI builds on the previous image where `state: present` keeps
    Ubuntu's already-installed package, and then asserts the installed `xpra`
    major version is at least 6 so a fallback to Ubuntu's 3.x fails the build. —
    already partly in: nowhere — written:
    `spec/agentdev-runtime-images.md#requirement-the-image-carries-xpra-6-or-newer`
  - [constraint] Xpra 6 rejects `--global-menus` and `--dbus-proxy`, and names
    its X server `Xvfb-for-Xpra-N` where Xpra 3 used `Xvfb-for-Xpra-:N`; the
    orphaned-display reclaim must accept both names or a crashed Xpra's X server
    keeps the display locked. — already partly in:
    `architecture/standalone-opencode-runtime.md#recovery` (the
    leftover-X-server stop, not the naming) — written:
    `spec/standalone-opencode-runtime.md#xpra-is-driven-with-xpra-6s-command-line-and-both-x-server-names`
- conflicts: none

## docs/knowledge/data/bugs/xpra-test-displays-collide-under-xdist.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: test-isolation; nearest existing is
  standalone-opencode-runtime)
- unique items:
  - [constraint] (test harness only) X displays are host-global and `xpra list`
    sees sessions across private `HOME`/`XDG_RUNTIME_DIR`, so supervised-Xpra
    tests give each xdist worker a disjoint display block
    (`:200 + 20 * <worker index>`), rotate within it, and stay clear of the
    runtime default `:100`; two concurrent pytest runs on one host are not
    covered. The runtime's refusal of an occupied display is correct, since it
    owns one desktop per container. — already partly in: nowhere — written:
    `AGENTS.md#tests`
- conflicts: none

## docs/knowledge/data/bugs/zizmor-online-audits-fail-in-cloud-devcontainer.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: cloud-session-host; today
  `architecture/cloud-session-host-toolchain.md`)
- unique items:
  - [constraint] The cloud session's placeholder `GH_TOKEN` is valid only for
    repositories in the session's GitHub scope: through the proxy a
    `git-upload-pack` with the token returns 401 for another repository
    (`actions/github-script`) while the same request with no token returns 200 —
    which is why zizmor's online audits, which send `GH_TOKEN` to the
    repositories of the actions a workflow uses, fail there. — already partly
    in: `architecture/cloud-session-host-toolchain.md` (holds
    `ZIZMOR_OFFLINE=true` and "the session's placeholder `GH_TOKEN` fails",
    pointing at this bug for the mechanism) — written:
    `spec/cloud-session-host.md#the-agent-proxy-owns-the-sessions-github-access`
- conflicts: none

## docs/knowledge/data/backlog/autonomous-implement-loop.md

- verdict: ALL ALREADY HELD
- owning spec: iwe-workflow-skills (loop, bound, evaluator scope, planner
  rulebook in `architecture/autonomous-implement-loop.md`; the
  `/agentdev:iwe-implement-all` coordinator half is dead)
- conflicts: none

## docs/knowledge/data/backlog/capture-current-architecture.md

- verdict: NOTHING DURABLE
- owning spec: NONE
- conflicts: none

## docs/knowledge/data/backlog/capture-skill.md

- verdict: ALL ALREADY HELD
- owning spec: iwe-workflow-skills (Capture requirements;
  `/agentdev:iwe-capture` owns the three inbox lanes and the someday promotion)
- conflicts: none

## docs/knowledge/data/backlog/drop-claude-free-form-task-trigger.md

- verdict: ALL ALREADY HELD
- owning spec: ai-review-gate (`architecture/pull-request-only-responder.md`
  records the removal and why keeping the task path was rejected)
- conflicts: none

## docs/knowledge/data/backlog/e2e-opencode-usage-limit-reason.md

- verdict: DEAD (subject removed)
- owning spec: NONE (`scripts/e2e/` is gone; `AGENTS.md#tests` forbids
  agent-session e2e tests)
- conflicts: none

## docs/knowledge/data/backlog/e2e-verify-report-cache.md

- verdict: DEAD (subject removed)
- owning spec: iwe-workflow-skills (the saved-report behaviour itself is
  specified there; the e2e suite is gone)
- conflicts: none

## docs/knowledge/data/backlog/git-core-ppa-without-launchpad-api.md

- verdict: ALL ALREADY HELD
- owning spec: agentdev-runtime-images (`architecture/no-launchpad-ppas.md`: no
  Launchpad host at build time, the PPA key pinned by fingerprint, packages
  republished as `pinned-deps/git/<version>` releases — a stricter form than
  this task proposed)
- conflicts: this document's done-condition "`git` still installs from the PPA"
  versus `architecture/no-launchpad-ppas.md`: "no Ansible role adds a PPA, and
  the devcontainer firewall allows neither `launchpad.net` nor
  `ppa.launchpadcontent.net`." — resolved:
  `spec/agentdev-runtime-images.md#requirement-image-builds-contact-no-launchpad-host`
  matches the code; the task's done-condition is stale

## docs/knowledge/data/backlog/implement-all-multi-plan-e2e.md

- verdict: DEAD (subject removed)
- owning spec: NONE (`/agentdev:iwe-implement-all` and the e2e suite are
  removed)
- conflicts: none

## docs/knowledge/data/backlog/map-doc-stamper.md

- verdict: DEAD (subject removed)
- owning spec: NONE (`iwe-map` and map docs retired)
- conflicts: none

## docs/knowledge/data/backlog/nested-catalog-agent-dispatch.md

- verdict: ALL ALREADY HELD
- owning spec: nested-agent-dispatch (per-harness cost in
  `architecture/nested-subagent-dispatch.md`; agents-as-leaves in
  `architecture/autonomous-implement-loop.md` and
  `architecture/fresh-context-verify.md`)
- conflicts: this document treats nested depth as a cost to avoid ("OpenCode's
  `experimental.subagent_depth`, an experimental key OpenCode may rename or
  drop"); `spec/devcontainer-opencode-policy.md` now sets
  "`experimental.subagent_depth` to `5`" and `spec/nested-agent-dispatch.md`
  says the limit exists "so a dispatched agent can dispatch another". —
  resolved: the specs match
  `py_packages/agentdev_runtime/agentdev_runtime/opencode_config.py::apply_policy`
  (`SUBAGENT_DEPTH = 5`); the task's stance is stale

## docs/knowledge/data/backlog/planner-spec-redundancy-check.md

- verdict: ALL ALREADY HELD
- owning spec: iwe-workflow-skills (scenarios "Plan names that requirement
  instead of restating the rule" and "A modification makes a scenario
  redundant")
- conflicts: none

## docs/knowledge/data/backlog/port-agent-owned-e2e-to-pytest.md

- verdict: DEAD (subject removed)
- owning spec: NONE (agent-session e2e suites are removed and forbidden by
  `AGENTS.md#tests`)
- conflicts: none

## docs/knowledge/data/backlog/pr-feedback-resolve-merge-conflicts.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: pr-merge-conflicts
- unique items:
  - ~~[rationale] A pull request that conflicts with its base gets no
    `pull_request` workflow runs, so the CI picture `pr-feedback-resolution`
    diagnoses is missing or stale until the conflict is resolved — the reason
    conflict resolution is the first step, which also satisfies
    `update-branch`'s clean-working-tree precondition because no feedback edit
    exists yet. — already partly in: `spec/pr-merge-conflicts.md` (behaviour:
    read merge state before any feedback edit, PR's own base, `UNKNOWN` re-poll,
    `BEHIND` not updated; purpose says "pushed at once so CI runs on the
    resolved head", not the GitHub fact)~~ — struck: already held by
    `spec/pr-merge-conflicts.md#conflicts-are-resolved-and-pushed-before-any-feedback-work`
- conflicts: none

## docs/knowledge/data/backlog/pr-merge-stack-post-merge-cleanup.md

- verdict: DEAD (subject removed)
- owning spec: stacked-prs (`gh stack merge` is gone;
  `architecture/manual-stacked-prs.md`)
- conflicts: none

## docs/knowledge/data/backlog/remove-agentdev-session-start-hook.md

- verdict: DEAD (subject removed)
- owning spec: NONE (the hook, and the `/agentdev:microvm-sandbox` and
  `/agentdev:remote-codespace-session` skills it deferred to, no longer exist;
  cloud sessions are covered by `architecture/cloud-session-host-toolchain.md`)
- conflicts: none

## docs/knowledge/data/backlog/remove-content-tests.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: test-policy; the rule itself lives in
  `AGENTS.md#tests`)
- unique items:
  - [rationale] Cross-file consistency tests are deleted with no replacement
    (maintainer decision): the Renovate pin test only checked that Renovate did
    its job, could not catch a new usage written with an old pin, and when two
    pins diverged on `main` it failed every pull request that merged `main`
    instead of preventing the divergence. — already partly in: `AGENTS.md#tests`
    (the rule, without the reason); nothing in spec/ or architecture/ — written:
    `AGENTS.md#tests`
- conflicts: none

## docs/knowledge/data/backlog/resilient-task-evidence.md

- verdict: ALL ALREADY HELD
- owning spec: plan-checkbox-evidence
  (`architecture/evidence-without-commit-ids.md` holds the decision, why, and
  the rejected commit-id and PR-number alternatives)
- conflicts: this document says the spec "makes a ticked task's evidence name
  the commit that holds its change";
  `architecture/evidence-without-commit-ids.md` says "A commit id on its own is
  not evidence." (old state, superseded). — resolved: stale;
  `spec/plan-checkbox-evidence.md#evidence-names-a-check-verify-can-repeat-never-a-commit-id`
  holds the decision

## docs/knowledge/data/backlog/ship-verifies-before-dispatch.md

- verdict: NOTHING DURABLE
- owning spec: iwe-workflow-skills
- conflicts: this document's intent is that the Shipper "never runs Verify in
  place" and "A miss is a Ship blocker"; `spec/iwe-workflow-skills.md` scenario
  "Ship runs Verify in place" says "it follows the `iwe-verifier` rulebook in
  its own context and dispatches no agent", and
  `.agents/plugins/agentdev/skills/iwe-verify/SKILL.md#from-inside-iwe-shipper`
  still exists. The proposal is not what the spec or catalog implement; no
  decision rejecting it is recorded anywhere. — resolved: the quoted scenario is
  gone; `spec/iwe-workflow-skills.md` and
  `.agents/plugins/agentdev/agents/iwe-shipper.agent.md` now route Ship's Verify
  through `/agentdev:iwe-verify`, which dispatches `iwe-verifier`, as the task
  proposed; nothing to migrate

## docs/knowledge/data/backlog/simplify-pr-skills-single-review-workflow.md

- verdict: DEAD (subject removed)
- owning spec: ai-review-refresh (the dispatched-review shape,
  `pr-discover-ai-responder`, and the trigger ledger are gone; "at most once per
  head SHA" is held in `spec/ai-review-refresh.md`)
- conflicts: none

## docs/knowledge/data/backlog/standalone-claude-remote-control.md

- verdict: ALL ALREADY HELD
- owning spec: claude-remote-control (gate owned by PID 1, watcher instead of
  one-shot and the rejected alternatives in
  `architecture/standalone-opencode-runtime.md#remote-control-watcher`)
- conflicts: this document proposes "an optional `remote-control` one-shot";
  `architecture/standalone-opencode-runtime.md#remote-control-watcher` says "The
  component is a long-running watcher, `agentdev-runtime remote-control run`,
  not a one-shot". — resolved: stale proposal;
  `spec/standalone-opencode-runtime.md#remote-control-is-a-long-running-watcher-gated-by-pid-1`
  matches `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py::run`

## docs/knowledge/data/backlog/supervision-orphan-kill-test-cause.md

- verdict: NOTHING DURABLE
- owning spec: standalone-opencode-runtime (its outcome is recorded in
  `bugs/supervision-orphan-kill-test-flaky.md`, scanned above)
- conflicts: none

## docs/knowledge/data/backlog/verify-in-fresh-context.md

- verdict: ALL ALREADY HELD
- owning spec: iwe-workflow-skills (`architecture/fresh-context-verify.md`; the
  Codex `spawn_agent` item is dead with Codex support)
- conflicts: none
