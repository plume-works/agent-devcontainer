"""Tests for the host initializer's shared auth volume, named after the host user's IDs."""

from collections.abc import Iterator
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

INIT = Path(__file__).parents[2] / '.devcontainer/devcontainer-init.sh'


@pytest.fixture
def checkout() -> Iterator[Path]:
    """Yield a git checkout holding only the init script, beside a docker stub that logs."""
    root = TMP_ROOT / f'devcontainer-init-{uuid4().hex}'
    path = root / 'checkout'
    (path / '.devcontainer').mkdir(parents=True)
    shutil.copy2(INIT, path / '.devcontainer/devcontainer-init.sh')
    subprocess.run(['git', 'init', '-q'], cwd=path, check=True)
    (root / 'bin').mkdir()
    (root / 'bin/docker').write_text(f'#!/bin/sh\necho "$*" >> "{root}/docker.log"\n')
    (root / 'bin/docker').chmod(0o755)
    yield path
    shutil.rmtree(root)


def test_the_auth_volume_is_named_after_the_host_users_uid_and_gid(checkout: Path) -> None:
    result = subprocess.run(
        ['.devcontainer/devcontainer-init.sh'],
        cwd=checkout,
        env={'PATH': f'{checkout.parent / "bin"}:{os.environ["PATH"]}', 'HOME': str(checkout)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    name = f'agentdev-agents-auth-{os.getuid()}-{os.getgid()}'
    env = dict(
        line.split('=', 1) for line in (checkout / '.devcontainer/.env').read_text().splitlines()
    )
    assert env['AGENTDEV_AUTH_VOLUME'] == name
    assert (checkout.parent / 'docker.log').read_text().splitlines() == [f'volume create {name}']


def test_two_host_users_get_separate_auth_volumes(checkout: Path) -> None:
    """Two host users on one engine never share Claude credentials."""
    stub = checkout.parent / 'bin/id'
    names = []
    for uid, gid in (('1000', '1000'), ('1001', '1002')):
        stub.write_text(f'#!/bin/sh\n[ "$1" = -u ] && echo {uid} || echo {gid}\n')
        stub.chmod(0o755)
        result = subprocess.run(
            ['.devcontainer/devcontainer-init.sh'],
            cwd=checkout,
            env={'PATH': f'{checkout.parent / "bin"}:{os.environ["PATH"]}', 'HOME': str(checkout)},
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        env = dict(
            line.split('=', 1)
            for line in (checkout / '.devcontainer/.env').read_text().splitlines()
        )
        names.append(env['AGENTDEV_AUTH_VOLUME'])
    assert names == ['agentdev-agents-auth-1000-1000', 'agentdev-agents-auth-1001-1002']
    assert (checkout.parent / 'docker.log').read_text().splitlines() == [
        f'volume create {name}' for name in names
    ]
