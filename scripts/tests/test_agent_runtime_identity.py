"""Container tests for runtime-bootstrap.sh: account creation and volume ownership rules."""

from __future__ import annotations

from collections.abc import Iterator
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / '.devcontainer/scripts'
BASE = 'ubuntu:24.04'
# Mirrors the account layout agent-opencode builds: no stock UID 1000 account, a docker group.
BASE_DOCKERFILE = f"""\
FROM {BASE}
RUN apt-get update && apt-get install -y --no-install-recommends sudo \\
 && rm -rf /var/lib/apt/lists/* && userdel --remove ubuntu && groupadd --system docker
"""
MOUNTS = {
    'home': '/home/agent',
    'uv': '/uv',
    'docker': '/var/lib/docker',
    'workspace': '/workspaces/project',
}
AUTH = '/var/lib/agentdev/auth'
SECRET = 'not-for-logs-7f3a'

pytestmark = pytest.mark.skipif(
    shutil.which('docker') is None
    or subprocess.run(['docker', 'info'], capture_output=True).returncode != 0,
    reason='requires a Docker daemon',
)


@pytest.fixture(scope='module')
def image() -> str:
    """Build (once per Dockerfile revision) the base the bootstrap runs on."""
    tag = f'agentdev-runtime-identity-test:{hashlib.sha256(BASE_DOCKERFILE.encode()).hexdigest()[:12]}'
    if subprocess.run(['docker', 'image', 'inspect', tag], capture_output=True).returncode:
        subprocess.run(
            ['docker', 'build', '-q', '-t', tag, '-'],
            input=BASE_DOCKERFILE,
            text=True,
            check=True,
            capture_output=True,
        )
    return tag


class Volumes:
    """Named volumes for one simulated project container plus its auth cohort."""

    def __init__(self) -> None:
        self.prefix = f'agentdev-test-{uuid4().hex[:8]}'
        self.auth = f'{self.prefix}-auth'
        self.created: list[str] = []

    def name(self, key: str) -> str:
        return f'{self.prefix}-{key}'

    def args(self, *, auth: str | None = None, **overrides: str | None) -> list[str]:
        """Return ``-v`` options; an override maps a mount key to a host path or None."""
        options = []
        for key, target in MOUNTS.items():
            source = overrides.get(key, self.name(key))
            if source is None:
                continue
            if source == self.name(key):
                self.created.append(source)
            options += ['-v', f'{source}:{target}']
        self.created.append(auth or self.auth)
        return options + ['-v', f'{auth or self.auth}:{AUTH}']

    def remove(self) -> None:
        subprocess.run(['docker', 'volume', 'rm', '-f', *set(self.created)], capture_output=True)


@pytest.fixture
def volumes() -> Iterator[Volumes]:
    box = Volumes()
    try:
        yield box
    finally:
        box.remove()


def run(
    image: str,
    mounts: list[str],
    script: str = '',
    *,
    uid: int | None = None,
    gid: int | None = None,
    extra_env: dict[str, str] | None = None,
    detach: bool = False,
):
    """Run the bootstrap in a fresh container, then ``script`` as root."""
    env = {
        'AGENTDEV_RUNTIME_MODE': 'deploy',
        'OPENCODE_SERVER_PASSWORD': SECRET,
        'GH_TOKEN': SECRET,
        **(extra_env or {}),
    }
    if uid is not None:
        env['AGENTDEV_UID'] = str(uid)
    if gid is not None:
        env['AGENTDEV_GID'] = str(gid)
    env_args = [arg for key, value in env.items() for arg in ('-e', f'{key}={value}')]
    command = [
        'docker',
        'run',
        '--rm',
        '-v',
        f'{SCRIPTS}:/opt/agentdev-runtime:ro',
        *mounts,
        *env_args,
        image,
        'bash',
        '-c',
        f'/opt/agentdev-runtime/runtime-bootstrap.sh && {script or "true"}',
    ]
    if detach:
        return subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return subprocess.run(command, capture_output=True, text=True, timeout=180)


def assert_ok(result: subprocess.CompletedProcess[str]) -> None:
    assert result.returncode == 0, result.stdout + result.stderr
    assert SECRET not in result.stdout + result.stderr


CHECKS = """
id -u agent; id -g agent; id -nG agent | tr ' ' '\\n' | grep -qx docker
su agent -c 'sudo -n true' && echo sudo-ok
stat -c '%u:%g' /home/agent /uv /workspaces/project
stat -c '%u:%g %a' /var/lib/agentdev/auth /var/lib/agentdev/auth/codex
stat -c '%u:%g %a' "${XDG_RUNTIME_DIR:-/run/user/$(id -u agent)}"
su agent -c 'test ! -r /root'  && echo root-private
"""


@pytest.mark.parametrize(('uid', 'gid'), [(None, None), (2345, 3456)])
def test_creates_the_account_and_claims_fresh_instance_storage(image, volumes, uid, gid):
    result = run(image, volumes.args(), CHECKS, uid=uid, gid=gid)
    assert_ok(result)
    want_uid, want_gid = uid or 1000, gid or 1000
    tail = result.stdout.split('runtime-bootstrap: identity')[1].splitlines()[1:]
    lines = [line for line in tail if not line.startswith('runtime-firewall:')]
    owner = f'{want_uid}:{want_gid}'
    assert lines == [
        str(want_uid),
        str(want_gid),
        'sudo-ok',
        owner,
        owner,
        owner,
        f'{owner} 700',
        f'{owner} 700',
        f'{owner} 700',
        'root-private',
    ]


@pytest.mark.parametrize('value', ['abc', '0', '-5', '1.5', '99999999999'])
def test_rejects_invalid_ids(image, volumes, value):
    result = run(image, volumes.args(), uid=None, extra_env={'AGENTDEV_UID': value})
    assert result.returncode == 1
    assert 'AGENTDEV_UID' in result.stderr


def test_rejects_a_uid_owned_by_another_account(image, volumes):
    collide = 'useradd --uid 1000 squatter && '
    command = [
        'docker',
        'run',
        '--rm',
        '-v',
        f'{SCRIPTS}:/opt/agentdev-runtime:ro',
        *volumes.args(),
        '-e',
        'AGENTDEV_RUNTIME_MODE=deploy',
        image,
        'bash',
        '-c',
        f'{collide}/opt/agentdev-runtime/runtime-bootstrap.sh',
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert result.returncode == 1
    assert 'UID 1000 already belongs to account squatter' in result.stderr


def test_reuses_a_colliding_group(image, volumes):
    command = [
        'docker',
        'run',
        '--rm',
        '-v',
        f'{SCRIPTS}:/opt/agentdev-runtime:ro',
        *volumes.args(),
        '-e',
        'AGENTDEV_RUNTIME_MODE=deploy',
        image,
        'bash',
        '-c',
        'groupadd --gid 1000 staff2 && /opt/agentdev-runtime/runtime-bootstrap.sh && id -gn agent',
    ]
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    assert_ok(result)
    assert result.stdout.strip().endswith('staff2')


def test_rejects_shared_auth_from_another_identity_without_touching_it(image, volumes):
    assert_ok(
        run(
            image,
            volumes.args(),
            f'su agent -c "echo token > {AUTH}/codex/auth.json"',
            uid=1001,
            gid=1001,
        )
    )
    other = Volumes()
    try:
        result = run(image, other.args(auth=volumes.auth))
        assert result.returncode == 1
        assert 'must all use AGENTDEV_UID=1001' in result.stderr
        inspect = run(
            image,
            other.args(auth=volumes.auth),
            f'stat -c "%u:%g" {AUTH} {AUTH}/codex/auth.json; cat {AUTH}/codex/auth.json',
            uid=1001,
            gid=1001,
        )
        assert inspect.stdout.splitlines()[-3:] == ['1001:1001', '1001:1001', 'token']
    finally:
        other.remove()


def test_concurrent_starts_share_one_initialization(image, volumes):
    others = [Volumes() for _ in range(3)]
    try:
        processes = [run(image, box.args(auth=volumes.auth), detach=True) for box in others]
        outputs = [process.communicate(timeout=180) for process in processes]
        assert [process.returncode for process in processes] == [0, 0, 0], outputs
        initialized = sum('initialized empty shared auth' in out for out, _ in outputs)
        assert initialized == 1
        check = run(
            image,
            others[0].args(auth=volumes.auth),
            f'stat -c "%u:%g %a" {AUTH} {AUTH}/claude {AUTH}/codex {AUTH}/opencode',
        )
        assert check.stdout.splitlines()[-4:] == ['1000:1000 700'] * 4
    finally:
        for box in others:
            box.remove()


def test_requires_persistent_mounts(image, volumes):
    result = run(image, volumes.args(home=None))
    assert result.returncode == 1
    assert '/home/agent is not a mounted volume' in result.stderr


@pytest.fixture
def checkout() -> Iterator[Path]:
    TMP_ROOT.mkdir(exist_ok=True)
    parent = TMP_ROOT / f'identity-checkout-{uuid4().hex[:8]}'
    repo = parent / 'repo'
    repo.mkdir(parents=True)
    (repo / 'README.md').write_text('checkout\n')
    try:
        yield repo
    finally:
        shutil.rmtree(parent, ignore_errors=True)


def test_rejects_an_unwritable_checkout_without_changing_ownership(image, volumes, checkout):
    before = {
        path: (path.stat().st_uid, path.stat().st_gid, path.stat().st_mode)
        for path in (checkout, checkout.parent, checkout / 'README.md')
    }
    result = run(image, volumes.args(workspace=str(checkout)), uid=4321, gid=4321)
    assert result.returncode == 1
    assert 'is not writable by 4321:4321' in result.stderr
    after = {
        path: (path.stat().st_uid, path.stat().st_gid, path.stat().st_mode) for path in before
    }
    assert after == before


def test_accepts_a_checkout_owned_by_the_runtime_identity(image, volumes, checkout):
    os.chown(checkout, 4321, 4321)
    result = run(
        image,
        volumes.args(workspace=str(checkout)),
        'su agent -c "touch /workspaces/project/new"',
        uid=4321,
        gid=4321,
    )
    assert_ok(result)
    assert (checkout / 'new').stat().st_uid == 4321
    assert (checkout / 'README.md').stat().st_uid == os.geteuid()


def test_restart_rewrites_nothing_and_resets_runtime_state(image, volumes):
    script = (
        f'first=$(stat -c %Z {AUTH} /home/agent); touch /run/user/1000/stale.pid; '
        '/opt/agentdev-runtime/runtime-bootstrap.sh >/tmp/second.log; '
        f'[ "$first" = "$(stat -c %Z {AUTH} /home/agent)" ] && echo unchanged; '
        'test ! -e /run/user/1000/stale.pid && echo reset; grep -c "reusing account" '
        '/tmp/second.log'
    )
    result = run(image, volumes.args(), script)
    assert_ok(result)
    assert result.stdout.splitlines()[-3:] == ['unchanged', 'reset', '1']


DEVCONTAINER_CHECKS = """
getent passwd agent >/dev/null && echo agent-created
stat -c '%u:%g' /workspaces/project /workspaces/project/file
test -e /var/lib/agentdev/auth && echo auth-created
stat -c '%u:%g %a' /var/lib/agentdev/lifecycle /run/agentdev/xdg
id -nG "$AGENTDEV_USER" | tr ' ' '\\n' | grep -qx docker && echo docker-member || true
"""


@pytest.mark.parametrize(('user', 'owner'), [('root', '0:0'), ('nobody', '65534:65534')])
def test_a_devcontainer_accepts_the_tools_account_and_workspace(image, tmp_path, user, owner):
    checkout = TMP_ROOT / f'dc-checkout-{uuid4().hex[:8]}'
    (checkout / 'nested').mkdir(parents=True)
    (checkout / 'file').write_text('keep')
    os.chown(checkout, 4242, 4242)
    os.chown(checkout / 'file', 4242, 4242)
    try:
        result = run(
            image,
            ['-v', f'{checkout}:/workspaces/project'],
            DEVCONTAINER_CHECKS,
            extra_env={
                'AGENTDEV_RUNTIME_MODE': 'devcontainer',
                'AGENTDEV_USER': user,
                'XDG_RUNTIME_DIR': '/run/agentdev/xdg',
            },
        )
        assert_ok(result)
        lines = result.stdout.splitlines()
        assert 'agent-created' not in lines and 'auth-created' not in lines
        assert '4242:4242' in lines and lines.count('4242:4242') == 2
        assert f'{owner} 755' in lines and f'{owner} 700' in lines
        assert ('docker-member' in lines) == (user != 'root')
        assert 'accepted account' in result.stdout
    finally:
        shutil.rmtree(checkout, ignore_errors=True)


def test_a_devcontainer_rejects_an_account_the_image_lacks(image):
    result = run(
        image, [], extra_env={'AGENTDEV_RUNTIME_MODE': 'devcontainer', 'AGENTDEV_USER': 'vscode'}
    )
    assert result.returncode == 1
    assert 'account vscode does not exist' in result.stderr


def test_the_bootstrap_requires_a_runtime_mode(image):
    result = run(image, [], extra_env={'AGENTDEV_RUNTIME_MODE': 'standalone'})
    assert result.returncode == 1
    assert 'AGENTDEV_RUNTIME_MODE must be deploy or devcontainer' in result.stderr
