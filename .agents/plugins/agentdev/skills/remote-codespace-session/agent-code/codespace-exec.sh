#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/__common.sh"

RESULT_CODES+=("4=REMOTE_COMMAND_FAILED")

usage() {
  show_help_header "Run a command on the codespace (created by codespace-ensure.sh, synced by codespace-sync.sh) via SSH."
  cat <<'EOF'

Usage:
  codespace-exec.sh <command> [args...]

Runs '<command> [args...]' on the codespace, inside the repo's workspace
directory, over 'gh codespace ssh'. Everything after the script name is
forwarded verbatim as the remote command -- including '-h'/'--help', which
is passed through to the remote command rather than being intercepted by
this script. This help text is therefore printed only when no command is
given at all.

Output:
  The remote command's own stdout, verbatim, then the key=value lines
  REMOTE_EXIT_CODE and RESULT.

REMOTE_EXIT_CODE is the status 'gh codespace ssh' returned -- normally the
remote command's own exit status. This script does NOT exit with it: its own
exit code names its own outcome, so a remote command exiting 3 cannot be read
as this script's CODESPACE_SCOPE_MISSING. Branch on REMOTE_EXIT_CODE when the
remote command's exact status matters (a test runner's 1 versus 5).

Results (RESULT / exit code):
  SUCCESS                  0  The remote command ran and exited 0
  REMOTE_COMMAND_FAILED    4  'gh codespace ssh' exited non-zero: the remote command
                              failed, or the connection to the codespace did.
                              REMOTE_EXIT_CODE carries the status
  CODESPACE_SCOPE_MISSING  3  gh token is missing the 'codespace' OAuth scope
  PREFLIGHT_ERROR          2  No command given, not a repo, gh missing or
                              unauthenticated, or no recorded codespace name
  SCRIPT_FAILURE           1  Unhandled error

Examples:
  codespace-exec.sh uv run pytest py_packages/validate_agent_files
  codespace-exec.sh bun test
EOF
}

if [[ $# -eq 0 ]]; then
  usage >&2
  quit_by_code 2
fi

require_git_repo
require_gh
require_codespace_auth

name="$(read_codespace_name)" || quit_by_code 2
workspace_dir="$(codespace_workspace_dir)" || quit_by_code 2

remote_cmd="cd ${workspace_dir} &&"
for arg in "$@"; do
  remote_cmd="${remote_cmd} $(printf '%q' "${arg}")"
done

# Pass the whole remote command as a SINGLE argument. 'gh codespace ssh --
# <args>' forwards <args> to ssh, which flattens them into one string that the
# remote shell re-parses; a 'bash -lc "<cmd>"' triple would lose its grouping
# there (the '&&' would re-split at the top level), so build one string and let
# the remote login shell run it directly.
status=0
gh codespace ssh -c "${name}" -- "${remote_cmd}" || status=$?

printf '\nREMOTE_EXIT_CODE=%s\n' "${status}"
if [[ "${status}" -ne 0 ]]; then
  print_error "Remote command exited ${status} on codespace ${name}."
  quit_by_code 4
fi
quit_by_code 0
