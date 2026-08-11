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

cbm_cache_dir="${CBM_CACHE_DIR:-$HOME/.cache/codebase-memory-mcp}"
cbm_bin_path="$(command -v codebase-memory-mcp)"
cbm_install_dir="${CBM_INSTALL_DIR:-$HOME/.local/bin}"

echo "codebase-memory-mcp install: user=$(id -un) home=$HOME cache_dir=$cbm_cache_dir binary=$cbm_bin_path"
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

install_status=0
CBM_LOG_LEVEL="${CBM_LOG_LEVEL:-debug}" codebase-memory-mcp install -y --force || install_status=$?

if ((install_status != 0)); then
  echo "codebase-memory-mcp install failed with exit code $install_status" >&2

  activation_log="$cbm_cache_dir/logs/activation-events.ndjson"
  if [[ -f "$activation_log" ]]; then
    echo "--- tail of $activation_log ---" >&2
    tail -n 50 "$activation_log" >&2
  else
    echo "no activation log found at $activation_log" >&2
  fi

  daemon_log="$cbm_cache_dir/logs/cbm-daemon.log"
  if [[ -f "$daemon_log" ]]; then
    echo "--- tail of $daemon_log ---" >&2
    tail -n 50 "$daemon_log" >&2
  else
    echo "no daemon log found at $daemon_log" >&2
  fi

  conflicts_log="$cbm_cache_dir/logs/daemon-conflicts.ndjson"
  if [[ -f "$conflicts_log" ]]; then
    echo "--- tail of $conflicts_log ---" >&2
    tail -n 50 "$conflicts_log" >&2
  fi

  exit "$install_status"
fi
