#!/usr/bin/env bash

set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

print_error() {
  printf 'ERROR: %s\n' "$*" >&2
}

# shellcheck source=/dev/null
source "${script_dir}/../../../bin/result-codes.sh"

RESULT_CODES+=(
  "3=MISSING_DEPENDENCY"
  "4=ALREADY_INITIALIZED"
  "5=RECONCILIATION_REQUIRED"
  "6=VALIDATION_FAILED"
)

assets_dir="$(cd -- "${script_dir}/.." && pwd)/assets"
transaction_name=".iwe-bootstrap.txn"
owner_mark="iwe-bootstrap transaction"
workspace_path="docs/knowledge"
# The two trees bootstrap owns; everything else in the repository is left alone.
managed_dirs=(".iwe" "docs/knowledge")

usage() {
  cat <<'EOF'
Install the blank IWE workspace this skill ships into a repository root.

Usage:
  bootstrap-iwe.sh [--root <dir>]

Options:
  --root <dir>  Repository root to initialize. Default: the git top level of
                the current directory
  -h, --help    Show this help text.

Bootstrap writes only .iwe/ and docs/knowledge/, and only when both are absent.
It stages the scaffold in <root>/.iwe-bootstrap.txn/, validates it with iwe, and
then moves it into place; an interrupted run leaves that directory behind, and
the next run discards or completes it.

Output (key=value lines):
  RESULT, ROOT
  After recovering an interrupted run also: RECOVERED_TRANSACTION
    (discarded | completed)
  On RECONCILIATION_REQUIRED also: one CONFLICT=<reason>:<path> per conflict,
    reason one of missing, not-a-directory, incompatible-config, invalid,
    foreign-transaction, collision
  On SUCCESS also: NEXT_SKILLS (the onboarding skills to run, in order)

Results (RESULT / exit code):
  SUCCESS                  0  The scaffold was installed and validated
  MISSING_DEPENDENCY       3  The iwe CLI is not on PATH; nothing was written
  ALREADY_INITIALIZED      4  A complete, valid workspace is present; nothing
                              was written
  RECONCILIATION_REQUIRED  5  A managed path exists but is not the complete
                              scaffold; nothing was written
  VALIDATION_FAILED        6  The staged scaffold failed iwe validation;
                              nothing was written
  PREFLIGHT_ERROR          2  Bad usage, a missing root, or a missing scaffold
  SCRIPT_FAILURE           1  Unhandled error
  SIGNAL_HUP             129  Interrupted by HUP
  SIGNAL_INT             130  Interrupted by INT
  SIGNAL_TERM            143  Interrupted by TERM
EOF
}

root=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --root)
      [[ $# -ge 2 ]] || {
        print_error "Missing value for --root"
        usage >&2
        quit_by_code 2
      }
      root="$2"
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

if [[ -n "${root}" ]]; then
  if [[ ! -d "${root}" ]]; then
    print_error "Repository root '${root}' is not a directory."
    quit_by_code 2
  fi
elif ! root="$(git rev-parse --show-toplevel 2>/dev/null)"; then
  print_error "The current directory is not inside a git repository; pass --root <dir>."
  quit_by_code 2
fi
root="$(cd -- "${root}" && pwd -P)"
printf 'ROOT=%s\n' "${root}"

if [[ ! -f "${assets_dir}/.iwe/config.toml" || ! -d "${assets_dir}/${workspace_path}/data" ]]; then
  print_error "The packaged scaffold is missing from ${assets_dir}; reinstall the agentdev catalog."
  quit_by_code 2
fi

if ! command -v iwe >/dev/null 2>&1; then
  print_error "The iwe CLI is not on PATH; install it (https://iwe.md/quick-start/) and rerun."
  quit_by_code 3
fi

transaction="${root}/${transaction_name}"
conflicts=()

add_conflict() {
  conflicts+=("$1:$2")
}

report_conflicts() {
  local entry
  for entry in "${conflicts[@]}"; do
    printf 'CONFLICT=%s\n' "${entry}"
  done
  print_error "Bootstrap found existing state it does not own; nothing was changed."
  print_error "Reconcile each CONFLICT path with the user before installing the scaffold."
}

path_exists() {
  [[ -e "$1" || -L "$1" ]]
}

write_phase() {
  printf '%s\nphase=%s\n' "${owner_mark}" "$1" >"${transaction}/OWNER.next"
  mv "${transaction}/OWNER.next" "${transaction}/OWNER"
}

# Removes OWNER last, so a partial discard never leaves owned files without their mark.
discard_transaction() {
  find "${transaction}" -mindepth 1 -maxdepth 1 ! -name OWNER -exec rm -rf {} +
  rm -rf "${transaction}"
}

# mkdir and the first OWNER rename are not atomic together; nothing is staged before it.
holds_only_first_owner_write() {
  local entries pending="${transaction}/OWNER.next"
  entries="$(ls -A "${transaction}")"
  [[ -z "${entries}" ]] && return 0
  [[ "${entries}" == "OWNER.next" && -f "${pending}" && ! -L "${pending}" ]] || return 1
  [[ ! -s "${pending}" || "$(head -n 1 "${pending}")" == "${owner_mark}" ]]
}

transaction_phase() {
  local owner="${transaction}/OWNER"
  [[ ! -L "${transaction}" && -d "${transaction}" ]] || return 1
  if holds_only_first_owner_write; then
    printf 'staging\n'
    return 0
  fi
  [[ -f "${owner}" && "$(head -n 1 "${owner}")" == "${owner_mark}" ]] || return 1
  sed -n 's/^phase=//p' "${owner}"
}

# Moving a staged tree requires its destination to still be absent.
check_staged_destinations() {
  local item
  for item in "${managed_dirs[@]}"; do
    if path_exists "${transaction}/stage/${item}" && path_exists "${root}/${item}"; then
      add_conflict collision "${item}"
    fi
  done
  if path_exists "${root}/docs" && [[ -L "${root}/docs" || ! -d "${root}/docs" ]]; then
    add_conflict not-a-directory docs
  fi
}

move_staged() {
  local item
  for item in "${managed_dirs[@]}"; do
    if path_exists "${transaction}/stage/${item}"; then
      mkdir -p "$(dirname -- "${root}/${item}")"
      mv "${transaction}/stage/${item}" "${root}/${item}"
    fi
  done
  discard_transaction
}

recovered=""
if path_exists "${transaction}"; then
  phase="$(transaction_phase)" || phase="foreign"
  case "${phase}" in
    staging)
      discard_transaction
      recovered="discarded"
      ;;
    committing)
      check_staged_destinations
      if [[ ${#conflicts[@]} -gt 0 ]]; then
        report_conflicts
        quit_by_code 5
      fi
      move_staged
      recovered="completed"
      ;;
    *)
      add_conflict foreign-transaction "${transaction_name}"
      report_conflicts
      quit_by_code 5
      ;;
  esac
  printf 'RECOVERED_TRANSACTION=%s\n' "${recovered}"
fi

configured_workspace_path() {
  awk '
    /^\[/ { in_workspace = ($0 == "[workspace]") ; next }
    in_workspace && /^path[[:space:]]*=/ {
      value = $0
      sub(/^path[[:space:]]*=[[:space:]]*"/, "", value)
      sub(/".*$/, "", value)
      print value
      exit
    }
  ' "$1"
}

# Structural files a complete workspace keeps; documents under data/ subdirectories
# are project content that onboarding deletes or rewrites.
required_files() {
  (cd -- "${assets_dir}" && find . -type f) |
    sed 's#^\./##' |
    grep -v "^${workspace_path}/data/[^/]*/" |
    sort
}

for item in .iwe docs docs/knowledge; do
  if path_exists "${root}/${item}" && [[ -L "${root}/${item}" || ! -d "${root}/${item}" ]]; then
    add_conflict not-a-directory "${item}"
    break
  fi
done

present=0
for item in "${managed_dirs[@]}"; do
  if path_exists "${root}/${item}"; then
    present=1
  fi
done

if [[ ${#conflicts[@]} -eq 0 && "${present}" -eq 1 ]]; then
  for item in "${managed_dirs[@]}"; do
    path_exists "${root}/${item}" || add_conflict missing "${item}"
  done
  while IFS= read -r file; do
    top="${managed_dirs[0]}"
    [[ "${file}" == "${managed_dirs[1]}/"* ]] && top="${managed_dirs[1]}"
    path_exists "${root}/${top}" || continue
    if [[ -L "${root}/${file}" || ! -f "${root}/${file}" ]]; then
      add_conflict missing "${file}"
    fi
  done < <(required_files)
  config="${root}/.iwe/config.toml"
  if [[ -f "${config}" && ! -L "${config}" ]] &&
    [[ "$(configured_workspace_path "${config}")" != "${workspace_path}" ]]; then
    add_conflict incompatible-config .iwe/config.toml
  fi
  if [[ ${#conflicts[@]} -eq 0 ]]; then
    if ! (cd -- "${root}" && iwe schema validate) >&2; then
      add_conflict invalid "${workspace_path}"
    fi
  fi
  if [[ ${#conflicts[@]} -gt 0 ]]; then
    report_conflicts
    quit_by_code 5
  fi
  if [[ "${recovered}" == "completed" ]]; then
    printf 'NEXT_SKILLS=iwe-setup iwe-map\n'
    quit_by_code 0
  fi
  printf 'The workspace at %s is already initialized.\n' "${root}" >&2
  quit_by_code 4
fi

if [[ ${#conflicts[@]} -gt 0 ]]; then
  report_conflicts
  quit_by_code 5
fi

printf 'Staging the scaffold in %s...\n' "${transaction}" >&2
mkdir "${transaction}"
write_phase staging
mkdir -p "${transaction}/stage/docs"
cp -R "${assets_dir}/.iwe" "${transaction}/stage/.iwe"
cp -R "${assets_dir}/${workspace_path}" "${transaction}/stage/${workspace_path}"

validated=1
if ! (cd -- "${transaction}/stage" && iwe schema validate) >&2; then
  print_error "The staged scaffold fails 'iwe schema validate'."
  validated=0
else
  cp -R "${transaction}/stage" "${transaction}/check"
  if ! (cd -- "${transaction}/check" && iwe normalize) >&2; then
    print_error "'iwe normalize' failed on the staged scaffold."
    validated=0
  elif ! diff -r "${transaction}/stage" "${transaction}/check" >&2; then
    print_error "The staged scaffold is not in 'iwe normalize' form."
    validated=0
  fi
fi
if [[ "${validated}" -eq 0 ]]; then
  discard_transaction
  quit_by_code 6
fi
rm -rf "${transaction}/check"

write_phase committing
move_staged
printf 'Installed .iwe/ and docs/knowledge/ in %s.\n' "${root}" >&2
printf 'NEXT_SKILLS=iwe-setup iwe-map\n'
quit_by_code 0
