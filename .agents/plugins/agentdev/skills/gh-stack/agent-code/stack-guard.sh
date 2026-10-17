#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
skill_root_dir="$(cd -- "${script_dir}/.." && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/../../../bin/result-codes.sh"

RESULT_CODES+=(
  "3=REMOTE_ONLY_COMMITS"
  "4=REMOTE_MOVED"
  "5=PUSH_FAILED"
  "6=PUSH_INCOMPLETE"
)

usage() {
  cat <<EOF
Guard every update of a GitHub stack's remote branches against dropping commits
that exist only on a layer's remote.

Skill root: ${skill_root_dir}

Usage:
  stack-guard.sh begin [--remote <name>]
  stack-guard.sh publish [--submit] [--remote <name>]

Subcommands:
  begin     Run before anything rewrites the stack. Fetches every active layer,
            fast-forwards a layer its remote is ahead of, stops on a layer whose
            remote holds a commit the local branch has no patch for, and records
            every layer's remote tip.
  publish   Run in place of gh stack push (or, with --submit, of
            gh stack submit --auto). Stops when a layer's remote tip moved since
            begin, pushes, then verifies every remote tip equals its local tip.
            Without a begin record, applies begin's remote-only test instead.

Options:
  --remote <name>  Remote of the stack. Default: remote.pushDefault, else origin
  --submit         publish only: run gh stack submit --auto instead of push
  -h, --help       Show this help text.

Output (key=value lines):
  RESULT, STATE_FILE
  begin also: FAST_FORWARDED=<layer> for each layer it moved; run
  gh stack rebase --upstack from the lowest of them before editing further
  On REMOTE_ONLY_COMMITS and REMOTE_MOVED, stderr names the layer and commits

Results (RESULT / exit code):
  SUCCESS              0  Nothing on any remote would be or was lost
  REMOTE_ONLY_COMMITS  3  A layer's remote holds commits the local branch lacks;
                          nothing was changed
  REMOTE_MOVED         4  publish: a layer's remote tip changed since begin;
                          nothing was pushed
  PUSH_FAILED          5  publish: the gh stack command failed
  PUSH_INCOMPLETE      6  publish: the push exited 0 but a remote tip still
                          differs from its local tip
  PREFLIGHT_ERROR      2  Bad usage, not a repo, not in a stack, detached HEAD,
                          fetch failure, or a layer that cannot be fast-forwarded
  SCRIPT_FAILURE       1  Unhandled error
  SIGNAL_HUP         129  Interrupted by HUP
  SIGNAL_INT         130  Interrupted by INT
  SIGNAL_TERM        143  Interrupted by TERM

Examples:
  agent-code/stack-guard.sh begin
  agent-code/stack-guard.sh publish
  agent-code/stack-guard.sh publish --submit
EOF
}

print_error() {
  printf 'ERROR: %s\n' "$*" >&2
}

subcommand=""
remote_name=""
submit_mode=0

parse_args() {
  if [[ $# -eq 0 ]]; then
    usage >&2
    quit_by_code 2
  fi
  case "$1" in
    -h | --help)
      usage
      quit_by_code 0
      ;;
    begin | publish) subcommand="$1" ;;
    *)
      print_error "Unknown subcommand: $1"
      quit_by_code 2
      ;;
  esac
  shift
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --remote)
        [[ $# -ge 2 ]] || {
          print_error "Missing value for --remote"
          quit_by_code 2
        }
        remote_name="$2"
        shift 2
        ;;
      --submit)
        [[ "${subcommand}" == "publish" ]] || {
          print_error "--submit applies to publish only"
          quit_by_code 2
        }
        submit_mode=1
        shift
        ;;
      -h | --help)
        usage
        quit_by_code 0
        ;;
      *)
        print_error "Unknown argument: $1"
        quit_by_code 2
        ;;
    esac
  done
}

trunk=""
layers=()
state_file=""

load_stack() {
  local repo_root stack_json
  repo_root="$(git rev-parse --show-toplevel 2>/dev/null)" || {
    print_error "This script must be run inside a Git repository."
    quit_by_code 2
  }
  git symbolic-ref -q HEAD >/dev/null || {
    print_error "HEAD is detached; check out a stack branch first."
    quit_by_code 2
  }
  if [[ -z "${remote_name}" ]]; then
    remote_name="$(git config --get remote.pushDefault || printf 'origin')"
  fi
  git remote get-url "${remote_name}" >/dev/null 2>&1 || {
    print_error "No remote named ${remote_name}."
    quit_by_code 2
  }
  stack_json="$(gh stack view --json 2>/dev/null)" || {
    print_error "The current branch is not in a gh stack (gh stack view --json failed)."
    quit_by_code 2
  }
  trunk="$(jq -r '.trunk // empty' <<<"${stack_json}")"
  mapfile -t layers < <(jq -r '.branches[] | select((.isMerged | not) and (.isQueued | not)) | .name' <<<"${stack_json}")
  if [[ -z "${trunk}" ]]; then
    print_error "gh stack view --json reported no trunk."
    quit_by_code 2
  fi
  state_file="${repo_root}/.tmp/gh-stack-guard/tips"
  printf 'STATE_FILE=%s\n' "${state_file}"
}

# Remote tips as "<branch> <sha>" lines, read straight from the remote.
declare -A remote_tip=()

fetch_layers() {
  local line sha ref refspecs=()
  local listing
  listing="$(git ls-remote --heads "${remote_name}")" || {
    print_error "Could not list branches on ${remote_name}."
    quit_by_code 2
  }
  remote_tip=()
  while read -r sha ref; do
    [[ -n "${ref}" ]] && remote_tip["${ref#refs/heads/}"]="${sha}"
  done <<<"${listing}"
  for line in "${trunk}" "${layers[@]}"; do
    if [[ -n "${remote_tip[${line}]:-}" ]]; then
      refspecs+=("+refs/heads/${line}:refs/remotes/${remote_name}/${line}")
    fi
  done
  if [[ ${#refspecs[@]} -gt 0 ]]; then
    git fetch --quiet "${remote_name}" "${refspecs[@]}" || {
      print_error "Could not fetch the stack from ${remote_name}."
      quit_by_code 2
    }
  fi
}

# Commits on the layer's remote, outside the trunk, with no patch-equivalent locally.
remote_only_commits() {
  local layer="$1"
  local trunk_ref="refs/remotes/${remote_name}/${trunk}"
  local exclude=()
  git rev-parse -q --verify "${trunk_ref}" >/dev/null && exclude=("^${trunk_ref}")
  git rev-list --right-only --cherry-pick --no-merges \
    "refs/heads/${layer}...refs/remotes/${remote_name}/${layer}" "${exclude[@]}"
}

report_remote_only() {
  local layer="$1"
  shift
  print_error "${layer} on ${remote_name} holds commits the local branch lacks:"
  git log --no-walk --format='  %h %s' "$@" >&2
}

# Classifies a layer as equal, absent, ahead, behind, or diverged (remote-only work).
classify_layer() {
  local layer="$1" local_sha remote_sha
  remote_sha="${remote_tip[${layer}]:-}"
  [[ -n "${remote_sha}" ]] || {
    printf 'absent'
    return
  }
  local_sha="$(git rev-parse -q --verify "refs/heads/${layer}")" || {
    printf 'behind'
    return
  }
  if [[ "${local_sha}" == "${remote_sha}" ]]; then
    printf 'equal'
  elif git merge-base --is-ancestor "${local_sha}" "${remote_sha}"; then
    printf 'behind'
  elif git merge-base --is-ancestor "${remote_sha}" "${local_sha}"; then
    printf 'ahead'
  elif [[ -z "$(remote_only_commits "${layer}")" ]]; then
    printf 'rewritten'
  else
    printf 'diverged'
  fi
}

worktree_of() {
  local layer="$1" path="" line
  while read -r line; do
    case "${line}" in
      "worktree "*) path="${line#worktree }" ;;
      "branch refs/heads/${layer}")
        printf '%s' "${path}"
        return
        ;;
    esac
  done < <(git worktree list --porcelain)
}

fast_forward() {
  local layer="$1" target="refs/remotes/${remote_name}/$1" old path
  old="$(git rev-parse -q --verify "refs/heads/${layer}" || true)"
  path="$(worktree_of "${layer}")"
  if [[ -n "${path}" ]]; then
    git -C "${path}" merge --quiet --ff-only "${target}" || {
      print_error "Could not fast-forward ${layer} in ${path}; commit or stash its changes."
      quit_by_code 2
    }
  else
    git update-ref "refs/heads/${layer}" "${target}" ${old:+"${old}"}
  fi
  printf 'FAST_FORWARDED=%s\n' "${layer}"
}

write_state() {
  local layer
  mkdir -p "$(dirname -- "${state_file}")"
  for layer in "${layers[@]}"; do
    printf '%s %s\n' "${layer}" "${remote_tip[${layer}]:--}"
  done >"${state_file}"
}

# Stops with REMOTE_ONLY_COMMITS when any of the given layers would lose remote work.
# Layers its remote is ahead of count as losses unless allow_behind is set.
check_layers() {
  local allow_behind="$1"
  shift
  local layer kind stop=0
  behind_layers=()
  for layer in "$@"; do
    kind="$(classify_layer "${layer}")"
    case "${kind}" in
      behind)
        if [[ "${allow_behind}" -eq 1 ]]; then
          behind_layers+=("${layer}")
        else
          mapfile -t commits < <(git rev-list "refs/heads/${layer}..refs/remotes/${remote_name}/${layer}")
          report_remote_only "${layer}" "${commits[@]}"
          stop=1
        fi
        ;;
      diverged)
        mapfile -t commits < <(remote_only_commits "${layer}")
        report_remote_only "${layer}" "${commits[@]}"
        stop=1
        ;;
    esac
  done
  [[ "${stop}" -eq 0 ]] || quit_by_code 3
}

run_begin() {
  local layer
  fetch_layers
  check_layers 1 "${layers[@]}"
  for layer in "${behind_layers[@]}"; do
    fast_forward "${layer}"
  done
  write_state
  quit_by_code 0
}

run_publish() {
  local layer recorded unrecorded=() moved=0
  declare -A recorded_tip=()
  fetch_layers
  if [[ -f "${state_file}" ]]; then
    while read -r layer recorded; do
      [[ -n "${layer}" ]] && recorded_tip["${layer}"]="${recorded}"
    done <"${state_file}"
  fi
  for layer in "${layers[@]}"; do
    recorded="${recorded_tip[${layer}]:-}"
    if [[ -z "${recorded}" ]]; then
      unrecorded+=("${layer}")
    elif [[ "${recorded}" != "${remote_tip[${layer}]:--}" ]]; then
      print_error "${layer} on ${remote_name} moved since begin: ${recorded:0:7} -> ${remote_tip[${layer}]:-deleted}"
      moved=1
    fi
  done
  [[ "${moved}" -eq 0 ]] || quit_by_code 4
  if [[ ${#unrecorded[@]} -gt 0 ]]; then
    check_layers 0 "${unrecorded[@]}"
  fi

  local push_cmd=(gh stack push --remote "${remote_name}")
  [[ "${submit_mode}" -eq 1 ]] && push_cmd=(gh stack submit --auto --remote "${remote_name}")
  "${push_cmd[@]}" >&2 || {
    print_error "${push_cmd[*]} failed."
    quit_by_code 5
  }

  fetch_layers
  local incomplete=0 local_sha published_sha
  for layer in "${layers[@]}"; do
    local_sha="$(git rev-parse -q --verify "refs/heads/${layer}" || true)"
    published_sha="${remote_tip[${layer}]:-}"
    if [[ "${local_sha}" != "${published_sha}" ]]; then
      print_error "${layer} is not published: local ${local_sha:0:7}, ${remote_name} ${published_sha:0:7}"
      incomplete=1
    fi
  done
  [[ "${incomplete}" -eq 0 ]] || quit_by_code 6
  write_state
  quit_by_code 0
}

parse_args "$@"
load_stack
behind_layers=()
if [[ "${subcommand}" == "begin" ]]; then
  run_begin
else
  run_publish
fi
