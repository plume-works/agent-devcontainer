#!/usr/bin/env bash
# Sourced. Agent-state path roots shared by the devcontainer hooks and the deploy
# runtime: the defaults are the devcontainer's root layout, the deploy image overrides each.

# shellcheck disable=SC2034  # consumed by the scripts that source this file.
agentdev_auth_dir="${AGENTDEV_AGENTS_AUTH_DIR:-/root/.agents-auth}"
# shellcheck disable=SC2034
agentdev_claude_dir="${AGENTDEV_CLAUDE_DIR:-/root/.claude}"
# shellcheck disable=SC2034
agentdev_claude_json="${AGENTDEV_CLAUDE_JSON:-/root/.claude.json}"
# shellcheck disable=SC2034
agentdev_codex_home="${CODEX_HOME:-/root/.codex}"
# shellcheck disable=SC2034
agentdev_opencode_data="${XDG_DATA_HOME:-$HOME/.local/share}/opencode"

agentdev_deploy() {
  [[ ${AGENTDEV_RUNTIME_MODE:-devcontainer} == deploy ]]
}

# A checkout's own catalog replaces the staged one only when all three clients' manifests ship.
# Spec: catalog-lifecycle.
agentdev_complete_catalog() {
  [[ -f $1/.claude-plugin/marketplace.json &&
    -f $1/.agents/plugins/marketplace.json &&
    -d $1/.agents/plugins/agentdev/.opencode-plugin ]]
}
