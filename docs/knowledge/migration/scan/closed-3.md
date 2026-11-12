# Batch 3 — durable knowledge held only in closed documents

## docs/knowledge/data/plans/20261016-opencode-web-coder-autostart.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: opencode-web (Coder dashboard-app facts belong to the
  `plume-works/coder-ide-baseline` repository's `spec/workspace-template`, which
  this checkout cannot read)
- unique items:
  - [rationale] The server's port is always passed explicitly (`--port`),
    because OpenCode's port 0 means "4096 if free, otherwise any port"; a taken
    port must fail the start rather than move the server to a port Coder's
    forwarding does not expect — already partly in: nowhere
    (`spec/opencode-web.md#requirement-the-server-is-exposed-only-behind-a-password`
    states only "SHALL listen on port 4096")
  - [rationale] The Coder tmux pane runs the server with `DISPLAY` removed so a
    server start can never open a browser window on the Xpra desktop at every
    workspace start. The code still does this
    (`py_packages/agentdev_runtime/agentdev_runtime/opencode.py::coder_pane`,
    `env -u DISPLAY`), but no spec or note says why — already partly in:
    `architecture/standalone-opencode-runtime.md#opencode-lifetime` (covers only
    the standalone side: `serve` opens no browser, `DISPLAY` kept)
  - [rationale] OpenCode's data directory is never shared between instances
    because it holds a WAL-mode SQLite database and per-project snapshot
    repositories that concurrent containers would corrupt — already partly in:
    `architecture/agent-auth-persistence.md#why-the-rest-of-the-state-is-not-shared`
    (gives the absolute-path reason) and
    `architecture/standalone-opencode-runtime.md#identity-and-state` ("two
    containers writing them would corrupt each other", no SQLite detail)
  - [constraint] Coder (v2.37.1) does not apply `customizations.coder.apps` from
    `devcontainer.json` to a Dev Container the template declares with
    `coder_devcontainer`, so the dashboard app must be a `coder_app` in the
    template; a subdomain `coder_app` joins every request path onto its `url`'s
    path, so the app's `url` must be the server root, and its healthcheck must
    be a path that answers without the server password — already partly in:
    nowhere in this repository (`spec/opencode-web.md` intro only says the
    dashboard app is the template's)
- conflicts:
  - Plan `## Approach`: "`devcontainer.json` mounts a Compose-prefixed
    `agentdev-opencode` volume at `/root/.local/share/opencode`" and
    `spec/opencode-web.md#requirement-opencode-logins-and-chats-survive-a-rebuild`:
    "SHALL live on the per-instance `agentdev-opencode` volume" — versus
    `architecture/agent-auth-persistence.md#decision`: "OpenCode's logins are
    per instance ... in its data directory, on the home volume";
    `.devcontainer/devcontainer.json` and `.devcontainer/docker-compose.yml`
    declare no `agentdev-opencode` volume, and `scripts/tests/test_docker_gc.py`
    treats `proj_devcontainer_agentdev-opencode` as an old volume. The spec
    requirement, not only the plan, is stale.
  - Plan `## Approach`: "`link-opencode-auth.sh` ... moves a regular
    `~/.local/share/opencode/auth.json` into `/root/.agents-auth/opencode/` and
    symlinks it back" — versus
    `architecture/agent-auth-persistence.md#decision`: "There is no file to
    share, so each worktree logs in once" (superseded; script removed).
  - Plan `## Approach`: "The pane runs `opencode web --port 4096` ...
    `--hostname 127.0.0.1` otherwise" with no password — versus
    `spec/opencode-web.md`: "`opencode serve`" and "SHALL always require a
    password" (superseded).
  - Plan `## Approach`: the printed link is
    "`/<base64url(workspace folder)>/session`" — versus
    `spec/opencode-web.md#requirement-the-coder-agent-start-runs-the-opencode-web-ui`:
    "SHALL print the server's root URL" (superseded).

## docs/knowledge/data/plans/20261016-release-impact-at-plan-time.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-workflow-skills
- unique items:
  - [rationale] The release impact lives in the `release` frontmatter field, not
    in a `## Release` body section, because the plan schema can require a
    frontmatter field only while a plan is active but cannot require a body
    section only on active plans; a body section would leave enforcement to the
    skills. The maintainer decided the impact is chosen and reviewed when the
    plan is written — already partly in:
    `spec/iwe-workflow-skills.md#requirement-plans-declare-their-release-impact`
    (behaviour only, no reason or rejected alternative)
  - [behaviour] A milestone aggregator plan declares `release: internal`,
    because its child plans carry the release entries — already partly in:
    nowhere
  - [non-goal] Verify does not cross-check `release: internal` against a
    non-empty `## Spec changes` section — already partly in: nowhere
- conflicts: none

## docs/knowledge/data/plans/20261017-gh-stack-push-guard.md

- verdict: DEAD (subject removed)
- owning spec: stacked-prs
- note: `stack-guard.sh` and the `gh-stack` skill no longer exist;
  `spec/stacked-prs.md` forbids `gh stack` and
  `architecture/manual-stacked-prs.md#rejected-alternatives` records the
  rejection. The plan's gh-stack v0.2.1 defect list (a lease built after its own
  fetch always passes, github/gh-stack#380; `sync` exits `0` after a rejected
  push, #472; `init` of a remote-only branch force-pushes over it, #489) is not
  in that note, but it concerns a tool the repository no longer uses.
- conflicts:
  - Plan `## Context`: "`push` and `submit` fetch every layer and only then
    build each `--force-with-lease` value ... The lease therefore always passes,
    and a stale local layer replaces newer remote commits" — versus
    `architecture/manual-stacked-prs.md#rejected-alternatives`: "a lease
    protects remote-only commits, not the consumers of a rewritten branch". The
    note credits the lease with a protection the plan measured as absent in
    gh-stack v0.2.1.

## docs/knowledge/data/plans/20261017-standalone-opencode-container.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: standalone-opencode-runtime
- unique items:
  - [constraint] Runtime configuration is exposed only through documented
    `AGENTDEV_*` variables, never through command strings a shell evaluates —
    already partly in:
    `spec/standalone-opencode-runtime.md#requirement-runtime-state-is-reported-persisted-and-retried-explicitly`
    (covers only rejecting malformed booleans and non-positive limits)
  - [non-goal] Standing exclusions of the standalone runtime: several projects
    in one running container, automatic repository updates, destructive checkout
    repair, SSH-agent or key provisioning, a bundled reverse proxy or TLS, a
    host Docker socket or remote Docker engine, and staged or transactional
    startup writes (a failed step latches for inspection and explicit retry
    instead) — already partly in: `spec/standalone-opencode-runtime.md`
    ("single-project runtime", "publish no host ports", "without a host socket
    mount") and `architecture/standalone-opencode-runtime.md#failure-latch`; the
    SSH, proxy/TLS, repository-update, and no-staged-writes exclusions are
    nowhere
- conflicts:
  - Plan `## Approach`: "Share only Claude and Codex credentials at
    `/var/lib/agentdev/auth`" — versus
    `spec/standalone-opencode-runtime.md#requirement-a-dedicated-image-owns-a-single-project-runtime`:
    "SHALL NOT install Codex" and
    `#requirement-state-survives-replacement-without-cross-project-session-sharing`:
    "Only Claude provider credentials SHALL be shared".
  - Plan `## Out of scope`: "Claude Remote Control autostart" — versus
    `spec/standalone-opencode-runtime.md`: "SHALL keep Claude Code available
    without autostarting it, except Claude Remote Control when
    `AGENTDEV_CLAUDE_RC_MODE` opts in".
  - Plan `## Approach`: "A background CBM index request for the workspace" and
    "CBM client configuration and its daemon" as optional work — versus
    `architecture/no-code-graph.md#decision`: "The images, the runtime, and the
    catalog ship no code-graph daemon, MCP server, hook, or index".
  - Plan names the image `ghcr.io/plume-works/agent-opencode` derived from
    `agent-desktop` and the retry command `runtime-supervisor.py retry` — versus
    spec: `ghcr.io/plume-works/agentdev-deploy` derived from `agentdev-base`,
    and `architecture/standalone-opencode-runtime.md#failure-latch`:
    "`agentdev-runtime supervisor retry`" (renamed).

## docs/knowledge/data/plans/20261018-opencode-full-access-config.md

- verdict: ALL ALREADY HELD
- owning spec: devcontainer-opencode-policy (rationale in
  `architecture/opencode-full-access-in-devcontainer.md`)
- conflicts:
  - Plan `## Approach`: "The three managed values are restored on every start"
    by "`.devcontainer/scripts/configure-opencode.py`, a PEP 723 Python script",
    run from "`postStartCommand.sh`" — versus
    `spec/devcontainer-opencode-policy.md#requirement-devcontainer-opencode-runs-with-unrestricted-filesystem-access`:
    four managed values (adds "`experimental.subagent_depth` to `5`"), set by
    "`agentdev-runtime state agent-policy`" from
    "`agentdev-runtime lifecycle ready`" (superseded).

## docs/knowledge/data/plans/20261018-opencode-v2-default.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: opencode-web (server and web UI items), opencode-catalog-bridge
  (bridge items), agentdev-runtime-images (install item)
- unique items:
  - [rationale] Without `OPENCODE_SERVER_PASSWORD` the start generates a
    password file instead of refusing to start, because requiring the Coder
    secret would take the web UI away from workspaces that lack it; the
    generated password is never printed in the agent-start log because anyone
    who can read that log would have it — already partly in:
    `spec/opencode-web.md#requirement-the-server-is-exposed-only-behind-a-password`
    (behaviour only)
  - [constraint] OpenCode v2's server always requires a password (its own random
    one when `OPENCODE_SERVER_PASSWORD` is unset) with basic-auth user
    `opencode`, and its web UI has no route or query parameter that opens a
    directory; the printed link is therefore the server's root URL, and a link
    to a session was rejected because the only session route needs a session the
    start would have to create on every run — already partly in:
    `spec/opencode-web.md` (states "always require a password" and "root URL" as
    behaviour, no host fact or rejected alternative)
  - [constraint] Bun blocks the `@opencode/cli` postinstall, which fetches the
    platform binary, until the package is trusted, so the image installs it as a
    trusted package — already partly in: nowhere in the graph
    (`ansible/roles/agentic_tools/README.md` mentions it)
  - [rationale] The full-access policy stays in v1's `permission` form because
    v1 ignores v2's `permissions` key while v2 reads the v1 block, on the
    assumption that v2 never rewrites `opencode.json` into its own form —
    already partly in:
    `architecture/opencode-catalog-bridge.md#opencode-v2-2032` ("Config." bullet
    states that v2 reads the v1 `permission` object; the rejected rewrite and
    the assumption are nowhere)
  - [non-goal] The catalog is not exposed through v2's native skill roots:
    `.agents/plugins/agentdev/skills` is not one of them, and native
    `.agents/skills` discovery is out of scope; skills reach v2 only through the
    bridge's skill editor — already partly in: nowhere
- conflicts:
  - Plan `## Context`: "`auth.json` is read once, as an import" and
    `## Approach` Assumptions: "v2 imports it once and never writes it" — versus
    `architecture/opencode-catalog-bridge.md#opencode-v2-2032`: "An OpenAI OAuth
    login in a v1 `auth.json` is not imported, so each data directory logs in
    again under v2".
    `architecture/standalone-opencode-runtime.md#identity-and-state` still says
    "OpenCode 2.0.32 imports it once and never writes it", so the two
    architecture notes also disagree with each other.
  - Plan `## Context`: "`opencode serve --port --hostname` serves the API and
    the web UI; there is no `web` command" — versus
    `architecture/standalone-opencode-runtime.md#opencode-lifetime`: "`serve`
    and `web` start the same server, but `serve` opens no browser".
  - Plan `## Approach`: "diagnostics go through the host's Effect logger ...
    annotated `service: agentdev`" and
    `spec/opencode-catalog-bridge.md#requirement-one-bridge-loads-in-opencode-v1-and-v2`
    scenario: "the bridge's warnings reach OpenCode's log" — versus
    `.agents/plugins/agentdev/.opencode-plugin/index.ts`, which now emits no
    warning and holds no log adapter (the workspace CBM registration that
    produced the warnings is gone). The spec scenario and the three diagnostics
    bullets under
    `architecture/opencode-catalog-bridge.md#rejected-alternatives` describe
    removed code.
  - Plan `## Approach`: "Logins live in v2's database on the `agentdev-opencode`
    volume" — versus `architecture/agent-auth-persistence.md#decision`: "on the
    home volume" (same stale volume as in `spec/opencode-web.md`).
  - Plan `## Approach` "Workspace CBM registration on v2" and "E2E harness on
    v2" — versus `architecture/no-code-graph.md#decision` and `AGENTS.md`
    ("NEVER WRITE AN END-TO-END TEST THAT DRIVES AN AGENT SESSION"); both
    subjects are removed.

## docs/knowledge/data/plans/20261018-opencode-workspace-cbm-indexing.md

- verdict: DEAD (subject removed)
- owning spec: NONE (removal is recorded in `architecture/no-code-graph.md`; the
  purge of leftovers is in `spec/catalog-lifecycle.md`)
- conflicts:
  - Plan `## Approach`: "launch one best-effort registration attempt from the
    config hook" for `mcp["codebase-memory-mcp"]` — versus
    `architecture/no-code-graph.md#decision`: "The images, the runtime, and the
    catalog ship no code-graph daemon, MCP server, hook, or index".

## docs/knowledge/data/plans/20261019-iwe-workflows-e2e-pytest.md

- verdict: DEAD (subject removed)
- owning spec: iwe-workflow-skills (holds the standing ban)
- note: `scripts/e2e/` does not exist. The ban on such suites is held in
  `AGENTS.md#tests` and `spec/iwe-workflow-skills.md` ("Plan SHALL add no
  end-to-end test that drives an agent session through the workflow skills
  against a live model").
- conflicts:
  - Plan `## Approach`: "one pytest test per scenario and harness" driving
    OpenCode, Claude Code, and Codex against live models — versus
    `AGENTS.md#tests`: "NEVER WRITE AN END-TO-END TEST THAT DRIVES AN AGENT
    SESSION (Claude Code, OpenCode) through the agentdev catalog's workflow
    skills against a live model".

## docs/knowledge/data/plans/20261020-gate-image-publication.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: image-pinning
- unique items:
  - [rationale] Each run builds, tests, and then promotes its own images;
    promoting the image a pull request tested when that pull request merges was
    rejected, because squash merges and Renovate commits make `main`'s tree
    differ from any tested pull request head — already partly in:
    `spec/image-pinning.md#requirement-published-tags-name-only-tested-images`
    (behaviour only)
  - [behaviour] The backwards-move guard reads the
    `org.opencontainers.image.revision` label of the image a moving tag names; a
    label naming a commit outside the checkout's history, such as a pull
    request's earlier merge commit, does not block promotion — already partly
    in:
    `spec/image-pinning.md#requirement-published-tags-name-only-tested-images`
    ("SHALL NOT move a tag to an image built from an ancestor of the commit it
    names"; the label mechanism and the unknown-commit case are only in
    `.github/actions/docker/promote/action.yml`)
  - [rationale] Primary checks runs on `main` queue instead of cancelling so
    `edge` keeps advancing while merges (Renovate automerges) arrive faster than
    one run completes; other refs keep cancelling — already partly in:
    `spec/image-pinning.md#requirement-published-tags-name-only-tested-images`
    ("Primary checks runs on `main` SHALL NOT cancel one another", no reason,
    and silent on other refs)
  - [non-goal] Old immutable `sha-<commit>` tags are not deleted — already
    partly in: nowhere
- conflicts:
  - Plan `## Context` names the images "`ubuntu-ansible`, `agent-desktop`, and
    `agent-opencode`" — versus `spec/image-pinning.md`: "`ubuntu-ansible`,
    `agentdev-base`, `agentdev-deploy`, and `agentdev-devcontainer`" (renamed).

## docs/knowledge/data/plans/20261020-iwe-branch-name.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: iwe-branch-name
- unique items:
  - [rationale] The skill exists because this repository squash-merges and
    deletes the head branch on merge, so after a merge nothing on the remote's
    branch list records which iteration comes next; that is why merged and
    closed pull requests are counted — already partly in:
    `spec/iwe-branch-name.md#requirement-the-next-iteration-follows-every-iteration-already-used`
    (behaviour and the "merged iteration's branch was deleted" scenario, no
    reason)
  - [constraint] The iteration suffix is always present because git cannot hold
    a ref beside another it would nest under (a bare `<phase>/<slug>` blocks
    `<phase>/<slug>/iter-2`); a name that always ends in the iteration is never
    a path prefix of another. A bare name for the first iteration was rejected
    for this reason — already partly in:
    `spec/iwe-branch-name.md#requirement-plan-work-branches-carry-phase-slug-and-iteration`
    ("SHALL always include ... the iteration suffix", no reason)
  - [rationale] `next` fails with `GH_UNAVAILABLE` instead of returning a lower
    bound when pull requests cannot be read, because a merged pull request may
    already hold that number and a reused name mixes pull-request history across
    iterations; deriving `N` from the current branch alone was rejected because
    it has no answer on the default branch and misses iterations made in other
    checkouts — already partly in:
    `spec/iwe-branch-name.md#requirement-the-next-iteration-follows-every-iteration-already-used`
    (behaviour only)
  - [rationale] The suffix word is `iter-<N>`; rejected were `iteration-<N>`
    (length), `t<N>` (reads as plan Task N), `take<N>` (implies the previous
    branch was discarded), `v<N>` (reads as a release version), a bare `<N>`, a
    flat `<slug>-<N>` (ambiguous beside slugs ending in digits), and
    `pr<N>`/`#<N>` (read as a pull request number; `#` starts a shell comment) —
    already partly in: nowhere
  - [rationale] The skill creates no branch because branch creation stays in one
    place, `/agentdev:git-new-branch` — already partly in:
    `spec/iwe-branch-name.md#requirement-the-next-name-follows-the-plans-state`
    ("SHALL NOT create, switch, or delete any branch", no reason)
  - [constraint] External-tool facts the lookup relies on: GitHub's `head:`
    pull-request search matches by prefix, so results are filtered to names
    matching the shape exactly; `gh --repo` accepts a remote's HTTPS, SSH, or
    scp-style URL as is, so the URL is passed unparsed and branches and pull
    requests come from the same repository — already partly in:
    `spec/iwe-branch-name.md` ("counting only names that match the shape
    exactly", "the repository the remote's URL names"; the tool facts are
    nowhere)
- conflicts:
  - Plan `## Approach`: "**Name shape.** `<phase>/<slug>/iter-<N>`, `phase` ∈
    `impl`, `ship`" — versus
    `spec/iwe-branch-name.md#requirement-plan-work-branches-carry-phase-slug-and-iteration`:
    "`iwe/<slug>/iter-<N>-<phase>` ... `phase` is `plan`, `impl`, or `ship`".
  - Plan `## Approach`: "one more than the highest `N` for that phase and slug"
    — versus spec: "one more than the highest `N` of any phase".
  - Plan `## Approach`: "`plan-state` ... fetches the remote's default branch,
    finds `data/plans/*-<slug>.md` in that tree" — versus
    `spec/iwe-branch-name.md#requirement-plan-state-is-read-in-the-checkout`:
    "SHALL read the plan from the working tree, never from another branch".
  - Plan `## Approach` "End to end" (cases in `scripts/e2e/iwe-workflows/`) —
    versus `AGENTS.md#tests`; the suite is removed.

## docs/knowledge/data/plans/20261021-map-masks-version-bumps.md

- verdict: DEAD (subject removed)
- owning spec: NONE
- note: the `/agentdev:iwe-map` skill, `stale-map-docs.py`, `source_digest`, and
  digest masks no longer exist in the catalog;
  `architecture/agent-metadata-files.md#consumers` lists `template-consume` as
  the only consumer of `.agent.metadata.json`.
- conflicts:
  - Plan `## Context`: masking "rules live in `.agent.metadata.json` files per
    Agent metadata files" — versus
    `architecture/agent-metadata-files.md#decision`: "template-consume's
    root-only adoption state is its only current consumer".

## docs/knowledge/data/plans/20261021-opencode-command-echo.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: opencode-catalog-bridge
- unique items:
  - [constraint] The bridge can reconstruct only the command name and the
    supplied argument text; whitespace OpenCode's command parser has already
    stripped cannot be restored, so the echoed invocation always uses exactly
    one separating space — already partly in:
    `spec/opencode-catalog-bridge.md#requirement-every-skill-is-a-namespaced-slash-command`
    ("one space and the supplied argument text"; the host limitation is nowhere)
  - [rationale] The invocation is shown by prefixing the user's own message, not
    by an assistant acknowledgment or a second synthetic message, because the
    invocation belongs in the user message; the skill body is never pasted back
    into chat — already partly in:
    `spec/opencode-catalog-bridge.md#requirement-every-skill-is-a-namespaced-slash-command`
    ("submit one user message", "rather than pasted into the text"; the rejected
    alternatives are nowhere)
- conflicts: none

## docs/knowledge/data/plans/20261021-playwright-browser.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: playwright-browser
- unique items:
  - [rationale] The browser comes from Playwright's own installer at an exact
    pinned version, and a bare Ubuntu Chromium package was rejected, because
    Playwright browser binaries are coupled to the client release and a
    distribution package does not preserve that client/browser version contract
    — already partly in:
    `spec/playwright-browser.md#requirement-the-development-image-provides-a-version-matched-playwright-browser`
    ("pinned Playwright CLI and its matching Chromium", no rejected alternative)
  - [rationale] The capability is its own opt-in Ansible role,
    `playwright_browser`, run after Bun and Node provisioning, separate from
    `agentic_tools`, because the browser binaries and their OS dependencies are
    an independently selectable image capability — already partly in: nowhere
    (the spec lists the role only as a source)
  - [non-goal] The image bundles Chromium only (no Firefox or WebKit), ships no
    Playwright MCP server, agent skill, test framework, or project-level
    configuration, and does not relax the opt-in egress firewall for browsing —
    already partly in:
    `spec/playwright-browser.md#requirement-project-playwright-dependencies-remain-project-owned`
    (covers only other Playwright versions)
- conflicts:
  - Plan `## Approach`: "Enable the role in `agent-desktop`" — versus
    `spec/playwright-browser.md`: "The published `agentdev-base` image SHALL
    provide ... and both runtime images SHALL inherit it" (renamed image
    layout).

## docs/knowledge/data/plans/20261021-remote-control-pin-follows-clear.md

- verdict: HAS UNIQUE KNOWLEDGE
- owning spec: claude-remote-control (rationale already in
  `architecture/claude-remote-control-resume.md`)
- unique items:
  - [behaviour] The pin hook never disturbs the session and never corrupts the
    pin: it writes the conversation ID through a temporary file in the same
    directory followed by a rename, so a reboot during the write cannot leave a
    truncated ID, and input that does not parse or carries no `session_id`
    leaves the pin unchanged, writes a message to stderr, and exits 0. Rewriting
    the already-pinned ID on `startup`, `resume`, and `compact` is harmless —
    already partly in: `spec/claude-remote-control.md` ("the session SHALL store
    the new conversation's ID in place of the old one"; atomic write and
    never-fail are only in
    `py_packages/agentdev_runtime/agentdev_runtime/remote_control.py::pin`)
- conflicts:
  - Plan `## Approach`: "`SessionStart` fires with `source` `startup`, `resume`,
    `clear`, and `compact`" — versus
    `architecture/claude-remote-control-resume.md#claude-code-behavior-the-decision-relies-on`:
    "fires with `source` `startup`, `clear`, and `resume`" (the note omits
    `compact`; not a contradiction of behaviour, but the lists differ).

## docs/knowledge/data/plans/20261023-claude-remote-control-server-mode.md

- verdict: ALL ALREADY HELD
- owning spec: claude-remote-control (rationale in
  `architecture/claude-remote-control-server-mode.md`)
- conflicts:
  - Plan `## Context`: "with `--spawn same-dir` as the only spawn mode" and
    `## Out of scope`: "`--spawn worktree` and any override that selects it" —
    versus `architecture/claude-remote-control-server-mode.md#decision`: "server
    mode spawns each on-demand conversation in its own git worktree by default:
    unset or `AGENTDEV_CLAUDE_RC_SPAWN=worktree` passes `--spawn worktree`".
  - Plan `## Approach` Rejected: "A spawned worktree session does not survive a
    server restart (Claude Code 2.1.309)" — versus
    `architecture/claude-remote-control-server-mode.md#claude-code-behavior-the-decision-relies-on`:
    "A spawned session returns after a restart in either spawn mode" (measured
    on 2.1.310).
  - Plan `## Approach`: "the pane command becomes
    `claude remote-control --spawn same-dir`" — versus
    `spec/claude-remote-control.md`:
    "`claude remote-control --spawn <spawn mode> --permission-mode auto`".
  - Plan `## Out of scope`: "A supervisor that restarts the server after it
    exits" — versus
    `architecture/standalone-opencode-runtime.md#remote-control-watcher`: in the
    standalone runtime "the watcher exits, and the controller's recovery budget
    ... bounds how often Remote Control restarts" (still true for Coder:
    `architecture/claude-remote-control-server-mode.md#consequences` "Nothing
    restarts the server after it exits on an extended outage").
