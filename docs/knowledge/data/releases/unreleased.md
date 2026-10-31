---
type: release
description: The accumulator page for work merged but not yet released.
version: unreleased
stage: unreleased
status: draft
generated:
  by: opencode/gpt-6.1-sol
  at: 2026-10-21T05:18:06Z
---

# Unreleased

*Work that has shipped to main but not yet to users. The ship skill adds an
inclusion link here for every feature or fix as it lands — a new feature under
`## Added`, a released feature that gained behavior under `## Changed`, a bug
under `## Fixed`; cutting a release renames this file to the version number and
starts a fresh one.*

## Added

[Remote Control server mode](../features/claude-remote-control-server-mode.md)

[Map masks version-only changes](../features/map-masks-version-bumps.md)

[Renovate maintains checksum-carrying
pins](../features/renovate-maintains-checksums.md)

[git-new-branch](../features/git-new-branch.md)

[Self-improve plugin in the
catalog](../features/self-improve-plugin-in-catalog.md)

[Fresh codebase map on push](../features/fresh-map-on-push.md)

[Native stacked pull requests](../features/native-stacked-prs.md)

[OpenCode as a catalog host](../features/opencode-catalog-host.md)

[Resume the Remote Control conversation across
restarts](../features/claude-remote-control-resume.md)

[Expo apps build for iOS through EAS](../features/expo-eas-builds.md)

[Docker storage limits](../features/docker-storage-limits.md)

[update-branch pulls the branch's
upstream](../features/update-branch-pulls-upstream.md)

[Remote Control autostart on
Coder](../features/coder-remote-control-autostart.md)

[Agent sign-in without credential
seeding](../features/agent-sign-in-without-seeding.md)

[Codex full-access config](../features/codex-full-access-config.md)

[PR feedback resolution resolves merge
conflicts](../features/pr-feedback-resolves-merge-conflicts.md)

[bun as the only JavaScript runner](../features/bun-only-javascript-runner.md)

[OpenCode web UI autostart on
Coder](../features/opencode-web-coder-autostart.md)

[OpenCode full-access config](../features/opencode-full-access-config.md)

[Automatic CBM indexing for OpenCode
workspaces](../features/opencode-workspace-cbm-indexing.md)

[iwe-branch-name](../features/iwe-branch-name.md)

[Playwright browser in the development image](../features/playwright-browser.md)

[Autonomous Implement loop](../features/autonomous-implement-loop.md)

[Standalone OpenCode container](../features/standalone-opencode-container.md)

[Remote Control autostart in the standalone
runtime](../features/standalone-remote-control-autostart.md)

[Remote Control environment
names](../features/remote-control-environment-names.md)

[Reusable agentdev Dev Container](../features/reusable-agentdev-devcontainer.md)

[Verify report cache](../features/verify-report-cache.md)

## Changed

[Verification in the main loop](../features/verification-in-the-main-loop.md)

[Reusable IWE bootstrap](../features/consumer-iwe-seed.md)

[Agentdev IWE workflow skills](../features/agentdev-iwe-workflow-skills.md)

[AI responder workflows](../features/ai-responder-workflows.md)

## Fixed

[Bug: every gh call in the devcontainer leaks a D-Bus session and a
keyring](../bugs/devcontainer-dbus-autolaunch-leak.md)

[Bug: CI/CD publishes images before testing
them](../bugs/ci-publishes-images-before-acceptance.md)

[Bug: xpra_setup installs Ubuntu's xpra
3.1.5](../bugs/xpra-setup-installs-ubuntu-xpra.md)

[Bug: gh stack push overwrites a stack layer whose remote is
ahead](../bugs/gh-stack-push-overwrites-remote-layer.md)

[Image rebuild lost when a later push to main cancels its
run](../bugs/main-image-rebuild-lost-on-cancel.md)

[HTTPS git push hangs on Coder's askpass when gh's login is only a session
token](../bugs/coder-askpass-push-hang.md)

[Codex never loads the agentdev catalog
agents](../bugs/codex-catalog-agents-not-loaded.md)

[Codex leaves ${CLAUDE_SKILL_DIR} unresolved in agentdev
skills](../bugs/codex-skill-dir-unresolved.md)

[Fixture git inherits the outer commit's
index](../bugs/fixture-git-inherits-commit-index.md)

[The review orchestrator ends its turn while its passes are still
running](../bugs/review-orchestrator-ends-turn-while-passes-run.md)

[Coder workspace Dev Container is lost on
restart](../bugs/coder-devcontainer-lost-on-restart.md)

[Ship's release-link rule is undefined for a plan with no feature or
bug](../bugs/ship-release-link-without-feature.md)

[Bug: the Remote Control pin ignores
`/clear`](../bugs/remote-control-pin-ignores-clear.md)

[Bug: a comment-requested review's gate does not count toward
merge](../bugs/dispatched-review-gate-not-counted.md)

[Bug: PR updates skip the re-review
evaluation](../bugs/pr-update-skips-review-eval.md)

[Bug: a client is recovered on its own budget before its dependency's failure is
confirmed](../bugs/supervisor-client-recovered-before-dependency.md)

[Bug: git-new-branch worktree mode fails on a standalone deployment's root-owned
/workspaces](../bugs/git-new-branch-worktree-unwritable-workspaces.md)
