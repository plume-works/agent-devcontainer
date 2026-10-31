#!/usr/bin/env python3

"""Tests for bin/macos-bootstrap.zsh, run against stubbed host tools under a scratch HOME."""

from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import Path
import re
import shutil
import subprocess
import tarfile

import pytest

ZSH = shutil.which('zsh')
pytestmark = pytest.mark.skipif(ZSH is None, reason='the bootstrap runs under zsh')

MARKER_BEGIN = '# >>> agentdev macos-bootstrap >>>'
MARKER_END = '# <<< agentdev macos-bootstrap <<<'
VERSION_TOOLS = ('jq', 'gh', 'shellcheck', 'bun', 'pre-commit')

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
    'uv': """
if [ "$1" = python ] && [ "$2" = install ] && [ -n "${STUB_UV_PYTHON:-}" ]; then
  mkdir -p "$UV_PYTHON_BIN_DIR"
  printf '#!/bin/bash\\necho "Python %s"\\n' "$STUB_UV_PYTHON" > "$UV_PYTHON_BIN_DIR/python3"
  chmod +x "$UV_PYTHON_BIN_DIR/python3"
fi
[ "$1" = --version ] && echo 'uv 0.0.0'
exit 0
""",
    'curl': """
out=''
while [ $# -gt 1 ]; do
  [ "$1" = -o ] && out="$2"
  shift
done
cp "$STUB_DIR/archives/$(basename "$1")" "$out"
""",
    'shasum': """
for file; do :; done
digest="$(cat "$STUB_DIR/sha256/$(basename "$file")" 2>/dev/null || printf '0%.0s' {1..64})"
echo "$digest  $file"
""",
    'claude': """
[ "$1" = --version ] && echo 'claude 0.0.0'
[ "$3" = list ] && echo '[]'
exit 0
""",
}

CODEX_STUB = """
[ "$1" = --version ] && echo 'codex 0.0.0'
exit 0
"""


def recorded(script: Path, name: str) -> str:
    """Return a ``typeset -r NAME=value`` constant the bootstrap records."""
    match = re.search(rf'^typeset -r {name}=(\S+)$', script.read_text(), re.MULTILINE)
    assert match, f'{name} is not recorded in {script.name}'
    return match.group(1)


def recorded_sha256(script: Path, key: str) -> str:
    """Return the SHA-256 the bootstrap records for one tool and architecture."""
    match = re.search(rf'^\s*{re.escape(key)} ([0-9a-f]{{64}})$', script.read_text(), re.MULTILINE)
    assert match, f'no SHA-256 recorded for {key}'
    return match.group(1)


def tarball(path: Path, members: dict[str, str]) -> None:
    """Write a flat gzip tarball of executable shell scripts."""
    with tarfile.open(path, 'w:gz') as bundle:
        for name, body in members.items():
            data = f'#!/bin/bash\n{body}\n'.encode()
            info = tarfile.TarInfo(name)
            info.size = len(data)
            info.mode = 0o755
            bundle.addfile(info, io.BytesIO(data))


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

    def stub(self, name: str, body: str) -> None:
        path = self.stub_dir / 'bin' / name
        path.write_text(LOGGING_STUB + body)
        path.chmod(0o755)

    def unstub(self, name: str) -> None:
        (self.stub_dir / 'bin' / name).unlink()

    def trust_archives(self) -> None:
        """Make the shasum stub report each archive's recorded SHA-256."""
        for archive in (self.stub_dir / 'archives').iterdir():
            key = 'iwe-arm64' if archive.name.startswith('iwe-') else 'codebase-memory-mcp-arm64'
            (self.stub_dir / 'sha256' / archive.name).write_text(recorded_sha256(self.script, key))


@pytest.fixture
def host(plugin_root: Path, plugin_tmp_path: Path) -> Host:
    script = plugin_root / 'bin' / 'macos-bootstrap.zsh'
    home = plugin_tmp_path / 'home'
    stub_dir = plugin_tmp_path / 'stubs'
    for directory in (home, stub_dir / 'bin', stub_dir / 'archives', stub_dir / 'sha256'):
        directory.mkdir(parents=True)
    env = {
        'HOME': str(home),
        'PATH': f'{stub_dir / "bin"}:/usr/bin:/bin:/usr/sbin:/sbin',
        'STUB_DIR': str(stub_dir),
        'STUB_LOG': str(stub_dir / 'calls.log'),
        'STUB_UNAME_S': 'Darwin',
        'STUB_UNAME_M': 'arm64',
        'STUB_UV_PYTHON': f'{recorded(script, "PYTHON_VERSION")}.99',
    }
    stubbed = Host(script, plugin_tmp_path, home, stub_dir, env)
    for name, body in STUBS.items():
        stubbed.stub(name, body)
    for name in VERSION_TOOLS:
        stubbed.stub(name, f'echo "{name} 0.0.0"')

    iwe = recorded(script, 'IWE_VERSION')
    tarball(
        stub_dir / 'archives' / f'{iwe}-aarch64-apple-darwin.tar.gz',
        {name: f'echo "{name} 0.0.0"' for name in ('iwe', 'iwes', 'iwec')},
    )
    tarball(
        stub_dir / 'archives' / 'codebase-memory-mcp-darwin-arm64.tar.gz',
        {'codebase-memory-mcp': 'echo "codebase-memory-mcp 0.0.0"', 'install.sh': 'exit 1'},
    )
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


def test_brew_bundle_receives_every_formula_and_the_claude_code_cask(host: Host) -> None:
    host.trust_archives()

    host.run('--skip-plugins')

    assert any(call.startswith('brew bundle --file=-') for call in host.calls('brew'))
    brewfile = (host.stub_dir / 'brewfile').read_text()
    for formula in ('uv', 'jq', 'gh', 'shellcheck', 'bun', 'pre-commit'):
        assert re.search(rf'^brew "{formula}"$', brewfile, re.MULTILINE), formula
    assert re.search(r'^cask "claude-code"$', brewfile, re.MULTILINE)


def test_uv_installs_the_recorded_python_as_default(host: Host) -> None:
    host.trust_archives()

    host.run('--skip-plugins')

    version = recorded(host.script, 'PYTHON_VERSION')
    installs = [call.split()[1:] for call in host.calls('uv') if call.startswith('uv python')]
    assert installs == [['python', 'install', version, '--default']]


def test_checksum_mismatch_rejects_the_archive(host: Host) -> None:
    result = host.run('--skip-plugins')

    assert result.returncode != 0
    assert 'SHA-256' in result.stderr
    bin_dir = host.home / '.local' / 'bin'
    assert not any(
        (bin_dir / name).exists() for name in ('iwe', 'iwes', 'iwec', 'codebase-memory-mcp')
    )


def test_only_iwe_and_iwes_are_installed_from_the_iwe_archive(host: Host) -> None:
    host.trust_archives()

    result = host.run('--skip-plugins')

    assert result.returncode == 0, result.stderr
    bin_dir = host.home / '.local' / 'bin'
    assert (bin_dir / 'iwe').exists()
    assert (bin_dir / 'iwes').exists()
    assert not (bin_dir / 'iwec').exists()
    assert (bin_dir / 'codebase-memory-mcp').exists()
    assert not (bin_dir / 'install.sh').exists()


def test_rerun_keeps_one_marker_block_and_preserves_other_content(host: Host) -> None:
    host.trust_archives()
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
    host.trust_archives()
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
    host.trust_archives()
    host.env['SHELL'] = '/bin/zsh'

    result = host.run('--skip-plugins')

    assert result.returncode == 0, result.stderr
    assert not (host.home / '.config' / 'fish').exists()


def test_user_shell_resolving_another_python_fails_its_check(host: Host) -> None:
    host.trust_archives()
    host.stub('othersh', login_shell_stub('/opt/homebrew/bin/python3', '3.14.0'))
    host.env['SHELL'] = str(host.stub_dir / 'bin' / 'othersh')

    result = host.run('--skip-plugins')

    assert result.returncode != 0
    assert 'othersh' in result.stderr
    assert 'python3' in result.stderr


def test_user_shell_resolving_the_provisioned_python_passes(host: Host) -> None:
    host.trust_archives()
    provisioned = host.home / '.local' / 'bin' / 'python3'
    host.stub('othersh', login_shell_stub(str(provisioned), host.env['STUB_UV_PYTHON']))
    host.env['SHELL'] = str(host.stub_dir / 'bin' / 'othersh')

    result = host.run('--skip-plugins')

    assert result.returncode == 0, result.stderr
    assert any(call.startswith('othersh -l -c') for call in host.calls('othersh'))


def test_stock_python_first_on_path_fails_the_python_check(host: Host) -> None:
    host.trust_archives()
    del host.env['STUB_UV_PYTHON']

    result = host.run('--skip-plugins')

    assert result.returncode != 0
    assert 'python3' in result.stderr


def test_plugin_step_installs_only_agentdev(host: Host) -> None:
    host.trust_archives()

    result = host.run()

    assert result.returncode == 0, result.stderr
    claude = host.calls('claude')
    assert any(
        re.match(r'claude plugin marketplace add \S+/agent-devcontainer', c) for c in claude
    )
    installs = [call for call in claude if call.startswith('claude plugin install')]
    assert installs and all(' agentdev@' in call and '--scope user' in call for call in installs)
    assert not any('self-improve' in call for call in claude)
    assert host.calls('codex') == []


def test_plugin_step_never_invokes_codex_on_path(host: Host) -> None:
    host.trust_archives()
    host.stub('codex', CODEX_STUB)

    result = host.run()

    assert result.returncode == 0, result.stderr
    assert any(call.startswith('claude plugin install') for call in host.calls('claude'))
    assert host.calls('codex') == []


def test_skip_plugins_does_not_invoke_claude(host: Host) -> None:
    host.trust_archives()

    result = host.run('--skip-plugins')

    assert result.returncode == 0, result.stderr
    assert host.calls('claude') == []
