#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

url=""
format="fields"
include_log=0
grep_failures=0

print_error() {
  printf 'ERROR: %s\n' "$*" >&2
}

# shellcheck source=/dev/null
source "${script_dir}/../../../bin/result-codes.sh"

RESULT_CODES+=("3=UNSUPPORTED_URL")

usage() {
  cat <<'EOF'
Parse a GitHub Actions run or job URL into fields or a gh command.

Usage:
  parse-actions-url.sh --url <github-actions-url> [--format fields|command] [--log] [--grep-failures]

Options:
  --url <url>          GitHub Actions run or job URL to parse.
  --format <mode>      Output mode: fields or command. Default: fields.
  --log                Include --log when generating a gh command.
  --grep-failures      Append the standard failure grep filter in command mode.
  -h, --help           Show this help text.

Output:
  RESULT is always the last line of stdout.
  --format fields   key=value lines: REPO, RUN_ID, and JOB_ID for a job URL
  --format command  one shell-quoted gh command line

Results (RESULT / exit code):
  SUCCESS          0  The URL was parsed and the requested output printed
  UNSUPPORTED_URL  3  The URL is not a GitHub Actions run or job URL
  PREFLIGHT_ERROR  2  Usage error: missing or unknown option, bad --format,
                      or --grep-failures without --format command
  SCRIPT_FAILURE   1  Unhandled error

Examples:
  parse-actions-url.sh --url 'https://github.com/<owner>/<repo>/actions/runs/12345678901'
  parse-actions-url.sh --url 'https://github.com/<owner>/<repo>/actions/runs/12345678901/job/23456789012?pr=42' --format command --log
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --url)
      [[ $# -ge 2 ]] || { print_error "Missing value for --url"; quit_by_code 2; }
      url="$2"
      shift 2
      ;;
    --format)
      [[ $# -ge 2 ]] || { print_error "Missing value for --format"; quit_by_code 2; }
      format="$2"
      shift 2
      ;;
    --log)
      include_log=1
      shift
      ;;
    --grep-failures)
      grep_failures=1
      shift
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

if [[ -z "$url" ]]; then
  print_error "Missing required --url argument"
  usage >&2
  quit_by_code 2
fi

if [[ "$format" != "fields" && "$format" != "command" ]]; then
  print_error "Unsupported --format value: $format"
  quit_by_code 2
fi

if [[ "$grep_failures" -eq 1 && "$format" != "command" ]]; then
  print_error "--grep-failures requires --format command"
  quit_by_code 2
fi

if [[ "$url" =~ ^https://github\.com/([^/]+)/([^/]+)/actions/runs/([0-9]+)(/attempts/[0-9]+)?(/job/([0-9]+))?([?#].*)?$ ]]; then
  repo="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
  run_id="${BASH_REMATCH[3]}"
  job_id="${BASH_REMATCH[6]:-}"
else
  print_error "Not a GitHub Actions run or job URL: $url"
  quit_by_code 3
fi

if [[ "$format" == "fields" ]]; then
  printf 'REPO=%q\n' "$repo"
  printf 'RUN_ID=%q\n' "$run_id"
  if [[ -n "$job_id" ]]; then
    printf 'JOB_ID=%q\n' "$job_id"
  fi
  quit_by_code 0
fi

command=(gh run view "$run_id" --repo "$repo")
if [[ -n "$job_id" ]]; then
  command+=(--job "$job_id")
fi
if [[ "$include_log" -eq 1 ]]; then
  command+=(--log)
fi

printf -v rendered '%q ' "${command[@]}"
rendered="${rendered% }"

if [[ "$grep_failures" -eq 1 ]]; then
  printf '%s | grep -nE %q\n' "$rendered" 'FAILED|FAILURES|AssertionError|ERROR:|Segmentation fault|test_'
else
  printf '%s\n' "$rendered"
fi

quit_by_code 0
