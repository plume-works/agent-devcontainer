#!/usr/bin/env bash
# Start phase for a checkout-relative lifecycle; see postCreateCommand.sh. With no runtime
# supervisor — a CI container job or Codex Cloud — it starts the services itself first.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ -S ${AGENTDEV_RUN_DIR:-/run/agentdev}/supervisor.sock ]]; then
  exec "$script_dir/devcontainer-ready.sh"
fi

"$script_dir/codebase-memory-mcp-start.sh"
# Headless callers — the CI responder job — opt out of the remote desktop
# nothing will connect to. Unset (the devcontainer default) starts it as before.
if [[ -n "${AGENTDEV_SKIP_XPRA:-}" ]]; then
  echo "AGENTDEV_SKIP_XPRA is set; skipping Xpra startup."
else
  /start-xpra.sh --background
fi

exec "$script_dir/devcontainer-ready.sh" --no-wait
