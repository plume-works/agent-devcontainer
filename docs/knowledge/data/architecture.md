---
type: hub
description: System design notes and the reasoning behind them, rejected alternatives included.
stage: living
generated:
  by: codex/gpt-6
  at: 2026-10-04T21:58:34Z
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

[Fork pull request builds](architecture/fork-pull-request-builds.md)

[gh authentication shim](architecture/gh-authentication-shim.md)

[Formatter ownership](architecture/formatter-ownership.md)

[Self-improve consolidation](architecture/self-improve-consolidation.md)

[Self-improve runtime](architecture/self-improve-runtime.md)

[PR review effort tiers](architecture/pr-review-effort-tiers.md)

[PR review correctness bar](architecture/pr-review-correctness-bar.md)

[PR review scenario validation](architecture/pr-review-scenario-validation.md)

[Headless Codex runs](architecture/codex-headless-runs.md)

[Ansible apt pins](architecture/ansible-apt-pins.md)

[Renovate config validation](architecture/renovate-config-validation.md)

[Renovate post-upgrade task](architecture/renovate-post-upgrade.md)

[OpenCode catalog bridge](architecture/opencode-catalog-bridge.md)

[Stacked pull requests](architecture/stacked-prs.md)

[Explicit-only workflow agents](architecture/explicit-only-workflow-agents.md)
