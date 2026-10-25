#!/usr/bin/env bash
set -uo pipefail
sd=.devcontainer/scripts
chk(){ local name="$1"; shift; local out; out="$(timeout 30 "$@" 2>&1)"; local rc=$?; printf '%-28s rc=%-3s %s\n' "$name" "$rc" "$(echo "$out" | head -n "${N:-1}" | tr '\n' ' ' | cut -c1-160)"; }
echo "== Toolchain =="
for t in uv bun python3 node git gh docker jq shellcheck pre-commit ruff clang-format cmake ninja ansible iwe xpra gdbus sshd codebase-memory-mcp; do
  if command -v "$t" >/dev/null; then chk "$t" bash -c "$t --version 2>/dev/null || $t -V 2>/dev/null || $t version 2>/dev/null"; else printf '%-28s MISSING\n' "$t"; fi; done
chk "uv venv python" /uv/venvs/ws-project/bin/python3 --version
chk "uv sync --check" uv sync --locked --check
echo "== AI tools =="
for t in claude codex opencode copilot gemini; do command -v "$t" >/dev/null && chk "$t" "$t" --version || printf '%-28s MISSING\n' "$t"; done
echo "== Services =="
chk "dockerd" docker info --format '{{.ServerVersion}} containers={{.Containers}} running={{.ContainersRunning}}'
chk "dbus session" gdbus call --session --dest org.freedesktop.DBus --object-path /org/freedesktop/DBus --method org.freedesktop.DBus.GetId
chk "keyring" "$sd/runtime-keyring.sh" check
chk "cbm" "$sd/runtime-cbm.sh" check
chk "xpra http :14500" curl -fsS -o /dev/null -w '%{http_code}' --max-time 5 http://127.0.0.1:14500/
chk "sshd process" pgrep -a sshd
chk "xpra process" pgrep -af xpra
chk "cbm process" pgrep -af codebase-memory
chk "opencode probe" "$sd/opencode-web-command.sh" probe
chk "mcp-gateway DNS" getent hosts mcp-gateway
chk "mcp-gateway :8811" curl -fsS -o /dev/null -w '%{http_code}' --max-time 5 http://mcp-gateway:8811/sse
chk "firewall (ENABLE=${ENABLE_FIREWALL:-})" bash -c 'sudo iptables -S 2>/dev/null | wc -l'
echo "== Auth / git =="
chk "gh auth" gh auth status
chk "git credential helper" git config --get-all credential.https://github.com.helper
chk "git user" printf '%s <%s>\n' "$(git config user.name)" "$(git config user.email)"
chk "pre-commit hook" test -x .git/hooks/pre-commit
chk "claude creds" ls "$CLAUDE_SECURESTORAGE_CONFIG_DIR"
chk "codex auth link" readlink -f /root/.codex/auth.json
chk "claude.json link" readlink -f /root/.claude.json
echo "== Network =="
chk "github.com" curl -fsS -o /dev/null -w '%{http_code}' --max-time 8 https://github.com
chk "api.anthropic.com" curl -sS -o /dev/null -w '%{http_code}' --max-time 8 https://api.anthropic.com
chk "pypi" curl -fsS -o /dev/null -w '%{http_code}' --max-time 8 https://pypi.org/simple/
