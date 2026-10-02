#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/__common.sh"

RESULT_CODES+=(
  "4=REMOTE_CHECKOUT_DIRTY"
  "5=REMOTE_COMMITS_ABSENT"
  "6=REMOTE_SSH_FAILED"
  "7=RSYNC_FAILED"
  "8=PUSH_REJECTED"
)

usage() {
  show_help_header "Sync the local working tree onto the codespace created by codespace-ensure.sh."
  cat <<'EOF'

Usage:
  codespace-sync.sh

Options:
  -h, --help         Show this help text.

Behavior:
  Refuses to overwrite a dirty Codespace checkout or one with commits that are
  absent from origin. If both trees are safe, a clean local tree is pushed then
  synced by git; a dirty local tree is copied by rsync without deleting
  remote-only files, then removes only git-tracked paths deleted locally. Both
  paths exclude .git and ignored local files.

Output (key=value lines):
  RESULT, ACTION, CODESPACE
  ACTION=rsync also prints: HOST
  ACTION=git-push also prints: BRANCH, and the git push and remote git
  transcripts verbatim before the keys

Results (RESULT / exit code):
  SUCCESS                  0  Synced (either path)
  REMOTE_CHECKOUT_DIRTY    4  Codespace checkout has uncommitted or untracked files
  REMOTE_COMMITS_ABSENT    5  Codespace checkout has commits absent from origin
  REMOTE_SSH_FAILED        6  An SSH call to the codespace failed: checkout inspection,
                              SSH config generation, deleting locally-removed paths, or
                              the remote fetch/checkout/reset
  RSYNC_FAILED             7  rsync to the codespace failed
  PUSH_REJECTED            8  git push failed (diverged, or another push error)
  CODESPACE_SCOPE_MISSING  3  gh token is missing the 'codespace' OAuth scope
  PREFLIGHT_ERROR          2  Usage error, not a repo, detached HEAD, gh or rsync missing,
                              gh unauthenticated, or no recorded codespace name
  SCRIPT_FAILURE           1  Unhandled error

Examples:
  agent-code/codespace-sync.sh
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      quit_by_code 0
      ;;
    *)
      print_error "Unknown argument: $1"
      usage >&2
      quit_by_code 2
      ;;
  esac
done

require_git_repo
require_gh
require_codespace_auth

name="$(read_codespace_name)" || quit_by_code 2
remote_workspace_dir="$(codespace_workspace_dir)" || quit_by_code 2
remote_workspace_dir_q="$(printf '%q' "${remote_workspace_dir}")"

# Build and test artifacts are normally ignored, so they do not make this
# check dirty. Source edits or notes made directly in the Codespace do. A clean
# checkout can still contain commits that only exist in the Codespace; a later
# reset --hard would discard those commits. Refuse both states so the user can
# explicitly preserve or discard remote work before local work becomes source
# of truth again. Each refusal prints a marker the wrapper matches on, so a
# plain SSH or git failure over the same connection is never mistaken for one
# of them.
remote_preflight_cmd="cd ${remote_workspace_dir_q} && git fetch origin && \
remote_status=\$(git status --porcelain) && \
if [[ -n \"\${remote_status}\" ]]; then \
  printf '%s\\n' 'CODESPACE_REMOTE_CHECKOUT_DIRTY' >&2; \
  exit 4; \
fi && \
remote_only_count=\$(git rev-list --count HEAD --not --remotes=origin) && \
if (( remote_only_count > 0 )); then \
  printf '%s\\n' 'CODESPACE_REMOTE_COMMITS_ABSENT_FROM_ORIGIN' >&2; \
  exit 5; \
fi"
remote_preflight_status=0
remote_preflight="$(gh codespace ssh -c "${name}" -- "${remote_preflight_cmd}" 2>&1)" \
  || remote_preflight_status=$?
if [[ "${remote_preflight_status}" -ne 0 ]]; then
  if [[ "${remote_preflight}" == *CODESPACE_REMOTE_CHECKOUT_DIRTY* ]]; then
    print_error "Codespace ${name} has uncommitted or untracked files; refusing to overwrite them. Commit and push them, or discard them, then re-run sync."
    quit_by_code 4
  fi
  if [[ "${remote_preflight}" == *CODESPACE_REMOTE_COMMITS_ABSENT_FROM_ORIGIN* ]]; then
    print_error "Codespace ${name} has commits absent from origin; refusing to reset it. Push or recover those commits, or explicitly return the Codespace checkout to an origin commit, then re-run sync."
    quit_by_code 5
  fi
  print_error "Could not safely inspect the Codespace checkout: ${remote_preflight}"
  quit_by_code 6
fi

if [[ -n "$(git status --porcelain)" ]]; then
  # Rsync path: working tree has uncommitted and/or untracked changes.
  require_rsync
  ssh_cfg="$(ssh_config_file)"

  if ! gh codespace ssh -c "${name}" --config > "${ssh_cfg}"; then
    print_error "Failed to generate SSH config for codespace ${name}."
    quit_by_code 6
  fi

  host="$(awk '/^Host /{print $2; exit}' "${ssh_cfg}")"
  if [[ -z "${host}" ]]; then
    print_error "Could not parse SSH host alias from generated config."
    quit_by_code 6
  fi

  repo_root="$(git rev-parse --show-toplevel)"
  exclude_file="$(sync_exclude_file)"

  # Ask git for its fully-resolved ignore list rather than feeding rsync the
  # root .gitignore directly: rsync's --exclude-from can't see the repo's
  # nested .gitignore files, and it has no concept of gitignore's '!'
  # negation, so files re-included by a negation line (e.g. .vscode/mcp.json)
  # would otherwise be silently dropped from every sync.
  git -C "${repo_root}" ls-files --others --ignored --exclude-standard \
    | sed 's|^|/|' > "${exclude_file}"

  if ! rsync_output="$(rsync -az -e "ssh -F ${ssh_cfg}" \
    --exclude-from="${exclude_file}" --exclude '.git' \
    "${repo_root}/" "${host}:${remote_workspace_dir}/" 2>&1)"; then
    print_error "rsync to codespace failed:"
    printf '%s\n' "${rsync_output}" >&2
    quit_by_code 7
  fi

  # Do not use rsync --delete: the Codespace can contain remote-only logs or
  # other ignored work that must survive a dirty-tree sync. Instead, remove
  # only paths tracked by Git that exist in HEAD but are deleted locally. With
  # --no-renames, a local rename is safely represented as one deletion plus
  # the new path copied by rsync. xargs receives NUL-delimited names, so spaces
  # and newlines in tracked paths remain safe.
  deleted_paths_file="$(repo_root_tmp_dir)/codespace-sync-deleted-paths"
  git -C "${repo_root}" diff --no-renames --name-only -z --diff-filter=D HEAD -- \
    > "${deleted_paths_file}"
  if [[ -s "${deleted_paths_file}" ]]; then
    if ! deletion_output="$(ssh -F "${ssh_cfg}" "${host}" \
      "cd ${remote_workspace_dir_q} && xargs -0 -r rm -f --" \
      < "${deleted_paths_file}" 2>&1)"; then
      print_error "Could not remove git-tracked paths deleted locally:"
      printf '%s\n' "${deletion_output}" >&2
      quit_by_code 6
    fi
  fi

  printf 'ACTION=rsync\n'
  printf 'HOST=%s\n' "${host}"
  printf 'CODESPACE=%s\n' "${name}"
  quit_by_code 0
fi

# Git-push path: working tree is clean.
branch="$(current_branch)" || {
  print_error "Could not determine the current branch."
  quit_by_code 2
}
if [[ "${branch}" == "HEAD" ]]; then
  print_error "Detached HEAD: check out the branch to sync before running this script."
  quit_by_code 2
fi

if git rev-parse --abbrev-ref --symbolic-full-name "${branch}@{u}" >/dev/null 2>&1; then
  push_cmd=(git push)
else
  push_cmd=(git push -u origin "${branch}")
fi

if ! push_output="$("${push_cmd[@]}" 2>&1)"; then
  print_error "Git push failed. Fetch/merge or rebase to resolve, then re-run:"
  printf '%s\n' "${push_output}" >&2
  quit_by_code 8
fi
printf '%s\n' "${push_output}"

branch_q="$(printf '%q' "${branch}")"
if ! ssh_output="$(gh codespace ssh -c "${name}" -- "cd ${remote_workspace_dir_q} && git fetch origin && git checkout ${branch_q} && git reset --hard origin/${branch_q}" 2>&1)"; then
  print_error "Remote sync over SSH failed:"
  printf '%s\n' "${ssh_output}" >&2
  quit_by_code 6
fi
printf '%s\n' "${ssh_output}"

printf 'ACTION=git-push\n'
printf 'BRANCH=%s\n' "${branch}"
printf 'CODESPACE=%s\n' "${name}"
quit_by_code 0
