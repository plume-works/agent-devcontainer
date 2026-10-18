"""Tests for how CI builds, publishes, and accepts agent-opencode, and how its pin is tracked."""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CI = yaml.safe_load((REPO_ROOT / '.github/workflows/ci.yml').read_text())
CHECKS_PATH = REPO_ROOT / '.github/workflows/opencode-runtime-checks.yml'
CHECKS = yaml.safe_load(CHECKS_PATH.read_text())
FILTER_ACTION = (REPO_ROOT / '.github/actions/paths-filter/action.yml').read_text()
RENOVATE = json.loads((REPO_ROOT / '.github/renovate.json').read_text())
PIN = 'opencode-compose-pins.yml'
RUNTIME_SOURCES = [
    '.devcontainer/scripts/runtime-supervisor.py',
    '.devcontainer/scripts/runtime-bootstrap.sh',
    '.devcontainer/firewall-allowlist.txt',
    'docker/opencode/agent-opencode.Dockerfile',
    'docker/opencode/supervisord.conf',
    'docker/desktop/start-xpra.sh',
    'scripts/tests/test_agent_runtime_acceptance.py',
]
DEPLOYMENT_ONLY = [PIN, 'compose.opencode.yml', 'compose.opencode.bind.yml']


def image_filter() -> list[str]:
    """Return the globs of the shared `image` path filter."""
    block = FILTER_ACTION.split('image:\n', 1)[1].split('YAML', 1)[0]
    return [line.strip()[2:] for line in block.splitlines() if line.strip().startswith('- ')]


def glob_match(pattern: str, path: str) -> bool:
    """Match like dorny/paths-filter's picomatch for the plain globs this repo uses."""
    regex = re.escape(pattern).replace(r'\*\*', '.*').replace(r'\*', '[^/]*')
    return re.fullmatch(regex, path) is not None


def steps(job: dict) -> list[dict]:
    return job['steps']


@pytest.mark.parametrize('path', RUNTIME_SOURCES)
def test_runtime_sources_trigger_the_image_build(path: str):
    assert any(glob_match(pattern, path) for pattern in image_filter())


@pytest.mark.parametrize('path', DEPLOYMENT_ONLY)
def test_deployment_files_do_not_trigger_the_image_build(path: str):
    assert not any(glob_match(pattern, path) for pattern in image_filter())


def test_the_runtime_builds_on_the_same_run_desktop_digest():
    build = steps(CI['jobs']['build-dev-image'])
    names = [step.get('name') for step in build]
    opencode = build[names.index('Build agent opencode image')]
    assert names.index('Build agent desktop image') < names.index('Build agent opencode image')
    assert build[names.index('Build agent desktop image')]['id'] == 'build'
    assert opencode['with']['file'] == 'docker/opencode/agent-opencode.Dockerfile'
    assert opencode['with']['arch'] == '${{ matrix.arch }}'
    assert (
        'DESKTOP_IMAGE_NAME }}@${{ steps.build.outputs.digest }}' in opencode['with']['build-args']
    )


def test_the_runtime_gets_its_own_manifest_and_native_acceptance():
    merge = CI['jobs']['merge-dev-image']
    merged = next(s for s in steps(merge) if s.get('id') == 'merge_opencode')
    assert merged['with']['image'].endswith('${{ env.OPENCODE_IMAGE_NAME }}')
    assert 'merge_opencode' in merge['outputs']['opencode_image_pinned']
    acceptance = CI['jobs']['opencode-acceptance']
    assert acceptance['needs'] == ['merge-dev-image']
    assert {
        entry['arch'].split("'")[-2] for entry in acceptance['strategy']['matrix']['include']
    } == {'amd64', 'arm64'}
    run = next(s for s in steps(acceptance) if 'test-agent-runtime.sh' in s.get('run', ''))
    assert 'opencode_image_pinned' in run['env']['AGENTDEV_RUNTIME_TEST_IMAGE']
    assert 'opencode-acceptance' in CI['jobs']['finished']['needs']
    assert {'build-dev-image', 'dev-container-ci'} <= set(CI['jobs']['finished']['needs'])


def test_pin_checks_accept_the_proposed_digest_without_building_anything():
    triggers = CHECKS.get('on', CHECKS.get(True))
    assert set(DEPLOYMENT_ONLY) <= set(triggers['pull_request']['paths'])
    job = CHECKS['jobs']['acceptance']
    assert job['permissions'] == {'contents': 'read', 'packages': 'read'}
    text = CHECKS_PATH.read_text()
    assert 'build-push-action' not in text and 'multiarch-merge' not in text
    run = next(s for s in steps(job) if 'test-agent-runtime.sh' in s.get('run', ''))
    assert run['env']['AGENTDEV_RUNTIME_TEST_IMAGE'] == '${{ steps.pin.outputs.image }}'
    pin = next(s for s in steps(job) if s.get('id') == 'pin')
    assert '@sha256:' in pin['run'] and PIN in pin['run']


def test_pin_checks_skip_only_when_ci_cd_runs_its_own_acceptance():
    scope = next(s for s in steps(CHECKS['jobs']['acceptance']) if s.get('id') == 'scope')
    ci_filter = next(s for s in steps(CI['jobs']['paths-filter']) if s.get('id') == 'filter')
    assert scope['uses'] == ci_filter['uses'] == './.github/actions/paths-filter'
    assert scope['with']['extra-filter'] == ci_filter['with']['extra-filter']
    gated = [s for s in steps(CHECKS['jobs']['acceptance']) if 'scope' in s.get('if', '')]
    assert gated and all(s['if'] == "steps.scope.outputs.pass != 'true'" for s in gated)


def test_renovate_tracks_the_pin_and_lets_its_tasks_edit_it():
    patterns = RENOVATE['docker-compose']['managerFilePatterns']
    assert any(re.search(p.strip('/'), PIN) for p in patterns)
    assert PIN in RENOVATE['postUpgradeTasks']['fileFilters']
    rule = next(
        r
        for r in RENOVATE['packageRules']
        if r.get('matchPackageNames') == ['ghcr.io/plume-works/agent-opencode']
    )
    assert rule['groupName'] == 'agent-opencode'
