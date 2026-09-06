#!/usr/bin/env python3

"""Behavior tests for digest masking in the iwe-map stale-map-docs script."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess

from test_stale_map_docs import (
    build_workspace,
    commit_file,
    git,
    run_script,
    stale_map_docs,
    verdict,
    write_map_doc,
)

PIN = 'a' * 64
BUMPED_PIN = 'b' * 64
MASK_REASON = 'Renovate automerges digest bumps.'


def compose_text(pin: str, image: str = 'example.invalid/app', extra: str = '') -> str:
    """Render a compose file pinning `image` by digest."""
    return f'services:\n  app:\n    image: {image}@sha256:{pin}\n{extra}'


def write_metadata(directory: Path, rules: dict) -> None:
    """Write an .agent.metadata.json declaring `rules` under iwe-map."""
    directory.mkdir(parents=True, exist_ok=True)
    (directory / '.agent.metadata.json').write_text(
        json.dumps({'iwe-map': {'digest_ignore': rules}}, indent=2)
    )


def digest_mask(pattern: str = '@sha256:[0-9a-f]{64}') -> list[dict]:
    """Return a single substitution rule masking a pinned digest."""
    return [{'pattern': pattern, 'replace': '@sha256:<PIN>', 'reason': MASK_REASON}]


def current_digest(repository: Path, *sources: str) -> str:
    """Compute the digest the script would record for `sources`, masks included."""
    previous = Path.cwd()
    os.chdir(repository)
    try:
        applied: list = []
        resolver = stale_map_docs.MetadataResolver()
        return stale_map_docs.fold_in_masks(
            stale_map_docs.source_digest_for_paths(list(sources), resolver, applied),
            applied,
        )
    finally:
        os.chdir(previous)


def pin_workspace(plugin_tmp_path: Path) -> tuple[Path, str]:
    """Build a repository whose map doc claims a masked, digest-pinned compose file."""
    repository = build_workspace(plugin_tmp_path)
    commit_file(repository, 'deploy/compose.yml', compose_text(PIN), 'add compose')
    write_metadata(repository / 'deploy', {'compose.yml': digest_mask()})
    git(repository, 'add', 'deploy/.agent.metadata.json')
    git(repository, 'commit', '-m', 'add masks')
    write_map_doc(repository, 'data/codebase/deploy', 'type: codebase\nsource: deploy\n')
    digest = current_digest(repository, 'deploy')
    write_map_doc(
        repository,
        'data/codebase/deploy',
        f"type: codebase\nsource: deploy\nsource_digest: '{digest}'\n",
    )
    return repository, digest


def test_a_masked_pin_bump_leaves_the_doc_fresh(plugin_root: Path, plugin_tmp_path: Path) -> None:
    """Changing only a masked pinned value does not mark the doc stale."""
    # Arrange
    repository, _ = pin_workspace(plugin_tmp_path)

    # Act
    commit_file(repository, 'deploy/compose.yml', compose_text(BUMPED_PIN), 'bump pin')
    completed = run_script(plugin_root, repository)

    # Assert
    assert verdict(completed) == (0, 'RESULT=SUCCESS')
    assert 'FRESH data/codebase/deploy' in completed.stdout.splitlines()


def test_an_unmasked_change_in_the_same_file_marks_the_doc_stale(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Masking one value leaves the rest of the same file under surveillance."""
    # Arrange
    repository, _ = pin_workspace(plugin_tmp_path)

    # Act
    commit_file(
        repository,
        'deploy/compose.yml',
        compose_text(BUMPED_PIN, extra='    restart: always\n'),
        'add a restart policy',
    )
    completed = run_script(plugin_root, repository)

    # Assert
    assert verdict(completed) == (3, 'RESULT=STALE_FOUND')
    assert 'STALE_COUNT=1' in completed.stdout.splitlines()


def test_structural_change_around_a_masked_value_is_still_staleness(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Substitution keeps structure tracked where deletion would not."""
    # Arrange
    changes = {
        'a second pinned service': compose_text(BUMPED_PIN)
        + f'  sidecar:\n    image: example.invalid/side@sha256:{PIN}\n',
        'a different image name': compose_text(BUMPED_PIN, image='example.invalid/other'),
        'the pin line deleted': 'services:\n  app:\n    image: example.invalid/app\n',
    }
    outcomes: dict[str, tuple[int, str]] = {}

    # Act
    for label, content in changes.items():
        case_path = plugin_tmp_path / label.replace(' ', '-')
        case_path.mkdir()
        repository, _ = pin_workspace(case_path)
        commit_file(repository, 'deploy/compose.yml', content, label)
        outcomes[label] = verdict(run_script(plugin_root, repository))

    # Assert
    assert outcomes == {label: (3, 'RESULT=STALE_FOUND') for label in changes}


def test_a_parent_rule_reaches_a_subdirectory_and_a_child_adds_to_it(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """Deeper metadata accumulates onto its ancestors' rules rather than replacing them."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    commit_file(
        repository,
        'stack/inner/compose.yml',
        compose_text(PIN) + '    build: 1001\n',
        'add nested compose',
    )
    write_metadata(repository / 'stack', {'**/*.yml': digest_mask()})
    write_metadata(
        repository / 'stack/inner',
        {'*.yml': [{'pattern': 'build: [0-9]+', 'replace': 'build: <N>', 'reason': 'ci'}]},
    )
    git(repository, 'add', '-A')
    git(repository, 'commit', '-m', 'add masks')
    write_map_doc(repository, 'data/codebase/stack', 'type: codebase\nsource: stack\n')
    digest = current_digest(repository, 'stack')
    write_map_doc(
        repository,
        'data/codebase/stack',
        f"type: codebase\nsource: stack\nsource_digest: '{digest}'\n",
    )

    # Act: the parent's rule and the child's rule each mask their own value
    commit_file(
        repository,
        'stack/inner/compose.yml',
        compose_text(BUMPED_PIN) + '    build: 2002\n',
        'bump both machine-managed values',
    )
    completed = run_script(plugin_root, repository)

    # Assert
    assert verdict(completed) == (0, 'RESULT=SUCCESS')
    assert 'FRESH data/codebase/stack' in completed.stdout.splitlines()


def test_globs_match_relative_to_the_declaring_directory(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """The same metadata file masks the same relative paths at any depth."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    rules = {'svc/*.yml': digest_mask()}
    for base in ('shallow', 'nested/deeper'):
        commit_file(repository, f'{base}/svc/compose.yml', compose_text(PIN), f'add {base}')
        write_metadata(repository / base, rules)
    git(repository, 'add', '-A')
    git(repository, 'commit', '-m', 'add masks at two depths')

    digests = {}
    for base in ('shallow', 'nested/deeper'):
        key = f'data/codebase/{base.replace("/", "-")}'
        write_map_doc(repository, key, f'type: codebase\nsource: {base}\n')
        digests[key] = current_digest(repository, base)
    for key, digest in digests.items():
        base = key.rsplit('/', 1)[1].replace('-', '/')
        write_map_doc(
            repository,
            key,
            f"type: codebase\nsource: {base}\nsource_digest: '{digest}'\n",
        )

    # Act
    for base in ('shallow', 'nested/deeper'):
        commit_file(repository, f'{base}/svc/compose.yml', compose_text(BUMPED_PIN), 'bump')
    completed = run_script(plugin_root, repository)

    # Assert
    assert verdict(completed) == (0, 'RESULT=SUCCESS')
    assert 'FRESH_COUNT=2' in completed.stdout.splitlines()


def test_absent_metadata_reproduces_the_unmasked_digest(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A repository declaring no masks behaves exactly as the unmasked script did."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    commit_file(repository, 'deploy/compose.yml', compose_text(PIN), 'add compose')
    write_map_doc(repository, 'data/codebase/deploy', 'type: codebase\nsource: deploy\n')
    digest = current_digest(repository, 'deploy')

    # Act: the digest of tracked content with no metadata anywhere
    listed = subprocess.run(
        ['git', 'ls-files', '-z', '--', 'deploy'],
        cwd=repository,
        check=True,
        capture_output=True,
    ).stdout
    unmasked = hashlib.sha256()
    for raw_path in sorted({path for path in listed.split(b'\0') if path}):
        content_hash = git(repository, 'hash-object', '--', raw_path.decode())
        unmasked.update(raw_path + b'\0' + content_hash.encode() + b'\0')

    # Assert
    assert digest == f'sha256:{unmasked.hexdigest()}'


def test_an_unparseable_metadata_file_breaks_only_its_own_subtree(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A metadata file that cannot be read reports BROKEN, leaving other docs alone."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    timer_digest = current_digest(repository, 'src/timer')
    commit_file(repository, 'deploy/compose.yml', compose_text(PIN), 'add compose')
    (repository / 'deploy' / '.agent.metadata.json').write_text('{ not json')
    write_map_doc(repository, 'data/codebase/deploy', 'type: codebase\nsource: deploy\n')
    write_map_doc(
        repository,
        'data/codebase/timer',
        f"type: codebase\nsource: src/timer\nsource_digest: '{timer_digest}'\n",
    )

    # Act
    completed = run_script(plugin_root, repository)

    # Assert
    lines = completed.stdout.splitlines()
    assert verdict(completed) == (5, 'RESULT=BROKEN_METADATA')
    assert 'BROKEN data/codebase/deploy deploy/.agent.metadata.json' in lines
    assert 'FRESH data/codebase/timer' in lines
    assert 'BROKEN_COUNT=1' in lines


def test_an_uncompilable_pattern_is_broken_metadata(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A rule whose regex cannot compile breaks its subtree rather than being skipped."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    commit_file(repository, 'deploy/compose.yml', compose_text(PIN), 'add compose')
    write_metadata(repository / 'deploy', {'*.yml': digest_mask(pattern='(unclosed')})
    write_map_doc(repository, 'data/codebase/deploy', 'type: codebase\nsource: deploy\n')

    # Act
    completed = run_script(plugin_root, repository)

    # Assert
    assert verdict(completed) == (5, 'RESULT=BROKEN_METADATA')
    assert 'BROKEN_COUNT=1' in completed.stdout.splitlines()


def test_an_invalid_replacement_template_is_broken_metadata(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A regex replacement error reports the metadata file that declared it."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    commit_file(repository, 'deploy/compose.yml', compose_text(PIN), 'add compose')
    rules = [{'pattern': 'sha256', 'replace': r'\d', 'reason': MASK_REASON}]
    write_metadata(repository / 'deploy', {'*.yml': rules})
    write_map_doc(
        repository,
        'data/codebase/deploy',
        "type: codebase\nsource: deploy\nsource_digest: 'sha256:recorded'\n",
    )

    # Act
    completed = run_script(plugin_root, repository)

    # Assert
    lines = completed.stdout.splitlines()
    assert verdict(completed) == (5, 'RESULT=BROKEN_METADATA')
    assert 'BROKEN data/codebase/deploy deploy/.agent.metadata.json' in lines


def test_a_masked_non_utf8_file_is_broken_metadata(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A masked file that cannot be decoded reports its mask's metadata file."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    binary = repository / 'deploy' / 'fixture.bin'
    binary.parent.mkdir(parents=True)
    binary.write_bytes(b'\xff\xfe')
    write_metadata(repository / 'deploy', {'*.bin': digest_mask(pattern='payload')})
    git(repository, 'add', 'deploy')
    git(repository, 'commit', '-m', 'add masked binary fixture')
    write_map_doc(
        repository,
        'data/codebase/deploy',
        "type: codebase\nsource: deploy\nsource_digest: 'sha256:recorded'\n",
    )

    # Act
    completed = run_script(plugin_root, repository)

    # Assert
    lines = completed.stdout.splitlines()
    assert verdict(completed) == (5, 'RESULT=BROKEN_METADATA')
    assert 'BROKEN data/codebase/deploy deploy/.agent.metadata.json' in lines


def test_editing_a_mask_invalidates_only_the_docs_it_reaches(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """A doc's digest folds in the masks that matched its own sources, and no others."""
    # Arrange
    repository = build_workspace(plugin_tmp_path)
    timer_digest = current_digest(repository, 'src/timer')
    commit_file(repository, 'deploy/compose.yml', compose_text(PIN), 'add compose')
    write_metadata(repository / 'deploy', {'*.yml': digest_mask()})
    git(repository, 'add', '-A')
    git(repository, 'commit', '-m', 'add masks')
    write_map_doc(repository, 'data/codebase/deploy', 'type: codebase\nsource: deploy\n')
    digest = current_digest(repository, 'deploy')
    write_map_doc(
        repository,
        'data/codebase/deploy',
        f"type: codebase\nsource: deploy\nsource_digest: '{digest}'\n",
    )
    write_map_doc(
        repository,
        'data/codebase/timer',
        f"type: codebase\nsource: src/timer\nsource_digest: '{timer_digest}'\n",
    )
    assert verdict(run_script(plugin_root, repository)) == (0, 'RESULT=SUCCESS')

    # Act: change the mask's replacement without touching any source file
    write_metadata(
        repository / 'deploy',
        {
            '*.yml': [
                {
                    'pattern': '@sha256:[0-9a-f]{64}',
                    'replace': '@sha256:<DIGEST>',
                    'reason': MASK_REASON,
                }
            ]
        },
    )
    git(repository, 'add', '-A')
    git(repository, 'commit', '-m', 'edit the mask')
    completed = run_script(plugin_root, repository)

    # Assert
    lines = completed.stdout.splitlines()
    assert verdict(completed) == (3, 'RESULT=STALE_FOUND')
    assert any(line.startswith('STALE data/codebase/deploy source_digest') for line in lines)
    assert 'FRESH data/codebase/timer' in lines


def test_explain_names_the_mask_its_source_and_its_reason(
    plugin_root: Path, plugin_tmp_path: Path
) -> None:
    """--explain makes a FRESH verdict reached through masking auditable."""
    # Arrange
    repository, _ = pin_workspace(plugin_tmp_path)

    # Act
    completed = run_script(plugin_root, repository, '--explain')

    # Assert
    lines = completed.stdout.splitlines()
    mask_lines = [line for line in lines if line.startswith('MASK ')]
    assert mask_lines == [
        'MASK data/codebase/deploy deploy/compose.yml deploy/.agent.metadata.json '
        f'@sha256:[0-9a-f]{{64}} {MASK_REASON}'
    ]
    assert lines[-1] == 'RESULT=SUCCESS'
