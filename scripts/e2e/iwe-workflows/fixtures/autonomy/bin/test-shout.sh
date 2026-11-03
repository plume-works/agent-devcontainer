#!/usr/bin/env bash
set -euo pipefail

script="$(dirname -- "${BASH_SOURCE[0]}")/shout.sh"
grep -qF "tr '[:lower:]' '[:upper:]'" "${script}"
echo 'ok'
