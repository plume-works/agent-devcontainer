#!/usr/bin/env python3
"""
Recompute the per-architecture SHA-256 of pinned downloads in Ansible role defaults.

Each pin's download URL is rendered from the consuming role's own Jinja templates, so the
script fetches exactly what the image build fetches. Every pin in a given file is hashed:
a bumped pin gets its checksums rewritten, and a pin whose version matches ``HEAD`` must
hash to its recorded value, or the tag moved under it. Any failure leaves every file as it
was and exits non-zero. Files that carry no known pins are ignored.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import subprocess
import sys
from typing import Any
import urllib.error
import urllib.request

import jinja2
import yaml

ARCHITECTURES = ('amd64', 'arm64')
DOWNLOAD_TIMEOUT_SECONDS = 120
JINJA = jinja2.Environment(undefined=jinja2.StrictUndefined, keep_trailing_newline=False)


class RefreshError(Exception):
    """A pin whose checksums cannot be trusted or recomputed."""


@dataclass(frozen=True)
class Pin:
    """One pinned download: its identity, version, and each architecture's URL and checksum."""

    key: str
    version: str
    urls: dict[str, str]
    checksums: dict[str, str]


@dataclass(frozen=True)
class ToolListPins:
    """A list of tool entries whose URLs are assembled by an install task file."""

    list_var: str
    task_file: str

    def versions(self, defaults: dict[str, Any]) -> dict[str, str]:
        """Map each tool's name to its version."""
        return {tool['name']: str(tool['version']) for tool in defaults[self.list_var]}

    def pins(self, defaults: dict[str, Any], repo_root: Path) -> list[Pin]:
        """Return one pin per tool entry, rendering URLs with the task file's templates."""
        asset_template, extension_template, url_template = self._templates(repo_root)
        pins = []
        for tool in defaults[self.list_var]:
            urls = {}
            for arch in ARCHITECTURES:
                context = {'dev_tools_tool': tool, 'system_arch': arch}
                context['dev_tools_tool_asset'] = _render(asset_template, context)
                context['dev_tools_tool_extension'] = _render(extension_template, context)
                urls[arch] = _render(url_template, context)
            checksums = {arch: tool['archives'][arch]['checksum'] for arch in ARCHITECTURES}
            pins.append(Pin(tool['name'], str(tool['version']), urls, checksums))
        return pins

    def _templates(self, repo_root: Path) -> tuple[str, str, str]:
        """Read the asset, extension, and URL expressions from the install task file."""
        tasks = yaml.safe_load((repo_root / self.task_file).read_text())
        facts: dict[str, str] = {}
        url = None
        for task in tasks:
            facts.update(task.get('ansible.builtin.set_fact', {}))
            url = task.get('ansible.builtin.get_url', {}).get('url', url)
        if url is None or 'dev_tools_tool_asset' not in facts:
            raise RefreshError(f'{self.task_file}: no download URL template found')
        return facts['dev_tools_tool_asset'], facts['dev_tools_tool_extension'], url


@dataclass(frozen=True)
class VariablePin:
    """A single pin spread over a version, a URL template, and a checksum map variable."""

    version_var: str
    url_var: str
    checksums_var: str
    arch_var: str

    def versions(self, defaults: dict[str, Any]) -> dict[str, str]:
        """Map the pin's version variable to its version."""
        return {self.version_var: str(defaults[self.version_var])}

    def pins(self, defaults: dict[str, Any], repo_root: Path) -> list[Pin]:
        """Return the pin, rendering its URL template once per architecture."""
        urls = {
            arch: _render(defaults[self.url_var], {**defaults, self.arch_var: arch})
            for arch in ARCHITECTURES
        }
        checksums = {arch: defaults[self.checksums_var][arch] for arch in ARCHITECTURES}
        return [Pin(self.version_var, str(defaults[self.version_var]), urls, checksums)]


PIN_FILES: dict[str, ToolListPins | VariablePin] = {
    'ansible/roles/dev_tools/defaults/main.yml': ToolListPins(
        list_var='dev_tools_pinned_tools',
        task_file='ansible/roles/dev_tools/tasks/install_pinned_tool.yml',
    ),
    'ansible/roles/agentic_tools/defaults/main.yml': VariablePin(
        version_var='agentic_tools_cc_filter_version',
        url_var='agentic_tools_cc_filter_download_url',
        checksums_var='agentic_tools_cc_filter_checksums',
        arch_var='system_arch',
    ),
    'ansible/roles/xpra_setup/defaults/main.yml': VariablePin(
        version_var='xpra_setup_virtualgl_version',
        url_var='xpra_setup_virtualgl_download_url',
        checksums_var='xpra_setup_virtualgl_checksums',
        arch_var='xpra_setup_virtualgl_arch',
    ),
}


def _render(template: str, context: dict[str, Any]) -> str:
    """Render one Jinja expression the way Ansible templates a variable."""
    try:
        return JINJA.from_string(template).render(context).strip()
    except jinja2.TemplateError as error:
        raise RefreshError(f'cannot render {template!r}: {error}') from error


def _digest_of(value: str) -> str:
    """Return the hex digest of a checksum written bare or as ``sha256:<hex>``."""
    return value.removeprefix('sha256:')


def _sha256_of_url(url: str) -> str:
    """Download a URL and return the SHA-256 of its body."""
    digest = hashlib.sha256()
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
            while chunk := response.read(1 << 20):
                digest.update(chunk)
    except (urllib.error.URLError, OSError) as error:
        raise RefreshError(f'download failed: {url}: {error}') from error
    return digest.hexdigest()


def _head_versions(path: str, spec: ToolListPins | VariablePin, repo_root: Path) -> dict[str, str]:
    """Map each pin key to its version at ``HEAD``; empty when the file is new."""
    shown = subprocess.run(
        ['git', 'show', f'HEAD:{path}'],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if shown.returncode != 0:
        return {}
    return spec.versions(yaml.safe_load(shown.stdout))


def refreshed_text(path: str, repo_root: Path) -> str | None:
    """Return the file's text with recomputed checksums, or None when it carries no pins."""
    spec = PIN_FILES.get(path)
    if spec is None:
        return None
    text = (repo_root / path).read_text()
    head_versions = _head_versions(path, spec, repo_root)
    for pin in spec.pins(yaml.safe_load(text), repo_root):
        bumped = head_versions.get(pin.key) != pin.version
        for arch in ARCHITECTURES:
            recorded = _digest_of(pin.checksums[arch])
            actual = _sha256_of_url(pin.urls[arch])
            if actual == recorded:
                continue
            if not bumped:
                raise RefreshError(
                    f'{path}: {pin.key} {pin.version} ({arch}) hashes to {actual}, '
                    f'but its version is unchanged and records {recorded}: the tag moved'
                )
            if text.count(recorded) != 1:
                raise RefreshError(f'{path}: checksum {recorded} is not unique in the file')
            text = text.replace(recorded, actual)
            print(f'{path}: {pin.key} {pin.version} ({arch}) -> {actual}')
    return text


def main(argv: list[str] | None = None) -> int:
    """Refresh the checksums in the given files; write nothing unless every pin verifies."""
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('files', nargs='*', help='Repository-relative paths; others ignored.')
    parser.add_argument('--repo-root', type=Path, default=Path.cwd())
    args = parser.parse_args(argv)

    updates: dict[str, str] = {}
    try:
        for path in dict.fromkeys(args.files):
            text = refreshed_text(path, args.repo_root)
            if text is not None:
                updates[path] = text
    except RefreshError as error:
        print(f'refresh-pin-checksums: {error}', file=sys.stderr)
        return 1
    for path, text in updates.items():
        target = args.repo_root / path
        if target.read_text() != text:
            target.write_text(text)
    return 0


if __name__ == '__main__':
    sys.exit(main())
