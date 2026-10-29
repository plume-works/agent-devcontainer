#!/usr/bin/env bash
set -euo pipefail

# Prints the dev container's hostname, which Claude Remote Control registers as its
# environment name. Spec: claude-remote-control. Usage: container-hostname.sh <checkout-dir>

checkout="${1:?usage: container-hostname.sh <checkout-dir>}"
stem="$(basename "$checkout")"
host="${HOSTNAME:-$(hostname)}"
host="${host%%.*}"

if [[ -n "${CODER_WORKSPACE_NAME:-}" ]]; then
  name="coder-$CODER_WORKSPACE_NAME"
elif [[ -n "${VSCODE_PID:-}" || -n "${VSCODE_IPC_HOOK:-}" ]]; then
  name="vscode-$host-$stem"
else
  name="cli-$host-$stem"
fi

# An RFC 1123 label: lowercase alphanumerics and inner hyphens, at most 63 characters.
name="$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-')"
name="${name#-}"
name="${name:0:63}"
printf '%s\n' "${name%-}"
