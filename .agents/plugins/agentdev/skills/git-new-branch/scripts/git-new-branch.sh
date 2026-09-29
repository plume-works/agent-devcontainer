#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/__common.sh"

RESULT_CODES+=(
  "3=BRANCH_EXISTS"
  "4=CARRY_CONFLICT"
  "5=PUSH_FAILED"
  "6=FETCH_FAILED"
  "7=STASH_CONFLICTS"
  "8=CREATE_FAILED"
)

remote_name="origin"
base_branch="main"
branch_name=""
worktree_mode=0
worktree_root=""
stash_mode=0

usage() {
  show_help_header "Create a work branch at the freshly fetched remote base and push it with its own upstream."
  cat <<'EOF'

Usage:
  git-new-branch.sh <name> [--remote <name>] [--base <branch>] [--stash]
  git-new-branch.sh <name> --worktree [--worktree-root <dir>] [--remote <name>] [--base <branch>]

Options:
  --remote <name>        Remote to fetch from and push to. Default: origin
  --base <branch>        Base branch on the remote. Default: main; when it does
                         not exist, the branch refs/remotes/<remote>/HEAD names,
                         or, when that is unset, the default branch gh reports
  --stash                Stash uncommitted and untracked changes, create the
                         branch, then pop them onto it. Only with user approval.
  --worktree             Create the branch in a new worktree; leave the current
                         checkout alone
  --worktree-root <dir>  Parent directory for the worktree (implies --worktree).
                         Default: /workspaces when the main checkout lives
                         directly under it, otherwise <main checkout>/.worktrees.
                         The worktree is <parent>/<repo>-<name>; a '/' in <name>
                         stays a directory separator
  -h, --help             Show this help text.

Output (key=value lines):
  RESULT, BRANCH, BASE, BASE_SHA
  In worktree mode also: WORKTREE
  When main/master holds commits the base lacks also: LOCAL_COMMITS; the
  branch then starts at HEAD instead of the base, and outside worktree mode
  main/master is reset to the base afterwards
  When changes are left stashed also: STASH_SHA (the entry's commit) and
  STASH_REF (its current stash@{n}; absent if the entry left the list)

Results (RESULT / exit code):
  SUCCESS          0  Branch created, pushed, and tracking <remote>/<name>
  BRANCH_EXISTS    3  <name> exists locally or on the remote; nothing was created
  CARRY_CONFLICT   4  Uncommitted changes touch paths that differ between HEAD
                      and the base; nothing was changed
  PUSH_FAILED      5  The branch was created locally but the push failed
  FETCH_FAILED     6  The remote could not be fetched
  STASH_CONFLICTS  7  The branch was created but popping the stash conflicted;
                      the stash entry STASH_REF is kept
  CREATE_FAILED    8  The branch could not be created; the checkout is unchanged
                      and any stash was restored (STASH_REF when restoring failed)
  PREFLIGHT_ERROR  2  Bad usage, not a repo, invalid name, or no base ref
  SCRIPT_FAILURE   1  Unhandled error
  SIGNAL_HUP     129  Interrupted by HUP
  SIGNAL_INT     130  Interrupted by INT
  SIGNAL_TERM    143  Interrupted by TERM

Examples:
  ${CLAUDE_SKILL_DIR}/scripts/git-new-branch.sh my-feature
  ${CLAUDE_SKILL_DIR}/scripts/git-new-branch.sh my-feature --stash
  ${CLAUDE_SKILL_DIR}/scripts/git-new-branch.sh my-feature --worktree
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --remote)
      [[ $# -ge 2 ]] || { print_error "Missing value for --remote"; quit_by_code 2; }
      remote_name="$2"
      shift 2
      ;;
    --base)
      [[ $# -ge 2 ]] || { print_error "Missing value for --base"; quit_by_code 2; }
      base_branch="$2"
      shift 2
      ;;
    --worktree)
      worktree_mode=1
      shift
      ;;
    --worktree-root)
      [[ $# -ge 2 ]] || { print_error "Missing value for --worktree-root"; quit_by_code 2; }
      worktree_root="$2"
      worktree_mode=1
      shift 2
      ;;
    --stash)
      stash_mode=1
      shift
      ;;
    -h|--help)
      usage
      quit_by_code 0
      ;;
    -*)
      print_error "Unknown option: $1"
      usage >&2
      quit_by_code 2
      ;;
    *)
      if [[ -n "${branch_name}" ]]; then
        print_error "Unexpected argument: $1"
        usage >&2
        quit_by_code 2
      fi
      branch_name="$1"
      shift
      ;;
  esac
done

if [[ -z "${branch_name}" ]]; then
  print_error "Missing branch name."
  usage >&2
  quit_by_code 2
fi

if [[ "${worktree_mode}" -eq 1 && "${stash_mode}" -eq 1 ]]; then
  print_error "--stash has no effect in worktree mode, which leaves the current checkout alone."
  quit_by_code 2
fi

require_git_repo

if ! git check-ref-format --branch "${branch_name}" >/dev/null 2>&1; then
  print_error "'${branch_name}' is not a valid branch name."
  quit_by_code 2
fi

printf 'BRANCH=%s\n' "${branch_name}"

printf 'Fetching %s...\n' "${remote_name}" >&2
if ! git fetch "${remote_name}"; then
  print_error "Failed to fetch remote '${remote_name}'."
  quit_by_code 6
fi

base_ref="${remote_name}/${base_branch}"
if ! git rev-parse --verify --quiet "refs/remotes/${base_ref}^{commit}" >/dev/null; then
  if ! default_branch="$(remote_default_branch "${remote_name}")"; then
    print_error "'${base_ref}' does not exist, refs/remotes/${remote_name}/HEAD is not set, and gh could not report the default branch."
    print_error "Pass --base <branch>, or run: git remote set-head ${remote_name} --auto"
    quit_by_code 2
  fi
  default_ref="${remote_name}/${default_branch}"
  if ! git rev-parse --verify --quiet "refs/remotes/${default_ref}^{commit}" >/dev/null; then
    print_error "The remote default branch '${default_branch}' was not fetched as '${default_ref}'."
    quit_by_code 2
  fi
  printf "'%s' does not exist; using the remote default branch '%s'.\n" \
    "${base_ref}" "${default_ref}" >&2
  base_ref="${default_ref}"
fi
base_sha="$(git rev-parse --verify "refs/remotes/${base_ref}^{commit}")"

printf 'BASE=%s\n' "${base_ref}"
printf 'BASE_SHA=%s\n' "${base_sha}"

if git show-ref --verify --quiet "refs/heads/${branch_name}"; then
  print_error "Local branch '${branch_name}' already exists; it is never reset or reused."
  quit_by_code 3
fi
if git show-ref --verify --quiet "refs/remotes/${remote_name}/${branch_name}"; then
  print_error "'${remote_name}/${branch_name}' already exists; it is never reset or reused."
  quit_by_code 3
fi

# Commits made on the default branch move to the new branch instead of being
# left behind; the caller merges the base in afterwards.
start_sha="${base_sha}"
moved_commits=0
current_branch="$(git symbolic-ref --quiet --short HEAD || true)"
if is_default_branch "${current_branch}"; then
  local_commits="$(git rev-list --count "${base_sha}..HEAD")"
  if [[ "${local_commits}" -gt 0 ]]; then
    start_sha="$(git rev-parse HEAD)"
    moved_commits=1
    printf 'LOCAL_COMMITS=%s\n' "${local_commits}"
    printf "'%s' holds %s commit(s) not in %s; the branch starts at HEAD.\n" \
      "${current_branch}" "${local_commits}" "${base_ref}" >&2
  fi
fi

push_branch() {
  printf 'Pushing %s to %s...\n' "${branch_name}" "${remote_name}" >&2
  git push --set-upstream "${remote_name}" "${branch_name}" >&2
}

if [[ "${worktree_mode}" -eq 1 ]]; then
  main_dir="$(main_checkout_dir)"
  parent_dir="${worktree_root}"
  if [[ -z "${parent_dir}" ]]; then
    if [[ "$(dirname -- "${main_dir}")" == "/workspaces" ]]; then
      parent_dir="/workspaces"
    else
      parent_dir="${main_dir}/.worktrees"
      if ! git -C "${main_dir}" check-ignore --quiet .worktrees/; then
        exclude_file="$(git rev-parse --path-format=absolute --git-common-dir)/info/exclude"
        mkdir -p -- "$(dirname -- "${exclude_file}")"
        printf '.worktrees/\n' >>"${exclude_file}"
        printf 'Added .worktrees/ to %s.\n' "${exclude_file}" >&2
      fi
    fi
  fi
  worktree_dir="${parent_dir}/$(basename -- "${main_dir}")-${branch_name}"
  if [[ -e "${worktree_dir}" ]]; then
    print_error "Worktree path '${worktree_dir}' already exists."
    quit_by_code 2
  fi
  mkdir -p -- "$(dirname -- "${worktree_dir}")"
  git worktree add --no-track -b "${branch_name}" "${worktree_dir}" "${start_sha}" >&2
  printf 'WORKTREE=%s\n' "${worktree_dir}"
  push_branch || { print_error "Push failed; the local branch and worktree are kept."; quit_by_code 5; }
  quit_by_code 0
fi

dirty=0
if [[ -n "$(git status --porcelain --untracked-files=all)" ]]; then
  dirty=1
fi

if [[ "${dirty}" -eq 1 && "${stash_mode}" -eq 0 ]]; then
  declare -A changed_between=()
  while IFS= read -r -d '' path; do
    changed_between["${path}"]=1
  done < <(git diff --no-renames --name-only -z HEAD "${start_sha}")

  blocked=()
  while IFS= read -r -d '' path; do
    if [[ -n "${changed_between["${path}"]+set}" ]]; then
      blocked+=("${path}")
    fi
  done < <(
    git diff --no-renames --name-only -z HEAD
    git diff --cached --no-renames --name-only -z
    git ls-files --others --exclude-standard -z
  )

  if [[ "${#blocked[@]}" -gt 0 ]]; then
    print_error "Uncommitted changes touch paths that differ between HEAD and ${base_ref}:"
    printf '  %s\n' "${blocked[@]}" >&2
    print_error "Nothing was changed. Rerun with --stash only after the user approves stashing."
    quit_by_code 4
  fi
fi

# The stash stack is shared, so only the entry this run created is ever
# popped, located by its commit rather than by position.
stashed=0
stash_sha=""
if [[ "${dirty}" -eq 1 && "${stash_mode}" -eq 1 ]]; then
  stash_before="$(git rev-parse -q --verify refs/stash || true)"
  git stash push --include-untracked --message "git-new-branch: ${branch_name}" >&2
  stash_after="$(git rev-parse -q --verify refs/stash || true)"
  if [[ -n "${stash_after}" && "${stash_after}" != "${stash_before}" ]]; then
    stashed=1
    stash_sha="${stash_after}"
  else
    printf 'git stash saved nothing; no stash entry will be popped.\n' >&2
  fi
fi

stash_ref() {
  local ref sha
  while read -r ref sha; do
    if [[ "${sha}" == "${stash_sha}" ]]; then
      printf '%s\n' "${ref}"
      return 0
    fi
  done < <(git stash list --format='%gd %H')
  return 1
}

pop_own_stash() {
  local ref
  if ! ref="$(stash_ref)"; then
    print_error "Stash entry ${stash_sha} is no longer in the stash list."
    return 1
  fi
  git stash pop "${ref}" >&2
}

# Sets kept_ref for the caller's message.
report_stash() {
  if kept_ref="$(stash_ref)"; then
    printf 'STASH_REF=%s\n' "${kept_ref}"
  else
    kept_ref="${stash_sha}"
  fi
  printf 'STASH_SHA=%s\n' "${stash_sha}"
}

if ! git switch --no-track --create "${branch_name}" "${start_sha}" >&2; then
  print_error "Could not create '${branch_name}'; the checkout was not changed."
  if [[ "${stashed}" -eq 1 ]] && ! pop_own_stash; then
    report_stash
    print_error "Restoring the stash failed; the stash entry ${kept_ref} holds the changes."
  fi
  quit_by_code 8
fi

# The default branch is reset only once its old tip is safe on the new branch.
if [[ "${moved_commits}" -eq 1 ]] \
  && git merge-base --is-ancestor "${start_sha}" "refs/heads/${branch_name}"; then
  git branch --force "${current_branch}" "${base_sha}"
  printf "Reset '%s' to %s; its commits now live on '%s'.\n" \
    "${current_branch}" "${base_ref}" "${branch_name}" >&2
fi

push_status=0
push_branch || push_status=$?

if [[ "${stashed}" -eq 1 ]] && ! pop_own_stash; then
  report_stash
  print_error "Popping the stash conflicted; the stash entry ${kept_ref} is kept."
  if [[ "${push_status}" -ne 0 ]]; then
    print_error "The push also failed; the branch has no upstream yet."
  fi
  quit_by_code 7
fi

if [[ "${push_status}" -ne 0 ]]; then
  print_error "Push failed; the local branch '${branch_name}' is kept."
  quit_by_code 5
fi

quit_by_code 0
