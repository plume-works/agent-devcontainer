#!/usr/bin/env python3

"""Behavior tests for the iwe-map stale-map-docs script."""

from __future__ import annotations

from pathlib import Path
import subprocess

SCRIPT_PATH = 'skills/iwe-map/scripts/stale-map-docs.sh'
LIBRARY = 'docs/knowledge'
GIT_IDENTITY = ['-c', 'user.name=Fixture Author', '-c', 'user.email=fixture@example.invalid']


def git(repository: Path, *arguments: str) -> str:
    """Run git in `repository` with a fixture identity and return stdout."""
    completed = subprocess.run(
        ['git', *GIT_IDENTITY, *arguments],
        cwd=repository,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def commit_file(repository: Path, relative: str, content: str, message: str) -> str:
    """Write `relative`, commit it, and return the new HEAD SHA."""
    target = repository / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content)
    git(repository, 'add', relative)
    git(repository, 'commit', '-m', message)
    return git(repository, 'rev-parse', 'HEAD')


def build_workspace(path: Path) -> Path:
    """Create a repository with an IWE config whose library is a subdirectory."""
    repository = path / 'repo'
    repository.mkdir()
    git(repository, 'init', '--initial-branch=main')
    (repository / '.iwe').mkdir()
    (repository / '.iwe' / 'config.toml').write_text(
        'version = 3\n\n[library]\npath = "docs/knowledge"\n'
    )
    commit_file(repository, 'src/timer/engine.txt', 'tick\n', 'add timer')
    commit_file(repository, 'src/store/log.txt', 'append\n', 'add store')
    return repository


def write_map_doc(repository: Path, key: str, frontmatter: str) -> None:
    """Write a map doc at `key` under the library without committing it."""
    target = repository / LIBRARY / f'{key}.md'
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(f'---\n{frontmatter}---\n\n# {key}\n')


def run_script(
    plugin_root: Path, repository: Path, *arguments: str
) -> subprocess.CompletedProcess[str]:
    """Run the staleness script from inside `repository`."""
    return subprocess.run(
        [str(plugin_root / SCRIPT_PATH), *arguments],
        cwd=repository,
        check=False,
        capture_output=True,
        text=True,
    )


def verdict(completed: subprocess.CompletedProcess[str]) -> tuple[int, str]:
    """Pair the exit code with the final RESULT line."""
    return completed.returncode, completed.stdout.splitlines()[-1]


def test_every_doc_fresh_reports_success(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """Docs whose sources have no commits after their pin are fresh."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    head = git(repository, 'rev-parse', 'HEAD')
    write_map_doc(
        repository,
        'data/codebase/timer',
        f"type: codebase\nsource: src/timer\ncommit: '{head}'\n",
    )

    # Act
    completed = run_script(plugin_root, repository)

    # Assert
    lines = completed.stdout.splitlines()
    assert verdict(completed) == (0, 'RESULT=SUCCESS')
    assert 'MAP_DIR=docs/knowledge/data/codebase' in lines
    assert 'FRESH data/codebase/timer' in lines
    assert 'DOC_COUNT=1' in lines


def test_commit_touching_a_source_marks_the_doc_stale(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A commit under any listed source path after the pin makes the doc stale."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    pinned = git(repository, 'rev-parse', 'HEAD')
    write_map_doc(
        repository,
        'data/codebase/timer',
        f'type: codebase\nsource:\n- src/timer\n- src/store\ncommit: "{pinned}"\n',
    )
    write_map_doc(
        repository,
        'data/codebase/store/log',
        f"type: codebase\nsource: [src/store/log.txt]\ncommit: '{pinned}'\n",
    )
    commit_file(repository, 'src/timer/engine.txt', 'tick tock\n', 'change timer')

    # Act
    completed = run_script(plugin_root, repository)

    # Assert
    lines = completed.stdout.splitlines()
    assert verdict(completed) == (3, 'RESULT=STALE_FOUND')
    assert f'STALE data/codebase/timer {pinned} 1' in lines
    assert 'FRESH data/codebase/store/log' in lines
    assert 'STALE_COUNT=1' in lines


def test_missing_source_reports_gone(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A source path absent from the checkout is reported as GONE, not as stale."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    head = git(repository, 'rev-parse', 'HEAD')
    write_map_doc(
        repository,
        'data/codebase/legacy',
        f"type: codebase\nsource: src/legacy\ncommit: '{head}'\n",
    )

    # Act
    completed = run_script(plugin_root, repository)

    # Assert
    lines = completed.stdout.splitlines()
    assert verdict(completed) == (3, 'RESULT=STALE_FOUND')
    assert 'GONE data/codebase/legacy src/legacy' in lines
    assert 'GONE_COUNT=1' in lines


def test_unknown_commit_and_past_stale_after_are_flagged(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """An unresolvable pin and an elapsed stale_after both need a refresh."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    head = git(repository, 'rev-parse', 'HEAD')
    write_map_doc(
        repository,
        'data/codebase/timer',
        "type: codebase\nsource: src/timer\ncommit: 'deadbeefcafe'\n",
    )
    write_map_doc(
        repository,
        'data/codebase/store',
        f"type: codebase\nsource: src/store\ncommit: '{head}'\nstale_after: 2000-01-01\n",
    )

    # Act
    completed = run_script(plugin_root, repository)

    # Assert
    lines = completed.stdout.splitlines()
    assert verdict(completed) == (3, 'RESULT=STALE_FOUND')
    assert 'UNKNOWN_COMMIT data/codebase/timer deadbeefcafe' in lines
    assert 'EXPIRED data/codebase/store 2000-01-01' in lines
    assert 'EXPIRED_COUNT=1' in lines


def test_empty_lane_reports_no_map_docs(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A workspace without map docs reports the empty lane rather than success."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)

    # Act
    completed = run_script(plugin_root, repository)

    # Assert
    assert verdict(completed) == (4, 'RESULT=NO_MAP_DOCS')
    assert 'DOC_COUNT=0' in completed.stdout.splitlines()


def test_missing_iwe_config_is_a_preflight_error(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """A repository that is not an IWE workspace stops before scanning."""
    # Arrange
    repository = plugin_tmp_path / 'bare'
    repository.mkdir()
    git(repository, 'init', '--initial-branch=main')

    # Act
    completed = run_script(plugin_root, repository)

    # Assert
    assert verdict(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert 'config.toml' in completed.stderr


def test_help_is_a_success(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """--help prints the contract on stdout and exits SUCCESS."""
    # Act
    completed = run_script(plugin_root, plugin_tmp_path, '--help')

    # Assert
    assert verdict(completed) == (0, 'RESULT=SUCCESS')
    assert 'STALE_FOUND' in completed.stdout
