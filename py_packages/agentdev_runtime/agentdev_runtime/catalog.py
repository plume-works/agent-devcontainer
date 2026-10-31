"""
Register a catalog root with Claude Code, Codex, and OpenCode.

A root that ships no manifest for a client leaves that client's registration as it was. Spec:
catalog-lifecycle.
"""

from __future__ import annotations

import filecmp
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from agentdev_runtime import agent_state, settings as env

CLAUDE_MANIFEST = '.claude-plugin/marketplace.json'
CODEX_MANIFEST = '.agents/plugins/marketplace.json'
OPENCODE_BRIDGE = '.agents/plugins/agentdev/.opencode-plugin'
CLAUDE_SCOPES = ('user', 'project', 'local')
# The removal sweeps run blind, so "nothing to remove" is the expected failure.
CLAUDE_ABSENT = re.compile(r'not found|is installed in [a-z]+ scope')
CODEX_ABSENT = re.compile(r'not found|is not configured or installed')


class CatalogError(Exception):
    """A client refused the registration."""


def complete(root: Path) -> bool:
    """Return whether ``root`` ships all three clients' manifests, so it can replace the staged one."""
    return (
        (root / CLAUDE_MANIFEST).is_file()
        and (root / CODEX_MANIFEST).is_file()
        and (root / OPENCODE_BRIDGE).is_dir()
    )


def run(*argv: str) -> None:
    """Run a client command whose failure fails the registration."""
    result = subprocess.run(argv, check=False)
    if result.returncode != 0:
        raise CatalogError(f'{" ".join(argv)} exited {result.returncode}')


def output(*argv: str) -> str:
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        raise CatalogError(f'{" ".join(argv)} exited {result.returncode}')
    return result.stdout


def listing(*argv: str) -> object:
    """Return a client's JSON listing; one it cannot give lists nothing to clean up."""
    result = subprocess.run(argv, capture_output=True, text=True, check=False)
    try:
        return json.loads(result.stdout) if result.returncode == 0 else []
    except ValueError:
        return []


def try_remove(absent: re.Pattern[str], *argv: str) -> None:
    """Remove blind, reporting output only on success or an unexpected failure."""
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    text = result.stdout.rstrip('\n')
    if result.returncode == 0:
        if text:
            print(text)
    elif not absent.search(text):
        print(text or f'failed: {" ".join(argv)} (exit {result.returncode})', file=sys.stderr)


def read_manifest(path: Path) -> dict:
    manifest = json.loads(path.read_text())
    if not isinstance(manifest, dict) or not manifest.get('name'):
        raise CatalogError(f'{path} names no marketplace')
    return manifest


def claude(root: str, scope: str = 'local') -> None:
    """Register the root as a Claude marketplace and install every plugin it publishes."""
    manifest_path = Path(root) / CLAUDE_MANIFEST
    if not manifest_path.is_file():
        print(f'{root} declares no Claude marketplace; nothing to reinstall.')
        return
    manifest = read_manifest(manifest_path)
    name = manifest['name']
    plugins = [plugin['name'] for plugin in manifest.get('plugins') or []]
    stale = {
        entry['name']
        for entry in listing('claude', 'plugin', 'marketplace', 'list', '--json')
        if isinstance(entry, dict)
        and (entry.get('path') == root or entry.get('installLocation') == root)
    }
    # A declaration left in either the image's user scope or a checkout's local scope
    # shadows the other, so both removals sweep every scope.
    for registered in sorted({name, *stale}):
        for plugin in plugins:
            for uninstall_scope in CLAUDE_SCOPES:
                try_remove(
                    CLAUDE_ABSENT,
                    'claude',
                    'plugin',
                    'uninstall',
                    f'{plugin}@{registered}',
                    '--scope',
                    uninstall_scope,
                )
        try_remove(CLAUDE_ABSENT, 'claude', 'plugin', 'marketplace', 'remove', registered)
    run('claude', 'plugin', 'marketplace', 'add', root, '--scope', scope)
    for plugin in plugins:
        run('claude', 'plugin', 'install', f'{plugin}@{name}', '--scope', scope)


def codex_registered(
    settings: env.Settings, stale: list[str], name: str, plugin: str, plugin_root: Path
) -> bool:
    """Return whether this root's plugin is installed from an identical copy already."""
    if stale != [name]:
        return False
    try:
        version = json.loads((plugin_root / '.codex-plugin/plugin.json').read_text())['version']
    except (OSError, ValueError, KeyError, TypeError):
        return False
    try:
        installed = json.loads(output('codex', 'plugin', 'list', '--json')).get('installed', [])
    except (CatalogError, ValueError, AttributeError):
        return False
    if not any(
        entry.get('pluginId') == f'{plugin}@{name}'
        and entry.get('installed')
        and entry.get('enabled')
        and entry.get('version') == version
        for entry in installed
    ):
        return False
    cache = settings.path('CODEX_HOME') / 'plugins/cache' / name / plugin / str(version)
    return cache.is_dir() and identical_trees(plugin_root, cache)


def identical_trees(left: Path, right: Path) -> bool:
    comparison = filecmp.dircmp(left, right)
    if comparison.left_only or comparison.right_only or comparison.funny_files:
        return False
    _, mismatch, errors = filecmp.cmpfiles(left, right, comparison.common_files, shallow=False)
    if mismatch or errors:
        return False
    return all(identical_trees(left / sub, right / sub) for sub in comparison.common_dirs)


def codex(settings: env.Settings, root: str) -> None:
    """Register the root as a Codex marketplace, add its plugin, and install its agents."""
    manifest_path = Path(root) / CODEX_MANIFEST
    if not manifest_path.is_file():
        print(f'{root} declares no Codex marketplace; nothing to reinstall.')
        return
    manifest = read_manifest(manifest_path)
    name = manifest['name']
    # The Codex manifest publishes one plugin: self-improve ships no Codex manifest.
    plugin = manifest['plugins'][0]['name']
    listed = listing('codex', 'plugin', 'marketplace', 'list', '--json')
    stale = [
        entry['name']
        for entry in (listed.get('marketplaces', []) if isinstance(listed, dict) else [])
        if entry.get('root') == root
        or (entry.get('marketplaceSource') or {}).get('source') == root
    ]
    plugin_root = Path(f'{root}/{manifest["plugins"][0]["source"]["path"]}')
    # Leaving an identical registration keeps config.toml byte-identical.
    if codex_registered(settings, stale, name, plugin, plugin_root):
        print(f'{name} and {plugin} are already registered from {root}; leaving them.')
    else:
        for registered in sorted({name, *stale}):
            try_remove(CODEX_ABSENT, 'codex', 'plugin', 'remove', f'{plugin}@{registered}')
            try_remove(CODEX_ABSENT, 'codex', 'plugin', 'marketplace', 'remove', registered)
        run('codex', 'plugin', 'marketplace', 'add', root)
        run('codex', 'plugin', 'add', f'{plugin}@{name}')
    # Codex loads custom agents only from its own agents/ directory, never from a plugin.
    installer = plugin_root / 'bin/install-codex-agents.py'
    if installer.is_file():
        # -B keeps __pycache__ out of a read-only staged catalog.
        run('python3', '-B', str(installer))
    else:
        print(f'{root} predates Codex agent install; no agents to install.')


def opencode(settings: env.Settings, root: str) -> None:
    """Leave exactly one OpenCode bridge entry, pointing at this root."""
    bridge_dir = Path(f'{root}{"/" + OPENCODE_BRIDGE}')
    if not bridge_dir.is_dir():
        print(f'{root} ships no OpenCode bridge plugin; nothing to register.')
        return
    bridge = os.path.abspath(bridge_dir)
    config_dir = settings.path('OPENCODE_CONFIG_DIR')
    config = config_dir / 'opencode.json'
    config_dir.mkdir(parents=True, exist_ok=True)
    if not config.is_file() or config.stat().st_size == 0:
        config.write_text('{}\n')
    document = json.loads(config.read_text())
    suffix = '/' + OPENCODE_BRIDGE

    def spec(entry: object) -> str:
        # A plugin entry is a spec string or a [spec, options] pair.
        first = entry[0] if isinstance(entry, list) and entry else entry
        return first if isinstance(first, str) else json.dumps(first)

    document['plugin'] = [
        entry for entry in document.get('plugin') or [] if not spec(entry).endswith(suffix)
    ] + [bridge]
    descriptor, temp = tempfile.mkstemp(dir=config_dir, prefix='opencode.json.')
    with os.fdopen(descriptor, 'w') as handle:
        json.dump(document, handle, indent=2)
        handle.write('\n')
    os.replace(temp, config)
    print(f'Registered the OpenCode bridge {bridge} in {config}.')


def install(settings: env.Settings, root: str, claude_scope: str | None = None) -> None:
    codex(settings, root)
    claude(root, claude_scope or 'local')
    opencode(settings, root)


def main(argv: list[str]) -> int:
    """``catalog install <root> [--claude-scope user|local]`` and ``catalog complete <root>``."""
    usage = (
        'usage: agentdev-runtime catalog install <root> [--claude-scope user|local]'
        ' | complete <root>'
    )
    if len(argv) == 2 and argv[0] == 'complete':
        return 0 if complete(Path(argv[1])) else 1
    scope = None
    if len(argv) == 4 and argv[2] == '--claude-scope' and argv[3] in ('user', 'local'):
        scope = argv[3]
    elif len(argv) != 2:
        print(usage, file=sys.stderr)
        return 2
    if argv[0] != 'install':
        print(usage, file=sys.stderr)
        return 2
    settings = env.Settings()
    try:
        with agent_state.config_lock(settings):
            install(settings, argv[1], scope)
    except agent_state.StateError as error:
        print(f'agentdev-runtime catalog: {error}', file=sys.stderr)
        return error.status
    except CatalogError as error:
        print(f'agentdev-runtime catalog: {error}', file=sys.stderr)
        return 1
    return 0
