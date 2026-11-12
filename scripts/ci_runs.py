"""
Look up the calling workflow's push runs through the GitHub REST API.

Reads ``GITHUB_API_URL``, ``GITHUB_REPOSITORY``, ``GITHUB_RUN_ID``, and ``GH_TOKEN`` from the
environment it is given. Standard library only, so CI scripts run it without a sync.
"""

from __future__ import annotations

from collections.abc import Mapping
import json
import urllib.error
from urllib.parse import urlencode
import urllib.request


class CIRunsError(Exception):
    """The run history could not be read."""


def _get(env: Mapping[str, str], path: str) -> dict:
    """Return the JSON body of a GET on the repository's API path."""
    try:
        url = f'{env["GITHUB_API_URL"]}/repos/{env["GITHUB_REPOSITORY"]}/{path}'
        request = urllib.request.Request(
            url,
            headers={
                'Accept': 'application/vnd.github+json',
                'Authorization': f'Bearer {env["GH_TOKEN"]}',
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except KeyError as error:
        raise CIRunsError(f'missing environment variable {error}') from error
    except (urllib.error.URLError, OSError, ValueError) as error:
        raise CIRunsError(f'GET {path}: {error}') from error


def current_run(env: Mapping[str, str]) -> dict:
    """Return the run named by ``GITHUB_RUN_ID``."""
    if 'GITHUB_RUN_ID' not in env:
        raise CIRunsError("missing environment variable 'GITHUB_RUN_ID'")
    return _get(env, f'actions/runs/{env["GITHUB_RUN_ID"]}')


def push_runs(
    env: Mapping[str, str], workflow_id: int, branch: str, *, status: str | None = None
) -> list[dict]:
    """Return the workflow's push runs on branch, newest first, optionally of one status."""
    query = {'branch': branch, 'event': 'push', 'per_page': '100'}
    if status:
        query['status'] = status
    body = _get(env, f'actions/workflows/{workflow_id}/runs?{urlencode(query)}')
    return list(body.get('workflow_runs', []))


def last_success_sha(env: Mapping[str, str], branch: str) -> str | None:
    """Return the head commit of the calling workflow's last successful push run on branch."""
    runs = push_runs(env, current_run(env)['workflow_id'], branch, status='success')
    return runs[0]['head_sha'] if runs else None
