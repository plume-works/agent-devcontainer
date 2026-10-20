"""
The fixture repository and the per-test clones the IWE workflow suite runs in.

The fixture repository is built once per worker from ``HEAD``: every active plan
cancelled, the fixture plans committed as ``base``, and the open-question edit
committed on top as ``open_question``. Each test gets its own clone of it.
"""

from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import subprocess

FIXTURES = Path(__file__).parent / 'fixtures'
DATA = 'docs/knowledge/data'
HELLO = f'{DATA}/plans/20261008-e2e-hello.md'
GREET = f'{DATA}/plans/20261008-e2e-greet.md'
UNRELEASED = f'{DATA}/releases/unreleased.md'
FIXTURE_PLANS = ('plans/20261008-e2e-hello.md', 'plans/20261008-e2e-greet.md')
MARKER = 'published.marker'
GREET_TASK = re.compile(r'^- \[ \] Write `e2e/greet\.txt`', re.MULTILINE)
_HUB_LINK = re.compile(r'^\[.*\]\((plans/[^)]*\.md)\)$')
_ACTIVE_LINKS = (
    '[E2E hello fixture](plans/20261008-e2e-hello.md)',
    '[E2E greet fixture](plans/20261008-e2e-greet.md)',
)
_AUTHOR = ('-c', 'user.name=e2e', '-c', 'user.email=e2e@example.invalid')


class CloneRefused(RuntimeError):
    """A git command would have run outside the clone's own repository."""


def _run(args: list[str], cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(f'{" ".join(args)} failed in {cwd}:\n{result.stderr}{result.stdout}')
    return result.stdout


class Repo:
    """A repository the suite owns; every git command refuses any other one."""

    def __init__(self, path: Path) -> None:
        """Wrap the repository rooted at ``path``."""
        self.path = path.resolve()

    def git(self, *args: str) -> str:
        """Run git in this repository, refusing when it resolves to another one."""
        top = subprocess.run(
            ['git', '-C', str(self.path), 'rev-parse', '--show-toplevel'],
            capture_output=True,
            text=True,
            check=False,
        )
        if top.returncode != 0 or Path(top.stdout.strip()).resolve() != self.path:
            raise CloneRefused(f'refusing: {self.path} is not its own repository')
        return _run(['git', '-C', str(self.path), *args], self.path)

    def commit_all(self, message: str) -> str:
        """Commit every change, hooks skipped, and return the new ``HEAD``."""
        self.git('add', '-A')
        self.git(*_AUTHOR, 'commit', '-q', '--no-verify', '-m', message)
        return self.head()

    def head(self) -> str:
        """Return the commit ``HEAD`` points at."""
        return self.git('rev-parse', 'HEAD').strip()

    def iwe_check(self) -> None:
        """Normalize the graph and fail unless its schema validates."""
        _run(['iwe', 'normalize'], self.path)
        _run(['iwe', 'schema', 'validate'], self.path)


@dataclass(frozen=True)
class FixtureRepo:
    """The once-per-worker repository every clone is made from."""

    path: Path
    base: str
    open_question: str


def cancel_active_plans(data: Path) -> list[str]:
    """Move every ``## Active`` plan to ``## Cancelled`` and mark it cancelled."""
    hub = data / 'plans.md'
    # iwe normalize wraps long link titles over several lines, so match paragraphs.
    paragraphs = [p for p in re.split(r'\n[ \t]*\n', hub.read_text().strip('\n')) if p]
    section, kept, moved, keys = '', [], [], []
    for paragraph in paragraphs:
        if paragraph.startswith('## '):
            section = paragraph
        link = _HUB_LINK.match(paragraph.replace('\n', ' '))
        if section == '## Active' and link:
            keys.append(link.group(1))
            moved.append(paragraph.replace('\n', ' '))
            continue
        kept.append(paragraph)
        if paragraph == '## Cancelled':
            kept.extend(moved)
    hub.write_text('\n\n'.join(kept) + '\n')
    for key in keys:
        plan = data / key
        plan.write_text(
            plan.read_text().replace(
                '\ntype: plan\n', '\ntype: plan\nstage: cancelled\nstatus: deprecated\n', 1
            )
        )
    return keys


def _activate_fixtures(data: Path) -> None:
    hub = data / 'plans.md'
    text = hub.read_text()
    entries = ''.join(f'\n{link}\n' for link in _ACTIVE_LINKS)
    hub.write_text(text.replace('## Active\n', f'## Active\n{entries}', 1))


def build_fixture_repo(source: Path, work: Path) -> FixtureRepo:
    """Build the fixture repository from ``source``'s ``HEAD`` under ``work``."""
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True)
    bundle = work / 'repo.bundle'
    _run(['git', '-C', str(source), 'bundle', 'create', str(bundle), 'HEAD'], source)
    path = work / 'repo'
    _run(['git', '-c', 'advice.detachedHead=false', 'clone', '-q', str(bundle), str(path)], work)
    repo = Repo(path)
    repo.git('remote', 'remove', 'origin')
    repo.git('checkout', '-q', '-b', 'e2e-fixture')

    data = path / DATA
    cancel_active_plans(data)
    (path / 'bin').mkdir(exist_ok=True)
    (path / 'e2e').mkdir(exist_ok=True)
    shutil.copy2(FIXTURES / 'bin/publish-e2e.sh', path / 'bin')
    shutil.copy2(FIXTURES / 'e2e/hello.txt', path / 'e2e')
    shutil.copy2(FIXTURES / 'plans/20261008-e2e-hello.md', path / HELLO)
    shutil.copy2(FIXTURES / 'plans/20261008-e2e-greet.md', path / GREET)
    _activate_fixtures(data)
    repo.iwe_check()
    base = repo.commit_all('e2e fixtures')

    shutil.copy2(FIXTURES / 'plans/20261008-e2e-hello.open-question.md', path / HELLO)
    repo.iwe_check()
    open_question = repo.commit_all('e2e: open question')
    return FixtureRepo(path=path, base=base, open_question=open_question)


class Clone(Repo):
    """One test's clone, with the facts the scenarios assert read from it."""

    def __init__(self, path: Path, start: str, base: str) -> None:
        """Wrap the clone at ``path``, checked out at ``start``."""
        super().__init__(path)
        self.start = start
        self.base = base

    @property
    def marker(self) -> Path:
        """Where ``bin/publish-e2e.sh`` writes its marker: beside the clone."""
        return self.path.parent / MARKER

    def has_marker(self) -> bool:
        """Whether the publish step ran."""
        return self.marker.exists()

    def status(self) -> str:
        """Return ``git status --porcelain``; empty means a clean tree."""
        return self.git('status', '--porcelain')

    def hello(self) -> str:
        """Return the hello fixture plan's text."""
        return (self.path / HELLO).read_text()

    def plan_active(self) -> bool:
        """Whether the hello plan still has no stage."""
        return re.search(r'^stage:', self.hello(), re.MULTILINE) is None

    def plan_done(self) -> bool:
        """Whether the hello plan was shipped."""
        return re.search(r'^stage: done$', self.hello(), re.MULTILINE) is not None

    def unreleased_diff(self) -> str:
        """Return the release accumulator's diff against ``base``; empty when unchanged."""
        return self.git('diff', self.base, '--', UNRELEASED)

    def greet_untouched(self) -> bool:
        """Whether the greet task is still unticked and its file still absent."""
        task = GREET_TASK.search((self.path / GREET).read_text()) is not None
        return task and not (self.path / 'e2e/greet.txt').exists()


def make_clone(fixture: FixtureRepo, parent: Path, start: str) -> Clone:
    """Clone ``fixture`` to ``parent/clone`` at ``start``, with no remote to push to."""
    if parent.exists():
        shutil.rmtree(parent)
    parent.mkdir(parents=True)
    path = parent / 'clone'
    _run(['git', 'clone', '-q', '--no-hardlinks', str(fixture.path), str(path)], parent)
    clone = Clone(path, start=start, base=fixture.base)
    clone.git('remote', 'remove', 'origin')
    clone.git('reset', '-q', '--hard', start)
    return clone
