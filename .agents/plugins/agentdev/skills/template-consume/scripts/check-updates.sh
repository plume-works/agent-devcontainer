#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/__common.sh"

RESULT_CODES+=(
  "3=NO_MARKER"
  "4=UP_TO_DATE"
  "5=CHANGES_FOUND"
  "6=CLONE_FAILED"
  "7=INVALID_MARKER"
)

source_repo="plume-works/agent-devcontainer"
repo_url=""
consumer_root=""
clone_dir=""

usage() {
  show_help_header "Diff this repository's copy of the agent-devcontainer template against the upstream repository's current default branch."
  cat <<'EOF'

Usage:
  check-updates.sh [--repo <owner/name>] [--repo-url <url>] [--root <path>]

Options:
  --repo <owner/name>  Template source repository, recorded for display. Default: plume-works/agent-devcontainer
  --repo-url <url>     Clone URL to fetch, when it differs from https://github.com/<repo>.git
                        (a fork, a GitHub Enterprise host, or a local path).
  --root <path>        Consumer repository root. Default: discovered via `git rev-parse`.
  -h, --help           Show this help text.

Reads the marker file (.agentdev-template.json) at the consumer repository root,
shallow-clones the template repository's default branch into ./.tmp/, and lists
which template-owned paths changed between the marker's consumed_ref and the
upstream HEAD. Prints nothing about paths this consumer already deleted.

Output (key=value lines):
  RESULT, CONSUMED_REF, UPSTREAM_REF
  On CHANGES_FOUND also: CHANGED_PATHS (newline-indented list)

Results (RESULT / exit code):
  UP_TO_DATE      4  consumed_ref already matches the upstream default branch
  CHANGES_FOUND   5  One or more tracked template paths changed upstream
  NO_MARKER       3  No .agentdev-template.json at the consumer root; run setup mode first
  INVALID_MARKER  7  Marker file exists but is not valid JSON or is missing consumed_ref
  CLONE_FAILED    6  Could not fetch the template repository
  PREFLIGHT_ERROR 2  Usage or preflight error (not a repo)
  SCRIPT_FAILURE  1  Unhandled error

Examples:
  ${CLAUDE_SKILL_DIR}/scripts/check-updates.sh
  ${CLAUDE_SKILL_DIR}/scripts/check-updates.sh --repo plume-works/agent-devcontainer
  ${CLAUDE_SKILL_DIR}/scripts/check-updates.sh --repo-url git@github.com:my-org/agent-devcontainer.git
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      [[ $# -ge 2 ]] || {
        print_error "Missing value for --repo"
        quit_by_code 2
      }
      source_repo="$2"
      shift 2
      ;;
    --repo-url)
      [[ $# -ge 2 ]] || {
        print_error "Missing value for --repo-url"
        quit_by_code 2
      }
      repo_url="$2"
      shift 2
      ;;
    --root)
      [[ $# -ge 2 ]] || {
        print_error "Missing value for --root"
        quit_by_code 2
      }
      consumer_root="$2"
      shift 2
      ;;
    -h | --help)
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

if [[ -z "${consumer_root}" ]]; then
  require_git_repo
  consumer_root="$(git rev-parse --show-toplevel)"
elif ! git -C "${consumer_root}" rev-parse --show-toplevel >/dev/null 2>&1; then
  print_error "--root ${consumer_root} is not inside a Git repository."
  quit_by_code 2
fi

marker_name="$(marker_file_name)"
marker_path="${consumer_root}/${marker_name}"

if [[ ! -f "${marker_path}" ]]; then
  print_error "No ${marker_name} at ${consumer_root}. Run setup mode first."
  quit_by_code 3
fi

if ! command -v jq >/dev/null 2>&1; then
  print_error "jq is required to read ${marker_name}."
  quit_by_code 1
fi

consumed_ref="$(jq -r '.consumed_ref // empty' "${marker_path}" 2>/dev/null)" || consumed_ref=""

if [[ -z "${consumed_ref}" ]] ||
  ! jq -e '(.tracked_paths | type) == "array" and (.tracked_paths | length) > 0' \
    "${marker_path}" >/dev/null 2>&1; then
  print_error "${marker_name} is missing consumed_ref or tracked_paths."
  quit_by_code 7
fi

tracked_paths_json="$(jq -c '.tracked_paths' "${marker_path}")"

cleanup() {
  local exit_code=$?
  [[ -n "${clone_dir}" && -d "${clone_dir}" ]] && rm -rf "${clone_dir}"
  # Re-run report_unhandled_exit here: this trap replaces the one it installed.
  (exit "${exit_code}") || report_unhandled_exit
  return "${exit_code}"
}
trap cleanup EXIT

tmp_root="${consumer_root}/.tmp"
mkdir -p "${tmp_root}"
clone_dir="$(mktemp -d "${tmp_root}/template-consume.XXXXXX")"

if [[ -z "${repo_url}" ]]; then
  repo_url="https://github.com/${source_repo}.git"
fi

if ! git clone --quiet --filter=blob:none "${repo_url}" "${clone_dir}" >/dev/null 2>&1; then
  print_error "Failed to clone ${repo_url} into ${clone_dir}."
  quit_by_code 6
fi

upstream_ref="$(git -C "${clone_dir}" rev-parse HEAD)"

printf 'CONSUMED_REF=%s\n' "${consumed_ref}"
printf 'UPSTREAM_REF=%s\n' "${upstream_ref}"

if [[ "${consumed_ref}" == "${upstream_ref}" ]]; then
  quit_by_code 4
fi

if ! git -C "${clone_dir}" cat-file -e "${consumed_ref}" 2>/dev/null; then
  print_error "consumed_ref ${consumed_ref} is not reachable in ${source_repo}; it may predate this clone's history."
  quit_by_code 7
fi

mapfile -t tracked_paths < <(printf '%s' "${tracked_paths_json}" | jq -r '.[]')

changed_paths=()
for path in "${tracked_paths[@]}"; do
  if ! git -C "${clone_dir}" diff --quiet "${consumed_ref}" "${upstream_ref}" -- "${path}" 2>/dev/null; then
    changed_paths+=("${path}")
  fi
done

if [[ ${#changed_paths[@]} -eq 0 ]]; then
  quit_by_code 4
fi

printf 'CHANGED_PATHS=%s\n' "${#changed_paths[@]}"
for path in "${changed_paths[@]}"; do
  printf '  %s\n' "${path}"
done

quit_by_code 5
