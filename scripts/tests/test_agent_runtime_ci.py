"""Tests for how CI builds, publishes, and accepts the agentdev image family, and its pins."""

from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

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
    'py_packages/agentdev_runtime/agentdev_runtime/supervisor.py',
    'py_packages/agentdev_runtime/agentdev_runtime/bootstrap.py',
    '.devcontainer/firewall-allowlist.txt',
    'docker/base/agentdev-base.Dockerfile',
    'docker/deploy/agentdev-deploy.Dockerfile',
    'docker/deploy/supervisord.conf',
    'docker/devcontainer/agentdev-devcontainer.Dockerfile',
    'docker/devcontainer/supervisord.conf',
    'py_packages/agentdev_runtime/agentdev_runtime/xpra.py',
    'scripts/tests/test_agent_runtime_acceptance.py',
]
DEPLOYMENT_ONLY = [
    PIN,
    'devcontainer-compose-pins.yml',
    'compose.opencode.yml',
    'compose.opencode.bind.yml',
]


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


RUNTIMES = {
    'deploy': ('Build agentdev deploy image', 'docker/deploy/agentdev-deploy.Dockerfile'),
    'devcontainer': (
        'Build agentdev devcontainer image',
        'docker/devcontainer/agentdev-devcontainer.Dockerfile',
    ),
}


@pytest.mark.parametrize('runtime', RUNTIMES)
def test_each_runtime_builds_on_the_same_run_base_digest(runtime: str):
    build = steps(CI['jobs']['build-dev-image'])
    names = [step.get('name') for step in build]
    name, dockerfile = RUNTIMES[runtime]
    step = build[names.index(name)]
    assert names.index('Build agentdev base image') < names.index(name)
    assert build[names.index('Build agentdev base image')]['id'] == 'build'
    assert step['with']['file'] == dockerfile
    assert step['with']['arch'] == '${{ matrix.arch }}'
    args = step['with']['build-args']
    assert 'BASE_IMAGE_NAME }}@${{ steps.build.outputs.digest }}' in args
    assert 'DEPLOY_IMAGE_NAME' not in args and 'DEVCONTAINER_IMAGE_NAME' not in args


def test_each_runtime_gets_its_own_manifest_and_native_acceptance():
    merge = CI['jobs']['merge-dev-image']
    for runtime, env in (('deploy', 'DEPLOY'), ('devcontainer', 'DEVCONTAINER')):
        merged = next(s for s in steps(merge) if s.get('id') == f'merge_{runtime}')
        assert merged['with']['image'].endswith(f'${{{{ env.{env}_IMAGE_NAME }}}}')
        assert f'merge_{runtime}' in merge['outputs'][f'{runtime}_image_pinned']
    for job, script, variable in (
        ('deploy-acceptance', 'test_agent_runtime_acceptance.py', 'AGENTDEV_RUNTIME_TEST_IMAGE'),
        (
            'devcontainer-acceptance',
            'test_agentdev_devcontainer_image.py',
            'AGENTDEV_DEVCONTAINER_TEST_IMAGE',
        ),
    ):
        acceptance = CI['jobs'][job]
        assert acceptance['needs'] == ['merge-dev-image']
        assert {
            entry['arch'].split("'")[-2] for entry in acceptance['strategy']['matrix']['include']
        } == {'amd64', 'arm64'}
        run = next(s for s in steps(acceptance) if script in s.get('run', ''))
        assert job.split('-')[0] + '_image_pinned' in run['env'][variable]
        assert job in CI['jobs']['finished']['needs']
    assert {'build-dev-image', 'dev-container-ci'} <= set(CI['jobs']['finished']['needs'])


def test_the_dev_container_check_runs_this_runs_image():
    job = steps(CI['jobs']['dev-container-ci'])
    patch = next(s for s in job if s.get('name', '').startswith('Patch image pin'))
    assert 'devcontainer_image_pinned' in patch['env']['MERGED_IMAGE']
    assert 's|image: ghcr.io/.*|image: ${MERGED_IMAGE}|' in patch['run']


@pytest.mark.parametrize('job', ['dev-container-ci', 'devcontainer-acceptance'])
def test_the_candidate_is_pulled_in_its_own_step_before_any_test(job):
    job_steps = steps(CI['jobs'][job])
    pulls = [i for i, s in enumerate(job_steps) if 'docker pull' in s.get('run', '')]
    assert len(pulls) == 1
    pull = job_steps[pulls[0]]
    assert pull['name'] == 'Pull the candidate image'
    assert 'devcontainer_image_pinned' in str(pull['env'])
    assert any('pytest' in str(s) for s in job_steps[pulls[0] + 1 :])


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
    assert set(promote['needs']) == {
        'merge-dev-image',
        'dev-container-ci',
        'deploy-acceptance',
        'devcontainer-acceptance',
    }
    assert 'if' not in promote
    checkout = steps(promote)[0]
    assert checkout['uses'].startswith('actions/checkout@')
    assert checkout['with']['fetch-depth'] == 0
    promoted = [s for s in steps(promote) if s.get('uses') == './.github/actions/docker/promote']
    image_names = [
        'ANSIBLE_IMAGE_NAME',
        'BASE_IMAGE_NAME',
        'DEPLOY_IMAGE_NAME',
        'DEVCONTAINER_IMAGE_NAME',
    ]
    assert [s['with']['image'].split('env.')[-1].rstrip(' }') for s in promoted] == image_names
    outputs = ['ansible_digest', 'base_digest', 'deploy_digest', 'devcontainer_digest']
    for step, output in zip(promoted, outputs):
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
