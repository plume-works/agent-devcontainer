"""Git trust and HTTPS credentials for the checkout. Spec: devcontainer-git-credentials."""

from __future__ import annotations

import os
from pathlib import Path
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


def keyring_environment(path: Path) -> dict[str, str]:
    """Return the environment a saved keyring-session file exports, so gh reaches the keyring."""
    if not path.is_file():
        return dict(os.environ)
    result = subprocess.run(
        ['bash', '-c', 'set -a; source "$1"; env -0', 'keyring-session', str(path)],
        capture_output=True,
        check=True,
    )
    pairs = (item.split(b'=', 1) for item in result.stdout.split(b'\0') if b'=' in item)
    return {key.decode(): value.decode() for key, value in pairs}


def credential_helper(settings: env.Settings) -> int:
    """Make HTTPS git reuse gh's login, unless another helper is already configured."""
    environ = keyring_environment(settings.path('AGENTDEV_KEYRING_ENV_FILE'))
    if shutil.which('gh', path=environ.get('PATH')) is None:
        print('gh is not installed; skipping git credential helper setup.')
        return 0
    status = subprocess.run(
        ['gh', 'auth', 'status', '--hostname', 'github.com'],
        env=environ,
        capture_output=True,
        check=False,
    )
    if status.returncode != 0:
        print('gh is not authenticated to github.com; skipping git credential helper setup.')
        return 0
    existing = subprocess.run(
        ['git', 'config', '--get-urlmatch', 'credential.helper', 'https://github.com'],
        env=environ,
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
    subprocess.run(['gh', 'auth', 'setup-git'], env=environ, check=True)
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
