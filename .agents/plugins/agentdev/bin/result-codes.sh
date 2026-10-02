#!/usr/bin/env bash

# Shared result-code helpers for agentdev skill scripts. This file is sourced
# by scripts under skills/*/agent-code; result names from 3 through 125 are added
# by each consuming script after it loads these defaults.

# Codes 0, 1, 2, 129, 130, and 143 mean the same thing in every skill script. A
# script declares its own workflow outcomes from 3 through 125 by appending to
# RESULT_CODES:
#
#   RESULT_CODES+=("3=NO_PR_FOUND" "4=MULTIPLE_PRS")
#
# A later entry overrides an earlier one for the same code, so a script may
# also give 2 a more specific name.
RESULT_CODES=(
  "0=SUCCESS"
  "1=SCRIPT_FAILURE"
  "2=PREFLIGHT_ERROR"
  "129=SIGNAL_HUP"
  "130=SIGNAL_INT"
  "143=SIGNAL_TERM"
)

result_emitted=0

emit_result() {
  local code="$1"
  local entry
  local result="UNKNOWN_CODE_${code}"

  for entry in ${RESULT_CODES[@]+"${RESULT_CODES[@]}"}; do
    if [[ "${entry%%=*}" == "${code}" ]]; then
      result="${entry#*=}"
    fi
  done

  result_emitted=1
  printf 'RESULT=%s\n' "${result}"
}

# Exit with `code` after naming it. Use for every terminal path, success
# included, so RESULT is always the last line of stdout.
quit_by_code() {
  emit_result "$1"
  exit "$1"
}

# A script stopped by `set -e` or a bare `exit` never reaches quit_by_code. The
# EXIT trap keeps the RESULT line total without altering the exit status.
# shellcheck disable=SC2317,SC2329
report_unhandled_exit() {
  local code=$?
  if [[ "${result_emitted}" -eq 0 ]]; then
    emit_result "${code}"
  fi
}

# Name a terminating signal, restore its default action, then re-raise it.
# Re-raising preserves real signal termination; a shell caller observes the
# conventional 128+signal status instead of a normal exit with that number.
# shellcheck disable=SC2317,SC2329
report_signal() {
  local signal_name="$1"
  local code="$2"

  if [[ "${result_emitted}" -eq 0 ]]; then
    emit_result "${code}"
  fi

  trap - "${signal_name}"
  kill -s "${signal_name}" "$$"
}

trap report_unhandled_exit EXIT
trap 'report_signal HUP 129' HUP
trap 'report_signal INT 130' INT
trap 'report_signal TERM 143' TERM
