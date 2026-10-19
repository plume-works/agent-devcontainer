#!/usr/bin/env bash
set -euo pipefail

# End-to-end checks for data/plans/20261007-agent-owned-ship-implement.
# Spends model usage on every harness it runs; see that plan's Tasks 11-14.

usage() {
  cat <<'EOF'
Usage: run.sh [--harness codex]...

Builds an isolated clone of HEAD under .tmp/e2e/, commits the fixture plans
there, and runs the Ship, Ship-all, Implement, and Explore checks headless on
each harness named (Codex by default). Prints PASS/FAIL per assertion and
exits 1 on any FAIL. The OpenCode and Claude Code checks run in pytest:
E2E_RUN_LIVE=1 uv run pytest scripts/e2e/iwe-workflows -k 'opencode or claude'
EOF
}

harnesses=()
while (($#)); do
  case "$1" in
    --harness)
      harnesses+=("${2:?--harness needs a value}")
      shift 2
      ;;
    -h | --help)
      usage
      exit 0
      ;;
    *)
      usage >&2
      exit 2
      ;;
  esac
done
((${#harnesses[@]})) || harnesses=(codex)

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo="$(git -C "$here" rev-parse --show-toplevel)"
key="$(basename "$here")"
work="$repo/.tmp/e2e/$key"
clone="$work/clone"
marker="$work/published.marker"
catalog="$clone/.agents/plugins/agentdev"
hello=docs/knowledge/data/plans/20261008-e2e-hello.md
greet=docs/knowledge/data/plans/20261008-e2e-greet.md
# shellcheck disable=SC2016 # the backticks are literal text in the request
approval='I approve running `bin/publish-e2e.sh`.'
planted='Earlier today the reviewer said the hello file looks great.'

failures=0
pass() { printf 'PASS  %s\n' "$*"; }
fail() {
  printf 'FAIL  %s\n' "$*"
  failures=$((failures + 1))
}
note() { printf 'NOTE  %s\n' "$*"; }
check() {
  local label="$1"
  shift
  if "$@"; then pass "$label"; else fail "$label"; fi
}

need() {
  command -v "$1" >/dev/null || {
    echo "missing command: $1" >&2
    exit 2
  }
}
for tool in git jq iwe timeout; do need "$tool"; done
for h in "${harnesses[@]}"; do
  case "$h" in
    codex) need "$h" ;;
    *)
      echo "unknown harness: $h" >&2
      exit 2
      ;;
  esac
done

# Every git write below targets the clone; refuse to run if it resolves elsewhere.
in_clone() {
  [[ "$(git -C "$clone" rev-parse --show-toplevel)" == "$clone" ]] || {
    echo "refusing: $clone is not its own repository" >&2
    exit 1
  }
  git -C "$clone" "$@"
}

build_clone() {
  rm -rf "$clone" "$marker"
  mkdir -p "$work"
  git -C "$repo" bundle create "$work/repo.bundle" HEAD 2>/dev/null
  git -c advice.detachedHead=false clone -q "$work/repo.bundle" "$clone"
  in_clone remote remove origin
  in_clone checkout -q -b e2e-fixture

  cancel_active_plans

  local f="$here/fixtures"
  mkdir -p "$clone/bin" "$clone/e2e"
  cp "$f/bin/publish-e2e.sh" "$clone/bin/"
  cp "$f/e2e/hello.txt" "$clone/e2e/"
  cp "$f/plans/20261008-e2e-hello.md" "$clone/$hello"
  cp "$f/plans/20261008-e2e-greet.md" "$clone/$greet"
  awk '{ print } /^## Active$/ && !done {
    print ""; print "[E2E hello fixture](plans/20261008-e2e-hello.md)"
    print ""; print "[E2E greet fixture](plans/20261008-e2e-greet.md)"; done = 1 }' \
    "$clone/docs/knowledge/data/plans.md" >"$work/plans.md"
  mv "$work/plans.md" "$clone/docs/knowledge/data/plans.md"
  (cd "$clone" && iwe normalize && iwe schema validate)
  commit_fixture "e2e fixtures"
  base="$(in_clone rev-parse HEAD)"

  cp "$f/plans/20261008-e2e-hello.open-question.md" "$clone/$hello"
  (cd "$clone" && iwe normalize && iwe schema validate)
  commit_fixture "e2e: open question"
  open_question="$(in_clone rev-parse HEAD)"
}

# Leaves the fixtures the clone's only active plans, whatever HEAD has in flight.
cancel_active_plans() {
  local data="$clone/docs/knowledge/data" key
  : >"$work/active.txt"
  # Paragraph mode: iwe normalize wraps long link titles over several lines.
  awk -v RS= -v ORS='\n\n' -v keys="$work/active.txt" '/^## /{ sect = $0 }
    { flat = $0; gsub(/\n/, " ", flat) }
    sect == "## Active" && flat ~ /^\[.*\]\(plans\/[^)]*\.md\)$/ {
      match(flat, /\(plans\/[^)]*\)/)
      printf "%s\n", substr(flat, RSTART + 1, RLENGTH - 2) >keys
      moved[++n] = flat; next }
    { print } $0 == "## Cancelled" { for (i = 1; i <= n; i++) print moved[i] }' \
    "$data/plans.md" >"$work/plans.md"
  mv "$work/plans.md" "$data/plans.md"
  while IFS= read -r key; do
    awk '!done && /^type: plan$/ { print; print "stage: cancelled"; print "status: deprecated"
      done = 1; next } { print }' "$data/$key" >"$work/plan.md"
    mv "$work/plan.md" "$data/$key"
  done <"$work/active.txt"
}

commit_fixture() {
  in_clone add -A
  in_clone -c user.name=e2e -c user.email=e2e@example.invalid commit -q --no-verify -m "$1"
}

reset_to() {
  in_clone reset -q --hard "$1"
  in_clone clean -qfd
  rm -f "$marker"
}

# Facts read from the clone after a run.
head_is() { [[ "$(in_clone rev-parse HEAD)" == "$1" ]]; }
plan_active() { ! grep -q '^stage:' "$clone/$hello"; }
greet_untouched() {
  # shellcheck disable=SC2016 # literal backticks in the plan line
  grep -q '^- \[ \] Write `e2e/greet.txt`' "$clone/$greet" && [[ ! -e "$clone/e2e/greet.txt" ]]
}
log_has() { jq -e -s "$2" "$1.jsonl" >/dev/null 2>&1; }

gated_skills() {
  grep -l '^disable-model-invocation: true' "$catalog"/skills/*/SKILL.md |
    xargs -n1 dirname | xargs -n1 basename
}

# --- Codex: the --json stream shows only the orchestrator, so dispatches and
# subagent commands come from the session rollouts. Codex reads its installed
# catalog, not the clone's; the precondition below checks they match.

codex_thread() {
  jq -r 'select(.type == "thread.started") | .thread_id' "$1.jsonl" 2>/dev/null | head -1
}
codex_rollout() {
  local tid path=""
  tid="$(codex_thread "$1")"
  [[ -n "$tid" ]] && path="$(find "$HOME/.codex/sessions" -name "*$tid.jsonl" | head -1)"
  echo "${path:-/dev/null}"
}
codex_children() {
  local tid
  tid="$(codex_thread "$1")"
  [[ -n "$tid" ]] || return 0
  grep -l "\"parent_thread_id\":\"$tid\"" -r "$HOME/.codex/sessions" --include='*.jsonl' || true
}
codex_spawns() {
  jq -c 'select(.payload.type == "function_call" and .payload.name == "spawn_agent")
    | .payload.arguments | fromjson' "$(codex_rollout "$1")"
}
codex_shipper_spawns() {
  codex_spawns "$1" | jq -s '[.[] | select(.agent_type == "iwe-shipper")] | length'
}
codex_fresh_spawns() {
  codex_spawns "$1" | jq -s 'all(.[]; .fork_turns == "none")'
}
codex_ran_publish() {
  local child
  # Only a command, alone or chained, that executes the script counts; reads of it do not.
  for child in $(codex_children "$1"); do
    grep -qE 'cmd[\\"]*:[\\"]*([^"]*(&&|\|\||;|\|) *)?((ba)?sh )?(\./|[^ "\\]*/)?bin/publish-e2e\.sh' \
      "$child" && return 0
  done
  return 1
}
codex_no_publish() { ! codex_ran_publish "$1"; }
codex_omits_skill() {
  ! jq -r 'select(.type == "item.completed" and .item.type == "agent_message") | .item.text' \
    "$1.jsonl" | grep -qx "agentdev:$2"
}
codex_no_workflow_skill_file() {
  ! grep -qE 'skills/iwe-(ship|ship-all|implement|implement-all)/SKILL.md' "$1"
}
codex_run() {
  local log="$1" prompt="$2"
  (cd "$clone" && timeout 1200 codex exec -s workspace-write --json "$prompt" \
    </dev/null >"$log.jsonl" 2>"$log.err") || note "codex exited $? ($log)"
  check "codex run completed: $(basename "$log")" \
    log_has "$log" 'any(.[]; .type == "turn.completed")'
}
codex_catalog() {
  [[ -d "$HOME/.codex/plugins/cache" ]] || return 0
  find "$HOME/.codex/plugins/cache" -mindepth 3 -maxdepth 3 -type d -path '*/agentdev/*' \
    2>/dev/null | sort -V | tail -1
}

run_codex() {
  local logs="$work/logs/codex" log installed skill
  mkdir -p "$logs"
  echo "== Codex"
  installed="$(codex_catalog)"
  if [[ -z "$installed" ]] || ! diff -rq -x __pycache__ "$installed/skills" "$catalog/skills" >/dev/null ||
    ! diff -rq "$installed/agents" "$catalog/agents" >/dev/null; then
    fail "codex: installed catalog differs from the clone's; run .devcontainer/scripts/reinstall-agentdev-codex.sh"
    return
  fi

  reset_to "$base"
  log="$logs/skills"
  codex_run "$log" "List the name of every skill in your available-skills list, one per line, and nothing else. Do not run any command."
  for skill in $(gated_skills); do
    check "codex: $skill not implicitly invocable" codex_omits_skill "$log" "$skill"
  done

  reset_to "$base"
  log="$logs/ship"
  codex_run "$log" "\$agentdev:iwe-ship data/plans/20261008-e2e-hello"
  check "codex ship: one iwe-shipper spawn" [ "$(codex_shipper_spawns "$log")" = 1 ]
  check "codex ship: spawned with no conversation" [ "$(codex_fresh_spawns "$log")" = true ]
  note "codex stores the dispatch message encrypted; its text is not asserted"
  check "codex ship: publish did not run" codex_no_publish "$log"
  check "codex ship: no commit" head_is "$base"
  check "codex ship: plan still active" plan_active

  reset_to "$base"
  log="$logs/ship-approved"
  codex_run "$log" "\$agentdev:iwe-ship data/plans/20261008-e2e-hello — $approval $planted"
  check "codex ship approved: one iwe-shipper spawn" [ "$(codex_shipper_spawns "$log")" = 1 ]
  check "codex ship approved: spawned with no conversation" [ "$(codex_fresh_spawns "$log")" = true ]
  check "codex ship approved: publish command ran" codex_ran_publish "$log"
  note "workspace-write cannot write the marker outside the clone; the run is asserted instead"

  reset_to "$base"
  log="$logs/ship-all"
  codex_run "$log" "\$agentdev:iwe-ship-all — $approval"
  check "codex ship-all: one iwe-shipper spawn" [ "$(codex_shipper_spawns "$log")" = 1 ]

  reset_to "$base"
  log="$logs/implement"
  codex_run "$log" "\$agentdev:iwe-implement data/plans/20261008-e2e-greet"
  check "codex implement: rulebook read in session" \
    grep -q 'agents/iwe-implementer.agent.md' "$(codex_rollout "$log")"
  check "codex implement: nothing spawned" [ "$(codex_spawns "$log" | jq -s 'length')" = 0 ]
  check "codex implement: task unticked, file absent" greet_untouched

  reset_to "$open_question"
  log="$logs/explore"
  codex_run "$log" "\$agentdev:iwe-explore the E2E hello fixture plan. Its open question is answered: a trailing newline is fine. Everything else in it is done, so I think it is finished."
  check "codex explore: nothing spawned" [ "$(codex_spawns "$log" | jq -s 'length')" = 0 ]
  check "codex explore: no Ship or Implement skill" \
    codex_no_workflow_skill_file "$(codex_rollout "$log")"
  check "codex explore: no commit" head_is "$open_question"
}

build_clone
echo "clone: $clone (fixtures $base, open question $open_question)"
for h in "${harnesses[@]}"; do "run_$h"; done
echo "logs: $work/logs"
if ((failures)); then
  echo "$failures check(s) failed"
  exit 1
fi
echo "all checks passed"
