#!/usr/bin/env bash
set -euo pipefail

if [[ "${1:-}" != open* ]]; then
  echo "rejected: expected open-sesame" >&2
  exit 1
fi
