#!/usr/bin/env bash
set -euo pipefail

printf '%s\n' "${1:-}" | tr '[:lower:]' '[:upper:]'
