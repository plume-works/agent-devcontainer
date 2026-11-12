# Batch 2 — durable knowledge held only in closed documents

Searched: `docs/knowledge/data/spec/` (32) and
`docs/knowledge/data/architecture/` (68) by distinctive terms, plus the
repository code for whether each subject still exists. "Partly in" names the
file that holds a fragment; "nowhere" means no hit in either directory (a skill
body or `.agents/AGENTS.md` may still state it, and is named where it does).

## docs/knowledge/data/plans/20260929-pr-review-scenario-bar-spike.md

- verdict: ALL ALREADY HELD
- owning spec: NONE (suggest: `pr-review`) — the spike's result and decision are
  in `architecture/pr-review-correctness-bar.md` (`## Decision`,
  `## What the result establishes`, `## Rejected alternatives`), superseded in
  turn by `architecture/pr-review-scenario-validation.md`.
- conflicts: `architecture/pr-review-correctness-bar.md#decision` says "Keep the
  shipped `pr-review` correctness bar unchanged";
  `architecture/pr-review-scenario-validation.md#decision` says "The maintainer
  ships the reachable-scenario correctness bar in `pr-review`". The second note
  supersedes the first; the plan itself conflicts with neither.

## docs/knowledge/data/plans/20260929-responder-review-grounded-and-collected.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: `ai-review-gate` for the responder job; NONE (suggest:
  `pr-review`) for the pass dispatch. The settings half is fully held in
  `architecture/ci-agent-plugin-availability.md#what-a-container-job-must-supply-itself`.
- unique items:
  - [behaviour] On Claude Code, `pr-review` dispatches every pass and validator
    of a batch as foreground `Agent` calls (`run_in_background: false`) in a
    single message, which runs them in parallel and returns only when all
    finish; where no foreground option exists the passes run sequentially in the
    session; nothing depends on a separate wait tool. — already partly in:
    nowhere (stated only in
    `.agents/plugins/agentdev/skills/pr-review/SKILL.md`)
  - [rationale] A headless `claude -p` run ends with its turn, so background
    passes are abandoned. Rejected: running every pass sequentially (gives up
    parallelism and each pass's clean context); keeping background dispatch and
    waiting through another primitive (binds the skill to a wait tool a Claude
    Code version bump can remove). — already partly in: nowhere
  - [constraint] Foreground `Agent` calls cannot be cancelled individually, so
    the Claude Code path has no per-pass ceiling and no drop-a-hung-pass
    fallback; the `claude-respond` job's `timeout-minutes` is the only ceiling,
    and a review that exceeds it fails the job and `ai-review-present` with it.
    — already partly in:
    `architecture/ci-agent-plugin-availability.md#cost-of-running-the-hooks`
    (the 30-minute job timeout), `spec/ai-review-gate.md` (a failed review job
    fails `ai-review-present`)
  - [rationale] Rejected: dropping the `settings:` input and relying on the
    hook-written user settings — the project's permissions and model pin reach
    the responder session only through that input. — already partly in: nowhere
- conflicts: plan `## Approach` says "The Codex path keeps its ceilings and hard
  fallback unchanged"; `architecture/supported-harnesses.md#decision` says
  "Codex is not supported anywhere".

## docs/knowledge/data/plans/20261001-opencode-catalog-bridge.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: `opencode-catalog-bridge` (design, host facts, tool mapping, and
  every rejected alternative are in `architecture/opencode-catalog-bridge.md`)
- unique items:
  - [non-goal] The `self-improve` plugin is not served to OpenCode: its reviewer
    builds a Claude-only command line
    (`.agents/plugins/self-improve/selfimprove/reviewer.py::build_command`) and
    its hook events, including the typed-command authorization
    `UserPromptExpansion` provides, have no OpenCode mapping. — already partly
    in: nowhere
  - [non-goal] The bridge maps no hooks because the agentdev catalog ships none,
    and it is not published to npm or an OpenCode marketplace; it is registered
    by absolute path only. — already partly in:
    `architecture/opencode-catalog-bridge.md#decision` (absolute path
    registration)
- conflicts: plan `## Context` says "The agentdev catalog serves Claude Code and
  Codex from one tree … This plan adds it as a third host";
  `architecture/opencode-catalog-bridge.md#decision` says "OpenCode is the
  catalog's second host", and `architecture/supported-harnesses.md` drops Codex.
  Plan `## Approach` says bare `<name>` commands "remain the fallback if Task 1
  measures `/pr` ranking as unusable"; the note's `## Rejected alternatives`
  says "The namespaced ranking above is usable, so this is not needed."

## docs/knowledge/data/plans/20261001-skill-relative-agent-code.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: NONE (suggest: `catalog-skill-layout`; nearest note is
  `architecture/catalog-script-language.md`, which names `skills/*/agent-code/`
  but not why)
- unique items:
  - [behaviour] A skill body names its bundled code as `agent-code/<file>`,
    relative to the skill directory; `${CLAUDE_SKILL_DIR}` appears only in
    `allowed-tools` (`Bash(${CLAUDE_SKILL_DIR}/agent-code/*)`), which only
    Claude Code reads and whose permission patterns need an absolute path. —
    already partly in: `spec/opencode-catalog-bridge.md` scenario "the user
    types a namespaced command on v1" (a relative `agent-code/` step resolves);
    the rule itself only in `.agents/AGENTS.md`
  - [constraint] The design relies on every host telling the model that a
    relative path in a `SKILL.md` resolves against the skill's directory: Claude
    Code prints "Base directory for this skill: <dir>", OpenCode appends a
    base-directory footer. `${CLAUDE_SKILL_DIR}` is a text substitution only
    Claude Code performs. — already partly in:
    `architecture/opencode-catalog-bridge.md#on-opencode-v1` (the OpenCode
    footer)
  - [rationale] The directory is `agent-code/`, not the Agent Skills convention
    `scripts/`, because a relative `scripts/<script>` resolved against the
    working directory instead of the skill can run a consuming repository's own
    same-named script rather than fail. Rejected: keeping `${CLAUDE_SKILL_DIR}`
    with per-host substitution; relative paths under the name `scripts/`. —
    already partly in: nowhere
  - [constraint] `self-improve` keeps `${CLAUDE_PLUGIN_ROOT}/agent-code/si`: its
    executable sits at the plugin root, not in a skill, so no skill-relative
    form exists, and the plugin is published only to Claude Code, which
    substitutes the variable for hooks. — already partly in: nowhere
  - [non-goal] `references/` directories keep their name: their pages are read,
    not executed, so the name collision does not apply. — already partly in:
    nowhere
- conflicts: the plan's accepted cost about Codex implicit-invocation counting
  and its Codex source citations describe a harness
  `architecture/supported-harnesses.md` says "is not supported anywhere"; that
  part is dead. Otherwise none.

## docs/knowledge/data/plans/20261002-native-stacked-prs.md

- verdict: DEAD (subject removed)
- owning spec: `stacked-prs` — the one decision that survives ("`pr-merge`
  merges explicitly — never through auto-merge") is `spec/stacked-prs.md`
  "Requirement: pr-merge merges explicitly"; the reversal of everything else is
  `architecture/manual-stacked-prs.md#rejected-alternatives`.
- conflicts: plan `## Context` decides "`--force-with-lease` is allowed only
  through `gh stack push`, `gh stack rebase`, and `gh stack sync`" and "a thin
  `pr-merge-stack` skill replaces `pr-merge-chain`" on native stacks; root
  `AGENTS.md` says "NEVER force-push. NEVER use `gh stack` or GitHub native
  stacked pull requests", and `architecture/manual-stacked-prs.md` rejects
  "GitHub native stacks driven by `gh stack`".

## docs/knowledge/data/plans/20261002-pr-feedback-resolve-merge-conflicts.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: `pr-merge-conflicts` (all behaviour, including `UNKNOWN`
  re-polling and the `BEHIND` non-update, is a requirement or scenario there)
- unique items:
  - [constraint] A pull request that conflicts with its base gets no
    `pull_request` workflow runs, so its CI picture is missing or stale until
    the conflict is resolved and pushed; that is why the conflict step runs
    before any feedback work and why `pr-merge` cannot wait on checks for a
    conflicted PR. — already partly in: `spec/pr-merge-conflicts.md#purpose`
    ("pushed at once so CI runs on the resolved head")
  - [rationale] Resolving first also keeps the working tree clean, which
    `update-branch` requires. Rejected: pushing the merge together with the
    feedback fixes — it saves one CI cycle but leaves CI blind while feedback is
    worked. — already partly in: nowhere
  - [rationale] The conflict step merges the PR's `baseRefName`, not
    `update-branch`'s `main` default, so a pull request based on a predecessor's
    branch merges its real base; `update-branch` names a calling skill as a
    legitimate source of `--remote` and `--base` so the override is not read as
    unrequested. — already partly in: `spec/pr-merge-conflicts.md` "Requirement:
    update-branch accepts a calling skill's remote and base" (behaviour only)
  - [non-goal] Fork pull requests whose base branch lives on a remote other than
    `origin` are not handled; the conflict step uses `update-branch`'s `origin`
    default. — already partly in: nowhere
- conflicts: none

## docs/knowledge/data/plans/20261005-codex-full-access-config.md

- verdict: DEAD (subject removed)
- owning spec: NONE — `.devcontainer/scripts/configure-codex.py`, `tomlkit`, and
  codebase-memory-mcp's marker sections no longer exist in the repository;
  `architecture/supported-harnesses.md` records that the runtime "writes no
  Codex configuration", and `architecture/no-code-graph.md` records
  codebase-memory-mcp's removal.
- conflicts: plan `## Approach` has the runtime write
  `sandbox_mode`/`approval_policy` into Codex's `config.toml` on every start;
  `architecture/supported-harnesses.md#decision` says "the runtime writes no
  Codex configuration, hooks, credential links, or `CODEX_HOME`".

## docs/knowledge/data/plans/20261005-pr-review-scenario-validation.md

- verdict: ALL ALREADY HELD
- owning spec: NONE (suggest: `pr-review`) — the shipped bar, the three
  validator changes, the `light` validator, both rejected alternatives, and the
  known limits are in `architecture/pr-review-scenario-validation.md`.
- conflicts: plan `## Approach` item B says a part false as written "is a drop
  naming that part";
  `architecture/pr-review-scenario-validation.md#known-limits` says "The
  validator judges the fault, not the stated parts … A drop's named part is a
  diagnostic hint, not a guarantee". The note is the settled statement.

## docs/knowledge/data/plans/20261007-agent-owned-ship-implement.md

- verdict: ALL ALREADY HELD
- owning spec: `iwe-workflow-skills` (rationale and host behaviour in
  `architecture/explicit-only-workflow-agents.md`, including all four rejected
  alternatives)
- conflicts:
  - plan `## Approach` says "only `iwe-implement-all` dispatches it" and lists
    `iwe-ship-all` as a dispatcher;
    `architecture/explicit-only-workflow-agents.md#decision` says
    "`iwe-implementer` is never dispatched" and "No coordinator runs workflows
    across plans or sessions". Neither coordinator skill exists in the catalog.
  - plan says "`/agentdev:iwe-implement` … (explicit-only)"; the note says
    "Implement's entry skill is model-invocable. `iwe-implement` carries no
    gate", and `.agents/plugins/agentdev/skills/iwe-implement/SKILL.md` has no
    `disable-model-invocation`.
  - plan says "Explicit-only on all three harnesses … plus `agents/openai.yaml`
    … for Codex"; the note says "The gate is explicit-only on both harnesses"
    and no `openai.yaml` exists.
  - plan says "The end-to-end checks are rerunnable. A committed harness …
    drives each harness headless" under `scripts/e2e/<plan key>/`; root
    `AGENTS.md` says "NEVER WRITE AN END-TO-END TEST THAT DRIVES AN AGENT
    SESSION", and `scripts/e2e/` does not exist.

## docs/knowledge/data/plans/20261007-codex-catalog-agents.md

- verdict: DEAD (subject removed)
- owning spec: NONE — `.agents/plugins/agentdev/bin/install-codex-agents.py` no
  longer exists; the one fact that outlived it (Codex loads catalog agents only
  through generated TOML, so an install-yourself Codex package would ship
  broken) is in `architecture/supported-harnesses.md#rejected-alternatives`.
- conflicts: plan `## Context` says catalog agents "must exist on all three
  harnesses"; `architecture/supported-harnesses.md#decision` says the catalog
  ships "nothing for Codex".

## docs/knowledge/data/plans/20261009-remove-coder-agent-auth-seeding.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: `claude-remote-control` (login gate, pre-approval, and the
  opt-out are requirements and scenarios there); the Git half is
  `devcontainer-git-credentials`
- unique items:
  - [non-goal] No mechanism copies, seeds, refreshes, or distributes agent
    credentials across workspaces: claude.ai rotates the refresh token on
    refresh, so one snapshot copied into several workspaces stays valid only in
    the first that refreshes and the rest reach `Login expired`. The maintainer
    deleted seeding outright; a login happens by `/login` inside a container and
    persists on the shared auth volume. — already partly in:
    `spec/claude-remote-control.md#diagnose-login-expired` (refresh-token
    divergence as a symptom),
    `architecture/agent-auth-persistence.md#consequences` (single-use refresh
    tokens); neither states the no-seeding decision
  - [rationale] The autostart gate checks `authMethod: "claude.ai"` in addition
    to `loggedIn` because a setup-token login cannot run Remote Control, and
    uses `claude auth status --json` rather than the credential file because a
    rejected refresh leaves a non-empty file with emptied tokens. — already
    partly in: `spec/claude-remote-control.md` scenarios "only a setup token is
    available" and "the saved login has expired", and `#diagnose-login-expired`
    (the non-empty-file half); the setup-token reason is nowhere
  - [rationale] Pre-approval has an opt-out, `AGENTDEV_SKIP_CLAUDE_PREAPPROVE`,
    so that `enableAllProjectMcpServers` does not reach the headless CI
    responder. Rejected: no opt-out (enables every project MCP server in the
    responder); gating on `AGENTDEV_SKIP_XPRA` (that variable names the remote
    desktop, not headlessness). — already partly in:
    `spec/claude-remote-control.md` "Requirement: every container pre-approves
    first-run Claude state" (behaviour: "The CI responder SHALL set the
    opt-out")
- conflicts: plan `## Approach` justifies the opt-out by the responder's
  "`.mcp.json` names an `mcp-gateway` server that CI does not run"; no root
  `.mcp.json` exists in the repository now, so that specific instance is stale
  while the opt-out itself remains
  (`.github/actions/run-claude-responder/action.yml`). Plan names shell scripts
  (`claude-remote-control-start.sh`, `preapprove-claude-workspace.sh`); the spec
  names `agentdev-runtime remote-control start` and
  `agentdev-runtime lifecycle created`.

## docs/knowledge/data/plans/20261011-coder-agent-gh-credential-helper.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: `devcontainer-git-credentials` (behaviour: "Requirement: HTTPS
  git uses the gh login"), with `coder-ide-baseline` holding the single
  agent-start entry point and the secrets-reach-only-agent-processes constraint
- unique items:
  - [constraint] With no git credential helper for github.com in a Coder
    workspace, git falls back to Coder's `GIT_ASKPASS=/.coder-agent/coder`,
    which never returns, so `git push` hangs; that is the reason the helper must
    be configured from the agent start, where `GITHUB_TOKEN` exists. — already
    partly in: `spec/devcontainer-git-credentials.md` ("so git never waits at an
    interactive credential prompt"), `spec/coder-ide-baseline.md` "Requirement:
    Coder user secrets reach only agent-started processes"
  - [rationale] Rejected: calling the helper setup from the Remote Control start
    (ties git credentials to Remote Control and to its claude.ai login gate); a
    second template `coder_script` that runs the helper directly (splits
    agent-start logic across two repositories). The template runs one
    configurable path and knows nothing of this repository's steps. — already
    partly in: `spec/coder-ide-baseline.md` "Requirement: the repository ships
    the Coder agent-start command" (the single-entry rule, without the rejected
    alternatives)
  - [non-goal] The helper is installed only when `gh` is authenticated, never
    unconditionally, and this repository does not change Coder's `GIT_ASKPASS`
    or configure Coder external auth for GitHub. Post-start keeps its own helper
    setup (maintainer decision) for containers with a stored `gh` login. —
    already partly in: `spec/devcontainer-git-credentials.md` (the "when `gh` is
    authenticated" condition and the stored-login scenario); the non-goals are
    nowhere
- conflicts: plan `## Approach` names
  "`.devcontainer/scripts/coder-agent-start.sh`, the single entry point";
  `spec/coder-ide-baseline.md` says "The repository SHALL ship
  `agentdev-runtime coder start`, the command the `coder-ide-baseline`
  template's `agent_start_script` parameter defaults to".

## docs/knowledge/data/plans/20261011-coder-claude-remote-control.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: `claude-remote-control` ("Requirement: Remote Control inherits
  the Coder agent's environment"), with `coder-ide-baseline` holding the
  lifecycle-ordering constraint
- unique items:
  - [constraint] tmux gives a new session its server's global environment and
    copies from the client only the `update-environment` variables; so Remote
    Control runs on a dedicated server (`tmux -L claude-remote`) that the start
    command itself always starts, and the Claude process inherits the caller's
    environment even when another tmux server is live on the default socket. —
    already partly in: `spec/claude-remote-control.md` "Requirement: Remote
    Control inherits the Coder agent's environment" and scenario "a default tmux
    server is already running" (behaviour, not the tmux fact)
  - [rationale] No Dev Container lifecycle hook starts Remote Control. Rejected:
    keeping the post-start entry and having one entry yield to the other —
    post-start always runs first in Coder, so the generic entry would need a
    Coder signal it cannot observe before the agent exists, or the Coder entry
    would have to kill a live session it did not start. — already partly in:
    `spec/claude-remote-control.md` ("no devcontainer lifecycle hook runs it";
    behaviour only)
  - [non-goal] The `gh` wrapper gets no `GIT_ASKPASS` fallback: `GITHUB_TOKEN`
    is a Coder user secret, stable for the life of the agent, so the copy a
    session inherits does not go stale. — already partly in: nowhere
- conflicts: plan `## Context` says "The maintainer decided that Remote Control
  autostart is a Coder-only feature" and `## Out of scope` says "Autostart on
  non-Coder hosts … nothing starts it"; `spec/claude-remote-control.md` says
  "the standalone runtime's `remote-control` watcher runs it when
  `AGENTDEV_CLAUDE_RC_MODE` is set".

## docs/knowledge/data/plans/20261012-update-branch-pulls-upstream.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: `update-branch` (every row of the plan's case table is a scenario
  there). The plan also records that "update-branch accepts a calling skill's
  remote and base" was deliberately left in `spec/pr-merge-conflicts.md`; under
  one-fact-one-home it belongs in `update-branch`.
- unique items:
  - [behaviour] The upstream is "gone" only when
    `git ls-remote --exit-code --heads <upstream-remote> <upstream-branch>`
    exits `2`; any other failure of that command is `FETCH_FAILED`. An upstream
    on the local repository (`branch.<name>.remote` is `.`) is synced like any
    other, with no fetch and no existence check. — already partly in:
    `spec/update-branch.md` scenario "The upstream branch is gone" (outcome
    only); the rest only in
    `.agents/plugins/agentdev/skills/update-branch/agent-code/update-branch.py`
  - [rationale] Rejected: `git pull --rebase` onto the upstream (rewrites local
    commits and contradicts the merge-based contract); fast-forward only with a
    new `UPSTREAM_DIVERGED` stop (a local fix plus a remote commit is a
    supported case and would always bounce back to the agent). — already partly
    in: `spec/update-branch.md` ("SHALL NOT rebase, reset, or force-push"; no
    alternatives)
  - [behaviour] Both merges run the merge helper as a child process and report
    through one path; exit codes are unchanged from before the upstream sync, so
    callers (`pr-open`, `pr-feedback-resolution`, `git-new-branch`) keep
    following update-branch's result table. — already partly in: nowhere
- conflicts: plan `## Out of scope` says "Stack branches, which Workflow 0
  already refuses" — that refusal belonged to the `gh stack` design root
  `AGENTS.md` now forbids ("NEVER use `gh stack`"). Plan names
  `update-branch.sh` and `git-merge-resolve.sh`; the spec's sources name
  `agent-code/update-branch.py`.

## docs/knowledge/data/plans/20261013-docker-storage-gc.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: `devcontainer-docker-storage`
- unique items:
  - [rationale] The Dev Container keeps its own nested engine. Rejected:
    docker-outside-of-docker — it breaks bind mounts of Dev Container paths
    outside the repository, which running another image's tools against Dev
    Container files depends on. — already partly in: nowhere
    (`architecture/nested-docker-provisioning.md` explains who supervises the
    engine, not why it is nested)
  - [rationale] Rejected: turning off the containerd image store to keep all
    storage under one directory — both limits would still be needed and Docker's
    default store would be given up. — already partly in: nowhere
  - [constraint] `docker image prune --filter until=72h` compares an image's
    creation time, not its last use, so an unused image built or published more
    than 72 hours ago is removed even if it was pulled today; an image
    referenced by any container, running or stopped, is kept. — already partly
    in: `spec/devcontainer-docker-storage.md` "Requirement: the Dev Container
    engine collects garbage hourly" ("created more than 72 hours ago") and
    scenario "an image is in use"
  - [rationale] Why the limits exist: all Coder workspaces share one host disk,
    and a full disk stops a workspace from unpacking its Dev Container image, so
    its sub-agent never starts and nothing the agent start runs (Remote Control
    included) comes up. The 10 GB and 72-hour values are the maintainer's
    choice. — already partly in: nowhere
- conflicts:
  - plan `## Approach` says "on every agent start, `docker image prune …`" and
    "Its prune runs from `coder-agent-start.sh`, so it runs on Coder only";
    `spec/devcontainer-docker-storage.md` says "Both runtime profiles SHALL
    supervise a non-core `docker-gc` service … one pass when it starts and
    another every `AGENTDEV_DOCKER_GC_INTERVAL` seconds, default 3600".
  - plan `## Out of scope` says "Pruning Docker volumes, containers, or
    networks"; the spec says a pass SHALL "remove each volume that no container
    references, whose name matches `(^|_)dind-var-lib-(docker|containerd)-` or
    `_agentdev-(cache|codex)$`".
  - plan `## Context` calls the engine "the nested `dockerd` from the
    docker-in-docker feature"; `architecture/nested-docker-provisioning.md` says
    "The upstream … `docker-in-docker` feature was the previous provider".

## docs/knowledge/data/plans/20261013-macos-native-bootstrap.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: `macos-native-bootstrap` (every step is a requirement; the zsh
  exception is in
  `architecture/catalog-script-language.md#the-one-non-python-script`; the
  host's scope is in `architecture/template-boundary.md#native-macos-host`)
- unique items:
  - [rationale] Rejected: Homebrew's `python` formula (uv provisions the exact
    version the catalog is tested on and is already required); a `macos/`
    Template-class directory at the repository root (reaches only template
    consumers who copy it, while the catalog reaches every plugin user); pinning
    brew formulae to the image's versions (would mean replacing Homebrew with
    release tarballs for every tool, so Homebrew versions float and only the uv
    Python and release-only tools are pinned). — already partly in: nowhere (the
    bash rejection is covered by `architecture/catalog-script-language.md` "its
    `/bin/bash` is 3.2")
  - [constraint] The Python version the script records is the lower bound of the
    root `pyproject.toml`'s `requires-python`, the oldest version the
    repository's tests run the catalog on; a stock host's `/usr/bin/python3`
    (Xcode Command Line Tools) is older than that floor. — already partly in:
    `spec/macos-native-bootstrap.md` "Requirement: uv provisions the catalog's
    Python" ("the Python version it records", without what fixes the value)
  - [rationale] The script does not install Homebrew because that needs an
    interactive `sudo` it should not drive; the Brewfile is inline so one `curl`
    fetches everything. — already partly in: `spec/macos-native-bootstrap.md`
    ("It SHALL NOT install Homebrew itself"; no reason)
  - [behaviour] A `$SHELL` other than zsh or fish gets no `PATH` block, so the
    final check fails and names that shell rather than reporting a `PATH` the
    user's terminal does not have; shell configuration that later puts another
    `python3` first is the user's to fix and the check surfaces it. — already
    partly in: `spec/macos-native-bootstrap.md` scenario "The user's shell
    resolves another Python"
  - [non-goal] The bootstrap sets up no Docker, Super-Linter, or
    `microvm-sandbox`, no MCP gateway, git SSH signing, or keyring, and no
    Xcode, Expo, or iOS Simulator; it does not install fish. — already partly
    in: `architecture/template-boundary.md#native-macos-host` ("no image,
    lifecycle commands, egress firewall, or shared agent volumes")
- conflicts:
  - plan step 4 installs "`codebase-memory-mcp` — from their GitHub release
    darwin tarballs"; `spec/macos-native-bootstrap.md` pins only `iwe` and
    `iwes`, and `architecture/no-code-graph.md` says "The maintainer removed
    codebase-memory-mcp".
  - plan `## Out of scope` says "Renovate automation for the script's release
    pins"; the spec says the version is one "which Renovate moves in the same
    pull request".

## docs/knowledge/data/plans/20261013-resume-claude-remote-control.md

- verdict: ALL ALREADY HELD
- owning spec: `claude-remote-control` (session-mode paragraph of "Requirement:
  Remote Control autostarts only on a live claude.ai login"); decision,
  relied-on Claude Code behaviour, rejected alternatives, and the
  one-ID-per-volume assumption are in
  `architecture/claude-remote-control-resume.md`
- conflicts: plan `## Approach` names a pane-side
  `claude-remote-control-session.sh`; the spec and the note's sources name
  `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py`. No
  behavioural conflict.

## docs/knowledge/data/plans/20261014-expo-eas-template-profile.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: `template-consumption` ("Requirement: an Expo consumer is
  prepared for EAS cloud builds"); the profile's file footprint is in
  `architecture/template-boundary.md#optional-expo-profile`
- unique items:
  - [constraint] Why every `eas.json` build profile pins `bun`: EAS macOS
    workers do not default to the image's bun, and the image's bun writes
    `bun.lock` `lockfileVersion: 2`, which an older bun cannot read under
    `--frozen-lockfile`. — already partly in: `spec/template-consumption.md`
    (the pin and its update scenario, no reason); the reason only in
    `.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md`
  - [constraint] EAS archives the project with `git clone` of the enclosing
    repository, so the app must be tracked in the consumer repository and never
    under an ignored path. — already partly in: nowhere
  - [constraint] An EAS build needs `api.expo.dev`, `cdp.expo.dev`,
    `storage.googleapis.com`, `expo.dev`, `wf-artifacts.eascdn.net`, and
    `mcp.expo.dev` (the Expo plugin's MCP server); `storage.googleapis.com` and
    `wf-artifacts.eascdn.net` are CDN hosts whose addresses rotate, so the
    allowlist may need a container restart. — already partly in:
    `spec/template-consumption.md` ("the Expo hosts in the firewall allowlist",
    unnamed)
  - [constraint] An empty `EXPO_TOKEN` is treated by `eas` as no token, which is
    what makes the template-wide passthrough of an unset host variable inert;
    EAS Simulator writes a session token to `.env.eas-simulator` in the project
    root, which is why it is git-ignored. — already partly in:
    `spec/template-consumption.md` (passthrough "empty when the host does not
    set it"; `.env.eas-simulator` ignored)
  - [rationale] Rejected: an agentdev EAS skill (duplicates Expo's official
    `expo@claude-plugins-official` plugin, which owns the agent workflow);
    passing the token only from the profile (an Expo-only edit to the
    Template-class `.devcontainer/devcontainer.json` makes every later
    devcontainer update a manual merge); guidance with no recorded profile
    (update mode would not know the consumer is an Expo app); persisting the
    token on the shared agent-auth volume (it belongs to the hosting
    environment, where it can be scoped and revoked). — already partly in:
    `architecture/template-boundary.md#optional-expo-profile` (why
    `optional_bundles` records it and why `EXPO_TOKEN` needs no profile edit)
  - [behaviour] The profile keeps `expo@claude-plugins-official` in
    `.claude/settings.json` `enabledPlugins`, and the merged root `AGENTS.md`
    translates Expo's `npx` commands to `bunx` (`bunx eas-cli@latest`); the Expo
    `AGENTS.md` is merged as a section rather than kept as a second file because
    the root `AGENTS.md` is the one instruction file every agent reads. —
    already partly in: `architecture/template-boundary.md#optional-expo-profile`
    (names `.claude/settings.json` among edited files)
  - [non-goal] The profile covers simulator builds only: Apple signing for
    device and store builds stays a one-time human `eas credentials` step, app
    config such as `expo.ios.bundleIdentifier` is the Expo plugin's, and
    `EXPO_TOKEN` passthrough on GitHub Codespaces is not provided. — already
    partly in: nowhere
- conflicts: plan `## Out of scope` lists "Native macOS hosts";
  `spec/template-consumption.md` now has "Requirement: an Expo consumer can
  build iOS on a Mac host through the bridge". Later work, not a contradiction
  of the EAS cloud path.
