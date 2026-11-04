#!/usr/bin/env bash
# Writes the labels output: $LABELS, minus the per-run labels when $STABLE_LABELS is true.
set -euo pipefail

labels="${LABELS:-}"
if [ "${STABLE_LABELS:-false}" = "true" ]; then
  labels="$(grep -vE '^org\.opencontainers\.image\.(created|revision|version)=' <<<"$labels" || true)"
fi
delimiter="labels_$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')"
{
  echo "labels<<${delimiter}"
  printf '%s\n' "$labels"
  echo "${delimiter}"
} >>"${GITHUB_OUTPUT:?}"
