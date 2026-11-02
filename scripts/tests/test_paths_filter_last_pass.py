"""Tests that a push to main is filtered against the last commit its workflow passed on."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ACTION = yaml.safe_load((REPO_ROOT / '.github/actions/paths-filter/action.yml').read_text())
STEPS = {step.get('id'): step for step in ACTION['runs']['steps']}
LAST_PASS = STEPS['last-pass']
HEAD_SHA = 'c' * 40
LAST_PASS_SHA = 'a' * 40
WORKFLOW_ID = '4242'


def _last_pass(
    tmp_path: Path, *, last_sha: str = LAST_PASS_SHA, gh_fails: bool = False
) -> tuple[subprocess.CompletedProcess[str], dict[str, str], list[str]]:
    """Run the last-pass step with a stub gh; return the result, its outputs, and gh calls."""
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    log = tmp_path / 'gh.log'
    (fake_bin / 'gh').write_text(
        '#!/usr/bin/env bash\n'
        f'echo "$*" >> "{log}"\n'
        f'if [[ "{int(gh_fails)}" == 1 ]]; then exit 1; fi\n'
        f'if [[ "$2" == */actions/runs/* ]]; then echo {WORKFLOW_ID}; exit 0; fi\n'
        f'echo "{last_sha}"\n'
    )
    (fake_bin / 'gh').chmod(0o755)
    output = tmp_path / 'github-output'
    output.write_text('')
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(
        {
            'PATH': f'{fake_bin}{os.pathsep}{env["PATH"]}',
            'GITHUB_OUTPUT': str(output),
            'GH_TOKEN': 'token',
            'REPO': 'owner/repo',
            'RUN_ID': '99',
            'BRANCH': 'main',
            'HEAD_SHA': HEAD_SHA,
        }
    )
    result = subprocess.run(
        ['bash', '--noprofile', '--norc', '-euo', 'pipefail', '-c', LAST_PASS['run']],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
    )
    outputs = dict(line.split('=', 1) for line in output.read_text().splitlines())
    calls = log.read_text().splitlines() if log.exists() else []
    return result, outputs, calls


def test_outputs_head_of_last_successful_push_run(tmp_path):
    result, outputs, calls = _last_pass(tmp_path)
    assert result.returncode == 0, result.stderr
    assert outputs == {'sha': LAST_PASS_SHA}
    query = calls[-1]
    assert f'actions/workflows/{WORKFLOW_ID}/runs?' in query
    for parameter in ('branch=main', 'status=success', 'event=push'):
        assert parameter in query


@pytest.mark.parametrize('last_sha', ['', HEAD_SHA], ids=['no-passing-run', 'rerun-of-head'])
def test_falls_back_to_previous_push_without_an_earlier_pass(tmp_path, last_sha):
    result, outputs, _ = _last_pass(tmp_path, last_sha=last_sha)
    assert result.returncode == 0, result.stderr
    assert outputs == {}


def test_lookup_failure_warns_and_falls_back(tmp_path):
    result, outputs, _ = _last_pass(tmp_path, gh_fails=True)
    assert result.returncode == 0, result.stderr
    assert outputs == {}
    assert '::warning::' in result.stdout
