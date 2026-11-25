"""The container environment the root bootstrap hands to the image's systemd units."""

import os
from pathlib import Path
import subprocess

from agentdev_runtime import bootstrap


def test_the_container_environment_is_read_from_a_nul_separated_environ(tmp_path: Path) -> None:
    environ = tmp_path / 'environ'
    environ.write_bytes(b'A=1\0B=two=parts\0EMPTY=\0junk\0')

    assert bootstrap.container_environment(environ) == {'A': '1', 'B': 'two=parts', 'EMPTY': ''}


def test_per_process_and_malformed_names_are_not_forwarded(tmp_path: Path) -> None:
    target = tmp_path / 'run/container.env'
    environ = {'HOME': '/root', 'TERM': 'xterm', 'KEEP_ME': 'x', 'bad-name': 'y'}

    bootstrap.write_environment_file(environ, target, os.getgid())

    assert target.read_text() == 'KEEP_ME="x"\n'
    assert oct(target.stat().st_mode & 0o777) == '0o640'


def test_quoted_values_read_back_unchanged(tmp_path: Path) -> None:
    """Systemd reads a double-quoted value with the shell's escapes; shlex follows the same rules."""
    value = 'a "quoted" $HOME `tick` back\\slash\nsecond line'
    target = tmp_path / 'container.env'

    bootstrap.write_environment_file({'TRICKY': value}, target, os.getgid())

    shown = subprocess.run(
        ['sh', '-c', '. "$1" && printf %s "$TRICKY"', 'sh', str(target)],
        capture_output=True,
        text=True,
        check=True,
    )
    assert shown.stdout == value
