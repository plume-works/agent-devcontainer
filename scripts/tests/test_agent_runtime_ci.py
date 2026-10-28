"""Tests for how CI builds, publishes, and accepts agent-opencode, and how its pin is tracked."""

from __future__ import annotations

import json
from pathlib import Path
import re

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CI = yaml.safe_load((REPO_ROOT / '.github/workflows/ci.yml').read_text())
FILTER_ACTION = (REPO_ROOT / '.github/actions/paths-filter/action.yml').read_text()
ACTIONS = REPO_ROOT / '.github/actions/docker'
MERGE_ACTION = yaml.safe_load((ACTIONS / 'multiarch-merge/action.yml').read_text())
METADATA_ACTION = yaml.safe_load((ACTIONS / 'metadata-action/action.yml').read_text())
PROMOTE_ACTION = yaml.safe_load((ACTIONS / 'promote/action.yml').read_text())
RENOVATE = json.loads((REPO_ROOT / '.github/renovate.json').read_text())
PIN = 'opencode-compose-pins.yml'
RUNTIME_SOURCES = [
    '.devcontainer/scripts/runtime-supervisor.py',
    '.devcontainer/scripts/runtime-bootstrap.sh',
    '.devcontainer/firewall-allowlist.txt',
    'docker/opencode/agent-opencode.Dockerfile',
    'docker/deploy/supervisord.conf',
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


def test_the_merge_pushes_only_the_candidate_tag():
    meta = next(s for s in MERGE_ACTION['runs']['steps'] if s.get('id') == 'meta')
    assert meta['with']['candidate'] == 'true'
    tags = next(s for s in METADATA_ACTION['runs']['steps'] if s.get('id') == 'meta')
    rules = tags['with']['tags'].splitlines()
    assert [r for r in rules if "candidate == 'true'" in r] == [
        r for r in rules if r.startswith('type=sha,')
    ]
    assert all("candidate != 'true'" in r for r in rules if not r.startswith('type=sha,'))


def test_promotion_waits_for_both_test_jobs_and_reuses_the_merged_digests():
    merge = CI['jobs']['merge-dev-image']
    promote = CI['jobs']['promote-dev-image']
    assert set(promote['needs']) == {'merge-dev-image', 'dev-container-ci', 'opencode-acceptance'}
    assert 'if' not in promote
    checkout = steps(promote)[0]
    assert checkout['uses'].startswith('actions/checkout@')
    assert checkout['with']['fetch-depth'] == 0
    promoted = [s for s in steps(promote) if s.get('uses') == './.github/actions/docker/promote']
    image_names = ['ANSIBLE_IMAGE_NAME', 'DESKTOP_IMAGE_NAME', 'OPENCODE_IMAGE_NAME']
    assert [s['with']['image'].split('env.')[-1].rstrip(' }') for s in promoted] == image_names
    for step, output in zip(promoted, ['ansible_digest', 'desktop_digest', 'opencode_digest']):
        assert step['with']['digest'] == f'${{{{ needs.merge-dev-image.outputs.{output} }}}}'
        assert merge['outputs'][output].endswith('.outputs.digest }}')
    assert 'promote-dev-image' in CI['jobs']['finished']['needs']


def test_promotion_never_moves_a_tag_back_or_rebuilds():
    run = PROMOTE_ACTION['runs']['steps'][-1]['run']
    assert 'org.opencontainers.image.revision' in run
    assert 'git merge-base --is-ancestor "${GITHUB_SHA}" "${current}"' in run
    assert 'imagetools create' in run
    uses = [s.get('uses', '') for s in PROMOTE_ACTION['runs']['steps']]
    assert not any('build-push-action' in u for u in uses)


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
