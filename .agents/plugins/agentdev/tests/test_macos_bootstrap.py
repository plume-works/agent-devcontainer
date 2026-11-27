#!/usr/bin/env python3

"""Tests for bin/macos-bootstrap.zsh, run against stubbed host tools under a scratch HOME."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess

import pytest

ZSH = shutil.which('zsh')
pytestmark = pytest.mark.skipif(ZSH is None, reason='the bootstrap runs under zsh')

MARKER_BEGIN = '# >>> agentdev macos-bootstrap >>>'
MARKER_END = '# <<< agentdev macos-bootstrap <<<'
VERSION_TOOLS = ('mise', 'jq', 'gh', 'shellcheck', 'bun', 'pre-commit', 'iwe', 'iwes')
TOOLCHAIN_URL = 'https://toolchain.example/ref'
# The host tools the script and its stubs run; nothing else on the host leaks onto PATH.
SYSTEM_TOOLS = (
    'awk',
    'basename',
    'bash',
    'cat',
    'chmod',
    'cp',
    'env',
    'install',
    'ln',
    'mkdir',
    'mktemp',
    'rm',
    'zsh',
)

LOGGING_STUB = """#!/bin/bash
printf '%s\\n' "$(basename "$0") $*" >> "$STUB_LOG"
"""

STUBS = {
    'uname': """
case "$1" in
  -s) echo "$STUB_UNAME_S" ;;
  -m) echo "$STUB_UNAME_M" ;;
  *) echo "$STUB_UNAME_S" ;;
esac
""",
    'brew': """
case "$1" in
  bundle) cat > "$STUB_DIR/brewfile" ;;
  shellenv) echo "export PATH=\\"$STUB_DIR/bin:\\$PATH\\"" ;;
esac
""",
    'curl': """
out=''
while [ $# -gt 1 ]; do
  [ "$1" = -o ] && out="$2"
  shift
done
cp "$STUB_DIR/toolchain/${1#"$STUB_TOOLCHAIN_URL"/}" "$out"
""",
    'claude': """
[ "$1" = --version ] && echo 'claude 0.0.0'
[ "$3" = list ] && echo '[]'
exit 0
""",
}

UV_STUB = """
if [ "$1" = python ] && [ "$2" = install ] && [ -n "${STUB_UV_PYTHON:-}" ]; then
  mkdir -p "$UV_PYTHON_BIN_DIR"
  printf '#!/bin/bash\\necho "Python %s"\\n' "$STUB_UV_PYTHON" > "$UV_PYTHON_BIN_DIR/python3"
  chmod +x "$UV_PYTHON_BIN_DIR/python3"
fi
[ "$1" = --version ] && echo 'uv 0.0.0'
exit 0
"""

# Stands in for scripts/install-toolchain: links the toolchain's stubs into its BIN_DIR.
INSTALL_TOOLCHAIN = """#!/bin/bash
printf '%s\\n' "install-toolchain $* MISE_ENV=${MISE_ENV:-} MISE_DATA_DIR=${MISE_DATA_DIR:-}" \\
  >> "$STUB_LOG"
mkdir -p "$1"
for tool in "$STUB_DIR"/tools/*; do ln -sf "$tool" "$1/"; done
"""

CODEX_STUB = """
[ "$1" = --version ] && echo 'codex 0.0.0'
exit 0
"""


def recorded(script: Path, name: str) -> str:
    """Return a ``typeset -r NAME=value`` constant the bootstrap records."""
    match = re.search(rf'^typeset -r {name}=(\S+)$', script.read_text(), re.MULTILINE)
    assert match, f'{name} is not recorded in {script.name}'
    return match.group(1)


@dataclass
class Host:
    """A stubbed macOS host: tool stubs on PATH, a scratch HOME, and a call log."""

    script: Path
    root: Path
    home: Path
    stub_dir: Path
    env: dict[str, str]

    def run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [ZSH, str(self.script), *args],
            env=self.env,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def calls(self, tool: str) -> list[str]:
        log = self.stub_dir / 'calls.log'
        lines = log.read_text().splitlines() if log.exists() else []
        return [line for line in lines if line.split(' ', 1)[0] == tool]

    def stub(self, name: str, body: str, where: str = 'bin') -> None:
        path = self.stub_dir / where / name
        path.write_text(LOGGING_STUB + body)
        path.chmod(0o755)

    def unstub(self, name: str) -> None:
        (self.stub_dir / 'bin' / name).unlink()


@pytest.fixture
def host(plugin_root: Path, plugin_tmp_path: Path) -> Host:
    script = plugin_root / 'bin' / 'macos-bootstrap.zsh'
    home = plugin_tmp_path / 'home'
    stub_dir = plugin_tmp_path / 'stubs'
    system = stub_dir / 'system'
    for directory in (home, stub_dir / 'bin', stub_dir / 'tools', system):
        directory.mkdir(parents=True)
    for tool in SYSTEM_TOOLS:
        (system / tool).symlink_to(shutil.which(tool))
    env = {
        'HOME': str(home),
        'PATH': f'{stub_dir / "bin"}:{system}',
        'STUB_DIR': str(stub_dir),
        'STUB_LOG': str(stub_dir / 'calls.log'),
        'STUB_UNAME_S': 'Darwin',
        'STUB_UNAME_M': 'arm64',
        'STUB_UV_PYTHON': f'{recorded(script, "PYTHON_VERSION")}.99',
        'AGENTDEV_TOOLCHAIN_URL': TOOLCHAIN_URL,
        'STUB_TOOLCHAIN_URL': TOOLCHAIN_URL,
    }
    stubbed = Host(script, plugin_tmp_path, home, stub_dir, env)
    for name, body in STUBS.items():
        stubbed.stub(name, body)
    for name in VERSION_TOOLS:
        stubbed.stub(name, f'echo "{name} 0.0.0"', where='tools')
    stubbed.stub('uv', UV_STUB, where='tools')
    toolchain = stub_dir / 'toolchain'
    (toolchain / 'scripts').mkdir(parents=True)
    (toolchain / 'scripts/install-toolchain').write_text(INSTALL_TOOLCHAIN)
    for name in ('mise.toml', 'mise.lock'):
        (toolchain / name).write_text(f'# {name}\n')
    return stubbed


def test_non_darwin_exits_before_any_installer(host: Host) -> None:
    host.env['STUB_UNAME_S'] = 'Linux'

    result = host.run()

    assert result.returncode != 0
    assert host.calls('brew') == []
    assert host.calls('uv') == []


def test_missing_brew_prints_install_command_and_changes_nothing(host: Host) -> None:
    host.unstub('brew')

    result = host.run()

    assert result.returncode != 0
    assert 'raw.githubusercontent.com/Homebrew/install/HEAD/install.sh' in result.stderr
    assert sorted(path.name for path in host.home.iterdir()) == []


def test_brew_bundle_receives_mise_and_the_claude_code_cask(host: Host) -> None:
    host.run('--skip-plugins')

    assert any(call.startswith('brew bundle --file=-') for call in host.calls('brew'))
    brewfile = (host.stub_dir / 'brewfile').read_text()
    assert re.findall(r'^(?:brew|cask) .*$', brewfile, re.MULTILINE) == [
        'brew "mise"',
        'cask "claude-code"',
    ]


def test_the_catalog_toolchain_is_fetched_and_linked_into_local_bin(host: Host) -> None:
    """
    The fetched install-toolchain gets ~/.local/bin, the catalog's list, and its own mise data.

    The user's mise housekeeping never sees that data directory, so never prunes those tools.
    """
    result = host.run('--skip-plugins')

    assert result.returncode == 0, result.stderr
    fetched = [call.split()[-1] for call in host.calls('curl')]
    assert fetched == [
        f'{TOOLCHAIN_URL}/{name}'
        for name in ('scripts/install-toolchain', 'mise.toml', 'mise.lock')
    ]
    bin_dir = host.home / '.local' / 'bin'
    data_dir = host.home / '.local/share/agentdev/mise'
    assert host.calls('install-toolchain') == [
        f'install-toolchain {bin_dir} MISE_ENV= MISE_DATA_DIR={data_dir}'
    ]
    assert (bin_dir / 'iwe').exists()


def test_a_failed_toolchain_install_stops_the_bootstrap(host: Host) -> None:
    (host.stub_dir / 'toolchain/scripts/install-toolchain').write_text('exit 4\n')

    result = host.run('--skip-plugins')

    assert result.returncode != 0
    assert host.calls('uv') == []
    assert not (host.home / '.zprofile').exists()


def test_uv_installs_the_recorded_python_as_default(host: Host) -> None:

    host.run('--skip-plugins')

    version = recorded(host.script, 'PYTHON_VERSION')
    installs = [call.split()[1:] for call in host.calls('uv') if call.startswith('uv python')]
    assert installs == [['python', 'install', version, '--default']]


def test_rerun_keeps_one_marker_block_and_preserves_other_content(host: Host) -> None:
    zprofile = host.home / '.zprofile'
    before, after = 'export EDITOR=vim\n# keep me\n', '\nalias ll="ls -l"\n'
    zprofile.write_text(before)

    host.run('--skip-plugins')
    with zprofile.open('a') as handle:
        handle.write(after)
    host.run('--skip-plugins')

    content = zprofile.read_text()
    assert content.count(MARKER_BEGIN) == 1
    assert content.count(MARKER_END) == 1
    start = content.index(MARKER_BEGIN)
    end = content.index(MARKER_END) + len(MARKER_END) + 1
    assert content[:start] == before
    assert content[end:] == after
    block = content[start:end]
    assert 'shellenv' in block
    assert '.local/bin' in block


def login_shell_stub(python3: str, version: str) -> str:
    """Body of a login shell stub that resolves ``python3`` to a fixed answer."""
    return f"""
case "$*" in
  *'command -v python3'*) echo "{python3}" ;;
  *'python3 --version'*) echo "Python {version}" ;;
esac
"""


def test_fish_on_path_gets_one_conf_d_block_and_keeps_other_content(host: Host) -> None:
    host.stub('fish', 'exit 0')
    conf = host.home / '.config' / 'fish' / 'conf.d' / 'agentdev.fish'
    conf.parent.mkdir(parents=True)
    before, after = 'set -gx EDITOR vim\n', '\nabbr -a ll ls -l\n'
    conf.write_text(before)

    host.run('--skip-plugins')
    with conf.open('a') as handle:
        handle.write(after)
    result = host.run('--skip-plugins')

    assert result.returncode == 0, result.stderr
    content = conf.read_text()
    assert content.count(MARKER_BEGIN) == 1
    assert content.count(MARKER_END) == 1
    start = content.index(MARKER_BEGIN)
    end = content.index(MARKER_END) + len(MARKER_END) + 1
    assert content[:start] == before
    assert content[end:] == after
    block = content[start:end].splitlines()
    shellenv = next(i for i, line in enumerate(block) if 'shellenv fish' in line)
    add_path = next(i for i, line in enumerate(block) if line.startswith('fish_add_path'))
    assert shellenv < add_path
    assert '.local/bin' in block[add_path]


def test_no_fish_block_without_fish(host: Host) -> None:
    host.env['SHELL'] = '/bin/zsh'

    result = host.run('--skip-plugins')

    assert result.returncode == 0, result.stderr
    assert not (host.home / '.config' / 'fish').exists()


def test_user_shell_resolving_another_python_fails_its_check(host: Host) -> None:
    host.stub('othersh', login_shell_stub('/opt/homebrew/bin/python3', '3.14.0'))
    host.env['SHELL'] = str(host.stub_dir / 'bin' / 'othersh')

    result = host.run('--skip-plugins')

    assert result.returncode != 0
    assert 'othersh' in result.stderr
    assert 'python3' in result.stderr


def test_user_shell_resolving_the_provisioned_python_passes(host: Host) -> None:
    provisioned = host.home / '.local' / 'bin' / 'python3'
    host.stub('othersh', login_shell_stub(str(provisioned), host.env['STUB_UV_PYTHON']))
    host.env['SHELL'] = str(host.stub_dir / 'bin' / 'othersh')

    result = host.run('--skip-plugins')

    assert result.returncode == 0, result.stderr
    assert any(call.startswith('othersh -l -c') for call in host.calls('othersh'))


def test_stock_python_first_on_path_fails_the_python_check(host: Host) -> None:
    del host.env['STUB_UV_PYTHON']

    result = host.run('--skip-plugins')

    assert result.returncode != 0
    assert 'python3' in result.stderr


def test_plugin_step_installs_only_agentdev(host: Host) -> None:

    result = host.run()

    assert result.returncode == 0, result.stderr
    claude = host.calls('claude')
    assert any(
        re.match(r'claude plugin marketplace add \S+/agent-devcontainer', c) for c in claude
    )
    installs = [call for call in claude if call.startswith('claude plugin install')]
    assert installs and all(' agentdev@' in call and '--scope user' in call for call in installs)
    assert host.calls('codex') == []


def test_plugin_step_never_invokes_codex_on_path(host: Host) -> None:
    host.stub('codex', CODEX_STUB)

    result = host.run()

    assert result.returncode == 0, result.stderr
    assert any(call.startswith('claude plugin install') for call in host.calls('claude'))
    assert host.calls('codex') == []


def test_skip_plugins_does_not_invoke_claude(host: Host) -> None:

    result = host.run('--skip-plugins')

    assert result.returncode == 0, result.stderr
    assert host.calls('claude') == []
