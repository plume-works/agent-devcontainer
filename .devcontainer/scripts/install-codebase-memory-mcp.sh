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

codebase-memory-mcp install -y --force
