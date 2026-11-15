"""A new Claude registration of a catalog root replaces each earlier one."""

from collections.abc import Callable
import json
import os
from pathlib import Path

from agentdev_runtime import catalog
import pytest

PLUGINS = ('agentdev', 'extra')


def write_root(root: Path) -> str:
    manifest = root / catalog.CLAUDE_MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.write_text(
        json.dumps({'name': 'shared', 'plugins': [{'name': name} for name in PLUGINS]})
    )
    return str(root)


def registered(*entries: dict[str, str]) -> None:
    Path(os.environ['CLAUDE_STUB_MARKETPLACES']).write_text(json.dumps(list(entries)))


def calls(log: Path) -> list[list[str]]:
    return [json.loads(line)['argv'] for line in log.read_text().splitlines()]


def sweep(marketplace: str) -> list[list[str]]:
    """Return the removals of one marketplace: each plugin in every scope, then the source."""
    return [
        ['plugin', 'uninstall', f'{plugin}@{marketplace}', '--scope', scope]
        for plugin in PLUGINS
        for scope in catalog.CLAUDE_SCOPES
    ] + [['plugin', 'marketplace', 'remove', marketplace]]


def test_a_marketplace_from_the_same_root_is_swept_before_the_new_one_is_added(
    tmp_path: Path,
    claude_stub: Path,
    make_repository: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(make_repository(tmp_path / 'repo', with_catalog=False))
    root = write_root(tmp_path / 'catalog')
    registered(
        {'name': 'renamed', 'path': root},
        {'name': 'installed', 'installLocation': root},
        {'name': 'unrelated', 'path': str(tmp_path / 'elsewhere')},
    )

    catalog.claude(root)

    assert calls(claude_stub) == [
        ['plugin', 'marketplace', 'list', '--json'],
        *sweep('installed'),
        *sweep('renamed'),
        *sweep('shared'),
        ['plugin', 'marketplace', 'add', root, '--scope', 'local'],
        *[['plugin', 'install', f'{plugin}@shared', '--scope', 'local'] for plugin in PLUGINS],
    ]


def test_a_removal_that_finds_nothing_does_not_stop_the_registration(
    tmp_path: Path, claude_stub: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = write_root(tmp_path / 'catalog')
    monkeypatch.setenv('CLAUDE_STUB_FAIL', 'uninstall')

    catalog.claude(root, 'user')

    assert calls(claude_stub)[-3:] == [
        ['plugin', 'marketplace', 'add', root, '--scope', 'user'],
        *[['plugin', 'install', f'{plugin}@shared', '--scope', 'user'] for plugin in PLUGINS],
    ]


def test_a_failed_add_fails_the_registration(
    tmp_path: Path,
    claude_stub: Path,
    make_repository: Callable[..., Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(make_repository(tmp_path / 'repo', with_catalog=False))
    root = write_root(tmp_path / 'catalog')
    monkeypatch.setenv('CLAUDE_STUB_FAIL', 'marketplace add')

    with pytest.raises(catalog.CatalogError, match='marketplace add'):
        catalog.claude(root)
