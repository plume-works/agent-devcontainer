# Batch 5 — durable knowledge held only in closed documents

## docs/knowledge/data/plans/20261030-responder-quill-app-identity.md

- verdict: ALL ALREADY HELD
- owning spec: ai-review-gate
- held in: `architecture/responder-app-identity.md` (`## Context`,
  `## Approach`, `## Residual exposure`, `## Rejected alternatives`) repeats
  every decision, the write-access constraint on approvals, the
  `permissions:`-bounds-only-`GITHUB_TOKEN` fact, the Dependabot secrets fact,
  and all four rejected alternatives.
- conflicts: none

## docs/knowledge/data/plans/20261030-verify-report-cache.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [rationale] One saved Verify report per plan, overwritten, rather than one
    per commit: only the latest report is ever looked up, and reading an older
    one would be the separate incremental re-verify feature
    (`backlog/incremental-re-verify.md`). — already partly in:
    `architecture/fresh-context-verify.md` › "The skill keeps one saved report
    per plan" (decision only, no reason)
  - [rationale] The user's approvals are recorded in the saved report but are
    not part of its key, because an approval changes a verdict only by
    unblocking a command and a run blocked on a missing approval ends in
    `Needs decision`, which is never saved. — already partly in:
    `spec/iwe-workflow-skills.md` (the `/agentdev:iwe-verify` saved-report
    requirement states "neither SHALL be part of the key");
    `architecture/fresh-context-verify.md` › "A `Needs decision` report is never
    saved"
  - [constraint] `verify-cache.py` writes `.tmp/verify/.gitignore` containing
    `*`, so saving a report never dirties the worktree Verify refuses to run on,
    including in a consuming repository that does not ignore `.tmp/`. — already
    partly in: nowhere
  - [non-goal] A saved Verify report is not reused across a rebase, a squash
    merge, or a fresh container, and `.tmp/verify/` is not protected against a
    hand-written file beyond the rule that only the skill's script writes it. —
    already partly in: `architecture/fresh-context-verify.md` › "Trust in
    `.tmp/verify/` rests on a rule" (second half only)
- conflicts: none. The plan's reason for rejecting a lookup in the
  `iwe-verifier` rulebook, "An agent body rendered into a Codex TOML cannot
  reach a skill's bundled script plugin-relatively", is about Codex, which
  `architecture/supported-harnesses.md` records as removed; the note keeps only
  "A hit would still cost a dispatch."

## docs/knowledge/data/plans/20261031-coder-template-knowledge-split.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: coder-ide-baseline
- unique items:
  - [rationale] Each requirement lives in the repository whose code satisfies
    it, so `spec/coder-ide-baseline` holds only what this repository owes the
    template and the template's requirements and runbook live in
    `coder-ide-baseline`'s own `spec/workspace-template`, linked by GitHub URLs
    on `main`. Rejected: moving the whole spec (the agent-start command would
    have no contract in the repository that ships it), keeping a copy in each
    repository (two texts drift), and moving every document that touches the
    template (it takes this repository's half of mixed plans). — already partly
    in: `spec/coder-ide-baseline.md` introduction › "This spec records this
    repository's side of the contract" (outcome only)
- conflicts: none

## docs/knowledge/data/plans/20261031-kb-conflict-free-layout.md

- verdict: ALL ALREADY HELD
- owning spec: iwe-workflow-skills
- held in: `architecture/kb-conflict-free-layout.md` (`## Decisions`,
  `## Constraints`, `## Rejected alternatives`) holds the single-owner rule,
  every `rank` default, the hub rules, the release-cut rule, and all rejected
  options.
- conflicts: the plan's `## Approach` says "OKF goes: no `data/index.md`, no
  `okf-index` schema, no `status` field"; `spec/iwe-workflow-skills.md`
  requirement "Workflow improvements preserve the IWE and OKF model" says "The
  graph SHALL remain a conformant OKF v0.2 bundle — `data/index.md` lists the
  hubs … and the `okf`, `okf-index`, and `okf-log` schemas check every
  document". The plan's `## Out of scope` lists "The `generated` and `verified`
  provenance fields"; the same requirement now says no document "SHALL set OKF's
  optional `status` … nor OKF's `generated` or `verified`".

## docs/knowledge/data/plans/20261031-model-invocable-implement.md

- verdict: ALL ALREADY HELD
- owning spec: iwe-workflow-skills
- held in: `architecture/explicit-only-workflow-agents.md` (`## Decision` ›
  "Implement's entry skill is model-invocable", `## Rejected alternatives` › "A
  separate model-invocable Implement entry skill" and "Workers following the
  rulebook file without the skill").
- conflicts: the plan's `## Approach` says a decision "comes from that session's
  own user, or from an approval of the user's that a coordinator session
  relays"; `architecture/explicit-only-workflow-agents.md#decision` says "An
  approval that another session's message claims the user gave is not one:
  nothing authenticates the sender or what the user said." The plan says
  "`iwe-implement-all`, `iwe-ship`, and `iwe-ship-all` stay explicit-only"; the
  same note says "There is no skill that implements or ships every plan in
  turn", and `.agents/plugins/agentdev/skills/` holds neither
  `iwe-implement-all` nor `iwe-ship-all`.

## docs/knowledge/data/plans/20261031-pre-commit-replaces-super-linter.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: pre-commit-gate
- unique items:
  - [rationale] The gitleaks hook's three-mode switch stays an inline `bash -c`
    entry in `.pre-commit-config.yaml` rather than a script, so the hook is
    self-contained for template consumers who copy that one file. — already
    partly in: nowhere
    (`architecture/formatter-ownership.md#secret-scanning-over-commit-ranges`
    describes the modes, not where they live)
  - [constraint] The `pre-commit` CI job has no path filter: pre-commit itself
    skips a hook whose files did not change, except `always_run` hooks such as
    gitleaks and `no-commit-to-branch`, which must run on every event. — already
    partly in: nowhere
- conflicts: none

## docs/knowledge/data/plans/20261031-remove-codebase-map.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills (the absence of a map lane);
  template-consumption (the consumer removal)
- unique items:
  - [rationale] The graph keeps no `data/codebase/` map and the catalog ships no
    `iwe-map` skill: no workflow skill or agent was told to read the map, a
    `source_digest` proves a document was re-stamped and not that its text is
    correct, and every pull request touching mapped code paid a refresh, a CI
    gate, and digest lines that conflict between branches; the module-layout
    architecture document `/agentdev:iwe-setup` drafts covers a new reader's
    cold start. — already partly in: `architecture/no-code-graph.md#decision` ›
    "Agents orient with `grep` over the code plus the `spec/` and
    `architecture/` documents" (about codebase-memory-mcp, not the map)
  - [non-goal] No replacement for the map: no one-page orientation document (it
    duplicates setup's architecture document and the README), no advisory digest
    gate (keeps the refresh cost and the risk of wrong text), and no instruction
    for planners to read derived text no check confirms. — already partly in:
    nowhere
  - [rationale] Template-consume update mode removes a consumer's map without
    asking — its one exception to "migrating consumer documents is the user's
    decision" — because the installed catalog no longer ships
    `stale-map-docs.py`, so a consumer that kept the map would keep a CI step
    that fails. — already partly in: `spec/template-consumption.md` requirement
    "an update removes a retired codebase map" › "This is the one
    consumer-memory change update mode makes without the user's decision"
    (behaviour, no reason)
- conflicts: the plan's `## Approach` says backlog tasks gain a `cancelled`
  stage "mapped to OKF `status: deprecated` as for cancelled plans and bugs";
  `spec/iwe-workflow-skills.md` requirement "Workflow improvements preserve the
  IWE and OKF model" says "No document under `data/` SHALL set OKF's optional
  `status`".

## docs/knowledge/data/plans/20261031-remove-codex.md

- verdict: ALL ALREADY HELD
- owning spec: NONE (suggest: supported-harnesses)
- held in: `architecture/supported-harnesses.md` (`## Decision`,
  `## What is not Codex support`, `## Rejected alternatives`) holds the
  decision, the `validate_agent_files` `codex` ecosystem exception, the
  `chatgpt-codex-connector[bot]` exception, and the rejected
  `.codex-plugin/plugin.json` package.
- conflicts: none

## docs/knowledge/data/plans/20261031-verify-report-in-chat.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [rationale] Every Verify caller shows the report verbatim as message text
    because the report is the deliverable of a fresh context: a summary is a
    paraphrase of that verdict, and a path to `.tmp/verify/` is something the
    user cannot follow in chat. Rejected: a summary plus the saved report's
    path. — already partly in: `spec/iwe-workflow-skills.md` (the requirement
    beginning "Every Verify report SHALL number its findings" states the
    behaviour only)
  - [rationale] A Ship blocker report routes each Verify CRITICAL by its `C<n>`
    ID instead of quoting the finding's first line, because a quote is long and
    breaks when the verifier rewords the line, while an ID is short and stable
    within one report. — already partly in: same requirement (behaviour only)
  - [constraint] Finding IDs are scoped to one Verify report and restart at 1 in
    each run; nothing may refer to a finding across reports or Verify rounds by
    ID. — already partly in: nowhere
- conflicts: the plan's `## Approach` says "`iwe-ship-all` is changed to do the
  same" and "`iwe-implement-all` re-posts each plan's final Verify report
  verbatim"; `architecture/explicit-only-workflow-agents.md#decision` says
  "There is no skill that implements or ships every plan in turn", and neither
  skill exists in `.agents/plugins/agentdev/skills/`.

## docs/knowledge/data/plans/20261101-build-on-unshipped-dependencies.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills (stacked-prs for the pull-request side)
- unique items:
  - [rationale] Implement may build on a `## Depends on` plan that is not
    `stage: done` when that plan has an open pull request, while Ship may not
    ship ahead of it; the rejected alternative, keeping Implement's dependency
    gate, serializes every dependent plan behind its dependency's full
    implement–review–merge–ship cycle. — already partly in:
    `spec/iwe-workflow-skills.md` requirement "Ship waits for every dependency"
    and the Implement branch-base scenarios (behaviour only)
- conflicts: the plan's `## Approach` says every `## Depends on` plan "must be
  `stage: done` at the remote default branch"; `spec/iwe-workflow-skills.md`
  requirement "Ship waits for every dependency" says Ship reads the stage "in
  the checkout, never on another branch", and its scenario "Dependency shipped
  on the same branch" says a dependency "not yet `stage: done` on the default
  branch" is treated as shipped.

## docs/knowledge/data/plans/20261101-docker-storage-periodic-gc.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: devcontainer-docker-storage (the workspace-engine half belongs to
  `coder-ide-baseline`'s `spec/workspace-template`)
- unique items:
  - [rationale] Volume collection is an allow-list of disposable name patterns
    gated by age. Rejected: a keep-list that removes every unused volume except
    named login volumes (it deletes any new stateful volume whose container
    happens to be gone), and a blanket `docker volume prune -a` (it deletes
    logins on an engine with no containers). — already partly in:
    `spec/devcontainer-docker-storage.md` requirement "the Dev Container engine
    collects garbage hourly" › "A pass SHALL NOT remove any other volume"
    (behaviour only)
  - [rationale] Collection runs hourly from a supervised service, with the first
    pass at host start, because workspaces have no autostop so a prune at agent
    start almost never runs, and each pass runs `docker builder prune` itself
    because BuildKit's own garbage collection may run only after a build. —
    already partly in: `spec/devcontainer-docker-storage.md` scenario "the cache
    stays over the limit without a build" (behaviour only)
  - [constraint] BuildKit counts toward the 10 GB cap only cache that kept
    images do not share (`docker buildx du` reports it as Private); shared cache
    is the kept images' layers, so removing it frees no disk, and it counts once
    the 72-hour image rule removes its image. — already partly in:
    `spec/devcontainer-docker-storage.md` requirement "the Dev Container engine
    limits its build cache" › "SHALL leave cache that a kept image shares"
  - [non-goal] Coder autostop is not turned on to make a start-time prune run
    (it changes workspace behaviour to work around a cleanup schedule); the
    72-hour image window is not counted from last use; per-id
    `dind-var-lib-docker-<id>` test volumes are not removed as their runs
    finish, the age-gated pass removes them. — already partly in: nowhere
- conflicts: none

## docs/knowledge/data/plans/20261101-explore-interviews-open-questions.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [rationale] The one-topic, one-decision interview is Explore's default
    behaviour, not a separate interview skill or an opt-in mode: the user asked
    for it as the default, and a second entry point would leave the default
    unchanged. — already partly in: `spec/iwe-workflow-skills.md` Explore
    requirement › "one decision per question, in the user's names and design"
    (behaviour only)
- conflicts: none

## docs/knowledge/data/plans/20261101-manual-stacked-prs.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: stacked-prs
- unique items:
  - [rationale] `git-new-branch --depends-on` and `pr-restack-all` refuse a pull
    request whose head lives in a fork because only branches of the remote are
    cut from or restacked: a fork head names a branch that the remote may also
    hold under the same name. — already partly in: `spec/stacked-prs.md`
    scenarios "Predecessor in a fork" and "Head in a fork" (behaviour only)
- held otherwise in: `architecture/manual-stacked-prs.md` (recording a
  dependency, reconnect, restack from a detached worktree, the `iwe/**` ruleset
  bypass constraint, all five rejected alternatives).
- conflicts: the plan's `## Out of scope` says of the AI task responder "It
  pushes as the GitHub Actions app", and
  `architecture/manual-stacked-prs.md#blocking-merges-into-dependent-branches`
  repeats "as the AI task responder does";
  `architecture/responder-app-identity.md#context` says "The responder runs only
  on pull request events and pushes nothing".

## docs/knowledge/data/plans/20261101-okf-bundle-in-spec.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [constraint] A pre-commit check, not a schema, keeps `status` out of the
    graph: the `okf` schema does not declare `status` and accepts undeclared
    fields, so rejecting it there would mean forbidding one property while still
    accepting every other undeclared one. — already partly in:
    `spec/iwe-workflow-skills.md` requirement "Workflow improvements preserve
    the IWE and OKF model" › "The `banned-frontmatter-keys` pre-commit check
    SHALL reject" (behaviour only)
- held otherwise in: `architecture/kb-conflict-free-layout.md#decisions` › "The
  graph stays an OKF v0.2 bundle and diverges only to cut merge or upkeep cost".
- conflicts: the plan's `## Approach` describes "A pytest module [that] reads
  the frontmatter of every document … and fails … when one carries a `status`
  key"; the spec names the enforcing mechanism as "The `banned-frontmatter-keys`
  pre-commit check", which rejects `status`, `generated`, and `verified`.

## docs/knowledge/data/plans/20261101-per-checkout-uv-environments.md

- verdict: ALL ALREADY HELD
- owning spec: agentdev-runtime-images
- held in: `architecture/uv-environment-location.md` (every section: the `.venv`
  link, the three triggers, removal, `<name>.checkout`, the host-git limitation,
  `default_stages`, all rejected alternatives) and
  `architecture/worktree-hooks.md`.
- conflicts: the plan's `## Approach` puts each environment at
  "`/uv/venvs/<checkout directory name>`" with the cache at "`/uv/cache`" on the
  `/uv` mount; `architecture/uv-environment-location.md` says
  "`agentdev-devcontainer` sets the root to `/home/agent/.local/share/uv/venvs`,
  on the home volume" with uv's cache at "its default, `~/.cache/uv`".

## docs/knowledge/data/plans/20261102-adversarial-review.md

- verdict: ALL ALREADY HELD
- owning spec: iwe-workflow-skills
- held in: `architecture/adversarial-review.md` (`## Decision`,
  `## Rejected alternatives`) holds the separate-agent decision, both targets,
  when it runs, finding routes, and all three rejected alternatives.
- conflicts: none

## docs/knowledge/data/plans/20261102-autonomy-loop.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [rationale] A `## Verification` search for leftover text is scoped to the
    files the plan changes because a repository-wide search reads other plans'
    files and fails on text the plan did not change. — already partly in:
    `spec/iwe-workflow-skills.md` requirement "Plans test behaviour and leave CI
    to the merge gate" › "SHALL scope a verification search for leftover text to
    the files the plan changes" (behaviour only)
  - [rationale] Verify accepts a CI job as evidence without a run on the current
    head because a task citing a CI run cannot close before the pull request
    exists and every fix commit makes the cited run stale. — already partly in:
    `architecture/autonomous-implement-loop.md#rejected-alternatives` › "its
    causes, CI timing and unbounded probing"; `spec/iwe-workflow-skills.md` ›
    "without requiring a run on the current head"
- held otherwise in: `architecture/autonomous-implement-loop.md#decision` › "The
  loop acts only on what the plan promised" and both rejected alternatives.
- conflicts: none

## docs/knowledge/data/plans/20261102-bug-lifecycle-and-sections.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [rationale] A bug keeps its own `## Fix` section because bugs reach `done`
    by two routes and about half are fixed directly by a pull request no plan
    references; the rejected alternative, dropping `## Fix` and sending the
    release-page reader to the fixing plan through `iwe find --references`,
    leaves those bugs with no record of their fix. — already partly in:
    `docs/knowledge/SCHEMA.md` bug section › "by the fixer when a change fixes
    it directly, by Ship from the plan that fixed it" (not in `spec/` or
    `architecture/`)
  - [rationale] Backlog tasks do not get the bug lifecycle: a task's job ends
    when a plan grows from it, so its stages are `pending | done | cancelled`
    and `planned` means only "a plan owns this bug". — already partly in:
    nowhere in `spec/` or `architecture/`
  - [rationale] `## Key references` is not required of a bug and Capture does
    not write it, because its anchors rot with the code while frontmatter
    `sources` already names the paths the bug derives from. — already partly in:
    nowhere
  - [constraint] No bug section states lifecycle — `stage` alone does — and
    `severity` measures impact, not urgency, and is descriptive only, tied to
    nothing including `rank`; an unknown Reproduction or Root cause records what
    is known, the hypotheses eliminated, and the backlog spike that settles it,
    never a bare "unknown". — already partly in: `docs/knowledge/SCHEMA.md` bug
    section (not in `spec/` or `architecture/`; `spec/iwe-workflow-skills.md`
    requirement "Bug and feature documents keep the SCHEMA.md shape" holds only
    the enums)
  - [behaviour] A plan revision that removes a bug from `release` returns that
    bug to `stage: pending`. — already partly in: nowhere
    (`spec/iwe-workflow-skills.md` covers only Ship's cancellation returning a
    bug to `pending`)
- conflicts: the plan's `## Context` says "Nothing enforces that a done bug
  carries a Fix — no schema rule, CI check, or refusal gate", and its
  `## Out of scope` lists "any check that a done bug carries a `## Fix`";
  `spec/pre-commit-gate.md` requirement "Ship records are gated in pre-commit"
  says "The CLI SHALL fail a bug at `stage: done` that has no `## Fix` heading".

## docs/knowledge/data/plans/20261102-model-invocable-ship.md

- verdict: NOTHING DURABLE
- owning spec: iwe-workflow-skills
- note: the plan is cancelled and its decision is not in force. The standing
  position — Ship keeps its gate — is held in
  `architecture/explicit-only-workflow-agents.md` (`## Decision` › "A stray Ship
  run reaches the remote, so Ship keeps its gate"; `## Rejected alternatives` ›
  "Drop the gate and rely on descriptions, for Ship").
- conflicts: the plan's `## Approach` says "Remove `disable-model-invocation`
  from `iwe-ship`"; `.agents/plugins/agentdev/skills/iwe-ship/SKILL.md`
  frontmatter carries `disable-model-invocation: true`, and
  `architecture/explicit-only-workflow-agents.md#decision` says "`iwe-ship`
  carries the `disable-model-invocation: true` frontmatter key". The plan's
  `## Context` says "The skill quotes a relayed approval into the dispatch
  prompt the same way as one the user typed"; the same note says "a relayed
  approval is a claim nothing authenticates".

## docs/knowledge/data/plans/20261102-narrow-image-build-context.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: agentdev-runtime-images (image-pinning for the Ubuntu base)
- unique items:
  - [rationale] The weekly Renovate bump of the `ubuntu:24.04` digest is the
    scheduled clean rebuild; between bumps `main` and pull requests share the
    layer cache, which is why no build warm-starts from `agentdev-base:edge` any
    more. — already partly in: `spec/image-pinning.md` requirement "the Ubuntu
    base is pinned by digest and refreshed weekly" (behaviour; scenario "a pull
    request builds the images" › "never from a published `agentdev-base` image")
  - [constraint] `agentdev-base` starts from `ubuntu-ansible` by digest, so that
    digest must not change per run: CI builds `ubuntu-ansible` without the
    `org.opencontainers.image.created`, `.revision`, and `.version` labels, and
    passes `agentdev-base` the per-architecture manifest digest rather than the
    pushed index, whose provenance attestation changes every run. — already
    partly in: `spec/agentdev-runtime-images.md` requirement "image builds read
    only their declared inputs" › "`ubuntu-ansible` SHALL carry no per-run
    labels" (labels only; the index-versus-manifest fact is nowhere)
  - [constraint] `ansible.cfg` sets `log_path=ansible/ansible.log`, which
    resolves inside the read-only `/provision` bind mount, so each provisioning
    step sets `ANSIBLE_LOG_PATH=` to keep Ansible from writing a log there. —
    already partly in: nowhere
  - [rationale] Provisioning is three `RUN` steps selected by Ansible tag rather
    than one step behind the `.dockerignore` allow-list, because the most
    frequent image change, a catalog edit, would otherwise reprovision every
    role; `entrypoint.sh` stays a narrow `COPY` from `docker/` rather than a
    role file, because a role would make host provisioning carry a container
    entrypoint it never uses. — already partly in:
    `spec/agentdev-runtime-images.md` scenario "a catalog-only change"
    (behaviour only)
  - [behaviour] An untagged `setup-dev.yml` run still runs every role in
    playbook order, and a build opts in or out of the catalog by running or
    omitting the `--tags agent_catalog` step, with no role switch variable. —
    already partly in: nowhere
- held otherwise in: `architecture/gh-wrapper-image-only.md` (the `gh` wrapper
  decision and why), `spec/catalog-lifecycle.md` requirement "the staged catalog
  holds only the plugin catalog", `architecture/template-boundary.md` ›
  "`.dockerignore` is an allow-list".
- conflicts: none
