"""Tests that run each decision of the AI review gate with facts the test controls."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / '.github/actions/ai-review-gate/decide.py'
BOT = 'acme-bot[bot]'
REVIEWER = 'plume-works-quill[bot]'


def _decide(tmp_path: Path, decision: str, facts: dict) -> tuple[int, dict[str, str], str]:
    """Run one decision; return its exit code, its outputs, and its stdout."""
    output = tmp_path / 'github-output'
    output.write_text('')
    env = dict(os.environ, FACTS=json.dumps(facts), GITHUB_OUTPUT=str(output))
    result = subprocess.run(
        [sys.executable, str(SCRIPT), decision], env=env, text=True, capture_output=True
    )
    outputs = dict(line.split('=', 1) for line in output.read_text().splitlines())
    return result.returncode, outputs, result.stdout


# PRs are blocked until an AI review exists.


def _review(login: str, state: str) -> dict:
    return {'login': login, 'state': state, 'commit_id': 'c' * 40}


@pytest.mark.parametrize('state', ['APPROVED', 'CHANGES_REQUESTED', 'COMMENTED'])
def test_a_review_by_the_reviewer_is_accepted_on_any_head(tmp_path, state):
    facts = {'author': {'login': 'dev', 'type': 'User'}, 'reviews': [_review(REVIEWER, state)]}
    _, outputs, _ = _decide(tmp_path, 'review-accepted', facts)
    assert outputs['found'] == 'true'


@pytest.mark.parametrize(
    'reviews',
    [[], [_review('someone', 'APPROVED')], [_review(REVIEWER, 'DISMISSED')]],
    ids=['none', 'other-reviewer', 'dismissed'],
)
def test_no_accepted_review_is_not_found(tmp_path, reviews):
    facts = {'author': {'login': 'dev', 'type': 'User'}, 'reviews': reviews}
    _, outputs, _ = _decide(tmp_path, 'review-accepted', facts)
    assert outputs['found'] == 'false'


def test_a_trusted_bot_needs_no_review(tmp_path):
    facts = {'author': {'login': BOT, 'type': 'Bot'}, 'trusted_bots': f'x, {BOT}', 'reviews': []}
    _, outputs, _ = _decide(tmp_path, 'review-accepted', facts)
    assert outputs['found'] == 'true'


def test_a_user_with_a_trusted_login_still_needs_a_review(tmp_path):
    facts = {'author': {'login': BOT, 'type': 'User'}, 'trusted_bots': BOT, 'reviews': []}
    _, outputs, _ = _decide(tmp_path, 'review-accepted', facts)
    assert outputs['found'] == 'false'


@pytest.mark.parametrize(
    ('job_result', 'found', 'passes'),
    [
        ('success', 'true', True),
        ('skipped', 'true', True),
        ('success', 'false', False),
        ('skipped', '', False),
        ('failure', 'true', False),
        ('cancelled', 'true', False),
    ],
)
def test_gate_passes_only_with_a_sound_review_job_and_a_review(
    tmp_path, job_result, found, passes
):
    facts = {'event': 'pull_request', 'review_job_result': job_result, 'found': found}
    code, _, _ = _decide(tmp_path, 'gate', facts)
    assert (code == 0) is passes


def test_gate_passes_a_merge_group(tmp_path):
    facts = {'event': 'merge_group', 'review_job_result': 'skipped', 'found': ''}
    code, _, _ = _decide(tmp_path, 'gate', facts)
    assert code == 0


# The responder only acts for authorized same-repository requests.


@pytest.mark.parametrize(
    ('head', 'is_fork'),
    [('acme/repo', 'false'), ('other/repo', 'true'), ('', 'false')],
    ids=['same-repository', 'fork', 'no-head'],
)
def test_a_head_in_another_repository_is_a_fork(tmp_path, head, is_fork):
    facts = {'head_repository': head, 'repository': 'acme/repo'}
    _, outputs, _ = _decide(tmp_path, 'is-fork', facts)
    assert outputs['is_fork'] == is_fork


@pytest.mark.parametrize(
    ('permission', 'allowed'),
    [('admin', True), ('maintain', True), ('write', True), ('triage', False), ('read', False)],
)
def test_only_write_access_authorizes_the_actor(tmp_path, permission, allowed):
    code, _, stdout = _decide(tmp_path, 'authorize', {'actor': 'dev', 'permission': permission})
    assert (code == 0) is allowed
    if not allowed:
        assert '::error::User dev does not have permission' in stdout


# A review runs on first push and on explicit request.


def _pull_request(action: str, **facts: str) -> dict:
    return {'event': 'pull_request', 'action': action, **facts}


@pytest.mark.parametrize(
    ('facts', 'wants'),
    [
        (_pull_request('opened'), 'true'),
        (_pull_request('reopened'), 'true'),
        (_pull_request('ready_for_review'), 'true'),
        (_pull_request('synchronize', review_exists='false'), 'true'),
        (_pull_request('synchronize', review_exists='true'), 'false'),
        (_pull_request('synchronize', review_exists='true', request_label='true'), 'true'),
        (_pull_request('labeled', label='request-ai-review', request_label='true'), 'true'),
        (_pull_request('unlabeled', label='block-ai-reviews', request_label='true'), 'true'),
        (_pull_request('unlabeled', label='block-ai-reviews'), 'false'),
        (_pull_request('labeled', label='other', request_label='true'), 'false'),
        (_pull_request('opened', draft='true'), 'false'),
        (_pull_request('opened', block_ai_reviews='true'), 'false'),
        (_pull_request('opened', block_ai_reviews='true', request_label='true'), 'false'),
        ({'event': 'pull_request_review', 'action': 'submitted'}, 'false'),
    ],
    ids=[
        'opened',
        'reopened',
        'ready-for-review',
        'first-push-without-review',
        'push-after-review',
        'push-with-request-label',
        'request-label-added',
        'block-label-removed-with-request',
        'block-label-removed-without-request',
        'other-label-event',
        'draft',
        'blocked',
        'blocked-with-request',
        'review-event',
    ],
)
def test_a_review_runs_on_first_push_and_on_request(tmp_path, facts, wants):
    _, outputs, _ = _decide(tmp_path, 'wants-review', facts)
    assert outputs['wants_review'] == wants


# Trusted-bot pull requests are approved without an AI review.


@pytest.mark.parametrize(
    ('login', 'approve'), [(BOT, 'true'), ('dev', None)], ids=['trusted', 'not-trusted']
)
def test_only_a_trusted_bot_is_approved(tmp_path, login, approve):
    facts = {'login': login, 'trusted_bots': f'renovate[bot], {BOT}'}
    _, outputs, _ = _decide(tmp_path, 'trusted-bot', facts)
    assert outputs.get('approve') == approve


def _commit(sha: str, **overrides: object) -> dict:
    return {'sha': sha, 'author': BOT, 'committer': BOT, 'verified': True, **overrides}


def _activity(kind: str, actor: str = BOT) -> dict:
    return {'type': kind, 'actor': actor, 'after': 'a' * 40}


@pytest.mark.parametrize(
    ('commits', 'failure'),
    [
        ([_commit('1'), _commit('2', committer='web-flow')], ''),
        ([_commit('1', author='dev')], 'commit 1: author is dev'),
        ([_commit('1', author=None)], 'commit 1: author is not a GitHub account'),
        ([_commit('1', committer='dev')], 'commit 1: committer is dev'),
        (
            [_commit('1', verified=False, verification_reason='unsigned')],
            'commit 1: signature is not verified (unsigned)',
        ),
    ],
    ids=['own-commits', 'foreign-author', 'no-author', 'foreign-committer', 'unsigned'],
)
def test_approval_covers_only_the_bots_own_commits(tmp_path, commits, failure):
    facts = {'login': BOT, 'activities': [_activity('branch_creation')], 'commits': commits}
    _, outputs, _ = _decide(tmp_path, 'bot-approval', facts)
    assert outputs['failure'] == failure


@pytest.mark.parametrize('kind', ['push', 'force_push', 'branch_creation'])
def test_a_foreign_push_refuses_the_approval(tmp_path, kind):
    activities = [_activity('push'), _activity(kind, actor='dev'), _activity('branch_creation')]
    if kind == 'branch_creation':
        activities = activities[:2]
    facts = {'login': BOT, 'activities': activities, 'commits': [_commit('1')]}
    _, outputs, _ = _decide(tmp_path, 'bot-approval', facts)
    assert outputs['failure'] == f'{kind} to {"a" * 40} by dev'


def test_a_reused_branch_starts_clean_at_its_latest_creation(tmp_path):
    activities = [_activity('push'), _activity('branch_creation'), _activity('push', actor='dev')]
    facts = {'login': BOT, 'activities': activities, 'commits': [_commit('1')]}
    _, outputs, _ = _decide(tmp_path, 'bot-approval', facts)
    assert outputs['failure'] == ''
