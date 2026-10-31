#!/usr/bin/env python3

"""Behavior tests for iwe-verify's verify-cache.py lookup and save."""

from __future__ import annotations

from pathlib import Path
import re
import shutil
import subprocess
import sys

from git_fixtures import git, outcome
import pytest

PLAN = 'data/plans/20260101-focus-timer'
REPORT = 'Ready to ship data/plans/20260101-focus-timer\n\n- Findings: none\n'
SKILL_REQUEST = '/agentdev:iwe-verify data/plans/20260101-focus-timer'
VERIFIER_PROMPT = 'Plan key: data/plans/20260101-focus-timer\n\nApprovals: none.'
PROMPTS = ('--skill-request', SKILL_REQUEST, '--verifier-prompt', VERIFIER_PROMPT)


@pytest.fixture
def installed_verify(plugin_root: Path, plugin_tmp_path: Path) -> Path:
    """Copy the iwe-verify skill and shared `bin/` into an isolated plugin layout."""
    installed = plugin_tmp_path / 'installed-plugin'
    shutil.copytree(plugin_root / 'bin', installed / 'bin')
    shutil.copytree(plugin_root / 'skills' / 'iwe-verify', installed / 'skills' / 'iwe-verify')
    return installed


@pytest.fixture
def repository(plugin_tmp_path: Path) -> Path:
    """Create a repository with one commit."""
    path = plugin_tmp_path / 'repository'
    path.mkdir()
    git(path, 'init', '--quiet', '--initial-branch=main')
    (path / 'README.md').write_text('# Project\n', encoding='utf-8')
    git(path, 'add', 'README.md')
    git(path, 'commit', '--quiet', '-m', 'Initial commit')
    return path


def run_cache(
    installed: Path, repository: Path, *arguments: str, stdin: str = ''
) -> tuple[subprocess.CompletedProcess[str], dict[str, str]]:
    """Run verify-cache.py in `repository`, returning the process and its key=value lines."""
    script = installed / 'skills' / 'iwe-verify' / 'agent-code' / 'verify-cache.py'
    completed = subprocess.run(
        [sys.executable, str(script), *arguments],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
        input=stdin,
    )
    values = dict(line.split('=', 1) for line in completed.stdout.splitlines() if '=' in line)
    return completed, values


def save_current(
    installed: Path, repository: Path, target: str = PLAN, prompts: tuple[str, ...] = PROMPTS
) -> dict[str, str]:
    """Look up `target`, expect a miss, and save REPORT for the commit it printed."""
    completed, values = run_cache(installed, repository, 'lookup', target)
    assert outcome(completed) == (4, 'RESULT=MISS')
    completed, saved = run_cache(
        installed,
        repository,
        'save',
        target,
        '--commit',
        values['COMMIT'],
        '--verdict',
        'Ready to ship',
        *prompts,
        stdin=REPORT,
    )
    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    return saved


def block_scalars(report: Path) -> dict[str, str]:
    """Read the `key: |2-` literal blocks from a saved report's frontmatter."""
    match = re.match(r'---\n(.*?)\n---\n', report.read_text(encoding='utf-8'), re.DOTALL)
    assert match is not None
    frontmatter = match.group(1)
    blocks: dict[str, list[str]] = {}
    current = None
    for line in frontmatter.splitlines():
        if line.endswith(': |2-'):
            current = line.removesuffix(': |2-')
            blocks[current] = []
        elif current is not None and (line.startswith('  ') or not line):
            blocks[current].append(line[2:])
        else:
            current = None
    return {key: '\n'.join(lines) for key, lines in blocks.items()}


def commit_change(repository: Path) -> None:
    """Add a commit so HEAD moves."""
    (repository / 'README.md').write_text('# Project\n\nChanged.\n', encoding='utf-8')
    git(repository, 'commit', '--quiet', '-am', 'Change')


def test_saved_report_for_head_is_a_hit(installed_verify: Path, repository: Path) -> None:
    """A report saved for HEAD and the active catalog comes back with its commit and verdict."""
    saved = save_current(installed_verify, repository)

    completed, values = run_cache(installed_verify, repository, 'lookup', PLAN)

    assert outcome(completed) == (3, 'RESULT=HIT')
    assert values['REPORT'] == saved['REPORT']
    assert values['COMMIT'] == git(repository, 'rev-parse', 'HEAD')
    assert values['VERDICT'] == 'Ready to ship'
    assert Path(values['REPORT']).read_text(encoding='utf-8').endswith(REPORT)


def test_plan_file_path_and_key_share_one_report(installed_verify: Path, repository: Path) -> None:
    """A plan's file path and its key name the same saved report."""
    save_current(installed_verify, repository)

    completed, _ = run_cache(installed_verify, repository, 'lookup', f'docs/knowledge/{PLAN}.md')

    assert outcome(completed) == (3, 'RESULT=HIT')


def test_new_commit_is_a_miss(installed_verify: Path, repository: Path) -> None:
    """A saved report for an earlier commit does not match a moved HEAD."""
    save_current(installed_verify, repository)
    commit_change(repository)

    completed, values = run_cache(installed_verify, repository, 'lookup', PLAN)

    assert outcome(completed) == (4, 'RESULT=MISS')
    assert values['COMMIT'] == git(repository, 'rev-parse', 'HEAD')
    assert values['CATALOG_DIGEST'].startswith('sha256:')


def test_changed_catalog_is_a_miss(installed_verify: Path, repository: Path) -> None:
    """Changing any file of the active catalog invalidates the saved report."""
    save_current(installed_verify, repository)
    (installed_verify / 'skills' / 'iwe-verify' / 'SKILL.md').write_text(
        'changed\n', encoding='utf-8'
    )

    completed, _ = run_cache(installed_verify, repository, 'lookup', PLAN)

    assert outcome(completed) == (4, 'RESULT=MISS')


def test_bytecode_cache_leaves_the_catalog_digest_unchanged(
    installed_verify: Path, repository: Path
) -> None:
    """A __pycache__ directory inside the catalog is not part of its digest."""
    save_current(installed_verify, repository)
    cache = installed_verify / 'bin' / '__pycache__'
    cache.mkdir(exist_ok=True)
    (cache / 'stray.pyc').write_bytes(b'bytecode')

    completed, _ = run_cache(installed_verify, repository, 'lookup', PLAN)

    assert outcome(completed) == (3, 'RESULT=HIT')


def test_fresh_is_a_miss(installed_verify: Path, repository: Path) -> None:
    """--fresh reports a miss even when the saved report matches."""
    save_current(installed_verify, repository)

    completed, _ = run_cache(installed_verify, repository, 'lookup', PLAN, '--fresh')

    assert outcome(completed) == (4, 'RESULT=MISS')


def test_save_overwrites_the_previous_report(installed_verify: Path, repository: Path) -> None:
    """Each save replaces the one saved report for the plan."""
    first = save_current(installed_verify, repository)
    commit_change(repository)
    second = save_current(installed_verify, repository)

    assert first['REPORT'] == second['REPORT']
    saved = list((repository / '.tmp' / 'verify').glob('*.md'))
    assert [path.name for path in saved] == ['20260101-focus-timer.md']
    assert f'commit: {git(repository, "rev-parse", "HEAD")}' in saved[0].read_text(
        encoding='utf-8'
    )


def test_audit_mode_uses_its_own_report(installed_verify: Path, repository: Path) -> None:
    """Audit mode saves to audit.md, apart from any plan's report."""
    saved = save_current(installed_verify, repository, 'audit')

    assert Path(saved['REPORT']) == repository / '.tmp' / 'verify' / 'audit.md'
    completed, _ = run_cache(installed_verify, repository, 'lookup', PLAN)
    assert outcome(completed) == (4, 'RESULT=MISS')


def test_saved_report_does_not_dirty_the_worktree(
    installed_verify: Path, repository: Path
) -> None:
    """The cache directory ignores itself, so a repository not ignoring .tmp/ stays clean."""
    save_current(installed_verify, repository)

    assert git(repository, 'status', '--porcelain') == ''


@pytest.mark.parametrize('kind', ['tracked', 'untracked'])
@pytest.mark.parametrize('command', ['lookup', 'save'])
def test_dirty_worktree_stops_both_commands(
    installed_verify: Path, repository: Path, kind: str, command: str
) -> None:
    """A tracked change or an unignored untracked file stops lookup and save."""
    head = git(repository, 'rev-parse', 'HEAD')
    if kind == 'tracked':
        (repository / 'README.md').write_text('edited\n', encoding='utf-8')
    else:
        (repository / 'new.txt').write_text('new\n', encoding='utf-8')
    arguments = ['lookup', PLAN]
    if command == 'save':
        arguments = ['save', PLAN, '--commit', head, '--verdict', 'Blocked', *PROMPTS]

    completed, _ = run_cache(installed_verify, repository, *arguments, stdin=REPORT)

    assert outcome(completed) == (5, 'RESULT=DIRTY_WORKTREE')
    assert not (repository / '.tmp' / 'verify').exists()


def test_save_refuses_a_moved_head(installed_verify: Path, repository: Path) -> None:
    """Saving under a commit HEAD no longer points at is refused."""
    stale = git(repository, 'rev-parse', 'HEAD')
    commit_change(repository)

    completed, _ = run_cache(
        installed_verify,
        repository,
        'save',
        PLAN,
        '--commit',
        stale,
        '--verdict',
        'Blocked',
        *PROMPTS,
        stdin=REPORT,
    )

    assert outcome(completed) == (6, 'RESULT=HEAD_MOVED')
    assert not (repository / '.tmp' / 'verify').exists()


def test_save_refuses_needs_decision(installed_verify: Path, repository: Path) -> None:
    """A Needs decision report is never saved."""
    head = git(repository, 'rev-parse', 'HEAD')

    completed, _ = run_cache(
        installed_verify,
        repository,
        'save',
        PLAN,
        '--commit',
        head,
        '--verdict',
        'Needs decision',
        *PROMPTS,
        stdin=REPORT,
    )

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert not (repository / '.tmp' / 'verify').exists()


def test_outside_a_repository_is_a_preflight_error(
    installed_verify: Path, plugin_tmp_path: Path
) -> None:
    """Running outside a git repository stops before any lookup."""
    outside = plugin_tmp_path / 'outside'
    outside.mkdir()

    completed, _ = run_cache(installed_verify, outside, 'lookup', PLAN)

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')


def test_help_prints_the_results_table(installed_verify: Path, repository: Path) -> None:
    """--help is the run's product and lists every declared result with its code."""
    completed, _ = run_cache(installed_verify, repository, '--help')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    for row in ('HIT                3', 'MISS               4', 'DIRTY_WORKTREE     5'):
        assert row in completed.stdout


def test_save_records_both_prompts_verbatim(installed_verify: Path, repository: Path) -> None:
    """Multi-line prompts with a colon and quotes survive into the frontmatter, and still hit."""
    skill_request = "/agentdev:iwe-verify data/plans/x — I approve: 'e2e'"
    verifier_prompt = (
        'Plan key: data/plans/x\n\nApprovals:\n  - "I approve running `bin/e2e.sh`."\n---'
    )
    saved = save_current(
        installed_verify,
        repository,
        prompts=('--skill-request', skill_request, '--verifier-prompt', verifier_prompt),
    )

    assert block_scalars(Path(saved['REPORT'])) == {
        'skill_request': skill_request,
        'verifier_prompt': verifier_prompt,
    }
    completed, values = run_cache(installed_verify, repository, 'lookup', PLAN)
    assert outcome(completed) == (3, 'RESULT=HIT')
    assert values['VERDICT'] == 'Ready to ship'


@pytest.mark.parametrize('prompt', ['-h', '--help'])
def test_help_flag_as_a_prompt_value_is_saved(
    installed_verify: Path, repository: Path, prompt: str
) -> None:
    """A prompt that reads exactly like a help flag is saved, not taken as a help request."""
    saved = save_current(
        installed_verify,
        repository,
        prompts=('--skill-request', prompt, '--verifier-prompt', VERIFIER_PROMPT),
    )

    assert block_scalars(Path(saved['REPORT']))['skill_request'] == prompt


@pytest.mark.parametrize('missing', ['--skill-request', '--verifier-prompt'])
def test_save_requires_both_prompts(
    installed_verify: Path, repository: Path, missing: str
) -> None:
    """Saving without either prompt is a usage error and writes nothing."""
    head = git(repository, 'rev-parse', 'HEAD')
    prompts = dict(zip(PROMPTS[::2], PROMPTS[1::2], strict=True))
    del prompts[missing]
    flags = [part for flag, value in prompts.items() for part in (flag, value)]

    completed, _ = run_cache(
        installed_verify,
        repository,
        'save',
        PLAN,
        '--commit',
        head,
        '--verdict',
        'Blocked',
        *flags,
        stdin=REPORT,
    )

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert not (repository / '.tmp' / 'verify').exists()
