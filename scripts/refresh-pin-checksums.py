#!/usr/bin/env python3
"""
Recompute the per-architecture SHA-256 of pinned downloads in their pin files.

Each pin's download URL is rendered from its consumer's own templates — an Ansible role's
Jinja, or the macOS bootstrap's zsh — so the script fetches exactly what that consumer fetches. Every pin in a given file is hashed:
a bumped pin gets its checksums rewritten, and a pin whose version matches ``HEAD`` must
hash to its recorded value, or the tag moved under it. Any failure leaves every file as it
was and exits non-zero. Files that carry no known pins are ignored.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
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

    def load(self, text: str) -> Any:
        """Parse the pin file."""
        return yaml.safe_load(text)

    def versions(self, defaults: dict[str, Any]) -> dict[str, str]:
        """Map each tool's name to its version."""
        return {tool['name']: str(tool['version']) for tool in defaults[self.list_var]}

    def pins(self, defaults: dict[str, Any], repo_root: Path) -> list[Pin]:
        """Return one pin per tool entry, rendering URLs with the task file's templates."""
        facts, url_template = self._templates(repo_root)
        pins = []
        for tool in defaults[self.list_var]:
            urls = {}
            for arch in ARCHITECTURES:
                context = {'dev_tools_tool': tool, 'system_arch': arch}
                for name, template in facts:
                    context[name] = _render(template, context)
                urls[arch] = _render(url_template, context)
            checksums = {arch: tool['archives'][arch]['checksum'] for arch in ARCHITECTURES}
            pins.append(Pin(tool['name'], str(tool['version']), urls, checksums))
        return pins

    def _templates(self, repo_root: Path) -> tuple[list[tuple[str, str]], str]:
        """Read the facts, in task order, and the URL expression from the install task file."""
        tasks = yaml.safe_load((repo_root / self.task_file).read_text())
        facts: list[tuple[str, str]] = []
        url = None
        for task in tasks:
            facts.extend(task.get('ansible.builtin.set_fact', {}).items())
            url = task.get('ansible.builtin.get_url', {}).get('url', url)
        if url is None or not facts:
            raise RefreshError(f'{self.task_file}: no download URL template found')
        return facts, url


@dataclass(frozen=True)
class VariablePin:
    """A single pin spread over a version, a URL template, and a checksum map variable."""

    version_var: str
    url_var: str
    checksums_var: str
    arch_var: str

    def load(self, text: str) -> Any:
        """Parse the pin file."""
        return yaml.safe_load(text)

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


@dataclass(frozen=True)
class ZshReleasePins:
    """
    Release downloads a zsh script passes to ``install_release`` and checks in ``SHA256``.

    Constants are ``typeset -r NAME=value`` lines; each ``*_VERSION`` constant a download URL
    names is that pin's version. Per-architecture variables come from the ``arch=`` case arms.
    """

    def load(self, text: str) -> str:
        """Keep the script's text: it is parsed per query."""
        return text

    def versions(self, text: str) -> dict[str, str]:
        """Map each version constant a download URL names to its value."""
        return {pin.key: pin.version for pin in self._calls(text)}

    def pins(self, text: str, repo_root: Path) -> list[Pin]:
        """Return one pin per ``install_release`` call."""
        return self._calls(text)

    def _calls(self, text: str) -> list[Pin]:
        constants = dict(re.findall(r'^typeset -r (\w+)=(\S+)$', text, re.MULTILINE))
        block = re.search(r'^typeset -rA SHA256=\(\n(.*?)^\)$', text, re.MULTILINE | re.DOTALL)
        if block is None:
            raise RefreshError('no SHA256 map found')
        digests = dict(re.findall(r'^\s*(\S+) ([0-9a-f]{64})$', block.group(1), re.MULTILINE))
        arms = {}
        for assignments in re.findall(r'^\s*\S+\)\s+(arch=\w+(?: \w+=\S+)*) ;;$', text, re.M):
            variables = dict(item.split('=', 1) for item in assignments.split())
            arms[variables['arch']] = variables
        calls = re.findall(r'^\s*install_release (\S+) \\\n\s*(\S+) \\$', text, re.MULTILINE)
        if not calls or set(arms) != set(ARCHITECTURES):
            raise RefreshError('no install_release calls or arch case arms found')
        pins = []
        for key_template, url_template in calls:
            versions = sorted(
                {name for name in _zsh_names(url_template) if name.endswith('_VERSION')}
            )
            if len(versions) != 1:
                raise RefreshError(f'{url_template}: names {len(versions)} version constants')
            urls, checksums = {}, {}
            for arch in ARCHITECTURES:
                context = {**constants, **arms[arch]}
                urls[arch] = _render_zsh(url_template, context)
                key = _render_zsh(key_template, context)
                if key not in digests:
                    raise RefreshError(f'SHA256 records no digest for {key}')
                checksums[arch] = digests[key]
            pins.append(Pin(versions[0], constants[versions[0]], urls, checksums))
        return pins


ZSH_PARAMETER = re.compile(r'\$\{?(\w+)\}?')


def _zsh_names(template: str) -> list[str]:
    """Return the parameter names a zsh word expands."""
    return ZSH_PARAMETER.findall(template)


def _render_zsh(template: str, context: dict[str, str]) -> str:
    """Expand the plain ``$name`` parameters of a zsh word."""

    def value(match: re.Match[str]) -> str:
        if match.group(1) not in context:
            raise RefreshError(f'cannot render {template!r}: ${match.group(1)} is unknown')
        return context[match.group(1)]

    return ZSH_PARAMETER.sub(value, template)


PinSpec = ToolListPins | VariablePin | ZshReleasePins

PIN_FILES: dict[str, PinSpec] = {
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
    '.agents/plugins/agentdev/bin/macos-bootstrap.zsh': ZshReleasePins(),
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


def _head_versions(path: str, spec: PinSpec, repo_root: Path) -> dict[str, str]:
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
    return spec.versions(spec.load(shown.stdout))


def refreshed_text(path: str, repo_root: Path) -> str | None:
    """Return the file's text with recomputed checksums, or None when it carries no pins."""
    spec = PIN_FILES.get(path)
    if spec is None:
        return None
    text = (repo_root / path).read_text()
    head_versions = _head_versions(path, spec, repo_root)
    for pin in spec.pins(spec.load(text), repo_root):
        bumped = head_versions.get(pin.key) != pin.version
        stale: dict[str, dict[str, str]] = {}
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
            stale.setdefault(recorded, {})[arch] = actual
        for recorded, actuals in stale.items():
            if len(set(actuals.values())) != 1:
                raise RefreshError(
                    f'{path}: {pin.key} {pin.version} shares checksum {recorded} across '
                    f'{", ".join(actuals)}, which now hash differently'
                )
            if text.count(recorded) != len(actuals):
                raise RefreshError(f'{path}: checksum {recorded} is not unique to its pin')
            actual = next(iter(actuals.values()))
            text = text.replace(recorded, actual)
            print(f'{path}: {pin.key} {pin.version} ({", ".join(actuals)}) -> {actual}')
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
