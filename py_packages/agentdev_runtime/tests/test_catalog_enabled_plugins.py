"""The project's enabled plugins from other marketplaces are installed at user scope."""

import json
from pathlib import Path

from agentdev_runtime import catalog
import pytest


def write_project(root: Path, enabled: dict[str, object]) -> str:
    settings = root / '.claude' / 'settings.json'
    settings.parent.mkdir(parents=True)
    settings.write_text(json.dumps({'enabledPlugins': enabled}))
    manifest = root / catalog.CLAUDE_MANIFEST
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps({'name': 'shared', 'plugins': [{'name': 'agentdev'}]}))
    return str(root)


def calls(log: Path) -> list[list[str]]:
    return [json.loads(line)['argv'] for line in log.read_text().splitlines()]


def test_each_enabled_plugin_from_another_marketplace_is_installed(
    claude_stub: Path, tmp_path: Path
) -> None:
    root = write_project(
        tmp_path / 'project',
        {
            'context7@official': True,
            'disabled@official': False,
            'agentdev@shared': True,
            'superpowers@official': True,
        },
    )

    catalog.install_enabled(root)

    assert calls(claude_stub) == [
        ['plugin', 'install', 'context7@official', '--scope', 'user'],
        ['plugin', 'install', 'superpowers@official', '--scope', 'user'],
    ]


def test_a_failed_install_warns_and_the_rest_still_install(
    claude_stub: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = write_project(tmp_path / 'project', {'first@official': True, 'second@official': True})
    monkeypatch.setenv('CLAUDE_STUB_FAIL', 'first@official')

    catalog.install_enabled(root)

    assert calls(claude_stub)[-1] == ['plugin', 'install', 'second@official', '--scope', 'user']
    assert 'first@official' in capsys.readouterr().err


def test_a_project_without_settings_installs_nothing(claude_stub: Path, tmp_path: Path) -> None:
    (tmp_path / 'project').mkdir()

    catalog.install_enabled(str(tmp_path / 'project'))

    assert calls(claude_stub) == []
