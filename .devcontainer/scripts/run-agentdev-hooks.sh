#!/usr/bin/env bash
set -euo pipefail

# Runs the executable hooks an image installed for one lifecycle phase, in C-locale name
# order, after the managed phase. Only the image's hook root is read; a mounted workspace
# never contributes hooks. Spec: agentdev-runtime-images.
# Usage: run-agentdev-hooks.sh created|started|attached

phase="${1:-}"
hooks_root="${AGENTDEV_HOOKS_ROOT:-/etc/agentdev/hooks}"
workspace="${DEV_WORKSPACE_FOLDER:-}"

fail() {
  echo "run-agentdev-hooks: $*" >&2
  exit 1
}

case "$phase" in
  created | started | attached) ;;
  *)
    echo "usage: $(basename "$0") created|started|attached" >&2
    exit 2
    ;;
esac

hooks_dir="$hooks_root/$phase.d"
[[ -d $hooks_dir ]] || exit 0
if [[ -n $workspace ]]; then
  resolved="$(realpath -m "$hooks_dir")"
  checkout="$(realpath -m "$workspace")"
  [[ $resolved != "$checkout" && $resolved != "$checkout"/* ]] ||
    fail "hook directory $hooks_dir is inside the workspace $workspace; hooks come from the image"
fi

mapfile -t hooks < <(LC_ALL=C find "$hooks_dir" -mindepth 1 -maxdepth 1 -print | LC_ALL=C sort)
for hook in "${hooks[@]}"; do
  name="$(basename "$hook")"
  if [[ ! -f $hook || ! -x $hook ]]; then
    echo "run-agentdev-hooks: skipping $name in the $phase phase: not an executable file"
    continue
  fi
  echo "run-agentdev-hooks: running $name in the $phase phase"
  status=0
  AGENTDEV_LIFECYCLE_PHASE="$phase" "$hook" || status=$?
  ((status == 0)) || fail "hook $name failed in the $phase phase (exit status $status)"
done
