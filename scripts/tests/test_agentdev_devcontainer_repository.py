"""
This repository's own Dev Container on agentdev-devcontainer: catalog and state boundaries.

Opens an ordinary clone and a Git worktree of HEAD with the Dev Containers CLI, pinned to
AGENTDEV_DEVCONTAINER_TEST_IMAGE, through reload, restart, and rebuild.
"""

from __future__ import annotations

from collections.abc import Iterator
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
from uuid import uuid4

import pytest
from test_agentdev_devcontainer_image import CLI, IMAGE, pytestmark, TMP_ROOT  # noqa: F401

REPO_ROOT = Path(__file__).resolve().parents[2]
PINS = 'devcontainer-compose-pins.yml'


class Checkout:
    """One clone or worktree of HEAD, opened in this repository's Dev Container."""

    def __init__(self, kind: str) -> None:
        self.id = uuid4().hex[:8]
        self.path = TMP_ROOT / f'dc-repo-{self.id}' / f'agentdev-{kind}-{self.id}'
        self.path.parent.mkdir(parents=True)
        self.kind = kind
        if kind == 'clone':
            subprocess.run(['git', 'clone', '-q', str(REPO_ROOT), str(self.path)], check=True)
        else:
            subprocess.run(
                ['git', '-C', str(REPO_ROOT), 'worktree', 'add', '-q', '--detach', str(self.path)],
                check=True,
            )
        pins = self.path / PINS
        pins.write_text(re.sub(r'image: \S+', f'image: {IMAGE}', pins.read_text()))
        self.container = ''

    @property
    def workspace(self) -> str:
        return f'/workspaces/{self.path.name}'

    def up(self, *args: str) -> dict:
        result = subprocess.run(
            [*CLI, 'up', '--workspace-folder', str(self.path), *args],
            capture_output=True,
            text=True,
            timeout=2400,
        )
        assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
        outcome = json.loads(result.stdout.strip().splitlines()[-1])
        self.container = outcome['containerId']
        return outcome

    def sh(self, script: str) -> str:
        result = subprocess.run(
            ['docker', 'exec', '-w', self.workspace, self.container, 'bash', '-lc', script],
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout.strip()

    def startup_id(self) -> str:
        return self.sh('jq -r .startup_id /run/agentdev/state.json')

    def remove(self) -> None:
        project = f'{self.path.name}_devcontainer'.lower()
        label = f'label=com.docker.compose.project={project}'
        for kind in ('container', 'volume'):
            listed = subprocess.run(
                [
                    'docker',
                    kind,
                    'ls',
                    '-q',
                    *(['-a'] if kind == 'container' else []),
                    '--filter',
                    label,
                ],
                capture_output=True,
                text=True,
            ).stdout.split()
            if listed:
                subprocess.run(['docker', kind, 'rm', '-f', *listed], capture_output=True)
        if self.kind == 'worktree':
            subprocess.run(
                ['git', '-C', str(REPO_ROOT), 'worktree', 'remove', '--force', str(self.path)],
                capture_output=True,
            )
        shutil.rmtree(self.path.parent, ignore_errors=True)


@pytest.fixture
def checkouts() -> Iterator:
    made: list[Checkout] = []

    def factory(kind: str) -> Checkout:
        made.append(Checkout(kind))
        return made[-1]

    yield factory
    for box in made:
        box.remove()


def assert_checkout_catalog(box: Checkout) -> None:
    claude = json.loads(box.sh('cat ~/.claude/plugins/known_marketplaces.json'))
    assert claude['agent-devcontainer']['installLocation'] == box.workspace
    assert f'source = "{box.workspace}"' in box.sh('cat ~/.codex/config.toml')
    assert box.workspace in box.sh('cat ~/.config/opencode/opencode.json')


@pytest.mark.parametrize('kind', ['clone', 'worktree'])
def test_the_checkout_catalog_wins_and_state_keeps_its_boundaries(checkouts, kind):
    box = checkouts(kind)
    box.up()
    box.sh('/opt/agentdev-runtime/runtime-health.sh ready')
    assert_checkout_catalog(box)
    box.sh('git status --short >/dev/null')
    first = box.startup_id()
    box.sh(
        'echo instance > ~/.claude/boundary-probe && echo container > /var/tmp/boundary-probe'
        ' && echo shared > /root/.agents-auth/boundary-probe-$DEVCONTAINER_ID'
    )

    # A window reload attaches again without restarting services.
    box.up()
    assert box.startup_id() == first
    assert_checkout_catalog(box)

    # A restart restarts services and keeps the container filesystem.
    subprocess.run(['docker', 'restart', box.container], check=True, capture_output=True)
    box.up()
    restarted = box.startup_id()
    assert restarted != first
    box.sh('test -f /var/tmp/boundary-probe && test -f /var/lib/agentdev/lifecycle/created')

    # A rebuild replaces the container and keeps the instance and shared volumes.
    old = box.container
    box.up('--remove-existing-container')
    assert box.container != old
    box.sh('/opt/agentdev-runtime/runtime-health.sh ready')
    box.sh('test ! -e /var/tmp/boundary-probe && test -f ~/.claude/boundary-probe')
    box.sh('ls /root/.agents-auth/ | grep -q boundary-probe-')
    assert_checkout_catalog(box)


def test_two_checkouts_share_only_credentials(checkouts):
    clone, worktree = checkouts('clone'), checkouts('worktree')
    clone.up()
    worktree.up()
    clone.sh(
        'echo clone > ~/.claude/isolation-probe && echo clone > /root/.agents-auth/isolation-probe'
    )
    worktree.sh(
        'test ! -e ~/.claude/isolation-probe && test -f /root/.agents-auth/isolation-probe'
    )
    assert os.path.basename(clone.workspace) != os.path.basename(worktree.workspace)
