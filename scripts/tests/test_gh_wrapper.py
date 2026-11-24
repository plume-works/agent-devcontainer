"""The gh wrapper of the image gives the token from the git credential helper to the real gh."""

from collections.abc import Iterator
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

WRAPPER = Path(__file__).parents[2] / 'docker/devcontainer/gh'
TOOLS = ('bash', 'sh', 'git', 'timeout', 'grep', 'cut', 'readlink', 'printf', 'cat')
REAL_GH = '#!/usr/bin/env bash\necho "token=${GH_TOKEN:-} args=$*"\n'
HELPER = '!f() { echo username=x-access-token; echo password=helper-token; }; f'


@pytest.fixture
def scratch() -> Iterator[Path]:
    """Yield a scratch root whose ``tools`` directory holds only what the wrapper needs."""
    root = TMP_ROOT / f'gh-wrapper-{uuid4().hex}'
    (root / 'tools').mkdir(parents=True)
    for tool in TOOLS:
        (root / 'tools' / tool).symlink_to(shutil.which(tool))
    (root / 'tools/env').symlink_to(shutil.which('env'))
    yield root
    shutil.rmtree(root)


def install(directory: Path, body: str) -> None:
    directory.mkdir()
    (directory / 'gh').write_text(body)
    (directory / 'gh').chmod(0o755)


def run_gh(
    scratch: Path, path: list[Path], helper: str | None, **extra: str
) -> subprocess.CompletedProcess[str]:
    """Run the first ``gh`` on ``path`` with a git config that has ``helper``, if any."""
    config = scratch / 'gitconfig'
    config.write_text(f'[credential]\n\thelper = "{helper}"\n' if helper else '')
    return subprocess.run(
        ['gh', 'api', 'user'],
        cwd=scratch,
        env={
            'PATH': os.pathsep.join(str(entry) for entry in [*path, scratch / 'tools']),
            'HOME': str(scratch),
            'GIT_CONFIG_GLOBAL': str(config),
            'GIT_CONFIG_NOSYSTEM': '1',
            **extra,
        },
        capture_output=True,
        text=True,
    )


@pytest.fixture
def wrapped(scratch: Path) -> list[Path]:
    """Return a ``PATH`` that has the wrapper before a stub of the real gh."""
    install(scratch / 'wrapper', WRAPPER.read_text())
    install(scratch / 'real', REAL_GH)
    return [scratch / 'wrapper', scratch / 'real']


def test_the_helper_token_reaches_the_real_gh(scratch: Path, wrapped: list[Path]) -> None:
    result = run_gh(scratch, wrapped, HELPER)

    assert result.returncode == 0, result.stderr
    assert result.stdout == 'token=helper-token args=api user\n'


def test_without_a_helper_the_real_gh_gets_no_token(scratch: Path, wrapped: list[Path]) -> None:
    result = run_gh(scratch, wrapped, None)

    assert result.returncode == 0, result.stderr
    assert result.stdout == 'token= args=api user\n'


def test_a_token_already_set_is_kept(scratch: Path, wrapped: list[Path]) -> None:
    result = run_gh(scratch, wrapped, HELPER, GH_TOKEN='caller-token')

    assert result.stdout == 'token=caller-token args=api user\n'


def test_with_no_real_gh_on_path_the_wrapper_exits_127(scratch: Path) -> None:
    install(scratch / 'wrapper', WRAPPER.read_text())

    result = run_gh(scratch, [scratch / 'wrapper'], None)

    assert result.returncode == 127
    assert 'real gh not found on PATH' in result.stderr


def test_gh_as_the_git_credential_helper_is_asked_once(scratch: Path, wrapped: list[Path]) -> None:
    calls = scratch / 'helper-calls'
    helper = f'!f() {{ echo call >> {calls}; gh auth git-credential "$@"; }}; f'

    result = run_gh(scratch, wrapped, helper)

    assert result.returncode == 0, result.stderr
    assert calls.read_text() == 'call\n'
