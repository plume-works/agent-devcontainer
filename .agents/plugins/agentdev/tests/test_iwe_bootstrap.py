#!/usr/bin/env python3

"""Behavior tests for the iwe-bootstrap skill's helper script."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

import pytest

SCRIPT = Path('agent-code') / 'bootstrap-iwe.sh'
ASSETS = Path('assets')
# The transaction directory name is part of the skill's documented contract.
TRANSACTION = '.iwe-bootstrap.txn'
ONBOARDING_KEYS = ('fill-product-doc', 'capture-current-architecture')
KNOWLEDGE_INSTRUCTIONS = ('AGENTS.md', 'CLAUDE.md', 'SCHEMA.md', 'STRUCTURE.md')
# Commands the helper may run; everything else is absent from a restricted PATH.
HELPER_TOOLS = (
    'bash',
    'env',
    'git',
    'cp',
    'mv',
    'rm',
    'mkdir',
    'rmdir',
    'diff',
    'find',
    'cat',
    'dirname',
    'basename',
    'grep',
    'sed',
    'awk',
    'cmp',
    'sort',
    'ls',
    'kill',
    'sleep',
    'pwd',
    'tr',
    'head',
    'touch',
    'mktemp',
    'chmod',
    'realpath',
    'readlink',
)

requires_iwe = pytest.mark.skipif(
    shutil.which('iwe') is None, reason='the iwe CLI is not installed'
)


def run_bootstrap(
    skill: Path,
    *args: str,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run the installed helper and capture its contract output."""
    return subprocess.run(
        [str(skill / SCRIPT), *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        env=env,
        timeout=120,
    )


def outcome(completed: subprocess.CompletedProcess[str]) -> tuple[int, str]:
    """Return the (exit code, last stdout line) contract pair."""
    lines = completed.stdout.splitlines()
    return completed.returncode, lines[-1] if lines else ''


def output_values(completed: subprocess.CompletedProcess[str], key: str) -> list[str]:
    """Return every value printed for ``key`` on stdout."""
    prefix = f'{key}='
    return [
        line[len(prefix) :] for line in completed.stdout.splitlines() if line.startswith(prefix)
    ]


def snapshot(root: Path) -> dict[str, tuple[str, bytes | str | None, int]]:
    """Capture every path's type, content, and modification time under ``root``."""
    state: dict[str, tuple[str, bytes | str | None, int]] = {}
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root).as_posix()
        stat = path.lstat()
        if path.is_symlink():
            state[relative] = ('link', os.readlink(path), stat.st_mtime_ns)
        elif path.is_dir():
            state[relative] = ('dir', None, stat.st_mtime_ns)
        else:
            state[relative] = ('file', path.read_bytes(), stat.st_mtime_ns)
    return state


def tree_files(root: Path) -> dict[str, bytes]:
    """Map every regular file under ``root`` to its bytes."""
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in sorted(root.rglob('*'))
        if path.is_file() and not path.is_symlink()
    }


def run_iwe(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run the real iwe CLI from ``cwd``."""
    return subprocess.run(['iwe', *args], cwd=cwd, capture_output=True, text=True, check=False)


def install_scaffold(skill: Path, root: Path) -> None:
    """Place the packaged scaffold into ``root`` without running the helper."""
    shutil.copytree(skill / ASSETS / '.iwe', root / '.iwe')
    shutil.copytree(skill / ASSETS / 'docs', root / 'docs', dirs_exist_ok=True)


def restricted_path(directory: Path, *, extra: dict[str, str] | None = None) -> str:
    """Build a PATH holding only the helper's tools plus ``extra`` stub scripts."""
    directory.mkdir()
    for tool in HELPER_TOOLS:
        resolved = shutil.which(tool)
        if resolved is not None:
            (directory / tool).symlink_to(resolved)
    for name, body in (extra or {}).items():
        stub = directory / name
        if stub.exists() or stub.is_symlink():
            stub.unlink()
        stub.write_text(body, encoding='utf-8')
        stub.chmod(0o755)
    return str(directory)


def frontmatter_value(document: Path, field: str) -> str | None:
    """Read a scalar frontmatter field without a YAML dependency."""
    text = document.read_text(encoding='utf-8')
    _, block, _ = text.split('---\n', 2)
    for line in block.splitlines():
        if line.startswith(f'{field}:'):
            return line.split(':', 1)[1].strip()
    return None


def wait_for(path: Path, timeout: float = 30.0) -> None:
    """Poll until ``path`` exists."""
    deadline = time.monotonic() + timeout
    while not path.exists():
        if time.monotonic() > deadline:
            raise AssertionError(f'{path} never appeared')
        time.sleep(0.05)


@requires_iwe
def test_fresh_install_creates_the_packaged_scaffold(
    installed_iwe_bootstrap: Path, unrelated_repository: Path
) -> None:
    completed = run_bootstrap(installed_iwe_bootstrap, cwd=unrelated_repository)

    assert outcome(completed) == (0, 'RESULT=SUCCESS'), completed.stderr
    assert output_values(completed, 'ROOT') == [str(unrelated_repository.resolve())]
    assert output_values(completed, 'NEXT_SKILLS') == ['iwe-setup iwe-map']
    assets = installed_iwe_bootstrap / ASSETS
    assert tree_files(unrelated_repository / '.iwe') == tree_files(assets / '.iwe')
    assert tree_files(unrelated_repository / 'docs') == tree_files(assets / 'docs')
    assert sorted(path.name for path in unrelated_repository.iterdir()) == [
        '.git',
        '.iwe',
        'README.md',
        'docs',
    ]


@requires_iwe
def test_installed_graph_is_normalized_and_schema_valid(
    installed_iwe_bootstrap: Path, unrelated_repository: Path
) -> None:
    run_bootstrap(installed_iwe_bootstrap, cwd=unrelated_repository)
    before = tree_files(unrelated_repository / 'docs')

    validate = run_iwe('schema', 'validate', cwd=unrelated_repository)
    normalize = run_iwe('normalize', cwd=unrelated_repository)

    assert validate.returncode == 0, validate.stdout + validate.stderr
    assert normalize.returncode == 0, normalize.stdout + normalize.stderr
    assert tree_files(unrelated_repository / 'docs') == before


@requires_iwe
def test_installed_graph_carries_what_iwe_setup_needs(
    installed_iwe_bootstrap: Path, unrelated_repository: Path
) -> None:
    run_bootstrap(installed_iwe_bootstrap, cwd=unrelated_repository)
    knowledge = unrelated_repository / 'docs' / 'knowledge'

    for key in ONBOARDING_KEYS:
        task = knowledge / 'data' / 'backlog' / f'{key}.md'
        assert task.is_file(), f'{key} is missing; iwe-setup closes it by key'
        assert frontmatter_value(task, 'type') == 'task'
        assert frontmatter_value(task, 'stage') == 'planned'
    assert '✏️' in (knowledge / 'data' / 'product.md').read_text(encoding='utf-8')
    for name in KNOWLEDGE_INSTRUCTIONS:
        assert (knowledge / name).is_file(), name
    license_text = (knowledge / 'LICENSE.md').read_text(encoding='utf-8')
    assert 'MIT License' in license_text
    assert 'WITHOUT WARRANTY OF ANY KIND' in license_text


@requires_iwe
def test_repeated_run_reports_already_initialized_without_changes(
    installed_iwe_bootstrap: Path, unrelated_repository: Path
) -> None:
    run_bootstrap(installed_iwe_bootstrap, cwd=unrelated_repository)
    before = snapshot(unrelated_repository)

    completed = run_bootstrap(installed_iwe_bootstrap, cwd=unrelated_repository)

    assert outcome(completed) == (4, 'RESULT=ALREADY_INITIALIZED'), completed.stderr
    assert snapshot(unrelated_repository) == before


@requires_iwe
def test_onboarded_workspace_still_counts_as_initialized(
    installed_iwe_bootstrap: Path, unrelated_repository: Path
) -> None:
    run_bootstrap(installed_iwe_bootstrap, cwd=unrelated_repository)
    data = unrelated_repository / 'docs' / 'knowledge' / 'data'
    for example in data.rglob('*.example.md'):
        example.unlink()
    product = data / 'product.md'
    product.write_text(product.read_text(encoding='utf-8').replace('✏️', ''), encoding='utf-8')
    assert run_iwe('schema', 'validate', cwd=unrelated_repository).returncode == 0
    before = snapshot(unrelated_repository)

    completed = run_bootstrap(installed_iwe_bootstrap, cwd=unrelated_repository)

    assert outcome(completed) == (4, 'RESULT=ALREADY_INITIALIZED'), completed.stderr
    assert snapshot(unrelated_repository) == before


def _partial_iwe(skill: Path, root: Path) -> None:
    (root / '.iwe').mkdir()
    shutil.copy2(skill / ASSETS / '.iwe' / 'config.toml', root / '.iwe' / 'config.toml')


def _partial_knowledge(skill: Path, root: Path) -> None:
    data = root / 'docs' / 'knowledge' / 'data'
    data.mkdir(parents=True)
    (data / 'product.md').write_text('# Our product\n\nNotes we wrote.\n', encoding='utf-8')


def _incomplete_schemas(skill: Path, root: Path) -> None:
    install_scaffold(skill, root)
    (root / '.iwe' / 'schemas' / 'plan.yaml').unlink()


def _incompatible_workspace_path(skill: Path, root: Path) -> None:
    install_scaffold(skill, root)
    config = root / '.iwe' / 'config.toml'
    text = config.read_text(encoding='utf-8')
    config.write_text(text.replace('path = "docs/knowledge"', 'path = "notes"'), encoding='utf-8')


def _iwe_is_a_file(skill: Path, root: Path) -> None:
    (root / '.iwe').write_text('not a directory\n', encoding='utf-8')


def _docs_is_a_file(skill: Path, root: Path) -> None:
    (root / 'docs').write_text('not a directory\n', encoding='utf-8')


def _knowledge_is_a_file(skill: Path, root: Path) -> None:
    (root / 'docs').mkdir()
    (root / 'docs' / 'knowledge').write_text('not a directory\n', encoding='utf-8')


def _knowledge_is_a_symlink(skill: Path, root: Path) -> None:
    (root / 'elsewhere').mkdir()
    (root / 'docs').mkdir()
    (root / 'docs' / 'knowledge').symlink_to(root / 'elsewhere')


def _foreign_transaction(skill: Path, root: Path) -> None:
    (root / TRANSACTION).mkdir()
    (root / TRANSACTION / 'notes.txt').write_text('someone else owns this\n', encoding='utf-8')


@requires_iwe
@pytest.mark.parametrize(
    ('arrange', 'conflict_path'),
    [
        pytest.param(_partial_iwe, 'docs/knowledge', id='partial-iwe'),
        pytest.param(_partial_knowledge, '.iwe', id='partial-knowledge'),
        pytest.param(_incomplete_schemas, '.iwe/schemas/plan.yaml', id='incomplete-schemas'),
        pytest.param(_incompatible_workspace_path, '.iwe/config.toml', id='incompatible-config'),
        pytest.param(_iwe_is_a_file, '.iwe', id='iwe-file-collision'),
        pytest.param(_docs_is_a_file, 'docs', id='docs-file-collision'),
        pytest.param(_knowledge_is_a_file, 'docs/knowledge', id='knowledge-file-collision'),
        pytest.param(_knowledge_is_a_symlink, 'docs/knowledge', id='knowledge-symlink'),
        pytest.param(_foreign_transaction, TRANSACTION, id='foreign-transaction'),
    ],
)
def test_refusals_preserve_every_existing_byte(
    installed_iwe_bootstrap: Path,
    unrelated_repository: Path,
    arrange,
    conflict_path: str,
) -> None:
    arrange(installed_iwe_bootstrap, unrelated_repository)
    before = snapshot(unrelated_repository)

    completed = run_bootstrap(installed_iwe_bootstrap, cwd=unrelated_repository)

    assert outcome(completed) == (5, 'RESULT=RECONCILIATION_REQUIRED'), completed.stderr
    conflicts = output_values(completed, 'CONFLICT')
    assert any(entry.endswith(f':{conflict_path}') for entry in conflicts), conflicts
    assert snapshot(unrelated_repository) == before


def test_missing_iwe_stops_before_writing(
    installed_iwe_bootstrap: Path, unrelated_repository: Path, plugin_tmp_path: Path
) -> None:
    env = {**os.environ, 'PATH': restricted_path(plugin_tmp_path / 'bin')}
    (plugin_tmp_path / 'bin' / 'iwe').unlink(missing_ok=True)
    before = snapshot(unrelated_repository)

    completed = run_bootstrap(installed_iwe_bootstrap, cwd=unrelated_repository, env=env)

    assert outcome(completed) == (3, 'RESULT=MISSING_DEPENDENCY'), completed.stderr
    assert snapshot(unrelated_repository) == before


def test_validation_failure_leaves_the_repository_untouched(
    installed_iwe_bootstrap: Path, unrelated_repository: Path, plugin_tmp_path: Path
) -> None:
    failing_iwe = '#!/usr/bin/env bash\necho "schema violation" >&2\nexit 1\n'
    env = {
        **os.environ,
        'PATH': restricted_path(plugin_tmp_path / 'bin', extra={'iwe': failing_iwe}),
    }
    before = snapshot(unrelated_repository)

    completed = run_bootstrap(installed_iwe_bootstrap, cwd=unrelated_repository, env=env)

    assert outcome(completed) == (6, 'RESULT=VALIDATION_FAILED'), completed.stderr
    assert snapshot(unrelated_repository) == before


@requires_iwe
def test_interrupted_staging_is_discarded_on_the_next_run(
    installed_iwe_bootstrap: Path, unrelated_repository: Path, plugin_tmp_path: Path
) -> None:
    started = plugin_tmp_path / 'iwe-started'
    stalled_iwe = f'#!/usr/bin/env bash\ntouch "{started}"\nexec sleep 60\n'
    env = {
        **os.environ,
        'PATH': restricted_path(plugin_tmp_path / 'bin', extra={'iwe': stalled_iwe}),
    }
    before = snapshot(unrelated_repository)
    process = subprocess.Popen(
        [str(installed_iwe_bootstrap / SCRIPT)],
        cwd=unrelated_repository,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        start_new_session=True,
    )
    wait_for(started)
    os.killpg(process.pid, signal.SIGTERM)
    stdout, _ = process.communicate(timeout=30)

    assert process.returncode == -signal.SIGTERM
    assert stdout.splitlines()[-1] == 'RESULT=SIGNAL_TERM'
    after = snapshot(unrelated_repository)
    for path, state in before.items():
        if path != '':
            assert after[path][:2] == state[:2], path
    assert not (unrelated_repository / '.iwe').exists()
    assert not (unrelated_repository / 'docs').exists()

    completed = run_bootstrap(installed_iwe_bootstrap, cwd=unrelated_repository)

    assert outcome(completed) == (0, 'RESULT=SUCCESS'), completed.stderr
    assert output_values(completed, 'RECOVERED_TRANSACTION') == ['discarded']
    assert not (unrelated_repository / TRANSACTION).exists()
    assert run_iwe('schema', 'validate', cwd=unrelated_repository).returncode == 0


@requires_iwe
def test_interrupted_commit_is_completed_on_the_next_run(
    installed_iwe_bootstrap: Path, unrelated_repository: Path, plugin_tmp_path: Path
) -> None:
    real_mv = shutil.which('mv')
    # Interrupt the helper just before it moves the staged knowledge tree.
    interrupting_mv = (
        '#!/usr/bin/env bash\n'
        'for arg in "$@"; do\n'
        '  if [[ "$arg" == */docs/knowledge ]]; then kill -TERM "$PPID"; exit 1; fi\n'
        'done\n'
        f'exec "{real_mv}" "$@"\n'
    )
    env = {
        **os.environ,
        'PATH': restricted_path(plugin_tmp_path / 'bin', extra={'mv': interrupting_mv})
        + os.pathsep
        + str(Path(shutil.which('iwe')).parent),
    }

    interrupted = run_bootstrap(installed_iwe_bootstrap, cwd=unrelated_repository, env=env)

    assert interrupted.returncode == -signal.SIGTERM, interrupted.stderr
    assert interrupted.stdout.splitlines()[-1] == 'RESULT=SIGNAL_TERM'
    assert (unrelated_repository / TRANSACTION).is_dir()
    assert not (unrelated_repository / 'docs' / 'knowledge').exists()

    completed = run_bootstrap(installed_iwe_bootstrap, cwd=unrelated_repository)

    assert outcome(completed) == (0, 'RESULT=SUCCESS'), completed.stderr
    assert output_values(completed, 'RECOVERED_TRANSACTION') == ['completed']
    assert not (unrelated_repository / TRANSACTION).exists()
    assets = installed_iwe_bootstrap / ASSETS
    assert tree_files(unrelated_repository / '.iwe') == tree_files(assets / '.iwe')
    assert tree_files(unrelated_repository / 'docs') == tree_files(assets / 'docs')


@requires_iwe
def test_default_root_is_the_enclosing_repository(
    installed_iwe_bootstrap: Path, unrelated_repository: Path
) -> None:
    nested = unrelated_repository / 'src' / 'module'
    nested.mkdir(parents=True)

    completed = run_bootstrap(installed_iwe_bootstrap, cwd=nested)

    assert outcome(completed) == (0, 'RESULT=SUCCESS'), completed.stderr
    assert (unrelated_repository / '.iwe' / 'config.toml').is_file()
    assert not (nested / '.iwe').exists()


@requires_iwe
def test_explicit_root_targets_that_directory(
    installed_iwe_bootstrap: Path, unrelated_repository: Path, plugin_tmp_path: Path
) -> None:
    completed = run_bootstrap(
        installed_iwe_bootstrap, '--root', str(unrelated_repository), cwd=plugin_tmp_path
    )

    assert outcome(completed) == (0, 'RESULT=SUCCESS'), completed.stderr
    assert (unrelated_repository / 'docs' / 'knowledge' / 'AGENTS.md').is_file()


@pytest.mark.parametrize(
    'args',
    [
        pytest.param(('--root', 'missing-directory'), id='missing-root'),
        pytest.param(('--root',), id='root-without-value'),
        pytest.param(('--unknown',), id='unknown-option'),
    ],
)
def test_bad_usage_is_a_preflight_error(
    installed_iwe_bootstrap: Path, plugin_tmp_path: Path, args: tuple[str, ...]
) -> None:
    completed = run_bootstrap(installed_iwe_bootstrap, *args, cwd=plugin_tmp_path)

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')


def test_a_directory_outside_any_repository_needs_an_explicit_root(
    installed_iwe_bootstrap: Path, plugin_tmp_path: Path
) -> None:
    outside = plugin_tmp_path / 'not-a-repository'
    outside.mkdir()
    env = {**os.environ, 'GIT_CEILING_DIRECTORIES': str(plugin_tmp_path)}

    completed = run_bootstrap(installed_iwe_bootstrap, cwd=outside, env=env)

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert list(outside.iterdir()) == []


def test_help_documents_every_result(installed_iwe_bootstrap: Path, plugin_tmp_path: Path) -> None:
    completed = run_bootstrap(installed_iwe_bootstrap, '--help', cwd=plugin_tmp_path)

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    for name in (
        'SUCCESS',
        'MISSING_DEPENDENCY',
        'ALREADY_INITIALIZED',
        'RECONCILIATION_REQUIRED',
        'VALIDATION_FAILED',
        'PREFLIGHT_ERROR',
        'SCRIPT_FAILURE',
        'SIGNAL_TERM',
    ):
        assert name in completed.stdout, name
