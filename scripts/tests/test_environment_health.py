"""Regression tests for the portable environment health check."""

from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import stat
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[2]
HEALTH = REPO_ROOT / '.devcontainer/scripts/environment-health.sh'


def _executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _run_health(
    tmp_path: Path,
    *,
    mode: str = 'standalone',
    missing: frozenset[str] = frozenset(),
    fail_commands: frozenset[str] = frozenset(),
    firewall: str = 'false',
    health_timeout: str = '30',
    processes_present: bool = True,
    sleep_commands: frozenset[str] = frozenset(),
) -> subprocess.CompletedProcess[str]:
    # The script beside stub helpers, as the image installs it, run from a workspace
    # that has no copy of this repository's scripts.
    project = tmp_path / 'project'
    project.mkdir(parents=True)
    runtime = tmp_path / 'runtime'
    runtime.mkdir()
    health = runtime / HEALTH.name
    shutil.copy2(HEALTH, health)
    for name in ('runtime-keyring.sh', 'runtime-cbm.sh', 'opencode-web-command.sh'):
        _executable(runtime / name, '#!/usr/bin/env bash\nexit 0\n')

    home = tmp_path / 'home'
    codex = home / '.codex'
    claude = home / '.claude'
    shared = tmp_path / 'auth/codex'
    codex.mkdir(parents=True)
    claude.mkdir(parents=True)
    shared.mkdir(parents=True)
    (shared / 'auth.json').write_text('{}')
    (codex / 'auth.json').symlink_to(shared / 'auth.json')
    (claude / 'claude.json').write_text('{}')
    (home / '.claude.json').symlink_to(claude / 'claude.json')

    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    call_log = tmp_path / 'calls.log'
    stub = f"""#!/usr/bin/env bash
set -eu
command_name="$(basename "$0")"
printf '%s %s\\n' "$command_name" "$*" >> "{call_log}"
case ",${{FAIL_COMMANDS:-}}," in
  *",$command_name,"*) exit 9 ;;
esac
case ",${{SLEEP_COMMANDS:-}}," in
  *",$command_name,"*) sleep 2 ;;
esac
if [[ "$command_name" == pgrep && "${{PROCESSES_PRESENT:-true}}" != true ]]; then
  exit 1
fi
case "$command_name:$*" in
  "gh:auth status"*) printf '%s\\n' SHOULD_NOT_APPEAR ;;
  "git:config --get-all credential.https://github.com.helper") printf '%s\\n' 'helper-with-SECRET_VALUE' ;;
  "git:config user.name") printf '%s\\n' 'Test User' ;;
  "git:config user.email") printf '%s\\n' 'test@example.invalid' ;;
  "sudo:iptables -S OUTPUT") printf '%s\\n' '-A OUTPUT -m set --match-set allowed-domains dst -j ACCEPT' ;;
  "curl:"*) printf 200 ;;
  *) printf '%s\\n' ok ;;
esac
"""
    commands = {
        'ansible',
        'bun',
        'clang-format',
        'claude',
        'cmake',
        'codebase-memory-mcp',
        'codex',
        'copilot',
        'curl',
        'docker',
        'gdbus',
        'gemini',
        'getent',
        'gh',
        'git',
        'iwe',
        'jq',
        'ninja',
        'node',
        'opencode',
        'pgrep',
        'pre-commit',
        'python3',
        'ruff',
        'shellcheck',
        'sshd',
        'sudo',
        'uv',
        'xpra',
    }
    for command in commands:
        if command in missing:
            continue
        _executable(fake_bin / command, stub)

    env = {
        **os.environ,
        'AGENTDEV_RUNTIME_MODE': mode,
        'CLAUDE_SECURESTORAGE_CONFIG_DIR': str(claude),
        'ENABLE_FIREWALL': firewall,
        'FAIL_COMMANDS': ','.join(sorted(fail_commands)),
        'AGENTDEV_HEALTH_TIMEOUT': health_timeout,
        'HOME': str(home),
        'PATH': f'{fake_bin}:/usr/bin:/bin',
        'PROCESSES_PRESENT': str(processes_present).lower(),
        'SLEEP_COMMANDS': ','.join(sorted(sleep_commands)),
    }
    return subprocess.run(
        [health],
        cwd=project,
        env=env,
        capture_output=True,
        text=True,
        timeout=20,
    )


def test_script_is_executable_and_uses_runtime_home() -> None:
    source = HEALTH.read_text()
    assert os.access(HEALTH, os.X_OK)
    assert '/root/.codex/auth.json' not in source
    assert '/root/.claude.json' not in source
    assert '"$HOME/.codex/auth.json"' in source
    assert '"$HOME/.claude.json"' in source


def test_script_uses_uv_project_environment_instead_of_workspace_slug() -> None:
    source = HEALTH.read_text()
    assert '/uv/venvs/ws-project' not in source
    assert 'uv run --no-sync python' in source
    assert 'uv run --no-sync ruff' in source


def test_standalone_mode_skips_non_applicable_sidecars_and_redacts_auth_output(
    tmp_path: Path,
) -> None:
    result = _run_health(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert re.search(r'^mcp-gateway\s+SKIP\b', result.stdout, re.MULTILINE)
    assert re.search(r'^sshd process\s+SKIP\b', result.stdout, re.MULTILINE)
    assert 'SHOULD_NOT_APPEAR' not in result.stdout
    assert 'SECRET_VALUE' not in result.stdout
    assert 'codex auth link' in result.stdout
    assert 'PASS' in result.stdout
    assert 'Overall: PASS' in result.stdout


def test_missing_required_tool_fails_health_check(tmp_path: Path) -> None:
    result = _run_health(tmp_path, missing=frozenset({'codex'}))
    assert result.returncode == 1
    assert re.search(r'^codex\s+FAIL\s+required tool not installed$', result.stdout, re.MULTILINE)
    assert 'Overall: FAIL' in result.stdout


def test_absent_processes_fail_without_printing_command_lines(tmp_path: Path) -> None:
    result = _run_health(tmp_path, processes_present=False)
    assert result.returncode == 1
    assert re.search(r'^xpra process\s+FAIL\b', result.stdout, re.MULTILINE)
    assert re.search(r'^cbm process\s+FAIL\b', result.stdout, re.MULTILINE)
    assert 'pgrep -f' not in result.stdout


def test_command_failure_sets_aggregate_failure(tmp_path: Path) -> None:
    result = _run_health(tmp_path, fail_commands=frozenset({'codex'}))
    assert result.returncode == 1
    assert re.search(r'^codex\s+FAIL\s+rc=9', result.stdout, re.MULTILINE)
    assert 'Overall: FAIL' in result.stdout


def test_command_timeout_sets_aggregate_failure(tmp_path: Path) -> None:
    result = _run_health(
        tmp_path,
        health_timeout='0.1',
        sleep_commands=frozenset({'codex'}),
    )
    assert result.returncode == 1
    assert re.search(r'^codex\s+FAIL\s+rc=124', result.stdout, re.MULTILINE)
    assert 'Overall: FAIL' in result.stdout


def test_devcontainer_mode_checks_sidecars(tmp_path: Path) -> None:
    result = _run_health(tmp_path, mode='devcontainer')
    assert result.returncode == 0, result.stdout + result.stderr
    assert re.search(r'^sshd process\s+PASS\b', result.stdout, re.MULTILINE)
    assert re.search(r'^mcp-gateway DNS\s+PASS\b', result.stdout, re.MULTILINE)
    assert re.search(r'^mcp-gateway :8811\s+PASS\b', result.stdout, re.MULTILINE)


def test_documented_false_firewall_values_are_skipped(tmp_path: Path) -> None:
    for value in ('false', '0', 'no', 'off', ''):
        result = _run_health(tmp_path / (value or 'empty'), firewall=value)
        assert result.returncode == 0, result.stdout + result.stderr
        assert re.search(
            r'^runtime firewall\s+SKIP\s+disabled by configuration$', result.stdout, re.MULTILINE
        )


def test_enabled_firewall_requires_agent_allowlist_rule(tmp_path: Path) -> None:
    for value in ('true', '1', 'yes', 'on'):
        result = _run_health(tmp_path / value, firewall=value)
        assert result.returncode == 0, result.stdout + result.stderr
        assert re.search(r'^runtime firewall\s+PASS\b', result.stdout, re.MULTILINE)


def test_unknown_runtime_mode_and_firewall_value_fail(tmp_path: Path) -> None:
    result = _run_health(tmp_path, mode='invalid', firewall='perhaps')
    assert result.returncode == 1
    assert re.search(r'^runtime mode\s+FAIL\b', result.stdout, re.MULTILINE)
    assert re.search(r'^runtime firewall\s+FAIL\b', result.stdout, re.MULTILINE)
    assert 'Overall: FAIL' in result.stdout
