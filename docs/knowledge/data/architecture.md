---
type: hub
description: System design notes and the reasoning behind them, rejected alternatives included.
stage: living
generated:
  by: opencode/openai-gpt-6.1-sol
  at: 2026-10-18T19:34:45Z
---

# 🏛️ Architecture

*System design notes — data structures, module boundaries, pipelines, and the
reasoning behind them, one topic per document in `architecture/<slug>.md`.
Frontmatter is `type: architecture`; like specs, these are durable reference.
Record a design decision here the moment it's made — the alternatives you
rejected are as valuable as the one you picked.*

[Module layout](architecture/module-layout.md)

[Template boundary](architecture/template-boundary.md)

[Agent metadata files](architecture/agent-metadata-files.md)

[Validator image install](architecture/validator-image-install.md)

[uv environment location](architecture/uv-environment-location.md)

[PR verification sections](architecture/pr-verification-sections.md)

[CI agent plugin availability](architecture/ci-agent-plugin-availability.md)

[AI review event selection](architecture/ai-review-event-selection.md)

[Dispatched review identity](architecture/dispatched-review-identity.md)

[Agent auth persistence](architecture/agent-auth-persistence.md)

[Nested Docker provisioning](architecture/nested-docker-provisioning.md)

[MCP gateway transport](architecture/mcp-gateway-transport.md)

[IWE through the CLI, not MCP](architecture/iwe-cli-over-mcp.md)

[Fork pull request builds](architecture/fork-pull-request-builds.md)

[gh authentication shim](architecture/gh-authentication-shim.md)

[Formatter ownership](architecture/formatter-ownership.md)

[Self-improve consolidation](architecture/self-improve-consolidation.md)

[Self-improve runtime](architecture/self-improve-runtime.md)

[PR review effort tiers](architecture/pr-review-effort-tiers.md)

[PR review correctness bar](architecture/pr-review-correctness-bar.md)

[PR review scenario validation](architecture/pr-review-scenario-validation.md)

[Headless Codex runs](architecture/codex-headless-runs.md)

[Codex full access in the
devcontainer](architecture/codex-full-access-in-devcontainer.md)

[OpenCode full access in the
devcontainer](architecture/opencode-full-access-in-devcontainer.md)

[Ansible apt pins](architecture/ansible-apt-pins.md)

[Renovate config validation](architecture/renovate-config-validation.md)

[Renovate post-upgrade task](architecture/renovate-post-upgrade.md)

[OpenCode catalog bridge](architecture/opencode-catalog-bridge.md)

[Stacked pull requests](architecture/stacked-prs.md)

[Stack push guard](architecture/stack-push-guard.md)

[Explicit-only workflow agents](architecture/explicit-only-workflow-agents.md)

[Claude Remote Control resume](architecture/claude-remote-control-resume.md)

[Claude Remote Control server
mode](architecture/claude-remote-control-server-mode.md)

[Claude Remote Control server restart
resume](architecture/claude-remote-control-server-restart-resume.md)

[Claude Remote Control server
--continue](architecture/claude-remote-control-server-continue.md)

[Claude Remote Control worktree restart
resume](architecture/claude-remote-control-worktree-restart-resume.md)

[Claude Remote Control spawn mode
switch](architecture/claude-remote-control-spawn-mode-switch.md)

[Claude Remote Control expired session
recovery](architecture/claude-remote-control-expired-session-recovery.md)

[Claude Remote Control archived pre-created
session](architecture/claude-remote-control-archived-pre-created-session.md)

[Claude Remote Control pointerless server
start](architecture/claude-remote-control-pointerless-server-start.md)

[CBM daemon lifecycle](architecture/cbm-daemon-lifecycle.md)

[Standalone OpenCode runtime](architecture/standalone-opencode-runtime.md)

[Dev Container runtime](architecture/devcontainer-runtime.md)

[Testing sibling workspaces in
devcontainers](architecture/sibling-devcontainer-testing.md)

[Dr.QP devcontainer testing](architecture/drqp-devcontainer-testing.md)

[Nested subagent dispatch](architecture/nested-subagent-dispatch.md)

[Fresh-context Verify](architecture/fresh-context-verify.md)

[Autonomous Implement loop](architecture/autonomous-implement-loop.md)

[Assignee-triggered AI re-reviews](architecture/assignee-review-trigger.md)

[Holding the AI review gate during a
re-review](architecture/rereview-gate-pending.md)
