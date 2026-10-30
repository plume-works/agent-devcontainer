"""
The fixture repository and the per-test clones the IWE workflow suite runs in.

The fixture repository is built once per worker from ``HEAD``: every active plan
cancelled, the fixture plans committed as ``base``, and the open-question edit
committed on top as ``open_question``, and, on a branch from ``base``, every
fixture plan but the loop plan cancelled and the pair plan added beside it as
``implement_all``, and, on another,
the catalog's revision evaluator replaced by a stub that rejects every revision
as ``stub_evaluator``, and, on a third, the planner replaced by a stub that
always drafts the revise plan's narrowing as ``stub_planner``. Each test gets
its own clone of it; a main clone also gets ``main``, a bare ``origin`` beside
it, and a stub ``gh``.
"""

from dataclasses import dataclass
import os
from pathlib import Path
import re
import shutil
import subprocess

FIXTURES = Path(__file__).parent / 'fixtures'
DATA = 'docs/knowledge/data'
HELLO = f'{DATA}/plans/20261008-e2e-hello.md'
GREET = f'{DATA}/plans/20261008-e2e-greet.md'
BRANCH = f'{DATA}/plans/20261025-e2e-branch.md'
LOOP = f'{DATA}/plans/20261026-e2e-loop.md'
REVISE = f'{DATA}/plans/20261026-e2e-revise.md'
CONFLICT = f'{DATA}/plans/20261027-e2e-conflict.md'
PAIR = f'{DATA}/plans/20261027-e2e-pair.md'
EVALUATOR_AGENT = '.agents/plugins/agentdev/agents/iwe-revision-evaluator.agent.md'
PLANNER_AGENT = '.agents/plugins/agentdev/agents/iwe-planner.agent.md'
UNRELEASED = f'{DATA}/releases/unreleased.md'
FIXTURE_PLANS = (
    'plans/20261008-e2e-hello.md',
    'plans/20261008-e2e-greet.md',
    'plans/20261025-e2e-branch.md',
    'plans/20261026-e2e-loop.md',
    'plans/20261026-e2e-revise.md',
    'plans/20261027-e2e-conflict.md',
)
MARKER = 'published.marker'
# An untracked file no fixture plan claims, so Verify sees a dirty worktree.
STRAY = 'e2e/stray.txt'
GREET_TASK = re.compile(r'^- \[ \] Write `e2e/greet\.txt`', re.MULTILINE)
TICKED_WITH_EVIDENCE = re.compile(
    r'^- \[x\] .*\n(?:  .*\n)*?  - \*\*Evidence:\*\* \S', re.MULTILINE
)
TASK_HEADING = re.compile(r'^### Task \d+', re.MULTILINE)
# The sections that state a plan's intent; ticks, evidence, and results live elsewhere.
INTENT_SECTIONS = ('## Approach', '## Spec changes', '## Verification', '## Out of scope')
_HUB_LINK = re.compile(r'^\[.*\]\((plans/[^)]*\.md)\)$')
_ACTIVE_LINKS = (
    '[E2E hello fixture](plans/20261008-e2e-hello.md)',
    '[E2E greet fixture](plans/20261008-e2e-greet.md)',
    '[E2E branch fixture](plans/20261025-e2e-branch.md)',
    '[E2E loop fixture](plans/20261026-e2e-loop.md)',
    '[E2E revise fixture](plans/20261026-e2e-revise.md)',
    '[E2E conflict fixture](plans/20261027-e2e-conflict.md)',
)
_PAIR_LINK = '[E2E pair fixture](plans/20261027-e2e-pair.md)'
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
    implement_all: str
    stub_evaluator: str
    stub_planner: str


def cancel_active_plans(data: Path, keep: tuple[str, ...] = ()) -> list[str]:
    """Cancel every ``## Active`` plan except those in ``keep``."""
    hub = data / 'plans.md'
    # iwe normalize wraps long link titles over several lines, so match paragraphs.
    paragraphs = [p for p in re.split(r'\n[ \t]*\n', hub.read_text().strip('\n')) if p]
    section, kept, moved, keys = '', [], [], []
    for paragraph in paragraphs:
        if paragraph.startswith('## '):
            section = paragraph
        link = _HUB_LINK.match(paragraph.replace('\n', ' '))
        if section == '## Active' and link and link.group(1) not in keep:
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
    shutil.copy2(FIXTURES / 'plans/20261025-e2e-branch.md', path / BRANCH)
    shutil.copy2(FIXTURES / 'plans/20261026-e2e-loop.md', path / LOOP)
    shutil.copy2(FIXTURES / 'plans/20261026-e2e-revise.md', path / REVISE)
    shutil.copy2(FIXTURES / 'plans/20261027-e2e-conflict.md', path / CONFLICT)
    _activate_fixtures(data)
    repo.iwe_check()
    base = repo.commit_all('e2e fixtures')

    shutil.copy2(FIXTURES / 'plans/20261008-e2e-hello.open-question.md', path / HELLO)
    repo.iwe_check()
    open_question = repo.commit_all('e2e: open question')

    repo.git('checkout', '-q', '-b', 'e2e-loop-only', base)
    cancel_active_plans(data, keep=('plans/20261026-e2e-loop.md',))
    shutil.copy2(FIXTURES / 'plans/20261027-e2e-pair.md', path / PAIR)
    hub = data / 'plans.md'
    hub.write_text(hub.read_text().replace('## Active\n', f'## Active\n\n{_PAIR_LINK}\n', 1))
    repo.iwe_check()
    implement_all = repo.commit_all('e2e: only the loop and pair plans active')

    repo.git('checkout', '-q', '-b', 'e2e-stub-evaluator', base)
    shutil.copy2(FIXTURES / 'agents/iwe-revision-evaluator.stub.md', path / EVALUATOR_AGENT)
    stub_evaluator = repo.commit_all('e2e: stub evaluator rejects every revision')

    repo.git('checkout', '-q', '-b', 'e2e-stub-planner', base)
    shutil.copy2(FIXTURES / 'agents/iwe-planner.narrowing-stub.md', path / PLANNER_AGENT)
    shutil.copy2(FIXTURES / 'e2e/revise.narrowed.md', path / 'e2e')
    stub_planner = repo.commit_all('e2e: stub planner drafts the narrowing')
    repo.git('checkout', '-q', 'e2e-fixture')
    return FixtureRepo(
        path=path,
        base=base,
        open_question=open_question,
        implement_all=implement_all,
        stub_evaluator=stub_evaluator,
        stub_planner=stub_planner,
    )


def plan_intent(text: str) -> tuple[list[str], dict[str, str]]:
    """Return a plan's task headings and the text of each of its intent sections."""
    sections = {}
    for heading in INTENT_SECTIONS:
        found = re.search(
            rf'^{re.escape(heading)}\n(.*?)(?=^## |\Z)', text, re.MULTILINE | re.DOTALL
        )
        sections[heading] = found.group(1).strip() if found else ''
    return TASK_HEADING.findall(text), sections


class Clone(Repo):
    """One test's clone, with the facts the scenarios assert read from it."""

    def __init__(self, path: Path, start: str, base: str, tool_dir: Path | None = None) -> None:
        """Wrap the clone at ``path``, checked out at ``start``; ``tool_dir`` leads its PATH."""
        super().__init__(path)
        self.start = start
        self.base = base
        self.tool_dir = tool_dir

    def agent_path(self, path: str) -> str:
        """Return the PATH an agent in this clone runs with, given the inherited ``path``."""
        return path if self.tool_dir is None else f'{self.tool_dir}{os.pathsep}{path}'

    @property
    def remote(self) -> Path:
        """Where a main clone's bare ``origin`` lives: beside the clone."""
        return self.path.parent / 'remote.git'

    def branch(self) -> str:
        """Return the checked-out branch."""
        return self.git('branch', '--show-current').strip()

    def local_branches(self) -> list[str]:
        """Return every local branch name."""
        return self.git('for-each-ref', '--format=%(refname:short)', 'refs/heads/').split()

    def remote_has(self, branch: str) -> bool:
        """Whether the bare ``origin`` holds ``branch``."""
        listing = _run(['git', 'ls-remote', '--heads', str(self.remote), branch], self.path)
        return listing.strip() != ''

    def gh_calls(self) -> str:
        """Return every call the stub ``gh`` logged; empty when none."""
        log = None if self.tool_dir is None else self.tool_dir / 'gh-calls.log'
        return log.read_text() if log is not None and log.exists() else ''

    @property
    def marker(self) -> Path:
        """Where ``bin/publish-e2e.sh`` writes its marker: beside the clone."""
        return self.path.parent / MARKER

    def has_marker(self) -> bool:
        """Whether the publish step ran."""
        return self.marker.exists()

    def remove_marker(self) -> None:
        """Forget an earlier publish, so a later run's publish is observable."""
        self.marker.unlink(missing_ok=True)

    def add_stray(self) -> None:
        """Leave an untracked file in the worktree."""
        (self.path / STRAY).write_text('stray\n')

    def saved_report(self, key: str) -> str | None:
        """Return the saved Verify report for plan ``key``, or ``None`` when none was saved."""
        report = self.path / '.tmp/verify' / f'{Path(key).name}.md'
        return report.read_text() if report.exists() else None

    def saved_prompt(self, key: str, field: str) -> str | None:
        """Return the ``field`` block scalar of plan ``key``'s saved report, or ``None``."""
        report = self.saved_report(key)
        block = re.search(rf'^{field}: \|2-\n((?:  .*\n|\n)*)', report or '', re.MULTILINE)
        return None if block is None else re.sub(r'^  ', '', block.group(1), flags=re.MULTILINE)

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

    def loop_done(self) -> bool:
        """Whether the loop task is ticked with an evidence line and its file holds ``loop``."""
        return self._plain_done(LOOP, 'loop')

    def pair_done(self) -> bool:
        """Whether the pair task is ticked with an evidence line and its file holds ``pair``."""
        return self._plain_done(PAIR, 'pair')

    def _plain_done(self, plan: str, word: str) -> bool:
        ticked = TICKED_WITH_EVIDENCE.search((self.path / plan).read_text()) is not None
        written = self.path / f'e2e/{word}.txt'
        return ticked and written.exists() and written.read_text().strip() == word

    def revise_tasks_committed(self) -> tuple[int, int]:
        """Return the revise plan's task count at ``base`` and at ``HEAD``."""
        before = self.git('show', f'{self.base}:{REVISE}')
        after = self.git('show', f'HEAD:{REVISE}')
        return len(TASK_HEADING.findall(before)), len(TASK_HEADING.findall(after))

    def revise_files(self) -> bool:
        """Whether both files the revise fixture's spec outcome names exist."""
        return all(
            (self.path / f'e2e/{name}').exists() for name in ('revise.txt', 'revise-notes.txt')
        )

    def draft_revision(self, variant: str) -> None:
        """Copy the revise plan's ``variant`` fixture over it, uncommitted, as a draft."""
        shutil.copy2(FIXTURES / f'plans/20261026-e2e-revise.{variant}.md', self.path / REVISE)

    def revision_kept(self, variant: str) -> bool:
        """Whether the revise plan still holds the ``variant`` draft, unrestored and unedited."""
        draft = (FIXTURES / f'plans/20261026-e2e-revise.{variant}.md').read_text()
        return (self.path / REVISE).read_text() == draft

    def intent_kept(self, plan: str) -> bool:
        """Whether ``plan``'s intent at ``HEAD`` matches ``base``, with no uncommitted edit."""
        before = plan_intent(self.git('show', f'{self.base}:{plan}'))
        after = plan_intent(self.git('show', f'HEAD:{plan}'))
        return before == after and self.git('status', '--porcelain', '--', plan) == ''

    def conflict_text(self) -> str | None:
        """Return the conflict fixture's file, stripped, or ``None`` when it was never written."""
        written = self.path / 'e2e/conflict.txt'
        return written.read_text().strip() if written.exists() else None

    def revise_notes_written(self) -> bool:
        """Whether the file no task of the revise fixture writes exists."""
        return (self.path / 'e2e/revise-notes.txt').exists()

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


def make_main_clone(fixture: FixtureRepo, parent: Path, start: str) -> Clone:
    """Clone ``fixture`` on ``main``, pushed to a bare ``origin`` beside it, with a stub ``gh``."""
    plain = make_clone(fixture, parent, start)
    plain.git('checkout', '-q', '-B', 'main')
    _run(['git', 'clone', '-q', '--bare', str(plain.path), str(plain.remote)], parent)
    plain.git('remote', 'add', 'origin', str(plain.remote))
    plain.git('fetch', '-q', 'origin')
    plain.git('remote', 'set-head', 'origin', 'main')
    tools = parent / 'tools'
    tools.mkdir()
    shutil.copy2(FIXTURES / 'bin/gh', tools / 'gh')
    return Clone(plain.path, start=start, base=fixture.base, tool_dir=tools)
