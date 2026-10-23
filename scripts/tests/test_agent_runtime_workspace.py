"""Tests for runtime-workspace.sh: reuse, clone, project preparation, and catalog choice."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / '.devcontainer/scripts'
REAL_SCRIPTS = (
    'runtime-workspace.sh',
    'setup-git-safe-directory.sh',
    'uv-sync.sh',
    'setup-pre-commit.sh',
)
STUBBED_SCRIPTS = ('setup-gh-credential-helper.sh', 'setup-agent-state.sh')
SECRET = 'hunter2-not-for-logs'
GIT_ID = ['-c', 'user.name=t', '-c', 'user.email=t@example.invalid']


class Runtime:
    """A copied script tree, fake tools, and an isolated Git/global state."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.scripts = root / 'scripts'
        self.bin = root / 'bin'
        self.home = root / 'home'
        self.workspace = root / 'workspace'
        self.log = root / 'calls.log'
        for directory in (self.scripts, self.bin, self.home, self.workspace):
            directory.mkdir(parents=True)
        for name in REAL_SCRIPTS:
            shutil.copy2(SCRIPTS / name, self.scripts / name)
        for name in STUBBED_SCRIPTS:
            self.stub(self.scripts / name, name)
        for tool in ('uv', 'pre-commit'):
            self.stub(self.bin / tool, tool)
        (root / 'gitconfig').touch()

    def stub(self, path: Path, label: str) -> None:
        variable = 'STUB_EXIT_' + label.split('.')[0].replace('-', '_').upper()
        path.write_text(
            f'#!/usr/bin/env bash\necho "{label} $*" >> "{self.log}"\nexit "${{{variable}:-0}}"\n'
        )
        path.chmod(0o755)

    def env(self, **extra: str) -> dict[str, str]:
        return {
            'PATH': f'{self.bin}:/usr/local/bin:/usr/bin:/bin',
            'HOME': str(self.home),
            'GIT_CONFIG_GLOBAL': str(self.root / 'gitconfig'),
            'GIT_CONFIG_NOSYSTEM': '1',
            'DEV_WORKSPACE_FOLDER': str(self.workspace),
            'AGENTDEV_RUNTIME_MODE': 'standalone',
            'AGENTDEV_CATALOG_DIR': str(self.root / 'image-catalog'),
            **extra,
        }

    def run(self, *args: str, **extra: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [self.scripts / 'runtime-workspace.sh', *args],
            env=self.env(**extra),
            capture_output=True,
            text=True,
            timeout=120,
        )

    def calls(self) -> list[str]:
        return self.log.read_text().splitlines() if self.log.exists() else []

    def git(self, *args: str, cwd: Path | None = None) -> str:
        return subprocess.run(
            ['git', *GIT_ID, *args],
            cwd=cwd or self.workspace,
            env=self.env(),
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()


@pytest.fixture
def runtime(tmp_path: Path) -> Runtime:
    return Runtime(tmp_path)


def make_remote(runtime: Runtime, name: str = 'remote.git') -> Path:
    """Create a bare repository with one commit on main and a release tag."""
    seed = runtime.root / f'{name}-seed'
    seed.mkdir()
    runtime.git('init', '-q', '-b', 'main', cwd=seed)
    (seed / 'README.md').write_text('hello\n')
    runtime.git('add', '.', cwd=seed)
    runtime.git('commit', '-qm', 'init', cwd=seed)
    runtime.git('tag', 'v1', cwd=seed)
    runtime.git('switch', '-qc', 'feature', cwd=seed)
    remote = runtime.root / name
    runtime.git('clone', '-q', '--bare', str(seed), str(remote), cwd=runtime.root)
    return remote


def test_first_start_clones_after_configuring_github_credentials(runtime: Runtime):
    remote = make_remote(runtime)
    result = runtime.run(
        'checkout', AGENTDEV_REPOSITORY_URL=f'file://{remote}', AGENTDEV_REPOSITORY_REF='v1'
    )
    assert result.returncode == 0, result.stderr
    assert (runtime.workspace / 'README.md').read_text() == 'hello\n'
    assert runtime.git('describe', '--tags') == 'v1'
    assert runtime.calls() == ['setup-gh-credential-helper.sh ']


def test_valid_checkout_wins_without_network_and_dirty_state_survives(runtime: Runtime):
    remote = make_remote(runtime)
    runtime.git('clone', '-q', '-b', 'feature', f'file://{remote}', '.')
    (runtime.workspace / 'README.md').write_text('edited\n')
    (runtime.workspace / 'scratch.txt').write_text('untracked\n')
    before = (runtime.git('rev-parse', 'HEAD'), runtime.git('status', '--porcelain'))
    shutil.rmtree(remote)

    result = runtime.run('checkout', AGENTDEV_REPOSITORY_URL='file:///nonexistent.git')
    assert result.returncode == 0, result.stderr
    assert runtime.git('branch', '--show-current') == 'feature'
    assert (runtime.git('rev-parse', 'HEAD'), runtime.git('status', '--porcelain')) == before
    assert not (runtime.workspace / '.git/FETCH_HEAD').exists()
    assert runtime.calls() == []


def test_empty_workspace_without_url_fails(runtime: Runtime):
    result = runtime.run('checkout')
    assert result.returncode == 1
    assert 'AGENTDEV_REPOSITORY_URL is not set' in result.stderr


def test_nonempty_non_checkout_fails_without_deleting(runtime: Runtime):
    (runtime.workspace / 'notes.txt').write_text('keep')
    result = runtime.run('checkout', AGENTDEV_REPOSITORY_URL='file:///x.git')
    assert result.returncode == 1
    assert 'is not empty and is not a Git checkout' in result.stderr
    assert (runtime.workspace / 'notes.txt').read_text() == 'keep'


def test_interrupted_clone_is_refused_without_deletion(runtime: Runtime):
    marker = runtime.home / '.local/state/agentdev/clone-in-progress'
    marker.parent.mkdir(parents=True)
    marker.touch()
    (runtime.workspace / '.git').mkdir()
    (runtime.workspace / '.git/partial').write_text('half')
    result = runtime.run('checkout', AGENTDEV_REPOSITORY_URL='file:///x.git')
    assert result.returncode == 1
    assert 'interrupted' in result.stderr
    assert (runtime.workspace / '.git/partial').read_text() == 'half'


def test_missing_worktree_metadata_is_reported(runtime: Runtime):
    main = runtime.root / 'main-repo'
    main.mkdir()
    runtime.git('init', '-q', '-b', 'main', cwd=main)
    (main / 'f').write_text('x')
    runtime.git('add', '.', cwd=main)
    runtime.git('commit', '-qm', 'init', cwd=main)
    runtime.workspace.rmdir()
    runtime.git('worktree', 'add', '-q', str(runtime.workspace), '-b', 'wt', cwd=main)
    shutil.rmtree(main / '.git')

    result = runtime.run('checkout')
    assert result.returncode == 1
    assert 'is not available; mount the main repository' in result.stderr
    assert (runtime.workspace / 'f').exists()


def test_clone_errors_do_not_leak_credentials(runtime: Runtime):
    url = f'https://user:{SECRET}@127.0.0.1:9/private.git'
    result = runtime.run('checkout', AGENTDEV_REPOSITORY_URL=url)
    assert result.returncode == 1
    assert SECRET not in result.stdout + result.stderr
    assert 'https://***@127.0.0.1:9/private.git' in result.stdout


def test_foreign_owned_checkout_is_trusted_once(runtime: Runtime):
    if os.geteuid() != 0:
        pytest.skip('changing ownership requires root')
    runtime.git('init', '-q')
    os.chown(runtime.workspace, 4321, 4321)
    for _ in range(2):
        result = runtime.run('checkout')
        assert result.returncode == 0, result.stderr
    trusted = runtime.git('config', '--global', '--get-all', 'safe.directory', cwd=runtime.root)
    assert trusted.splitlines() == [str(runtime.workspace)]


@pytest.mark.parametrize(
    ('files', 'expected'),
    [
        ((), []),
        (('pyproject.toml',), ['uv sync --all-groups --all-extras']),
        (
            ('.pre-commit-config.yaml',),
            [
                'pre-commit install --hook-type=pre-commit --hook-type=pre-push '
                '--hook-type=pre-merge-commit',
            ],
        ),
    ],
)
def test_project_setup_runs_only_for_present_configuration(runtime: Runtime, files, expected):
    runtime.git('init', '-q')
    for name in files:
        (runtime.workspace / name).write_text('')
    result = runtime.run('project')
    assert result.returncode == 0, result.stderr
    assert runtime.calls() == expected


@pytest.mark.parametrize(
    ('files', 'stub'),
    [
        ('pyproject.toml', 'uv'),
        ('.pre-commit-config.yaml', 'pre-commit'),
    ],
)
def test_project_setup_failures_fail_startup(runtime: Runtime, files, stub):
    runtime.git('init', '-q')
    (runtime.workspace / files).write_text('')
    result = runtime.run('project', **{f'STUB_EXIT_{stub.replace("-", "_").upper()}': '3'})
    assert result.returncode != 0


def test_standalone_skips_the_venv_migration(runtime: Runtime):
    runtime.git('init', '-q')
    (runtime.workspace / 'pyproject.toml').write_text('')
    (runtime.workspace / '.venv').symlink_to('/uv/venvs/old')
    assert runtime.run('project').returncode == 0
    assert (runtime.workspace / '.venv').is_symlink()


def test_custom_hooks_and_hooks_path_are_conflicts(runtime: Runtime):
    runtime.git('init', '-q')
    (runtime.workspace / '.pre-commit-config.yaml').write_text('')
    hook = runtime.workspace / '.git/hooks/pre-push'
    hook.write_text('#!/bin/sh\necho mine\n')
    result = runtime.run('project')
    assert result.returncode == 1
    assert 'pre-push is a custom hook' in result.stderr
    assert hook.read_text() == '#!/bin/sh\necho mine\n'

    hook.unlink()
    runtime.git('config', 'core.hooksPath', '.githooks')
    result = runtime.run('project')
    assert result.returncode == 1
    assert 'core.hooksPath is set to .githooks' in result.stderr
    assert runtime.calls() == []


def test_regenerated_pre_commit_hooks_are_not_conflicts(runtime: Runtime):
    runtime.git('init', '-q')
    (runtime.workspace / '.pre-commit-config.yaml').write_text('')
    (runtime.workspace / '.git/hooks/pre-commit').write_text('# File generated by pre-commit\n')
    assert runtime.run('project').returncode == 0


@pytest.mark.skipif(
    not shutil.which('pre-commit') or not shutil.which('unshare') or os.geteuid() != 0,
    reason='requires pre-commit and a root network namespace',
)
def test_standalone_hook_registration_builds_no_environment_offline(runtime: Runtime):
    runtime.git('init', '-q')
    shutil.copy2(REPO_ROOT / '.pre-commit-config.yaml', runtime.workspace)
    (runtime.bin / 'pre-commit').unlink()
    cache = runtime.root / 'pre-commit-home'
    cache.mkdir()
    result = subprocess.run(
        ['unshare', '-n', runtime.scripts / 'setup-pre-commit.sh'],
        env=runtime.env(
            PATH=f'{Path(shutil.which("pre-commit")).parent}:/usr/bin:/bin',
            PRE_COMMIT_HOME=str(cache),
        ),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    for hook in ('pre-commit', 'pre-push', 'pre-merge-commit'):
        assert (
            'File generated by pre-commit' in (runtime.workspace / '.git/hooks' / hook).read_text()
        )
    assert not [path for path in cache.iterdir() if path.name.startswith('repo')]


def ship_catalog(root: Path) -> None:
    for manifest in ('.claude-plugin/marketplace.json', '.agents/plugins/marketplace.json'):
        (root / manifest).parent.mkdir(parents=True, exist_ok=True)
        (root / manifest).write_text('{}')
    (root / '.agents/plugins/agentdev/.opencode-plugin').mkdir(parents=True)


def test_checkout_catalog_wins_when_complete(runtime: Runtime):
    ship_catalog(runtime.workspace)
    (runtime.root / 'image-catalog').mkdir()
    assert runtime.run('catalog').returncode == 0
    assert runtime.calls() == [f'setup-agent-state.sh catalog {runtime.workspace} user']


def test_image_catalog_is_used_otherwise(runtime: Runtime):
    (runtime.workspace / '.claude-plugin').mkdir()
    (runtime.workspace / '.claude-plugin/marketplace.json').write_text('{}')
    (runtime.root / 'image-catalog').mkdir()
    assert runtime.run('catalog').returncode == 0
    assert runtime.calls() == [
        f'setup-agent-state.sh catalog {runtime.root / "image-catalog"} user'
    ]


def test_devcontainer_helpers_keep_their_defaults(runtime: Runtime):
    runtime.git('init', '-q')
    result = subprocess.run(
        [runtime.scripts / 'setup-pre-commit.sh'],
        capture_output=True,
        text=True,
        env=runtime.env(AGENTDEV_RUNTIME_MODE='', STUB_EXIT_PRE_COMMIT='3'),
    )
    assert result.returncode == 0
    assert 'pre-commit install failed' in result.stdout


@pytest.mark.skipif(
    not all(shutil.which(tool) for tool in ('claude', 'codex', 'jq')),
    reason='requires the Claude and Codex CLIs',
)
def test_switching_catalogs_replaces_managed_registrations_only(tmp_path: Path):
    image_catalog = tmp_path / 'image-catalog'
    for part in ('.claude-plugin', '.agents/plugins'):
        shutil.copytree(REPO_ROOT / part, image_catalog / part, symlinks=True)
    home = tmp_path / 'home'
    (home / '.codex/agents').mkdir(parents=True)
    (home / '.codex/agents/mine.toml').write_text('name = "mine"\n')
    (home / '.config/opencode').mkdir(parents=True)
    (home / '.config/opencode/opencode.json').write_text('{"plugin": ["other"], "theme": "x"}')
    env = {
        'PATH': os.environ['PATH'],
        'HOME': str(home),
        'CODEX_HOME': str(home / '.codex'),
        'XDG_CONFIG_HOME': str(home / '.config'),
    }

    def register(catalog: Path) -> None:
        result = subprocess.run(
            [SCRIPTS / 'setup-agent-state.sh', 'catalog', str(catalog), 'user'],
            env=env,
            capture_output=True,
            text=True,
            timeout=300,
        )
        assert result.returncode == 0, result.stdout + result.stderr

    def registered() -> tuple[list[str], list[str], dict]:
        claude = subprocess.run(
            ['claude', 'plugin', 'marketplace', 'list', '--json'],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        codex = subprocess.run(
            ['codex', 'plugin', 'marketplace', 'list', '--json'],
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
        opencode = json.loads((home / '.config/opencode/opencode.json').read_text())
        return (
            [m['path'] for m in json.loads(claude.stdout)],
            [m['root'] for m in json.loads(codex.stdout)['marketplaces']],
            opencode,
        )

    register(REPO_ROOT)
    register(image_catalog)

    claude, codex, opencode = registered()
    assert claude == [str(image_catalog)]
    assert codex == [str(image_catalog)]
    bridge = str(image_catalog / '.agents/plugins/agentdev/.opencode-plugin')
    assert opencode == {'plugin': ['other', bridge], 'theme': 'x'}
    assert (home / '.codex/agents/mine.toml').read_text() == 'name = "mine"\n'
    assert (home / '.codex/agents/agentdev-iwe-implementer.toml').exists()
