#!/usr/bin/env bash
set -euo pipefail

# Create phase (postCreateCommand), idempotent: client state, project dependencies and
# hooks, the staged catalog, then the created hooks. `wait` blocks until one has finished.
# Spec: agentdev-runtime-images, catalog-lifecycle. Usage: devcontainer-created.sh [wait]

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace="${DEV_WORKSPACE_FOLDER:-$PWD}"
export DEV_WORKSPACE_FOLDER="$workspace"
# Container storage, made by the bootstrap: gone after a rebuild, kept across a restart.
marker="${AGENTDEV_LIFECYCLE_DIR:-/var/lib/agentdev/lifecycle}/created"

# CBM rejects a workspace or home whose ancestors another UID owns, as in a GitHub Actions
# container job. Ancestors only: the checkout's contents are never touched.
claim_ancestors() {
  local owner="$1" dir="$2"
  while [[ -n $dir && $dir != / ]]; do
    sudo chown "$owner" "$dir"
    dir="$(dirname "$dir")"
  done
}

# Named volumes are created root-owned; claim /uv only when it is mounted.
claim_mounts() {
  local owner="$1" mount_point=/uv
  if [[ -e $mount_point ]]; then
    sudo chown -R "$owner" "$mount_point"
  else
    echo "$mount_point is not mounted; skipping its ownership fix."
  fi
}

cmd_create() {
  local owner
  owner="$(id -u):$(id -g)"
  if [[ $(id -u) == 0 ]]; then
    claim_ancestors "$owner" "$workspace"
    claim_ancestors "$owner" "$HOME"
  fi
  claim_mounts "$owner"
  # Before the project's hooks: pre-commit refuses a checkout another UID owns until trusted.
  agentdev-runtime git safe-directory
  # Links ~/.claude.json, wires CBM into each client, and creates the shared auth directories.
  agentdev-runtime state create
  agentdev-runtime workspace project
  # The client-state volumes shadow the build-time install, so install the staged catalog
  # again at user scope; the attach phase layers a complete checkout catalog on top.
  if [[ -n ${AGENTDEV_CATALOG_DIR:-} && -d $AGENTDEV_CATALOG_DIR ]]; then
    agentdev-runtime catalog install "$AGENTDEV_CATALOG_DIR" --claude-scope user
  else
    echo "No catalog staged in the image; skipping the image-scoped plugin install."
  fi
  "$script_dir/run-agentdev-hooks.sh" created
  mkdir -p "$(dirname "$marker")"
  touch "$marker"
}

cmd_wait() {
  until [[ -f $marker ]]; do
    sleep 1
  done
}

case "${1:-}" in
  '') cmd_create ;;
  wait) cmd_wait ;;
  *)
    echo "usage: $(basename "$0") [wait]" >&2
    exit 2
    ;;
esac
