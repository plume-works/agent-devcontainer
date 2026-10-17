#!/usr/bin/env bash
set -euo pipefail

# Standalone workspace preparation, run as the runtime user. A valid checkout is
# reused without contacting a remote; only an empty destination is cloned into.
# Usage: runtime-workspace.sh checkout|project|catalog|prepare. Spec: standalone-opencode-runtime.

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
workspace="${DEV_WORKSPACE_FOLDER:-/workspaces/project}"
state_dir="${AGENTDEV_STATE_DIR:-${XDG_STATE_HOME:-$HOME/.local/state}/agentdev}"
clone_marker="$state_dir/clone-in-progress"
export GIT_TERMINAL_PROMPT=0

fail() {
  echo "runtime-workspace: $*" >&2
  exit 1
}

log() { echo "runtime-workspace: $*"; }

# Strip any user:password@ from URLs so credentials never reach the log.
redact() { sed -E 's#(://)[^/@[:space:]]+@#\1***@#g'; }

is_empty_dir() { [[ -z $(find "$1" -mindepth 1 -maxdepth 1 -print -quit) ]]; }

validate_checkout() {
  local git_dir common_dir
  if ! git_dir="$(git -C "$workspace" rev-parse --absolute-git-dir 2>/dev/null)"; then
    if [[ -f $workspace/.git ]]; then
      fail "$workspace is a worktree whose Git metadata ($(sed -n 's/^gitdir: //p' "$workspace/.git")) is not available; mount the main repository's .git at that same path"
    fi
    fail "$workspace has a .git entry but is not a valid Git checkout; repair or empty it"
  fi
  common_dir="$(git -C "$workspace" rev-parse --path-format=absolute --git-common-dir)"
  [[ -d $common_dir/objects ]] ||
    fail "$workspace uses Git metadata at $common_dir, which is not mounted; mount it at that same path"
  log "reusing checkout $workspace (git dir $git_dir) without contacting its remotes"
}

clone_workspace() {
  local url="${AGENTDEV_REPOSITORY_URL:-}" ref="${AGENTDEV_REPOSITORY_REF:-}" status=0
  [[ -n $url ]] ||
    fail "$workspace is empty and AGENTDEV_REPOSITORY_URL is not set; mount a checkout or set a repository to clone"
  # HTTPS credentials come from the injected token through gh, set up before the clone.
  "$script_dir/setup-gh-credential-helper.sh"
  mkdir -p "$state_dir"
  touch "$clone_marker"
  log "cloning $(redact <<<"$url")${ref:+ at $ref} into $workspace"
  git clone ${ref:+--branch "$ref"} -- "$url" "$workspace" 2> >(redact >&2) || status=$?
  ((status == 0)) || fail "git clone failed with exit code $status"
  rm -f "$clone_marker"
}

cmd_checkout() {
  [[ -d $workspace ]] || fail "workspace $workspace does not exist"
  if [[ -f $clone_marker ]] && ! is_empty_dir "$workspace"; then
    fail "an earlier clone into $workspace was interrupted; empty that directory to retry (nothing was deleted)"
  fi
  rm -f "$clone_marker"
  # Before validation: Git refuses a checkout another UID owns until it is trusted.
  if [[ $(stat -c %u "$workspace") != "$(id -u)" ]]; then
    "$script_dir/setup-git-safe-directory.sh"
  fi
  if [[ -e $workspace/.git ]]; then
    validate_checkout
  elif is_empty_dir "$workspace"; then
    clone_workspace
  else
    fail "$workspace is not empty and is not a Git checkout; mount a checkout or an empty volume there"
  fi
}

cmd_project() {
  if [[ -f $workspace/pyproject.toml ]]; then
    "$script_dir/uv-sync.sh"
  else
    log "no pyproject.toml; skipping uv sync"
  fi
  if [[ -f $workspace/.pre-commit-config.yaml ]]; then
    "$script_dir/setup-pre-commit.sh"
  else
    log "no .pre-commit-config.yaml; skipping pre-commit hooks"
  fi
}

# The checkout's own catalog wins when it ships all three clients' manifests.
select_catalog() {
  if [[ -f $workspace/.claude-plugin/marketplace.json &&
    -f $workspace/.agents/plugins/marketplace.json &&
    -d $workspace/.agents/plugins/agentdev/.opencode-plugin ]]; then
    echo "$workspace"
  elif [[ -n ${AGENTDEV_CATALOG_DIR:-} && -d $AGENTDEV_CATALOG_DIR ]]; then
    echo "$AGENTDEV_CATALOG_DIR"
  else
    fail "no catalog: the checkout ships none and AGENTDEV_CATALOG_DIR is not a directory"
  fi
}

cmd_catalog() {
  local catalog
  catalog="$(select_catalog)"
  log "registering the agentdev catalog at $catalog for Claude, Codex, and OpenCode"
  "$script_dir/setup-agent-state.sh" catalog "$catalog" user
}

# The supervisor's one-shot preparation gate: checkout, agent state, catalog, project.
cmd_prepare() {
  # Nonfatal by design; see spec/devcontainer-docker-storage.
  "$script_dir/docker-image-prune.sh"
  cmd_checkout
  "$script_dir/setup-agent-state.sh" create
  "$script_dir/setup-agent-state.sh" codex-policy
  cmd_catalog
  cmd_project
}

case "${1:-}" in
  checkout) cmd_checkout ;;
  project) cmd_project ;;
  catalog) cmd_catalog ;;
  prepare) cmd_prepare ;;
  *)
    echo "usage: $(basename "$0") checkout|project|catalog|prepare" >&2
    exit 2
    ;;
esac
