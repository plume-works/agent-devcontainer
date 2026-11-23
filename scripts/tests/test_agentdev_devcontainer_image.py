"""
Dev Container acceptance for agentdev-devcontainer, through direct and derived consumers.

Runs against the explicit image in AGENTDEV_DEVCONTAINER_TEST_IMAGE with the Dev Containers
CLI, through create, repeated attach, stop/start, and rebuild.
"""

from __future__ import annotations

from collections.abc import Iterator
import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / 'scripts/tests/fixtures'
IMAGE = os.environ.get('AGENTDEV_DEVCONTAINER_TEST_IMAGE', '')
INSTALLED_PACKAGE = '/opt/uv-tools/agentdev-runtime/lib/python3*/site-packages/agentdev_runtime'
CLI = shlex.split(
    os.environ.get('AGENTDEV_DEVCONTAINER_CLI', 'bunx --bun @devcontainers/cli@0.80.2')
)
LABEL = 'agentdev.test=devcontainer-fixture'

pytestmark = pytest.mark.skipif(
    not IMAGE
    or shutil.which('docker') is None
    or subprocess.run(['docker', 'info'], capture_output=True).returncode != 0,
    reason='set AGENTDEV_DEVCONTAINER_TEST_IMAGE and provide a Docker daemon',
)


class Consumer:
    """One fixture repository opened in its own Dev Container."""

    def __init__(self, fixture: str) -> None:
        self.id = uuid4().hex[:8]
        self.workspace = TMP_ROOT / f'dc-{fixture}-{self.id}'
        shutil.copytree(FIXTURES / f'devcontainer-{fixture}', self.workspace, symlinks=True)
        for command in (['init', '-q', '-b', 'main'], ['add', '-A']):
            subprocess.run(['git', *command], cwd=self.workspace, check=True)
        subprocess.run(
            ['git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'fixture'],
            cwd=self.workspace,
            check=True,
        )
        self.labels = ['--id-label', LABEL, '--id-label', f'agentdev.test.id={self.id}']

    def cli(self, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [*CLI, *args, '--workspace-folder', str(self.workspace), *self.labels],
            capture_output=True,
            text=True,
            timeout=1200,
            env={**os.environ, 'AGENTDEV_DEVCONTAINER_TEST_IMAGE': IMAGE},
        )
        if check:
            assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
        return result

    def up(self, *args: str) -> dict:
        result = self.cli('up', *args)
        return json.loads(result.stdout.strip().splitlines()[-1])

    def container(self) -> str:
        return subprocess.run(
            ['docker', 'ps', '-aq', '--filter', f'label=agentdev.test.id={self.id}'],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()

    def exec(self, script: str, check: bool = True) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [
                'docker',
                'exec',
                '-u',
                'dev',
                '-w',
                '/workspaces/fixture',
                self.container(),
                'bash',
                '-lc',
                script,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if check:
            assert result.returncode == 0, result.stdout + result.stderr
        return result

    def boot(self) -> str:
        """Return the root bootstrap's invocation ID, new each time the container starts."""
        return self.exec(
            'systemctl show --value -p InvocationID agentdev-bootstrap.service'
        ).stdout.strip()

    def xpra(self) -> str:
        return self.exec(
            'systemctl --user is-active agentdev-xpra.service', check=False
        ).stdout.strip()

    def xpra_journal(self) -> str:
        return subprocess.run(
            [
                'docker',
                'exec',
                self.container(),
                'journalctl',
                '-b',
                '--no-pager',
                '-n',
                '80',
                '_SYSTEMD_USER_UNIT=agentdev-xpra.service',
            ],
            capture_output=True,
            text=True,
            timeout=60,
        ).stdout

    def lines(self, name: str) -> list[str]:
        path = self.workspace / name
        return path.read_text().splitlines() if path.exists() else []

    def remove(self) -> None:
        container = self.container()
        if container:
            subprocess.run(['docker', 'rm', '-f', '-v', container], capture_output=True)
        shutil.rmtree(self.workspace, ignore_errors=True)


@pytest.fixture
def consumer() -> Iterator:
    made: list[Consumer] = []

    def factory(fixture: str) -> Consumer:
        made.append(Consumer(fixture))
        return made[-1]

    yield factory
    for box in made:
        box.remove()


def assert_ready(box: Consumer, xpra: str = 'active') -> None:
    box.exec('agentdev-runtime health ready')
    box.exec('test "$(systemctl is-system-running)" = running')
    assert box.xpra() == xpra, box.xpra_journal()


def test_a_direct_consumer_gets_the_managed_runtime_without_lifecycle_scripts(consumer):
    box = consumer('direct')
    assert not (box.workspace / '.devcontainer/scripts').exists()
    box.up()
    assert_ready(box)
    # Project dependencies and pre-commit, from the create phase.
    box.exec('test -d .venv && grep -q "File generated by pre-commit" .git/hooks/pre-commit')
    # The image's environment root, on the home volume beside uv's cache.
    assert box.exec('readlink .venv').stdout.strip().startswith('/home/dev/.local/share/uv/venvs/')
    # Agent policy, the staged catalog, Xpra, and the nested engine.
    box.exec('grep -q permission "${XDG_CONFIG_HOME:-$HOME/.config}/opencode/opencode.json"')
    box.exec('grep -q agentdev "$HOME/.claude/plugins/installed_plugins.json"')
    box.exec('test -d "$AGENTDEV_CATALOG_DIR/.claude-plugin"')
    box.exec('test -z "$(find "$AGENTDEV_CATALOG_DIR" -type d -name tests)"')
    box.exec('test "$(ls -A "$AGENTDEV_CATALOG_DIR/.agents")" = plugins')
    box.exec('curl -fsS -o /dev/null http://127.0.0.1:14500/')
    box.exec(
        'mkdir -p /tmp/ctx && echo hi > /tmp/ctx/f && printf "FROM scratch\\nCOPY f /f\\n" '
        '> /tmp/ctx/Dockerfile && docker build -q -t agentdev-fixture-nested /tmp/ctx'
    )


def test_a_direct_consumer_runs_each_phase_exactly_when_specified(consumer):
    box = consumer('direct')
    box.up()
    assert box.lines('.phases') == ['created', 'started', 'attached']
    first = box.boot()

    box.up()
    assert box.lines('.phases') == ['created', 'started', 'attached', 'attached']
    assert box.boot() == first, 'attach must not restart services'

    subprocess.run(['docker', 'stop', box.container()], check=True, capture_output=True)
    box.up()
    assert box.lines('.phases')[4:] == ['started', 'attached']
    assert_ready(box)
    assert box.boot() != first
    box.exec('test -f /var/lib/agentdev/lifecycle/created')

    box.up('--remove-existing-container')
    assert box.lines('.phases')[6:] == ['created', 'started', 'attached']
    assert_ready(box)


def test_a_derived_image_keeps_the_managed_lifecycle_and_runs_its_hooks_in_order(consumer):
    box = consumer('derived')
    box.up()
    # The derived image turned Xpra off through the documented setting.
    assert_ready(box, xpra='inactive')
    assert box.exec('fixture-tool').stdout.strip() == 'fixture-tool from-the-descriptor'
    assert box.lines('.hook-phases') == [
        'created',
        'created-after',
        'started',
        'started-after',
        'attached',
        'attached-after',
    ]
    assert not (box.workspace / '.evil').exists()

    box.up()
    assert box.lines('.hook-phases')[6:] == ['attached', 'attached-after']
    subprocess.run(['docker', 'stop', box.container()], check=True, capture_output=True)
    box.up()
    assert box.lines('.hook-phases')[8:] == [
        'started',
        'started-after',
        'attached',
        'attached-after',
    ]
    box.up('--remove-existing-container')
    assert box.lines('.hook-phases')[12:] == [
        'created',
        'created-after',
        'started',
        'started-after',
        'attached',
        'attached-after',
    ]
    assert not (box.workspace / '.evil').exists()


@pytest.mark.parametrize(
    'change',
    [
        f"for d in {INSTALLED_PACKAGE}; do echo '# patched' >> $d/health.py; done",
        f'for d in {INSTALLED_PACKAGE}; do touch $d/extra.py; done',
    ],
)
def test_a_derived_image_cannot_replace_the_managed_runtime(change):
    tag = f'agentdev-devcontainer-tampered:{uuid4().hex[:8]}'
    subprocess.run(
        ['docker', 'build', '-q', '-t', tag, '-'],
        input=f'FROM {IMAGE}\nRUN {change}\n',
        text=True,
        check=True,
        capture_output=True,
    )
    container = subprocess.run(
        ['docker', 'run', '-d', '--privileged', '--label', LABEL, tag],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    try:
        # The failed bootstrap keeps the engine down; the container stays up for its journal.
        waited = subprocess.run(
            [
                'docker',
                'exec',
                container,
                'bash',
                '-c',
                'for _ in $(seq 240); do systemctl is-failed -q agentdev-bootstrap && exit 0; '
                'sleep 0.5; done; exit 1',
            ],
            capture_output=True,
            timeout=300,
        )
        journal = subprocess.run(
            ['docker', 'exec', container, 'journalctl', '-u', 'agentdev-bootstrap', '--no-pager'],
            capture_output=True,
            text=True,
        ).stdout
        assert waited.returncode == 0, journal
        assert 'extend the runtime through /etc/agentdev/hooks' in journal
        assert subprocess.run(
            ['docker', 'exec', container, 'systemctl', 'is-active', '-q', 'docker'],
            capture_output=True,
        ).returncode
    finally:
        subprocess.run(['docker', 'rm', '-f', '-v', container], capture_output=True)
        subprocess.run(['docker', 'image', 'rm', '-f', tag], capture_output=True)


def test_the_image_gives_the_dev_account_its_home_and_a_home_volume():
    home = subprocess.run(
        [
            'docker',
            'run',
            '--rm',
            '--entrypoint',
            'sh',
            IMAGE,
            '-c',
            'stat -c "%U:%G" /home/dev && getent passwd dev',
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert home == ['dev:dev', 'dev:x:1000:1000::/home/dev:/bin/bash']
    label = subprocess.run(
        [
            'docker',
            'image',
            'inspect',
            IMAGE,
            '--format',
            '{{index .Config.Labels "devcontainer.metadata"}}',
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    metadata = json.loads(label)[0]
    assert metadata['remoteUser'] == 'dev'
    assert metadata['updateRemoteUserUID'] is True
    assert {
        'source': 'agentdev-home-${devcontainerId}',
        'target': '/home/dev',
        'type': 'volume',
    } in metadata['mounts']


@pytest.mark.skipif(
    os.getuid() in (0, 1000), reason='the remap needs a host UID other than root and 1000'
)
def test_the_dev_account_is_remapped_to_the_host_user_who_owns_the_checkout(consumer):
    box = consumer('direct')
    assert box.workspace.stat().st_uid == os.getuid()
    box.up('--skip-post-create')
    result = subprocess.run(
        [
            *CLI,
            'exec',
            '--workspace-folder',
            str(box.workspace),
            *box.labels,
            'sh',
            '-c',
            'id -u; id -g; stat -c "%u:%g" "$HOME"',
        ],
        capture_output=True,
        text=True,
        timeout=300,
        env={**os.environ, 'AGENTDEV_DEVCONTAINER_TEST_IMAGE': IMAGE},
    )
    assert result.returncode == 0, result.stdout + result.stderr
    uid, gid = os.getuid(), os.getgid()
    assert result.stdout.split()[-3:] == [str(uid), str(gid), f'{uid}:{gid}']


def test_an_interactive_shell_on_a_new_home_volume_gets_the_image_shell_setup():
    volume = f'agentdev-test-home-{uuid4().hex[:8]}'
    script = (
        'mkdir -p ~/.bun/bin; '
        'bash -ic \'echo "$HISTSIZE"; echo "$PATH"\' 2>/dev/null; fish -c \'string join : $PATH\''
    )
    try:
        result = subprocess.run(
            [
                'docker',
                'run',
                '--rm',
                '--label',
                LABEL,
                '-u',
                'dev',
                '--entrypoint',
                'bash',
                '-v',
                f'{volume}:/home/dev',
                IMAGE,
                '-c',
                script,
            ],
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        history, bash_path, fish_path = result.stdout.splitlines()[-3:]
        assert history == '100000'
        assert {'/home/dev/.local/bin', '/home/dev/.bun/bin'} <= set(bash_path.split(':'))
        assert '/home/dev/.bun/bin' in fish_path.split(':')
    finally:
        subprocess.run(['docker', 'volume', 'rm', '-f', volume], capture_output=True)
