#!/usr/bin/env bash
set -euo pipefail

# Root bootstrap: deploy creates or reuses the runtime account, then validates and initializes
# only its own storage; a Dev Container keeps the tool's account and mounts. Ownership is never
# rewritten recursively. Spec: standalone-opencode-runtime, agentdev-runtime-images.

runtime_user="${AGENTDEV_USER:-agent}"
runtime_uid="${AGENTDEV_UID:-1000}"
runtime_gid="${AGENTDEV_GID:-1000}"
runtime_home="${AGENTDEV_HOME:-/home/$runtime_user}"
workspace="${DEV_WORKSPACE_FOLDER:-/workspaces/project}"
uv_dir="${AGENTDEV_UV_DIR:-/uv}"
docker_dir="${AGENTDEV_DOCKER_DATA_DIR:-/var/lib/docker}"
auth_dir="${AGENTDEV_AGENTS_AUTH_DIR:-/var/lib/agentdev/auth}"
runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$runtime_uid}"
sudoers_file="${AGENTDEV_SUDOERS_FILE:-/etc/sudoers.d/agentdev-runtime}"
lock_timeout="${AGENTDEV_AUTH_LOCK_TIMEOUT:-60}"
lifecycle_dir="${AGENTDEV_LIFECYCLE_DIR:-/var/lib/agentdev/lifecycle}"
runtime_root="${AGENTDEV_RUNTIME_ROOT:-/opt/agentdev-runtime}"
runtime_manifest="${AGENTDEV_RUNTIME_MANIFEST:-/etc/agentdev/runtime.sha256}"

fail() {
  echo "runtime-bootstrap: $*" >&2
  exit 1
}

log() { echo "runtime-bootstrap: $*"; }

validate_id() {
  local name="$1" value="$2"
  [[ $value =~ ^[0-9]+$ ]] || fail "$name must be a numeric ID, got '$value'"
  ((10#$value >= 1 && 10#$value <= 2147483647)) ||
    fail "$name must be between 1 and 2147483647; root (0) is not a runtime identity"
}

owner_of() { stat -c '%u:%g' "$1"; }

is_empty_dir() { [[ -d $1 && -z $(find "$1" -mindepth 1 -maxdepth 1 -print -quit) ]]; }

as_runtime_user() {
  setpriv --reuid="$runtime_uid" --regid="$runtime_gid" --init-groups -- "$@"
}

ensure_group() {
  local existing
  if existing="$(getent group "$runtime_gid")"; then
    log "reusing group ${existing%%:*} ($runtime_gid) as the primary group"
    return
  fi
  if getent group "$runtime_user" >/dev/null; then
    fail "group $runtime_user exists with another GID; it cannot become GID $runtime_gid"
  fi
  groupadd --gid "$runtime_gid" "$runtime_user"
}

ensure_account() {
  local by_uid by_name
  by_uid="$(getent passwd "$runtime_uid" || true)"
  by_name="$(getent passwd "$runtime_user" || true)"
  if [[ -n $by_uid && ${by_uid%%:*} != "$runtime_user" ]]; then
    fail "UID $runtime_uid already belongs to account ${by_uid%%:*}; choose another AGENTDEV_UID"
  fi
  if [[ -n $by_name ]]; then
    IFS=: read -r _ _ uid gid _ home _ <<<"$by_name"
    [[ $uid == "$runtime_uid" && $gid == "$runtime_gid" && $home == "$runtime_home" ]] ||
      fail "account $runtime_user exists as $uid:$gid home $home, not $runtime_uid:$runtime_gid home $runtime_home; recreate the container"
    log "reusing account $runtime_user ($runtime_uid:$runtime_gid)"
  else
    useradd --no-create-home --uid "$runtime_uid" --gid "$runtime_gid" \
      --home-dir "$runtime_home" --shell /bin/bash "$runtime_user"
    log "created account $runtime_user ($runtime_uid:$runtime_gid)"
  fi
  if getent group docker >/dev/null; then
    usermod --append --groups docker "$runtime_user"
  fi
}

ensure_sudo() {
  local staged="$sudoers_file.new"
  mkdir -p "$(dirname "$sudoers_file")"
  printf '%s ALL=(ALL:ALL) NOPASSWD: ALL\n' "$runtime_user" >"$staged"
  chmod 0440 "$staged"
  visudo -cqf "$staged" || fail "generated sudoers entry failed validation"
  mv -f "$staged" "$sudoers_file"
}

require_mount() {
  [[ ${AGENTDEV_REQUIRE_MOUNTS:-1} == 1 ]] || return 0
  mountpoint -q "$1" ||
    fail "$1 is not a mounted volume; its $2 would be lost when the container is replaced"
}

# Instance storage: an empty root-owned mount becomes the runtime user's; a
# populated one must already be. Only the mount root is ever chowned.
claim_instance_dir() {
  local path="$1" purpose="$2"
  require_mount "$path" "$purpose"
  [[ -d $path ]] || fail "$path ($purpose) is missing"
  local owner
  owner="$(owner_of "$path")"
  if [[ $owner == "$runtime_uid:$runtime_gid" ]]; then
    return
  fi
  if is_empty_dir "$path"; then
    chown "$runtime_uid:$runtime_gid" "$path"
    log "initialized empty $purpose at $path"
    return
  fi
  fail "$path ($purpose) is owned by $owner, not $runtime_uid:$runtime_gid; it belongs to another identity"
}

validate_workspace() {
  require_mount "$workspace" "checkout"
  [[ -d $workspace ]] || fail "workspace $workspace is missing; mount a checkout or a volume there"
  if is_empty_dir "$workspace" && [[ $(owner_of "$workspace") != "$runtime_uid:$runtime_gid" ]]; then
    chown "$runtime_uid:$runtime_gid" "$workspace"
    log "initialized empty workspace at $workspace"
  fi
  as_runtime_user test -w "$workspace" ||
    fail "workspace $workspace is not writable by $runtime_uid:$runtime_gid; match AGENTDEV_UID/AGENTDEV_GID to the checkout owner"
}

# Containers sharing one credential volume serialize here; only the first, on an
# empty volume, writes anything.
prepare_shared_auth() {
  require_mount "$auth_dir" "shared agent credentials"
  [[ -d $auth_dir ]] || fail "shared auth directory $auth_dir is missing"
  exec {lock_fd}<"$auth_dir"
  flock --wait "$lock_timeout" "$lock_fd" || fail "timed out waiting for the lock on $auth_dir"
  if is_empty_dir "$auth_dir"; then
    local agent
    chown "$runtime_uid:$runtime_gid" "$auth_dir"
    chmod 700 "$auth_dir"
    for agent in claude codex opencode; do
      as_runtime_user install -d -m 700 "$auth_dir/$agent"
    done
    log "initialized empty shared auth volume at $auth_dir"
  else
    local entry owner
    for entry in "$auth_dir" "$auth_dir"/* "$auth_dir"/.[!.]*; do
      [[ -e $entry || -L $entry ]] || continue
      owner="$(stat -c '%u' "$entry")"
      [[ $owner == "$runtime_uid" ]] ||
        fail "shared auth entry $entry is owned by UID $owner; containers sharing $auth_dir must all use AGENTDEV_UID=$owner"
    done
  fi
  exec {lock_fd}<&-
}

reset_runtime_dir() {
  rm -rf "$runtime_dir"
  install -d -m 700 -o "$runtime_uid" -g "$runtime_gid" "$runtime_dir"
}

bootstrap_deploy() {
  validate_id AGENTDEV_UID "$runtime_uid"
  validate_id AGENTDEV_GID "$runtime_gid"
  runtime_uid=$((10#$runtime_uid))
  runtime_gid=$((10#$runtime_gid))

  ensure_group
  ensure_account
  ensure_sudo
  claim_instance_dir "$runtime_home" "home and client configuration"
  claim_instance_dir "$uv_dir" "uv cache and environments"
  require_mount "$docker_dir" "nested Docker storage"
  validate_workspace
  prepare_shared_auth
  reset_runtime_dir
  log "identity $runtime_user ($runtime_uid:$runtime_gid) ready"
}

# The image records its runtime root at build time; a derived image that replaced, added, or
# removed a file there would run lifecycle code nobody tested. Spec: agentdev-runtime-images.
verify_runtime_root() {
  [[ -f $runtime_manifest ]] || return 0
  local recorded actual
  if ! (cd "$runtime_root" && sha256sum --check --quiet --strict "$runtime_manifest" >/dev/null 2>&1); then
    fail "a file below $runtime_root differs from the image's; extend the runtime through /etc/agentdev/hooks and documented environment instead"
  fi
  recorded="$(awk '{print $2}' "$runtime_manifest" | sed 's#^\*##' | LC_ALL=C sort)"
  actual="$(cd "$runtime_root" && find . -type f -not -path '*/__pycache__/*' | LC_ALL=C sort)"
  [[ $recorded == "$actual" ]] ||
    fail "files were added to or removed from $runtime_root; extend the runtime through /etc/agentdev/hooks and documented environment instead"
}

# The Dev Container tool owns the account, mounts, and checkout; the create lifecycle
# prepares client state. Only the directories the runtime itself owns are set up here.
bootstrap_devcontainer() {
  local entry
  entry="$(getent passwd "$runtime_user")" ||
    fail "account $runtime_user does not exist; AGENTDEV_USER must name an account in the image"
  IFS=: read -r _ _ runtime_uid runtime_gid _ _ _ <<<"$entry"
  runtime_dir="${XDG_RUNTIME_DIR:-/run/user/$runtime_uid}"
  if ((runtime_uid != 0)) && getent group docker >/dev/null; then
    usermod --append --groups docker "$runtime_user"
  fi
  # Container storage: it survives a restart and is gone after a rebuild, like the create phase.
  install -d -m 0755 -o "$runtime_uid" -g "$runtime_gid" "$lifecycle_dir"
  reset_runtime_dir
  log "accepted account $runtime_user ($runtime_uid:$runtime_gid) and workspace $workspace as mounted"
}

verify_runtime_root
case "${AGENTDEV_RUNTIME_MODE:-}" in
  deploy) bootstrap_deploy ;;
  devcontainer) bootstrap_devcontainer ;;
  *) fail "AGENTDEV_RUNTIME_MODE must be deploy or devcontainer; got '${AGENTDEV_RUNTIME_MODE:-}'" ;;
esac
# Last, and before supervisord starts dockerd: see runtime-firewall.sh.
"$(dirname "${BASH_SOURCE[0]}")/runtime-firewall.sh"
