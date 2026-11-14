#!/usr/bin/env python3
"""
Make one decision of the AI review gate from the JSON facts in the FACTS variable.

The caller reads the facts from GitHub. This script makes no call to GitHub. It
writes each output as `name=value` to the GITHUB_OUTPUT file and exits 1 when
the decision stops the job.
"""

from __future__ import annotations

from collections.abc import Callable
import json
import os
import sys

REVIEWER_LOGIN = 'plume-works-quill[bot]'
ACCEPTED_REVIEW_STATES = {'approved', 'changes_requested', 'commented'}
WRITE_PERMISSIONS = {'admin', 'maintain', 'write'}
REVIEW_GROUP_ACTIONS = {'opened', 'ready_for_review', 'reopened'}
PUSH_ACTIVITIES = {'branch_creation', 'push', 'force_push'}

Facts = dict
Outputs = dict[str, str]


class Blocked(Exception):
    """The decision stops the job; the message says why."""


def trusted_bots(value: object) -> list[str]:
    """Return the logins in a comma-separated `TRUSTED_BOT_ACTORS` value."""
    return [login.strip() for login in str(value or '').split(',') if login.strip()]


def review_accepted(facts: Facts) -> Outputs:
    """Find if the pull request has an accepted AI review."""
    author = facts.get('author') or {}
    if author.get('type') == 'Bot' and author.get('login') in trusted_bots(
        facts.get('trusted_bots')
    ):
        reason = f'Pull request authored by {author["login"]} (bot); AI review is not required.'
        return {'found': 'true', 'reason': reason}

    # The rule makes sure that the PR has a review, not that the AI reviewer
    # reviewed its current head. Do not compare commit_id against the head SHA.
    for review in reversed(facts.get('reviews') or []):
        state = str(review.get('state') or '').lower()
        if review.get('login') == REVIEWER_LOGIN and state in ACCEPTED_REVIEW_STATES:
            reason = (
                f'Found accepted AI review by {review["login"]} for {review.get("commit_id")} '
                f'with state {review.get("state")}.'
            )
            return {'found': 'true', 'reason': reason}
    return {
        'found': 'false',
        'reason': f'No AI review found. Expected a review from {REVIEWER_LOGIN}.',
    }


def gate(facts: Facts) -> Outputs:
    """Pass the ai-review-present check only when the review job did not fail or stop and a review exists."""
    if facts.get('event') == 'merge_group':
        print('Merge group event, skipping AI review check')
        return {}
    job_result = facts.get('review_job_result')
    if job_result in ('failure', 'cancelled'):
        raise Blocked(f'The review job ended with {job_result}.')
    print(f'Review job: {job_result}. {facts.get("reason") or ""}')
    if facts.get('found') != 'true':
        raise Blocked('')
    return {}


def is_fork(facts: Facts) -> Outputs:
    """Find if the head of the pull request is in another repository."""
    head = facts.get('head_repository') or ''
    return {'is_fork': str(bool(head) and head != facts.get('repository')).lower()}


def authorize(facts: Facts) -> Outputs:
    """Let only an actor with write access start the review responder."""
    actor = facts.get('actor')
    if facts.get('permission') not in WRITE_PERMISSIONS:
        raise Blocked(f'User {actor} does not have permission to trigger the responder.')
    return {}


def wants_review(facts: Facts) -> Outputs:
    """Find if this `pull_request` run starts an AI review."""
    action = facts.get('action')
    label = facts.get('label')

    def decide() -> bool:
        if facts.get('event') != 'pull_request' or facts.get('draft') == 'true':
            return False
        # A run in the pr-<n> group takes an open request if block-ai-reviews is
        # not on the pull request. A run in a label-<run id> group never takes it.
        # Label lifecycle: ADR-0059.
        label_event = action in ('labeled', 'unlabeled')
        in_pr_group = (
            not label_event
            or (action == 'labeled' and label == 'request-ai-review')
            or (action == 'unlabeled' and label == 'block-ai-reviews')
        )
        if not in_pr_group or facts.get('block_ai_reviews') == 'true':
            return False
        if facts.get('request_label') == 'true':
            return True
        if label_event:
            return False
        if action in REVIEW_GROUP_ACTIONS:
            return True
        return action == 'synchronize' and facts.get('review_exists') != 'true'

    return {'wants_review': str(decide()).lower()}


def trusted_bot(facts: Facts) -> Outputs:
    """Find if the author of the pull request is a trusted bot."""
    login = facts.get('login')
    if login not in trusted_bots(facts.get('trusted_bots')):
        print(f'{login} is not a trusted bot; nothing to approve.')
        return {}
    return {'approve': 'true'}


def commit_failure(commit: Facts, login: str) -> str:
    """Return why a commit blocks the approval, or an empty string."""
    if commit.get('author') != login:
        return f'author is {commit.get("author") or "not a GitHub account"}'
    committer = commit.get('committer')
    if committer not in (login, 'web-flow'):
        return f'committer is {committer or "not a GitHub account"}'
    if commit.get('verified') is not True:
        return f'signature is not verified ({commit.get("verification_reason") or "unknown"})'
    return ''


def bot_approval(facts: Facts) -> Outputs:
    """
    Approve only when the trusted bot alone pushed the branch and wrote every commit.

    Approval covers only the commits of the bot. Refer to ADR-0069.
    """
    login = facts.get('login')
    activities = facts.get('activities') or []
    # The list starts with the newest activity. For a branch name used again,
    # the decision reads only the activities since the latest branch creation.
    created = next(
        (i for i, a in enumerate(activities) if a.get('type') == 'branch_creation'), None
    )
    if created is not None:
        activities = activities[: created + 1]
    for activity in activities:
        if activity.get('type') in PUSH_ACTIVITIES and activity.get('actor') != login:
            actor = activity.get('actor') or 'an unknown actor'
            failure = f'{activity["type"]} to {activity.get("after")} by {actor}'
            return {'failure': failure}
    for commit in facts.get('commits') or []:
        reason = commit_failure(commit, login)
        if reason:
            return {'failure': f'commit {commit.get("sha")}: {reason}'}
    return {'failure': ''}


DECISIONS: dict[str, Callable[[Facts], Outputs]] = {
    'review-accepted': review_accepted,
    'gate': gate,
    'is-fork': is_fork,
    'authorize': authorize,
    'wants-review': wants_review,
    'trusted-bot': trusted_bot,
    'bot-approval': bot_approval,
}


def main(argv: list[str]) -> int:
    """Run the decision that argv names and write its outputs."""
    if len(argv) != 2 or argv[1] not in DECISIONS:
        print(f'usage: decide.py {{{",".join(DECISIONS)}}}', file=sys.stderr)
        return 2
    facts = json.loads(os.environ.get('FACTS') or '{}')
    try:
        outputs = DECISIONS[argv[1]](facts)
    except Blocked as blocked:
        if str(blocked):
            print(f'::error::{blocked}')
        return 1
    with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as output:
        for name, value in outputs.items():
            output.write(f'{name}={value}\n')
            print(f'{name}={value}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
