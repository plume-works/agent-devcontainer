"""Git trust and HTTPS credentials for the checkout."""

from __future__ import annotations

import shutil
import subprocess
import sys

from agentdev_runtime import settings as env


def safe_directory(settings: env.Settings) -> int:
    """Trust the checkout, which a different UID than the one running git may own."""
    workspace = settings.get('DEV_WORKSPACE_FOLDER')
    if shutil.which('git') is None:
        print('git not found')
    listed = subprocess.run(
        ['git', 'config', '--global', '--get-all', 'safe.directory'],
        capture_output=True,
        text=True,
        check=False,
    ).stdout.splitlines()
    if workspace not in listed:
        subprocess.run(
            ['git', 'config', '--global', '--add', 'safe.directory', workspace], check=True
        )
    return 0


def credential_helper(settings: env.Settings) -> int:
    """Make HTTPS git reuse gh's login, unless another helper is already configured."""
    if shutil.which('gh') is None:
        print('gh is not installed; skipping git credential helper setup.')
        return 0
    status = subprocess.run(
        ['gh', 'auth', 'status', '--hostname', 'github.com'],
        capture_output=True,
        check=False,
    )
    if status.returncode != 0:
        print('gh is not authenticated to github.com; skipping git credential helper setup.')
        return 0
    existing = subprocess.run(
        ['git', 'config', '--get-urlmatch', 'credential.helper', 'https://github.com'],
        capture_output=True,
        text=True,
        check=False,
    )
    if existing.returncode == 0 and existing.stdout.strip():
        print(
            'A git credential helper for github.com is already configured; leaving it unchanged.'
        )
        return 0
    sys.stdout.flush()
    subprocess.run(['gh', 'auth', 'setup-git'], check=True)
    print('Configured gh as the git credential helper.')
    return 0


def main(argv: list[str]) -> int:
    settings = env.Settings()
    if argv == ['safe-directory']:
        return safe_directory(settings)
    if argv == ['credential-helper']:
        try:
            return credential_helper(settings)
        except subprocess.CalledProcessError as error:
            print(f'agentdev-runtime git: {error}', file=sys.stderr)
            return 1
    print('usage: agentdev-runtime git safe-directory|credential-helper', file=sys.stderr)
    return 2
