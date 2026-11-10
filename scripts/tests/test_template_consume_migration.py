"""
The template-consume migration's end state: a consumer that keeps only the descriptor files.

The guide's migration deletes `.devcontainer/scripts/` and tracks only the files listed in
its marker step; these tests prove those files alone open a ready Dev Container.
"""

from __future__ import annotations

from collections.abc import Iterator
import json
from pathlib import Path
import re
import shutil
import subprocess
from uuid import uuid4

import pytest
from test_agentdev_devcontainer_image import CLI, IMAGE, pytestmark as needs_image, TMP_ROOT

REPO_ROOT = Path(__file__).resolve().parents[2]
GUIDE = (
    REPO_ROOT / '.agents/plugins/agentdev/skills/template-consume/references/consumption-guide.md'
)
PINS = 'devcontainer-compose-pins.yml'
LIFECYCLE_KEYS = ('postCreateCommand', 'postStartCommand', 'postAttachCommand', 'waitFor')


def migrated_paths() -> list[str]:
    section = GUIDE.read_text().split('## Migrating to the agentdev image family', 1)[1]
    marker = section.split('6. **Marker.**', 1)[1].split('```text', 1)[1].split('```', 1)[0]
    return marker.split()


def strip_comments(text: str) -> str:
    return '\n'.join(re.sub(r'(^|\s)(//|#).*$', '', line) for line in text.splitlines())


def test_the_migrated_descriptor_runs_no_copied_script():
    paths = migrated_paths()
    assert paths and all(path.startswith('.devcontainer/') for path in paths)
    assert not any(path.startswith('.devcontainer/scripts/') for path in paths)
    for path in paths:
        assert (REPO_ROOT / path).is_file(), path
        assert '.devcontainer/scripts' not in strip_comments((REPO_ROOT / path).read_text())
    descriptor = strip_comments((REPO_ROOT / '.devcontainer/devcontainer.json').read_text())
    assert not any(f'"{key}"' in descriptor for key in LIFECYCLE_KEYS)
    assert 'docker-in-docker' not in descriptor


class Consumer:
    """A repository holding only the migrated descriptor files, opened in a Dev Container."""

    def __init__(self) -> None:
        self.id = uuid4().hex[:8]
        self.path = TMP_ROOT / f'dc-migrated-{self.id}' / f'consumer-{self.id}'
        self.path.mkdir(parents=True)
        for path in [*migrated_paths(), PINS]:
            (self.path / path).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(REPO_ROOT / path, self.path / path)
        pins = self.path / PINS
        pins.write_text(re.sub(r'image: \S+', f'image: {IMAGE}', pins.read_text()))
        for command in (['init', '-q', '-b', 'main'], ['add', '-A']):
            subprocess.run(['git', *command], cwd=self.path, check=True)
        subprocess.run(
            ['git', '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'migrated'],
            cwd=self.path,
            check=True,
        )
        self.container = ''

    def up(self) -> None:
        result = subprocess.run(
            [*CLI, 'up', '--workspace-folder', str(self.path)],
            capture_output=True,
            text=True,
            timeout=2400,
        )
        assert result.returncode == 0, result.stdout[-4000:] + result.stderr[-4000:]
        self.container = json.loads(result.stdout.strip().splitlines()[-1])['containerId']

    def sh(self, script: str) -> str:
        result = subprocess.run(
            ['docker', 'exec', '-w', f'/workspaces/{self.path.name}', self.container]
            + ['bash', '-lc', script],
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result.stdout.strip()

    def remove(self) -> None:
        label = f'label=com.docker.compose.project={self.path.name}_devcontainer'.lower()
        for kind in ('container', 'volume'):
            listed = subprocess.run(
                ['docker', kind, 'ls', '-q', *(['-a'] if kind == 'container' else [])]
                + ['--filter', label],
                capture_output=True,
                text=True,
            ).stdout.split()
            if listed:
                subprocess.run(['docker', kind, 'rm', '-f', *listed], capture_output=True)
        shutil.rmtree(self.path.parent, ignore_errors=True)


@pytest.fixture
def consumer() -> Iterator[Consumer]:
    box = Consumer()
    yield box
    box.remove()


@needs_image
def test_a_migrated_consumer_reaches_runtime_readiness(consumer: Consumer):
    consumer.up()
    consumer.sh('agentdev-runtime health ready')
    consumer.sh('test ! -e .devcontainer/scripts')
    marketplaces = json.loads(consumer.sh('cat ~/.claude/plugins/known_marketplaces.json'))
    assert marketplaces['agent-devcontainer']['installLocation'] == '/opt/agentdev'
