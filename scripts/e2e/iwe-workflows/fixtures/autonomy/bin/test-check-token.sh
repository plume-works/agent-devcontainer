#!/usr/bin/env bash
set -euo pipefail

here="$(dirname -- "${BASH_SOURCE[0]}")"
"${here}/check-token.sh" open-sesame
if "${here}/check-token.sh" ''; then
  echo 'empty argument accepted' >&2
  exit 1
fi
echo 'ok'
