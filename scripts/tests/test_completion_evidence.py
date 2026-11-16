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
# A hook exports these variables. If the fixture gets one of them from its parent, Git in the fixture uses the outer repository.
GIT_VARIABLES = ('GIT_DIR', 'GIT_INDEX_FILE', 'GIT_WORK_TREE')
IDENTITY = (
    '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
    '-c', 'commit.gpgsign=false',
)  # fmt: skip


@dataclass(frozen=True)
class Repository:
    """A fixture repository with one plan."""

    root: Path

    def env(self) -> dict[str, str]:
        """Return the environment with no inherited Git location."""
        return {k: v for k, v in os.environ.items() if k not in GIT_VARIABLES}

    def git(self, *arguments: str) -> str:
        """Run Git in the repository with a fixed identity and no hooks."""
        return subprocess.run(
            ['git', *IDENTITY, '-c', 'core.hooksPath=/dev/null', *arguments],
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

    def hooked_commit(
        self, hooks: Path, *arguments: str, editor: str = ':', settings: tuple[str, ...] = ()
    ) -> subprocess.CompletedProcess[str]:
        """Run `git commit` with the script as its `commit-msg` hook."""
        options = [*IDENTITY, *settings, '-c', f'core.hooksPath={hooks}']
        return subprocess.run(
            ['git', *options, 'commit', '--quiet', *arguments],
            cwd=self.root,
            env={**self.env(), 'GIT_EDITOR': editor},
            capture_output=True,
            text=True,
            check=False,
        )

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

    def check_push(self, from_ref: str) -> subprocess.CompletedProcess[str]:
        """Run `check-push` on the range from `from_ref` to `HEAD`, as pre-commit gives it."""
        env = {**self.env(), 'PRE_COMMIT_FROM_REF': from_ref, 'PRE_COMMIT_TO_REF': 'HEAD'}
        return subprocess.run(
            [sys.executable, str(SCRIPT), 'check-push'],
            cwd=self.root,
            env=env,
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
    """Give an empty directory under the scratch root of the tests."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'completion-evidence-{uuid4().hex}'
    root.mkdir()
    yield root
    shutil.rmtree(root)


@pytest.fixture
def hooks(scratch: Path) -> Path:
    """Give a hooks directory whose `commit-msg` hook runs `check-message`."""
    directory = scratch / 'hooks'
    directory.mkdir()
    hook = directory / 'commit-msg'
    hook.write_text(f'#!/bin/sh\nexec "{sys.executable}" "{SCRIPT}" check-message "$1"\n')
    hook.chmod(0o755)
    return directory


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
    """A commit with one ticked task and a block with text is valid."""
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


def test_evidence_like_a_trailer_passes(repo: Repository) -> None:
    """A block whose one line looks like `Key: value` is evidence, not a trailer paragraph."""
    repo.tick('First task.')

    result = repo.check('Do the first task\n\n---\ncompletion evidence:\npytest: 14 passed\n')

    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    'setting', ['diff.mnemonicPrefix=true', 'diff.noprefix=true', 'diff.dstPrefix=new/']
)
def test_diff_prefix_config_does_not_hide_a_tick(repo: Repository, setting: str) -> None:
    """The hook finds a tick with each diff configuration of the user."""
    repo.git('config', *setting.split('='))
    repo.tick('First task.')

    result = repo.check('Do the first task\n')

    assert result.returncode == 1
    assert f'{PLAN}: First task.' in result.stderr


@pytest.mark.parametrize(
    ('tasks', 'arguments', 'passes'),
    [
        ((), ('-m', 'Shorten the message'), False),
        (('Second task.',), ('--no-edit',), False),
        ((), ('--no-edit',), True),
    ],
)
def test_amend_checks_the_ticks_of_the_amended_commit(
    repo: Repository, hooks: Path, tasks: tuple[str, ...], arguments: tuple[str, ...], passes: bool
) -> None:
    """The hook checks an amend against the parent of the commit that the amend replaces."""
    repo.tick('First task.')
    repo.commit(f'Do the first task\n\n{BLOCK}')
    repo.tick(*tasks)

    result = repo.hooked_commit(hooks, '--amend', *arguments)

    assert (result.returncode == 0) is passes, result.stderr


@pytest.mark.parametrize(
    ('settings', 'arguments'),
    [((), ('-v',)), (('-c', 'core.commentChar=;'), ('-v',)), (('-c', 'core.commentChar=;'), ())],
)
def test_editor_text_after_the_block_is_not_evidence(
    repo: Repository, hooks: Path, settings: tuple[str, ...], arguments: tuple[str, ...]
) -> None:
    """Comment lines and the diff below the scissors line are not the text of a block."""
    repo.tick('First task.')
    editor = (
        'sh -c \'{ printf "Do the first task\\n\\n---\\ncompletion evidence:\\n"; cat "$1"; }'
        ' > "$1.new" && mv "$1.new" "$1"\' editor'
    )

    result = repo.hooked_commit(hooks, *arguments, editor=editor, settings=settings)

    assert result.returncode == 1, result.stderr
    assert f'{PLAN}: First task.' in result.stderr


def test_two_ticks_fail(repo: Repository) -> None:
    """One block cannot show which text is for which plan task."""
    repo.tick('First task.', 'Second task.')

    result = repo.check(f'Do two tasks\n\n{BLOCK}')

    assert result.returncode == 1
    assert 'First task.' in result.stderr
    assert 'Second task.' in result.stderr


def test_no_tick_needs_no_block(repo: Repository) -> None:
    """A commit that changes a plan but ticks no task needs no block."""
    path = repo.root / PLAN
    path.write_text(path.read_text() + '- [ ] Fourth task.\n')
    repo.git('add', PLAN)

    assert repo.check('Add a task\n').returncode == 0


def test_merge_in_progress_is_skipped(repo: Repository) -> None:
    """A merge moves ticks from other commits, so its message needs no block."""
    repo.git('switch', '--quiet', '-c', 'topic')
    repo.tick('First task.', 'Second task.')
    repo.commit(f'Tick two tasks\n\n{BLOCK}')
    repo.git('switch', '--quiet', 'main')
    repo.git('merge', '--quiet', '--no-ff', '--no-commit', 'topic')

    assert (repo.root / '.git' / 'MERGE_HEAD').exists()
    assert repo.check('Merge topic\n').returncode == 0


def test_show_prints_each_tick(repo: Repository, scratch: Path) -> None:
    """`show` prints each tick of a pull request with its block, oldest first, and none of main."""
    origin = scratch / 'origin.git'
    subprocess.run(['git', 'init', '--quiet', '--bare', str(origin)], check=True)
    repo.git('remote', 'add', 'origin', str(origin))
    repo.git('switch', '--quiet', '-c', 'topic')
    repo.tick('First task.')
    repo.commit('Do the first task\n\n---\ncompletion evidence:\nFirst evidence.\n')
    repo.git('switch', '--quiet', 'main')
    repo.tick('Third task.')
    repo.commit('Do the third task\n\n---\ncompletion evidence:\nMain evidence.\n')
    repo.git('switch', '--quiet', 'topic')
    repo.git('merge', '--quiet', '--no-edit', 'main')
    repo.tick('Second task.')
    repo.commit('Do the second task\n\n---\ncompletion evidence:\nSecond evidence.\n')
    repo.git('push', '--quiet', 'origin', 'main', 'topic:refs/pull/7/head')

    result = repo.run('show', '7')

    assert result.returncode == 0, result.stderr
    output = result.stdout
    assert 'Main evidence.' not in output
    assert 'Third task.' not in output
    first = output.index(f'ticks {PLAN}: First task.')
    second = output.index(f'ticks {PLAN}: Second task.')
    assert first < output.index('First evidence.') < second < output.index('Second evidence.')


def test_push_tick_without_block_fails(repo: Repository) -> None:
    """A pushed commit that ticks a plan task with no block stops the push."""
    base = repo.git('rev-parse', 'HEAD')
    repo.tick('First task.')
    repo.commit('Do the first task\n')
    commit = repo.git('rev-parse', '--short=12', 'HEAD')

    result = repo.check_push(base)

    assert result.returncode == 1
    assert commit in result.stderr
    assert f'{PLAN}: First task.' in result.stderr


def test_push_amended_two_ticks_fail(repo: Repository) -> None:
    """A pushed commit that an amend made with a second tick stops the push."""
    base = repo.git('rev-parse', 'HEAD')
    repo.tick('First task.')
    repo.commit(f'Do the first task\n\n{BLOCK}')
    repo.tick('Second task.')
    repo.git('commit', '--quiet', '--amend', '--no-edit')

    result = repo.check_push(base)

    assert result.returncode == 1
    assert f'{PLAN}: First task.' in result.stderr
    assert f'{PLAN}: Second task.' in result.stderr


def test_push_valid_range_passes(repo: Repository) -> None:
    """Commits with one tick and a block each, and a merge commit, pass the push."""
    base = repo.git('rev-parse', 'HEAD')
    repo.git('switch', '--quiet', '-c', 'topic')
    repo.tick('First task.')
    repo.commit(f'Do the first task\n\n{BLOCK}')
    repo.git('switch', '--quiet', 'main')
    repo.tick('Third task.')
    repo.commit(f'Do the third task\n\n{BLOCK}')
    repo.git('switch', '--quiet', 'topic')
    repo.git('merge', '--quiet', '--no-edit', 'main')
    repo.tick('Second task.')
    repo.commit(f'Do the second task\n\n{BLOCK}')

    result = repo.check_push(base)

    assert result.returncode == 0, result.stderr
