#!/usr/bin/env bash
set -euo pipefail

# Wire the codebase-memory-mcp binary (installed system-wide by the dev_tools
# Ansible role at image-build time) into the current user's agent config.
#
# This has to run here rather than during the image build: `install` writes
# MCP entries into ~/.claude.json and ~/.codex, and the persistent
# ~/.claude/~/.codex volumes mount over anything written at build time — the
# same reason reinstall-agentdev-claude.sh/reinstall-agentdev-codex.sh run
# their plugin registration from here instead of from Ansible.
#
# `install -y --force` is idempotent: it re-verifies the already-installed
# binary and re-applies agent config, so re-running this on every container
# start is safe.

if ! command -v codebase-memory-mcp &>/dev/null; then
  echo "codebase-memory-mcp is not installed; skipping agent config wiring."
  exit 0
fi

if [[ -z $CBM_CACHE_DIR ]]; then
  echo "CBM_CACHE_DIR is required for codebase-memory-mcp install; it is not set in this container." >&2
  exit 1
fi

# CBM's activation opens the cache directory through a "private directory" walk
# that rejects a component it does not consider exclusively owned, and reports
# `ancestry component validation failed (errno 17)` when the directory already
# exists with a mode it will not accept. On a fresh `agentdev-cache` volume the
# leaf is created under this container's umask (0022 -> 0755), whereas a working
# tree has it at 0700 — so pre-create it at 0700 before the installer sees it.
#
# Only the leaf is forced: the parent `.cache` mount point is 0755 in a known
# working container, so the check does not extend up the whole ancestry.
stat -c 'cache preflight: %n mode=%a owner=%U:%G' \
  "$CBM_CACHE_DIR" "$(dirname "$CBM_CACHE_DIR")" 2>&1 || true
mkdir -p "$CBM_CACHE_DIR"
chmod 700 "$CBM_CACHE_DIR"

cbm_bin_path="$(command -v codebase-memory-mcp)"
cbm_install_dir="${CBM_INSTALL_DIR:-$HOME/.local/bin}"

echo "codebase-memory-mcp install: user=$(id -un) home=$HOME cache_dir=$CBM_CACHE_DIR binary=$cbm_bin_path"
echo "umask=$(umask)"

# The activation-transaction staging step refuses a candidate/target that
# looks tampered with: group/other-writable mode bits, unexpected hard links,
# or unexpected ACLs (see upstream issue #1483, which traces the same "I/O
# failed" message to umask 002 producing group-writable staged files). Log the
# mode/owner/link-count of everything the transaction touches so a failure
# here is diagnosable from CI output alone, without needing to reproduce it.
for path in "$cbm_bin_path" "$(dirname "$cbm_bin_path")" "$cbm_install_dir" "$HOME"; do
  if [[ -e "$path" ]]; then
    stat -c 'preflight stat: %n mode=%a owner=%U:%G links=%h' "$path" 2>&1 || true
  else
    echo "preflight stat: $path does not exist"
  fi
done

# postCreateCommand.sh symlinks ~/.claude.json into the persistent ~/.claude
# volume (Docker volumes are directory-backed, so the file cannot be mounted
# directly). The installer's MCP write refuses to operate on that symlink and
# fails with `op=mcp_install path=$HOME/.claude.json`, which aborts the whole
# activation. Materialize the symlink target as a real file for the duration of
# the install, then fold the result back into the volume and relink — so the
# installed MCP entry persists across container restarts either way.
claude_json="$HOME/.claude.json"
claude_json_link_target=""
if [[ -L "$claude_json" ]]; then
  claude_json_link_target="$(readlink -f "$claude_json")"
  echo "temporarily materializing $claude_json (symlink -> $claude_json_link_target) for the install"
  rm "$claude_json"
  cp -a "$claude_json_link_target" "$claude_json"
fi

# shellcheck disable=SC2317  # reached via the EXIT trap below, not inline.
restore_claude_json_symlink() {
  [[ -n "$claude_json_link_target" ]] || return 0
  if [[ -f "$claude_json" && ! -L "$claude_json" ]]; then
    cp -a "$claude_json" "$claude_json_link_target"
    rm -f "$claude_json"
  fi
  ln -sf "$claude_json_link_target" "$claude_json"
  echo "restored $claude_json -> $claude_json_link_target"
}
# Restore on any exit path, so an installer crash cannot leave the symlink off
# and strand later config writes outside the persistent volume.
trap restore_claude_json_symlink EXIT

install_status=0

codebase-memory-mcp daemon status || true  # log any existing daemon status, but don't fail the install if it's not running
codebase-memory-mcp daemon stop || true  # stop any existing daemon so the install can run without conflicting with it

mapfile -t zombie_pids < <(pgrep codebase-me || true)
if [[ ${#zombie_pids[@]} -gt 0 ]]; then
  echo "found ${#zombie_pids[@]} zombie codebase-memory-mcp process(es) with PID(s): ${zombie_pids[*]}"
  ps -fp "${zombie_pids[@]}"
fi

CBM_LOG_LEVEL="${CBM_LOG_LEVEL:-debug}" codebase-memory-mcp install -y --force || install_status=$?

mapfile -t zombie_pids < <(pgrep codebase-me || true)
if [[ ${#zombie_pids[@]} -gt 0 ]]; then
  echo "found ${#zombie_pids[@]} zombie codebase-memory-mcp process(es) with PID(s): ${zombie_pids[*]}"
  ps -fp "${zombie_pids[@]}"
fi

stat -c 'cache postinstall: %n mode=%a owner=%U:%G' "$CBM_CACHE_DIR" 2>&1 || true

if ((install_status != 0)); then
  echo "codebase-memory-mcp install failed with exit code $install_status" >&2

  # When the configured cache directory is itself what activation rejected,
  # nothing is written under it and every tail below reports "not found". CBM
  # falls back to the HOME-default tree in that case, so check both roots.
  for log_root in "$CBM_CACHE_DIR" "$HOME/.cache/codebase-memory-mcp"; do
    for log_name in activation-events.ndjson cbm-daemon.log daemon-conflicts.ndjson; do
      log_path="$log_root/logs/$log_name"
      if [[ -f "$log_path" ]]; then
        echo "--- tail of $log_path ---" >&2
        tail -n 50 "$log_path" >&2
      else
        echo "no log found at $log_path" >&2
      fi
    done
  done

  exit "$install_status"
fi
