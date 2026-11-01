"""Tests that Renovate moves the agentdev image pins together and workflows share one pin."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[2]
RENOVATE = json.loads((REPO_ROOT / '.github/renovate.json').read_text())
PIN = 'opencode-compose-pins.yml'


AGENTDEV_DIGEST_GROUP = 'agentdev image digests'


def test_renovate_tracks_the_pin_and_lets_its_tasks_edit_it():
    patterns = RENOVATE['docker-compose']['managerFilePatterns']
    assert any(re.search(p.strip('/'), PIN) for p in patterns)
    assert PIN in RENOVATE['postUpgradeTasks']['fileFilters']
    rule = next(
        r
        for r in RENOVATE['packageRules']
        if 'ghcr.io/plume-works/agentdev-deploy' in r.get('matchPackageNames', [])
    )
    assert rule['groupName'] == AGENTDEV_DIGEST_GROUP


def test_renovate_moves_every_dev_container_reference_together():
    rule = next(
        r
        for r in RENOVATE['packageRules']
        if 'ghcr.io/plume-works/agentdev-devcontainer' in r.get('matchPackageNames', [])
    )
    assert rule['groupName'] == AGENTDEV_DIGEST_GROUP
    names = {p for r in RENOVATE['packageRules'] for p in r.get('matchPackageNames', [])}
    assert not {'ghcr.io/plume-works/agent-desktop', 'ghcr.io/plume-works/agent-opencode'} & names


def test_workflow_jobs_share_the_dev_container_pin():
    # The committed pin: the Dev Container smoke test patches the working copy to its own build.
    committed = subprocess.run(
        ['git', 'show', 'HEAD:devcontainer-compose-pins.yml'],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    pin = re.search(r'image: (\S+)', committed)
    assert pin is not None and '/agentdev-devcontainer:' in pin.group(1)
    workflows = REPO_ROOT / '.github/workflows'
    images = [
        line.split('image:', 1)[1].strip()
        for path in workflows.glob('*.yml')
        for line in path.read_text().splitlines()
        if re.match(r'\s+image: ghcr.io/plume-works/', line)
    ]
    assert images and set(images) == {pin.group(1)}
