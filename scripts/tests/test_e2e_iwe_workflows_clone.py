"""The IWE workflow suite's per-test clones are isolated and refuse foreign repositories."""

import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).parents[2]
_spec = importlib.util.spec_from_file_location(
    'e2e_iwe_workflows_clone', REPO_ROOT / 'scripts/e2e/iwe-workflows/clone.py'
)
clone_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(clone_module)


@pytest.fixture(scope='module')
def work():
    """Provide a scratch directory under /tmp for this module's repositories."""
    path = TMP_ROOT / f'e2e-iwe-workflows-clone-{uuid.uuid4().hex}'
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path)


@pytest.fixture(scope='module')
def fixture(work):
    """Build the fixture repository from this checkout's ``HEAD``."""
    return clone_module.build_fixture_repo(REPO_ROOT, work / 'fixture')


def active_plans(data: Path) -> list[str]:
    """Return the plan keys whose frontmatter carries no ``stage``."""
    return sorted(
        f'plans/{plan.name}'
        for plan in (data / 'plans').glob('*.md')
        if not re.search(r'^stage:', plan.read_text(), re.MULTILINE)
    )


def test_fixtures_are_the_only_active_plans(fixture, work):
    """Every other active plan is cancelled in its own frontmatter, and the fixtures are listed."""
    clone = clone_module.make_clone(fixture, work / 'only-active', fixture.base)
    data = clone.path / clone_module.DATA
    assert active_plans(data) == sorted(clone_module.FIXTURE_PLANS)
    for key in active_plans(REPO_ROOT / clone_module.DATA):
        plan = (data / key).read_text()
        assert '\nstage: cancelled\n' in plan, key
        assert not re.search(r'^rank:', plan, re.MULTILINE), key
    hub = (data / 'plans.md').read_text().replace('\n', ' ')
    for key in clone_module.FIXTURE_PLANS:
        assert f']({key})' in hub, key
    assert clone.plan_active()
    assert clone.greet_untouched()
    assert clone.status() == ''


def test_shared_diff_covers_hubs_releases_and_log_only(fixture, work):
    """A plan edit is not a shared change; a hub, release page, or log edit is."""
    clone = clone_module.make_clone(fixture, work / 'shared', fixture.base)
    data = clone.path / clone_module.DATA
    (clone.path / clone_module.HELLO).write_text(clone.hello() + '\nedited\n')
    assert clone.shared_diff() == ''
    for path in ('plans.md', 'log.md', 'releases.md', 'releases/1.0.0.md'):
        target = data / path
        original = target.read_text()
        target.write_text(original + '\nedited\n')
        assert path in clone.shared_diff(), path
        target.write_text(original)


def test_add_hub_links_keeps_the_hub_sorted(work):
    """A link lands before the first member whose key sorts after it, date prefix ignored."""
    hub = work / 'sorted-hub.md'
    hub.write_text(
        '# Plans\n\n[A](plans/20260101-alpha.md)\n\n[C wrapped\ntitle](plans/gamma.md)\n'
    )
    clone_module.add_hub_links(hub, ('[B](plans/20991231-beta.md)', '[Z](plans/zeta.md)'))
    assert re.findall(r'\(([^)]*)\)', hub.read_text()) == [
        'plans/20260101-alpha.md',
        'plans/20991231-beta.md',
        'plans/gamma.md',
        'plans/zeta.md',
    ]


def test_base_and_open_question_commits(fixture, work):
    """``open_question`` edits only the hello plan on top of ``base``."""
    clone = clone_module.make_clone(fixture, work / 'commits', fixture.open_question)
    assert clone.head() == fixture.open_question
    changed = clone.git('diff', '--name-only', fixture.base, fixture.open_question).split()
    assert changed == [clone_module.HELLO]
    assert clone.shared_diff() == ''


def test_clones_share_no_commits_or_marker(fixture, work):
    """A commit or a publish in one clone never shows up in another."""
    first = clone_module.make_clone(fixture, work / 'first', fixture.base)
    second = clone_module.make_clone(fixture, work / 'second', fixture.base)
    (first.path / 'e2e/extra.txt').write_text('extra\n')
    commit = first.commit_all('only in first')
    subprocess.run([str(first.path / 'bin/publish-e2e.sh')], cwd=first.path, check=True)

    assert first.has_marker()
    assert not second.has_marker()
    assert second.head() == fixture.base
    missing = subprocess.run(
        ['git', '-C', str(second.path), 'cat-file', '-e', f'{commit}^{{commit}}'],
        capture_output=True,
        check=False,
    )
    assert missing.returncode != 0
    assert second.git('remote') == ''


def test_git_refuses_a_path_outside_its_own_repository(fixture, work):
    """A clone whose path resolves into another repository refuses every git command."""
    clone = clone_module.make_clone(fixture, work / 'refuse', fixture.base)
    nested = clone_module.Clone(clone.path / 'e2e', start=fixture.base, base=fixture.base)
    with pytest.raises(clone_module.CloneRefused):
        nested.git('status')
    with pytest.raises(clone_module.CloneRefused):
        nested.commit_all('must not land')
    assert clone.head() == fixture.base


def test_each_test_gets_its_own_work_directory(monkeypatch):
    """Same-named tests in different modules or checkouts never share a clone directory."""
    suite = REPO_ROOT / 'scripts/e2e/iwe-workflows'
    monkeypatch.syspath_prepend(str(suite))
    monkeypatch.setitem(sys.modules, 'clone', clone_module)
    spec = importlib.util.spec_from_file_location(
        'e2e_iwe_workflows_conftest', suite / 'conftest.py'
    )
    conftest = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(conftest)

    prefix = 'scripts/e2e/iwe-workflows/test_iwe_workflows_'
    names = {conftest.work_dir_name(f'{prefix}{h}.py::test_ship') for h in ('opencode', 'claude')}
    assert names == {
        'test_iwe_workflows_opencode-test_ship',
        'test_iwe_workflows_claude-test_ship',
    }
    assert conftest.work_dir_name(f'{prefix}claude.py::test_x[a/b c]') == (
        'test_iwe_workflows_claude-test_x_a_b_c_'
    )
    assert conftest.WORK == conftest.work_root(REPO_ROOT)
    roots = {conftest.work_root(Path(f'/workspaces/{name}')) for name in ('one', 'two')}
    assert len(roots) == 2
    assert all(root.parent.parent == TMP_ROOT / 'e2e' for root in roots)
    assert all(root.name == 'iwe-workflows' for root in roots)


def test_main_clone_has_a_remote_and_a_stub_gh(fixture, work):
    """A main clone sits on ``main``, pushed to a bare origin, with only the stub gh on PATH."""
    clone = clone_module.make_main_clone(fixture, work / 'main', fixture.base)
    assert clone.branch() == 'main'
    assert clone.head() == fixture.base
    assert clone.git('remote', 'get-url', 'origin').strip() == str(clone.remote)
    assert (
        clone.git('symbolic-ref', '--short', 'refs/remotes/origin/HEAD').strip() == 'origin/main'
    )
    assert clone.remote_has('main')
    assert clone.agent_path('/usr/bin').split(os.pathsep) == [str(clone.tool_dir), '/usr/bin']

    script = clone.path / '.agents/plugins/agentdev/skills/iwe-branch-name/agent-code'
    named = subprocess.run(
        [str(script / 'iwe-branch-name.py'), 'next', 'data/plans/20261025-e2e-branch', '--phase',
         'impl'],
        cwd=clone.path,
        capture_output=True,
        text=True,
        check=False,
        env={**os.environ, 'PATH': clone.agent_path(os.environ['PATH'])},
    )  # fmt: skip
    assert named.stdout.splitlines()[-1] == 'RESULT=SUCCESS', named.stderr
    assert 'NEXT=iwe/e2e-branch/iter-1-impl' in named.stdout.splitlines()
    assert f'--repo {clone.remote}' in clone.gh_calls()
    assert clone.local_branches() == ['e2e-fixture', 'main']


def test_plain_clones_have_no_tool_dir(fixture, work):
    """Only a main clone changes the agent's PATH."""
    clone = clone_module.make_clone(fixture, work / 'plain', fixture.base)
    assert clone.tool_dir is None
    assert clone.agent_path('/usr/bin') == '/usr/bin'
    assert clone.gh_calls() == ''


def test_implement_all_commit_keeps_the_loop_and_pair_plans(fixture, work):
    """``implement_all`` leaves exactly the loop and pair plans active, both unimplemented."""
    clone = clone_module.make_clone(fixture, work / 'implement-all', fixture.implement_all)
    assert active_plans(clone.path / clone_module.DATA) == [
        'plans/20261026-e2e-loop.md',
        'plans/20261027-e2e-pair.md',
    ]
    assert not clone.loop_done()
    assert not clone.pair_done()
    assert clone.status() == ''
