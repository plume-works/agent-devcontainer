"""Drive the gitleaks pre-commit hook's entry in each of its three scan modes."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import secrets
import shlex
import shutil
import string
import subprocess
from uuid import uuid4

import pytest
from scratch import TMP_ROOT
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG = REPO_ROOT / '.pre-commit-config.yaml'
MODE_VARIABLES = ('GITLEAKS_LOG_OPTS', 'PRE_COMMIT_FROM_REF', 'PRE_COMMIT_TO_REF')

pytestmark = pytest.mark.skipif(shutil.which('gitleaks') is None, reason='gitleaks not on PATH')


def hook_command() -> list[str]:
    """Return the gitleaks hook's command as pre-commit runs it."""
    for repo in yaml.safe_load(CONFIG.read_text())['repos']:
        for hook in repo['hooks']:
            if hook['id'] == 'gitleaks':
                assert hook.get('pass_filenames') is False
                return [*shlex.split(hook['entry']), *hook.get('args', [])]
    raise AssertionError('no gitleaks hook in .pre-commit-config.yaml')


def fake_token() -> str:
    """Return a GitHub token-shaped secret built at run time, so none is committed here."""
    alphabet = string.ascii_letters + string.digits
    return 'ghp_' + ''.join(secrets.choice(alphabet) for _ in range(36))


@dataclass(frozen=True)
class History:
    """A scratch repository whose range adds a secret in one commit and removes it in the next."""

    root: Path
    base: str
    head: str

    def git(self, *arguments: str) -> str:
        """Run Git in the repository with a fixed identity and return its stdout."""
        identity = ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid']
        return subprocess.run(
            ['git', *identity, *arguments],
            cwd=self.root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def commit(self, text: str) -> str:
        """Commit config.txt with the given text and return the commit's SHA."""
        (self.root / 'config.txt').write_text(text)
        self.git('add', 'config.txt')
        self.git('commit', '--quiet', '-m', 'change')
        return self.git('rev-parse', 'HEAD')

    def run_hook(self, **variables: str) -> subprocess.CompletedProcess[str]:
        """Run the hook in the repository with only the given mode variables set."""
        env = {k: v for k, v in os.environ.items() if k not in MODE_VARIABLES}
        return subprocess.run(
            hook_command(),
            cwd=self.root,
            env={**env, **variables},
            capture_output=True,
            text=True,
            check=False,
        )


@pytest.fixture
def history(monkeypatch: pytest.MonkeyPatch) -> Iterator[History]:
    """Create base, a commit adding a secret, and head, which removes it again."""
    for name in ('GIT_DIR', 'GIT_INDEX_FILE', 'GIT_WORK_TREE'):
        monkeypatch.delenv(name, raising=False)
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'gitleaks-hook-{uuid4().hex}'
    root.mkdir()
    try:
        repo = History(root, '', '')
        repo.git('init', '--quiet', '--initial-branch=main')
        base = repo.commit('clean\n')
        repo.commit(f'token = {fake_token()}\n')
        head = repo.commit('clean again\n')
        yield History(root, base, head)
    finally:
        shutil.rmtree(root)


def test_log_opts_range_finds_a_secret_removed_inside_it(history: History) -> None:
    """GITLEAKS_LOG_OPTS scans every commit's patch, not only the range's end state."""
    result = history.run_hook(GITLEAKS_LOG_OPTS=f'{history.base}..{history.head}')
    assert result.returncode != 0, result.stdout + result.stderr


def test_log_opts_takes_precedence_over_push_refs(history: History) -> None:
    """A clean GITLEAKS_LOG_OPTS range wins over a push range that holds the secret."""
    result = history.run_hook(
        GITLEAKS_LOG_OPTS=f'-1 {history.head}',
        PRE_COMMIT_FROM_REF=history.base,
        PRE_COMMIT_TO_REF=history.head,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_push_refs_scan_every_pushed_commit(history: History) -> None:
    """At pre-push, the hook scans PRE_COMMIT_FROM_REF..PRE_COMMIT_TO_REF."""
    result = history.run_hook(PRE_COMMIT_FROM_REF=history.base, PRE_COMMIT_TO_REF=history.head)
    assert result.returncode != 0, result.stdout + result.stderr


def test_push_refs_outside_the_secret_pass(history: History) -> None:
    """A pushed range that never held the secret passes."""
    result = history.run_hook(PRE_COMMIT_FROM_REF=history.base, PRE_COMMIT_TO_REF=history.base)
    assert result.returncode == 0, result.stdout + result.stderr


def test_commit_scans_the_staged_change(history: History) -> None:
    """With no range, the hook scans the staged change: clean passes, a staged secret fails."""
    assert history.run_hook().returncode == 0

    (history.root / 'config.txt').write_text(f'token = {fake_token()}\n')
    history.git('add', 'config.txt')
    result = history.run_hook()
    assert result.returncode != 0, result.stdout + result.stderr
