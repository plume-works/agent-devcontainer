"""Tests for scripts/renovate-post-upgrade.py, with its tools replaced by recording stubs."""

from __future__ import annotations

from collections.abc import Iterator
import os
from pathlib import Path
import shutil
import subprocess
from uuid import uuid4

import pytest
from scratch import TMP_ROOT

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = 'scripts/renovate-post-upgrade.py'
TOOLCHAIN = 'mise.toml'
IWE_CONFIG = '.iwe/config.toml'
INSTALLER = 'scripts/install-toolchain'
OLD_X64, OLD_ARM64, NEW_X64, NEW_ARM64 = ('a' * 64, 'b' * 64, 'c' * 64, 'd' * 64)


def installer(version: str) -> str:
    """Return an install-toolchain holding the pin lines the task rewrites."""
    return (
        '#!/usr/bin/env bash\n'
        '# renovate: datasource=github-releases depName=jdx/mise\n'
        f'readonly MISE_VERSION={version}\n'
        f'readonly MISE_SHA256_X64={OLD_X64}\n'
        f'readonly MISE_SHA256_ARM64={OLD_ARM64}\n'
        'install_mise() { :; }\n'
    )


# Each stub logs its arguments; STUB_* variables choose its outcome per call.
UV_STUB = """#!/usr/bin/env bash
set -euo pipefail
printf 'uv %s\\n' "$*" >> "$STUB_LOG"
printf '%s\n' "${SKIP-<unset>}" >> "$STUB_LOG.skip"
count_file="$STUB_LOG.precommit"
count=$(( $(cat "$count_file" 2>/dev/null || echo 0) + 1 ))
echo "$count" > "$count_file"
if [[ $count -eq 1 && -n "${STUB_PRECOMMIT_REWRITE:-}" ]]; then
  echo formatted > "$STUB_PRECOMMIT_REWRITE"
  exit 1
fi
exit "${STUB_PRECOMMIT_EXIT:-0}"
"""
# mise runs the command after `--`; the bumped iwe migrates the config the way a bump does.
MISE_STUB = """#!/usr/bin/env bash
set -euo pipefail
printf 'mise %s | trusted=%s\\n' "$*" "${MISE_TRUSTED_CONFIG_PATHS-}" >> "$STUB_LOG"
[[ -z "${STUB_MISE_EXIT:-}" ]] || exit "$STUB_MISE_EXIT"
while [[ "$1" != -- ]]; do shift; done
shift
if [[ "$1 $2" == 'iwe normalize' ]]; then
  echo migrated > .iwe/config.toml
else
  exec "$@"
fi
"""


@pytest.fixture
def repo() -> Iterator[Path]:
    """Create a Git repository holding the script, with one committed file per concern."""
    TMP_ROOT.mkdir(exist_ok=True)
    root = TMP_ROOT / f'post-upgrade-{uuid4().hex}'
    (root / 'scripts').mkdir(parents=True)
    (root / '.iwe').mkdir()
    (root / 'bin').mkdir()
    shutil.copy(REPO_ROOT / SCRIPT, root / SCRIPT)
    for name, body in (('uv', UV_STUB), ('mise', MISE_STUB)):
        (root / 'bin' / name).write_text(body)
        (root / 'bin' / name).chmod(0o755)
    (root / '.gitignore').write_text('bin/\nstub.log*\n.tmp/\nrelease/\n')
    (root / INSTALLER).write_text(installer('1.0.0'))
    for path in ('pins.yml', 'gone.yml', IWE_CONFIG):
        (root / path).write_text('original\n')
    (root / TOOLCHAIN).write_text('original\n')
    try:
        git(root, 'init', '--quiet', '--initial-branch=main')
        git(root, 'add', '-A')
        git(root, 'commit', '--quiet', '-m', 'fixture')
        yield root
    finally:
        shutil.rmtree(root)


def git(root: Path, *arguments: str) -> None:
    """Run Git in the fixture repository, isolated from any outer Git environment."""
    identity = ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid']
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    subprocess.run(['git', *identity, *arguments], cwd=root, check=True, env=env)


def run(root: Path, **stub_env: str) -> tuple[int, list[str]]:
    """Run the script with stubbed tools; return its exit code and the stub call log."""
    log = root / 'stub.log'
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    env.update(
        stub_env,
        STUB_LOG=str(log),
        PATH=f'{root / "bin"}:{env["PATH"]}',
        MISE_RELEASES_URL=f'file://{root / "release"}',
    )
    result = subprocess.run([str(root / SCRIPT)], cwd=root, env=env, check=False)
    calls = log.read_text().splitlines() if log.exists() else []
    return result.returncode, calls


def test_changed_files_reach_pre_commit(repo: Path) -> None:
    """Modified and new files are checked; deleted files are skipped."""
    (repo / 'pins.yml').write_text('bumped\n')
    (repo / 'new.yml').write_text('added\n')
    (repo / 'gone.yml').unlink()

    code, calls = run(repo)

    assert code == 0
    assert calls == ['uv run --frozen pre-commit run --files pins.yml new.yml']


def test_a_hook_rewrite_passes_on_the_second_pass(repo: Path) -> None:
    """A first pass that only rewrites files is followed by a clean second pass."""
    (repo / 'pins.yml').write_text('bumped\n')

    code, calls = run(repo, STUB_PRECOMMIT_REWRITE=str(repo / 'pins.yml'))

    assert code == 0
    assert [call for call in calls if 'pre-commit' in call] == [
        'uv run --frozen pre-commit run --files pins.yml',
        'uv run --frozen pre-commit run --files pins.yml',
    ]
    assert (repo / 'pins.yml').read_text() == 'formatted\n'


def test_a_hook_still_failing_on_the_second_pass_fails(repo: Path) -> None:
    """A hook that fails both passes fails the task."""
    (repo / 'pins.yml').write_text('bumped\n')

    code, _ = run(repo, STUB_PRECOMMIT_EXIT='1')

    assert code != 0


def test_nothing_changed_runs_nothing(repo: Path) -> None:
    """With no edits against HEAD the task is a no-op."""
    code, calls = run(repo)

    assert code == 0
    assert calls == []


def pre_commit_skips(root: Path) -> list[str]:
    """Return the SKIP value each pre-commit invocation saw."""
    return (root / 'stub.log.skip').read_text().splitlines()


def test_pre_commit_skips_the_default_branch_guard_on_every_pass(repo: Path) -> None:
    """Both passes run on the base branch, so both skip no-commit-to-branch."""
    (repo / 'pins.yml').write_text('bumped\n')

    code, _ = run(repo, STUB_PRECOMMIT_REWRITE=str(repo / 'pins.yml'))

    assert code == 0
    assert pre_commit_skips(repo) == ['no-commit-to-branch', 'no-commit-to-branch']


def test_pre_commit_skip_keeps_the_callers_value(repo: Path) -> None:
    """A SKIP set by the caller is extended, not replaced."""
    (repo / 'pins.yml').write_text('bumped\n')

    code, _ = run(repo, SKIP='fixture-hook')

    assert code == 0
    assert pre_commit_skips(repo) == ['fixture-hook,no-commit-to-branch']


def test_toolchain_bump_runs_the_bumped_iwe_before_pre_commit(repo: Path) -> None:
    """A mise.toml change runs the locked iwe, and pre-commit sees what it migrated."""
    (repo / TOOLCHAIN).write_text('bumped\n')

    code, calls = run(repo)

    assert code == 0
    pre_commit = f'uv run --frozen pre-commit run --files {IWE_CONFIG} {TOOLCHAIN}'
    assert calls == [
        f'mise exec --locked -- iwe normalize | trusted={repo}',
        f'mise exec --locked -- {pre_commit} | trusted={repo}',
        pre_commit,
    ]


def test_toolchain_bump_runs_both_pre_commit_passes_under_the_bumped_iwe(repo: Path) -> None:
    """The hooks' bare `iwe` resolves to the locked one on every pass, not the image's."""
    (repo / TOOLCHAIN).write_text('bumped\n')

    code, calls = run(repo, STUB_PRECOMMIT_REWRITE=str(repo / 'pins.yml'))

    assert code == 0
    assert [call for call in calls if call.startswith('mise')] == [
        f'mise exec --locked -- iwe normalize | trusted={repo}',
        f'mise exec --locked -- uv run --frozen pre-commit run --files {IWE_CONFIG} {TOOLCHAIN}'
        f' | trusted={repo}',
        f'mise exec --locked -- uv run --frozen pre-commit run --files {IWE_CONFIG} {TOOLCHAIN}'
        f' pins.yml | trusted={repo}',
    ]


def test_no_toolchain_change_runs_no_iwe(repo: Path) -> None:
    """The bumped iwe runs only when the toolchain changed."""
    (repo / 'pins.yml').write_text('bumped\n')

    _, calls = run(repo)

    assert not any(call.startswith('mise') for call in calls)


def test_a_failed_iwe_run_fails_before_pre_commit(repo: Path) -> None:
    """An iwe that cannot be installed or run fails the task without running pre-commit."""
    (repo / TOOLCHAIN).write_text('bumped\n')

    code, calls = run(repo, STUB_MISE_EXIT='1')

    assert code != 0
    assert not any('pre-commit' in call for call in calls)


def release(root: Path, version: str, sums: str) -> None:
    """Serve SHASUMS256.txt for VERSION from the fixture's release directory."""
    (root / 'release' / f'v{version}').mkdir(parents=True)
    (root / 'release' / f'v{version}' / 'SHASUMS256.txt').write_text(sums)


def test_mise_bump_refreshes_the_pinned_digests_before_pre_commit(repo: Path) -> None:
    """The bumped release's musl digests replace the pins, and pre-commit sees them."""
    (repo / INSTALLER).write_text(installer('2.0.0'))
    release(
        repo,
        '2.0.0',
        f'{"e" * 64}  ./mise-v2.0.0-linux-x64\n'
        f'{NEW_X64}  ./mise-v2.0.0-linux-x64-musl\n'
        f'{NEW_ARM64}  ./mise-v2.0.0-linux-arm64-musl\n',
    )

    code, calls = run(repo)

    assert code == 0
    assert (repo / INSTALLER).read_text() == installer('2.0.0').replace(OLD_X64, NEW_X64).replace(
        OLD_ARM64, NEW_ARM64
    )
    assert calls == [f'uv run --frozen pre-commit run --files {INSTALLER}']


def test_a_release_missing_a_musl_digest_fails_before_pre_commit(repo: Path) -> None:
    """Without a digest for every architecture the pins stay put and the task fails."""
    (repo / INSTALLER).write_text(installer('2.0.0'))
    release(repo, '2.0.0', f'{NEW_X64}  ./mise-v2.0.0-linux-x64-musl\n')

    code, calls = run(repo)

    assert code != 0
    assert (repo / INSTALLER).read_text() == installer('2.0.0')
    assert calls == []
