---
type: hub
description: System design notes and the reasoning behind them, rejected alternatives included.
stage: living
generated:
  by: claude-code/opus-5.5
  at: 2026-10-31T21:18:50Z
---

# 🏛️ Architecture

*System design notes — data structures, module boundaries, pipelines, and the
reasoning behind them, one topic per document in `architecture/<slug>.md`.
Frontmatter is `type: architecture`; like specs, these are durable reference.
Record a design decision here the moment it's made — the alternatives you
rejected are as valuable as the one you picked.*

[Actions approval permission](architecture/actions-approval-permission.md)

[Agent auth persistence](architecture/agent-auth-persistence.md)

[Agent metadata files](architecture/agent-metadata-files.md)

[agentdev runtime package](architecture/agentdev-runtime-package.md)

[AI review event selection](architecture/ai-review-event-selection.md)

[Ansible apt pins](architecture/ansible-apt-pins.md)

[Assignee-triggered AI re-reviews](architecture/assignee-review-trigger.md)

[Autonomous Implement loop](architecture/autonomous-implement-loop.md)

[Catalog script language](architecture/catalog-script-language.md)

[CBM daemon lifecycle](architecture/cbm-daemon-lifecycle.md)

[CI agent plugin availability](architecture/ci-agent-plugin-availability.md)

[Claude Remote Control archived pre-created
session](architecture/claude-remote-control-archived-pre-created-session.md)

[Claude Remote Control expired session
recovery](architecture/claude-remote-control-expired-session-recovery.md)

[Claude Remote Control pointerless server
start](architecture/claude-remote-control-pointerless-server-start.md)

[Claude Remote Control resume](architecture/claude-remote-control-resume.md)

[Claude Remote Control server
--continue](architecture/claude-remote-control-server-continue.md)

[Claude Remote Control server
mode](architecture/claude-remote-control-server-mode.md)

[Claude Remote Control server restart
resume](architecture/claude-remote-control-server-restart-resume.md)

[Claude Remote Control spawn mode
switch](architecture/claude-remote-control-spawn-mode-switch.md)

[Claude Remote Control worktree restart
resume](architecture/claude-remote-control-worktree-restart-resume.md)

[Dev Container home volume](architecture/devcontainer-home-volume.md)

[Dev Container runtime](architecture/devcontainer-runtime.md)

[Dispatched review identity](architecture/dispatched-review-identity.md)

[Dr.QP devcontainer testing](architecture/drqp-devcontainer-testing.md)

[Explicit-only workflow agents](architecture/explicit-only-workflow-agents.md)

[Fork pull request builds](architecture/fork-pull-request-builds.md)

[Formatter ownership](architecture/formatter-ownership.md)

[Fresh-context Verify](architecture/fresh-context-verify.md)

[gh authentication shim](architecture/gh-authentication-shim.md)

[IWE through the CLI, not MCP](architecture/iwe-cli-over-mcp.md)

[Conflict-free knowledge layout](architecture/kb-conflict-free-layout.md)

[MCP gateway transport](architecture/mcp-gateway-transport.md)

[Module layout](architecture/module-layout.md)

[Nested Docker provisioning](architecture/nested-docker-provisioning.md)

[Nested subagent dispatch](architecture/nested-subagent-dispatch.md)

[OpenCode catalog bridge](architecture/opencode-catalog-bridge.md)

[OpenCode full access in the
devcontainer](architecture/opencode-full-access-in-devcontainer.md)

[PR review correctness bar](architecture/pr-review-correctness-bar.md)

[PR review effort tiers](architecture/pr-review-effort-tiers.md)

[PR review scenario validation](architecture/pr-review-scenario-validation.md)

[PR verification sections](architecture/pr-verification-sections.md)

[Renovate config validation](architecture/renovate-config-validation.md)

[Renovate post-upgrade task](architecture/renovate-post-upgrade.md)

[Holding the AI review gate during a
re-review](architecture/rereview-gate-pending.md)

[Self-improve consolidation](architecture/self-improve-consolidation.md)

[Self-improve runtime](architecture/self-improve-runtime.md)

[Testing sibling workspaces in
devcontainers](architecture/sibling-devcontainer-testing.md)

[Stack push guard](architecture/stack-push-guard.md)

[Stacked pull requests](architecture/stacked-prs.md)

[Standalone OpenCode runtime](architecture/standalone-opencode-runtime.md)

[Supported harnesses](architecture/supported-harnesses.md)

[Template boundary](architecture/template-boundary.md)

[uv environment location](architecture/uv-environment-location.md)

[Validator image install](architecture/validator-image-install.md)
