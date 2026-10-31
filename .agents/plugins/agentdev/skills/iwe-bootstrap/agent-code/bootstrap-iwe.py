#!/usr/bin/env python3

"""
Install the blank IWE workspace this skill ships into a repository root.

Runs from any consuming repository that installs this plugin, so it imports
nothing beyond the standard library.
"""

from __future__ import annotations

import locale
import os
from pathlib import Path
import re
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'bin'))

import result_codes as rc  # noqa: E402  (path set above so the plugin's bin/ resolves)
from skill_common import print_error, run_to_stderr, run_tool, Stop  # noqa: E402

MISSING_DEPENDENCY = 3
ALREADY_INITIALIZED = 4
RECONCILIATION_REQUIRED = 5
VALIDATION_FAILED = 6
PREFLIGHT_ERROR = 2

ASSETS_DIR = Path(__file__).resolve().parents[1] / 'assets'
TRANSACTION_NAME = '.iwe-bootstrap.txn'
OWNER_MARK = 'iwe-bootstrap transaction'
WORKSPACE_PATH = 'docs/knowledge'
# The two trees bootstrap owns; everything else in the repository is left alone.
MANAGED_DIRS = ('.iwe', 'docs/knowledge')
NEXT_SKILLS = 'NEXT_SKILLS=iwe-setup iwe-map'

USAGE = """\
Install the blank IWE workspace this skill ships into a repository root.

Usage:
  bootstrap-iwe.py [--root <dir>]

Options:
  --root <dir>  Repository root to initialize. Default: the git top level of
                the current directory
  -h, --help    Show this help text.

Bootstrap writes only .iwe/ and docs/knowledge/, and only when both are absent.
It stages the scaffold in <root>/.iwe-bootstrap.txn/, validates it with iwe, and
then moves it into place; an interrupted run leaves that directory behind, and
the next run discards or completes it.

Output (key=value lines):
  RESULT, ROOT
  After recovering an interrupted run also: RECOVERED_TRANSACTION
    (discarded | completed)
  On RECONCILIATION_REQUIRED also: one CONFLICT=<reason>:<path> per conflict,
    reason one of missing, not-a-directory, incompatible-config, invalid,
    foreign-transaction, collision
  On SUCCESS also: NEXT_SKILLS (the onboarding skills to run, in order)

Results (RESULT / exit code):
  SUCCESS                  0  The scaffold was installed and validated
  MISSING_DEPENDENCY       3  The iwe CLI is not on PATH; nothing was written
  ALREADY_INITIALIZED      4  A complete, valid workspace is present; nothing
                              was written
  RECONCILIATION_REQUIRED  5  A managed path exists but is not the complete
                              scaffold; nothing was written
  VALIDATION_FAILED        6  The staged scaffold failed iwe validation;
                              nothing was written
  PREFLIGHT_ERROR          2  Bad usage, a missing root, or a missing scaffold
  SCRIPT_FAILURE           1  Unhandled error
  SIGNAL_HUP             129  Interrupted by HUP
  SIGNAL_INT             130  Interrupted by INT
  SIGNAL_TERM            143  Interrupted by TERM
"""


def path_exists(path: Path) -> bool:
    """Return whether anything, a dangling symlink included, is at `path`."""
    return path.exists() or path.is_symlink()


def is_real_directory(path: Path) -> bool:
    """Return whether `path` is a directory and not a symlink to one."""
    return path.is_dir() and not path.is_symlink()


def first_line(path: Path) -> str:
    """Return the first line of a file, without its newline."""
    with path.open() as text:
        return text.readline().rstrip('\n')


def remove(path: Path) -> None:
    """Remove a file, symlink, or directory tree."""
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


def configured_workspace_path(config: Path) -> str:
    """Return [workspace].path from an IWE config, as the quoted value it holds."""
    in_workspace = False
    for line in config.read_text().splitlines():
        if line.startswith('['):
            in_workspace = line == '[workspace]'
            continue
        if in_workspace and re.match(r'path[ \t]*=', line):
            value = re.sub(r'^path[ \t]*=[ \t]*"', '', line, count=1)
            return re.sub(r'".*$', '', value, count=1)
    return ''


def required_files() -> list[str]:
    """
    Return the structural files a complete workspace keeps.

    Documents under data/ subdirectories are project content onboarding deletes or rewrites.
    """
    files = []
    for directory, _, names in os.walk(ASSETS_DIR):
        for name in names:
            path = Path(directory) / name
            if path.is_file() and not path.is_symlink():
                files.append(path.relative_to(ASSETS_DIR).as_posix())
    excluded = re.compile(rf'^{re.escape(WORKSPACE_PATH)}/data/[^/]*/')
    # Ordered as sort(1) orders them, by the runtime locale's collation.
    try:
        locale.setlocale(locale.LC_COLLATE, '')
    except locale.Error:
        locale.setlocale(locale.LC_COLLATE, 'C')
    return sorted((file for file in files if not excluded.match(file)), key=locale.strxfrm)


class Bootstrap:
    """One install, recovery, or reconciliation check of a repository root."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.transaction = root / TRANSACTION_NAME
        self.conflicts: list[str] = []

    def add_conflict(self, reason: str, path: str) -> None:
        """Record one path bootstrap does not own."""
        self.conflicts.append(f'{reason}:{path}')

    def report_conflicts(self) -> Stop:
        """Print every CONFLICT line and return the RECONCILIATION_REQUIRED stop."""
        for conflict in self.conflicts:
            print(f'CONFLICT={conflict}')
        print_error('Bootstrap found existing state it does not own; nothing was changed.')
        print_error('Reconcile each CONFLICT path with the user before installing the scaffold.')
        return Stop(RECONCILIATION_REQUIRED)

    def write_phase(self, phase: str) -> None:
        """Record the transaction's phase through an atomic rename."""
        pending = self.transaction / 'OWNER.next'
        pending.write_text(f'{OWNER_MARK}\nphase={phase}\n')
        pending.replace(self.transaction / 'OWNER')

    def discard_transaction(self) -> None:
        """Remove the transaction, OWNER last, so owned files never lose their mark."""
        for entry in self.transaction.iterdir():
            if entry.name != 'OWNER':
                remove(entry)
        shutil.rmtree(self.transaction)

    def holds_only_first_owner_write(self) -> bool:
        """Return whether only the first OWNER write, which is not atomic with mkdir, happened."""
        entries = sorted(entry.name for entry in self.transaction.iterdir())
        if not entries:
            return True
        pending = self.transaction / 'OWNER.next'
        if entries != ['OWNER.next'] or not pending.is_file() or pending.is_symlink():
            return False
        return pending.stat().st_size == 0 or first_line(pending) == OWNER_MARK

    def transaction_phase(self) -> str:
        """Return the recorded phase, staging for a bare first write, or foreign."""
        owner = self.transaction / 'OWNER'
        if not is_real_directory(self.transaction):
            return 'foreign'
        if self.holds_only_first_owner_write():
            return 'staging'
        if not owner.is_file() or first_line(owner) != OWNER_MARK:
            return 'foreign'
        phases = [
            line.removeprefix('phase=')
            for line in owner.read_text().splitlines()
            if line.startswith('phase=')
        ]
        return '\n'.join(phases)

    def check_staged_destinations(self) -> None:
        """Record each staged tree whose destination exists, since moving requires it absent."""
        for item in MANAGED_DIRS:
            if path_exists(self.transaction / 'stage' / item) and path_exists(self.root / item):
                self.add_conflict('collision', item)
        docs = self.root / 'docs'
        if path_exists(docs) and not is_real_directory(docs):
            self.add_conflict('not-a-directory', 'docs')

    def move_staged(self) -> None:
        """Move the staged trees into the root, then drop the transaction."""
        for item in MANAGED_DIRS:
            staged = self.transaction / 'stage' / item
            if path_exists(staged):
                (self.root / item).parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(staged), str(self.root / item))
        self.discard_transaction()

    def recover(self) -> str:
        """Discard a staging transaction or complete a committing one; '' when there is none."""
        if not path_exists(self.transaction):
            return ''
        phase = self.transaction_phase()
        if phase == 'staging':
            self.discard_transaction()
            recovered = 'discarded'
        elif phase == 'committing':
            self.check_staged_destinations()
            if self.conflicts:
                raise self.report_conflicts()
            self.move_staged()
            recovered = 'completed'
        else:
            self.add_conflict('foreign-transaction', TRANSACTION_NAME)
            raise self.report_conflicts()
        print(f'RECOVERED_TRANSACTION={recovered}')
        return recovered

    def check_existing(self, recovered: str) -> None:
        """Stop when any managed path exists: done, already initialized, or in conflict."""
        for item in ('.iwe', 'docs', 'docs/knowledge'):
            path = self.root / item
            if path_exists(path) and not is_real_directory(path):
                self.add_conflict('not-a-directory', item)
                break
        present = any(path_exists(self.root / item) for item in MANAGED_DIRS)
        if self.conflicts or not present:
            return
        for item in MANAGED_DIRS:
            if not path_exists(self.root / item):
                self.add_conflict('missing', item)
        for file in required_files():
            top = MANAGED_DIRS[1] if file.startswith(f'{MANAGED_DIRS[1]}/') else MANAGED_DIRS[0]
            if not path_exists(self.root / top):
                continue
            target = self.root / file
            if target.is_symlink() or not target.is_file():
                self.add_conflict('missing', file)
        config = self.root / '.iwe' / 'config.toml'
        if (
            config.is_file()
            and not config.is_symlink()
            and configured_workspace_path(config) != WORKSPACE_PATH
        ):
            self.add_conflict('incompatible-config', '.iwe/config.toml')
        if not self.conflicts and run_to_stderr('iwe', 'schema', 'validate', cwd=self.root):
            self.add_conflict('invalid', WORKSPACE_PATH)
        if self.conflicts:
            raise self.report_conflicts()
        if recovered == 'completed':
            print(NEXT_SKILLS)
            raise Stop(0)
        print(f'The workspace at {self.root} is already initialized.', file=sys.stderr)
        raise Stop(ALREADY_INITIALIZED)

    def validate_stage(self) -> bool:
        """Return whether the staged scaffold validates and is already in normalize form."""
        stage = self.transaction / 'stage'
        if run_to_stderr('iwe', 'schema', 'validate', cwd=stage):
            print_error("The staged scaffold fails 'iwe schema validate'.")
            return False
        check = self.transaction / 'check'
        shutil.copytree(stage, check, symlinks=True)
        if run_to_stderr('iwe', 'normalize', cwd=check):
            print_error("'iwe normalize' failed on the staged scaffold.")
            return False
        if run_to_stderr('diff', '-r', str(stage), str(check)):
            print_error("The staged scaffold is not in 'iwe normalize' form.")
            return False
        shutil.rmtree(check)
        return True

    def install(self) -> int:
        """Stage, validate, and move the scaffold into place."""
        print(f'Staging the scaffold in {self.transaction}...', file=sys.stderr)
        self.transaction.mkdir()
        self.write_phase('staging')
        stage = self.transaction / 'stage'
        (stage / 'docs').mkdir(parents=True)
        shutil.copytree(ASSETS_DIR / '.iwe', stage / '.iwe', symlinks=True)
        shutil.copytree(ASSETS_DIR / WORKSPACE_PATH, stage / WORKSPACE_PATH, symlinks=True)
        if not self.validate_stage():
            self.discard_transaction()
            return VALIDATION_FAILED
        self.write_phase('committing')
        self.move_staged()
        print(f'Installed .iwe/ and docs/knowledge/ in {self.root}.', file=sys.stderr)
        print(NEXT_SKILLS)
        return 0


def parse_arguments(arguments: list[str]) -> str:
    """Return --root, stopping at a usage error or help."""
    root = ''
    remaining = list(arguments)
    while remaining:
        argument = remaining.pop(0)
        if argument == '--root':
            if not remaining:
                print_error('Missing value for --root')
                print(USAGE, end='', file=sys.stderr)
                raise Stop(PREFLIGHT_ERROR)
            root = remaining.pop(0)
        elif argument in ('-h', '--help'):
            print(USAGE, end='')
            raise Stop(0)
        else:
            print_error(f'Unknown argument: {argument}')
            print(USAGE, end='', file=sys.stderr)
            raise Stop(PREFLIGHT_ERROR)
    return root


def run(arguments: list[str]) -> int:
    """Install the scaffold, or report why nothing was written."""
    root = parse_arguments(arguments)
    if root:
        if not Path(root).is_dir():
            print_error(f"Repository root '{root}' is not a directory.")
            return PREFLIGHT_ERROR
    else:
        toplevel = run_tool('git', 'rev-parse', '--show-toplevel')
        if toplevel.returncode != 0:
            print_error('The current directory is not inside a git repository; pass --root <dir>.')
            return PREFLIGHT_ERROR
        root = toplevel.stdout.strip()
    resolved = Path(root).resolve()
    print(f'ROOT={resolved}')

    if (
        not (ASSETS_DIR / '.iwe' / 'config.toml').is_file()
        or not (ASSETS_DIR / WORKSPACE_PATH / 'data').is_dir()
    ):
        print_error(
            f'The packaged scaffold is missing from {ASSETS_DIR}; reinstall the agentdev catalog.'
        )
        return PREFLIGHT_ERROR
    if shutil.which('iwe') is None:
        print_error(
            'The iwe CLI is not on PATH; install it (https://iwe.md/quick-start/) and rerun.'
        )
        return MISSING_DEPENDENCY

    bootstrap = Bootstrap(resolved)
    recovered = bootstrap.recover()
    bootstrap.check_existing(recovered)
    if bootstrap.conflicts:
        raise bootstrap.report_conflicts()
    return bootstrap.install()


def main() -> int:
    """Run the script, turning a declared stop into its result code."""
    try:
        return run(sys.argv[1:])
    except Stop as stop:
        return stop.code


if __name__ == '__main__':
    rc.RESULT_CODES.update(
        {
            MISSING_DEPENDENCY: 'MISSING_DEPENDENCY',
            ALREADY_INITIALIZED: 'ALREADY_INITIALIZED',
            RECONCILIATION_REQUIRED: 'RECONCILIATION_REQUIRED',
            VALIDATION_FAILED: 'VALIDATION_FAILED',
        }
    )
    rc.install()
    rc.run(main)
