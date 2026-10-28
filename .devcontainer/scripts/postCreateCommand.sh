#!/usr/bin/env bash
# Create phase for a checkout-relative lifecycle, such as the CI responder job and Codex
# Cloud; agentdev-devcontainer runs devcontainer-created.sh itself.
set -euo pipefail

exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/devcontainer-created.sh"
