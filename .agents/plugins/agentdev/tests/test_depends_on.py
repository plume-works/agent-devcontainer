#!/usr/bin/env python3

"""Tests for the dependency-record helpers in bin/depends_on.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from git_fixtures import git
import pytest


@pytest.fixture
def depends_on(plugin_root: Path) -> ModuleType:
    """Load the module from the plugin root under test."""
    spec = importlib.util.spec_from_file_location('depends_on', plugin_root / 'bin/depends_on.py')
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def numbers(module: ModuleType, body: str) -> list[int]:
    """Return the entry numbers the module reads from `body`."""
    return [entry.number for entry in module.entries(body)]


def test_body_without_a_section_has_no_entries(depends_on: ModuleType) -> None:
    body = '## Summary\n\nDepends on nothing.\n- #12\n'
    assert depends_on.find_section(body) is None
    assert numbers(depends_on, body) == []
    with pytest.raises(depends_on.DependsOnError):
        depends_on.record_merge(body, 12, 'a' * 8, 'b' * 8)


def test_one_entry_is_replaced_by_its_record(depends_on: ModuleType) -> None:
    body = '## Summary\n\nText.\n\n## Depends on\n\n- #591\n'
    edited = depends_on.record_merge(body, 591, 'd66fdf4d', '7a8c22c2')
    assert edited == (
        '## Summary\n\nText.\n\n## Depends on\n\n'
        '- #591 — merged as d66fdf4d (head 7a8c22c2), reconnected\n'
    )


def test_several_entries_keep_their_order_and_only_one_changes(
    depends_on: ModuleType,
) -> None:
    body = '## Depends on\r\n\r\n- #3\r\n- #5\r\n- #8\r\n'
    assert numbers(depends_on, body) == [3, 5, 8]
    edited = depends_on.record_merge(body, 5, '1234567a', '89abcdef')
    assert edited == (
        '## Depends on\r\n\r\n- #3\r\n'
        '- #5 — merged as 1234567a (head 89abcdef), reconnected\r\n- #8\r\n'
    )


def test_an_entry_already_carrying_a_record_is_read(depends_on: ModuleType) -> None:
    body = '## Depends on\n\n- #591 — merged as d66fdf4d (head 7a8c22c2), reconnected\n- #600\n'
    first, second = depends_on.entries(body)
    assert (first.number, first.merge, first.head) == (591, 'd66fdf4d', '7a8c22c2')
    assert (second.number, second.merge, second.head) == (600, None, None)
    assert depends_on.record_merge(body, 591, 'd66fdf4d', '7a8c22c2') == body


def test_the_section_ends_at_the_next_heading(depends_on: ModuleType) -> None:
    body = '## Depends on\n\n- #3\n\n## Testing\n\n- #4\n- not an entry\n'
    section = depends_on.find_section(body)
    assert section is not None
    assert numbers(depends_on, body) == [3]
    assert section.invalid == ()
    edited = depends_on.record_merge(body, 3, 'aaaaaaaa', 'bbbbbbbb')
    assert edited.endswith('## Testing\n\n- #4\n- not an entry\n')


def test_a_list_item_that_is_not_an_entry_is_invalid(depends_on: ModuleType) -> None:
    section = depends_on.find_section('## Depends on\n\n- #3\n- PR 4\n')
    assert section is not None
    assert section.invalid == (3,)


def test_a_heading_inside_a_code_fence_is_not_the_section(depends_on: ModuleType) -> None:
    body = '```markdown\n## Depends on\n\n- #1\n```\n\n## Depends on\n\n- #2\n'
    assert numbers(depends_on, body) == [2]


def test_trailers_on_two_commits_are_read_oldest_first(
    depends_on: ModuleType, plugin_tmp_path: Path
) -> None:
    repository = plugin_tmp_path / 'repository'
    repository.mkdir()
    git(repository, 'init', '--quiet', '--initial-branch=main')
    git(repository, 'commit', '--allow-empty', '-m', 'base')
    git(repository, 'commit', '--allow-empty', '-m', 'Depend on 12\n\nDepends-on: #12')
    git(repository, 'commit', '--allow-empty', '-m', 'Work\n\nNo trailer here.')
    git(repository, 'commit', '--allow-empty', '-m', 'Depend on 7\n\nDepends-on: #7')
    assert depends_on.read_trailers('HEAD', cwd=repository) == [12, 7]
    assert depends_on.read_trailers('HEAD', 'HEAD~2', cwd=repository) == [7]
