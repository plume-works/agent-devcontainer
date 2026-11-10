#!/usr/bin/env python3
"""
Set up a Claude Code cloud session's host to work on this repository.

`startup.py setup`, the environment setup script, registers the agentdev plugin, installs the
cloud-session instructions and environment, provisions the project toolchain on the host, and
installs the git hooks. Standard library only: the session host has no project environment yet.
Design: architecture/cloud-session-host-toolchain.
"""

import argparse
from collections.abc import Callable, Mapping
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

REPO_ROOT = Path(__file__).resolve().parents[1]
# The ansible playbook's roles that put every pre-commit hook's binary on PATH.
TOOLCHAIN_TAGS = 'dev_tools,uv_setup'
HOOK_TYPES = ('pre-commit', 'pre-push', 'pre-merge-commit', 'post-checkout')
# The session's placeholder GH_TOKEN fails zizmor's online audits:
# see bugs/zizmor-online-audits-fail-in-cloud-devcontainer.
SESSION_ENV = {'ZIZMOR_OFFLINE': 'true'}


def log(message: str) -> None:
    """Announce a step on stderr."""
    print(f'\n==> {message}', file=sys.stderr, flush=True)


def run(*command: str, env: Mapping[str, str] | None = None) -> None:
    """Run a command in the checkout with its output on stderr, raising when it fails."""
    subprocess.run(command, cwd=REPO_ROOT, env=env, stdout=sys.stderr, check=True)


def register_plugin() -> None:
    """Register this checkout as the plugin marketplace and install agentdev."""
    log('Registering agent-devcontainer marketplace and installing agentdev')
    run('claude', 'plugin', 'marketplace', 'add', './')
    run('claude', 'plugin', 'install', 'agentdev@agent-devcontainer')


def add_cloud_instructions() -> None:
    """Install the cloud-session instructions as the user-level CLAUDE.md."""
    target = Path.home() / '.claude/CLAUDE.md'
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / '.claude/CLAUDE.cloud.md', target)


def add_session_env() -> None:
    """Merge SESSION_ENV into the user-level Claude Code settings, which every tool inherits."""
    target = Path.home() / '.claude/settings.json'
    settings = json.loads(target.read_text()) if target.exists() else {}
    settings['env'] = {**settings.get('env', {}), **SESSION_ENV}
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(settings, indent=2) + '\n')


def provision_toolchain(environ: Mapping[str, str]) -> None:
    """Install Ansible, then the pinned tools the image's dev_tools and uv_setup roles install."""
    log('Provisioning the project toolchain on the host')
    run('bash', 'docker/ansible/setup-ansible.sh')
    run(
        'ansible-playbook',
        'ansible/playbooks/setup-dev.yml',
        '--tags',
        TOOLCHAIN_TAGS,
        env={**environ, 'ANSIBLE_LOG_PATH': ''},
    )


def sync_project() -> None:
    """Create the project environment and install the git hooks from it."""
    log('Syncing the project environment and installing git hooks')
    run('uv', 'sync')
    hook_types = [arg for hook in HOOK_TYPES for arg in ('--hook-type', hook)]
    run('uv', 'run', 'pre-commit', 'install', '--install-hooks', *hook_types)


def timed(step: Callable[..., None], *args: object) -> None:
    """Run one setup step and report how long it took."""
    started = time.monotonic()
    step(*args)
    print(f'{step.__name__}: {time.monotonic() - started:.1f}s', file=sys.stderr)


def setup(environ: Mapping[str, str]) -> None:
    """Run the whole environment setup."""
    timed(register_plugin)
    add_cloud_instructions()
    add_session_env()
    timed(provision_toolchain, environ)
    timed(sync_project)
    log('Setup complete')


def main(argv: list[str]) -> int:
    """Parse the mode and run it."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument('mode', nargs='?', default='setup', choices=('setup',))
    parser.parse_args(argv)
    try:
        setup(os.environ)
    except (subprocess.CalledProcessError, OSError, ValueError) as error:
        print(f'startup: error: {error}', file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        raise SystemExit(130) from None
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
