#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"$script_dir/reinstall-agentdev-plugins.sh"
git config --global gpg.ssh.program ssh-keygen
"$script_dir/uv-sync.sh"
