#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=/dev/null
source "${script_dir}/__common.sh"

RESULT_CODES+=("3=GH_UNAVAILABLE" "4=ISSUE_NOT_FOUND")

issue_ref=""
issue_repo=""
issue_number=""
repo_root=""

usage() {
  show_help_header "Read a GitHub issue, with its comments, into ./.tmp for exploration."
  cat <<'HELP'

Usage:
  fetch-issue.sh <issue>

Arguments:
  <issue>    An issue URL, OWNER/REPO#N, #N, or N. The bare forms resolve
             against the repository in the current directory.

Options:
  -h, --help    Show this help text.

Output (key=value lines):
  RESULT, ISSUE_REPO, ISSUE_NUMBER, ISSUE_URL, ISSUE_STATE, ISSUE_TITLE,
  ISSUE_FILE
  ISSUE_FILE is a Markdown file under ./.tmp holding the title, labels, body,
  and every comment, written fresh on each run.

Results (RESULT / exit code):
  SUCCESS          0  The issue was read and written to ISSUE_FILE
  ISSUE_NOT_FOUND  4  The repository has no issue with that number
  GH_UNAVAILABLE   3  gh is missing, unauthenticated, or its API call failed
  PREFLIGHT_ERROR  2  Usage or preflight error (not a repo, unparseable ref)
  SCRIPT_FAILURE   1  Unhandled error
  SIGNAL_HUP     129  Interrupted by HUP
  SIGNAL_INT     130  Interrupted by INT
  SIGNAL_TERM    143  Interrupted by TERM
HELP
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      quit_by_code 0
      ;;
    -*)
      print_error "Unknown argument: $1"
      usage >&2
      quit_by_code 2
      ;;
    *)
      [[ -z "${issue_ref}" ]] || { print_error "Only one issue reference is accepted."; quit_by_code 2; }
      issue_ref="$1"
      shift
      ;;
  esac
done

[[ -n "${issue_ref}" ]] || { print_error "Missing issue reference."; usage >&2; quit_by_code 2; }

if ! parse_issue_ref "${issue_ref}"; then
  print_error "Unrecognized issue reference: ${issue_ref} (use a URL, OWNER/REPO#N, #N, or N)."
  quit_by_code 2
fi

require_git_repo

require_gh || quit_by_code 3

if [[ -z "${issue_repo}" ]]; then
  issue_repo="$(resolve_current_repo)" || {
    print_error "Could not resolve the current repository; pass OWNER/REPO#N or an issue URL."
    quit_by_code 3
  }
fi

# One gh call carries both the key lines and the document; the marker splits them.
# shellcheck disable=SC2016  # Go template, not shell
issue_template='ISSUE_NUMBER={{.number}}
ISSUE_URL={{.url}}
ISSUE_STATE={{.state}}
ISSUE_TITLE={{.title}}
== ISSUE ==
# {{.title}}

- Issue: {{.url}}
- State: {{.state}}
- Author: {{.author.login}}
- Labels: {{range $i, $l := .labels}}{{if $i}}, {{end}}{{$l.name}}{{end}}

## Body

{{.body}}

## Comments
{{range .comments}}
### {{.author.login}} — {{.createdAt}}

{{.body}}
{{end}}'

issue_output=""
if ! issue_output="$(gh issue view "${issue_number}" --repo "${issue_repo}" \
  --json number,title,url,state,body,author,labels,comments \
  --template "${issue_template}" 2>&1)"; then
  printf '%s\n' "${issue_output}" >&2
  if gh_output_says_not_found "${issue_output}"; then
    print_error "Issue ${issue_repo}#${issue_number} does not exist."
    quit_by_code 4
  fi
  print_error "gh issue view failed for ${issue_repo}#${issue_number}."
  quit_by_code 3
fi

tmp_dir="${repo_root}/.tmp"
mkdir -p "${tmp_dir}"
issue_file="${tmp_dir}/issue-${issue_repo//\//-}-${issue_number}.md"

printf 'ISSUE_REPO=%s\n' "${issue_repo}"
printf '%s\n' "${issue_output}" | sed '/^== ISSUE ==$/,$d'
printf '%s\n' "${issue_output}" | sed '1,/^== ISSUE ==$/d' >"${issue_file}"
printf 'ISSUE_FILE=%s\n' "${issue_file}"

quit_by_code 0
