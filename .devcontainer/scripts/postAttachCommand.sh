#!/usr/bin/env bash
# Attach phase for a checkout-relative lifecycle; see postCreateCommand.sh.
set -euo pipefail

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/devcontainer-attached.sh"
