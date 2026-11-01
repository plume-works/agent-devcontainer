# Project Update Log

The history of this workspace, newest first. The `ship` skill's release cut adds
one dated group per release; nothing else writes here.

## 2026-11-01

- **Release**: [2.0.0](releases/2.0.0.md) cut from every feature and fix
  accumulated since 1.0.0; later releases are built from the plans completed
  after it.
- **Update**: [Native macOS bootstrap](features/macos-native-bootstrap.md)
  implemented; [Bootstrap agentdev natively on macOS with
  Homebrew](plans/20261013-macos-native-bootstrap.md) plan done; specs synced.
- **Update**: [Claude Code and OpenCode are the only supported
  harnesses](features/claude-and-opencode-only-harnesses.md) implemented;
  [Remove Codex support](plans/20261031-remove-codex.md) plan done; specs synced
  and the Devcontainer Codex policy spec retired.
- **Update**: fixed [Bug: OpenCode's config is reordered on the first
  restart](bugs/opencode-config-reordered-on-restart.md).

## 2026-10-31

- **Update**: [Bug: an AI re-review that comments leaves its own change request
  blocking merge](bugs/ai-rereview-comment-keeps-changes-requested.md) fixed;
  [AI review verdicts gate merge and trusted bots are
  auto-approved](plans/20261030-ai-review-verdicts-and-bot-approval.md) plan
  done; specs synced.
- **Update**: [Remove the codebase map](plans/20261031-remove-codebase-map.md)
  plan done; specs synced.
- **Update**: [agentdev-runtime CLI](features/agentdev-runtime-cli.md)
  implemented; [Replace the runtime shell scripts with one agentdev-runtime
  CLI](plans/20261029-off-bash-migration.md) plan done; fixed [Bug: a workspace
  on a pre-pin image has no gitleaks or actionlint and nothing says
  so](bugs/workspace-image-lacks-hook-binaries.md), [Bug: the Remote Control
  watcher restarts a session that never comes up on every
  tick](bugs/remote-control-watcher-start-loop.md), and [Bug: doctor fails a
  healthy Coder Dev Container](bugs/doctor-fails-healthy-coder-devcontainer.md).
- **Create**: [agentdev runtime
  package](architecture/agentdev-runtime-package.md) records the runtime as one
  `agentdev-runtime` CLI package, its `RECORD` integrity check, the firewall run
  from the bootstrap, and the CBM-only start of a container with no supervisor.
- **Update**: the codebase map follows the runtime into agentdev_runtime
  package, which replaces the lifecycle-scripts doc, and refreshes the Docker,
  Dev Container, lifecycle, image-runtime, firewall, Ansible, GitHub, and
  validator docs it touched.
- **Update**: [Bug: git-new-branch worktree mode fails on a standalone
  deployment's root-owned
  /workspaces](bugs/git-new-branch-worktree-unwritable-workspaces.md) fixed;
  [Port the catalog's bundled shell scripts to
  Python](plans/20261029-catalog-scripts-python.md) plan done.
- **Update**: fixed [Bug: body-shape schema tests share one scratch graph across
  concurrent runs](bugs/body-shape-schemas-shared-scratch.md) and refreshed the
  knowledge workspace map doc.
- **Update**: refreshed the agentdev catalog, skills, .github, workflows, and
  pull request checks flow map docs for the AI review verdict rule and the
  trusted-bot approval job.
- **Update**: [Verify report cache](features/verify-report-cache.md)
  implemented; [Verify report cache](plans/20261030-verify-report-cache.md) plan
  done.

## 2026-10-30

- **Update**: refreshed the agentdev catalog, skills, and tests map docs for the
  saved Verify report cache.
- **Update**: revised the six active plans for the agreed sequence. [Share one
  BuildKit builder across Coder
  workspaces](plans/20261013-shared-buildkit-workspace.md) registers the builder
  in `agentdev-runtime`; [Bootstrap agentdev natively on macOS with
  Homebrew](plans/20261013-macos-native-bootstrap.md) is a zsh script that
  provisions Python through Homebrew's uv; [Resume interrupted Claude PR reviews
  on a persistent runner](plans/20260909-resumable-claude-review-sessions.md)
  starts from a one-shot `ai-review-resume` label; [Replace the runtime shell
  scripts with one agentdev-runtime CLI](plans/20261029-off-bash-migration.md)
  also fixes [Bug: a workspace on a pre-pin image has no gitleaks or
  actionlint](bugs/workspace-image-lacks-hook-binaries.md); [Run the Dev
  Container as a non-root account with one home
  volume](plans/20261030-devcontainer-home-volume.md) first settles whether a
  Codex login keeps the `auth.json` link; [Port the catalog's bundled shell
  scripts to Python](plans/20261029-catalog-scripts-python.md) refreshes its
  anchors.
- **Update**: ordered the active [plans](plans.md), open [bugs](bugs.md), and
  planned [backlog](backlog.md) items into one implementation sequence; [Share
  one BuildKit builder across Coder
  workspaces](plans/20261013-shared-buildkit-workspace.md) now depends on the
  agentdev-runtime CLI plan, [Bootstrap agentdev natively on macOS with
  Homebrew](plans/20261013-macos-native-bootstrap.md) on the catalog Python
  port, and [Run the Dev Container as a non-root account with one home
  volume](plans/20261030-devcontainer-home-volume.md) releases [~/.claude.json
  stops being the volume symlink](bugs/claude-json-symlink-replaced.md).
- **Update**: [Escalate a client failure to the dependency that caused
  it](plans/20261030-dbus-keyring-flaky-test.md) done; [Bug: a client is
  recovered on its own budget before its dependency's failure is
  confirmed](bugs/supervisor-client-recovered-before-dependency.md) fixed and
  listed under Unreleased Fixed.
- **Update**: refreshed the devcontainer, devcontainer scripts, and devcontainer
  lifecycle map docs for the runtime controller escalating a client failure to
  its failing dependency.
- **Update**: [iwe-branch-name v2: one iteration counter per
  plan](plans/20261030-iwe-branch-name-v2.md) done; merged the
  `iwe/<slug>/iter-<N>-<phase>` shape and shared counter into
  [iwe-branch-name](spec/iwe-branch-name.md) and the start-on-main scenario of
  [iwe-workflow-skills](spec/iwe-workflow-skills.md);
  [iwe-branch-name](features/iwe-branch-name.md) stays implemented and listed
  under Unreleased Added.
- **Update**: refreshed the agentdev, agentdev skills, iwe-bootstrap, agentdev
  tests, and knowledge workspace map docs for the `iwe/<slug>/iter-<N>-<phase>`
  work branch shape.
- **Update**: [Persist the pre-commit hook
  cache](features/persist-pre-commit-cache.md) now uses its own
  `agentdev-pre-commit` volume at `~/.cache/pre-commit`; no cache volume is
  mounted inside the checkout any more.
- **Update**: [Bug: CBM cache under a checkout another UID
  owns](bugs/cbm-cache-under-foreign-owned-checkout.md) fixed: the Dev Container
  keeps `CBM_CACHE_DIR` on its own `agentdev-cbm` volume, off the checkout; [CBM
  daemon lifecycle](architecture/cbm-daemon-lifecycle.md) records why.
- **New**: [Run the Dev Container as a non-root account with one home
  volume](plans/20261030-devcontainer-home-volume.md) plans the [Dev Container
  home volume](features/devcontainer-home-volume.md) feature, now accepted.
- **New**: [Dev Container home volume](architecture/devcontainer-home-volume.md)
  records the decision to run the Dev Container as a non-root account with one
  home volume, and the open editor-server cleanup risk.
- **Update**: refreshed the github and pull request checks flow map docs for the
  single Renovate group that now carries both agentdev image digests.
- **Update**: [Name Remote Control environments after their
  launcher](plans/20261029-remote-control-environment-names.md) done; merged the
  launcher hostname requirement into [Claude Remote
  Control](spec/claude-remote-control.md); [Remote Control environment
  names](features/remote-control-environment-names.md) implemented and listed
  under Unreleased Added.
- **Update**: refreshed the devcontainer, devcontainer scripts, and devcontainer
  lifecycle map docs for the launcher-derived container hostname.
- **Update**: the launcher hostname is now derived inside
  `devcontainer-init.sh`, since a migrated consumer keeps no
  `.devcontainer/scripts/`; [Claude Remote
  Control](spec/claude-remote-control.md) and the devcontainer map docs say so.
- **Update**: [Publish the reusable agentdev Dev Container
  image](plans/20261023-reusable-agentdev-devcontainer.md) done; created the
  [agentdev runtime images](spec/agentdev-runtime-images.md) spec and merged the
  image family into [Image pinning](spec/image-pinning.md), [Catalog
  lifecycle](spec/catalog-lifecycle.md), [Devcontainer Docker
  storage](spec/devcontainer-docker-storage.md), [Standalone OpenCode
  runtime](spec/standalone-opencode-runtime.md), [Playwright
  browser](spec/playwright-browser.md), [Template
  consumption](spec/template-consumption.md), and [Claude Remote
  Control](spec/claude-remote-control.md); [Reusable agentdev Dev
  Container](features/reusable-agentdev-devcontainer.md) implemented and listed
  under Unreleased Added.

## 2026-10-29

- **Update**: refreshed the agentdev, agentdev tests, knowledge workspace,
  validate_agent_files, and its tests map docs after test scratch moved under
  `/tmp/agentdev-tests`.
- **Update**: re-stamped the agentdev, skills, iwe-bootstrap, and knowledge
  workspace map docs after the `generated.by` actor wording became a pattern.
- **Update**: re-verified 10 codebase map docs after the agentdev images were
  pinned to their promoted `edge` digests and the remaining repository
  references named the canonical images.
- **Update**: refreshed 14 codebase map docs for the agentdev image family — the
  base and its deploy and Dev Container siblings, the image-owned lifecycle
  commands and hooks, the four-image CI pipeline and its acceptance jobs, the
  `agentdev-devcontainer` and `agentdev-deploy` pins, and the template-consume
  image-family migration.
- **Update**: refreshed the devcontainer and devcontainer lifecycle map docs for
  the per-instance `/workspaces/project` volume.
- **Update**: [Move the Expo bridge knowledge into its own
  repository](plans/20261028-move-expo-bridge-kb.md) done; no `data/spec/`
  change.

## 2026-10-28

- **Update**: [Start Claude Remote Control in the standalone
  runtime](plans/20261027-standalone-remote-control-autostart.md) done; merged
  the standalone watcher requirement into [Claude Remote
  Control](spec/claude-remote-control.md) and Remote Control as an optional
  service into [Standalone OpenCode
  runtime](spec/standalone-opencode-runtime.md); [Remote Control autostart in
  the standalone runtime](features/standalone-remote-control-autostart.md)
  implemented and listed under Unreleased Added.
- **Update**: [Ship a standalone OpenCode
  container](plans/20261017-standalone-opencode-container.md) done; created the
  [Standalone OpenCode runtime](spec/standalone-opencode-runtime.md) and [CBM
  startup integration](spec/cbm-startup-integration.md) specs and merged the
  standalone requirements into [Catalog lifecycle](spec/catalog-lifecycle.md)
  and [Image pinning](spec/image-pinning.md); [Standalone OpenCode
  container](features/standalone-opencode-container.md) implemented and listed
  under Unreleased Added.
- **Update**: bug [Command-result evidence is judged
  inconsistently](bugs/command-result-evidence-ambiguous.md) records the Codex
  e2e run under the fixed rules: both plans' evidence cites the code commit and
  passes its first Verify.
- **Update**: [Plan checkbox evidence](spec/plan-checkbox-evidence.md) now
  counts a check only together with the commit that holds its change, and puts
  the tick in a commit after the code rather than in the same one; bug
  [Command-result evidence is judged
  inconsistently](bugs/command-result-evidence-ambiguous.md) done.
- **Map**: re-stamped the agentdev catalog, its skills, iwe-bootstrap, and the
  knowledge workspace for the evidence rule change.
- **Create**: [Make plan task evidence survive history
  rewrites](backlog/resilient-task-evidence.md).
- **Create**: bug [Command-result evidence is judged
  inconsistently](bugs/command-result-evidence-ambiguous.md), found by the
  two-plan `implement-all` e2e run on Codex.
- **Update**: [Expo Bridge panel, status bar, and Problems in the workspace
  extension](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/plans/20261026-expo-bridge-panel.md)
  done; no `data/spec/` change.
- **Update**: [Bug: the Expo bridge's project ID check ignores dynamic app
  config](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/bugs/expo-bridge-project-id-ignores-dynamic-config.md)
  fixed and listed under Unreleased Fixed.
- **Update**: [Bug: the container sees the Expo bridge's build log only after
  the build
  ends](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/bugs/expo-bridge-build-log-invisible-until-close.md)
  fixed and listed under Unreleased Fixed.
- **Update**: [Bug: the Expo bridge's build log tail drops
  lines](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/bugs/expo-bridge-build-log-tail-drops-lines.md)
  fixed and listed under Unreleased Fixed.
- **Bug**: filed [Bug: the Expo bridge's project ID diagnostic stays stale after
  a config
  edit](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/bugs/expo-bridge-project-id-diagnostic-stale-after-config-edit.md).
- **Bug**: filed [Bug: the Expo bridge's CocoaPods fix does not repair an
  unlinked
  keg](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/bugs/expo-bridge-cocoapods-fix-misses-unlinked-keg.md).
- **Bug**: filed [Bug: the Expo bridge's simulator profile quick fix omits the
  bun
  pin](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/bugs/expo-bridge-simulator-profile-quick-fix-omits-bun.md).
- **Task**: captured [Revise the Expo bridge build controls after CMake
  Tools](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/backlog/expo-bridge-build-controls.md).
- **Task**: captured [Show one Expo Bridge status bar
  item](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/backlog/expo-bridge-one-status-bar-item.md).
- **Task**: captured [Show each Expo bridge panel section's state on its
  row](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/backlog/expo-bridge-section-status-icons.md).
- **Task**: captured [Verify the build in the Expo bridge sideload
  procedure](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/backlog/expo-bridge-sideload-procedure.md).

## 2026-10-27

- **Create**: [Run implement-all live against two
  plans](backlog/implement-all-multi-plan-e2e.md), done in the same change:
  `test_implement_all` now runs against the loop and pair fixture plans on every
  harness.
- **Create**: someday ideas [Calibrate the revision evaluator against human
  review](someday/revision-evaluator-calibration.md) and [Nested dispatch from
  catalog agents](someday/nested-catalog-agent-dispatch.md).
- **Map**: re-anchored the scripts map for the Remote Control watcher's shorter
  header, and re-stamped devcontainer and the devcontainer lifecycle.
- **Map**: refreshed the scripts, docker, and image and runtime maps for the
  standalone Remote Control watcher and its settings, and re-stamped
  devcontainer, the devcontainer lifecycle, and the image build.
- **Update**: recorded [Holding the AI review gate during a
  re-review](architecture/rereview-gate-pending.md): a separate commit status is
  the leading candidate, and the marker-commit trigger and a merged
  review-and-gate job are rejected.
- **Update**: [PR skills drive the AI review lifecycle on the single review
  workflow](plans/20261023-pr-skills-ai-review-lifecycle.md) done; merged the
  assignee-toggle request and head-check status into the [AI review
  refresh](spec/ai-review-refresh.md) spec; [Bug: PR updates skip the re-review
  evaluation](bugs/pr-update-skips-review-eval.md) fixed and listed under
  Unreleased Fixed.
- **Update**: [Assignee-triggered AI re-reviews replace the comment
  trigger](plans/20261026-assignee-review-trigger.md) done; merged the assignee
  re-review trigger and the `@claude review` rejection into the [AI review
  gate](spec/ai-review-gate.md) spec; [Bug: a comment-requested review's gate
  does not count toward merge](bugs/dispatched-review-gate-not-counted.md) fixed
  and listed under Unreleased Fixed; [AI responder
  workflows](features/ai-responder-workflows.md) stays implemented and listed
  under Unreleased Changed.
- **Map**: re-stamped the agentdev catalog and its skills after merging `main`
  into the Implement loop branch.
- **Map**: re-verified the agentdev catalog for the Implement loop's plan-edit
  commit before a revision.
- **Map**: refreshed the agentdev skills and catalog for implement-all's
  conversation-free Implementer dispatch.
- **Map**: re-verified the agentdev catalog for the Implement loop's
  restore-from-`HEAD` wording.
- **Update**: [Let Implement verify, fix, and revise on its
  own](plans/20261026-autonomous-implement-loop.md) done; [IWE workflow
  skills](spec/iwe-workflow-skills.md) now requires Implement to verify its own
  work, act on the findings, and revise its plan only after an independent
  evaluation.
- **Update**: [Autonomous Implement loop](features/autonomous-implement-loop.md)
  implemented; listed under Unreleased Added.
- **Update**: [Verification in the main
  loop](features/verification-in-the-main-loop.md) gained the Implement
  orchestrator's Verify dispatch; already listed under Unreleased Changed.
- **Update**: [Run Verify from a fresh
  context](plans/20261026-verify-in-fresh-context.md) done; [IWE workflow
  skills](spec/iwe-workflow-skills.md) now requires every Verify run to start
  from a fresh context through the `iwe-verifier` agent.
- **Update**: [Verification in the main
  loop](features/verification-in-the-main-loop.md) gained fresh-context Verify;
  listed under Unreleased Changed.
- **Map**: refreshed the agentdev plugin tests map for `request-review.sh`'s
  assignee toggle, and re-stamped the agentdev catalog and its skills.
- **Map**: refreshed the workflows map for the assignee re-review trigger and
  the `@claude review` rejection, re-anchored pull request checks, and
  re-stamped GitHub, actions, and the agentdev catalog, its skills and plugin
  tests after merging `main`.

## 2026-10-26

- **Map**: refreshed the agentdev catalog and its skills for the `iwe-planner`
  and `iwe-revision-evaluator` agents, the thin `iwe-plan` skill, and the
  Implement loop.
- **Create**: [Autonomous Implement
  loop](architecture/autonomous-implement-loop.md) architecture doc.
- **Map**: refreshed the agentdev catalog and its skills for the `iwe-verifier`
  agent and the dispatching `iwe-verify` skill.
- **Update**: [Configurable Remote Control spawn mode, worktree by
  default](plans/20261025-claude-remote-control-spawn-mode.md) done; merged the
  spawn mode into the [Claude Remote Control](spec/claude-remote-control.md)
  spec; [Remote Control server
  mode](features/claude-remote-control-server-mode.md) stays implemented and
  listed under Unreleased Added.
- **Update**: refreshed the devcontainer scripts map for the Remote Control
  spawn mode, and re-stamped devcontainer and devcontainer lifecycle.
- **Update**: recorded [Assignee-triggered AI
  re-reviews](architecture/assignee-review-trigger.md) and filed backlog task
  [Verify that auto-merge waits for an assignee-triggered
  review](backlog/verify-assignee-review-automerge.md).
- **Update**: filed backlog task [Drop the `@claude <custom prompt>` free-form
  task trigger](backlog/drop-claude-free-form-task-trigger.md).

## 2026-10-25

- **Update**: [Expo bridge bun fix upgrades the bun the check
  runs](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/plans/20261025-expo-bridge-bun-fix-resolved-bun.md)
  done; no `data/spec/` change, the behavior lives in
  `plume-works/vscode-expo-bridge`.
- **Update**: [Bug: the Expo bridge's bun fix upgrades a bun the check never
  runs](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/bugs/expo-bridge-bun-fix-misses-path-bun.md)
  fixed; listed under Unreleased Fixed.
- **Update**: [iwe-branch-name skill](plans/20261020-iwe-branch-name.md) done;
  new spec [iwe-branch-name](spec/iwe-branch-name.md), and [IWE workflow
  skills](spec/iwe-workflow-skills.md) now names the Implement work branch
  `impl/<slug>/iter-<N>`.
- **Update**: [iwe-branch-name](features/iwe-branch-name.md) implemented; listed
  under Unreleased Added.
- **Map**: refreshed the agentdev catalog, its skills, and plugin tests for
  `iwe-branch-name`'s task headings, empty plans, and `--repo` lookup.
- **Map**: refreshed the agentdev catalog, its skills and plugin tests, and the
  knowledge workspace for the `iwe-branch-name` skill.
- **Map**: refreshed the iwe-bootstrap skill and the plugin tests for recovery
  of a transaction interrupted at its first `OWNER` write.
- **Update**: [Extract a reusable IWE bootstrap
  skill](plans/20261023-reusable-iwe-bootstrap.md) done; created the [IWE
  bootstrap](spec/iwe-bootstrap.md) spec, and [Template
  consumption](spec/template-consumption.md) now initializes knowledge through
  the catalog-owned bootstrap.
- **Update**: [Reusable IWE bootstrap](features/consumer-iwe-seed.md) gained
  direct bootstrap; listed under Unreleased Changed.
- **Update**: [Bundle a Playwright browser in the development
  image](plans/20261021-playwright-browser.md) done; created the [Playwright
  browser](spec/playwright-browser.md) spec.
- **Update**: [Playwright browser in the development
  image](features/playwright-browser.md) implemented; listed under Unreleased
  Added.
- **Map**: refreshed the agentdev plugin and its skills for the `exec-summary`
  skill.
- **Update**: [Reuse a matching Expo bridge build by
  fingerprint](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/plans/20261023-expo-bridge-fingerprint-reuse.md)
  done; no `data/spec/` change, the protocol contract lives in the bridge's
  `docs/protocol.md`; [VS Code Expo
  bridge](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/features/vscode-expo-bridge.md)
  stays implemented and listed under Unreleased Added.
- **Task**: captured [Start Claude Remote Control in the standalone runtime when
  asked](backlog/standalone-claude-remote-control.md).
- **Bug**: filed [Codex login stops being shared between standalone
  projects](bugs/standalone-codex-auth-unshared.md).
- **Bug**: filed [plan tasks edit spec documents that only Ship may
  change](bugs/plan-tasks-edit-specs.md).
- **Map**: moved the IWE seed component to the iwe-bootstrap skill, now a child
  of Catalog skills, and refreshed the agentdev catalog, its tests, the
  knowledge workspace, GitHub automation and its workflows, the pull request
  checks, and the validator package, its tests, and rules for the catalog-owned
  scaffold.
- **Update**: filed [Bug: a comment-requested review's gate does not count
  toward merge](bugs/dispatched-review-gate-not-counted.md), reproduced on
  throwaway PR #472.
- **Map**: refreshed the agentdev plugin, its skills, and its tests for the
  removed `pr-discover-ai-responder` skill and the new `request-review.sh`
  script.

## 2026-10-24

- **Update**: [Expo bridge fix terminal launches the Mac's own
  shell](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/plans/20261024-expo-bridge-fix-terminal-mac-shell.md)
  done; no `data/spec/` change, the behavior lives in
  `plume-works/vscode-expo-bridge`.
- **Update**: [Bug: the Expo bridge's fix terminal launches the container's
  shell on the
  Mac](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/bugs/expo-bridge-fix-terminal-remote-shell.md)
  fixed; listed under Unreleased Fixed.
- **Update**: [Expo bridge acts on the agent's window and workspace
  folder](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/plans/20261023-expo-bridge-workspace-folders.md)
  done; no `data/spec/` change, the protocol contract lives in the bridge's
  `docs/protocol.md`.
- **Update**: [Bug: the Expo bridge builds only the devcontainer window's root
  folder](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/bugs/expo-bridge-builds-only-window-root.md)
  fixed; listed under Unreleased Fixed.
- **Update**: [Bug: Expo bridge windows sharing a container break each other's
  socket](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/bugs/expo-bridge-shared-socket-across-windows.md)
  fixed; listed under Unreleased Fixed.
- **Update**: [Opt-in Claude Remote Control server
  mode](plans/20261023-claude-remote-control-server-mode.md) done; [Claude
  Remote Control](spec/claude-remote-control.md) now specifies opt-in server
  mode and limits pinned-conversation resume to session mode.
- **Update**: [Remote Control server
  mode](features/claude-remote-control-server-mode.md) implemented; listed under
  Unreleased Added.
- **Map**: refreshed the devcontainer, its scripts, and the devcontainer
  lifecycle for the Remote Control launcher's `AGENTDEV_CLAUDE_RC_MODE` server
  mode.
- **Bug**: filed and fixed [every gh call in the devcontainer leaks a D-Bus
  session and a keyring](bugs/devcontainer-dbus-autolaunch-leak.md).
- **Map**: refreshed GitHub automation, its workflows, and the pull request
  checks flow for the compose files in the image filter, and the image runtime
  and .devcontainer scripts for the strict firewall switch and comment-keeping
  hooks repair.
- **Map**: refreshed the image runtime and the .devcontainer scripts for
  attempt-scoped failure output and client refresh on retry, and re-verified
  .devcontainer, Docker, and the devcontainer lifecycle and image build flows.

## 2026-10-23

- **Map**: refreshed Ansible, dev_tools, .devcontainer, its scripts, Docker, the
  image runtime, GitHub automation, its workflows, and the devcontainer
  lifecycle, image build, and pull request checks flows for the standalone
  runtime's failure latch, optional work, background indexing, and pinned hook
  binaries.
- **Map**: refreshed GitHub automation, its workflows, and the pull request
  checks flow for the removed pinned runtime acceptance workflow.
- **Map**: refreshed Docker, the image runtime, and the image build flow for the
  agent-opencode deployment guide.
- **Update**: [Publish the Expo bridge to Open VSX through trusted
  publishing](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/plans/20261023-openvsx-trusted-publishing.md)
  done; internal, no release entry.
- **Update**: [Build iOS on the Mac host through a VS Code
  bridge](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/plans/20261015-vscode-expo-bridge.md)
  done; [Template consumption](spec/template-consumption.md) now specifies that
  an Expo consumer builds iOS on a Mac host through the bridge.
- **Update**: [VS Code Expo
  bridge](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/features/vscode-expo-bridge.md)
  implemented; listed under Unreleased Added.
- **Map**: refreshed the agentdev plugin and its skills for the Expo profile's
  silenced Metro port and `eas-host` iOS build rule.
- **Update**: [Template consumption](spec/template-consumption.md) now limits
  the bridge to Simulator builds, keeps the profile on the EAS cloud fallback,
  and has update mode reconcile the Expo profile on every run.

## 2026-10-22

- **Map**: refreshed the agentdev plugin and its skills for the Expo Bridge
  local-iOS path and EAS cloud fallback.
- **Map**: refreshed the agentdev plugin, its skills, and its tests for replay
  safeguards and their regressions.
- **Map**: refreshed the agentdev plugin, skills, and tests docs for replay
  boundary digests reading committed blobs with universal newlines.

## 2026-10-21

- **Update**: [Mask version-only changes during a map
  refresh](plans/20261021-map-masks-version-bumps.md) done; [IWE workflow
  skills](spec/iwe-workflow-skills.md) now specifies replay-proven masks before
  prose refreshes.
- **Update**: [Map masks version-only
  changes](features/map-masks-version-bumps.md) implemented; listed under
  Unreleased Added.
- **Map**: refreshed the agentdev plugin, its skills, and its tests for
  `stale-map-docs.py --replay` and its test module.
- **Map**: refreshed Ansible, image runtime, Docker, the devcontainer lifecycle,
  image build, pull request checks, GitHub, and workflows for the bundled
  Playwright CLI and Chromium browser.
- **Update**: [Show the full OpenCode slash-command
  invocation](plans/20261021-opencode-command-echo.md) done; [OpenCode catalog
  bridge](spec/opencode-catalog-bridge.md) now preserves the full namespaced
  invocation in OpenCode v2 user messages.
- **Update**: [Keep the Remote Control pin on the pane's current
  conversation](plans/20261021-remote-control-pin-follows-clear.md) done;
  [Claude Remote Control](spec/claude-remote-control.md) now stores the pane's
  new conversation ID on `/clear` and gains the clear-then-restart scenario.
- **Update**: [Bug: the Remote Control pin ignores
  `/clear`](bugs/remote-control-pin-ignores-clear.md) fixed; listed under
  Unreleased.
- **Map**: refreshed the devcontainer, its scripts, and the devcontainer
  lifecycle for the `claude-remote-control-pin.sh` `SessionStart` hook.

## 2026-10-20

- **Update**: [Gate image publication on
  acceptance](plans/20261020-gate-image-publication.md) done; [image
  pinning](spec/image-pinning.md) gains the requirement that published tags name
  only tested images.
- **Update**: [Bug: CI/CD publishes images before testing
  them](bugs/ci-publishes-images-before-acceptance.md) fixed; listed under
  Unreleased.
- **Map**: refreshed the image build, pull request checks, GitHub, workflows,
  and composite actions for candidate-only `sha-<commit>` tags, the
  `promote-dev-image` job, and queued `main` runs.
- **Update**: [Make OpenCode v2 the devcontainer
  default](plans/20261018-opencode-v2-default.md) done; specs synced for the
  [catalog bridge](spec/opencode-catalog-bridge.md), [OpenCode
  web](spec/opencode-web.md), [workspace CBM
  indexing](spec/opencode-workspace-cbm-indexing.md), and the [Coder IDE
  baseline](spec/coder-ide-baseline.md); its three features stay implemented and
  listed under Unreleased.
- **Update**: [Port the IWE workflow e2e suite to
  pytest](plans/20261019-iwe-workflows-e2e-pytest.md) done; internal, no release
  entry.
- **Map**: refreshed the devcontainer, its lifecycle scripts, and the lifecycle
  flow for the OpenCode link that prints the server's root URL.

## 2026-10-19

- **Map**: refreshed image runtime, docker, the lifecycle scripts, the
  workflows, and the pull request checks for the required standalone
  `XPRA_PASSWORD` and the pinned-acceptance gate that always runs on a changed
  OpenCode pin.
- **Map**: refreshed image runtime, the devcontainer, its lifecycle scripts, the
  lifecycle flow, and the image build for the standalone runtime on OpenCode v2.
- **Map**: refreshed the OpenCode bridge, its tests, the agentic_tools role, the
  lifecycle scripts, the devcontainer, and the lifecycle flow for OpenCode v2
  (`970a3ae`).

## 2026-10-18

- **Update**: [Configure devcontainer OpenCode for full
  access](plans/20261018-opencode-full-access-config.md) done; [Devcontainer
  OpenCode policy](spec/devcontainer-opencode-policy.md) spec added; [OpenCode
  full-access config](features/opencode-full-access-config.md) implemented.
- **Update**: [Automatically index OpenCode workspaces in
  CBM](plans/20261018-opencode-workspace-cbm-indexing.md) done; [OpenCode
  workspace CBM indexing](spec/opencode-workspace-cbm-indexing.md) spec added;
  [Automatic CBM indexing for OpenCode
  workspaces](features/opencode-workspace-cbm-indexing.md) implemented.
- **Update**: OpenCode bridge, catalog, and plugin tests maps refreshed for
  workspace registration and bounded daemon startup (`8f2c5ef`, `2aa4304`).

## 2026-10-17

- **Map**: refreshed agentdev, its skills, and its tests for the stack guard's
  partial-push rerun, remote-only merges, overwritten-push detection, leased
  push, verbatim patch matching, and queued-layer coverage.
- **Update**: [Autostart the OpenCode web UI on
  Coder](plans/20261016-opencode-web-coder-autostart.md) done; [OpenCode
  web](spec/opencode-web.md) spec added, [Catalog
  lifecycle](spec/catalog-lifecycle.md) shares OpenCode credentials, and [Coder
  IDE baseline template](spec/coder-ide-baseline.md) offers the OpenCode app;
  [OpenCode web UI autostart on Coder](features/opencode-web-coder-autostart.md)
  implemented.
- **Update**: Devcontainer scaffolding, lifecycle scripts, and devcontainer
  lifecycle map docs refreshed for the OpenCode web UI autostart on Coder.
- **Update**: Lifecycle scripts map doc refreshed for the OpenCode workspace
  link; devcontainer scaffolding and devcontainer lifecycle re-digested.
- **Update**: Lifecycle scripts map doc re-anchored for the shorter
  `link-opencode-auth.sh` header; devcontainer scaffolding and devcontainer
  lifecycle re-digested.
- **Update**: [Guard every gh stack push against overwriting a layer's remote
  commits](plans/20261017-gh-stack-push-guard.md) done; [Stacked
  PRs](spec/stacked-prs.md) and [PR merge conflicts](spec/pr-merge-conflicts.md)
  now route every stack push through the gh-stack skill's guard; [Bug: gh stack
  push overwrites a stack layer whose remote is
  ahead](bugs/gh-stack-push-overwrites-remote-layer.md) fixed.
- **Add**: [Stack push guard](architecture/stack-push-guard.md) records why
  every stack push goes through the gh-stack skill's two-phase guard.
- **Map**: refreshed the agentdev plugin, skills, and tests docs for
  `stack-guard.sh` and the repository-owned gh-stack skill.

## 2026-10-16

- **Update**: [Declare release impact when a plan is
  written](plans/20261016-release-impact-at-plan-time.md) done; [IWE workflow
  skills](spec/iwe-workflow-skills.md) now requires every active plan to declare
  its release impact and Ship to apply it; [Ship's release-link rule is
  undefined for a plan with no feature or
  bug](bugs/ship-release-link-without-feature.md) fixed.
- **Update**: Agentdev plugin, agentdev skills, Knowledge base, and IWE seed map
  docs refreshed for the plan `release` declaration.
- **Update**: [Xpra port forwarding](features/xpra-port-forwarding.md)
  backfilled as implemented and listed under Added on the
  [1.0.0](releases/1.0.0.md) release, which shipped it.
- **Update**: Features backfilled as implemented for shipped plans that had
  none, and listed under Added in the [unreleased release](releases/2.0.0.md):
  [Docker storage limits](features/docker-storage-limits.md), [update-branch
  pulls the branch's upstream](features/update-branch-pulls-upstream.md),
  [Remote Control autostart on
  Coder](features/coder-remote-control-autostart.md), [Agent sign-in without
  credential seeding](features/agent-sign-in-without-seeding.md), [Codex
  full-access config](features/codex-full-access-config.md), [PR feedback
  resolution resolves merge
  conflicts](features/pr-feedback-resolves-merge-conflicts.md), and [bun as the
  only JavaScript runner](features/bun-only-javascript-runner.md).
- **Feature**: [Native macOS bootstrap](features/macos-native-bootstrap.md),
  [Shared BuildKit builder](features/shared-buildkit-builder.md), and [VS Code
  Expo
  bridge](https://github.com/plume-works/vscode-expo-bridge/blob/main/docs/knowledge/data/features/vscode-expo-bridge.md)
  filed and accepted for their active plans.
- **Plan**: [Declare release impact when a plan is
  written](plans/20261016-release-impact-at-plan-time.md) filed, to fix [Ship's
  release-link rule is undefined for a plan with no feature or
  bug](bugs/ship-release-link-without-feature.md).
- **Update**: [Expo apps build for iOS through EAS](features/expo-eas-builds.md)
  recorded as implemented and listed in the unreleased release.
- **Update**: [Expo profile for template
  adoption](plans/20261014-expo-eas-template-profile.md) done; [Template
  consumption](spec/template-consumption.md) now requires the template
  devcontainer to pass `EXPO_TOKEN` and an Expo consumer to be prepared for EAS
  cloud builds.
- **Update**: Devcontainer scaffolding maps the `EXPO_TOKEN` passthrough in
  `containerEnv`; the devcontainer lifecycle flow, agentdev catalog, and
  agentdev skills map docs re-verified.

## 2026-10-15

- **Update**: agentdev skills maps the template-consume Optional Expo profile;
  the agentdev catalog map doc re-verified.
- **Update**: [IWE through the CLI, not MCP](architecture/iwe-cli-over-mcp.md)
  recorded; `.mcp.json` drops the IWE MCP server and the image stops installing
  `iwec`.

## 2026-10-14

- **Update**: [Image rebuild lost when a later push to main cancels its
  run](bugs/main-image-rebuild-lost-on-cancel.md) done; the shared
  `paths-filter` action filters a push to `main` from its workflow's last
  passing run.

## 2026-10-13

- **Update**: [Cap Docker storage with automatic garbage
  collection](plans/20261013-docker-storage-gc.md) done; [Coder IDE baseline
  template](spec/coder-ide-baseline.md) now bounds the workspace engine's
  storage, and the new [Devcontainer Docker
  storage](spec/devcontainer-docker-storage.md) spec records the Dev Container
  engine's 10 GB build-cache limit and agent-start image prune.
- **Update**: Devcontainer lifecycle scripts and Flow: devcontainer lifecycle
  map the agent-start image prune; the ansible, devcontainer, and image-build
  map docs re-verified.
- **Update**: [Resume the Remote Control conversation across
  restarts](features/claude-remote-control-resume.md) implemented.
- **Update**: [Resume the autostarted Remote Control conversation by a pinned
  ID](plans/20261013-resume-claude-remote-control.md) done; [Claude Remote
  Control](spec/claude-remote-control.md) now resumes its pinned conversation on
  every start and falls back to a fresh pinned conversation when the resume
  fails.
- **Update**: Devcontainer lifecycle scripts map refreshed for
  `claude-remote-control-session.sh`, the pinned-conversation pane script, in
  commit "map: refresh devcontainer scripts for the Remote Control session
  script".
- **Plan**: [Resume the autostarted Remote Control conversation by a pinned
  ID](plans/20261013-resume-claude-remote-control.md) filed, with its decision
  in [Claude Remote Control
  resume](architecture/claude-remote-control-resume.md).
- **Update**: Codebase map refreshed for the template-consume guide stating the
  iwe version config version 4 needs: two docs re-verified.

## 2026-10-12

- **Update**: [Persist the Coder workspace containerd image
  store](plans/20261011-persist-coder-workspace-containerd.md) done; the
  coder-ide-baseline template persists `/var/lib/containerd` and its overlayfs
  snapshotter directory in per-workspace volumes.
- **Bug**: [Coder workspace Dev Container is lost on
  restart](bugs/coder-devcontainer-lost-on-restart.md) fixed.
- **Update**: [Start Claude Remote Control from the Coder
  agent](plans/20261011-coder-claude-remote-control.md) done; [Claude Remote
  Control](spec/claude-remote-control.md) now starts from the Coder template's
  `coder_script` on a dedicated tmux server and inherits the agent's
  environment, with the postStart autostart and `AGENTDEV_CLAUDE_AUTOSTART`
  removed.
- **Update**: [Configure the gh credential helper from the Coder
  agent](plans/20261011-coder-agent-gh-credential-helper.md) done; [Devcontainer
  Git credentials](spec/devcontainer-git-credentials.md) gains the Coder agent
  start as a second helper trigger.
- **Bug**: [HTTPS git push hangs on Coder's askpass when gh's login is only a
  session token](bugs/coder-askpass-push-hang.md) fixed.
- **Update**: [Coder IDE baseline template](spec/coder-ide-baseline.md) spec
  created: the template's agent-start hook, per-workspace state volumes, and how
  to validate and ship a template version.
- **Update**: [Update branch pulls its upstream before merging the
  base](plans/20261012-update-branch-pulls-upstream.md) done. update-branch now
  fast-forwards or merges the branch's own upstream before the base; see
  [update-branch](spec/update-branch.md).
- **Update**: [update-branch](spec/update-branch.md) spec created with the
  upstream-sync and conflict-rerun requirements.
- **Update**: Codebase map refreshed for `update-branch.sh` bringing in the
  branch's upstream before the base: three docs re-verified.
- **Idea**: [Resume the Remote Control conversation across
  restarts](features/claude-remote-control-resume.md) filed with measured resume
  behavior; the downtime limit and lost-session detection stay open.

## 2026-10-11

- **Update**: Codebase map refreshed for `coder-agent-start.sh`, the Coder
  agent's entry point: three docs re-verified.
- **Update**: Codebase map refreshed for the Remote Control session taking its
  name from `CODER_WORKSPACE_NAME`: three docs re-verified.
- **Update**: Codebase map re-verified for the `CBM_CACHE_DIR` guard fix in the
  codebase-memory-mcp scripts: three devcontainer docs.
- **Update**: Codebase map refreshed for Claude Remote Control moving from
  postStart to the Coder template's `coder_script` on a dedicated tmux server:
  three docs re-verified.

## 2026-10-10

- **Bug**: [gh-stack extension install needs a token the image build
  lacks](bugs/gh-stack-install-needs-token.md) fixed; the `github_cli` role now
  installs the checksummed release binary, and Codebase map refreshed: four docs
  re-verified.
- **Update**: [Agent-owned Ship and Implement
  workflows](plans/20261007-agent-owned-ship-implement.md) done. Ship and
  Implement now run as the `iwe-shipper` and `iwe-implementer` catalog agents,
  started only by their explicit-only entry skills, coordinators, or Plan revise
  answering a Ship blocker; see [IWE workflow
  skills](spec/iwe-workflow-skills.md).
- **Update**: [IWE workflow skills](spec/iwe-workflow-skills.md) spec gains the
  explicit-only Ship and Implement dispatch requirement.
- **Update**: Codebase map refreshed for the `iwe-shipper` and `iwe-implementer`
  agents and the Codex explicit-only gates: three agentdev docs re-verified.
- **Update**: Codebase map re-verified for the Ship blocker routing: two
  agentdev docs.

## 2026-10-09

- **Update**: Codebase map refreshed for the Codex hooks-block repair ahead of
  the CBM install and the non-fatal CBM install in postCreate: three docs
  re-verified. Bug: [Codex tables inside cbm hooks block break cbm
  install](bugs/cbm-codex-hooks-block-foreign-tables.md).
- **Update**: [Remove Coder agent auth seeding; keep Claude Remote Control
  autostart](plans/20261009-remove-coder-agent-auth-seeding.md) done. Coder
  credential seeding is gone; Remote Control autostarts only on a live claude.ai
  login, and every container pre-approves first-run Claude state unless it opts
  out. The devcontainer agent authentication spec is retired, split into [Claude
  Remote Control](spec/claude-remote-control.md) and [Devcontainer Git
  credentials](spec/devcontainer-git-credentials.md).
- **Update**: Codebase map refreshed for the removal of Coder agent auth seeding
  and the Claude login gate: six docs re-verified.
- **Update**: Refreshed nine codebase map documents for the merge of `main` into
  the Codex catalog agent install and its `python3 -B` installer runs.
- **Update**: Codebase map refreshed for the pinned iwe 0.26.1 in CI and
  Renovate post-upgrade: eight docs re-verified.
- **Update**: [Run Node tooling through bun instead of
  npm](plans/20260925-bun-for-node-tooling.md) done. Prettier and the Renovate
  config validator run as local `bunx` hooks, the Renovate version lives in the
  validator's `bunx` pin under a regex manager, and `AGENTS.md` names
  `bun`/`bunx` as the only JavaScript runners.
- **Update**: [Configure devcontainer Codex for full
  access](plans/20261005-codex-full-access-config.md) done. Devcontainer Codex
  runs with full access and no approval prompts, per the new Devcontainer Codex
  policy spec.

## 2026-10-08

- **Update**: [Keep agentdev enabled in the responder and collect review passes
  in the foreground](plans/20260929-responder-review-grounded-and-collected.md)
  done. The responder layers the hook-written user settings under the project
  settings, and `pr-review` collects its passes with foreground `Agent` calls.
- **Update**: [The review orchestrator ends its turn while its passes are still
  running](bugs/review-orchestrator-ends-turn-while-passes-run.md) fixed.
- **Update**: [Fail a review run that published no
  review](backlog/fail-review-run-without-review.md) task filed.
- **Update**: Refreshed the agentdev, agentdev skills, GitHub, workflows, and
  pull-request-checks codebase maps for the `bunx` Prettier and Renovate
  validator hooks and the Renovate pin they now carry.
- **Update**: Codex full access in the devcontainer recorded; refreshed the
  devcontainer, lifecycle-scripts, and lifecycle-flow codebase maps for the
  `configure-codex.py` postStart step.
- **Update**: [Install the catalog agents into
  Codex](plans/20261007-codex-catalog-agents.md) done. Every Codex install now
  writes the catalog agents as generated TOML agents; see [Catalog
  lifecycle](spec/catalog-lifecycle.md).
- **Update**: [Codex never loads the agentdev catalog
  agents](bugs/codex-catalog-agents-not-loaded.md) fixed.
- **Update**: Refreshed ten codebase map documents for the Codex catalog agent
  install: the `bin` installer, its tests, the Codex reinstall script, and the
  `agentic_tools` image-build step.

## 2026-10-07

- **Update**: [Ship the reachable-scenario bar with part-by-part validation in
  pr-review](plans/20261005-pr-review-scenario-validation.md) done. `pr-review`
  ships the reachable-scenario correctness bar with three-part scenarios
  validated as written; see [PR review scenario
  validation](architecture/pr-review-scenario-validation.md).
- **Update**: Re-verified the agentdev and agentdev skills codebase maps after
  the pr-review correctness-bar change.

## 2026-10-05

- **Update**: [Spike: does a reachable-scenario bar let pr-review find
  Greptile-class bugs](plans/20260929-pr-review-scenario-bar-spike.md) done. The
  Codex replay was mixed, so the shipped correctness bar stays unchanged and
  validator strictness is the open question; see [PR review correctness
  bar](architecture/pr-review-correctness-bar.md).
- **Update**: [Native stacked pull requests](features/native-stacked-prs.md)
  implemented.
- **Update**: [Adopt GitHub native stacked pull
  requests](plans/20261002-native-stacked-prs.md) done. The PR skills merge
  every PR explicitly, merge a GitHub native stack through `gh stack merge` with
  the new pr-merge-stack skill, and route stack branches through `gh stack`;
  force-pushes are limited to `gh stack` on stack branches.
- **Update**: [Stacked PRs](spec/stacked-prs.md) spec created.
- **Update**: [PR merge conflicts](spec/pr-merge-conflicts.md) spec resolves a
  conflicted stacked PR with `gh stack rebase`.
- **Update**: [Load the agentdev catalog into OpenCode through a bridge
  plugin](plans/20261001-opencode-catalog-bridge.md) done.
- **Update**: [OpenCode as a catalog host](features/opencode-catalog-host.md)
  implemented.
- **Update**: [OpenCode catalog bridge](spec/opencode-catalog-bridge.md) spec
  created.
- **Update**: [Stacked pull requests](architecture/stacked-prs.md) architecture
  doc created from the stacked-PR spike.
- **Update**: Refreshed the agentdev, agentdev skills, agentdev tests, Ansible,
  and image-build flow codebase maps for the vendored gh-stack skill, the new
  pr-merge-stack skill and the chain-merge skill it replaced, and the pinned
  gh-stack extension.
- **Update**: Re-verified the agentdev, agentdev tests, Ansible, and image-build
  flow codebase maps after merging the stacked-PR work with the OpenCode bridge.

## 2026-10-04

- **Update**: Mapped the OpenCode bridge plugin and refreshed the thirteen
  codebase-map docs that the OpenCode catalog host and the agentdev 4.2.0 pins
  moved.

## 2026-10-02

- **Update**: Refreshed the ansible, validate_agent_files role, and image-build
  flow codebase maps after the validator role began reinstalling on every run.
- **Update**: Re-stamped the agentdev, agentdev skills, and agentdev tests
  codebase maps after merging the push-time map gate with the move to
  `agent-code/`.
- **Update**: [Reference bundled skill code by skill-relative agent-code
  paths](plans/20261001-skill-relative-agent-code.md) done. Bundled skill code
  lives in `agent-code/` and skill bodies reference it relative to the skill
  directory; agentdev 4.1.0 and self-improve 0.1.1 ship it.
- **Update**: [Codex leaves ${CLAUDE_SKILL_DIR} unresolved in agentdev
  skills](bugs/codex-skill-dir-unresolved.md) fixed.
- **Update**: Refreshed the fifteen codebase-map docs that the move of bundled
  skill code to `agent-code/` and the validator 1.0.1 remediation changed, and
  re-stamped five of them for the agentdev 4.1.0 version pins.
- **Update**: [Resolve merge conflicts in
  pr-feedback-resolution](plans/20261002-pr-feedback-resolve-merge-conflicts.md)
  done. pr-feedback-resolution merges a conflicted PR's base through
  update-branch before collecting feedback, pr-merge routes conflicted PRs to
  it, and update-branch accepts a calling skill's `--base`.
- **Update**: [PR merge conflicts](spec/pr-merge-conflicts.md) spec created.
- **Update**: Refreshed the agentdev and agentdev skills codebase maps after the
  pr-merge, pr-feedback-resolution, and update-branch skill edits.
- **Update**: [Refresh the codebase map before pushing and keep its staleness
  out of AI reviews](plans/20260929-map-refresh-before-push.md) done.
  `push-branch.sh` refuses to push a stale codebase map, the pull request skills
  push through it, and the AI review leaves map staleness to CI.
- **Update**: [IWE workflow skills](spec/iwe-workflow-skills.md) gained an agent
  push carrying a fresh codebase map.
- **Update**: [Fresh codebase map on push](features/fresh-map-on-push.md)
  implemented.
- **Update**: Refreshed the two codebase-map docs the push-branch map-check test
  loader annotation moved.

## 2026-10-01

- **Update**: Refreshed the three codebase-map docs the push-branch map check on
  an up-to-date head moved.
- **Update**: [Remove the agentdev SessionStart
  hook](backlog/remove-agentdev-session-start-hook.md) done. The agentdev plugin
  declares no hooks and is released as 4.0.0; the agentdev,
  devcontainer-lifecycle, and three image codebase maps were refreshed.

## 2026-09-30

- **Update**: Refreshed the three codebase-map docs the push-branch map gate and
  its tests moved.

## 2026-09-29

- **Update**: Refreshed the two codebase-map docs the Dev Container feature
  automerge rule in `renovate.json` moved.
- **Update**: [Self-hosted Renovate in the agent-desktop
  image](plans/20260925-self-hosted-renovate.md) done. Renovate runs from
  `renovate.yml` inside the pinned agent-desktop image as a GitHub App, and one
  post-upgrade script refreshes checksums, the devcontainer lock, and pre-commit
  output in the bump's own commit.
- **Update**: [Dependency updates](spec/dependency-updates.md) spec created, and
  [Image pinning](spec/image-pinning.md) gained the shared workflow container
  pin requirement.
- **Update**: [Renovate maintains checksum-carrying
  pins](features/renovate-maintains-checksums.md) implemented.
- **Update**: [git-new-branch skill](plans/20260928-git-new-branch-skill.md)
  done. `/agentdev:git-new-branch` starts work branches at the fetched remote
  base with their own upstream, and git-commit refuses the default branch.
- **Update**: [git-new-branch](spec/git-new-branch.md) spec created, and [IWE
  workflow skills](spec/iwe-workflow-skills.md) gained Implement starting on its
  own branch.
- **Update**: [git-new-branch](features/git-new-branch.md) implemented.
- **Update**: Refreshed the five codebase-map docs the git-new-branch and
  git-commit scripts, the default-branch helper, and their tests moved.
- **Update**: Refreshed the five codebase-map docs the foreground review-pass
  dispatch in `pr-review` and the user-layer settings merge in
  `run-claude-responder` moved.
- **Update**: Refreshed the seven codebase-map docs that Coder agent-auth
  seeding, the gh credential helper, Remote Control autostart, and the
  `scripts/tests` CI suite moved.

## 2026-09-28

- **Update**: Refreshed the eight codebase-map docs the Super-Linter v8.7.0
  tool-version sync, the zizmor 1.25.2 pin, the Renovate role and pre-commit pin
  bumps, and the version-agnostic zizmor mask test moved.

## 2026-09-27

- **Update**: Refreshed the codebase-map doc for the consumer seed after its
  bugs and features hubs deferred the document shape to `SCHEMA.md`.
- **Update**: [Add the iwe-capture skill](plans/20260927-iwe-capture-skill.md)
  done. `/agentdev:iwe-capture` is the single writer of bug, proposed-feature,
  and backlog-task documents, and the bug and feature schemas now enforce the
  `SCHEMA.md` body shape.
- **Update**: [IWE workflow skills](spec/iwe-workflow-skills.md) gained the
  Capture and document-shape requirements.
- **Update**: [Agentdev IWE workflow
  skills](features/agentdev-iwe-workflow-skills.md) changed — it now includes
  Capture.
- **Update**: Refreshed the nine codebase-map docs the iwe-capture skill, the
  shared issue-closing helper, the body-shape schemas, and the agentdev 3.4.0
  pins moved.
- **Update**: Refreshed the nine codebase-map docs the narrowed role checksum
  mask and the Git-isolated mask test fixture moved.
- **Update**: Refreshed the three codebase-map docs over `.github` for the
  Renovate App token's named permissions.

## 2026-09-26

- **Update**: Refreshed the thirteen codebase-map docs whose tracked sources
  moved with the self-hosted Renovate workflow, the pinned-image Renovate config
  validation, and Renovate-managed checksum pins.

## 2026-09-25

- **Update**: The Ansible roles install apt packages unpinned again. The
  per-release, per-architecture pin files, `scripts/apt-pins-refresh.py`, the
  Renovate `deb` managers with their per-role `registryUrls` and daily
  automerged group, and the apt digest mask are removed; the role version pins
  in `defaults/` and their Renovate regex managers stay.
- **Update**: [Ansible apt pins](architecture/ansible-apt-pins.md) now records
  the unpinned decision, with the pin files as the rejected alternative. The
  Renovate rule that holds the `ubuntu` base stays, now because the base stays
  at 24.04 for downstream consumers.
- **Update**: Refreshed the eight codebase-map docs whose tracked sources the
  revert moved.

## 2026-09-23

- **Update**: Bun is installed by `dev_tools` from its pinned, checksum-verified
  release zip instead of by `bun_setup` from the unversioned
  `https://bun.com/install` script. `install_pinned_tool.yml` gained `extension`
  and `binaries_in_asset_dir` to handle that archive shape; `bun_setup` keeps
  the bunx alias and the PATH wiring, and Bun leaves the automerged role-pin
  group for the hand-maintained `dev_tools` pattern.
- **Update**: The five identical `<role>/defaults/main.yml` digest masks
  collapsed into one `*/defaults/main.yml` glob, so a role that gains a pin
  needs no new entry.
- **Update**: Every pinned apt install sets `allow_downgrade: true`, so a role
  converges to its pin from a newer version instead of failing — the state a
  warm image is in after a reverted bump.
- **Update**: `apt-pins-refresh.py` treats only a 404 as an empty component and
  makes every other download failure fatal, rather than caching it as an empty
  index and silently resolving pins from a partial view; cached indices now
  expire after six hours.
- **Creation**: [Renovate config
  validation](architecture/renovate-config-validation.md) records why the config
  is validated twice, once at a pinned Renovate and once at the current one, and
  why both pass `--no-global`.
- **Update**: `.agent.metadata.json` files no longer contribute to a
  codebase-map source digest — [metadata](architecture/agent-metadata-files.md)
  records the rule. A metadata file describes how the digest is computed, not
  the code a map doc claims, and an applied rule already enters the digest as
  its pattern and replacement, so editing a reason or adding a rule that reaches
  nothing leaves every doc fresh.
- **Update**: Dev Container feature version pins in
  `.devcontainer/devcontainer.json` are masked out of the codebase-map source
  digest by a rule colocated in `.devcontainer/`, so a Renovate feature bump no
  longer marks a map doc stale while the feature set itself stays tracked.
- **Update**: Refreshed the eight codebase-map docs whose tracked sources the
  two rules above moved.

## 2026-09-22

- **Update**: Refreshed the four codebase-map docs whose tracked sources the
  release-page `## Changed` work moved.
- **Update**: Release pages carry a `## Changed` section. A feature already
  released in an earlier version, but which gained behavior in this one, belongs
  there rather than under `## Added` — `AI responder workflows` is the first,
  for the effort tiers. `SCHEMA.md` had reserved the name and nothing used it;
  the accumulator template and the ship skill now do.
- **Update**: The AI pull request review now runs at two named effort tiers —
  [AI responder workflows](features/ai-responder-workflows.md) implemented.
  `@claude review light`/`full` or a `[ci:review-effort=…]` body marker picks
  the tier, the comment outranking the marker, and a requested tier is obeyed
  exactly; with none the review sizes itself and keeps the session model.
  Neither tier waives `ai-review-present`, the metadata check, or the
  durable-knowledge pass.
- **Update**: Findings validation now runs on the light model at both effort
  tiers, under one validator prompt shared by the tiers — [PR review effort
  tiers](architecture/pr-review-effort-tiers.md) records why the gate's
  strictness belongs in the prompt rather than in the model size, and why the
  slot that scales with finding count is the one to bound.
- **Update**: Removed the `require-review` publish-or-fail check from the
  responder action. A timestamp window cannot tell this run's review from a
  concurrent run's, so an abandoned run passed on another run's review — [the
  orchestrator ends its turn while its passes are still
  running](bugs/review-orchestrator-ends-turn-while-passes-run.md) stays open
  and records the attempt, the concurrency reason, and the quota hypothesis with
  the telemetry for and against.
- **Update**: Every apt package the Ansible roles install is pinned per Ubuntu
  release and architecture in a generated `vars/apt_pins_<suite>_<arch>.yml`,
  refreshed by `scripts/apt-pins-refresh.py` and kept current by two `deb`
  custom managers batched into one automerged Renovate PR.
- **Creation**: [Ansible apt pins](architecture/ansible-apt-pins.md) records the
  decision, the per-role repository sets, and the pin-rot and rebuild costs it
  buys.
- **Creation**: [Fisher install over untracked
  plugins](bugs/fisher-install-over-untracked-plugins.md) fixed — `fish_setup`
  now reconciles `fish_plugins` with `fisher update` instead of installing each
  pinned plugin.
- **Update**: `.github/renovate.json` is validated by a pre-commit hook and a
  workflow, both running `renovate-config-validator --no-global --strict`.
- **Update**: Refreshed the nine codebase-map docs whose tracked sources the apt
  pinning and the validator gate moved, and masked the automerged apt pin values
  out of the Ansible map digests.

## 2026-09-21

- **Creation**: [A capitalized @Claude mention was admitted, then
  misrouted](bugs/responder-mention-case-sensitivity.md) fixed — the preflight
  `if:` gate folds case and every mention test behind it now does too, so
  `@Claude review` reaches the review job and its effort label instead of
  dispatching as a free-form task.
- **Update**: Refreshed the three codebase-map docs whose tracked sources the
  case fix moved.
- **Update**: The installer- and registry-sourced dependencies in the Ansible
  roles (Bun, uv, Yarn, the agent CLIs, fisher, bass) are pinned in each role's
  `defaults/`, and Renovate's two new custom regex managers keep them current as
  one automerged group.
- **Creation**: [Renovate maintains checksum-carrying
  pins](features/renovate-maintains-checksums.md) proposed — the pins carrying a
  per-architecture checksum need `postUpgradeTasks`, whose command gate only a
  self-hosted Renovate can open.
- **Update**: Refreshed the six codebase-map docs whose tracked sources the
  pinning moved, and masked the automerged pin values out of the Ansible map
  digests.

## 2026-09-19

- **Creation**: [The review orchestrator ends its turn while its passes are
  still running](bugs/review-orchestrator-ends-turn-while-passes-run.md) filed —
  a headless responder run ends when the orchestrator's turn ends, so a turn
  that stops on a status update publishes no review and still goes green.
- **Creation**: [PR review effort tiers](architecture/pr-review-effort-tiers.md)
  records why the review has two named tiers, why an explicitly requested tier
  is absolute, and why the responder's preflight rather than the skill resolves
  it.
- **Update**: Refreshed the six codebase-map docs whose tracked sources the
  review effort-tier work moved — the responder workflow, the responder
  composite action, and the catalog skill tree.
- **Creation**: [Test the responder workflow's inline
  JavaScript](backlog/test-responder-workflow-js.md) filed — no harness in this
  repository reaches the `github-script` blocks that decide review tier, model,
  and prompt.

## 2026-09-12

- **Creation**: [AI review gate was self-waivable from the PR
  body](bugs/ai-review-gate-self-waivable.md) fixed — the opt-out marker,
  renamed `[ci:skip-ai-review]`, now suppresses only the review responder, and
  `ai-review-present` no longer reads it, so a marked pull request keeps a red
  required check.
- **Update**: Refreshed the three codebase-map docs whose tracked sources the
  gate fix moved.
- **Creation**: [The review opt-out marker fired too
  broadly](bugs/skip-ai-review-marker-overreach.md) fixed — the marker is
  matched only as a whole line, so a body that discusses it stays prose, and an
  explicit `@claude review` now outranks it.

## 2026-09-11

- **Update**: Refreshed the five codebase-map docs whose tracked sources the
  consumer-facing fixes moved — the responder merges the gitignored local
  settings layer only where it exists, and the consumption guide requires an
  adopter to exclude `docs/knowledge/**` from Prettier.

## 2026-09-10

- **Update**: Refreshed the three codebase-map docs whose tracked sources the
  responder and CI changes moved — `run-claude-responder` now uploads its
  execution file and checks it for a usage limit under `always()`, so a failed
  Claude step still leaves inspectable output.

## 2026-09-09

- **Update**: [Consolidate the self-improve plugin into this
  repository](plans/20260909-consolidate-self-improve-plugin.md) done — the
  plugin tree, its tests, and its Makefile moved into this repository, the
  Claude marketplace publishes it as a second plugin, and its live tests are
  guarded at collection behind `SELF_IMPROVE_RUN_LIVE`.
- **Creation**: [Self-improve plugin in the
  catalog](features/self-improve-plugin-in-catalog.md) implemented and recorded
  in [unreleased](releases/2.0.0.md). It is published from the Claude
  marketplace and not enabled by anything the repository ships.
- **Update**: Refreshed the eight codebase-map docs whose tracked sources the
  consolidation changed — the reinstall scripts now install every published
  plugin, and the agent-files workflow runs a third pytest suite.

## 2026-09-08

- **Release**: cut [1.0.0](releases/1.0.0.md) from the unreleased accumulator —
  16 features and 4 fixes — and started a fresh [unreleased](releases/2.0.0.md)
  page.
- **Update**: [Connect validator
  warnings](plans/20260907-connect-validator-warnings.md) done — `--recommend`
  now produces skill frontmatter and structure recommendations, `--errors-only`
  is the single suppression flag, and warnings still never move the exit code.
- **Update**: [Validator warning
  visibility](bugs/validator-warning-visibility.md) fixed and recorded in
  [1.0.0](releases/1.0.0.md). The two skill validators are wired into the
  engine, `main.py` reads the real argparse destinations, `--no-warnings` is
  gone, and the CLI contract is stated in the validator CLI interface.
- **Map**: refreshed the validator package, its tests, its validators, the
  agentdev catalog, and its skills against their current sources; all 27 map
  docs match their tracked-source digests.

## 2026-09-06

- **Update**: [Track template consumption progress and
  choices](plans/20260906-template-consumption-progress.md) done — setup now
  persists a resumable task and choice record before executing the consumption
  guide, and update mode retains those choices across episodes.
- **Creation**: [Resumable template
  consumption](features/resumable-template-consumption.md) implemented and
  recorded in [1.0.0](releases/1.0.0.md), with the two-record ownership,
  migration, resume, and IWE-summary contract synced into [Template
  consumption](spec/template-consumption.md).
- **Map**: refreshed the agentdev catalog, bin, skills, tests, pull-request
  checks, GitHub automation, workflows, and consumer seed against their current
  sources; all codebase-map digests match the checkout.
- **Update**: `source_digest` is now the only map-freshness mechanism. The
  legacy `commit` pin, its `UNKNOWN_COMMIT`/`NO_COMMIT` verdicts, and the
  `codebase` schema's `commit` field are gone; a doc without a digest is
  `NO_DIGEST`. `stale-map-docs.py` now runs in the agent-files CI job, so a map
  doc that drifts from its sources fails the build.
- **Map**: refreshed the agentdev catalog, its skills, its tests, and the
  knowledge workspace against their current sources (`b928025`); all 27 map docs
  match their tracked-source digests.
- **Update**: [Repository-owned IWE seed for
  consumers](plans/20260905-consumer-iwe-seed.md) done — both adoption workflows
  can seed and onboard fresh IWE project memory without replacing existing
  consumer knowledge, and update mode excludes both publisher memory and
  initialization-only seed content.
- **Creation**: [Consumer IWE seed](features/consumer-iwe-seed.md) implemented
  and recorded in [1.0.0](releases/1.0.0.md). The reusable seed is maintained in
  this repository, validated in an isolated consumer layout, and specified in
  [Template consumption](spec/template-consumption.md).
- **Update**: [Template consumption](spec/template-consumption.md) now requires
  a repository-owned seed, ordered setup and mapping for fresh adoption, and
  preservation of consumer-authored knowledge during adoption and updates.
- **Update**: [Python skill scripts](plans/20260905-python-skill-scripts.md)
  done — the codebase-map freshness classifier now runs as standard-library
  Python on the shared Python result-code helper while preserving its output,
  exit-code, and source-digest contracts.
- **Update**: [Digest masks for map docs](plans/20260905-digest-masks.md) done —
  machine-managed pins are normalized before codebase-map source fingerprints
  are computed, while surrounding structural changes still mark affected
  documents stale.
- **Update**: [Pin bumps invalidate map
  docs](bugs/pin-bumps-invalidate-map-docs.md) fixed and recorded in
  [1.0.0](releases/1.0.0.md).
- **Update**: Refreshed the codebase map: six changed scopes were re-read, all
  source digests were verified, and the tested consumer IWE seed was added as
  the twenty-seventh mapped document.
- **Update**: Refreshed the codebase map — the catalog, bin helpers, skills,
  plugin tests, knowledge machinery, and the devcontainer lifecycle flow re-read
  against the checkout, anchors re-verified, and source digests bumped.
- **Creation**: [Xpra port forwarding](spec/xpra-port-forwarding.md) specifies
  the fixed container-port and VS Code local-remapping contracts.
- **Update**: [Use VS Code port forwarding for
  Xpra](plans/20260905-xpra-vscode-port-forwarding.md) done — Xpra uses
  container port 14500 independently of `DEVCONTAINER_ID`, explicit `--port`
  overrides remain supported, and concurrent devcontainers are reachable through
  distinct VS Code-forwarded local addresses.

## 2026-09-05

- **Creation**: [Pin bumps invalidate map
  docs](bugs/pin-bumps-invalidate-map-docs.md) — `source_digest` fingerprints
  whole tracked files, so an automerged Renovate pin bump marks a map doc stale
  even when the doc never mentions the pinned value. Five of twenty-six docs
  went amber on three one-line bumps.
- **Update**: [Missing map skill](bugs/missing-map-skill.md) fixed —
  `/agentdev:iwe-map` now owns the `data/codebase/` lane that Setup, Verify, and
  the operating loop all handed to a skill that did not exist. Initial mode
  surveys the outside of the system, confirms the containment tree, then writes
  one doc per component at its canonical key plus flow and api docs; refresh
  mode re-reads only the docs whose tracked source contents no longer match
  their `source_digest`, classified by the bundled `stale-map-docs.sh`. This
  repository is mapped: 26 docs under Codebase. Recorded in
  [1.0.0](releases/1.0.0.md) and specified in [IWE workflow
  skills](spec/iwe-workflow-skills.md); [its
  plan](plans/20260903-iwe-map-skill.md) is done.
- **Creation**: [Consumer PR description
  guidance](features/pr-description-guidance.md) implemented, recorded in
  [1.0.0](releases/1.0.0.md) — a consuming repository may now capture its extra
  PR-template sections as instructions in a consumer-owned
  `.github/pr-description-guidance.md`, which `pr-gen-description` reads with
  precedence over its own section generation while preserving the Verification /
  Reviewer Handoff tense split, and template setup and update evaluate an
  existing template into covered/extras buckets before anything is written.
  Specified in [Template consumption](spec/template-consumption.md) and
  classified in [Template boundary](architecture/template-boundary.md); [its
  plan](plans/20260903-pr-description-guidance.md) is done.

## 2026-09-04

- **Creation**: five decision records recovered from the Dr.QP history the
  template was extracted from — [Agent auth
  persistence](architecture/agent-auth-persistence.md), [Nested Docker
  provisioning](architecture/nested-docker-provisioning.md), [MCP gateway
  transport](architecture/mcp-gateway-transport.md), [gh authentication
  shim](architecture/gh-authentication-shim.md), and [Formatter
  ownership](architecture/formatter-ownership.md). Each records a rejected
  alternative that the code alone cannot show; every decision was re-verified
  against this repository before being written.

## 2026-09-03

- **Creation**: the codebase map — 26 documents under Codebase (19 components, 3
  flows, 2 interfaces), written by `/agentdev:iwe-map` in initial mode from the
  tree at `eb60f60`, per [Add the iwe-map
  skill](plans/20260903-iwe-map-skill.md).
- **Update**: [One AI review workflow with a needs-coupled
  gate](plans/20260903-single-ai-review-workflow.md) done — the responder and
  the merge gate are now one workflow whose `ai-review-present` job `needs` the
  review job, so the check stays pending while a review runs and evaluates
  without polling; PR comment mentions bridge into a `workflow_dispatch` on the
  head branch so the review runs the branch's own file. `require-ai-review.yml`
  is deleted and the acceptance test moved to the `ai-review-status` composite
  action. Recorded under [AI responder
  workflows](features/ai-responder-workflows.md) and synced into [AI review
  gate](spec/ai-review-gate.md) and [Template
  consumption](spec/template-consumption.md).

## 2026-09-02

- **Update**: [Audit every plan edit in a fresh
  context](plans/20260902-audit-plan-edits-in-fresh-context.md) done — a
  fresh-context `Durable Knowledge Auditor` agent now gates every plan-intent
  edit in the Plan skill, and Implement and Verify share its Evidence-residue
  vocabulary. Recorded under [Never write a working
  logbook](features/no-working-logbooks.md) and specified in [IWE workflow
  skills](spec/iwe-workflow-skills.md).
- **Creation**: [Install the agentdev catalog into the
  image](features/catalog-installed-in-image.md) implemented, recorded in
  [1.0.0](releases/1.0.0.md), with the build-time install and the
  `~/.claude.json` handoff reorder synced into [Catalog
  lifecycle](spec/catalog-lifecycle.md); [its
  plan](plans/20260817-catalog-install-in-image.md) is done.
- **Creation**: [Gitignore-aware agent file
  discovery](features/gitignore-aware-agent-file-discovery.md) implemented,
  recorded in [1.0.0](releases/1.0.0.md), and specified by [Agent file
  discovery](spec/agent-file-discovery.md); [its
  plan](plans/20260901-gitignore-aware-discovery.md) is done.
- **Creation**: [Agentdev IWE workflow
  skills](features/agentdev-iwe-workflow-skills.md) implemented, recorded in
  [1.0.0](releases/1.0.0.md), and reflected in [Template
  consumption](spec/template-consumption.md); [its
  plan](plans/20260816-move-iwe-skills-to-agentdev.md) is done.
- **Update**: [Persist the pre-commit hook cache on the agentdev-cache
  volume](plans/20260902-persist-pre-commit-cache.md) done — `PRE_COMMIT_HOME`
  now points at the per-worktree `agentdev-cache` volume, so the ~33s cold hook
  install is paid only on the first create per worktree and every rebuild starts
  warm. The failure-log tail in `setup-pre-commit.sh` follows `PRE_COMMIT_HOME`.
  No behavioral change — cache location and startup latency only, so no spec
  changed.
- **Creation**: [Persist the pre-commit hook
  cache](features/persist-pre-commit-cache.md) implemented, recorded in
  [1.0.0](releases/1.0.0.md).

## 2026-09-01

- **Update**: PR body structure moved into the `agentdev` catalog, replacing
  `## How to Test` with `## Verification` (closed items, `- [x]` +
  `**Evidence:**`) and `## Reviewer Handoff` (open items, `- [ ]` +
  `**Closed by:**`), per [PR verification
  sections](architecture/pr-verification-sections.md). **Downstream break**, in
  the same register as the `setup-python-venv` activation change: a consuming
  repository that copied `.github/pull_request_template.md` still holds the old
  structural version, and its updated `agentdev` skills now ignore it —
  `pr-gen-description` states the structure itself and reports that the copied
  template was not consulted rather than reading one out of it. Adopting means
  replacing the copied file with the pointer stub or deleting it; keeping it
  costs nothing but a report on every run.
- **Creation**: [Split PR How to Test into Verification and Reviewer
  Handoff](features/pr-verification-sections.md) implemented, recorded in
  [1.0.0](releases/1.0.0.md); [its
  plan](plans/20260815-pr-verification-sections.md) is done.
- **Creation**: [Critical docs and durable-knowledge review in
  pr-review](features/pr-review-docs-durable-knowledge.md) implemented, recorded
  in [1.0.0](releases/1.0.0.md); [its
  plan](plans/20260831-pr-review-docs-durable-knowledge.md) is done. `pr-review`
  now reviews docs and skills critically by invoking `iwe-audit` in a
  report-only diff mode, with a conditional file-following durable-knowledge
  pass; only version-only and generated-file-only diffs stay fast-approved.

## 2026-08-31

- **Update**: [Let pre-commit own
  formatting](plans/20260831-pre-commit-owns-formatting.md) done — the
  pre-commit hooks are the single local formatting path, now extended to merge
  commits via the `pre-merge-commit` hook type. The `local-reformat` mandates in
  `pr-open` and `git-merge-resolve` and the formatting routes in the
  `principal-engineer` and `tdd-refactor` agents are removed, `local-reformat`'s
  obligation language is softened, and the redundant `python-format-lint` skill
  is retired into the `AGENTS.md` Python section.
- **Creation**: [Let pre-commit own
  formatting](features/pre-commit-owns-formatting.md) implemented, recorded in
  [1.0.0](releases/1.0.0.md).
- **Update**: [Template consumption](spec/template-consumption.md) §5 item 5 now
  keeps the consuming project's `zizmor` hook as `language: system` resolved
  from `PATH`, dropping the bare-host `zizmorcore/zizmor-pre-commit`
  substitution — a workflow this container-only product does not support. No
  requirement or scenario changed; the edit is procedural adoption guidance.
- **Update**: [AI responder workflows](plans/20260816-ai-responder-workflows.md)
  done — the Claude-only `ai-responder.yml` and the `require-ai-review.yml` gate
  are imported; the responder reviews with the branch's own agentdev catalog and
  an indexed CBM by running the devcontainer lifecycle hooks after checkout, and
  `ai-review-present` is now a required status check in the `main` ruleset.
- **Creation**: [AI responder workflows](features/ai-responder-workflows.md)
  implemented, and [AI review gate](spec/ai-review-gate.md) records the gate's
  acceptance contract and the responder's fork/write-access security boundary.

## 2026-08-24

- **Update**: [Preserve approved wording across the explore
  handoff](plans/20260817-preserve-approved-wording.md) done — Explore now
  writes approved text to `.tmp/approved-wording-<slug>.md` before the
  conversation continues and names that file in the handoff, and Plan's task
  format distinguishes describing an action from paraphrasing approved content.
  Both skills carry the same falsifiable test: whether a session starting cold
  from the written plan could reproduce the agreed bytes.
- **Creation**: [Preserved approved
  wording](features/preserved-approved-wording.md) records the split obligation
  — Explore writes, Plan inlines — and why neither half binds alone, plus the
  rejection of a `data/drafts/` hub in favour of `.tmp/`.
- **Update**: [IWE workflow skills](spec/iwe-workflow-skills.md) extends the
  Explore and Plan requirements with the verbatim-preservation obligation, one
  new scenario on each side.
- **Update**: [Never write a working
  logbook](plans/20260817-no-logbooks-in-the-graph.md) done — the rule against
  working-logbook prose now binds every file in the repository from `AGENTS.md`
  Best Practice 8, with the durable-knowledge vocabulary extracted there from
  `## Project memory` so the graph manual and the `iwe-audit` skill point at one
  definition instead of three.
- **Creation**: [Never write a working logbook](features/no-working-logbooks.md)
  records the two coexisting tests, the graph's three narrative exceptions, the
  plan's single narrative section, Implement's capture-and-route contract, and
  the widened auditor scope. Commit messages stay out; `/agentdev:git-commit`
  owns them.
- **Update**: [IWE workflow skills](spec/iwe-workflow-skills.md) gains
  `Requirement: Plans record intent, not the path taken to it` — the
  workflow-skill half of the rule. The general authoring convention gets no spec
  document, since `AGENTS.md` is its only statement.
- **Creation**: [Detect plan narration growth
  mechanically](backlog/detect-plan-narration-growth.md) files the deferred
  automation. The plan-shape gate reads structure, and narration has none —
  every proxy considered fires on legitimately long plans or misses a short
  dense one.

## 2026-08-16

- **Update**: [Embed structured spec deltas in IWE
  plans](plans/20260816-structured-plan-spec-deltas.md) done — `## Spec changes`
  now has three risk-scaled forms: an explicit `None`, a linked spec plus a
  concise normative outcome, or a fenced `ADDED`/`MODIFIED`/`REMOVED` delta
  carrying complete post-change requirements. The change that mattered was
  naming the delta *intent* rather than truth, which dissolved a structural
  disagreement: Verify had demanded that durable specs already reflect an
  unshipped change while Ship was the skill that updates them afterwards. Verify
  now judges code against the durable spec plus the plan's intent, and a
  not-yet-created spec is valid when the plan supplies its contract.
- **Creation**: [Risk-scaled spec deltas](features/risk-scaled-spec-deltas.md)
  records the three forms, the intent-versus-truth boundary, and the four
  exclusions — no change bundle, store, separate delta file, or application
  engine. OpenSpec's notation is adopted; its parser is not.
- **Creation**: [Exercise REMOVED delta blocks end to
  end](backlog/exercise-removed-delta-blocks.md) files the gap this shipment
  left open. `ADDED` and `MODIFIED` were worked end to end by the plan's own
  delta; `REMOVED` was specified in the same pass and never run, so the plan's
  fixture bullet asking for all three is unmet. Verify flagged it as a WARNING,
  not a CRITICAL — no ticked task claimed otherwise.
- **Update**: [Make plan checkboxes carry their
  evidence](plans/20260815-honest-plan-checkboxes.md) done — a ticked `- [x]`
  now requires an indented `- **Evidence:**` child naming the commit, test run,
  or CI run that closed it. A find-and-replace can flip eight boxes; it cannot
  write eight evidence lines. Plan specifies the format and gains a
  task-atomicity rule, Implement writes the evidence in the same edit and never
  changes two boxes at once, and Verify's unchecked-box CRITICAL finally has a
  ticked-box counterpart recommending "untick it". A pytest over `data/plans/`
  enforces the shape from the suite, a pre-commit hook, and the knowledge-base
  CI job — the first gate here that reads plan documents rather than agent
  files.
- **Creation**: [Plan checkbox evidence](spec/plan-checkbox-evidence.md) records
  the contract as durable requirements: what a tick must carry, how tasks are
  sized so a tick can be honest, and what the gate does and cannot do. It reads
  shape only; whether a claim is *true* stays Verify's judgment and a human's.
- **Update**: [Plan checkbox over-claiming](bugs/plan-checkbox-over-claiming.md)
  fixed and recorded in [1.0.0](releases/1.0.0.md). `48d0f79` had fixed the
  instance and left both root causes standing; this closes them.
- **Update**: [Name the missing handoff routes in explore and
  verify](plans/20260816-skill-handoff-routes.md) done — Explore's
  `## Capturing` now routes an established defect to `data/bugs/<slug>.md`, and
  Verify's unchecked-box CRITICAL offers a third way out (revise the plan to
  drop the task) alongside completing and ticking, which Ship's no-override rule
  had left unstated. [Verification in the main
  loop](features/verification-in-the-main-loop.md) records the same three
  routes. No spec changed: the plan's rationale for that was corrected at ship
  time, since [IWE workflow skills](spec/iwe-workflow-skills.md) now covers
  these skills and was re-checked against both edits.
- **Creation**: [Strengthen the workflow skill
  contracts](plans/20260815-strengthen-workflow-skill-contracts.md)
  reconstructed post-hoc from the OpenSpec change bundle's proposal, design, and
  tasks artifacts, which `.gitignore` keeps out of the repository. Records the
  eight design decisions and their rejected alternatives behind the Explore-to-
  Ship prompt edits in `0d4d37b`, `61cce13`, `fcdd45a`, and `a35c802`; filed
  `done` because the graph already carries the shipped state.
- **Creation**: [IWE workflow skills](spec/iwe-workflow-skills.md) records the
  verified Explore, Plan, Implement, Verify, and Ship behavior as durable
  requirements and scenarios.
- **Update**: [Verification in the main
  loop](features/verification-in-the-main-loop.md) implemented and recorded in
  [1.0.0](releases/1.0.0.md).

## 2026-08-15

- **Update**: [Finish uv-run-only in CI](plans/20260815-uv-run-in-ci.md) done —
  all nine tasks verified green in CI (PR #61). CI stops activating the
  environment, syncs with `--locked` so lockfile drift fails at provisioning,
  and pins uv to the `actions/setup-python` interpreter; `python-lint-check.sh`
  no longer installs as a side effect of a check. Harvested from the parallel
  `no-venv-openspec` branch (PR #60); two of its changes declined with reasoning
  recorded.
- **Update**: [uv-run-only environment](features/uv-run-only-environment.md)
  extended to cover CI — the feature now spans both sides of the repository, so
  no spec changed: `data/spec/template-consumption.md` covers adapting the
  template into a consuming project, not this repository's CI provisioning
  contract.
- **Update**: [Drop the .venv symlink](plans/20260814-drop-venv-symlink.md) done
  — the in-tree symlink is gone and every consumer reaches the environment
  through `uv run` or the fixed `/uv/venvs/ws-project` path.
- **Creation**: [uv-run-only environment](features/uv-run-only-environment.md)
  implemented, recorded in [1.0.0](releases/1.0.0.md).
- **Creation**: Proposed [Verification in the main
  loop](features/verification-in-the-main-loop.md) — ship's step 1 names the
  verify skill without invoking it, so verification at ship time is
  discretionary rather than compelled.

## 2026-08-01

- **Initialization**: Created the project workspace — [product](product.md) as
  the foundation, with [plans](plans.md), [backlog](backlog.md),
  [milestones](milestone.md), and [someday](someday.md) for work, and
  [features](features.md), [bugs](bugs.md), and [releases](releases.md) for
  delivery.
- **Creation**: Seeded the reference side — [spec](spec.md), codebase,
  [architecture](architecture.md), and [concept](concept.md) — with example
  documents showing the shape of each type.
