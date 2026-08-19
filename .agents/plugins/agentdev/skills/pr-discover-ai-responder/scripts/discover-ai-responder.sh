#!/usr/bin/env bash

set -euo pipefail

skill_script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
skill_root_dir="$(cd -- "${skill_script_dir}/.." && pwd)"
# shellcheck source=/dev/null
source "${skill_script_dir}/../../../bin/result-codes.sh"

RESULT_CODES+=("3=NO_RESPONDER_WORKFLOW" "4=AMBIGUOUS_WORKFLOW" "5=GH_UNAVAILABLE")

# Workflow names that answer an `@claude review` mention. The responder is named
# for what it does, not for a fixed filename, so match on the display name.
name_pattern="responder|claude"
workflow_override=""

print_error() {
  printf 'ERROR: %s\n' "$*" >&2
}

usage() {
  printf 'Resolve the workflow file that answers @claude review mentions.\n\n'
  printf 'Skill root: %s\n' "${skill_root_dir}"
  cat <<'EOF'

Usage:
  discover-ai-responder.sh [--pattern <regex>] [--workflow <file>]

Options:
  --pattern <regex>  Case-insensitive regex matched against workflow names.
                     Default: responder|claude
  --workflow <file>  Skip discovery and emit this filename. Use when the
                     responder's filename is already known.
  -h, --help         Show this help text.

Output (key=value lines):
  RESPONDER_WORKFLOW, RESULT

Results (RESULT / exit code):
  SUCCESS               0  Exactly one responder workflow resolved
  NO_RESPONDER_WORKFLOW 3  No workflow name matched the pattern
  AMBIGUOUS_WORKFLOW    4  Several matched; candidates are listed on stderr
  GH_UNAVAILABLE        5  gh is missing, unauthenticated, or its API call failed
  PREFLIGHT_ERROR       2  Usage error or invalid pattern
  SCRIPT_FAILURE        1  Unhandled error

Examples:
  ${CLAUDE_SKILL_DIR}/scripts/discover-ai-responder.sh
  ${CLAUDE_SKILL_DIR}/scripts/discover-ai-responder.sh --pattern 'ai-responder'
  ${CLAUDE_SKILL_DIR}/scripts/discover-ai-responder.sh --workflow ai-responder.yml
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pattern)
      [[ $# -ge 2 ]] || { print_error "Missing value for --pattern"; quit_by_code 2; }
      name_pattern="$2"
      shift 2
      ;;
    --workflow)
      [[ $# -ge 2 ]] || { print_error "Missing value for --workflow"; quit_by_code 2; }
      workflow_override="$2"
      shift 2
      ;;
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

if [[ -n "${workflow_override}" ]]; then
  printf 'RESPONDER_WORKFLOW=%s\n' "$(basename -- "${workflow_override}")"
  quit_by_code 0
fi

if ! command -v gh >/dev/null 2>&1; then
  print_error "The GitHub CLI (gh) is not installed or not on PATH."
  quit_by_code 5
fi

# Filter with gh's own --jq so the script needs no standalone jq. A repository
# may file its workflows under a nested path, so reduce to the basename that
# `gh run list --workflow=` accepts.
invalid_pattern_marker="__AGENTDEV_INVALID_RESPONDER_NAME_PATTERN__"
if ! matched_paths="$(
  # shellcheck disable=SC2016 # jq variables must remain literal for gh.
  NAME_PATTERN="${name_pattern}" gh workflow list --all --json name,path \
    --jq '. as $workflows
      | env.NAME_PATTERN as $pattern
      | (try ("" | test($pattern; "i"))
         catch "__AGENTDEV_INVALID_RESPONDER_NAME_PATTERN__") as $pattern_validation
      | if $pattern_validation == "__AGENTDEV_INVALID_RESPONDER_NAME_PATTERN__"
        then "__AGENTDEV_INVALID_RESPONDER_NAME_PATTERN__"
        else
          $workflows[]
          | select(.name | test($pattern; "i"))
          | .path
        end' 2>&1
)"; then
  print_error "Could not list workflows. Check 'gh auth status' and the current repository."
  printf '%s\n' "${matched_paths}" >&2
  quit_by_code 5
fi

if [[ "${matched_paths}" == "${invalid_pattern_marker}" ]]; then
  print_error "Invalid workflow name pattern: ${name_pattern}"
  quit_by_code 2
fi

candidates=()
while IFS= read -r workflow_path; do
  [[ -n "${workflow_path}" ]] || continue
  candidates+=("$(basename -- "${workflow_path}")")
done < <(printf '%s\n' "${matched_paths}" | sort -u)

case "${#candidates[@]}" in
  0)
    print_error "No workflow name matched /${name_pattern}/i in this repository."
    print_error "Re-run with --pattern if the responder is named differently."
    quit_by_code 3
    ;;
  1)
    printf 'RESPONDER_WORKFLOW=%s\n' "${candidates[0]}"
    quit_by_code 0
    ;;
  *)
    # Never guess. Picking the first match silently sends every later
    # `gh run list --workflow=` query at the wrong workflow, and an empty
    # result there is indistinguishable from "the responder never ran".
    print_error "Several workflows matched /${name_pattern}/i; cannot choose between them:"
    printf '  %s\n' "${candidates[@]}" >&2
    print_error "Re-run with --pattern to narrow, or --workflow to select one."
    quit_by_code 4
    ;;
esac
