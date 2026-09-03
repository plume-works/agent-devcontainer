#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

print_error() {
  printf 'ERROR: %s\n' "$*" >&2
}

# shellcheck source=/dev/null
source "${script_dir}/../../../bin/result-codes.sh"

RESULT_CODES+=("3=STALE_FOUND" "4=NO_MAP_DOCS")

usage() {
  cat <<'HELP'
Classify every codebase-map doc (data/codebase/**/*.md) by whether the code it
describes moved after the commit it was read at.

Usage:
  stale-map-docs.sh [--library <path>]

Options:
  --library <path>  IWE library directory, relative to the repository root.
                    Default: [library].path from .iwe/config.toml, or "." when
                    the key is absent.
  -h, --help        Show this help text.

Output:
  One line per map doc, then the counts, then RESULT:
    FRESH <key>                          no commit touched any source path
    STALE <key> <commit> <n>             n commits touched a source path
    GONE <key> <source>                  a source path no longer exists
    UNKNOWN_COMMIT <key> <commit>        the pinned commit is not in this clone
    EXPIRED <key> <stale_after>          fresh, but stale_after has passed
    NO_COMMIT <key>                      frontmatter has no commit (treated as stale)
  Keys: MAP_DIR, DOC_COUNT, FRESH_COUNT, STALE_COUNT, GONE_COUNT, EXPIRED_COUNT

Results (RESULT / exit code):
  SUCCESS          0  Every map doc is fresh
  STALE_FOUND      3  At least one doc is STALE, GONE, UNKNOWN_COMMIT, NO_COMMIT, or EXPIRED
  NO_MAP_DOCS      4  The library holds no data/codebase/ docs
  PREFLIGHT_ERROR  2  Usage error, not a git repository, or no .iwe/config.toml
  SCRIPT_FAILURE   1  Unhandled error
  SIGNAL_HUP     129  Interrupted by HUP
  SIGNAL_INT     130  Interrupted by INT
  SIGNAL_TERM    143  Interrupted by TERM
HELP
}

library_override=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      quit_by_code 0
      ;;
    --library)
      [[ $# -ge 2 ]] || { print_error "Missing value for --library."; quit_by_code 2; }
      library_override="$2"
      shift 2
      ;;
    *)
      print_error "Unknown argument: $1"
      usage >&2
      quit_by_code 2
      ;;
  esac
done

if ! repo_root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  print_error "This script must be run inside a Git repository."
  quit_by_code 2
fi
cd "${repo_root}"

config_file="${repo_root}/.iwe/config.toml"
[[ -f "${config_file}" ]] || { print_error "No .iwe/config.toml at ${repo_root}; run from an IWE workspace root."; quit_by_code 2; }

library_path="${library_override}"
if [[ -z "${library_path}" ]]; then
  # The [library] table's path key; the first match wins, quotes stripped.
  library_path="$(awk '
    /^\[/ { in_library = ($0 == "[library]") }
    in_library && $1 == "path" {
      sub(/^[^=]*=[[:space:]]*/, ""); gsub(/["'"'"']/, ""); print; exit
    }' "${config_file}")"
fi
library_path="${library_path:-.}"
map_dir="${library_path%/}/data/codebase"
printf 'MAP_DIR=%s\n' "${map_dir}"

doc_files=()
if [[ -d "${map_dir}" ]]; then
  while IFS= read -r file; do
    doc_files+=("${file}")
  done < <(find "${map_dir}" -type f -name '*.md' | LC_ALL=C sort)
fi

if [[ ${#doc_files[@]} -eq 0 ]]; then
  printf 'DOC_COUNT=0\n'
  quit_by_code 4
fi

# Print the frontmatter block (between the first two --- lines) of a doc.
frontmatter_of() {
  awk 'NR == 1 && $0 != "---" { exit } NR > 1 && $0 == "---" { exit } NR > 1 { print }' "$1"
}

# Scalar value of a top-level key, quotes stripped; empty when absent.
scalar_field() {
  local key="$1"
  awk -v key="${key}" '
    $0 ~ "^" key ":" {
      sub("^" key ":[[:space:]]*", ""); gsub(/^["'"'"']|["'"'"']$/, ""); print; exit
    }'
}

# The source paths, one per line: a scalar, a flow list [a, b], or a block list.
source_paths() {
  awk '
    /^source:/ {
      value = $0; sub(/^source:[[:space:]]*/, "", value)
      if (value ~ /^\[/) {
        gsub(/[][]/, "", value); n = split(value, parts, ",")
        for (i = 1; i <= n; i++) { p = parts[i]; gsub(/^[[:space:]"'"'"']+|[[:space:]"'"'"']+$/, "", p); if (p != "") print p }
        exit
      }
      if (value != "") { gsub(/^["'"'"']|["'"'"']$/, "", value); print value; exit }
      in_list = 1; next
    }
    in_list && /^[[:space:]]*-[[:space:]]*/ {
      p = $0; sub(/^[[:space:]]*-[[:space:]]*/, "", p); gsub(/^["'"'"']|["'"'"']$/, "", p); print p; next
    }
    in_list { exit }'
}

today="$(date +%F)"
fresh_count=0
stale_count=0
gone_count=0
expired_count=0

for file in "${doc_files[@]}"; do
  key="${file%.md}"
  key="${key#"${library_path%/}"/}"
  frontmatter="$(frontmatter_of "${file}")"
  commit="$(printf '%s\n' "${frontmatter}" | scalar_field commit)"
  stale_after="$(printf '%s\n' "${frontmatter}" | scalar_field stale_after)"
  sources=()
  while IFS= read -r source_path; do
    [[ -n "${source_path}" ]] && sources+=("${source_path}")
  done < <(printf '%s\n' "${frontmatter}" | source_paths)

  if [[ -z "${commit}" ]]; then
    printf 'NO_COMMIT %s\n' "${key}"
    stale_count=$((stale_count + 1))
    continue
  fi

  missing=""
  for source_path in ${sources[@]+"${sources[@]}"}; do
    [[ -e "${source_path}" ]] || { missing="${source_path}"; break; }
  done
  if [[ -n "${missing}" ]]; then
    printf 'GONE %s %s\n' "${key}" "${missing}"
    gone_count=$((gone_count + 1))
    continue
  fi

  if ! git cat-file -e "${commit}^{commit}" 2>/dev/null; then
    printf 'UNKNOWN_COMMIT %s %s\n' "${key}" "${commit}"
    stale_count=$((stale_count + 1))
    continue
  fi

  touching=0
  if [[ ${#sources[@]} -gt 0 ]]; then
    touching="$(git log --oneline "${commit}..HEAD" -- "${sources[@]}" | wc -l | tr -d '[:space:]')"
  fi
  if [[ "${touching}" -gt 0 ]]; then
    printf 'STALE %s %s %s\n' "${key}" "${commit}" "${touching}"
    stale_count=$((stale_count + 1))
    continue
  fi

  if [[ -n "${stale_after}" && "${stale_after}" < "${today}" ]]; then
    printf 'EXPIRED %s %s\n' "${key}" "${stale_after}"
    expired_count=$((expired_count + 1))
    continue
  fi

  printf 'FRESH %s\n' "${key}"
  fresh_count=$((fresh_count + 1))
done

printf 'DOC_COUNT=%s\n' "${#doc_files[@]}"
printf 'FRESH_COUNT=%s\n' "${fresh_count}"
printf 'STALE_COUNT=%s\n' "${stale_count}"
printf 'GONE_COUNT=%s\n' "${gone_count}"
printf 'EXPIRED_COUNT=%s\n' "${expired_count}"

if [[ $((stale_count + gone_count + expired_count)) -gt 0 ]]; then
  quit_by_code 3
fi
quit_by_code 0
