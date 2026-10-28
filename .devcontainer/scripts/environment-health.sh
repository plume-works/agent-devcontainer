#!/usr/bin/env bash
# Read-only health report for the devcontainer or deploy runtime; exits 1 on any FAIL.
# Run from the workspace root as the runtime user. Never prints auth output.
set -euo pipefail

# Beside this script: /opt/agentdev-runtime in the runtime images, which any workspace can use.
runtime_scripts="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
runtime_mode="${AGENTDEV_RUNTIME_MODE:-devcontainer}"
checks_passed=0
checks_failed=0
checks_skipped=0

result() {
  local name="$1" status="$2" detail="${3:-}"
  printf '%-28s %-5s %s\n' "$name" "$status" "$detail"
  case "$status" in
    PASS) ((checks_passed += 1)) ;;
    FAIL) ((checks_failed += 1)) ;;
    SKIP) ((checks_skipped += 1)) ;;
  esac
}

check() {
  local name="$1"
  shift
  local out rc
  if out="$(timeout "${AGENTDEV_HEALTH_TIMEOUT:-30}" "$@" 2>&1)"; then
    rc=0
  else
    rc=$?
  fi
  out="${out//$'\n'/ }"
  out="${out:0:160}"
  if ((rc == 0)); then
    result "$name" PASS "$out"
  else
    result "$name" FAIL "rc=$rc $out"
  fi
}

check_command() {
  local command="$1"
  shift
  if command -v "$command" >/dev/null 2>&1; then
    check "$command" "$@"
  else
    result "$command" FAIL 'required tool not installed'
  fi
}

check_link() {
  local name="$1" path="$2"
  if [[ ! -L "$path" ]]; then
    result "$name" FAIL 'not a symlink'
    return
  fi
  local target
  target="$(readlink -f "$path" 2>/dev/null || true)"
  if [[ -n "$target" && -f "$target" ]]; then
    result "$name" PASS "target=$target"
  else
    result "$name" FAIL 'symlink target is missing'
  fi
}

echo '== Runtime =='
case "$runtime_mode" in
  deploy | devcontainer) result 'runtime mode' PASS "$runtime_mode" ;;
  *) result 'runtime mode' FAIL 'expected deploy or devcontainer' ;;
esac
if [[ -x /opt/agentdev-runtime/runtime-health.sh ]]; then
  check 'runtime ready' /opt/agentdev-runtime/runtime-health.sh ready
  check 'runtime status' /opt/agentdev-runtime/runtime-health.sh status
else
  result 'runtime health' SKIP 'runtime-health.sh unavailable'
fi

echo '== Toolchain =='
for tool in uv bun python3 node git gh docker jq shellcheck pre-commit cmake ninja ansible iwe xpra codebase-memory-mcp; do
  if command -v "$tool" >/dev/null 2>&1; then
    check "$tool" "$tool" --version
  else
    result "$tool" FAIL 'required tool not installed'
  fi
done
check 'uv project python' uv run --no-sync python --version
check 'ruff' uv run --no-sync ruff --version
check 'uv sync --check' uv sync --locked --check
for tool in clang-format copilot gemini; do
  if command -v "$tool" >/dev/null 2>&1; then
    check "$tool" "$tool" --version
  else
    result "$tool" SKIP 'optional tool not installed'
  fi
done

echo '== AI tools =='
for tool in claude codex opencode; do
  check_command "$tool" "$tool" --version
done

echo '== Services =='
check 'dockerd' docker info --format '{{.ServerVersion}} containers={{.Containers}} running={{.ContainersRunning}}'
check 'dbus session' gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.GetId
check 'keyring' "$runtime_scripts/runtime-keyring.sh" check
check 'cbm' "$runtime_scripts/runtime-cbm.sh" check
check 'xpra http :14500' curl -fsS -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:14500/
check 'xpra process' bash -c "pgrep -f '[x]pra' >/dev/null"
check 'cbm process' bash -c "pgrep -f '[c]odebase-memory' >/dev/null"
check 'opencode probe' "$runtime_scripts/opencode-web-command.sh" probe
if [[ "$runtime_mode" == deploy ]]; then
  result 'sshd process' SKIP 'not used in deploy mode'
  result 'mcp-gateway' SKIP 'sidecar is not part of deploy mode'
elif [[ "$runtime_mode" == devcontainer ]]; then
  check 'sshd process' bash -c "pgrep -x sshd >/dev/null"
  check 'mcp-gateway DNS' getent hosts mcp-gateway
  check 'mcp-gateway :8811' curl -fsS -o /dev/null -w '%{http_code}' --max-time 5 http://mcp-gateway:8811/sse
else
  result 'sshd process' SKIP 'runtime mode is invalid'
  result 'mcp-gateway' SKIP 'runtime mode is invalid'
fi
case "${ENABLE_FIREWALL:-false}" in
  true | 1 | yes | on)
    check 'runtime firewall' bash -c "sudo iptables -S OUTPUT | grep -Fq -- '--match-set allowed-domains dst'"
    ;;
  false | 0 | no | off | '')
    result 'runtime firewall' SKIP 'disabled by configuration'
    ;;
  *)
    result 'runtime firewall' FAIL 'ENABLE_FIREWALL must be true or a documented false value'
    ;;
esac

echo '== Auth / git =='
check 'gh auth' bash -c 'gh auth status >/dev/null 2>&1'
if git config --get-all credential.https://github.com.helper >/dev/null 2>&1; then
  result 'git credential helper' PASS 'configured'
else
  result 'git credential helper' FAIL 'not configured'
fi
git_name="$(git config user.name 2>/dev/null || true)"
git_email="$(git config user.email 2>/dev/null || true)"
if [[ -n "$git_name" && -n "$git_email" ]]; then
  result 'git user' PASS 'name and email configured'
else
  result 'git user' FAIL 'name or email missing'
fi
if [[ -x .git/hooks/pre-commit ]]; then
  result 'pre-commit hook' PASS 'installed'
else
  result 'pre-commit hook' SKIP 'not installed'
fi
if [[ -n "${CLAUDE_SECURESTORAGE_CONFIG_DIR:-}" && -d "$CLAUDE_SECURESTORAGE_CONFIG_DIR" ]]; then
  result 'claude credentials' PASS 'credential directory present'
else
  result 'claude credentials' FAIL 'credential directory missing'
fi
check_link 'codex auth link' "$HOME/.codex/auth.json"
check_link 'claude.json link' "$HOME/.claude.json"

echo '== Network =='
check 'github.com' curl -fsS -o /dev/null -w '%{http_code}' --max-time 8 https://github.com
check 'api.anthropic.com' curl -sS -o /dev/null -w '%{http_code}' --max-time 8 https://api.anthropic.com
check 'pypi' curl -fsS -o /dev/null -w '%{http_code}' --max-time 8 https://pypi.org/simple/

echo '== Summary =='
printf 'PASS=%s FAIL=%s SKIP=%s\n' "$checks_passed" "$checks_failed" "$checks_skipped"
if ((checks_failed > 0)); then
  echo 'Overall: FAIL'
  exit 1
fi
echo 'Overall: PASS'
