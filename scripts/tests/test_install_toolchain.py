"""Tests for scripts/install-toolchain, run against a stubbed mise in a fixture checkout."""

from collections.abc import Iterator
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

SCRIPT = Path(__file__).parents[2] / 'scripts/install-toolchain'

# Logs its arguments and the settings it ran with; `bin-paths` prints $TOOL_DIRS.
MISE_STUB = """#!/bin/sh
echo "mise $* | cwd=$PWD trusted=$MISE_TRUSTED_CONFIG_PATHS ceiling=$MISE_CEILING_PATHS \
global=$MISE_GLOBAL_CONFIG_FILE" >> "$CALLS"
if [ "$1" = bin-paths ]; then printf '%s\\n' $TOOL_DIRS; fi
"""


@pytest.fixture
def scratch() -> Iterator[Path]:
    """Yield a fresh scratch directory under real /tmp."""
    path = TMP_ROOT / f'install-toolchain-{uuid4().hex}'
    path.mkdir(parents=True)
    yield path
    shutil.rmtree(path)


def stub(directory: Path, name: str, body: str) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(body)
    (directory / name).chmod(0o755)


def checkout(scratch: Path) -> Path:
    root = scratch / 'repo'
    (root / 'scripts').mkdir(parents=True)
    shutil.copy(SCRIPT, root / 'scripts/install-toolchain')
    return root


def run(scratch: Path, stubs: Path, *args: str, **env: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(checkout(scratch) / 'scripts/install-toolchain'), *args],
        env={'PATH': f'{stubs}:/usr/bin:/bin', 'CALLS': str(scratch / 'calls'), **env},
        capture_output=True,
        text=True,
        check=False,
    )


def test_installs_from_the_checkout_and_links_every_executable(scratch: Path) -> None:
    """Only the checkout's lists are installed, locked; each tool's executables are linked."""
    stubs = scratch / 'stubs'
    stub(stubs, 'mise', MISE_STUB)
    first, second = scratch / 'installs/a/bin', scratch / 'installs/b'
    stub(first, 'alpha', '#!/bin/sh\n')
    stub(second, 'beta', '#!/bin/sh\n')
    (second / 'LICENSE').write_text('not a tool')
    bin_dir = scratch / 'out'

    result = run(scratch, stubs, str(bin_dir), TOOL_DIRS=f'{first} {second}')

    assert result.returncode == 0, result.stderr
    root = scratch / 'repo'
    settings = f'cwd={root} trusted={root} ceiling={scratch} global={root}/mise.toml'
    assert (scratch / 'calls').read_text().splitlines() == [
        f'mise install --locked | {settings}',
        f'mise bin-paths | {settings}',
    ]
    assert sorted(path.name for path in bin_dir.iterdir()) == ['alpha', 'beta']
    assert os.readlink(bin_dir / 'alpha') == str(first / 'alpha')


def test_a_failed_install_links_nothing(scratch: Path) -> None:
    stubs = scratch / 'stubs'
    stub(stubs, 'mise', '#!/bin/sh\n[ "$1" != install ] || exit 3\necho /nowhere\n')
    bin_dir = scratch / 'out'

    result = run(scratch, stubs, str(bin_dir))

    assert result.returncode == 3
    assert list(bin_dir.iterdir()) == []


def test_without_mise_off_linux_it_asks_for_mise(scratch: Path) -> None:
    stubs = scratch / 'stubs'
    stub(stubs, 'uname', '#!/bin/sh\necho Darwin\n')

    result = run(scratch, stubs, str(scratch / 'out'), PATH=str(stubs) + ':/usr/bin:/bin')

    assert result.returncode == 1
    assert 'brew install mise' in result.stderr


def release_stubs(stubs: Path, release: Path) -> None:
    """Serve release assets from a directory: curl -o TARGET URL copies its basename."""
    stub(stubs, 'curl', f'#!/bin/sh\ncp "{release}/$(basename "$4")" "$3"\n')
    stub(stubs, 'uname', '#!/bin/sh\n[ "$1" = -m ] && echo x86_64 || echo Linux\n')


def test_without_mise_on_linux_it_installs_the_verified_release(scratch: Path) -> None:
    """The pinned release is installed when the release's checksum list vouches for it."""
    stubs, release = scratch / 'stubs', scratch / 'release'
    release_stubs(stubs, release)
    asset = f'mise-v{pinned_version()}-linux-x64-musl'
    stub(release, asset, MISE_STUB.replace('if [ "$1"', 'if [ "$1" = never ] && [ "$1"'))
    digest = hashlib.sha256((release / asset).read_bytes()).hexdigest()
    (release / 'SHASUMS256.txt').write_text(f'{digest}  ./{asset}\n')
    bin_dir = scratch / 'out'

    result = run(scratch, stubs, str(bin_dir))

    assert result.returncode == 0, result.stderr
    assert (bin_dir / 'mise').read_bytes() == (release / asset).read_bytes()
    assert (scratch / 'calls').read_text().startswith('mise install --locked')


def test_without_mise_on_linux_a_checksum_mismatch_installs_nothing(scratch: Path) -> None:
    stubs, release = scratch / 'stubs', scratch / 'release'
    release_stubs(stubs, release)
    asset = f'mise-v{pinned_version()}-linux-x64-musl'
    stub(release, asset, '#!/bin/sh\n')
    (release / 'SHASUMS256.txt').write_text(f'{"0" * 64}  ./{asset}\n')
    bin_dir = scratch / 'out'

    result = run(scratch, stubs, str(bin_dir))

    assert result.returncode == 1
    assert 'checksum mismatch' in result.stderr
    assert not (bin_dir / 'mise').exists()


def pinned_version() -> str:
    """Return the script's MISE_VERSION, the contract the release asset name follows."""
    line = next(
        line
        for line in SCRIPT.read_text().splitlines()
        if line.startswith('readonly MISE_VERSION=')
    )
    return line.split('=', 1)[1]
