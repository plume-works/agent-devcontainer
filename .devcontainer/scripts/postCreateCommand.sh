#!/usr/bin/env bash
set -exuo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace="${DEV_WORKSPACE_FOLDER:-$(cd "$script_dir/../.." && pwd)}"

chown_up() {
  local owner="$1"
  local loop_dir="$2"
  while [[ -n "$loop_dir" && "$loop_dir" != "/" ]]; do
    sudo chown "$owner" "$loop_dir"
    loop_dir="$(dirname "$loop_dir")"
  done
}

# Fix ownership of the workspace and its parent directories.
# This was originally needed for GitHub Actions where workspace is owned by 1001:1001
# which blows up the CBM internal checks of ownership of the cache directory and workspace
# Fix is placed next to other ownership fixes as it might be needed for other tools
#
# Ownership alone is what CBM's ancestry check rejects; the mode is not part of
# it. The run that first passed had every component still at 0755 and only the
# owner corrected.
#
# Do NOT add a chmod here. This loop walks up to /, and narrowing /workspaces
# to 0700 was tried: it strips traverse for every non-root user, so the
# postStartCommand died with `spawn docker EACCES`. Worse, the workspace is a
# bind mount of the runner's checkout, so the mode change propagates back to
# the host and the rest of the job fails to read its own files ("Can't find
# 'action.yml' ... under .github/actions/...").
chown_up "root:root" "$workspace"

# Named volumes are created root-owned by the daemon; make sure the container
# user owns the mount points it writes to.
sudo chown -R root:root \
    "$workspace/.cache" \
    /uv

# Wire the codebase-memory-mcp binary staged by dev_tools into this user's
# agent config now that the real ~/.claude and ~/.codex volumes are mounted.
# This script has to run before symlinking ~/.claude.json
"$script_dir/codebase-memory-mcp-install.sh"

# Both agents' credential setup below needs their subdirectory of the shared
# agentdev-agents-auth volume to exist first.
mkdir -p /root/.agents-auth/claude /root/.agents-auth/codex
chmod 700 /root/.agents-auth/claude /root/.agents-auth/codex

# ~/.claude.json can't be backed directly by a named volume (Docker volumes are always
# directory-backed, so mounting one at a file path materializes an empty directory
# there instead of the file Claude Code expects). Persist it as a plain file inside the
# already-mounted agentdev-claude volume and symlink it into place instead.
claude_json_target="/root/.claude/claude.json"
if [[ -f /root/.claude.json && ! -L /root/.claude.json ]]; then
    mv /root/.claude.json "$claude_json_target"
elif [[ ! -e "$claude_json_target" ]]; then
    echo '{}' >"$claude_json_target"
fi
ln -sf "$claude_json_target" /root/.claude.json

# See link-codex-auth.sh for why Codex's auth.json needs the same file-in-a-shared-
# volume-plus-symlink treatment, and why this also has to run again from
# postStartCommand.sh.
"$script_dir/link-codex-auth.sh"

# Sync the project environment into the container's .venv directory so that
# extension settings are valid when the container is rebuilt. This is a no-op if the environment is already up to date.
"$script_dir/uv-sync.sh"

# Install the catalog staged in the image. This has to happen here rather than
# during the image build: the persistent ~/.claude and ~/.codex volumes mount over
# where both agents record installed plugins, so a build-time install would be
# shadowed for every container whose volume already exists. At user scope for
# Claude, so it applies to every workspace opened in this container;
# postAttachCommand re-registers this checkout on top when there is one.
if [[ -n "${AGENTDEV_CATALOG_DIR:-}" && -d "$AGENTDEV_CATALOG_DIR" ]]; then
    "$script_dir/reinstall-agentdev-codex.sh" "$AGENTDEV_CATALOG_DIR"
    "$script_dir/reinstall-agentdev-claude.sh" "$AGENTDEV_CATALOG_DIR" user
else
    echo "No catalog staged in the image; skipping the image-scoped plugin install."
fi
