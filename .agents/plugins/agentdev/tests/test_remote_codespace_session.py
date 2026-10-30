#!/usr/bin/env python3

"""Behavior tests for the remote Codespace session scripts."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from git_fixtures import FIXTURE_ENV, git, outcome
import pytest

SKILL = 'skills/remote-codespace-session/agent-code'
EXT = 'py'

# A stateful gh: codespaces live in a JSON file, and every call is logged.
GH_STUB = r"""
import json
import os
import re
import sys

state_path = os.environ['CS_STATE']
state = json.loads(open(state_path).read())
arguments = sys.argv[1:]
with open(state_path + '.log', 'a') as log:
    log.write(json.dumps(arguments) + '\n')


def save():
    open(state_path, 'w').write(json.dumps(state))


def option(name):
    return arguments[arguments.index(name) + 1] if name in arguments else None


if arguments[:2] == ['repo', 'view']:
    query = option('-q')
    print('octo/fixture-repo' if 'owner' in query else 'fixture-repo')
    sys.exit(0)
if arguments[:2] == ['codespace', 'list']:
    if state.get('list_error'):
        print(state['list_error'], file=sys.stderr)
        sys.exit(1)
    query = option('-q')
    if query == 'length':
        print(len(state['codespaces']))
        sys.exit(0)
    match = re.search(r'select\(\.(\w+)=="([^"]*)"\) \| \.(\w+)', query)
    key, value, field = match.groups()
    for codespace in state['codespaces']:
        if codespace[key] == value:
            print(codespace[field])
    if state.get('settle'):
        for codespace in state['codespaces']:
            codespace['state'] = state['settle']
        state['codespaces'] = [c for c in state['codespaces'] if c['state'] != 'Deleted']
        save()
    sys.exit(0)
if arguments[:2] == ['codespace', 'create']:
    if state.get('create_error'):
        print(state['create_error'], file=sys.stderr)
        sys.exit(1)
    state['codespaces'].append(
        {'name': 'fixture-cs-new', 'displayName': option('--display-name'), 'state': 'Starting'}
    )
    state['settle'] = 'Available'
    save()
    print('  fixture-cs-new  ')
    sys.exit(0)
if arguments[:2] == ['codespace', 'stop']:
    if state.get('stop_error'):
        print(state['stop_error'], file=sys.stderr)
        sys.exit(1)
    state['codespaces'][0]['state'] = 'ShuttingDown'
    state['settle'] = state.get('stop_settles', 'Shutdown')
    save()
    sys.exit(0)
if arguments[:2] == ['codespace', 'delete']:
    state['settle'] = 'Deleted'
    save()
    sys.exit(0)
if arguments[:2] == ['codespace', 'ssh']:
    if '--config' in arguments:
        print('Host cs.fixture-cs.main\n  HostName localhost')
        sys.exit(0)
    remote = arguments[arguments.index('--') + 1]
    reply = state.get('ssh_replies', {}).get('preflight' if 'remote_status' in remote else 'run')
    reply = reply or {'stdout': 'remote ok', 'exit': 0}
    print(reply['stdout'], end='' if reply.get('no_newline') else '\n')
    sys.exit(reply['exit'])
sys.exit(64)
"""

RECORDER = """#!/usr/bin/env bash
printf '%s\\n' "$@" > "${CS_STATE}.$(basename "$0")"
cat > "${CS_STATE}.$(basename "$0").stdin"
"""


class Session:
    """A repository with an origin, a stub gh, rsync, and ssh, and the codespace state file."""

    def __init__(self, root: Path) -> None:
        self.root = root
        remote = root / 'origin.git'
        git(root, 'init', '--quiet', '--bare', '--initial-branch=main', str(remote))
        self.repo = root / 'fixture-repo'
        git(root, 'clone', '--quiet', str(remote), str(self.repo))
        git(self.repo, 'checkout', '--quiet', '-b', 'Feature/Thing_1')
        (self.repo / 'tracked.txt').write_text('tracked\n')
        (self.repo / 'gone.txt').write_text('to delete\n')
        (self.repo / '.gitignore').write_text('ignored.log\n.tmp/\n')
        git(self.repo, 'add', '.')
        git(self.repo, 'commit', '--quiet', '-m', 'Fixture')
        self.bin = root / 'bin'
        self.bin.mkdir()
        gh = self.bin / 'gh'
        gh.write_text(f'#!{sys.executable}\n{GH_STUB}')
        gh.chmod(0o755)
        for tool in ('rsync', 'ssh'):
            (self.bin / tool).write_text(RECORDER)
            (self.bin / tool).chmod(0o755)
        self.state = root / 'cs-state.json'
        self.set_state()

    def set_state(self, codespaces: list[dict[str, str]] | None = None, **extra: Any) -> None:
        """Replace the stub's codespaces and behaviour flags."""
        self.state.write_text(json.dumps({'codespaces': codespaces or [], **extra}))

    def record(self, name: str) -> None:
        """Record `name` as the session's codespace."""
        (self.repo / '.tmp').mkdir(exist_ok=True)
        (self.repo / '.tmp' / 'codespace-name').write_text(name)

    def gh_calls(self) -> list[list[str]]:
        """Return every gh invocation, in order."""
        log = Path(f'{self.state}.log')
        return [json.loads(line) for line in log.read_text().splitlines()] if log.exists() else []

    def run(self, script: str, *arguments: str) -> subprocess.CompletedProcess[str]:
        """Run one of the skill's scripts in the repository."""
        environment = {
            **os.environ,
            **FIXTURE_ENV,
            'PATH': f'{self.bin}{os.pathsep}{os.environ["PATH"]}',
            'CS_STATE': str(self.state),
        }
        return subprocess.run(
            [str(PLUGIN_ROOT / SKILL / f'{script}.{EXT}'), *arguments],
            cwd=self.repo,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )


PLUGIN_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def session(plugin_tmp_path: Path) -> Session:
    """Create the fixture session."""
    return Session(plugin_tmp_path)


def keys(completed: subprocess.CompletedProcess[str]) -> dict[str, str]:
    """Return the KEY=value lines of a run."""
    return dict(line.split('=', 1) for line in completed.stdout.splitlines() if '=' in line)


DISPLAY = 'agent-feature-thing-1'


def test_ensure_reuses_the_branch_codespace(session: Session) -> None:
    """A codespace named for the branch is reused and recorded."""
    session.set_state([{'name': 'fixture-cs', 'displayName': DISPLAY, 'state': 'Shutdown'}])

    completed = session.run('codespace-ensure')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert keys(completed) == {
        'ACTION': 'reuse', 'CODESPACE': 'fixture-cs', 'STATE': 'Shutdown', 'RESULT': 'SUCCESS'
    }  # fmt: skip
    assert (session.repo / '.tmp' / 'codespace-name').read_text() == 'fixture-cs'


def test_ensure_notes_an_unexpected_state(session: Session) -> None:
    """A reused codespace in another state is reported but still reused."""
    session.set_state([{'name': 'fixture-cs', 'displayName': DISPLAY, 'state': 'Rebuilding'}])

    completed = session.run('codespace-ensure', '--dry-run')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert 'has unexpected state Rebuilding' in completed.stderr
    assert not (session.repo / '.tmp' / 'codespace-name').exists()


def test_ensure_dry_run_reports_the_create(session: Session) -> None:
    """--dry-run with no codespace prints the create parameters and creates nothing."""
    completed = session.run(
        'codespace-ensure', '--dry-run', '--machine', 'premiumLinux', '--branch', 'other'
    )

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert completed.stdout.splitlines()[:-1] == [
        'ACTION=create',
        'DISPLAY_NAME=agent-other',
        'MACHINE=premiumLinux',
        'IDLE_TIMEOUT=30m',
        'RETENTION_PERIOD=24h',
        'BRANCH=other',
    ]
    assert not any(call[:2] == ['codespace', 'create'] for call in session.gh_calls())


def test_ensure_creates_and_waits_for_available(session: Session) -> None:
    """A missing codespace is created with the documented flags and polled to Available."""
    completed = session.run('codespace-ensure', '--poll-interval', '1')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert keys(completed) == {
        'ACTION': 'create', 'CODESPACE': 'fixture-cs-new', 'STATE': 'Available',
        'RESULT': 'SUCCESS',
    }  # fmt: skip
    [create] = [call for call in session.gh_calls() if call[:2] == ['codespace', 'create']]
    assert create[2:] == [
        '-R', 'octo/fixture-repo', '-b', 'Feature/Thing_1',
        '--devcontainer-path', '.devcontainer/devcontainer.json',
        '-m', 'standardLinux32gb', '--idle-timeout', '30m', '--retention-period', '24h',
        '--default-permissions', '--display-name', DISPLAY,
    ]  # fmt: skip
    assert (session.repo / '.tmp' / 'codespace-name').read_text() == 'fixture-cs-new'


def test_ensure_create_failure(session: Session) -> None:
    """A failing gh codespace create reports CREATE_FAILED with gh's message."""
    session.set_state(create_error='quota exceeded')

    completed = session.run('codespace-ensure')

    assert outcome(completed) == (4, 'RESULT=CREATE_FAILED')
    assert 'ERROR: gh codespace create failed: quota exceeded' in completed.stderr


@pytest.mark.parametrize(
    ('error', 'expected'),
    [
        ('HTTP 403: missing scope codespace', (3, 'RESULT=CODESPACE_SCOPE_MISSING')),
        ('not logged in', (2, 'RESULT=PREFLIGHT_ERROR')),
    ],
)
def test_auth_failures(session: Session, error: str, expected: tuple[int, str]) -> None:
    """A scope error is CODESPACE_SCOPE_MISSING; any other auth failure is a preflight error."""
    session.set_state(list_error=error)

    completed = session.run('codespace-ensure')

    assert outcome(completed) == expected


@pytest.mark.parametrize(
    ('arguments', 'message'),
    [
        (['--poll-interval', '0'], '--poll-interval expects an integer >= 1, got: 0'),
        (['--poll-timeout', '08x'], '--poll-timeout expects an integer >= 0, got: 08x'),
        (['--bogus'], 'Unknown argument: --bogus'),
    ],
)
def test_ensure_usage_errors(session: Session, arguments: list[str], message: str) -> None:
    """Bad option values are preflight errors before gh is called."""
    completed = session.run('codespace-ensure', *arguments)

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert f'ERROR: {message}' in completed.stderr


def test_exec_runs_the_quoted_command_in_the_workspace(session: Session) -> None:
    """Arguments are quoted into one remote command run from the workspace directory."""
    session.record('fixture-cs')

    completed = session.run('codespace-exec', 'echo', 'a b', "it's", '$HOME', '')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert completed.stdout.splitlines()[-2] == 'REMOTE_EXIT_CODE=0'
    [ssh] = [call for call in session.gh_calls() if call[:2] == ['codespace', 'ssh']]
    assert ssh[2:4] == ['-c', 'fixture-cs']
    remote = ssh[-1]
    assert remote.startswith('cd /workspaces/fixture-repo && echo ')
    assert subprocess.run(
        ['bash', '-c', f'printf "%s|" {remote.split(" && ", 1)[1].removeprefix("echo ")}'],
        capture_output=True, text=True, check=True, env={'HOME': '/home/x'},
    ).stdout == "a b|it's|$HOME||"  # fmt: skip


def test_exec_reports_a_failing_remote_command(session: Session) -> None:
    """A non-zero ssh status is REMOTE_COMMAND_FAILED with the status as a key."""
    session.record('fixture-cs')
    session.set_state(ssh_replies={'run': {'stdout': 'boom', 'exit': 3}})

    completed = session.run('codespace-exec', 'false')

    assert outcome(completed) == (4, 'RESULT=REMOTE_COMMAND_FAILED')
    assert 'REMOTE_EXIT_CODE=3' in completed.stdout.splitlines()


def test_exec_without_a_recorded_name(session: Session) -> None:
    """No recorded codespace is a preflight error naming the ensure script."""
    completed = session.run('codespace-exec', 'true')

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert 'ERROR: No codespace name recorded. Run codespace-ensure.' in completed.stderr


def test_sync_clean_tree_pushes_and_resets_the_codespace(session: Session) -> None:
    """A clean tree is pushed with upstream, then fetched and reset on the codespace."""
    session.record('fixture-cs')

    completed = session.run('codespace-sync')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert keys(completed)['ACTION'] == 'git-push'
    assert keys(completed)['BRANCH'] == 'Feature/Thing_1'
    assert git(session.repo, 'rev-parse', '--abbrev-ref', '@{u}') == 'origin/Feature/Thing_1'
    remote = [call[-1] for call in session.gh_calls() if call[:2] == ['codespace', 'ssh']][-1]
    assert remote == (
        'cd /workspaces/fixture-repo && git fetch origin && git checkout Feature/Thing_1'
        ' && git reset --hard origin/Feature/Thing_1'
    )


def test_sync_dirty_tree_rsyncs_and_deletes_removed_paths(session: Session) -> None:
    """A dirty tree is rsynced without ignored files, then locally deleted paths are removed."""
    session.record('fixture-cs')
    (session.repo / 'tracked.txt').write_text('edited\n')
    (session.repo / 'ignored.log').write_text('ignored\n')
    (session.repo / 'gone.txt').unlink()

    completed = session.run('codespace-sync')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert completed.stdout.splitlines()[:-1] == [
        'ACTION=rsync', 'HOST=cs.fixture-cs.main', 'CODESPACE=fixture-cs'
    ]  # fmt: skip
    rsync = Path(f'{session.state}.rsync').read_text().splitlines()
    assert rsync[-2:] == [f'{session.repo}/', 'cs.fixture-cs.main:/workspaces/fixture-repo/']
    exclude = (session.repo / '.tmp' / 'codespace-sync-exclude').read_text().splitlines()
    assert '/ignored.log' in exclude
    assert Path(f'{session.state}.ssh.stdin').read_text() == 'gone.txt\0'


@pytest.mark.parametrize(
    ('marker', 'expected'),
    [
        ('CODESPACE_REMOTE_CHECKOUT_DIRTY', (4, 'RESULT=REMOTE_CHECKOUT_DIRTY')),
        ('CODESPACE_REMOTE_COMMITS_ABSENT_FROM_ORIGIN', (5, 'RESULT=REMOTE_COMMITS_ABSENT')),
        ('Connection refused', (6, 'RESULT=REMOTE_SSH_FAILED')),
    ],
)
def test_sync_refuses_an_unsafe_codespace(
    session: Session, marker: str, expected: tuple[int, str]
) -> None:
    """The remote preflight's marker decides the refusal; anything else is an SSH failure."""
    session.record('fixture-cs')
    session.set_state(ssh_replies={'preflight': {'stdout': marker, 'exit': 1}})

    completed = session.run('codespace-sync')

    assert outcome(completed) == expected


def test_teardown_stops_and_waits_for_shutdown(session: Session) -> None:
    """The default teardown stops the codespace and keeps its recorded name."""
    session.record('fixture-cs')
    session.set_state([{'name': 'fixture-cs', 'displayName': DISPLAY, 'state': 'Available'}])

    completed = session.run('codespace-teardown', '--poll-interval', '1')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert completed.stdout.splitlines()[:-1] == [
        'ACTION=stop', 'CODESPACE=fixture-cs', 'STATE=Shutdown'
    ]  # fmt: skip
    assert (session.repo / '.tmp' / 'codespace-name').exists()


def test_teardown_stop_wait_times_out(session: Session) -> None:
    """A codespace that never reaches Shutdown times out after the stop was accepted."""
    session.record('fixture-cs')
    session.set_state(
        [{'name': 'fixture-cs', 'displayName': DISPLAY, 'state': 'Available'}],
        stop_settles='ShuttingDown',
    )

    completed = session.run('codespace-teardown', '--poll-timeout', '0')

    assert outcome(completed) == (5, 'RESULT=STATE_WAIT_TIMEOUT')
    assert '(last state: ShuttingDown)' in completed.stderr


def test_teardown_stop_failure(session: Session) -> None:
    """A failing gh codespace stop is TEARDOWN_FAILED."""
    session.record('fixture-cs')
    session.set_state(
        [{'name': 'fixture-cs', 'displayName': DISPLAY, 'state': 'Available'}],
        stop_error='HTTP 500',
    )

    completed = session.run('codespace-teardown')

    assert outcome(completed) == (4, 'RESULT=TEARDOWN_FAILED')
    assert 'ERROR: gh codespace stop failed: HTTP 500' in completed.stderr


def test_teardown_delete_forgets_the_codespace(session: Session) -> None:
    """--delete removes the codespace, then the recorded name and SSH config."""
    session.record('fixture-cs')
    (session.repo / '.tmp' / 'codespace-ssh-config').write_text('Host x\n')
    session.set_state([{'name': 'fixture-cs', 'displayName': DISPLAY, 'state': 'Available'}])

    completed = session.run('codespace-teardown', '--delete', '--poll-interval', '1')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert completed.stdout.splitlines()[:-1] == ['ACTION=delete', 'CODESPACE=fixture-cs']
    assert not (session.repo / '.tmp' / 'codespace-name').exists()
    assert not (session.repo / '.tmp' / 'codespace-ssh-config').exists()
    [delete] = [call for call in session.gh_calls() if call[:2] == ['codespace', 'delete']]
    assert delete[2:] == ['-c', 'fixture-cs', '--force']


@pytest.mark.parametrize('script', ['codespace-ensure', 'codespace-sync', 'codespace-teardown'])
def test_help_names_the_skill_root(session: Session, script: str) -> None:
    """Every script's help starts with its description and the skill root."""
    completed = session.run(script, '--help')

    assert outcome(completed) == (0, 'RESULT=SUCCESS')
    assert f'Skill root: {PLUGIN_ROOT / SKILL.removesuffix("/agent-code")}' in completed.stdout


def test_exec_without_arguments_prints_usage(session: Session) -> None:
    """codespace-exec with no command prints usage on stderr."""
    completed = session.run('codespace-exec')

    assert outcome(completed) == (2, 'RESULT=PREFLIGHT_ERROR')
    assert 'Usage:' in completed.stderr


def test_tools_are_present() -> None:
    """The fixture needs bash to evaluate the quoted remote command."""
    assert shutil.which('bash') is not None


def test_codespace_exec_separates_metadata_from_unterminated_remote_stdout(
    plugin_root: Path,
    plugin_tmp_path: Path,
) -> None:
    """Remote output without a newline must not absorb the exit-code key."""
    # Arrange
    script = plugin_root / 'skills/remote-codespace-session/agent-code/codespace-exec.py'
    mock_bin = plugin_tmp_path / 'bin'
    mock_bin.mkdir()
    mock_repository = plugin_tmp_path / 'repository'
    (mock_repository / '.tmp').mkdir(parents=True)
    (mock_repository / '.tmp' / 'codespace-name').write_text('fixture-codespace\n')

    mock_git = mock_bin / 'git'
    mock_git.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf '%s\n' "${MOCK_REPOSITORY_ROOT}"
"""
    )
    mock_git.chmod(0o755)

    mock_gh = mock_bin / 'gh'
    mock_gh.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case "${1:-} ${2:-}" in
  'codespace list')
    ;;
  'repo view')
    printf '%s\n' 'fixture-repository'
    ;;
  'codespace ssh')
    printf 'foo'
    ;;
  *)
    exit 64
    ;;
esac
"""
    )
    mock_gh.chmod(0o755)

    environment = os.environ.copy()
    environment['MOCK_REPOSITORY_ROOT'] = str(mock_repository)
    environment['PATH'] = f'{mock_bin}:{environment["PATH"]}'

    # Act
    completed = subprocess.run(
        [str(script), 'printf', 'foo'],
        cwd=plugin_root,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    # Assert
    assert completed.returncode == 0
    assert completed.stdout == 'foo\nREMOTE_EXIT_CODE=0\nRESULT=SUCCESS\n'
