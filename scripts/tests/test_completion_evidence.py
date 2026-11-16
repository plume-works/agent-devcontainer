"""Run scripts/completion-evidence.py against fixture repositories."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess
import sys
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

SCRIPT = Path(__file__).resolve().parents[2] / 'scripts/completion-evidence.py'
PLAN = 'docs/knowledge/data/plans/20260101-fixture.md'
PLAN_TEXT = (
    '# Fixture\n\n## Implementation Steps\n\n'
    '- [ ] First task.\n- [ ] Second task.\n- [ ] Third task.\n'
)
BLOCK = '---\ncompletion evidence:\n`pytest` passed.\n'
# A hook exports these, and an inherited one points the fixture's Git at the outer repository.
GIT_VARIABLES = ('GIT_DIR', 'GIT_INDEX_FILE', 'GIT_WORK_TREE')


@dataclass(frozen=True)
class Repository:
    """A fixture repository with one plan."""

    root: Path

    def env(self) -> dict[str, str]:
        """Return the environment with no inherited Git location."""
        return {k: v for k, v in os.environ.items() if k not in GIT_VARIABLES}

    def git(self, *arguments: str) -> str:
        """Run Git in the repository with a fixed identity and no hooks."""
        options = [
            '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
            '-c', 'commit.gpgsign=false', '-c', 'core.hooksPath=/dev/null',
        ]  # fmt: skip
        return subprocess.run(
            ['git', *options, *arguments],
            cwd=self.root,
            env=self.env(),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()

    def tick(self, *tasks: str) -> None:
        """Tick plan tasks in the working tree and stage the plan."""
        path = self.root / PLAN
        text = path.read_text()
        for task in tasks:
            text = text.replace(f'- [ ] {task}', f'- [x] {task}')
        path.write_text(text)
        self.git('add', PLAN)

    def commit(self, message: str) -> None:
        """Commit the staged changes with a message."""
        self.git('commit', '--quiet', '-m', message)

    def run(self, *arguments: str) -> subprocess.CompletedProcess[str]:
        """Run the script in the repository."""
        return subprocess.run(
            [sys.executable, str(SCRIPT), *arguments],
            cwd=self.root,
            env=self.env(),
            capture_output=True,
            text=True,
            check=False,
        )

    def check(self, message: str) -> subprocess.CompletedProcess[str]:
        """Run `check-message` on a message file."""
        message_file = self.root / '.git' / 'COMMIT_EDITMSG'
        message_file.write_text(message)
        return self.run('check-message', str(message_file))


@pytest.fixture
def scratch() -> Iterator[Path]:
    """Yield an empty directory under the tests' scratch root."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'completion-evidence-{uuid4().hex}'
    root.mkdir()
    yield root
    shutil.rmtree(root)


@pytest.fixture
def repo(scratch: Path) -> Repository:
    """Return a repository on `main` whose one commit adds a plan with open tasks."""
    repository = Repository(scratch / 'work')
    repository.root.mkdir()
    repository.git('init', '--quiet', '--initial-branch=main')
    (repository.root / PLAN).parent.mkdir(parents=True)
    (repository.root / PLAN).write_text(PLAN_TEXT)
    repository.git('add', PLAN)
    repository.commit('Add the plan')
    return repository


def test_one_tick_with_block_passes(repo: Repository) -> None:
    """One ticked task and a block with text is a valid commit."""
    repo.tick('First task.')

    result = repo.check(f'Do the first task\n\n{BLOCK}\nCo-Authored-By: A <a@example.invalid>\n')

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize('message', ['Do the first task\n', 'Do the first task\n\n# ---\n'])
def test_tick_without_block_fails(repo: Repository, message: str) -> None:
    """A tick with no block fails and names the plan task."""
    repo.tick('First task.')

    result = repo.check(message)

    assert result.returncode == 1
    assert f'{PLAN}: First task.' in result.stderr


@pytest.mark.parametrize('footer', ['', '\n\n', '\nCo-Authored-By: A <a@example.invalid>\n'])
def test_tick_with_empty_block_fails(repo: Repository, footer: str) -> None:
    """A block with no text, or with only trailers, fails and names the plan task."""
    repo.tick('First task.')

    result = repo.check(f'Do the first task\n\n---\ncompletion evidence:\n{footer}')

    assert result.returncode == 1
    assert f'{PLAN}: First task.' in result.stderr
