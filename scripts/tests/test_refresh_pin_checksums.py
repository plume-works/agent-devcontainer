"""Tests for scripts/refresh-pin-checksums.py against locally served release assets."""

from __future__ import annotations

from collections.abc import Iterator
import hashlib
import http.server
import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys
import threading
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / 'scripts/refresh-pin-checksums.py'


def _load_script():
    """Load the hyphen-named script as a module."""
    spec = importlib.util.spec_from_file_location('refresh_pin_checksums', SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


refresh = _load_script()
PINS = 'docker/devcontainer/pinned-tools.yml'


def sha(body: bytes) -> str:
    """Return the hex SHA-256 of a byte string."""
    return hashlib.sha256(body).hexdigest()


class AssetServer:
    """An HTTP server whose assets the test can replace between runs."""

    def __init__(self) -> None:
        """Start serving an empty asset map on a free local port."""
        self.assets: dict[str, bytes] = {}
        assets = self.assets

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self) -> None:  # noqa: N802 - http.server's handler name
                body = assets.get(self.path)
                self.send_response(200 if body is not None else 404)
                self.end_headers()
                self.wfile.write(body or b'')

            def log_message(self, *args: object) -> None:
                """Keep request logs out of test output."""

        self.server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.url = f'http://127.0.0.1:{self.server.server_port}'
        threading.Thread(target=self.server.serve_forever, daemon=True).start()


@pytest.fixture
def server() -> Iterator[AssetServer]:
    """Serve release assets for the duration of one test."""
    served = AssetServer()
    yield served
    served.server.shutdown()


@pytest.fixture
def repo(monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    """Create an isolated Git repository."""
    for name in ('GIT_DIR', 'GIT_INDEX_FILE', 'GIT_WORK_TREE'):
        monkeypatch.delenv(name, raising=False)
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'refresh-pins-{uuid4().hex}'
    root.mkdir()
    try:
        git(root, 'init', '--quiet', '--initial-branch=main')
        yield root
    finally:
        shutil.rmtree(root)


def git(root: Path, *arguments: str) -> None:
    """Run Git in the fixture repository with a fixed identity."""
    identity = ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid']
    subprocess.run(['git', *identity, *arguments], cwd=root, check=True, capture_output=True)


def write(root: Path, path: str, text: str) -> None:
    """Write a repository file, creating its directory."""
    (root / path).parent.mkdir(parents=True, exist_ok=True)
    (root / path).write_text(text)


def commit(root: Path) -> None:
    """Commit everything in the fixture repository."""
    git(root, 'add', '-A')
    git(root, 'commit', '--quiet', '-m', 'fixture')


def virtualgl_pins(url: str, version: str, amd64: str, arm64: str) -> str:
    """Return a pin file holding one VirtualGL-shaped package entry."""
    return (
        '---\n'
        'tools:\n'
        '  - name: virtualgl\n'
        f'    version: "{version}"\n'
        f'    url_prefix: {url}\n'
        '    asset_prefix: "virtualgl_{version}_"\n'
        '    extension: deb\n'
        '    deb: true\n'
        '    archives:\n'
        '      amd64:\n'
        '        target: amd64\n'
        f'        checksum: {amd64}\n'
        '      arm64:\n'
        '        target: arm64\n'
        f'        checksum: {arm64}\n'
    )


def serve_virtualgl(server: AssetServer, version: str, tag: bytes) -> dict[str, str]:
    """Serve both VirtualGL architectures for a version and return their checksums."""
    checksums = {}
    for arch in refresh.ARCHITECTURES:
        body = tag + arch.encode()
        server.assets[f'/{version}/virtualgl_{version}_{arch}.deb'] = body
        checksums[arch] = sha(body)
    return checksums


def run(root: Path, *paths: str) -> int:
    """Run the script's entry point against the fixture repository."""
    return refresh.main(['--repo-root', str(root), *paths])


def test_bumped_pin_gets_every_architecture_rehashed(repo: Path, server: AssetServer) -> None:
    """A bumped version's checksums are recomputed from the new assets, in place."""
    old = serve_virtualgl(server, '1.0', b'old')
    write(repo, PINS, virtualgl_pins(server.url, '1.0', old['amd64'], old['arm64']))
    commit(repo)
    new = serve_virtualgl(server, '2.0', b'new')
    write(repo, PINS, virtualgl_pins(server.url, '2.0', old['amd64'], old['arm64']))

    assert run(repo, PINS) == 0
    assert (repo / PINS).read_text() == virtualgl_pins(
        server.url, '2.0', new['amd64'], new['arm64']
    )


def test_unchanged_pin_with_matching_assets_is_left_alone(repo: Path, server: AssetServer) -> None:
    """A pin whose version and assets are unchanged passes without an edit."""
    checksums = serve_virtualgl(server, '1.0', b'same')
    text = virtualgl_pins(server.url, '1.0', checksums['amd64'], checksums['arm64'])
    write(repo, PINS, text)
    commit(repo)

    assert run(repo, PINS) == 0
    assert (repo / PINS).read_text() == text


def test_failed_download_fails_and_leaves_the_file(repo: Path, server: AssetServer) -> None:
    """A missing asset for any architecture fails the refresh with nothing written."""
    old = serve_virtualgl(server, '1.0', b'old')
    write(repo, PINS, virtualgl_pins(server.url, '1.0', old['amd64'], old['arm64']))
    commit(repo)
    serve_virtualgl(server, '2.0', b'new')
    del server.assets['/2.0/virtualgl_2.0_arm64.deb']
    bumped = virtualgl_pins(server.url, '2.0', old['amd64'], old['arm64'])
    write(repo, PINS, bumped)

    assert run(repo, PINS) == 1
    assert (repo / PINS).read_text() == bumped


def test_moved_tag_under_unchanged_version_fails(repo: Path, server: AssetServer) -> None:
    """An unchanged version that now hashes differently is a moved tag, not a bump."""
    recorded = serve_virtualgl(server, '1.0', b'original')
    text = virtualgl_pins(server.url, '1.0', recorded['amd64'], recorded['arm64'])
    write(repo, PINS, text)
    commit(repo)
    serve_virtualgl(server, '1.0', b'republished')

    assert run(repo, PINS) == 1
    assert (repo / PINS).read_text() == text


def tool_pins(url: str, version: str, checksums: dict[str, str]) -> str:
    """Return a pin file with one tool whose prefix carries its version."""
    return (
        '---\n'
        'tools:\n'
        '  - name: tool\n'
        f'    version: tool-v{version}\n'
        f'    url_prefix: {url}\n'
        '    asset_prefix: "{version}-"\n'
        '    archives:\n'
        '      amd64:\n'
        '        target: x86_64\n'
        f'        checksum: {checksums["amd64"]}\n'
        '      arm64:\n'
        '        target: aarch64\n'
        f'        checksum: {checksums["arm64"]}\n'
    )


def serve_tool(server: AssetServer, version: str, tag: bytes) -> dict[str, str]:
    """Serve the tool's archives at the URL fetch-pinned-tool.py assembles."""
    checksums = {}
    for arch, target in (('amd64', 'x86_64'), ('arm64', 'aarch64')):
        body = tag + target.encode()
        server.assets[f'/tool-v{version}/tool-v{version}-{target}.tar.gz'] = body
        checksums[arch] = sha(body)
    return checksums


def test_tool_list_urls_follow_the_fetcher(repo: Path, server: AssetServer) -> None:
    """A tool's URL is the one fetch-pinned-tool.py assembles, version placeholder included."""
    old = serve_tool(server, '1.0', b'old')
    write(repo, PINS, tool_pins(server.url, '1.0', old))
    commit(repo)
    new = serve_tool(server, '2.0', b'new')
    write(repo, PINS, tool_pins(server.url, '2.0', old))

    assert run(repo, PINS) == 0
    assert (repo / PINS).read_text() == tool_pins(server.url, '2.0', new)


def test_files_without_pins_are_ignored(repo: Path) -> None:
    """Changed files the script does not own pass through untouched."""
    write(repo, 'README.md', 'text\n')
    commit(repo)

    assert run(repo, 'README.md', '.devcontainer/devcontainer.json') == 0


def serve_shared_virtualgl(server: AssetServer, version: str, body: bytes) -> str:
    """Serve one architecture-independent VirtualGL asset at both URLs; return its checksum."""
    for arch in refresh.ARCHITECTURES:
        server.assets[f'/{version}/virtualgl_{version}_{arch}.deb'] = body
    return sha(body)


def test_bumped_pin_sharing_one_checksum_is_rehashed(repo: Path, server: AssetServer) -> None:
    """Architectures that record one shared checksum get it rewritten together."""
    old = serve_shared_virtualgl(server, '1.0', b'old')
    write(repo, PINS, virtualgl_pins(server.url, '1.0', old, old))
    commit(repo)
    new = serve_shared_virtualgl(server, '2.0', b'new')
    write(repo, PINS, virtualgl_pins(server.url, '2.0', old, old))

    assert run(repo, PINS) == 0
    assert (repo / PINS).read_text() == virtualgl_pins(server.url, '2.0', new, new)


def test_shared_checksum_that_now_diverges_fails(repo: Path, server: AssetServer) -> None:
    """A shared recorded checksum whose architectures now hash apart cannot be replaced."""
    old = serve_shared_virtualgl(server, '1.0', b'old')
    write(repo, PINS, virtualgl_pins(server.url, '1.0', old, old))
    commit(repo)
    serve_virtualgl(server, '2.0', b'new')
    bumped = virtualgl_pins(server.url, '2.0', old, old)
    write(repo, PINS, bumped)

    assert run(repo, PINS) == 1
    assert (repo / PINS).read_text() == bumped


def test_checksum_recorded_elsewhere_in_the_file_fails(repo: Path, server: AssetServer) -> None:
    """A stale checksum that also appears outside the bumped pin is not replaced."""
    old = serve_shared_virtualgl(server, '1.0', b'old')
    text = virtualgl_pins(server.url, '1.0', old, old) + f'other_checksum: "sha256:{old}"\n'
    write(repo, PINS, text)
    commit(repo)
    serve_shared_virtualgl(server, '2.0', b'new')
    bumped = text.replace('"1.0"', '"2.0"')
    write(repo, PINS, bumped)

    assert run(repo, PINS) == 1
    assert (repo / PINS).read_text() == bumped


LAYOUT_TARGETS = (('amd64', 'x86_64'), ('arm64', 'aarch64'))


def layout_defaults(url: str, version: str, checksums: dict[str, dict[str, str]]) -> str:
    """Return a pin file with a bare-binary tool and a tool unpacking into its own dir."""

    def archives(name: str) -> str:
        return ''.join(
            f'      {arch}:\n        target: {target}\n        checksum: {checksums[name][arch]}\n'
            for arch, target in LAYOUT_TARGETS
        )

    return (
        '---\n'
        'tools:\n'
        '  - name: bare\n'
        f'    version: v{version}\n'
        f'    url_prefix: {url}\n'
        '    asset_prefix: bare-linux-\n'
        '    bare_binary: true\n'
        f'    archives:\n{archives("bare")}'
        '  - name: nested\n'
        f'    version: v{version}\n'
        f'    url_prefix: {url}\n'
        '    asset_prefix: "nested-{version}.linux."\n'
        '    extension: tar.xz\n'
        '    binaries_dir: "nested-{version}"\n'
        f'    archives:\n{archives("nested")}'
    )


def serve_layouts(server: AssetServer, version: str, tag: bytes) -> dict[str, dict[str, str]]:
    """Serve both tools at the release URLs their publishers use; return their checksums."""
    paths = {
        'bare': '/v{version}/bare-linux-{target}',
        'nested': '/v{version}/nested-v{version}.linux.{target}.tar.xz',
    }
    checksums: dict[str, dict[str, str]] = {}
    for name, path in paths.items():
        for arch, target in LAYOUT_TARGETS:
            body = tag + name.encode() + target.encode()
            server.assets[path.format(version=version, target=target)] = body
            checksums.setdefault(name, {})[arch] = sha(body)
    return checksums


def test_bare_binary_and_nested_dir_urls_follow_the_fetcher(
    repo: Path, server: AssetServer
) -> None:
    """A bare binary has no extension in its URL; a nested archive keeps its own extension."""
    old = serve_layouts(server, '1.0', b'old')
    write(repo, PINS, layout_defaults(server.url, '1.0', old))
    commit(repo)
    new = serve_layouts(server, '2.0', b'new')
    write(repo, PINS, layout_defaults(server.url, '2.0', old))

    assert run(repo, PINS) == 0
    assert (repo / PINS).read_text() == layout_defaults(server.url, '2.0', new)


BOOTSTRAP = '.agents/plugins/agentdev/bin/macos-bootstrap.zsh'
DARWIN_TARGETS = {
    'iwe': {'arm64': 'aarch64-apple-darwin', 'amd64': 'x86_64-apple-darwin'},
}


def serve_darwin(server: AssetServer, iwe: str, tag: bytes) -> dict[str, str]:
    """Serve the bootstrap's darwin archives and return digests by SHA256 key."""
    digests = {}
    for arch, target in DARWIN_TARGETS['iwe'].items():
        body = tag + f'iwe-{iwe}-{arch}'.encode()
        server.assets[f'/iwe-org/iwe/releases/download/{iwe}/{iwe}-{target}.tar.gz'] = body
        digests[f'iwe-{arch}'] = sha(body)
    return digests


def bootstrap(url: str, iwe: str, digests: dict[str, str]) -> str:
    """Return the real bootstrap, downloading from ``url``, at the given version and digests."""
    text = (REPO_ROOT / BOOTSTRAP).read_text().replace('https://github.com', url)
    lines = []
    for line in text.splitlines(keepends=True):
        key = line.split()[0] if line.startswith('  ') and line.split() else None
        if key in digests and len(line.split()) == 2:
            line = f'  {key} {digests[key]}\n'
        elif line.startswith('typeset -r IWE_VERSION='):
            line = f'typeset -r IWE_VERSION={iwe}\n'
        lines.append(line)
    return ''.join(lines)


def test_bootstrap_bump_rehashes_the_bumped_tool(repo: Path, server: AssetServer) -> None:
    """A bumped bootstrap version gets its darwin digests rewritten."""
    old = serve_darwin(server, 'iwe-v1.0.0', b'old')
    write(repo, BOOTSTRAP, bootstrap(server.url, 'iwe-v1.0.0', old))
    commit(repo)
    new = serve_darwin(server, 'iwe-v2.0.0', b'old')
    write(repo, BOOTSTRAP, bootstrap(server.url, 'iwe-v2.0.0', old))

    assert run(repo, BOOTSTRAP) == 0
    assert (repo / BOOTSTRAP).read_text() == bootstrap(server.url, 'iwe-v2.0.0', new)


def test_bootstrap_moved_tag_fails(repo: Path, server: AssetServer) -> None:
    """An unchanged bootstrap version whose archive changed fails with the script kept."""
    recorded = serve_darwin(server, 'iwe-v1.0.0', b'original')
    text = bootstrap(server.url, 'iwe-v1.0.0', recorded)
    write(repo, BOOTSTRAP, text)
    commit(repo)
    serve_darwin(server, 'iwe-v1.0.0', b'republished')

    assert run(repo, BOOTSTRAP) == 1
    assert (repo / BOOTSTRAP).read_text() == text


def test_failure_in_one_file_writes_no_file(repo: Path, server: AssetServer) -> None:
    """Every file stays untouched when any file's refresh fails."""
    old_tool = serve_tool(server, '1.0', b'old')
    old_darwin = serve_darwin(server, 'iwe-v1.0.0', b'old')
    write(repo, PINS, tool_pins(server.url, '1.0', old_tool))
    write(repo, BOOTSTRAP, bootstrap(server.url, 'iwe-v1.0.0', old_darwin))
    commit(repo)
    serve_tool(server, '2.0', b'new')
    tool_bumped = tool_pins(server.url, '2.0', old_tool)
    bootstrap_bumped = bootstrap(server.url, 'iwe-v9.9.9', old_darwin)
    write(repo, PINS, tool_bumped)
    write(repo, BOOTSTRAP, bootstrap_bumped)

    assert run(repo, PINS, BOOTSTRAP) == 1
    assert (repo / PINS).read_text() == tool_bumped
    assert (repo / BOOTSTRAP).read_text() == bootstrap_bumped
