"""
Repair codebase-memory-mcp's SessionStart block in Codex's config.toml before cbm installs.

A complete block keeps only cbm's own tables, foreign ones moved below it. An orphaned block, a
marker without its partner, loses cbm's tables when each is exactly cbm's canonical content.
Why and when: see bugs/cbm-codex-hooks-block-foreign-tables and spec/cbm-startup-integration.
"""

import os
from pathlib import Path
import re
import sys
import tempfile

OPEN_MARKER = '# >>> codebase-memory-mcp SessionStart >>>'
CLOSE_MARKER = '# <<< codebase-memory-mcp SessionStart <<<'
OWNED_HEADER = re.compile(r'\[\[hooks\.(SessionStart|SubagentStart)(\.hooks)?\]\]')
HEADER = re.compile(r'\[')
MATCHERS = {'SessionStart': 'startup|resume|clear|compact', 'SubagentStart': '*'}


class ForeignHook(Exception):
    """An orphaned block claims a hook table that is not cbm's canonical content."""


def codex_home() -> Path:
    """Return the Codex home directory, honoring ``CODEX_HOME``."""
    return Path(os.environ.get('CODEX_HOME') or Path.home() / '.codex')


def installed_binary(install_dir: str | None = None) -> str:
    """Return the path cbm's hooks invoke: the binary its installer staged."""
    install_dir = (
        install_dir or os.environ.get('CBM_INSTALL_DIR') or str(Path.home() / '.local/bin')
    )
    return f'{install_dir}/codebase-memory-mcp'


def canonical_tables(binary: str) -> dict[str, list[str]]:
    """Return the key lines cbm 0.12.1 writes under each hook table header it owns."""
    hook = [
        'type = "command"',
        f'command = "\'{binary}\' hook-augment"',
        f'command_windows = "& \'{binary}\' hook-augment"',
        'timeout = 5',
    ]
    tables = {}
    for event, matcher in MATCHERS.items():
        tables[f'[[hooks.{event}]]'] = [f'matcher = "{matcher}"']
        tables[f'[[hooks.{event}.hooks]]'] = hook
    return tables


def foreign_start(body: list[str]) -> int:
    """Return the index in ``body`` where the first foreign table and its leading comments begin."""
    for index, line in enumerate(body):
        stripped = line.strip()
        if HEADER.match(stripped) and not OWNED_HEADER.fullmatch(stripped):
            while index > 0 and body[index - 1].lstrip().startswith('#'):
                index -= 1
            return index
    return len(body)


def strip_blank_edges(lines: list[str]) -> list[str]:
    """Return ``lines`` without leading or trailing blank lines."""
    while lines and not lines[0].strip():
        lines = lines[1:]
    while lines and not lines[-1].strip():
        lines = lines[:-1]
    return lines


def newline_of(lines: list[str]) -> str:
    """Return the file's line ending, so lines this repair adds match it."""
    return '\r\n' if lines and lines[0].endswith('\r\n') else '\n'


def move_foreign(lines: list[str], open_index: int, close_index: int) -> str:
    """Return the text with foreign tables moved from inside the block to just below it."""
    newline = newline_of(lines)
    body = lines[open_index + 1 : close_index]
    split = foreign_start(body)
    owned = strip_blank_edges(body[:split])
    foreign = strip_blank_edges(body[split:])
    after = lines[close_index + 1 :]

    close = lines[close_index]
    moved = [newline, *foreign] if foreign else []
    if moved:
        close = close.rstrip('\r\n') + newline
        if after and after[0].strip():
            moved.append(newline)
    return ''.join(lines[: open_index + 1] + owned + [close] + moved + after)


def is_comment(line: str) -> bool:
    """Return whether ``line`` is a TOML comment, which the repair keeps."""
    return line.lstrip().startswith('#')


def is_key(line: str) -> bool:
    """Return whether ``line`` holds TOML content rather than a blank or a comment."""
    return bool(line.strip()) and not is_comment(line)


def block_headers(bare: list[str], marker: int) -> list[int]:
    """Return the header lines of the owned tables that belong to the lone marker's block."""
    # The contiguous run of owned tables after an opening marker, or the last run before a
    # closing one, since Codex inserts its tables above a trailing marker.
    headers = [index for index, line in enumerate(bare) if HEADER.match(line.strip())]
    owned = {index for index in headers if OWNED_HEADER.fullmatch(bare[index].strip())}
    if bare[marker] == OPEN_MARKER:
        side = [index for index in headers if index > marker]
    else:
        side = [index for index in reversed(headers) if index < marker]
        while side and side[0] not in owned:
            side = side[1:]
    run = []
    for index in side:
        if index not in owned:
            break
        run.append(index)
    return sorted(run)


def remove_orphan(lines: list[str], bare: list[str], marker: int, binary: str) -> str:
    """Return the text without the lone marker and cbm's tables, refusing any it does not own."""
    canonical = canonical_tables(binary)
    drop = {marker}
    for start in block_headers(bare, marker):
        header = bare[start].strip()
        # A table runs to the next header: a comment does not end it, and its keys still count.
        end = last = start + 1
        while end < len(bare) and not bare[end].lstrip().startswith('['):
            if is_key(bare[end]):
                last = end + 1
            end += 1
        body = [line.rstrip() for line in bare[start + 1 : last] if is_key(line)]
        if body != canonical[header]:
            raise ForeignHook(f'{header} at line {start + 1}')
        while last < end and not bare[last].strip():
            last += 1
        drop.update(index for index in range(start, last) if not is_comment(bare[index]))
    return ''.join(line for index, line in enumerate(lines) if index not in drop)


def repair(current: str, binary: str | None = None) -> str:
    """Return ``current`` with the hooks block holding only codebase-memory-mcp's own tables."""
    lines = current.splitlines(keepends=True)
    bare = [line.rstrip('\r\n') for line in lines]
    opens = [index for index, line in enumerate(bare) if line == OPEN_MARKER]
    closes = [index for index, line in enumerate(bare) if line == CLOSE_MARKER]
    if opens:
        later = [index for index in closes if index > opens[0]]
        if later:
            return move_foreign(lines, opens[0], later[0])
        return remove_orphan(lines, bare, opens[0], binary or installed_binary())
    if closes:
        return remove_orphan(lines, bare, closes[0], binary or installed_binary())
    return current


def write_atomically(path: Path, content: str) -> None:
    """Replace ``path`` with ``content`` through a temporary file beside it, keeping its mode."""
    fd, temp_name = tempfile.mkstemp(dir=path.parent, prefix=f'.{path.name}.')
    temp_path = Path(temp_name)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as temp_file:
            temp_file.write(content)
        temp_path.chmod(path.stat().st_mode & 0o777)
        temp_path.replace(path)
    except BaseException:
        temp_path.unlink(missing_ok=True)
        raise


def repair_config(home: Path | None = None, install_dir: str | None = None) -> int:
    """Repair the hooks block in the Codex home's config, if it needs it."""
    config = (home or codex_home()) / 'config.toml'
    if not config.is_file():
        return 0
    with config.open(encoding='utf-8', newline='') as handle:
        current = handle.read()
    try:
        repaired = repair(current, installed_binary(install_dir))
    except ForeignHook as foreign:
        print(
            f'{config}: the orphaned codebase-memory-mcp hooks block claims {foreign}, which is '
            "not cbm's own hook; left the file unchanged. Remove or restore that table by hand.",
            file=sys.stderr,
        )
        return 1
    if repaired != current:
        write_atomically(config, repaired)
        print(f'repaired the codebase-memory-mcp hooks block in {config}')
    return 0
