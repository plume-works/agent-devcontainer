# `.codex/` — Codex repository configuration

The shared agent catalog lives entirely in [`.agents/plugins/agentdev/`](../.agents/plugins/agentdev/) and is
packaged for Codex by
[`.agents/plugins/agentdev/.codex-plugin/plugin.json`](../.agents/plugins/agentdev/.codex-plugin/plugin.json).
Codex discovers the canonical `.agents/plugins/agentdev/agents/` and `.agents/plugins/agentdev/skills/` files
directly, so this directory no longer contains generated trampolines or a
skills symlink.

| Path                   | Nature                                                                                                                         |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `setup-codex-cloud.sh` | Codex Cloud bootstrap: provisions the same tools and capabilities as the agent-desktop image, then checks `gh` authentication. |
