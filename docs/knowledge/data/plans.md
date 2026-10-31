---
type: hub
description: Implementation plans, migrations, and design proposals, one document per unit of work.
stage: living
generated:
  by: codex/gpt-5
  at: 2026-10-23T03:13:20Z
---

# 🗺️ Plans

*Every plan lives in `plans/YYYYMMDD-<slug>.md` and is listed here, always — a
status change moves its link between sections, never removes it. `## Active`
holds plans without a `status`; `## Done` mirrors `status: done`; `## Cancelled`
mirrors `status: cancelled`. The plan skill files new plans, the ship skill
moves them.*

## Active

[Move the Coder template's knowledge into
coder-ide-baseline](plans/20261031-coder-template-knowledge-split.md)

[AI review verdicts gate merge and trusted bots are
auto-approved](plans/20261030-ai-review-verdicts-and-bot-approval.md)

[Replace the runtime shell scripts with one agentdev-runtime
CLI](plans/20261029-off-bash-migration.md)

[Remove Codex support](plans/20261031-remove-codex.md)

[Replace Super-Linter with pre-commit in
CI](plans/20261031-pre-commit-replaces-super-linter.md)

[Run the Dev Container as a non-root account with one home
volume](plans/20261030-devcontainer-home-volume.md)

[Share one BuildKit builder across Coder
workspaces](plans/20261013-shared-buildkit-workspace.md)

[Bootstrap agentdev natively on macOS with
Homebrew](plans/20261013-macos-native-bootstrap.md)

[The AI responder posts as the plume-works-quill
App](plans/20261030-responder-quill-app-identity.md)

[Resume interrupted Claude PR reviews on a persistent
runner](plans/20260909-resumable-claude-review-sessions.md)

## Done

[Port the catalog's bundled shell scripts to
Python](plans/20261029-catalog-scripts-python.md)

[Verify report cache](plans/20261030-verify-report-cache.md)

[Escalate a client failure to the dependency that caused
it](plans/20261030-dbus-keyring-flaky-test.md)

[iwe-branch-name v2: one iteration counter per
plan](plans/20261030-iwe-branch-name-v2.md)

[Name Remote Control environments after their
launcher](plans/20261029-remote-control-environment-names.md)

[Publish the reusable agentdev Dev Container
image](plans/20261023-reusable-agentdev-devcontainer.md)

[Move the Expo bridge knowledge into its own
repository](plans/20261028-move-expo-bridge-kb.md)

[Start Claude Remote Control in the standalone
runtime](plans/20261027-standalone-remote-control-autostart.md)

[Ship a standalone OpenCode
container](plans/20261017-standalone-opencode-container.md)

[PR skills drive the AI review lifecycle on the single review
workflow](plans/20261023-pr-skills-ai-review-lifecycle.md)

[Assignee-triggered AI re-reviews replace the comment
trigger](plans/20261026-assignee-review-trigger.md)

[Let Implement verify, fix, and revise on its
own](plans/20261026-autonomous-implement-loop.md)

[Run Verify from a fresh context](plans/20261026-verify-in-fresh-context.md)

[Configurable Remote Control spawn mode, worktree by
default](plans/20261025-claude-remote-control-spawn-mode.md)

[iwe-branch-name skill](plans/20261020-iwe-branch-name.md)

[Bundle a Playwright browser in the development
image](plans/20261021-playwright-browser.md)

[Extract a reusable IWE bootstrap
skill](plans/20261023-reusable-iwe-bootstrap.md)

[Opt-in Claude Remote Control server
mode](plans/20261023-claude-remote-control-server-mode.md)

[Mask version-only changes during a map
refresh](plans/20261021-map-masks-version-bumps.md)

[Show the full OpenCode slash-command
invocation](plans/20261021-opencode-command-echo.md)

[Keep the Remote Control pin on the pane's current
conversation](plans/20261021-remote-control-pin-follows-clear.md)

[Gate image publication on acceptance](plans/20261020-gate-image-publication.md)

[Make OpenCode v2 the devcontainer
default](plans/20261018-opencode-v2-default.md)

[Port the IWE workflow e2e suite to
pytest](plans/20261019-iwe-workflows-e2e-pytest.md)

[Automatically index OpenCode workspaces in
CBM](plans/20261018-opencode-workspace-cbm-indexing.md)

[Configure devcontainer OpenCode for full
access](plans/20261018-opencode-full-access-config.md)

[Autostart the OpenCode web UI on
Coder](plans/20261016-opencode-web-coder-autostart.md)

[Guard every gh stack push against overwriting a layer's remote
commits](plans/20261017-gh-stack-push-guard.md)

[Declare release impact when a plan is
written](plans/20261016-release-impact-at-plan-time.md)

[Expo profile for template
adoption](plans/20261014-expo-eas-template-profile.md)

[Cap Docker storage with automatic garbage
collection](plans/20261013-docker-storage-gc.md)

[Resume the Remote Control conversation across
restarts](plans/20261013-resume-claude-remote-control.md)

[Persist the Coder workspace containerd image
store](plans/20261011-persist-coder-workspace-containerd.md)

[Start Claude Remote Control from the Coder
agent](plans/20261011-coder-claude-remote-control.md)

[Configure the gh credential helper from the Coder
agent](plans/20261011-coder-agent-gh-credential-helper.md)

[Update branch pulls its upstream before merging the
base](plans/20261012-update-branch-pulls-upstream.md)

[Agent-owned Ship and Implement
workflows](plans/20261007-agent-owned-ship-implement.md)

[Remove Coder agent auth seeding; keep Claude Remote Control
autostart](plans/20261009-remove-coder-agent-auth-seeding.md)

[Install the catalog agents into Codex](plans/20261007-codex-catalog-agents.md)

[Run Node tooling through bun instead of
npm](plans/20260925-bun-for-node-tooling.md)

[Configure devcontainer Codex for full
access](plans/20261005-codex-full-access-config.md)

[Keep agentdev enabled in the responder and collect review passes in the
foreground](plans/20260929-responder-review-grounded-and-collected.md)

[Ship the reachable-scenario bar with part-by-part validation in
pr-review](plans/20261005-pr-review-scenario-validation.md)

[Adopt GitHub native stacked pull
requests](plans/20261002-native-stacked-prs.md)

[Spike: does a reachable-scenario bar let pr-review find Greptile-class
bugs](plans/20260929-pr-review-scenario-bar-spike.md)

[Load the agentdev catalog into OpenCode through a bridge
plugin](plans/20261001-opencode-catalog-bridge.md)

[Reference bundled skill code by skill-relative agent-code
paths](plans/20261001-skill-relative-agent-code.md)

[Resolve merge conflicts in
pr-feedback-resolution](plans/20261002-pr-feedback-resolve-merge-conflicts.md)

[Refresh the codebase map before pushing and keep its staleness out of AI
reviews](plans/20260929-map-refresh-before-push.md)

[Self-hosted Renovate in the agent-desktop
image](plans/20260925-self-hosted-renovate.md)

[git-new-branch skill](plans/20260928-git-new-branch-skill.md)

[Add the iwe-capture skill](plans/20260927-iwe-capture-skill.md)

[Effort tiers for the AI pull request
review](plans/20260917-pr-review-effort-tiers.md)

[Consolidate the self-improve plugin into this
repository](plans/20260909-consolidate-self-improve-plugin.md)

[Self-improve MVP](plans/20260909-self-improve-mvp.md)

[Connect validator warnings](plans/20260907-connect-validator-warnings.md)

[Track template consumption progress and
choices](plans/20260906-template-consumption-progress.md)

[Repository-owned IWE seed for consumers](plans/20260905-consumer-iwe-seed.md)

[Python skill scripts](plans/20260905-python-skill-scripts.md)

[Digest masks for map docs](plans/20260905-digest-masks.md)

[Use VS Code port forwarding for
Xpra](plans/20260905-xpra-vscode-port-forwarding.md)

[Add the iwe-map skill](plans/20260903-iwe-map-skill.md)

[Consumer PR description guidance](plans/20260903-pr-description-guidance.md)

[One AI review workflow with a needs-coupled
gate](plans/20260903-single-ai-review-workflow.md)

[Audit every plan edit in a fresh
context](plans/20260902-audit-plan-edits-in-fresh-context.md)

[Install the agentdev catalog into the
image](plans/20260817-catalog-install-in-image.md)

[Move the IWE workflow skills into the agentdev
plugin](plans/20260816-move-iwe-skills-to-agentdev.md)

[Gitignore-aware file discovery in
validate_agent_files](plans/20260901-gitignore-aware-discovery.md)

[Persist the pre-commit hook cache on the agentdev-cache
volume](plans/20260902-persist-pre-commit-cache.md)

[Critical docs and durable-knowledge review in
pr-review](plans/20260831-pr-review-docs-durable-knowledge.md)

[Split PR How to Test into Verification and Reviewer
Handoff](plans/20260815-pr-verification-sections.md)

[Let pre-commit own formatting](plans/20260831-pre-commit-owns-formatting.md)

[AI responder workflows](plans/20260816-ai-responder-workflows.md)

[Preserve approved wording across the explore
handoff](plans/20260817-preserve-approved-wording.md)

[Never write a working logbook](plans/20260817-no-logbooks-in-the-graph.md)

[Embed structured spec deltas in IWE
plans](plans/20260816-structured-plan-spec-deltas.md)

[Make plan checkboxes carry their
evidence](plans/20260815-honest-plan-checkboxes.md)

[Name the missing handoff routes in explore and
verify](plans/20260816-skill-handoff-routes.md)

[Strengthen the workflow skill
contracts](plans/20260815-strengthen-workflow-skill-contracts.md)

[Finish uv-run-only in CI](plans/20260815-uv-run-in-ci.md)

[Drop the .venv symlink](plans/20260814-drop-venv-symlink.md)

## Cancelled
