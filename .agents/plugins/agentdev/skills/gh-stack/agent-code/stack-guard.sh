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
  "7=REMOTE_OVERWRITTEN"
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
  begin     Run before anything rewrites the stack. Fetches every unmerged layer,
            queued ones included, fast-forwards a layer its remote is ahead of,
            stops on a layer whose remote holds a commit the local branch has no
            identical patch for or a merge it lacks, and records every layer's
            remote tip.
  publish   Run in place of gh stack push (or, with --submit, of
            gh stack submit --auto). Stops when a layer's remote tip moved since
            begin to anything but its local tip, pushes every changed layer in
            one atomic push leased on the tips it checked, runs the gh stack
            command, reports remote work that command overwrote, then verifies
            every remote tip equals its local tip. A layer still in the merge
            queue is left unpushed, as gh stack leaves it, and noted on stderr.
            Without a begin record, applies begin's remote-only test instead.

Options:
  --remote <name>  Remote of the stack. Default: remote.pushDefault, else origin
  --submit         publish only: run gh stack submit --auto instead of push
  -h, --help       Show this help text.

Output (key=value lines):
  RESULT, STATE_FILE
  begin also: FAST_FORWARDED=<layer> for each layer it moved; run
  gh stack rebase --upstack from the lowest of them before editing further
  On REMOTE_ONLY_COMMITS, REMOTE_MOVED, and REMOTE_OVERWRITTEN, stderr names
  the layer and commits

Results (RESULT / exit code):
  SUCCESS              0  Nothing on any remote would be or was lost
  REMOTE_ONLY_COMMITS  3  A layer's remote holds commits the local branch lacks;
                          nothing was changed
  REMOTE_MOVED         4  publish: a layer's remote tip changed since begin or
                          after the check; nothing was pushed
  PUSH_FAILED          5  publish: the guard's push or the gh stack command failed
  PUSH_INCOMPLETE      6  publish: the push exited 0 but a remote tip still
                          differs from its local tip
  REMOTE_OVERWRITTEN   7  publish: a push that landed after the guard's push was
                          overwritten by gh stack; stderr names the lost commits
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
declare -A queued=()
state_file=""

# Queued layers stay guarded: a push to one dequeues it, and gh stack then pushes it too.
read_queued() {
  local layer
  queued=()
  while read -r layer; do
    [[ -n "${layer}" ]] && queued["${layer}"]=1
  done < <(jq -r '.branches[] | select((.isMerged | not) and .isQueued) | .name' <<<"$1")
}

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
  mapfile -t layers < <(jq -r '.branches[] | select(.isMerged | not) | .name' <<<"${stack_json}")
  read_queued "${stack_json}"
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

# "<patch-id> <commit>" for the non-merge commits of one side of a range.
# --verbatim: the default patch-id ignores whitespace, so a whitespace-only fix would match.
side_patch_ids() {
  git log -p --no-merges --no-color --no-ext-diff --format='commit %H' "$@" |
    git patch-id --verbatim
}

# Commits on the layer's remote (or on rev $2), outside the trunk, that the local branch
# lacks: non-merges with no byte-identical local patch, and every remote-only merge.
remote_only_commits() {
  local layer="$1" remote_rev="${2:-refs/remotes/${remote_name}/$1}"
  local trunk_ref="refs/remotes/${remote_name}/${trunk}"
  local exclude=() range="refs/heads/${layer}...${remote_rev}" id sha
  declare -A local_ids=() remote_id=()
  git rev-parse -q --verify "${trunk_ref}" >/dev/null && exclude=("^${trunk_ref}")
  while read -r id sha; do
    local_ids["${id}"]=1
  done < <(side_patch_ids --left-only "${range}" "${exclude[@]}")
  while read -r id sha; do
    remote_id["${sha}"]="${id}"
  done < <(side_patch_ids --right-only "${range}" "${exclude[@]}")
  while read -r sha; do
    id="${remote_id[${sha}]:-}"
    [[ -n "${id}" && -n "${local_ids[${id}]:-}" ]] || printf '%s\n' "${sha}"
  done < <(git rev-list --right-only --no-merges "${range}" "${exclude[@]}")
  git rev-list --right-only --merges "${range}" "${exclude[@]}"
}

report_remote_only() {
  local layer="$1"
  shift
  print_error "${layer} on ${remote_name} holds commits the local branch lacks:"
  git log --no-walk --format='  %h %s' "$@" >&2
}

# rewritten: the histories split, but the remote holds no patch the local branch lacks.
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

# An untracked .tmp/ would make gh stack rebase refuse the worktree as dirty.
exclude_state_dir() {
  local exclude_file
  git check-ignore --quiet "${state_file}" && return 0
  exclude_file="$(git rev-parse --path-format=absolute --git-common-dir)/info/exclude"
  mkdir -p -- "$(dirname -- "${exclude_file}")"
  if [[ -s "${exclude_file}" && -n "$(tail -c 1 -- "${exclude_file}")" ]]; then
    printf '\n' >>"${exclude_file}"
  fi
  printf '.tmp/\n' >>"${exclude_file}"
}

# Reflog depth of each layer's tracking ref; gh stack's own fetch adds entries above it.
declare -A reflog_depth=()

reflog_tips() {
  git reflog show --format=%H "refs/remotes/${remote_name}/$1" -- 2>/dev/null || true
}

mark_reflogs() {
  local layer
  for layer in "${layers[@]}"; do
    reflog_depth["${layer}"]="$(reflog_tips "${layer}" | wc -l)"
  done
}

# Stops with REMOTE_OVERWRITTEN when a tip gh stack fetched after the check held remote work.
check_overwritten() {
  local layer local_sha seen new_count sha lost=0
  for layer in "${layers[@]}"; do
    local_sha="$(git rev-parse -q --verify "refs/heads/${layer}" || true)"
    mapfile -t seen < <(reflog_tips "${layer}")
    new_count=$((${#seen[@]} - ${reflog_depth[${layer}]:-0}))
    for sha in "${seen[@]:0:$((new_count > 0 ? new_count : 0))}"; do
      [[ "${sha}" == "${checked_tip[${layer}]:-}" || "${sha}" == "${local_sha}" ]] && continue
      mapfile -t commits < <(remote_only_commits "${layer}" "${sha}")
      if [[ ${#commits[@]} -gt 0 ]]; then
        print_error "The push overwrote ${layer} at ${sha:0:7}, pushed after the check."
        report_remote_only "${layer}" "${commits[@]}"
        lost=1
      fi
    done
  done
  [[ "${lost}" -eq 0 ]] || quit_by_code 7
}

# Forces reflogs on remote-tracking refs for this run and the gh stack it starts.
log_ref_updates() {
  local index="${GIT_CONFIG_COUNT:-0}"
  export "GIT_CONFIG_KEY_${index}=core.logAllRefUpdates" "GIT_CONFIG_VALUE_${index}=true"
  export GIT_CONFIG_COUNT=$((index + 1))
}

# Pushes every changed layer in one atomic push leased on the tip publish checked, so a
# push landing after the check is refused rather than overwritten (REMOTE_MOVED).
push_layers() {
  local layer local_sha flag ref summary output leases=() refspecs=() status=0 moved=0
  for layer in "${layers[@]}"; do
    local_sha="$(git rev-parse -q --verify "refs/heads/${layer}" || true)"
    [[ -z "${local_sha}" || "${local_sha}" == "${remote_tip[${layer}]:-}" ]] && continue
    # Pushing would take the layer out of the merge queue, which gh stack avoids too.
    if [[ -n "${queued[${layer}]:-}" ]]; then
      printf 'NOTE: %s is queued; leaving it unpushed.\n' "${layer}" >&2
      continue
    fi
    leases+=("--force-with-lease=refs/heads/${layer}:${remote_tip[${layer}]:-}")
    refspecs+=("refs/heads/${layer}:refs/heads/${layer}")
  done
  [[ ${#refspecs[@]} -gt 0 ]] || return 0
  output="$(git push --atomic --porcelain "${leases[@]}" "${remote_name}" "${refspecs[@]}")" ||
    status=$?
  [[ "${status}" -eq 0 ]] && return 0
  while IFS=$'\t' read -r flag ref summary; do
    [[ "${flag}" == '!' && "${summary}" == *'(stale info)'* ]] || continue
    ref="${ref%%:*}"
    print_error "${ref#refs/heads/} on ${remote_name} moved after the check; nothing was pushed."
    moved=1
  done <<<"${output}"
  [[ "${moved}" -eq 0 ]] || quit_by_code 4
  printf '%s\n' "${output}" >&2
  print_error "Pushing the stack to ${remote_name} failed."
  quit_by_code 5
}

write_state() {
  local layer
  exclude_state_dir
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
  local layer recorded current unrecorded=() moved=0
  declare -A recorded_tip=()
  log_ref_updates
  fetch_layers
  if [[ -f "${state_file}" ]]; then
    while read -r layer recorded; do
      [[ -n "${layer}" ]] && recorded_tip["${layer}"]="${recorded}"
    done <"${state_file}"
  fi
  for layer in "${layers[@]}"; do
    recorded="${recorded_tip[${layer}]:-}"
    # A remote already at the local tip loses nothing, e.g. a layer a failed publish pushed.
    current="$(git rev-parse -q --verify "refs/heads/${layer}" || true)"
    if [[ -z "${recorded}" ]]; then
      unrecorded+=("${layer}")
    elif [[ "${recorded}" != "${remote_tip[${layer}]:--}" && "${current}" != "${remote_tip[${layer}]:-}" ]]; then
      print_error "${layer} on ${remote_name} moved since begin: ${recorded:0:7} -> ${remote_tip[${layer}]:-deleted}"
      moved=1
    fi
  done
  [[ "${moved}" -eq 0 ]] || quit_by_code 4
  if [[ ${#unrecorded[@]} -gt 0 ]]; then
    check_layers 0 "${unrecorded[@]}"
  fi

  local push_cmd=(gh stack push --remote "${remote_name}") push_status=0
  [[ "${submit_mode}" -eq 1 ]] && push_cmd=(gh stack submit --auto --remote "${remote_name}")
  declare -A checked_tip=()
  for layer in "${layers[@]}"; do
    checked_tip["${layer}"]="${remote_tip[${layer}]:-}"
  done
  push_layers
  mark_reflogs
  "${push_cmd[@]}" >&2 || push_status=$?
  check_overwritten
  if [[ "${push_status}" -ne 0 ]]; then
    print_error "${push_cmd[*]} failed."
    quit_by_code 5
  fi

  fetch_layers
  # gh stack skips only layers still queued when it runs, so re-read the queue for the verify.
  local incomplete=0 local_sha published_sha stack_json=""
  stack_json="$(gh stack view --json 2>/dev/null)" || print_error "gh stack view --json failed."
  queued=()
  [[ -z "${stack_json}" ]] || read_queued "${stack_json}"
  for layer in "${layers[@]}"; do
    local_sha="$(git rev-parse -q --verify "refs/heads/${layer}" || true)"
    published_sha="${remote_tip[${layer}]:-}"
    if [[ "${local_sha}" != "${published_sha}" && -n "${queued[${layer}]:-}" ]]; then
      printf 'NOTE: %s is queued and was not published.\n' "${layer}" >&2
    elif [[ "${local_sha}" != "${published_sha}" ]]; then
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
