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

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / 'scripts/refresh-pin-checksums.py'
TMP_ROOT = REPO_ROOT / '.tmp'


def _load_script():
    """Load the hyphen-named script as a module."""
    spec = importlib.util.spec_from_file_location('refresh_pin_checksums', SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


refresh = _load_script()
XPRA = 'ansible/roles/xpra_setup/defaults/main.yml'
DEV_TOOLS = 'ansible/roles/dev_tools/defaults/main.yml'
DEV_TOOLS_TASK = refresh.PIN_FILES[DEV_TOOLS].task_file


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
    """Create an isolated Git repository carrying the real dev_tools install task."""
    for name in ('GIT_DIR', 'GIT_INDEX_FILE', 'GIT_WORK_TREE'):
        monkeypatch.delenv(name, raising=False)
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'refresh-pins-{uuid4().hex}'
    (root / DEV_TOOLS_TASK).parent.mkdir(parents=True)
    shutil.copy(REPO_ROOT / DEV_TOOLS_TASK, root / DEV_TOOLS_TASK)
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


def xpra_defaults(url: str, version: str, amd64: str, arm64: str) -> str:
    """Return a VirtualGL-shaped defaults file."""
    return (
        '---\n'
        '# VirtualGL pin.\n'
        f'xpra_setup_virtualgl_version: "{version}"\n'
        'xpra_setup_virtualgl_checksums:\n'
        f'  amd64: "sha256:{amd64}"\n'
        f'  arm64: "sha256:{arm64}"\n'
        'xpra_setup_virtualgl_download_url: >-\n'
        f'  {url}/{{{{ xpra_setup_virtualgl_version }}}}/virtualgl_{{{{\n'
        '  xpra_setup_virtualgl_version }}_{{ xpra_setup_virtualgl_arch }}.deb\n'
    )


def serve_virtualgl(server: AssetServer, version: str, tag: bytes) -> dict[str, str]:
    """Serve both VirtualGL architectures for a version and return their checksums."""
    checksums = {}
    for arch in ('amd64', 'arm64'):
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
    write(repo, XPRA, xpra_defaults(server.url, '1.0', old['amd64'], old['arm64']))
    commit(repo)
    new = serve_virtualgl(server, '2.0', b'new')
    write(repo, XPRA, xpra_defaults(server.url, '2.0', old['amd64'], old['arm64']))

    assert run(repo, XPRA) == 0
    assert (repo / XPRA).read_text() == xpra_defaults(
        server.url, '2.0', new['amd64'], new['arm64']
    )


def test_unchanged_pin_with_matching_assets_is_left_alone(repo: Path, server: AssetServer) -> None:
    """A pin whose version and assets are unchanged passes without an edit."""
    checksums = serve_virtualgl(server, '1.0', b'same')
    text = xpra_defaults(server.url, '1.0', checksums['amd64'], checksums['arm64'])
    write(repo, XPRA, text)
    commit(repo)

    assert run(repo, XPRA) == 0
    assert (repo / XPRA).read_text() == text


def test_failed_download_fails_and_leaves_the_file(repo: Path, server: AssetServer) -> None:
    """A missing asset for any architecture fails the refresh with nothing written."""
    old = serve_virtualgl(server, '1.0', b'old')
    write(repo, XPRA, xpra_defaults(server.url, '1.0', old['amd64'], old['arm64']))
    commit(repo)
    serve_virtualgl(server, '2.0', b'new')
    del server.assets['/2.0/virtualgl_2.0_arm64.deb']
    bumped = xpra_defaults(server.url, '2.0', old['amd64'], old['arm64'])
    write(repo, XPRA, bumped)

    assert run(repo, XPRA) == 1
    assert (repo / XPRA).read_text() == bumped


def test_moved_tag_under_unchanged_version_fails(repo: Path, server: AssetServer) -> None:
    """An unchanged version that now hashes differently is a moved tag, not a bump."""
    recorded = serve_virtualgl(server, '1.0', b'original')
    text = xpra_defaults(server.url, '1.0', recorded['amd64'], recorded['arm64'])
    write(repo, XPRA, text)
    commit(repo)
    serve_virtualgl(server, '1.0', b'republished')

    assert run(repo, XPRA) == 1
    assert (repo / XPRA).read_text() == text


def dev_tools_defaults(url: str, version: str, checksums: dict[str, str]) -> str:
    """Return a dev_tools-shaped defaults file with one tool whose prefix carries its version."""
    return (
        '---\n'
        'dev_tools_pinned_tools:\n'
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
    """Serve the tool's archives at the URL the install task assembles."""
    checksums = {}
    for arch, target in (('amd64', 'x86_64'), ('arm64', 'aarch64')):
        body = tag + target.encode()
        server.assets[f'/tool-v{version}/tool-v{version}-{target}.tar.gz'] = body
        checksums[arch] = sha(body)
    return checksums


def test_tool_list_urls_follow_the_install_task(repo: Path, server: AssetServer) -> None:
    """dev_tools URLs come from the install task's templates, version placeholder included."""
    old = serve_tool(server, '1.0', b'old')
    write(repo, DEV_TOOLS, dev_tools_defaults(server.url, '1.0', old))
    commit(repo)
    new = serve_tool(server, '2.0', b'new')
    write(repo, DEV_TOOLS, dev_tools_defaults(server.url, '2.0', old))

    assert run(repo, DEV_TOOLS) == 0
    assert (repo / DEV_TOOLS).read_text() == dev_tools_defaults(server.url, '2.0', new)


def test_failure_in_one_file_writes_no_file(repo: Path, server: AssetServer) -> None:
    """Every file stays untouched when any file's refresh fails."""
    old_tool = serve_tool(server, '1.0', b'old')
    old_gl = serve_virtualgl(server, '1.0', b'old')
    write(repo, DEV_TOOLS, dev_tools_defaults(server.url, '1.0', old_tool))
    write(repo, XPRA, xpra_defaults(server.url, '1.0', old_gl['amd64'], old_gl['arm64']))
    commit(repo)
    serve_tool(server, '2.0', b'new')
    tool_bumped = dev_tools_defaults(server.url, '2.0', old_tool)
    gl_bumped = xpra_defaults(server.url, '2.0', old_gl['amd64'], old_gl['arm64'])
    write(repo, DEV_TOOLS, tool_bumped)
    write(repo, XPRA, gl_bumped)

    assert run(repo, DEV_TOOLS, XPRA) == 1
    assert (repo / DEV_TOOLS).read_text() == tool_bumped
    assert (repo / XPRA).read_text() == gl_bumped


def test_files_without_pins_are_ignored(repo: Path) -> None:
    """Changed files the script does not own pass through untouched."""
    write(repo, 'README.md', 'text\n')
    commit(repo)

    assert run(repo, 'README.md', '.devcontainer/devcontainer.json') == 0
