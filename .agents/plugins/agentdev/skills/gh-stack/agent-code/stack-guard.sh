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
  begin     Run before anything rewrites the stack. Fetches every unmerged layer,
            queued ones included, fast-forwards a layer its remote is ahead of,
            stops on a layer whose remote holds a commit the local branch has no
            identical patch for or a merge it lacks, and records every layer's
            remote tip.
  publish   Run in place of gh stack push (or, with --submit, of
            gh stack submit --auto). Stops when a layer's remote tip moved since
            begin to anything but its local tip, then pushes every changed layer
            in one atomic push leased on the tips it checked; this is the only
            force-push. --submit then runs gh stack link, which pushes without
            force and opens the missing draft PRs: create mode for a stack with
            no merged layer, add mode (link <stack#> <new layers>) to append
            PR-less top layers once one has merged, and no link when every
            layer has a PR and one has merged. After a link it runs
            gh stack checkout <stack#> to record the PRs locally, keeping the
            current branch. Finally verifies every remote
            tip equals its local tip. A layer still in the merge queue is never
            pushed and is noted on stderr.
            Without a begin record, applies begin's remote-only test instead.

Options:
  --remote <name>  Remote of the stack. Default: remote.pushDefault, else origin
  --submit         publish only: also open and link the PRs with gh stack link;
                   refused for a PR-less layer below one with a PR, an
                   all-digit layer name, or a failed stack-number lookup
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
  REMOTE_MOVED         4  publish: a layer's remote tip changed since begin or
                          after the check; nothing was pushed
  PUSH_FAILED          5  publish: the guard's push, gh stack link, or recording
                          the linked PRs locally failed
  PUSH_INCOMPLETE      6  publish: the push exited 0 but a remote tip still
                          differs from its local tip
  PREFLIGHT_ERROR      2  Bad usage, not a repo, not in a stack, detached HEAD,
                          fetch failure, a layer that cannot be fast-forwarded,
                          or a stack --submit cannot link
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
stack_view=""
state_file=""

load_stack() {
  local repo_root layer
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
  stack_view="$(gh stack view --json 2>/dev/null)" || {
    print_error "The current branch is not in a gh stack (gh stack view --json failed)."
    quit_by_code 2
  }
  trunk="$(jq -r '.trunk // empty' <<<"${stack_view}")"
  mapfile -t layers < <(jq -r '.branches[] | select(.isMerged | not) | .name' <<<"${stack_view}")
  # Queued layers are checked and recorded like any other, but never pushed.
  while read -r layer; do
    [[ -n "${layer}" ]] && queued["${layer}"]=1
  done < <(jq -r '.branches[] | select((.isMerged | not) and .isQueued) | .name' <<<"${stack_view}")
  if [[ -z "${trunk}" ]]; then
    print_error "gh stack view --json reported no trunk."
    quit_by_code 2
  fi
  state_file="${repo_root}/.tmp/gh-stack-guard/tips"
  printf 'STATE_FILE=%s\n' "${state_file}"
}

# Tip of each branch on the remote, as fetched. ls-remote only says which branches exist, so
# the checks, the record, and the lease all use the very SHA the checks examined.
declare -A remote_tip=()

fetch_layers() {
  local branch ref listing refspecs=() present=()
  declare -A on_remote=()
  listing="$(git ls-remote --heads "${remote_name}")" || {
    print_error "Could not list branches on ${remote_name}."
    quit_by_code 2
  }
  while read -r _ ref; do
    [[ -n "${ref}" ]] && on_remote["${ref#refs/heads/}"]=1
  done <<<"${listing}"
  for branch in "${trunk}" "${layers[@]}"; do
    if [[ -n "${on_remote[${branch}]:-}" ]]; then
      refspecs+=("+refs/heads/${branch}:refs/remotes/${remote_name}/${branch}")
      present+=("${branch}")
    fi
  done
  if [[ ${#refspecs[@]} -gt 0 ]]; then
    git fetch --quiet "${remote_name}" "${refspecs[@]}" || {
      print_error "Could not fetch the stack from ${remote_name}."
      quit_by_code 2
    }
  fi
  remote_tip=()
  for branch in "${present[@]}"; do
    remote_tip["${branch}"]="$(git rev-parse --verify "refs/remotes/${remote_name}/${branch}")"
  done
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

# The only force-push: every changed layer in one atomic push leased on the tip publish
# checked, so a push landing after the check is refused rather than overwritten.
push_layers() {
  local layer local_sha flag ref summary output leases=() refspecs=() status=0 moved=0
  for layer in "${layers[@]}"; do
    local_sha="$(git rev-parse -q --verify "refs/heads/${layer}" || true)"
    [[ -z "${local_sha}" || "${local_sha}" == "${remote_tip[${layer}]:-}" ]] && continue
    # Pushing would take the layer out of the merge queue.
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

pr_of() {
  jq -r --arg name "$1" --arg field "$2" \
    '.branches[] | select(.name == $name) | .pr[$field] // empty' <<<"${stack_view}"
}

link_args=()

# Chooses the gh stack link call before anything is pushed: none when every layer has a PR
# and one has merged, add mode to append PR-less top layers to the GitHub stack, else create
# mode. Policy: see architecture/stack-push-guard.
plan_link() {
  local layer number="" stack_number="" new=() names=() merged
  merged="$(jq '[.branches[] | select(.isMerged)] | length' <<<"${stack_view}")"
  number="$(jq -r '[.branches[].pr.number // empty] | last // empty' <<<"${stack_view}")"
  for layer in "${layers[@]}"; do
    if [[ -z "$(pr_of "${layer}" number)" ]]; then
      [[ -z "${queued[${layer}]:-}" ]] || {
        print_error "Queued layer ${layer} has no PR to link."
        quit_by_code 2
      }
      new+=("${layer}")
    elif [[ ${#new[@]} -gt 0 ]]; then
      print_error "${new[0]} has no PR but ${layer} above it does; link can only append on top."
      quit_by_code 2
    fi
  done
  if [[ ${#new[@]} -gt 0 && -n "${number}" ]]; then
    stack_number="$(gh api "repos/{owner}/{repo}/pulls/${number}" --jq .stack.number)" || {
      print_error "Could not read the GitHub stack of PR #${number}; nothing was pushed."
      quit_by_code 2
    }
    [[ "${stack_number}" != null ]] || stack_number=""
  fi
  if [[ -n "${stack_number}" ]]; then
    names=("${new[@]}")
    link_args=("${stack_number}" "${names[@]}")
  elif [[ ${#new[@]} -eq 0 && "${merged}" -gt 0 ]]; then
    link_args=()
  elif [[ "${merged}" -gt 0 ]]; then
    print_error "The stack has merged layers but no GitHub stack to append to."
    quit_by_code 2
  else
    link_args=(--base "${trunk}")
    for layer in "${layers[@]}"; do
      if [[ -n "${queued[${layer}]:-}" ]]; then
        link_args+=("$(pr_of "${layer}" url)")
      else
        names+=("${layer}")
        link_args+=("${layer}")
      fi
    done
  fi
  for layer in "${names[@]}"; do
    if [[ "${layer}" =~ ^[0-9]+$ ]]; then
      print_error "gh stack link would read layer ${layer} as a PR number; rename the branch."
      quit_by_code 2
    fi
  done
}

link_layers() {
  [[ ${#link_args[@]} -gt 0 ]] || return 0
  gh stack link --remote "${remote_name}" "${link_args[@]}" >&2 || {
    print_error "gh stack link failed."
    quit_by_code 5
  }
  stack_number=""
  record_stack || {
    print_error "PRs are linked but not recorded locally;" \
      "run gh stack checkout ${stack_number:-<stack#>} or rerun publish --submit."
    quit_by_code 5
  }
}

# gh stack link writes no local state, so the next view would report the new PRs as missing;
# gh stack checkout of the GitHub stack records them. It may move HEAD, which is restored.
record_stack() {
  local layer number branch
  branch="$(git symbolic-ref -q --short HEAD)" || return 1
  if [[ "${link_args[0]}" == --base ]]; then
    for layer in "${layers[@]}"; do
      [[ -n "${queued[${layer}]:-}" ]] || break
    done
    number="$(gh pr list --head "${layer}" --json number --jq '.[0].number')" || return 1
    [[ -n "${number}" ]] || return 1
    stack_number="$(gh api "repos/{owner}/{repo}/pulls/${number}" --jq .stack.number)" || return 1
    [[ -n "${stack_number}" && "${stack_number}" != null ]] || return 1
  else
    stack_number="${link_args[0]}"
  fi
  gh stack checkout "${stack_number}" </dev/null >&2 || return 1
  [[ "$(git symbolic-ref -q --short HEAD)" == "${branch}" ]] || git switch -q "${branch}"
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
  declare -A recorded_tip=() checked_tip=()
  [[ "${submit_mode}" -eq 0 ]] || plan_link
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
    checked_tip["${layer}"]="${remote_tip[${layer}]:-}"
  done
  [[ "${moved}" -eq 0 ]] || quit_by_code 4
  if [[ ${#unrecorded[@]} -gt 0 ]]; then
    check_layers 0 "${unrecorded[@]}"
  fi

  push_layers
  [[ "${submit_mode}" -eq 0 ]] || link_layers

  fetch_layers
  local incomplete=0 local_sha published_sha
  for layer in "${layers[@]}"; do
    local_sha="$(git rev-parse -q --verify "refs/heads/${layer}" || true)"
    published_sha="${remote_tip[${layer}]:-}"
    [[ "${local_sha}" == "${published_sha}" ]] && continue
    if [[ -n "${queued[${layer}]:-}" && "${published_sha}" == "${checked_tip[${layer}]}" ]]; then
      printf 'NOTE: %s is queued and was not published.\n' "${layer}" >&2
    else
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
