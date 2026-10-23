#!/usr/bin/env bash
set -euo pipefail

# Ask the running CBM daemon to index the workspace in the background, and return as
# soon as it accepts the job. Startup never waits for the index. Spec: cbm-startup-integration.

cbm="${AGENTDEV_CBM_BIN:-codebase-memory-mcp}"
if ! command -v "$cbm" &>/dev/null; then
  echo "codebase-memory-mcp is not installed; skipping agent config wiring."
  exit 0
fi

if [[ -z ${CBM_CACHE_DIR:-} ]]; then
  echo "CBM_CACHE_DIR is required for codebase-memory-mcp install; it is not set in this container." >&2
  exit 1
fi

repo="${DEV_WORKSPACE_FOLDER:?DEV_WORKSPACE_FOLDER must name the workspace to index}"
status=0
output="$("$cbm" cli --json index_repository --repo-path "$repo" --async true)" || status=$?
if ((status != 0)); then
  echo "codebase-memory-mcp index request for $repo exited $status: ${output:0:500}" >&2
  exit 1
fi
# Accepted means queued, running, or joined to a job already in flight.
if ! state="$(jq -er '
    select(.isError != true) | .structuredContent
    | select(.joined == true or (.state | IN("queued", "running", "succeeded"))) | .state
  ' <<<"$output" 2>/dev/null)"; then
  echo "codebase-memory-mcp did not accept the index request for $repo: ${output:0:500}" >&2
  exit 1
fi
echo "codebase-memory-mcp: indexing $repo in the background ($state)"
