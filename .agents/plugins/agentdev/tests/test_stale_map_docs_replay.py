#!/usr/bin/env python3

"""Behavior tests for the --replay mode of the iwe-map stale-map-docs script."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest
from test_stale_map_docs import (
    build_workspace,
    GIT_IDENTITY,
    run_script,
    verdict,
    write_map_doc,
)
from test_stale_map_docs_masks import (
    BUMPED_PIN,
    compose_text,
    current_digest,
    digest_mask,
    PIN,
    write_metadata,
)

# Fixture commits are dated after build_workspace's own, so history stays in date order.
ADDED_AT = '2090-01-01T00:00:00Z'
VERIFIED_AT = '2090-02-01T00:00:00Z'
BUMPED_AT = '2090-03-01T00:00:00Z'
COMPOSE = 'deploy/compose.yml'
NOTES = 'deploy/notes.txt'
KEY = 'data/codebase/deploy'


def commit_dated(repository: Path, files: dict[str, str], date: str) -> str:
    """Write and commit `files` with author and committer dated `date`; return the SHA."""
    for relative, content in files.items():
        target = repository / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)
    environment = {**os.environ, 'GIT_AUTHOR_DATE': date, 'GIT_COMMITTER_DATE': date}
    for arguments in (['add', *files], ['commit', '-m', f'change at {date}']):
        subprocess.run(
            ['git', *GIT_IDENTITY, *arguments],
            cwd=repository,
            check=True,
            capture_output=True,
            env=environment,
        )
    return subprocess.run(
        ['git', 'rev-parse', 'HEAD'], cwd=repository, check=True, capture_output=True, text=True
    ).stdout.strip()


def write_deploy_doc(repository: Path, digest: str, verified: bool = True) -> None:
    """Map `deploy` at `digest`, verified at VERIFIED_AT unless `verified` is False."""
    stamp = f'verified:\n  by: human:fixture\n  at: {VERIFIED_AT}\n' if verified else ''
    write_map_doc(
        repository,
        KEY,
        f"type: codebase\nsource: deploy\nsource_digest: '{digest}'\n{stamp}",
    )


def bumped_workspace(plugin_tmp_path: Path, extra: str = '') -> tuple[Path, str]:
    """Map a pinned compose file, then bump its pin; return the repository and bump SHA."""
    repository = build_workspace(plugin_tmp_path)
    commit_dated(repository, {COMPOSE: compose_text(PIN), NOTES: 'notes\n'}, ADDED_AT)
    write_deploy_doc(repository, current_digest(repository, 'deploy'))
    bump = commit_dated(repository, {COMPOSE: compose_text(BUMPED_PIN, extra=extra)}, BUMPED_AT)
    return repository, bump


def test_a_doc_stale_only_from_a_pin_bump_is_restamped(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A new rule covering the bump makes the doc RESTAMP with the digest a plain run records."""
    # Arrange
    repository, bump = bumped_workspace(plugin_tmp_path)
    write_metadata(repository / 'deploy', {'compose.yml': digest_mask()})

    # Act
    completed = run_script(plugin_root, repository, '--replay')

    # Assert
    lines = completed.stdout.splitlines()
    restamped = current_digest(repository, 'deploy')
    assert verdict(completed) == (0, 'RESULT=SUCCESS')
    assert f'ABSORBED {bump} {COMPOSE}' in lines
    assert f'RESTAMP {KEY} {restamped}' in lines
    write_deploy_doc(repository, restamped)
    assert f'FRESH {KEY}' in run_script(plugin_root, repository).stdout.splitlines()


def test_a_fresh_doc_the_new_rule_reaches_is_restamped(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A doc fresh under HEAD's metadata is RESTAMP even without a verified date."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    commit_dated(repository, {COMPOSE: compose_text(PIN)}, ADDED_AT)
    write_deploy_doc(repository, current_digest(repository, 'deploy'), verified=False)
    write_metadata(repository / 'deploy', {'compose.yml': digest_mask()})

    # Act
    completed = run_script(plugin_root, repository, '--replay')

    # Assert
    assert verdict(completed) == (0, 'RESULT=SUCCESS')
    assert f'RESTAMP {KEY} {current_digest(repository, "deploy")}' in completed.stdout.splitlines()


def test_a_change_outside_the_rule_is_moved_and_refreshed(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A bump that also edits described content stays MOVED, so the doc is REFRESH."""
    # Arrange
    repository, bump = bumped_workspace(plugin_tmp_path, extra='    restart: always\n')
    write_metadata(repository / 'deploy', {'compose.yml': digest_mask()})

    # Act
    completed = run_script(plugin_root, repository, '--replay')

    # Assert
    lines = completed.stdout.splitlines()
    assert verdict(completed) == (0, 'RESULT=SUCCESS')
    assert f'MOVED {bump} {COMPOSE}' in lines
    assert f'REFRESH {KEY}' in lines
    assert 'RESTAMP_COUNT=0' in lines


def test_an_uncommitted_unmasked_edit_forces_a_refresh(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """An absorbed history does not cover a working-tree edit the masks do not hide."""
    # Arrange
    repository, _ = bumped_workspace(plugin_tmp_path)
    write_metadata(repository / 'deploy', {'compose.yml': digest_mask()})
    (repository / NOTES).write_text('notes, edited\n')

    # Act
    completed = run_script(plugin_root, repository, '--replay')

    # Assert
    assert verdict(completed) == (0, 'RESULT=SUCCESS')
    assert f'REFRESH {KEY}' in completed.stdout.splitlines()


def test_an_uncommitted_masked_edit_is_reported_as_absorbed(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Working-tree evidence names an edit that contributes to a RESTAMP verdict."""
    repository, _ = bumped_workspace(plugin_tmp_path)
    write_metadata(repository / 'deploy', {'compose.yml': digest_mask()})
    (repository / COMPOSE).write_text(compose_text('c' * 64))

    completed = run_script(plugin_root, repository, '--replay')

    lines = completed.stdout.splitlines()
    assert f'ABSORBED WORKTREE {COMPOSE}' in lines
    assert (
        f'HIDDEN deploy/.agent.metadata.json @sha256:[0-9a-f]{{64}} "@sha256:{"c" * 64}"' in lines
    )


def test_hidden_lists_each_distinct_value_once(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """The pin seen in two revisions is one HIDDEN line, beside the bumped pin's."""
    # Arrange
    repository, _ = bumped_workspace(plugin_tmp_path)
    write_metadata(repository / 'deploy', {'compose.yml': digest_mask()})

    # Act
    completed = run_script(plugin_root, repository, '--replay')

    # Assert
    hidden = [line for line in completed.stdout.splitlines() if line.startswith('HIDDEN ')]
    prefix = 'HIDDEN deploy/.agent.metadata.json @sha256:[0-9a-f]{64}'
    assert hidden == [f'{prefix} "@sha256:{PIN}"', f'{prefix} "@sha256:{BUMPED_PIN}"']


def test_hidden_includes_current_values_from_unchanged_masked_files(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """HIDDEN inventories every current masked file, not only changed evidence."""
    repository, _ = bumped_workspace(plugin_tmp_path)
    unchanged = 'deploy/unchanged.yml'
    commit_dated(repository, {unchanged: compose_text('d' * 64)}, ADDED_AT)
    write_metadata(repository / 'deploy', {'*.yml': digest_mask()})

    completed = run_script(plugin_root, repository, '--replay')

    assert (
        f'HIDDEN deploy/.agent.metadata.json @sha256:[0-9a-f]{{64}} "@sha256:{"d" * 64}"'
        in completed.stdout.splitlines()
    )


def test_replay_handles_non_ascii_and_quoted_masked_filenames(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Changed paths and ls-files are parsed without Git's display quoting."""
    repository = build_workspace(plugin_tmp_path)
    unusual = 'deploy/café "pin".yml'
    commit_dated(repository, {unusual: compose_text(PIN)}, ADDED_AT)
    write_deploy_doc(repository, current_digest(repository, 'deploy'))
    bump = commit_dated(repository, {unusual: compose_text(BUMPED_PIN)}, BUMPED_AT)
    write_metadata(repository / 'deploy', {'*.yml': digest_mask()})

    completed = run_script(plugin_root, repository, '--replay')

    lines = completed.stdout.splitlines()
    assert verdict(completed) == (0, 'RESULT=SUCCESS')
    assert f'ABSORBED {bump} {unusual}' in lines
    assert any(line.startswith(f'RESTAMP {KEY} ') for line in lines)


def test_since_without_replay_is_a_preflight_error(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """--since only bounds a replay, so on its own it is a usage error."""
    # Arrange
    repository, _ = bumped_workspace(plugin_tmp_path)

    # Act
    completed = run_script(plugin_root, repository, '--since', '2090-01-01')

    # Assert
    assert verdict(completed) == (2, 'RESULT=PREFLIGHT_ERROR')


def test_replay_uses_the_digest_commit_ancestry_even_when_since_is_later(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Commit ancestry, not timestamps or --since, bounds evidence used for a verdict."""
    repository = build_workspace(plugin_tmp_path)
    commit_dated(repository, {COMPOSE: compose_text(PIN)}, ADDED_AT)
    write_deploy_doc(repository, current_digest(repository, 'deploy'))
    doc_path = repository / 'docs' / 'knowledge' / f'{KEY}.md'
    commit_dated(
        repository, {str(doc_path.relative_to(repository)): doc_path.read_text()}, VERIFIED_AT
    )
    bump = commit_dated(repository, {COMPOSE: compose_text(BUMPED_PIN)}, ADDED_AT)
    write_metadata(repository / 'deploy', {'compose.yml': digest_mask()})

    completed = run_script(plugin_root, repository, '--replay', '--since', '2090-04-01')

    lines = completed.stdout.splitlines()
    assert f'ABSORBED {bump} {COMPOSE}' in lines
    assert any(line.startswith(f'RESTAMP {KEY} ') for line in lines)


def test_a_recorded_digest_mismatch_at_its_starting_commit_forces_refresh(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Replay cannot restamp when the recorded digest was never valid for its source."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    commit_dated(repository, {COMPOSE: compose_text(PIN)}, ADDED_AT)
    write_deploy_doc(repository, 'sha256:not-the-source-digest')
    doc_path = repository / 'docs' / 'knowledge' / f'{KEY}.md'
    commit_dated(
        repository, {str(doc_path.relative_to(repository)): doc_path.read_text()}, VERIFIED_AT
    )
    commit_dated(repository, {COMPOSE: compose_text(BUMPED_PIN)}, BUMPED_AT)
    write_metadata(repository / 'deploy', {'compose.yml': digest_mask()})

    # Act
    completed = run_script(plugin_root, repository, '--replay')

    # Assert
    lines = completed.stdout.splitlines()
    assert verdict(completed) == (0, 'RESULT=SUCCESS')
    assert f'REFRESH {KEY}' in lines
    assert 'RESTAMP_COUNT=0' in lines


def test_a_crlf_masked_file_validates_its_recorded_digest_at_the_starting_commit(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Committed CRLF content digests as the working tree does, so a new mask can RESTAMP."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    metadata = repository / 'deploy' / '.agent.metadata.json'
    write_metadata(repository / 'deploy', {'compose.yml': digest_mask()})
    crlf_compose = compose_text(PIN).replace('\n', '\r\n')
    commit_dated(
        repository,
        {COMPOSE: crlf_compose, 'deploy/.agent.metadata.json': metadata.read_text()},
        ADDED_AT,
    )
    write_deploy_doc(repository, current_digest(repository, 'deploy'))
    doc_path = repository / 'docs' / 'knowledge' / f'{KEY}.md'
    commit_dated(
        repository, {str(doc_path.relative_to(repository)): doc_path.read_text()}, VERIFIED_AT
    )
    commit_dated(repository, {COMPOSE: compose_text(BUMPED_PIN).replace('\n', '\r\n')}, BUMPED_AT)
    image_mask = digest_mask('example[.]invalid/app')[0] | {'replace': '<IMAGE>'}
    write_metadata(repository / 'deploy', {'compose.yml': [*digest_mask(), image_mask]})

    # Act
    completed = run_script(plugin_root, repository, '--replay')

    # Assert
    lines = completed.stdout.splitlines()
    assert verdict(completed) == (0, 'RESULT=SUCCESS')
    assert f'RESTAMP {KEY} {current_digest(repository, "deploy")}' in lines


def test_malformed_working_tree_metadata_is_broken(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A replay never proves anything with a rule file it cannot read."""
    # Arrange
    repository, _ = bumped_workspace(plugin_tmp_path)
    (repository / 'deploy' / '.agent.metadata.json').write_text('{ not json')

    # Act
    completed = run_script(plugin_root, repository, '--replay')

    # Assert
    assert verdict(completed) == (5, 'RESULT=BROKEN_METADATA')
    assert f'BROKEN {KEY} deploy/.agent.metadata.json' in completed.stdout.splitlines()


def test_broken_metadata_during_replay_evidence_names_the_doc(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Evidence decoding errors are classified instead of escaping replay."""
    repository = build_workspace(plugin_tmp_path)
    target = repository / COMPOSE
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'\xff')
    environment = {**os.environ, 'GIT_AUTHOR_DATE': ADDED_AT, 'GIT_COMMITTER_DATE': ADDED_AT}
    subprocess.run(
        ['git', *GIT_IDENTITY, 'add', COMPOSE],
        cwd=repository,
        check=True,
        capture_output=True,
        env=environment,
    )
    subprocess.run(
        ['git', *GIT_IDENTITY, 'commit', '-m', 'binary source'],
        cwd=repository,
        check=True,
        capture_output=True,
        env=environment,
    )
    commit_dated(repository, {COMPOSE: compose_text(PIN)}, BUMPED_AT)
    write_deploy_doc(repository, current_digest(repository, 'deploy'))
    write_metadata(repository / 'deploy', {'compose.yml': digest_mask()})

    completed = run_script(plugin_root, repository, '--replay')

    assert verdict(completed) == (5, 'RESULT=BROKEN_METADATA')
    assert f'BROKEN {KEY} deploy/.agent.metadata.json' in completed.stdout.splitlines()


def test_malformed_metadata_is_broken_when_missing_digest_would_refresh(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Metadata validation precedes an early REFRESH verdict."""
    repository, _ = bumped_workspace(plugin_tmp_path)
    write_deploy_doc(repository, '', verified=False)
    (repository / 'deploy' / '.agent.metadata.json').write_text('{ not json')

    completed = run_script(plugin_root, repository, '--replay')

    assert verdict(completed) == (5, 'RESULT=BROKEN_METADATA')
    assert f'BROKEN {KEY} deploy/.agent.metadata.json' in completed.stdout.splitlines()


@pytest.mark.parametrize('otherwise', ['restamp', 'refresh', 'fresh'])
def test_malformed_committed_metadata_is_broken(
    plugin_root: Path, plugin_tmp_path: Path, otherwise: str
) -> None:
    """Repaired working-tree metadata cannot hide a broken committed designation."""
    extra = '    restart: always\n' if otherwise == 'refresh' else ''
    repository, _ = bumped_workspace(plugin_tmp_path, extra=extra)
    commit_dated(repository, {'deploy/.agent.metadata.json': '{ not json'}, BUMPED_AT)
    write_metadata(repository / 'deploy', {'compose.yml': digest_mask()})
    if otherwise == 'fresh':
        write_deploy_doc(repository, current_digest(repository, 'deploy'))

    completed = run_script(plugin_root, repository, '--replay')

    lines = completed.stdout.splitlines()
    assert verdict(completed) == (5, 'RESULT=BROKEN_METADATA')
    assert f'BROKEN {KEY} deploy/.agent.metadata.json' in lines
    assert 'BROKEN_COUNT=1' in lines
    assert 'RESTAMP_COUNT=0' in lines
    assert 'REFRESH_COUNT=0' in lines
