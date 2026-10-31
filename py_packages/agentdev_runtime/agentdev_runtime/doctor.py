"""
Read-only health report for the devcontainer or deploy runtime; exits 1 on any FAIL.

Run from the workspace root as the runtime user. It never prints auth output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
import shutil
import subprocess
import sys

from agentdev_runtime import settings as env

# The hooks in a checkout's .pre-commit-config.yaml run these as `language: system` binaries.
REQUIRED_TOOLS = (
    'uv',
    'bun',
    'python3',
    'node',
    'git',
    'gh',
    'docker',
    'jq',
    'shellcheck',
    'pre-commit',
    'gitleaks',
    'actionlint',
    'cmake',
    'ninja',
    'ansible',
    'iwe',
    'xpra',
    'codebase-memory-mcp',
)
# gitleaks prints its version through a subcommand; every other tool takes --version.
VERSION_ARGS = {'gitleaks': ('version',)}
OPTIONAL_TOOLS = ('clang-format', 'copilot', 'gemini')
AI_TOOLS = ('claude', 'codex', 'opencode')
DETAIL_LIMIT = 160
FALSE_WORDS = {'false', '0', 'no', 'off', ''}
TRUE_WORDS = {'true', '1', 'yes', 'on'}


@dataclass
class Report:
    timeout: float
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    lines: list[str] = field(default_factory=list)

    def result(self, name: str, status: str, detail: str = '') -> None:
        print(f'{name:<28} {status:<5} {detail}', flush=True)
        if status == 'PASS':
            self.passed += 1
        elif status == 'FAIL':
            self.failed += 1
        elif status == 'SKIP':
            self.skipped += 1

    def check(self, name: str, *command: str) -> None:
        """Run ``command`` within the timeout; PASS on exit 0 with its output trimmed."""
        try:
            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                errors='replace',
                timeout=self.timeout,
                check=False,
            )
            code, output = result.returncode, result.stdout
        except subprocess.TimeoutExpired:
            code, output = 124, ''
        except OSError as error:
            code, output = 127, str(error)
        output = output.rstrip('\n').replace('\n', ' ')[:DETAIL_LIMIT]
        if code == 0:
            self.result(name, 'PASS', output)
        else:
            self.result(name, 'FAIL', f'rc={code} {output}')

    def check_command(self, tool: str, *command: str) -> None:
        if shutil.which(tool):
            self.check(tool, *command)
        else:
            self.result(tool, 'FAIL', 'required tool not installed')

    def check_link(self, name: str, path: Path) -> None:
        if not path.is_symlink():
            self.result(name, 'FAIL', 'not a symlink')
            return
        target = path.resolve()
        if target.is_file():
            self.result(name, 'PASS', f'target={target}')
        else:
            self.result(name, 'FAIL', 'symlink target is missing')


def git_config(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(['git', 'config', *args], capture_output=True, text=True, check=False)


def runtime(report: Report, mode: str) -> None:
    print('== Runtime ==')
    if mode in env.PROFILES:
        report.result('runtime mode', 'PASS', mode)
    else:
        report.result('runtime mode', 'FAIL', 'expected deploy or devcontainer')
    if shutil.which('agentdev-runtime'):
        report.check('runtime ready', 'agentdev-runtime', 'health', 'ready')
        report.check('runtime status', 'agentdev-runtime', 'health', 'status')
    else:
        report.result('runtime health', 'SKIP', 'agentdev-runtime unavailable')


def toolchain(report: Report) -> None:
    print('== Toolchain ==')
    for tool in REQUIRED_TOOLS:
        report.check_command(tool, tool, *VERSION_ARGS.get(tool, ('--version',)))
    report.check('uv project python', 'uv', 'run', '--no-sync', 'python', '--version')
    report.check('ruff', 'uv', 'run', '--no-sync', 'ruff', '--version')
    report.check('uv sync --check', 'uv', 'sync', '--locked', '--check')
    for tool in OPTIONAL_TOOLS:
        if shutil.which(tool):
            report.check(tool, tool, '--version')
        else:
            report.result(tool, 'SKIP', 'optional tool not installed')


def ai_tools(report: Report) -> None:
    print('== AI tools ==')
    for tool in AI_TOOLS:
        report.check_command(tool, tool, '--version')


def gateway(report: Report) -> None:
    """Check the mcp-gateway sidecar when Compose was asked to start it."""
    # Compose starts it only under the opt-in profile devcontainer-init.sh enables.
    if 'mcp' not in os.environ.get('COMPOSE_PROFILES', '').split(','):
        report.result('mcp-gateway', 'SKIP', 'the mcp Compose profile is not enabled')
        return
    report.check('mcp-gateway DNS', 'getent', 'hosts', 'mcp-gateway')
    report.check(
        'mcp-gateway :8811',
        'curl',
        '-fsS',
        '-o',
        '/dev/null',
        '-w',
        '%{http_code}',
        '--max-time',
        '5',
        'http://mcp-gateway:8811/sse',
    )


def services(report: Report, mode: str, firewall: str) -> None:
    print('== Services ==')
    report.check(
        'dockerd',
        'docker',
        'info',
        '--format',
        '{{.ServerVersion}} containers={{.Containers}} running={{.ContainersRunning}}',
    )
    report.check(
        'dbus session',
        'gdbus',
        'call',
        '--session',
        '--dest',
        'org.freedesktop.DBus',
        '--object-path',
        '/org/freedesktop/DBus',
        '--method',
        'org.freedesktop.DBus.GetId',
    )
    report.check('keyring', 'agentdev-runtime', 'keyring', 'check')
    report.check('cbm', 'agentdev-runtime', 'cbm', 'check')
    report.check(
        'xpra http :14500',
        'curl',
        '-fsS',
        '-o',
        '/dev/null',
        '-w',
        '%{http_code}',
        '--max-time',
        '5',
        'http://127.0.0.1:14500/',
    )
    report.check('xpra process', 'bash', '-c', "pgrep -f '[x]pra' >/dev/null")
    report.check('cbm process', 'bash', '-c', "pgrep -f '[c]odebase-memory' >/dev/null")
    report.check('opencode probe', 'agentdev-runtime', 'opencode', 'probe')
    if mode == env.DEPLOY:
        report.result('sshd process', 'SKIP', 'not used in deploy mode')
        report.result('mcp-gateway', 'SKIP', 'sidecar is not part of deploy mode')
    elif mode == env.DEVCONTAINER:
        report.check('sshd process', 'bash', '-c', 'pgrep -x sshd >/dev/null')
        gateway(report)
    else:
        report.result('sshd process', 'SKIP', 'runtime mode is invalid')
        report.result('mcp-gateway', 'SKIP', 'runtime mode is invalid')
    if firewall in TRUE_WORDS:
        report.check(
            'runtime firewall',
            'bash',
            '-c',
            "sudo iptables -S OUTPUT | grep -Fq -- '--match-set allowed-domains dst'",
        )
    elif firewall in FALSE_WORDS:
        report.result('runtime firewall', 'SKIP', 'disabled by configuration')
    else:
        report.result(
            'runtime firewall', 'FAIL', 'ENABLE_FIREWALL must be true or a documented false value'
        )


def auth(report: Report, settings: env.Settings) -> None:
    print('== Auth / git ==')
    report.check('gh auth', 'bash', '-c', 'gh auth status >/dev/null 2>&1')
    if git_config('--get-all', 'credential.https://github.com.helper').returncode == 0:
        report.result('git credential helper', 'PASS', 'configured')
    else:
        report.result('git credential helper', 'FAIL', 'not configured')
    # git var resolves identity as a commit would, including GIT_AUTHOR_* and GIT_COMMITTER_*.
    roles = ('GIT_AUTHOR_IDENT', 'GIT_COMMITTER_IDENT')
    identities = [
        subprocess.run(['git', 'var', role], capture_output=True, check=False) for role in roles
    ]
    if all(result.returncode == 0 for result in identities):
        report.result('git user', 'PASS', 'name and email configured')
    else:
        report.result('git user', 'FAIL', 'name or email missing')
    hook = Path('.git/hooks/pre-commit')
    if hook.is_file() and os.access(hook, os.X_OK):
        report.result('pre-commit hook', 'PASS', 'installed')
    else:
        report.result('pre-commit hook', 'SKIP', 'not installed')
    secure = settings.raw('CLAUDE_SECURESTORAGE_CONFIG_DIR')
    if secure and Path(secure).is_dir():
        report.result('claude credentials', 'PASS', 'credential directory present')
    else:
        report.result('claude credentials', 'FAIL', 'credential directory missing')
    home = Path(os.environ.get('HOME') or Path.home())
    report.check_link('codex auth link', home / '.codex/auth.json')
    report.check_link('claude.json link', home / '.claude.json')


def network(report: Report) -> None:
    print('== Network ==')
    for name, flags, url in (
        ('github.com', '-fsS', 'https://github.com'),
        ('api.anthropic.com', '-sS', 'https://api.anthropic.com'),
        ('pypi', '-fsS', 'https://pypi.org/simple/'),
    ):
        report.check(
            name, 'curl', flags, '-o', '/dev/null', '-w', '%{http_code}', '--max-time', '8', url
        )


def main(argv: list[str]) -> int:
    if argv:
        print('usage: agentdev-runtime doctor', file=sys.stderr)
        return 2
    settings = env.Settings()
    mode = settings.raw('AGENTDEV_RUNTIME_MODE') or env.DEVCONTAINER
    report = Report(timeout=float(settings.get('AGENTDEV_HEALTH_TIMEOUT')))
    runtime(report, mode)
    toolchain(report)
    ai_tools(report)
    services(report, mode, settings.get('ENABLE_FIREWALL'))
    auth(report, settings)
    network(report)
    print('== Summary ==')
    print(f'PASS={report.passed} FAIL={report.failed} SKIP={report.skipped}')
    if report.failed:
        print('Overall: FAIL')
        return 1
    print('Overall: PASS')
    return 0
